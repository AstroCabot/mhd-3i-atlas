#!/usr/bin/env python3
"""Render retained solar-wind fields to transparent browser-ready PNG tiles.

This is a style-only renderer. It reads the compact, already homogenized JSON
products; no native science archive or simulation is accessed. Rerun after
changing PALETTE or ALPHA to update the presentation independently of analysis.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

APP = Path(__file__).resolve().parents[1]
DATA = APP / 'public/data'
DEST = APP / 'public/assets/frames'
PALETTE = [[21, 40, 73], [58, 54, 116], [158, 71, 118], [224, 132, 89], [245, 221, 143]]
ALPHA = 205


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def colorize(codes, encoding, limits):
    """Straight-alpha RGBA with fixed logarithmic RGB palette interpolation."""
    a = np.asarray(codes)
    valid = a != encoding['missing']
    log_values = encoding['log10Offset'] + (a.astype(float) - 1) / encoding['log10Scale']
    lower, upper = np.log10(limits)
    position = np.clip((log_values - lower) / (upper - lower), 0, 1) * (len(PALETTE) - 1)
    left = np.minimum(position.astype(int), len(PALETTE) - 2)
    fraction = position - left
    palette = np.array(PALETTE, float)
    rgb = np.rint(palette[left] * (1 - fraction[..., None]) + palette[left + 1] * fraction[..., None]).astype(np.uint8)
    rgba = np.zeros(a.shape + (4,), np.uint8)
    rgba[..., :3] = np.where(valid[..., None], rgb, 0)
    rgba[..., 3] = np.where(valid, ALPHA, 0)
    # Scientific row zero is south; PNG row zero is north.
    return rgba[::-1]


def verify_palette_endpoints():
    encoding = {'missing': 0, 'log10Offset': 3, 'log10Scale': 5000}
    # 1e3 and 1e7 are exactly represented by the logarithmic integer encoding.
    rgba = colorize(np.array([[0, 1, 20001]], np.uint16), encoding, [1e3, 1e7])[0]
    assert rgba[0].tolist() == [0, 0, 0, 0]
    assert rgba[1].tolist() == PALETTE[0] + [ALPHA]
    assert rgba[2].tolist() == PALETTE[-1] + [ALPHA]


def main():
    verify_palette_endpoints()
    science_path = DATA / 'science.json'
    science = json.loads(science_path.read_text())
    animation = science['animation']
    sources = {str(science_path.relative_to(APP / 'public')): sha256(science_path)}
    manifest = {'schemaVersion': 1, 'renderer': 'scripts/render_frames.py',
        'rendererSha256': sha256(__file__), 'width': animation['width'], 'height': animation['height'],
        'palette': PALETTE, 'paletteInterpolation': 'linear RGB between uniformly spaced logarithmic color stops',
        'alpha': ALPHA, 'transparentCode': 0, 'rowOrder': 'North at top; encoded science rows reversed',
        'timeMjd': animation['timeMjd'], 'extentAu': animation['extentAu'],
        'limits': {'flux': animation['fluxLimits'], 'contrast': animation['contrastLimits']},
        'sourceHashes': sources, 'models': {},
        'verification': {'paletteEndpoints': True, 'allMissingMasks': True,
                         'allImagePixels': True, 'sourceHashesUnchanged': True},
        'rebuild': 'python scripts/render_frames.py'}
    for id in ('argon', 'codex', 'claude'):
        source_path = DATA / f'solarwind-{id}.json'
        sources[str(source_path.relative_to(APP / 'public'))] = sha256(source_path)
        data = json.loads(source_path.read_text())
        assert data['timeMjd'] == animation['timeMjd']
        width, height = data['width'], data['height']
        assert (width, height) == (animation['width'], animation['height'])
        target = DEST / id
        target.mkdir(parents=True, exist_ok=True)
        fields = {}
        for field in ('flux', 'contrast'):
            images = []
            limits = animation[field + 'Limits']
            for i, flat in enumerate(data[field]):
                native = np.asarray(flat).reshape(height, width)
                rgba = colorize(native, data['encoding'], limits)
                assert np.array_equal(rgba[..., 3] == 0, native[::-1] == 0)
                assert np.all(rgba[..., 3][native[::-1] != 0] == ALPHA)
                path = target / f'{field}-{i:02d}.png'
                Image.fromarray(rgba).save(path, optimize=True)
                # Read back every PNG, detecting orientation/channel or mode
                # changes by the encoder as well as missing-data corruption.
                with Image.open(path) as image:
                    assert image.mode == 'RGBA'
                    assert np.array_equal(np.asarray(image), rgba)
                images.append({'url': '/assets/frames/' + str(path.relative_to(DEST)),
                    'frame': i, 'timeMjd': animation['timeMjd'][i],
                    'bytes': path.stat().st_size, 'sha256': sha256(path),
                    'validPixels': int(np.count_nonzero(native))})
            assert len(images) == len(animation['timeMjd'])
            fields[field] = images
        manifest['models'][id] = {'nativePlane': animation['models'][id]['nativePlane'],
            'definition': animation['models'][id]['definition'], 'fields': fields}
    for rel, digest in sources.items():
        assert sha256(APP / 'public' / rel) == digest
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(f'Rendered and verified {len(animation["timeMjd"]) * 3 * 2} transparent RGBA PNG tiles at {animation["width"]}×{animation["height"]}.')
    print(f'Manifest: {DEST / "manifest.json"}')


if __name__ == '__main__':
    main()
