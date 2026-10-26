When AI agents model the solar wind
==================================

Open index.html for the self-contained, responsive article.
Open report.pdf for the typeset printable version.

The article contains four comparison tables, three original figures and eight
featured quotation records. Ten exact quotation records are documented in the
source register. Qualitative assessments use anchored labels, not summed scores.

figures/ contains each figure as editable SVG, PNG and vector PDF.
derived/ contains the complete quantitative tables, model/data pairs, quotation
provenance and source hashes. The paired evaluation uses the same 96 native
hourly observations per spacecraft and model. Calibration histories differ;
this is a descriptive reconstruction comparison, not a predictive leaderboard.

Original experiment files were not modified and models were not rerun.
No content was deployed or published to a remote service.

Reproduce from the original research archive:

  python -B derive_validation.py
  python -B collect_quotes.py
  python -B build_report.py --collect
  python -B render_report.py

Run these commands from this directory or use their absolute paths.
The scripts locate the original research data in the parent directory. Private
session logs under the user's home directory are required to recollect tokens
and reverify quotes. They are not included in the publication bundle.

To rebuild prose and figures while reusing the saved effort and quote records:

  python -B build_report.py

This still needs the original comet series; matched monitor pairs are bundled.
The static HTML, PDF, data tables and figures can be read without any Python
packages or access to the original archive.

Dependencies: Python 3, numpy, pandas, matplotlib, Jinja2, pymupdf; a local
Chromium binary for PDF rendering. No experiment modules are imported.

Interpretive corrections:
- Argon's extra human message is treated as a minimal operational nudge.
  It provided no scientific assumption or correction; the solver and first
  comet run were already under way. No causal scientific effect is established.
- Generated tokens are not unique words, billing tokens or energy measurements.
- Summed concurrent solver runtimes are not exclusive GPU-hours.
- The comet flux spread is conditional model sensitivity, not a calibrated CI.
- Competitive Codex delivered nominal products but left final closeout incomplete.

For publication, retain the qualification below Table 3 and the quotation record
types. Do not relabel assimilated nominal curves as blind predictions or public
commentary as private reasoning.
