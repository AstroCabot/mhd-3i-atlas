# Independent layout and typography audit

Reference inspected on 17 October 2026: [HENYEY, The program, annotated](https://oklo.github.io/Henyey/source.html), together with its [stylesheet](https://oklo.github.io/Henyey/site.css). The reference HTML and CSS were fetched directly because the web text parser could not access the page.

## Findings

The previous interface gave branding and summary cards more visual prominence than the scientific figures. A 222 px rail, 74 px header, 32 px page padding, oversized summary cells, and several repeated section gaps consumed much of a laptop display before the first data comparison. Its green accent, pill-like controls, glows, radial background and rounded panel collection suggested a general-purpose demonstration dashboard. Body copy and chart annotations were also too small: numerous labels were 7–9 px despite the generous spacing around them.

The reference uses TeX Gyre Schola, a Century Schoolbook-derived face, with monospace for code and data. Numbered sections, captions, thin rules and red reference marks establish a hierarchy without decorating every paragraph as a card. It also puts an annotated listing next to marginal notes; the notes explain concrete operations and references. These are the useful principles for a research interface. Its narrow single-column reading measure and large chapter spacing should not be adopted indiscriminately in a comparative workstation.

## Applied design

- The dark theme is retained with neutral warm charcoal surfaces, pale paper-like text, and muted red accents. Model colours are ochre, slate blue and red. Gradients and glows are removed from interface decoration; the scientific scalar colour scale is retained.
- TeX Gyre Schola is served locally for headings, scientific prose and captions. IBM Plex Mono remains the face for numeric tables, controls, provenance and transcripts. UI navigation retains a restrained sans-serif face.
- The contents rail is 184 px on large displays and 174 px on smaller desktop displays; the running header is 43 px. Main content uses 18–30 px horizontal margins. Navigation has compact numbered rows.
- Page titles are 26 px, prose is 13–14 px, main table values are 12 px, and ordinary interface labels are 11–12 px. Metadata is subordinate without being reduced to an unreadable texture. The JavaScript chart theme is adjusted separately because ECharts writes its SVG typography inline.
- Summary quantities share one ruled strip rather than four raised cards. Tables have stable numerical spacing and tabular figures. Primary panels have square corners, fine rules, compact headers and explanatory figure captions.
- Scientific figures remain large. The comparative figure layout uses two columns on wide desktop displays; lower-priority reading and marginal notes use compact columns. At narrower desktop widths, the three maps preserve a 260 px minimum and scroll together within their own container. Mobile displays stack the figures, preserve full plots and scroll wide data tables within their own boundaries. Full-screen map panels use the available viewport.
- Buttons, tabs, selectors, exports and mobile navigation keep their existing interactions and accessible focus states. Native video is fitted inside the scientific figure, with a persistent SVG annotation layer above it.
- Responsive styles preserve mathematical scrolling, transcript readability and a collapsible contents rail. Reduced-motion preferences remove interface transitions; animation playback remains an explicit control.

## Scope and attribution

The stylesheet is an original adaptation of the reference's hierarchy and typographic approach. No reference-site application code or scientific material was copied. TeX Gyre Schola is obtained from the [CTAN TeX Gyre distribution](https://ctan.org/pkg/tex-gyre) and its [GUST Font License](https://ctan.math.illinois.edu/fonts/tex-gyre/doc/GUST-FONT-LICENSE.txt) is included in `public/assets/fonts/GUST-FONT-LICENSE.txt`. Existing IBM Plex Mono and DM Sans licenses remain included.

This audit covers presentation. The separate scientific/editorial audit is responsible for scientific wording and the playback audit is responsible for native sampling, interpolation limits and smooth transport through time.

## Independent layout validation

All eight desktop routes were inspected in a browser with the final local typography and styles. Additional checks covered overview widths of 1280, 1024, 768 and 390 px, and the mobile equations view. All 13 viewport/route cases had zero horizontal document overflow; wide tables and equations retain their own internal scrolling. Every chart SVG label inspected on the eight desktop routes was at least 10 px. Local Schola font loading was confirmed.

The final compact header moves the first overview field from y = 363 px to y = 321 px at a 1440 px desktop width, with the 390 px high scientific map retained. Grid alignment also stops shorter scientific notes and model sidebars from expanding to the height of longer neighbouring text.

Visual checks used native observation-time poster frames through a browser-request-only playback stub while the separate playback audit investigated decoding. They establish layout and typography, not continuous video playback. The displayed marker-label collision near Earth was referred to the playback/overlay audit for offsets and leader lines that preserve all physical positions.
