"""Regression checks for attribution and address detection in the shared record."""
from pathlib import Path
import collections
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_transcripts', ROOT / 'scripts/build_transcripts.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class SharedNoteMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notes = json.loads((ROOT / 'public/data/shared-notes.json').read_text())['notes']
        cls.by_id = {note['id']: note for note in cls.notes}

    def test_reply_authors_are_not_their_recipients(self):
        for note_id in ('claude_20261016T2244Z_reply_codex_argon', 'claude_20261017T0049Z_reply_codex012_pressure'):
            note = self.by_id[note_id]
            self.assertEqual(note['author'], 'claude')
            self.assertEqual(builder.note_author(note['filename'], note['text']), 'claude')
        self.assertEqual(collections.Counter(note['author'] for note in self.notes), {'argon': 4, 'codex': 69, 'claude': 12})

    def test_actual_replies_restore_the_intended_recipients(self):
        expected = {
            'claude_20261016T2244Z_reply_codex_argon': ['argon', 'codex'],
            'claude_20261017T0049Z_reply_codex012_pressure': ['codex'],
            'claude_20261016T2310Z_solver_verification': ['argon'],
        }
        for note_id, recipients in expected.items():
            self.assertEqual(self.by_id[note_id]['directed_to'], recipients)

    def test_general_mentions_do_not_become_directed_messages(self):
        note = self.by_id['claude_20261017T0315Z_final_results']
        self.assertEqual(note['directed_to'], [])
        self.assertIsNone(note['exchange_excerpt'])
        addressed, _ = builder.note_addresses('Useful to Argon and Codex: this is a general discussion.', 'claude')
        self.assertEqual(addressed, [])
        addressed, _ = builder.note_addresses('Reply to Argon: this is the caution Codex raised.', 'claude')
        self.assertEqual(addressed, ['argon'])

    def test_conflicting_header_and_filename_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            builder.note_author('claude_20261016T2244Z_reply_codex_argon.md', 'Author: Argon')

    def test_complete_corpus_receipts_and_chronology(self):
        self.assertEqual(len(self.notes), 85)
        self.assertEqual(self.notes, sorted(self.notes, key=lambda note: (note['timestamp'] or '', note['filename'])))
        for note in self.notes:
            raw = (ROOT.parent / 'mhd_llm/shared_notes' / note['filename']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), note['source_sha256'])
            self.assertEqual(note['text'], builder.redact(raw.decode()))

    def test_notes_only_does_not_regenerate_conversations(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            sentinel = {'sessions': [{'id': 'preserve-this-session', 'tokens': 12345}], 'stats': {'notes': 85, 'messages': 16745}, 'notes': {'url': '/data/shared-notes.json', 'count': 85, 'directed_count': 14}}
            index = output / 'transcripts.json'
            index.write_text(json.dumps(sentinel, indent=4) + '\n')
            before = index.read_bytes()
            subprocess.run([sys.executable, str(ROOT / 'scripts/build_transcripts.py'), '--notes-only', '--output', directory], cwd=ROOT, check=True, capture_output=True)
            self.assertEqual(index.read_bytes(), before)
            self.assertFalse((output / 'transcripts').exists())
            self.assertEqual(len(json.loads((output / 'shared-notes.json').read_text())['notes']), 85)


if __name__ == '__main__':
    unittest.main()
