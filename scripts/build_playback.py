"""Batch the original WebP bytes for playback; retain the scientific source products."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path


def package_playback(directory, frames_per_pack=8):
    directory = Path(directory)
    manifest = json.loads((directory / 'data/animation-v2.json').read_text())
    playback = deepcopy(manifest)
    target = directory / 'assets/animation-v2/frame-packs'
    target.mkdir(parents=True, exist_ok=True)
    written = set()
    for model, product in playback['models'].items():
        sequence = product['frameSequence']
        sequence['packs'] = {}
        for field, rows in sequence['fields'].items():
            packs, compact = [], []
            for start in range(0, len(rows), frames_per_pack):
                payload = bytearray()
                for row in rows[start:start + frames_per_pack]:
                    raw = (directory / row['url'].lstrip('/')).read_bytes()
                    if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
                        raise ValueError(f"Changed animation frame: {row['url']}")
                    compact.append({'url': row['url'], 'bytes': len(raw),
                                    'pack': len(packs), 'offset': len(payload)})
                    payload.extend(raw)
                digest = hashlib.sha256(payload).hexdigest()
                name = f'{model}-{field}-{start:03d}-{digest[:12]}.bin'
                path = target / name
                if not path.exists() or path.read_bytes() != payload:
                    path.write_bytes(payload)
                written.add(name)
                packs.append({'url': '/' + path.relative_to(directory).as_posix(),
                              'bytes': len(payload), 'sha256': digest})
            sequence['packs'][field] = packs
            sequence['fields'][field] = compact
    for path in target.glob('*.bin'):
        if path.name not in written:
            path.unlink()
    (directory / 'data/animation-playback.json').write_text(
        json.dumps(playback, ensure_ascii=False, separators=(',', ':')) + '\n')
    science = json.loads((directory / 'data/science.json').read_text())
    opening = {key: value for key, value in science.items()
               if key not in ('validation', 'benchmarks', 'provenance')}
    (directory / 'data/science-overview.json').write_text(
        json.dumps(opening, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(f'Playback: {len(written)} packs of unchanged WebP frames; opening data packaged separately.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=Path('dist'))
    package_playback(parser.parse_args().directory)
