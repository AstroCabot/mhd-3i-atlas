# Independent animation audit

The original display presented discrete image changes at about 1.33 frames per second. Its coarse temporal sampling and replacement of the image element on every update explain the stepwise motion and the possibility of a blank flash while the next image loads. The retained simulation archives support a substantially better presentation without rerunning any solver.

## Findings in the original implementation

- `scripts/build_science.py::animation_product` reduced every native field to a 128 × 128 Cartesian display raster and selected 32 exact six-hour timestamps. These pixels represent display interpolation, not native solver resolution.
- `src/app.js::tick` advanced one timestamp every 750 ms at the default playback setting. It did not interpolate between displayed frames.
- `drawSolar` assigned a new SVG `innerHTML` for each frame, recreating the `<image>`, grid, markers, and labels. Image resources were neither loaded as a complete sequence nor explicitly awaited before the previous image was removed.
- `scripts/render_frames.py` faithfully rendered the 128² extract. Changing its PNG export dimensions alone could not restore native spatial detail.
- The native archives do not all have the same temporal or spatial resolution. In particular, describing every native movie as having three-hour cadence would misstate the Codex archive.

## Retained spatial and temporal support

| Model | Solver grid (r × θ × φ) | Retained slice samples | Retained cadence | Field and surface |
|---|---|---|---|---|
| Argon | 160 × 32 × 180 | 160 radius × 180 longitude | approximately 3 h; actual timestamps retained | nₚ\|v\| on the solar-latitude −6.455° cone, projected into fixed-J2000 ecliptic x/y |
| Codex | 156 × 40 × 192 | 512 × 512 Cartesian raster interpolated from the CT state | approximately 6 h; actual timestamps retained | nₚ\|v\| in the fixed-J2000 ecliptic z = 0 plane |
| Claude | 512 × 120 × 360 | 320 radius × 360 longitude | exactly 3 h | nₚvᵣ in the fixed-J2000 ecliptic z = 0 plane |

Argon’s movie belongs to its baseline run. The 224 × 48 × 240 run remains the reference for the quantitative comet comparison; no high-resolution movie for that run was retained. Claude’s 512-cell radial solver grid must not be confused with its 320-cell radial movie sampling. Codex’s 512² raster is not a 512² independent solver grid.

## Replacement

`scripts/build_animation_v2.py` reads the immutable native binary and NPY archives directly. The default browser product contains 2,238 WebP images: 373 epochs for each of the six model/field combinations. Every field is rendered at 768 × 768 pixels on an exact 30-minute display-support clock. Two persistent image layers crossfade continuously at browser animation-frame cadence over a nominal 48 s playback interval. This provides 36 times as many display pixels as the original 128² extract and 12 times as many support epochs per physical day. Neither increase changes native physical resolution.

The same builder also supplies six downloadable H.264 videos at 768 × 768 pixels, 30 fps, and 48 s, containing 1,440 encoded frames each. All browser images and videos represent 2025-11-27 06:00 through 2025-12-05 00:00 geometric UTC, with identical projection, ±2.4 AU limits, and logarithmic colour scales.

Each 30-minute image support epoch and each encoded video frame is computed by bounded linear interpolation of **physical flux** between consecutive actual native epochs, followed by logarithmic colour mapping. Browser crossfades then blend the RGB colours of adjacent 30-minute images. This last step supplies visual continuity between closely spaced display images and is explicitly a display interpolation; it is not an additional native physical calculation. It is not optical-flow synthesis, interpolation of an already degraded 128² image, or a new simulation. The shared three-hour support clock in the manifest interpolates the approximately six-hour Codex archive. Additional display frames supply visual continuity, not additional native physical information. The interpolation can broaden a moving front between native epochs; sub-cadence shock evolution cannot be recovered from these archives.

Argon’s conical geometry is inverted analytically before sampling. Its r² transform uses the true three-dimensional conical radius. The Codex and Claude transforms use their ecliptic-plane radius. Bilinear spatial interpolation never extrapolates beyond the source support. A display pixel is masked when either time bracket lacks finite positive native coverage. The common colour map does not erase the different flux definitions or sampling surfaces.

The 2,238 portable images total exactly 42,525,668 bytes (40.6 MiB). The six videos total about 24.2 MB; the twelve JPEG posters add about 0.7 MB. All new animation products together require about 67 MB. The manifest records image and video dimensions, every frame timestamp and SHA-256 hash, playback clock, spatial support, source filenames, and SHA-256 receipts for 119 native inputs. Rebuild both products with:

```bash
python scripts/build_animation_v2.py
python scripts/build_animation_v2.py --images-only
```

`src/solar-player.js` maintains two persistent image layers and one persistent SVG overlay per panel. It preloads adjacent HTTP images into a bounded 48-frame cache, waits for load completion and valid native dimensions, then varies only opacity during playback. It avoids Blob URLs and explicit `Image.decode()` calls, both of which stalled the WSL headless test environment. At a support boundary, the former upper image becomes the lower image while the other layer accepts the next predecoded source. Loading or network delays freeze the physical clock while preserving a decoded image. Field and model changes wait for the incoming data at the same physical epoch. Overlay frames update only marker transforms and timestamp text; clustered spacecraft labels use fixed screen-space offsets and leader lines. The shared controls scrub continuously, pause, change playback rate, and preserve the epoch across model or field changes. Reduced-motion preferences pause initial playback. End-to-start looping restarts the finite interval; the physical model is not periodic.

The default player creates no video element and calls no native media API. This choice avoids an observed failure of the WSL headless browser’s platform-media initialization, reproduced independently with minimal H.264 and VP9 fixtures. The native MP4 files remain available for download without making their platform decoder a dependency of the dashboard.

## Verification

The builder checks all six encoded files with `ffprobe`: 768², 1,440 frames, 30 fps, 48 s. Physical interpolation is independently checked at the first, middle, and final frames; the maximum relative arithmetic error is below 10⁻⁷. It checks valid spatial masks and verifies each native source hash again after rendering. Those results are recorded in `public/data/animation-v2.json`.

The scientific regression suite is `tests/test_animation.py`. It checks all native receipts, source dimensions and cadence, all 2,238 WebP hashes and sizes, all six encoded video streams, and scattered decoded colours against independently resampled native physical fields. This last check jointly tests projection, physical epoch, logarithmic colour mapping, the r² transform, and north-up image orientation. Results are written to `tests/animation-science-results.txt`.

All six scientific regression checks passed. The browser regression test is `tests/solar-player.mjs`. It checks actual clock and opacity advancement, persistent image and SVG nodes during playback, decoded image dimensions, exact-epoch field/model changes, rate control, finite-interval looping, reduced motion, and cleanup. Its results are written to `tests/animation-results.txt`.

All nine browser behavior and lifecycle checks passed in matching Playwright Chromium 156 and Firefox 157. The measured 1.4 s playback sample advanced the physical clock by approximately 1.395 s of its 48 s display interval, with hundreds of image-attribute updates, zero SVG child replacements, and the same persistent image elements. Firefox captured the actual rendered fields successfully in `tests/screenshots/solar-player-v2.png`. Chromium’s headless screenshot compositor still timed out on this host, independently of its successful runtime checks.

When a remote browser suppresses animation-frame callbacks while its document is visible, a 33 ms timer advances the same clock only after the last animation callback is more than 80 ms old. Normal browser animation frames remain the primary clock. Pausing, loading, unmounting, or hiding the document cancels the animation callback; asynchronous manifest mounts accept an AbortSignal and do not create a stale player after route changes.
