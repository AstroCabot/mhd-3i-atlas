# Independent interface review, 25 October 2026

Three independent reviewers examined visual design and responsive layout, functionality and accessibility, and playback efficiency and reliability. The baseline was the deployed commit `34311c4`. Reviews used the running application and source code, with separate staging for corrections.

The visual sweep covered all eleven sections in dark and manila themes at 320, 390, 768, 1280 and 1600 pixels: 110 layout states. Forty-four Firefox screenshots supplemented measured geometry. The review checked content inside clipped panels as well as overall page overflow. The application already retained a consistent technical-report presentation; corrections address specific defects within that design.

## Findings and corrections

| Finding | Correction |
| --- | --- |
| At 320 pixels, aspect-ratio sizing made maps wider than their panels. Hidden overflow cropped maps and controls despite page-level overflow checks passing. | Explicit canvas width and minimum width keep the complete map inside its panel. The source Method selector also flexes within its label. |
| Tracked-body names collided with one another, the Sun, and map overlays on small displays. | Labels use measured exclusion boxes, short leader lines and stable placement priorities. Small maps omit redundant static distance captions; orbital circles, actual marker positions, common scales and the distance guide below the maps are retained. Measurements are cached between resizes. |
| Closed mobile navigation remained keyboard-focusable; opening and closing the drawer could leave focus behind the overlay or on a hidden link. | Closed links are inert; the open drawer contains focus and isolates the background. Escape, backdrop dismissal, same-section links and breakpoint changes restore a useful focus position. Background scrolling is locked while open. |
| Source files exposed hundreds of line-number links as consecutive Tab stops. | One selected line link remains in the tab order. Arrow, Home and End keys select lines; Tab exits the source region. Mouse permalinks, searching and method jumps remain available. |
| A delayed unfiltered transcript request could overwrite newer filtered results. | Request generations guard both conversation and shared-note rendering, including errors arriving after navigation. |
| Failed shared-note requests raised an unhandled error; some archive sections retained their loading text after failure. | Conversations, notes, NASA comparison, source and report views offer recoverable Retry controls and clear completed loading states. |
| Shared notes offered dialogue filters that had no effect; following a note reference could leave Directed mode selected while showing a broader search. | Notes expose only their supported filters, normalize unsupported deep-link values, and reset filters consistently when following a reference. |
| Changing model visibility or design spread reset a chart's chosen time window. | Chart windows survive those updates without remounting playback. |
| A failed field or model request could leave the old image visible under the newly requested quantity or identity. A failed seek could show the requested UTC and planet positions over retained old pixels. | Displayed identity, units, UTC and markers commit with successfully promoted fields. The scrubber retains the requested target for retry while visible metadata continues to describe the retained image. |
| Fields continued fetching and decoding while readers were far below every map; paused players retained a 33 ms fallback timer. | Offscreen fields suspend playback and lookahead, preserving physical UTC and the user's play/pause choice. Returning to the fields resumes without skipping the hidden interval. Idle fallback clocks stop. |
| Long explanation columns made numerical values sit midway down tall mobile table rows. | Comparison cells align at the top, consistent with report tables. |

## Regression coverage

- `tests/usability.mjs`: native keyboard navigation, retry controls, adversarial archive responses, supported note filters, source navigation and retained chart windows.
- `tests/player-lifecycle.mjs`: offscreen suspension and resumption, manual pause, idle timers, failed field/model/epoch transitions and successful retries.
- `tests/responsive-layout.mjs`: all eleven views, both themes and five widths, including panel-level cropping checks.
- `tests/pages.mjs`: deployment under account-root and repository-prefixed URLs, with matching module and JSON versions.
- Existing browser, research and playback checks cover the surrounding interactions. Static packaging checks retain scientific frame and source checksums.

Chromium and Firefox passed the focused usability, playback-lifecycle and responsive checks. The consolidated compiled build passed the complete review suite, existing browser/research/interaction checks, both static-host prefixes, and eleven native scientific-integrity checks. Packaging verified all original frame hashes and required resources.

The cold-cache playback check at 6 Mbit/s and 250 ms latency retained the previous optimization's result: 60 animation requests during the measured ten-second window, continuous playback, and no sampled buffering. Paused and offscreen checks separately confirmed zero idle fallback clocks and no additional offscreen batch requests.

The review does not alter submitted reports, archived conversations, research inputs, simulation values, physical marker coordinates or animation samples. Browser evidence was collected with Chromium and Firefox; it is not a device-lab or Safari certification.
