"""Check the standalone Pages artifact using only Python's standard library."""
from html.parser import HTMLParser
from pathlib import Path
import argparse
import hashlib
import json
import re
from urllib.parse import unquote, urlsplit


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and attrs.get('src'):
            self.urls.append(attrs['src'])
        if tag == 'link' and attrs.get('href'):
            self.urls.append(attrs['href'])


def check(directory):
    directory = Path(directory).resolve()
    required = ('index.html', '.nojekyll', 'app.js', 'site-paths.js', 'solar-player.js', 'solar-labels.js', 'frame-cache.js',
                'styles.css', 'theme.js', 'data/science.json', 'data/models.json',
                'research-pages.js', 'report-math.js', 'cooperation-page.js', 'data/agent-comparison.json', 'data/nasa-comparison.json', 'data/solver-code.json',
                'data/model-writeups.json', 'data/ccmc-movie-provenance.json', 'docs/ccmc-movie-audit.md', 'docs/model-writeups.md', 'docs/nasa-comparison-audit.md',
                'data/transcripts.json', 'data/physics-comparison.json', 'data/animation-v2.json',
                'data/animation-playback.json', 'data/science-overview.json', 'data/equations.json')
    for name in required:
        if not (directory / name).is_file():
            raise SystemExit(f'Missing packaged file: {name}')
    files = list(directory.rglob('*'))
    if any(path.is_symlink() for path in files):
        raise SystemExit('Pages artifacts must not contain symbolic links')
    files = [path for path in files if path.is_file()]
    total = sum(path.stat().st_size for path in files)
    if total >= 1_000_000_000:
        raise SystemExit('The published site exceeds the GitHub Pages 1 GB limit')
    if any(path.stat().st_size >= 100_000_000 for path in files):
        raise SystemExit('A packaged file exceeds the regular GitHub file-size limit')
    assets = Assets()
    assets.feed((directory / 'index.html').read_text())
    for url in assets.urls:
        parts = urlsplit(url)
        if parts.scheme or url.startswith('/'):
            raise SystemExit(f'Index asset is not repository-relative: {url}')
        if not (directory / unquote(parts.path)).is_file():
            raise SystemExit(f'Index asset does not exist: {url}')
    # Font paths are resolved relative to each stylesheet, rather than the domain root.
    for css in directory.rglob('*.css'):
        for match in re.finditer(r'url\(\s*[\'\"]?([^\s\)\'\"]+)', css.read_text()):
            url = match[1]
            if url.startswith('data:'):
                continue
            parts = urlsplit(url)
            if parts.scheme or url.startswith('/'):
                raise SystemExit(f'CSS asset is not repository-relative: {css.name}: {url}')
            if not (css.parent / unquote(parts.path)).is_file():
                raise SystemExit(f'CSS asset does not exist: {css.name}: {url}')
    index = json.loads((directory / 'data/transcripts.json').read_text())
    archive_urls = [index['notes']['url']]
    for session in index['sessions']:
        archive_urls += [session['search_url']] + [chunk['url'] for chunk in session['chunks']]
    for url in archive_urls:
        if not (directory / url.lstrip('/')).is_file():
            raise SystemExit(f'Missing packaged archive resource: {url}')
    catalogue = json.loads((directory / 'data/solver-code.json').read_text())
    reports = json.loads((directory / 'data/model-writeups.json').read_text())['reports']
    for row in catalogue['files'] + [report for report in reports if report['status'] == 'submitted']:
        path = directory / row['rawUrl'].lstrip('/')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise SystemExit(f'Missing or changed source/report download: {path}')
    for url in (catalogue['athena']['licenseUrl'], '/docs/model-writeups.md'):
        if not (directory / url.lstrip('/')).is_file():
            raise SystemExit(f'Missing source/report documentation: {url}')
    comparison = json.loads((directory / 'data/agent-comparison.json').read_text())
    for row in comparison['files']:
        path = directory / row['url'].lstrip('/')
        if not path.is_file() or path.stat().st_size != row['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise SystemExit(f'Missing or changed analyzer product: {path}')
    source = json.loads((directory / 'data/animation-v2.json').read_text())
    playback = json.loads((directory / 'data/animation-playback.json').read_text())
    for model, product in playback['models'].items():
        sequence = product['frameSequence']
        original = source['models'][model]['frameSequence']
        if sequence['timeMjd'] != original['timeMjd']:
            raise SystemExit('Playback batches changed the scientific time support')
        for field, rows in sequence['fields'].items():
            packs = []
            for pack in sequence['packs'][field]:
                raw = (directory / pack['url'].lstrip('/')).read_bytes()
                if len(raw) != pack['bytes'] or hashlib.sha256(raw).hexdigest() != pack['sha256']:
                    raise SystemExit(f"Changed frame batch: {pack['url']}")
                packs.append(raw)
            if len(rows) != len(original['fields'][field]):
                raise SystemExit('Playback batches dropped animation frames')
            for row, native in zip(rows, original['fields'][field]):
                raw = packs[row['pack']][row['offset']:row['offset'] + row['bytes']]
                if row['url'] != native['url'] or hashlib.sha256(raw).hexdigest() != native['sha256']:
                    raise SystemExit(f"Frame batch differs from the original: {row['url']}")
    science = json.loads((directory / 'data/science.json').read_text())
    opening = json.loads((directory / 'data/science-overview.json').read_text())
    if opening != {key: value for key, value in science.items() if key not in ('validation', 'benchmarks', 'provenance')}:
        raise SystemExit('Opening data differs from the scientific catalogue')
    print(f'Standalone Pages artifact: {len(files):,} files, {total / 1_000_000:.1f} MB; '
          'relative index/CSS assets and all archive chunks verified.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=Path('dist'))
    check(parser.parse_args().directory)
