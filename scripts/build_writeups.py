#!/usr/bin/env python3
"""Package submitted model writeups without creating or rewriting their prose."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = {'argon': 'Argon', 'codex': 'Codex', 'claude': 'Claude'}
ARCHIVED_REPORTS = {
    'argon': 'assets/reports/argon_report.md',
    'codex': 'assets/reports/Codex_report.md',
    'claude': 'assets/reports/report_claude-opus-5-5.md',
}


def build(root=ROOT):
    models = json.loads((root/'public/data/models.json').read_text())
    runs = {model['id']: model['selection']['reference'] for model in models['models']}
    target = root/'public/data/writeups'
    target.mkdir(parents=True, exist_ok=True)
    reports = []
    for id, name in NAMES.items():
        source_path = f'content/model-writeups/{id}.md'
        source = root/source_path
        archived = False
        if not source.exists() and (root/'public'/ARCHIVED_REPORTS[id]).exists():
            source_path = 'public/'+ARCHIVED_REPORTS[id]
            source = root/source_path
            archived = True
        raw = source.read_bytes() if source.exists() else b''
        text = raw.decode('utf-8')
        available = bool(text.strip())
        row = {'id': id, 'name': name, 'referenceRun': runs[id],
               'status': 'submitted' if available else 'pending',
               'sourcePath': source_path, 'markdown': text if available else '',
               'sha256': hashlib.sha256(raw).hexdigest() if available else None,
               'rawUrl': ('/'+ARCHIVED_REPORTS[id] if archived else f'/data/writeups/{id}.md') if available else None}
        if available and not archived:
            (target/(id+'.md')).write_bytes(raw)
        else:
            (target/(id+'.md')).unlink(missing_ok=True)
        reports.append(row)
    result = {'schemaVersion': 1, 'guideUrl': '/docs/model-writeups.md', 'reports': reports,
              'policy': 'Submitted text is displayed under the named model and preserved verbatim in its download. A report is an author account; it does not replace the independently extracted comparisons or source receipts.'}
    (root/'public/data/model-writeups.json').write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':'))+'\n')
    return result


if __name__ == '__main__':
    result = build()
    print('Model writeups:', ', '.join(row['name']+': '+row['status'] for row in result['reports']))
