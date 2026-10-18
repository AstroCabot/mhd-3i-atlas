# Independent animation audit

The first display presented discrete image changes at about 1.33 frames per second. Its coarse temporal sampling and replacement of the image element on every update explain the stepwise motion and the possibility of a blank flash while the next image loads. The second display retained its image layers and interpolated physical flux, but Claude's three-hour archive still separated narrow moving fronts by many display pixels. Colour continuity alone could not recover their intermediate evolution.

The current Claude movie therefore uses new **30-minute native solver outputs**, reproduced from the selected production setup in application-owned runtime storage. This is a sixfold improvement in physical output cadence, rather than additional blends between the same three-hour frames. Argon and Codex retain their original native archives. All three still share the same display clock, geometry, colour scales and controls; their different source support remains explicit.

## Findings in the original implementation

- `scripts/build_science.py::animation_product` reduced every native field to a 128 × 128 Cartesian display raster and selected 32 exact six-hour timestamps. These pixels represent display interpolation, not native solver resolution.
- `src/app.js::tick` advanced one timestamp every 750 ms at the default playback setting. It did not interpolate between displayed frames.
- `drawSolar` assigned a new SVG `innerHTML` for each frame, recreating the `<image>`, grid, markers, and labels. Image resources were neither loaded as a complete sequence nor explicitly awaited before the previous image was removed.
- `scripts/render_frames.py` faithfully rendered the 128² extract. Changing its PNG export dimensions alone could not restore native spatial detail.
- The native archives do not all have the same temporal or spatial resolution. In particular, describing every native movie as having three-hour cadence would misstate the Codex archive.

## Retained spatial and temporal support

| Model | Solver grid (r × θ × φ) | Slice samples | Current native output cadence | Field and surface |
|---|---|---|---|---|
| Argon | 160 × 32 × 180 | 160 radius × 180 longitude | approximately 3 h; actual timestamps retained | nₚ\|v\| on the solar-latitude −6.455° cone, projected into fixed-J2000 ecliptic x/y |
| Codex | 156 × 40 × 192 | 512 × 512 Cartesian raster interpolated from the CT state | approximately 6 h; actual timestamps retained | nₚ\|v\| in the fixed-J2000 ecliptic z = 0 plane |
| Claude | 512 × 120 × 360 | 320 radius × 360 longitude | 30 min verified re-output; original retained archive 3 h | nₚvᵣ in the fixed-J2000 ecliptic z = 0 plane |

Argon’s movie belongs to its baseline run. The 224 × 48 × 240 run remains the reference for the quantitative comet comparison; no high-resolution movie for that run was retained. Claude’s 512-cell radial solver grid must not be confused with its 320-cell radial movie sampling. Codex’s 512² raster is not a 512² independent solver grid.

## Claude temporal refinement

`scripts/refine_claude_movie.py` copies the selected Claude source, boundary data, tracks and CME list into a temporary Linux directory and compiles with the original Makefile flags. It adds only a host-side output hook: after each existing 1,800-second probe callback, the existing slice kernel reads the current state into a separate movie file. Every numerical kernel, timestep expression, original probe clock and original three-hour slice clock remains unchanged. The extra extraction does not advance or modify the MHD state.

Keeping the original clocks matters. Merely changing `slice_dt_s` from 10,800 to 1,800 seconds perturbs independently accumulated floating-point output times; small timestep differences then accumulate near sharp structures. An early trial detected this and was discarded. The output-only hook preserves the original trajectory instead. Its regression test compares all numerical-kernel source and the full timestep/update expression byte for byte.

The replay begins at the selected run's original 2025-11-12 start and stops at the common movie's 2025-12-05 endpoint. It retains 373 half-hour states for 2025-11-27 06:00 through 2025-12-05 00:00. All 63 coincident states reproduce the original five primitive-field arrays **bit for bit**; the builder enforces this gate before accepting the refined data. Timestamp bytes are checked separately: the largest difference is 18.6 ns, caused by stopping exactly at the movie endpoint. The 1,105 records from all 12 three-dimensional moving probes also preserve every primitive value bit for bit, with the same final timestamp qualification. `public/data/claude-temporal-refinement.json` records every coincident comparison, source hashes, GPU/compiler identity, effective configuration hash, output hook, generated archive and actual 2,067.41 s solver runtime. All files under `../mhd_llm` remain unchanged.

The finer cadence supplies actual intermediate solutions, including moving fronts; it does not increase the solver's spatial resolution or replace its calibrated boundary conditions. Quantitative comet/probe results remain the original selected research products. Reproducing the finer movie requires the original CUDA sources and inputs, nvcc and a suitable NVIDIA GPU. Packaging or serving the committed web application does not require them.

Claude's selected production run includes catalogued hydrodynamic CME cones; selected Argon and Codex runs model ambient wind without those injections. The visual differences therefore have physical as well as numerical causes. An individual bright front cannot be attributed to a particular CME by appearance alone. The app's physics comparison lists the actual injected event catalogues and model assumptions.

Near-black regions inside Claude's valid radial domain can be physical low-flux regions. At 2025-12-03 18:00, every retained density and radial-speed sample is finite and positive, but 5.67% of native polar cells have nₚvᵣ below the shared 10⁷ cm⁻² s⁻¹ colour floor. The minimum is about 1.13 × 10⁶ cm⁻² s⁻¹. Such values saturate at the darkest Inferno colour. They are different from unsupported pixels beyond the saved radial domain, which use the fixed dark-grey background. Colour bars mark their clipped endpoints explicitly; the r² view applies its own stated limits.

## Replacement

`scripts/build_animation_v2.py` reads the immutable native binary and NPY archives directly. The default browser product contains 2,238 WebP images: 373 epochs for each of the six model/field combinations. Every field is rendered at 768 × 768 pixels on an exact 30-minute display-support clock. Two persistent image layers crossfade continuously at browser animation-frame cadence over a nominal 48 s playback interval. This provides 36 times as many display pixels as the original 128² extract and 12 times as many support epochs per physical day. Neither increase changes native physical resolution.

The same builder also supplies six downloadable H.264 videos at 768 × 768 pixels, 30 fps, and 48 s, containing 1,440 encoded frames each. All browser images and videos represent 2025-11-27 06:00 through 2025-12-05 00:00 geometric UTC, with identical projection, ±2.4 AU limits, and logarithmic colour scales.

Claude's 30-minute image-support epochs use actual solver outputs from the verified replay. Argon and Codex's support epochs use bounded linear interpolation of **physical flux** between consecutive actual native epochs, followed by logarithmic colour mapping. All encoded video frames use the same physical interpolation within their respective native support. Browser crossfades then blend the RGB colours of adjacent 30-minute images. This last step supplies visual continuity between closely spaced images and is explicitly a display interpolation; it is not an additional physical calculation. No optical-flow synthesis is used. The shared three-hour track clock in the manifest describes overlay ephemerides, not field cadence. Interpolation can still broaden a moving front within each model's native interval; it cannot recover sub-cadence shock evolution.

Argon’s conical geometry is inverted analytically before sampling. Its r² transform uses the true three-dimensional conical radius. The Codex and Claude transforms use their ecliptic-plane radius. Bilinear spatial interpolation never extrapolates beyond the source support. A display pixel is masked when either time bracket lacks finite positive native coverage. The common colour map does not erase the different flux definitions or sampling surfaces.

The 2,238 WebP images total 43,483,894 bytes; Claude's 746 images account for 20,872,006 bytes. The six MP4 exports total 22,286,262 bytes. The manifest records image and video dimensions, byte sizes, every frame timestamp and SHA-256 hash, playback clock, spatial support, source filenames, and SHA-256 receipts for 119 original native inputs. Claude's separate temporal-refinement receipt covers the output-only replay. Its movie and image paths include `native30m` so cached older three-hour products cannot conceal the change. Reproduce the refined archive, then rebuild both display products with:

```bash
python scripts/refine_claude_movie.py
python scripts/build_animation_v2.py --with-images
```

`src/solar-player.js` maintains two persistent image layers and one persistent SVG overlay per panel. It preloads adjacent HTTP images into a bounded 48-frame cache, waits for load completion and valid native dimensions, then varies only opacity during playback. It avoids Blob URLs and explicit `Image.decode()` calls, both of which stalled the WSL headless test environment. At a support boundary, the former upper image becomes the lower image while the other layer accepts the next predecoded source. Loading or network delays freeze the physical clock while preserving a decoded image. Field and model changes wait for the incoming data at the same physical epoch. Overlay frames update only marker transforms and timestamp text; clustered spacecraft labels use fixed screen-space offsets and leader lines. The shared controls scrub continuously, pause, change playback rate, and preserve the epoch across model or field changes. Reduced-motion preferences pause initial playback. End-to-start looping restarts the finite interval; the physical model is not periodic.

The default player creates no video element and calls no native media API. This choice avoids an observed failure of the WSL headless browser’s platform-media initialization, reproduced independently with minimal H.264 and VP9 fixtures. The native MP4 files remain available for download without making their platform decoder a dependency of the dashboard.

## Verification

The builder checks all six encoded files with `ffprobe`: 768², 1,440 frames, 30 fps, 48 s. Physical interpolation is independently checked at the first, middle, and final frames; the maximum relative arithmetic error is below 10⁻⁷. It checks valid spatial masks and verifies each native source hash again after rendering. Those results are recorded in `public/data/animation-v2.json`.

The scientific regression suite is `tests/test_animation.py`. It checks all native receipts, source dimensions and cadence, all 2,238 WebP hashes and sizes, all six encoded video streams, and scattered decoded colours against independently resampled native physical fields. This last check jointly tests projection, physical epoch, logarithmic colour mapping, the r² transform, and north-up image orientation. Results are written to `tests/animation-science-results.txt`.

The six native-media regression checks and five temporal-refinement checks passed. The latter independently check the unchanged numerical source, half-hour native clock, all coincident primitive arrays, moving probes and the fact that intermediate native states differ from three-hour Eulerian blends. Results are recorded in `tests/animation-science-results.txt` and `tests/refinement-results.txt`. The browser regression test is `tests/solar-player.mjs`. It checks actual clock and opacity advancement, persistent image and SVG nodes during playback, decoded image dimensions, exact-epoch field/model changes, rate control, finite-interval looping, reduced motion, and cleanup. Its results are written to `tests/animation-results.txt`.

All nine browser behavior and lifecycle checks passed in matching Playwright Chromium 156 and Firefox 157. The measured 1.4 s playback sample advanced the physical clock by approximately 1.395 s of its 48 s display interval, with hundreds of image-attribute updates, zero SVG child replacements, and the same persistent image elements. Firefox captured the actual rendered fields successfully in `tests/screenshots/solar-player-v2.png`. Chromium’s headless screenshot compositor still timed out on this host, independently of its successful runtime checks.

When a remote browser suppresses animation-frame callbacks while its document is visible, a 33 ms timer advances the same clock only after the last animation callback is more than 80 ms old. Normal browser animation frames remain the primary clock. Pausing, loading, unmounting, or hiding the document cancels the animation callback; asynchronous manifest mounts accept an AbortSignal and do not create a stale player after route changes.

## Playback interaction revision, 18 October 2026

The shared controls use fixed grid positions for the slider, timestamp and playback rate, with status text on its own row. Changing between playing, paused, seeking and loading cannot change the slider's position or width. The slider updates on each animation frame; timestamp text remains throttled separately.

Rapid scrub inputs are combined over 40 ms before starting frame downloads. Each new seek cancels obsolete pending image requests and invalidates the previous image transition. Only completed images enter the shared 48-frame cache; pending downloads belong to the mounted player and are cancelled when it is destroyed. Current requests cannot lose their cache entries to a late completion from an older request. Across all three panels, a decoded layer remains visible while replacement layers load, and the final epoch follows the most recent seek and pause/play intent.

Ordinary cached interval changes show a loading message only after a 180 ms wait, avoiding short status flashes. Upcoming frames are prefetched in epoch order across models. Failed downloads can be retried with the play button.

`tests/solar-interactions.mjs` exercises the real application through a controlled HTTP proxy. It checks slider geometry at 1280, 1024, 768 and 390 pixels, obsolete ten-second downloads, rapid scrubbing, pause during loading, preservation of visible decoded fields, retry after an HTTP failure, and overlapping field/epoch changes. These interaction checks and the nine existing player checks passed in Chromium and Firefox.
