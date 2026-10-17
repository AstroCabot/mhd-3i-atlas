#!/usr/bin/env python3
"""Apply audited explanatory copy to a generated science document.

This changes only exact string matches listed in data/editorial.json. It does
not rebuild scientific analysis, alter arrays or update animation manifests.
Run after the science builder and before packaging or hashing its output:

    python scripts/apply_editorial_metadata.py --input public/data/science.json
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

APP = Path(__file__).resolve().parents[1]


def apply(document, replacements):
    mapping = {row['old']: row['new'] for row in replacements}
    counts = Counter()

    def walk(value):
        if isinstance(value, dict):
            return {key: walk(item) for key, item in value.items()}
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, str) and value in mapping:
            counts[value] += 1
            return mapping[value]
        return value

    return walk(document), counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=APP / 'public/data/science.json')
    parser.add_argument('--output', type=Path, help='Default: replace the input document.')
    parser.add_argument('--editorial', type=Path, default=APP / 'public/data/editorial.json')
    args = parser.parse_args()
    policy = json.loads(args.editorial.read_text())['scienceReplacements']['replacements']
    original = json.loads(args.input.read_text())
    revised, counts = apply(original, policy)
    target = args.output or args.input
    target.write_text(json.dumps(revised, ensure_ascii=False, indent=2) + '\n')
    print(f'Updated {sum(counts.values())} explanatory string fields in {target}; scientific values unchanged.')


if __name__ == '__main__':
    main()
