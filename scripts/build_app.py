"""Package the research application without importing or changing solver code."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=ROOT/'dist')
args=parser.parse_args()
DIST=args.output.resolve()
DIST.mkdir(parents=True,exist_ok=True)

def copy_changed(src,dst):
    src,dst=Path(src),Path(dst)
    if not dst.exists() or src.stat().st_size!=dst.stat().st_size or src.stat().st_mtime_ns!=dst.stat().st_mtime_ns:
        shutil.copy2(src,dst)
    return str(dst)

for path in (ROOT/'src').glob('*'):
    if path.suffix in ('.js','.css'):
        copy_changed(path,DIST/path.name)
for name in ('data','assets'):
    shutil.copytree(ROOT/'public'/name,DIST/name,dirs_exist_ok=True,copy_function=copy_changed)
if (ROOT/'docs').exists():
    shutil.copytree(ROOT/'docs',DIST/'docs',dirs_exist_ok=True,copy_function=copy_changed)
for name in ('science.json','models.json','transcripts.json','equations.json','animation-v2.json'):
    with (DIST/'data'/name).open() as f:json.load(f)
models=json.loads((DIST/'data/models.json').read_text())
math=json.loads((DIST/'data/equations.json').read_text())['equations']
for eq in models['commonEquations']+[e for m in models['models'] for e in m['equations']]:
    if eq['latex'].replace(chr(92)*2,chr(92)) not in math:
        raise SystemExit('Equation catalogue is stale: run node scripts/compile_math.mjs')
manifest=json.loads((DIST/'data/animation-v2.json').read_text())
for model in manifest['models'].values():
    for media in model['media'].values():
        path=DIST/media['url'].lstrip('/')
        if not path.is_file():raise SystemExit(f'Missing animation {path}')
        if media.get('sha256') and hashlib.sha256(path.read_bytes()).hexdigest()!=media['sha256']:
            raise SystemExit(f'Animation checksum differs: {path}')
    sequence=model.get('frameSequence')
    if not sequence or sequence['width']!=768 or sequence['height']!=768:
        raise SystemExit('Portable 768-pixel animation frames are missing')
    for rows in sequence['fields'].values():
        if len(rows)!=sequence['frameCount'] or len(rows)!=len(sequence['timeMjd']):
            raise SystemExit('Animation frame sequence has inconsistent support')
        for row in rows:
            path=DIST/row['url'].lstrip('/')
            if not path.is_file() or path.stat().st_size!=row['bytes']:
                raise SystemExit(f'Missing or incomplete display frame {path}')
            if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
                raise SystemExit(f'Display-frame checksum differs: {path}')
# A changed source produces a new module/stylesheet request on ordinary reload.
fingerprint=hashlib.sha256(b''.join((DIST/name).read_bytes() for name in ('app.js','styles.css','solar-player.js','site-paths.js'))).hexdigest()[:12]
index=(ROOT/'index.html').read_text().replace('/styles.css',f'/styles.css?v={fingerprint}').replace('/app.js',f'/app.js?v={fingerprint}')
(DIST/'index.html').write_text(index)
(DIST/'.nojekyll').touch()
print(f'Built {DIST}: compiled equations, portable field frames and six video exports verified; version {fingerprint}')
