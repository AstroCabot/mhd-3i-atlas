# Independent notebook and graphics review

Reviewed 17 October 2026 against the application source, rendered light and dark views, and [Henyey’s annotated program](https://oklo.github.io/Henyey/source.html). The reference HTML and CSS were read directly. This review concerns presentation and scientific comparability; it does not revalidate the MHD solvers.

The existing manila palette and two-column overview provide a useful basis. Their preservation is intentional: the user requested a saved version of this design, and commit `2396a71` was preserved separately before this refinement.

## Findings

1. **The remaining visual inconsistency comes from hierarchy.** Serif chapter titles coexist with a sans-serif application rail, an operational status strip, bordered chart cards, metadata badges and large record-count tiles. Each component is defensible on its own, but together they give a command-centre hierarchy to a document whose primary task is explanation. The useful features to borrow from Henyey are its consistent type system, numbered argument, restrained red, figure captions and marginal notes. They do not require imitation of a printed page or removal of interactive scientific controls.
2. **The overview mixes two kinds of comparison.** Numerical configuration and exposure-weighted physical estimates appear in the same model-row table. This makes it harder to scan one quantity across the three models and can imply that differences in native grids are directly comparable numerical resolution. The principal comparison should place models in stable columns and quantities in rows, using a common clock, accepted exposures and units. Solver settings and native surface differences need a separate, clearly scoped table.
3. **The archive is technically available but poorly signposted.** “Research record” gives little indication that it contains internal dialogue, recorded reasoning, tool activity and directed communications. Counts appear before meaningful entry choices. Explicit links to agent dialogues, shared notes and directed exchanges should be visible from the overview and at the start of the archive. Filters must describe exactly what is recorded; the application should not imply that unrecorded private reasoning is available.
4. **Equal colour scales do not establish equal physical sampling.** Argon uses a projected cone; Codex and Claude use ecliptic slices. Claude uses radial speed in its retained movie flux, while the other fields use total speed. These differences belong beside the comparison, together with exact saved-output cadence and interpolation method. A smooth display is not evidence of newly resolved physical evolution.
5. **Claude’s bright structures and black regions invite causal interpretation.** The CME prescription should be named for each model in one table, with evidence from selected runs. The black region in the current Claude slice is especially conspicuous: the interface should distinguish a source mask from a physically low flux before a reader interprets it as an eruptive cavity. Appearance alone cannot identify a CME. This requires a data/physics audit rather than a decorative change to the field colours.
6. **Model ordering must stay stable.** Argon, Codex and Claude should keep the same order in tables, legends and model selectors. Hiding and restoring a model must not silently move it to the end of the legend. Scales and comparison windows should remain explicit, rather than being normalised per model for visual similarity.

## Implemented presentation changes

- Preserved all dark and manila theme colour variables, the fixed contents rail, the paired overview figures and the existing route structure.
- Used Schola for the contents and running header, matching the chapter text; kept monospace for numerical quantities, machine records and short technical controls.
- Reduced competing panel borders to horizontal figure/table rules. Explanatory sections now share the page surface, while scientific figures retain a separate legible plotting surface.
- Subdued repeated heading actions, source download links and the running header. Interactive controls remain keyboard accessible and visible.
- Standardised caption leading, section spacing and comparison-table alignment. Bounded the article at 1440 px without widening its text measure.
- Added shared styles for reading links, explicit research-record entry points, a compact archive summary and a model-column comparison matrix. These support the parent agent’s structural changes without duplicating navigation logic.

The scientific heat-map field remains on a dark surface in both themes. This preserves the same field colour encoding and keeps the text overlays readable; the manila theme applies to the document and its comparison charts.

## Independent visual checks

Firefox rendered the source preview on 17 October 2026 using the real image player, with reduced motion set to pause playback. The following passed:

- Overview, solar wind, X-ray comparison, model physics, transcripts and resources in both light and dark at 1280 px.
- Overview, solar wind, model physics and transcripts at 1440, 1024, 768 and 390 px, with no horizontal overflow of the document. Tables and the narrow desktop triptych retain their own bounded scrolling where needed.
- No JavaScript errors were observed in those checks.
- All chart SVG text observed on the checked routes was at least 10 px.
- Schola was the computed font for both chapter headings and contents links.
- Main, muted, dim and model-label colours all exceeded a 4.5:1 contrast ratio against their corresponding panel background in both palettes (the lowest measured was 5.01:1). This is a limited palette check, not a full accessibility certification.

Screenshots and measured results are in `runtime/notebook-review/`; they are local review artifacts, not publication assets. These checks do not establish the scientific accuracy of a new temporal interpolation scheme or verify an eventual external deployment. Those require their own tests.

## Integrated navigation and comparison review

A second pass reviewed the parent agent’s integrated changes on the source preview:

- The overview now opens with explicit links to agent conversations, shared research notes and agent-to-agent exchanges. The contents uses the same clear “Agent conversations” label.
- The primary result table places the same three models in stable columns and common exposure-weighted quantities in rows. It includes a selected-run CME row, while the full forcing, grid and sampling comparison appears with the physics explanation.
- The archive presents three named reading views before its compact totals. Main-agent shortcuts and the recorded-reasoning filter are visible without inspecting the session hierarchy.
- The CME case-study deep link opens exactly four original notes, with the catalogue correction and provisional nature of contemporary claims explained above them.
- The movie panels state CME forcing directly in their footers. The adjacent text distinguishes stream compressions, injected hydrodynamic cones, low values below the colour floor and areas outside retained radial coverage. It also states why the plotted two-dimensional comet marker need not reproduce a three-dimensional moving-probe value.

This pass identified and corrected two CSS integration issues. Generic table styles imposed a 170 px minimum per prose cell and prevented first-column labels from wrapping; the comparison matrices now use defined column proportions and wrapping labels. Numeric result columns remain right aligned, while forcing prose is left aligned. The four archive shortcuts now form one desktop row and a compact two-column mobile arrangement; the mobile search input receives the full available line.

Firefox checked the overview, solar wind, model physics and session archive in both themes at 1280 and 390 px, plus the four-note CME link. Across these 17 views there were no JavaScript errors, page-width overflow or clipped matrix-cell contents. Results and screenshots are in `runtime/notebook-integration/`. This second pass checks the integrated hierarchy and responsive presentation; the interpolation algorithm and source-data classification are reviewed independently.
