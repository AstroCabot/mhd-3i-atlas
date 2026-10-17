# Shared-note attribution and recipient audit

The audit reviewed all 85 exported notes against their original filenames and explicit author headers. It found two author errors caused by searching the entire filename for agent names in a fixed order. A reply by Claude could therefore be assigned to a named recipient appearing later in its filename. Removing that apparent author's name from the recipient list then hid the actual exchange.

The corrected parser reads the filename's author prefix, after an optional leading timestamp, and checks it against the note's explicit `Author:` or Markdown `agent` header. Conflicting metadata raises an error rather than silently choosing an author. All 85 prefixes agree with their headers.

Recipient detection for shared notes now reads address clauses rather than every agent name in the same line. For example, “Reply to Argon: … the caution Codex raised” addresses Argon; the later mention of Codex does not make Codex a recipient. References, acknowledgements and general mentions remain present in the full text. An empty recipient list means that no supported address clause was found; it does not imply that a note was private or unread by the other agents.

| Note | Corrected fields |
|---|---|
| `claude_20261016T2244Z_reply_codex_argon.md` | `author`: Argon → Claude. `directed_to`: Codex → Argon and Codex. The title explicitly addresses both recipients and the header identifies Claude. |
| `claude_20261016T2310Z_solver_verification.md` | `directed_to`: Argon and Codex → Argon. `exchange_excerpt` now contains the actual reply to Argon, excluding the general heading about relevance to both solvers. The complete note is unchanged. |
| `claude_20261017T0049Z_reply_codex012_pressure.md` | `author`: Codex → Claude. `directed_to`: empty → Codex. `exchange_excerpt`: empty → the explicit reply heading. |
| `claude_20261017T0315Z_final_results.md` | `directed_to`: Argon and Codex → empty. `exchange_excerpt`: the general GPU availability statement → empty. The statement remains in the complete note, but is not an address clause. |

These four notes account for nine changed note fields: two `author` values, four `directed_to` lists and three `exchange_excerpt` values. The shared-notes export also has an updated generation timestamp and disclosure describing the attribution rules. No other note fields changed.

The corrected author totals are Argon 4, Codex 69 and Claude 12. Fourteen notes have explicit recipients; the total is unchanged because one previously hidden directed reply was restored and one general availability statement was removed from that category. `transcripts.json` therefore requires no count change and is preserved byte for byte.

Verification compared the exports before and after correction. All 85 complete note texts, source hashes, titles, timestamps, timestamp precision, chronological positions and cross-references are identical. All 85 original source hashes match their recorded SHA-256 receipts. All 447 conversation chunk and search-index files are byte-for-byte unchanged. The ordered `(note ID, complete exported text)` corpus has SHA-256:

```text
e5e7af39166717f137a421a34017fff73e1a680139851f4d882eab97f215dcb8
```

The new `--notes-only` option updates shared notes and, only when necessary, the transcript index's note counts. It neither reads nor regenerates conversation sessions:

```bash
python scripts/build_transcripts.py --notes-only
python -m unittest discover -s tests -p test_note_metadata.py -v
```

All six regression tests pass, covering the two misattributed real replies, recipient restoration, incidental-mention exclusion, contradictory author metadata, the complete source corpus and notes-only isolation. Results are recorded in `tests/note-metadata-results.txt`.

The science export's `meta.sourcePolicy` was also corrected to distinguish the unchanged quantitative comparison extraction from the separately regenerated high-cadence Claude animation. No scientific values or original research files changed.
