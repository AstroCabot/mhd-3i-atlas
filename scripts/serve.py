"""Serve the packaged research application, including byte-range video requests."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import gzip
import io
import json
import mimetypes
import re

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self._remaining = None
        super().__init__(*args, directory=str(DIST), **kwargs)

    def do_GET(self):
        stream = self.send_head()
        if stream is not None:
            try:
                self.copyfile(stream, self.wfile)
            except (BrokenPipeError, ConnectionResetError):
                pass  # A browser may cancel a media preload or seek.
            finally:
                stream.close()

    def send_head(self):
        self._remaining = None
        request_path = urlsplit(self.path).path
        if request_path == '/health':
            body = json.dumps({'status':'ok','application':'helios','version':'2','data_mode':'archived'}).encode()
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-cache')
            self.end_headers()
            return io.BytesIO(body)
        target = Path(self.translate_path(self.path)).resolve()
        if not target.is_relative_to(DIST.resolve()) or request_path.startswith('/.'):
            self.send_error(404)
            return None
        if target.is_dir():
            target = target / 'index.html'
        if not target.is_file():
            self.send_error(404)
            return None
        stat = target.stat()
        size = stat.st_size
        media_type = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
        etag = f'"{stat.st_mtime_ns:x}-{size:x}"'
        range_header = self.headers.get('Range')
        if_range = self.headers.get('If-Range')
        if if_range and if_range not in (etag, self.date_time_string(stat.st_mtime)):
            range_header = None
        if not range_header and self.headers.get('If-None-Match') == etag:
            self.send_response(304)
            self.send_header('ETag',etag)
            self.send_header('Cache-Control','no-cache')
            self.end_headers()
            return None
        if range_header:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)',range_header.strip())
            if not match or not any(match.groups()) or size == 0:
                return self.invalid_range(size)
            lo,hi = match.groups()
            if not lo:
                count = int(hi)
                if count <= 0:
                    return self.invalid_range(size)
                start,end = max(0,size-count),size-1
            else:
                start = int(lo)
                end = min(int(hi),size-1) if hi else size-1
            if start >= size or end < start:
                return self.invalid_range(size)
            stream = target.open('rb')
            stream.seek(start)
            self._remaining = end-start+1
            self.send_response(206)
            self.send_header('Content-Type',media_type)
            self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            self.send_header('Content-Length',str(self._remaining))
        elif target.suffix in ('.json','.js','.css','.svg') and 'gzip' in self.headers.get('Accept-Encoding',''):
            body = gzip.compress(target.read_bytes(),compresslevel=5)
            stream = io.BytesIO(body)
            self.send_response(200)
            self.send_header('Content-Type',media_type)
            self.send_header('Content-Encoding','gzip')
            self.send_header('Vary','Accept-Encoding')
            self.send_header('Content-Length',str(len(body)))
        else:
            stream = target.open('rb')
            self.send_response(200)
            self.send_header('Content-Type',media_type)
            self.send_header('Content-Length',str(size))
        self.send_header('Accept-Ranges','bytes')
        self.send_header('Last-Modified',self.date_time_string(stat.st_mtime))
        self.send_header('ETag',etag)
        # Revalidate scripts and data on reload; video files are versioned assets.
        self.send_header('Cache-Control','public, max-age=86400' if target.suffix in ('.mp4','.webm','.woff2','.otf','.ttf') else 'no-cache')
        self.end_headers()
        return stream

    def invalid_range(self,size):
        self.send_response(416)
        self.send_header('Content-Range',f'bytes */{size}')
        self.send_header('Content-Length','0')
        self.end_headers()
        return None

    def copyfile(self,source,output):
        while self._remaining is None or self._remaining > 0:
            length = 128*1024 if self._remaining is None else min(128*1024,self._remaining)
            block = source.read(length)
            if not block:
                break
            output.write(block)
            if self._remaining is not None:
                self._remaining -= len(block)

    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','same-origin')
        super().end_headers()

    def list_directory(self,path):
        self.send_error(404)
        return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8080)
    parser.add_argument('--directory',type=Path,default=DIST)
    args = parser.parse_args()
    DIST = args.directory.resolve()
    if not (DIST/'index.html').exists():
        raise SystemExit('Build first: python scripts/build_app.py')
    server = ThreadingHTTPServer((args.host,args.port),Handler)
    print(f'Serving {DIST} at http://{args.host}:{args.port}',flush=True)
    server.serve_forever()
