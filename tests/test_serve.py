"""Verify byte ranges needed by Safari video playback and the static-file boundary."""
import gzip
import http.client
import importlib.util
from pathlib import Path
import tempfile
import threading
import unittest

spec=importlib.util.spec_from_file_location('helios_serve',Path(__file__).resolve().parents[1]/'scripts/serve.py')
serve=importlib.util.module_from_spec(spec)
spec.loader.exec_module(serve)

class MediaServing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        serve.DIST=Path(cls.temp.name)
        (serve.DIST/'index.html').write_text('<title>test</title>')
        (serve.DIST/'movie.mp4').write_bytes(bytes(range(256))*8)
        (serve.DIST/'record.json').write_text('{"value":42}')
        class Quiet(serve.Handler):
            def log_message(self,*args):pass
        cls.server=serve.ThreadingHTTPServer(('127.0.0.1',0),Quiet)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.temp.cleanup()
    def request(self,path='/movie.mp4',headers=None,method='GET'):
        connection=http.client.HTTPConnection(*self.server.server_address,timeout=3)
        connection.request(method,path,headers=headers or {})
        r=connection.getresponse();result=(r.status,dict(r.getheaders()),r.read())
        connection.close();return result
    def test_safari_initial_two_byte_request(self):
        status,headers,body=self.request(headers={'Range':'bytes=0-1'})
        self.assertEqual(status,206);self.assertEqual(body,b'\0\1')
        self.assertEqual(headers['Content-Range'],'bytes 0-1/2048')
        self.assertEqual(headers['Content-Type'],'video/mp4')
        self.assertEqual(headers['Accept-Ranges'],'bytes')
    def test_middle_and_open_ended_seek(self):
        for h,expected in [('bytes=250-259',(bytes(range(256))*8)[250:260]),('bytes=2040-',bytes(range(248,256)))]:
            status,headers,body=self.request(headers={'Range':h})
            self.assertEqual(status,206);self.assertEqual(body,expected)
            self.assertEqual(int(headers['Content-Length']),len(expected))
    def test_suffix_and_clamped_end(self):
        self.assertEqual(self.request(headers={'Range':'bytes=-3'})[2],bytes([253,254,255]))
        self.assertEqual(self.request(headers={'Range':'bytes=2046-9999'})[2],bytes([254,255]))
    def test_invalid_ranges(self):
        for h in ('bytes=9999-','bytes=2-1','bytes=0-1,5-6','bytes=-0','bytes=-'):
            status,headers,body=self.request(headers={'Range':h})
            self.assertEqual(status,416);self.assertEqual(body,b'')
    def test_head_and_etag_revalidation(self):
        status,headers,body=self.request(method='HEAD')
        self.assertEqual(status,200);self.assertEqual(body,b'')
        self.assertEqual(headers['Content-Length'],'2048')
        self.assertEqual(self.request(headers={'If-None-Match':headers['ETag']})[0],304)
    def test_gzip_and_private_paths(self):
        status,headers,body=self.request('/record.json',{'Accept-Encoding':'gzip'})
        self.assertEqual(gzip.decompress(body),b'{"value":42}')
        self.assertEqual(headers['Cache-Control'],'no-cache')
        self.assertEqual(self.request('/.private')[0],404)
        self.assertEqual(self.request('/missing')[0],404)

if __name__=='__main__':unittest.main()
