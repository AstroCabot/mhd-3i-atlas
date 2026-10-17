# Editorial audit of HELIOS

The interface needed a scientific editorial revision across all eight views. Its most conspicuous problems were advertising-style fragments, rhetorical headings, imperatives that added no information, and repeated generic cautions. Several phrases described the presentation's intentions instead of explaining the underlying calculation. The audit preserves uncertainty where it changes scientific interpretation and names the relevant source, assumption or measurement.

## Sources and editorial standard

[Wikipedia's community guide to signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) identifies promotional phrasing, inflated significance, generic commentary, repeated negative parallelism and formulaic disclaimers as recurring editing problems. The guide treats these as contextual observations and warns against relying on either detectors or intuition to establish authorship. This audit uses those observations to identify weak prose; it makes no claim to detect machine authorship.

The [Australian Government Style Manual](https://www.stylemanual.gov.au/writing-and-designing-content/clear-language-and-writing-style/plain-language-and-word-choice) recommends direct language, active constructions and familiar words, while allowing technical terms appropriate to the audience. For this research interface, terms such as constrained transport, GTI integration and charge state remain necessary. They should refer to a specific operation or physical quantity and be explained where the reader needs the distinction.

The user's [Henyey reference](https://oklo.github.io/Henyey/source.html) supplies the presentation direction. Scientific explanation, readable equations, precise chart labels and compact navigation should carry the hierarchy. Decorative slogans do not help a reader assess a numerical result.

## Changes by view

| Area | Original issue | Revision |
| --- | --- | --- |
| Shared shell | Observatory branding, reconstruction slogans and an unsupported reproducibility claim | Descriptive archive and comparison labels; direct destination links |
| Overview | “Three models. One interstellar visitor.” and a sequence of rhetorical insight cards | A target-and-quantity heading, physical interpretation and explicit calibration limits |
| Solar wind | “A moving heliosphere.” and “Match the display; retain the physics.” | A field-evolution heading and an explanation of sampling surfaces and flux definitions |
| Verification | “Trust begins with the equations.” and “Small changes are evidence, not an error bar.” | Numerical-verification and refinement labels with the actual scope of each test |
| Observations | “Anchor the model to the sky.” and a rhetorical holdout assertion | Spacecraft/coronal-constraint labels and the recorded held-out results |
| X-ray comparison | “The X-rays ask a harder question.” and an emission-model slogan | Exposure-matched variability, measured rates and the missing physical ingredients |
| Model physics | “Shared equations. Distinct choices.”, “excellent fit” and “actual” source labels | Named methods, selected configurations and explicit omissions |
| Resources | “Account for the work.” and contest/leaderboard language | Recorded accounting scopes and file checksums |
| Research record | “Read the record behind the result.” | Searchable session-archive description; original entries remain verbatim |

`public/data/editorial.json` records 85 exact substitutions for the original `src/app.js`. It includes 11 further proposed substitutions for explanatory strings in scientific metadata. Structural interface revisions may supersede some original substrings. The prose audit should therefore be checked against the rendered application as well as the replacement record.

The curated model guide received 38 source-level prose substitutions affecting 41 JSON string fields, including its generation timestamp. Its summaries now name the method, result and limitation directly. The shared-physics section uses descriptive topic headings. Calibration residuals, withheld measurements and finite refinement tests remain distinct because they constrain different sources of error. Repeated probability disclaimers were shortened while retaining the absence of calibrated coverage.

## Scientific qualifications retained

The fine Argon time series and baseline animation use different grids. Argon's movie is a solar-latitude cone; the other movies sample the ecliptic plane. Claude's animation provides radial flux, whereas the other two provide total-speed flux. The common projection cannot remove these differences.

The X-ray comparison uses the same accepted PN exposures and an observer-arrival clock. Normalizing the curves permits a variability comparison, but an emission calculation also requires ion abundances and charge states, neutral gas, charge-exchange yields and the detector response. The eight frames provide limited statistical information.

Spacecraft measurements used in fitting remain identified as calibration data. Model-specific holdouts use different configurations and intervals. The Observations copy also required a factual correction: Argon's report gives holdout speed RMSE 67.3 km s⁻¹, while its machine-readable summary gives 95.4305 km s⁻¹. Both values are now identified as a source discrepancy rather than endorsing the report value without qualification.

Resource totals retain their recorded scopes. Missing telemetry remains unknown. Concurrent wall times cannot be interpreted as exclusive GPU time, and provider token counters have different definitions.

## Verification performed

Every proposed interface substitution matched the original source exactly when the replacement record was written. The model JSON was rebuilt from the immutable research archive after changing only curated prose in its builder. A recursive before/after comparison confirmed that all numeric values, keys, array lengths and 27 source-file checksums were unchanged. Session transcript and shared-note contents were not edited.

An independent review of the revised source and rendered interface covered all eight routes and all three model-implementation tabs on the review server. The revised headings, chart notes, figure captions and table descriptions use descriptive scientific language. The overview values were checked against the common exposure-weighted data, and its descriptions of the declining Argon flux, narrow Claude peak and gradual Codex increase match the displayed series. Video requests were blocked during the copy extraction to separate the language review from media performance checks. No JavaScript errors occurred in that extraction. Animation playback and transitions require their own validation. Original transcript and shared-note language remains outside the editorial rewrite.

## Final source review

Seven further interface revisions clarified geometric UTC, identified the table speed as heliocentric solar-wind speed, removed an enhancement claim with no defined baseline, corrected the explanation of the emitting-ion fraction, shortened a duplicated benchmark caution and simplified two labels. The emitting-ion fraction in the displayed nₚf_q expression includes both elemental abundance and charge-state fraction.

The scientific-metadata builder received eleven explanatory-string substitutions. `scripts/apply_editorial_metadata.py` can apply the same exact substitutions to an existing generated document before packaging. Its preview changed thirteen string fields because one rule matches all three spacecraft qualifications. A recursive comparison confirmed that numeric values, keys, array lengths and scientific arrays remain unchanged.
