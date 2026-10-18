# Submit an agent's model writeup

The **Model writeups** view has separate Argon, Codex and Claude slots. Each remains pending until a report is supplied. Existing application summaries and transcripts remain accessible separately. The initial supplied reports are read directly from `public/assets/reports/argon_report.md`, `Codex_report.md` and `report_claude-opus-5-5.md`, including their relative figures and evidence links.

Ask each agent to save its report in this application repository:

| Agent | File |
|---|---|
| Argon | `content/model-writeups/argon.md` |
| Codex | `content/model-writeups/codex.md` |
| Claude | `content/model-writeups/claude.md` |

Use `content/model-writeups/_template.md` as an outline. Identify the author, date, exact selected run and code revision. Distinguish the reported model from sensitivity cases and experimental solvers. Include physical assumptions, core algorithms, boundary/calibration choices, benchmarks, spacecraft and NASA comparisons, comet/X-ray interpretation, resources, reproduction steps and limitations.

A file in `content/model-writeups/` takes precedence over that model's initial report. Relative figure/evidence links resolve beside the original report, so place its accompanying files in the corresponding published directory. For a new report in `content/model-writeups/`, use absolute HTTPS URLs or links to packaged assets such as `../../assets/reports/figure.png` (resolved from its download location in `data/writeups/`).

Reports support paragraphs, lists, tables, links, fenced code blocks, inline `$math$` and display `$$math$$`. The reading view omits Markdown headings and submission banners, uses one centered column with consistent paragraph spacing, and reflows equations over multiple lines. Headings and original TeX remain intact in the Markdown download. Raw HTML is shown as text. Use links such as `#code?agent=claude&file=claude-core&line=90` to refer to a method in the source viewer. Source file IDs are available in that view's URL.

The original Markdown is packaged without editing and offered as a download. The application treats the text as a submitted account; its numerical claims do not overwrite the shared comparisons or their provenance.

For a local package build, run:

```bash
python scripts/build_writeups.py
python scripts/build_app.py
```

Commit the submitted file and push to `main`. The Pages workflow runs the writeup packager automatically before publishing. Neither this process nor the source viewer needs an MHD rerun. Keep `../mhd_llm` immutable.
