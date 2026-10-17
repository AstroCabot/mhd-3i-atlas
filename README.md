# 3I/ATLAS — Comparative solar-wind MHD

This application compares the selected Argon, Codex and Claude reconstructions of the solar wind incident on 3I/ATLAS during XMM–Newton observation 0963720201. The original `../mhd_llm` directory is read-only. Packaging and presentation changes do not run an MHD solver.

## Open from a Mac

The application runs in WSL on port **8080**, in tmux session `helios_dashboard`. If your SSH connection logs into **Windows**, forward to WSL’s current address:

```bash
ssh -N -T -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:8080:172.24.73.84:8080 cabot@TORCH
```

Use your actual Windows SSH username and reachable hostname/IP in place of `cabot@TORCH` where necessary. Leave that terminal open, then run on your Mac:

```bash
open http://127.0.0.1:8080
```

After a WSL restart, obtain its current address in Windows PowerShell with `wsl hostname -I` and update the forwarding target. If your usual SSH connection logs directly into **WSL**, keep that SSH destination and forward to `127.0.0.1:8080` instead. VS Code Remote users may forward port 8080 in the Ports panel.

```bash
# In WSL:
curl http://127.0.0.1:8080/health
tmux attach -t helios_dashboard
# Manual start if needed:
python scripts/serve.py --host 0.0.0.0 --port 8080
```

Python 3.10+ serves the packaged application. Fonts, equations, charts, fields and transcripts are local; the running site needs no API keys, CDN, Node server or access to the original research directory. The server supports byte ranges and HEAD requests for the downloadable MP4s.

## Publish on GitHub Pages

The live application is at **https://astrocabot.github.io/mhd-3i-atlas/**; its repository is [AstroCabot/mhd-3i-atlas](https://github.com/AstroCabot/mhd-3i-atlas). The included [deployment workflow](.github/workflows/pages.yml) packages the precomputed assets with Python and publishes pushes to `main`. Viewing the public site needs no SSH tunnel or running WSL machine. The [publishing instructions](docs/github-pages.md) also explain how to publish a separate copy under another personal account. Both account-root and repository-prefixed Pages URLs are supported.

## Saved manila dashboard

The deployed dashboard before the notebook refinements is preserved by the Git tag [`manila-dashboard-2026-10-17`](https://github.com/AstroCabot/mhd-3i-atlas/tree/manila-dashboard-2026-10-17), commit `2396a71`. To inspect that version without changing the current checkout:

```bash
git worktree add ../mhd-manila-dashboard manila-dashboard-2026-10-17
```

## Revision and independent audits

The revised presentation follows the numbered scientific sections, TeX Gyre Schola typography, ruled figures and restrained colour use of the [Henyey source site](https://oklo.github.io/Henyey/source.html). Its prose identifies quantities, methods and limitations directly. The layout removes the large introductory banner and promotional cards and uses larger chart labels, compact tables and figure captions.

Independent reviews cover prose, layout, scientific interpretation and animation:

- `docs/editorial-audit.md`: online style references, all eight views, model prose and the rendered-copy review. Original transcript and shared-note text remains verbatim.
- `docs/layout-audit.md`: reference inspection, layout measurements, typography and viewport review.
- `docs/animation-audit.md`: archived spatial/time support, interpolation, player behaviour and numerical checks.
- `docs/scientific-review.md`: selected CME forcing, common comparison quantities and source-specific limits.
- `docs/shared-note-metadata-audit.md`: corrected authors and addressed recipients, with original text preserved.
- `docs/notebook-review.md`: consistency of the notebook presentation, integrated comparison tables and archive entry points.

The original 128², six-hour, stepwise image display has been replaced with 768² fields rendered directly from the native binary/NPY slices. The portable player uses 373 display epochs per field at 30-minute spacing, persistent predecoded image layers and continuous display interpolation. It preserves the previous decoded field until the next is ready. The 2,238 WebP frames are fetched as needed. The six 30 fps, 48-second H.264 videos remain available as standalone exports.

**Claude now uses genuine 30-minute solver output.** An output-only replay of its selected production setup retains 373 half-hour states, with all 63 coincident three-hour field arrays byte-identical to the original archive. Its slice has 320×360 radial/longitude samples. Argon retains 160×180 samples at about three-hour cadence; Codex retains a 512² interpolation of its native CT grid at about six hours. Their intermediate display epochs remain interpolated. All three use the same geometric-UTC clock, projected extent and colour scales, with their distinct physical support stated beside each field. Higher display resolution does not add spatial information.

The header’s theme switch selects the existing dark palette or a manila-paper light palette. The choice is saved in the browser and applied before the page is drawn. Charts, tables, equations and exports follow the selected palette; switching themes preserves field playback and chart zoom.

## Application views

1. **Overview:** incident-flux curves, common exposure-weighted density/speed/flux table and selected solver configurations.
2. **Solar wind:** synchronized field playback, continuous scrubber, field selection, full-screen view and comet time series.
3. **Verification:** native benchmark profiles, convergence curves and registered numerical controls.
4. **Observations:** common hourly spacecraft samples/residual masks, WSA boundary map and coronal-replication evidence.
5. **X-ray comparison:** eight measured PN rates with uncertainties, common exposure matching, arrival-clock normalization and native/report mean reconciliation.
6. **Agent conversations:** 18 sessions, 16,745 paginated entries, full-session term search, 85 shared notes and recorded agent settings. Direct links open main conversations, explicitly addressed exchanges and a four-note CME input-audit case study. Encrypted material is marked unavailable; credential patterns are redacted.
7. **Model physics:** precompiled LaTeX/MathML equations, formulations, boundary conditions, calibration and limitations.
8. **Resources and provenance:** scoped CPU/GPU/token accounting, source discrepancies and SHA-256 receipts.

## Source organisation

```text
src/app.js                     routes, scientific tables and SVG charts
src/solar-player.js            persistent field player and synchronized controls
src/site-paths.js              asset URLs for root and repository-prefixed hosting
src/styles.css                 responsive scientific typography and layout
public/data/                   science, models, session chunks and animation manifest
public/assets/animation-v2/     native-derived high-resolution playback products
scripts/build_science.py        common science extraction, no solver reruns
scripts/build_models.py         model descriptions and source receipts
scripts/build_transcripts.py    allowlisted session and shared-note extraction
scripts/build_animation_v2.py   direct native-slice rendering
scripts/refine_claude_movie.py  verified output-only CUDA replay for finer movie cadence
scripts/compile_math.mjs        build-time KaTeX compilation to HTML/MathML
scripts/build_app.py            incremental standalone packaging and asset checks
scripts/serve.py                static server with gzip, byte ranges and health endpoint
tests/                         scientific, media-server and browser checks
```

For presentation-only changes:

```bash
python scripts/build_app.py
```

The existing server serves updated files; reload the browser. Scripts, styles, imported modules and packaged JSON requests carry the same content version. Changing typography or layout does not rerun scientific analysis. A staging build can be served separately:

```bash
python scripts/build_app.py --output runtime/review
python scripts/serve.py --directory runtime/review --port 8081
```

To regenerate source-derived products:

```bash
python -m pip install -r requirements-analysis.txt
python scripts/build_models.py
python scripts/build_physics_comparison.py
python scripts/build_science.py
python scripts/apply_editorial_metadata.py --input public/data/science.json
python scripts/build_transcripts.py
python scripts/build_animation_v2.py --with-images
node scripts/compile_math.mjs
python scripts/build_app.py
```

Animation rendering also needs ffmpeg. Transcript extraction needs the identified local session logs under `~/.codex`, `~/.claude` and `~/.gemini/antigravity-cli`. The packaged site works without those originals. The extraction allowlist excludes the application-building conversation and unrelated sessions.

To reproduce Claude's finer native movie, first run the output-only replay on a compatible NVIDIA GPU with nvcc and the original research inputs available, then render its two display products:

```bash
python scripts/refine_claude_movie.py
python scripts/build_animation_v2.py --model claude --with-images
python scripts/build_app.py
```

The replay writes only to application-owned runtime storage and verifies the original inputs and coincident states. Its [verification receipt](public/data/claude-temporal-refinement.json) records source hashes, compiler settings and runtime. This additional movie computation is separate from the original research resource counters and quantitative comet/probe results. The published site and its Pages build use committed display assets and need no GPU or solver.

## Verification

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
# Browser tests require Node 22.12+ and the browser matching this Playwright version:
npm ci
PLAYWRIGHT_SKIP_BROWSER_GC=1 npx playwright install chromium
npm test
node tests/solar-player.mjs
```

`TEST_URL` selects a different serving address. `CHROMIUM_PATH` is an optional browser executable override; use the installed matching browser unless diagnosing the host. Browser checks cover navigation, model/spacecraft selection, math, source archives, exports and mobile layout. Playback checks additionally examine decoded fields, clock advancement, seeking, synchronization and persistence of the image/SVG elements. Scientific checks compare native outputs, flux units, PN exposures, light-time conversion, resampling and source hashes.

## Scientific conventions

Comet plots use photon-arrival UTC at the geometric Earth proxy. Spatial playback and spacecraft data use geometric UTC. Exact native piecewise-linear samples and accepted GTI endpoints determine tabulated means; display resampling does not determine metrics. Missing values remain masked.

Argon’s retained movie samples a constant solar-latitude −6.455° cone. Claude/Codex sample the ecliptic. Each available surface is projected into J2000 ecliptic x/y; a scalar slice cannot supply the missing three-dimensional field. Claude supplies the radial proxy nₚvᵣ, while Argon/Codex supply nₚ|v|. Argon’s fine run supplies the quantitative comet comparison and its baseline supplies the retained movie.

Resource counters keep their recorded scopes. Cached API traffic, fresh tokens and tool-reported goal tokens have different meanings. Missing counters are unknown. The comparisons do not determine absolute X-ray brightness, monetary cost or solver performance on a common workload.
