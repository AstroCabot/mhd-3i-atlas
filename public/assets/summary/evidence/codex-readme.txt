3I/ATLAS solar-wind reconstruction — Codex

STATUS: final conditional reference ct156_w30_theta40_phi192 completed on a
156 x 40 x 192 grid (1,198,080 cells), 0.099985 to 2.3 AU, +/-30 degrees latitude.
All four selected directional pointwise and separate PN-exposure comparisons
pass their registered criteria, with source/physical/experiment checks. The
baseline timestep, domain, spinup and moderate outer controls pass in their
recorded geometries. Final charts, CSV, MP4/GIF animations and report have been
generated from this selection; the product workflow and artifact checks pass.

PN-GTI-weighted model estimates (photon-arrival UTC at the geometric Earth proxy):
  proton density                         2.6633164 cm^-3
  heliocentric bulk speed                485.08326 km/s
  comet-relative wind speed              446.40336 km/s
  incident proton flux n_p|v_SW-v_comet|  1.1931000e8 cm^-2 s^-1
  heliocentric proton flux n_p|v_SW|     1.2963264e8 cm^-2 s^-1

These are conditional model means, not plasma measurements at the comet.
Spacecraft residuals and substantial qualified input/closure sensitivities
prevent a strong empirical-accuracy or additional-physics-insensitivity claim.
There is no calibrated confidence interval. Distinct MOS/PN GTIs and the whole
published pointing have separate means in the report and results/summary.json.
The superseded GLM calculations remain at report_glm_history.html and
history/glm/archive_manifest.json; their fixed-method flags do not qualify CT.

The CT calculation uses pinned Athena++ native double-precision HLLD transport,
PLM reconstruction, SSPRK2, spherical geometry, gravity and staggered magnetic
CT. Our problem generator supplies the calibrated, rotating boundary, compatible
surface electric fields, physical ghost cells, probes and passive audits. Native
radial MeshBlocks/OpenMP provide CPU parallelism; CT does not use the GPU.
The pinned upstream is https://github.com/PrincetonUniversity/athena at commit
e47fabb7dd5efb22e1e2c7ff193148d723e3e952. Sources, own code, compiled binaries,
receipts and tests are retained under solver/athena_ct*, solver/athena_ct_pins/ and validation/.

Work from this directory with Python 3.12 and requirements.txt installed. GCC
with OpenMP and GNU time are needed for solver builds/run accounting; ffmpeg
is needed for MP4/GIF product rendering. Frozen archived CT executables allow
replay without a new Athena checkout, /tmp build tree or network access.
Six controls sharing the input-capability receipt (outer285, hotter,
density_high, fast, Bzero and frozenBr26) also verify the ROOT-local parent code
and pilot artifacts named by that receipt. Keep the copied workspace intact;
replaying the whole control campaign is not a claim that binaries and receipt
files alone replace all those retained inputs.
Acquisition from NASA, NSO, JPL and the other cited services is documented
separately; reproduction uses the copied inputs and evidence already present.

Reproduction:

    make plan

This prints a read-only plan from results/reference_selection.json and the
selected cases' actual run.cfg, native input, code selection, input/source
hashes and runner receipts. It invents no reference, case, settings or resource
caps. It refuses a missing CT selection, missing records, changed hashes, or
configuration disagreement. required_case_names, when explicitly present in
the selection, must include the reference, animation, every selected comparison,
envelope_cases and comparison_plot_cases. Otherwise their union supplies the
case names. Failed attempts remain evidence outside the required completed-run
set. An explicit empty envelope_cases prevents unrelated historical runs from
being drawn as a physical uncertainty band.

    make simulations

This explicitly executes the planned groups through the qualified archived-pin
controller. Matching completed cases are reused. To recompute the recorded
campaign, explicitly use:

    make simulations FORCE=--force

The controller archives prior outputs under each case's previous_attempts/
before recomputing. No other command silently adds --force. Per-case recorded
threads, radial blocks, resource caps, input capabilities and movie settings
are reused; incompatible cases form separate sequential groups. Each group
has at most two simultaneous jobs and eight reserved CPU threads. The shared
runner guard also enforces 3 GiB aggregate RSS, nice 15 and finite process-tree
wall/CPU/RSS/address-space limits. Actual caps and measured costs are in each
runner_usage.json and GNU-time resource_usage.txt; they vary by case.

    make all

make all and make products regenerate selected CT products through
scripts/render_products.py --gif. They require an explicit completed CT
reference and a completed selected CT animation case with recorded movie
output. A missing selection means a clear refusal, never a fallback to an
old GLM run. Products do not launch simulations, even with FORCE set. To
recompute and then render, run the two commands separately. make audit refreshes
the cached campaign diagnostics and registered convergence comparisons.
The original top-level GLM recipe is history/glm/Makefile.original; it is a
historical record and is outside the current default workflow.

Product locations:
  report.html                       scientific results, checks and limitations
  figures/comet_timeseries.png      density, bulk speed and incident-flux charts
  figures/solar_wind_topdown.mp4    accepted-state solar-system flux animation
  results/comet_timeseries.csv      selected clock, heliocentric/comet quantities
  results/reference_selection.json explicit case names and comparison choices
  validation/ct_selection_qualification.json immutable selection-time evidence
  validation/ct_final_replay_plan.json actual offline bounded replay commands

Inputs and physical interpretation:
  Day 0 is 2025-11-01T00:00:00 UTC (MJD 60980). Angular data and tracks share the
  recorded inertial solar-equatorial basis. WSA/GONG speed and magnetic maps,
  spacecraft calibration, Horizons ephemerides, accepted PN GTIs, CCMC models
  and coronagraph/cone provenance are copied with their primary-source links
  in inputs/, observations/ and external_model/. Dataset/source indexes include
  inputs/metadata.json, observations/evidence_report.txt and external_model/report.txt.
  The WSA archive is
  https://iswa.ccmc.gsfc.nasa.gov/iswa_data_tree/model/solar/WSA5.4/
  and the comparison run is
  https://ccmc.gsfc.nasa.gov/ror/results/viewrun.php?runnumber=Jan_Deca_120925_SH_1.
  The remote maps and coronal boundary closures are model inputs, not plasma measurements at the comet.

  Density denotes proton number density. Heliocentric flux is n_p|v_SW|;
  incident flux is n_p|v_SW-v_comet|. CT summary/selected comparison curves use
  observer-arrival UTC at the geometric Earth proxy, while the wind and comet
  velocity are evaluated at the same comet emission epoch. PN means integrate
  exact accepted exposure intervals and endpoints without extrapolation.
  Native spacecraft validation and movie frames retain physical geometric UTC.

  The hydrogen fluid uses p=2n_p k_B T_p (T_e=T_p); gamma and all calibration
  choices are recorded per case. Boundary, transient, speed, temperature, density and
  gamma controls are conditional sensitivities. Their envelope is not a
  confidence interval. Proton transport does not determine unmeasured heavy-ion
  abundance/charge states, the neutral coma, or an absolute X-ray brightness.

Scientific and resource evidence:
  validation/ct_convergence_plan.json       registered physical/numerical gates
  validation/ct_campaign_summary.json      completed/excluded cases, native CT,
                                          entropy, PN means and actual costs
  validation/ct_convergence_summary.json   registered comparison results
  validation/ct_input_native/             baseline input-control spacecraft
                                          residuals and qualification status
  validation/ct_thermomagnetic_selected/   selected-only native Tp and |B| checks
  validation/ct_campaign_audit_qualification.json  audit/cache/no-extrapolation gates
  external_model/athena_ct_parallel_validation/  native parallel/controller gates
  external_model/athena_ct_validation/controller_README.txt  low-level replay API
  monitoring/latest.json                  elapsed time and live resource samples
  monitoring/summary.json                 elapsed/completed-run CPU summary
  monitoring/token_snapshots.jsonl        tool-reported goal-token snapshots
  monitoring/ct_progress.json             current CT runner group progress

Monitoring counters have explicit limits: completed-run CPU sums omit some
experiments/interrupted work; concurrent wall times do not sum to elapsed time;
goal-token counts are tool-reported and are not a provider billing audit.
Timestamped collaboration notes, with individual authors, are in ../shared_notes/.
Legacy GLM convergence flags are namespaced in the current CT summary as
historical_GLM_convergence_flags; they do not certify the selected model.
No frozen historical source, hash receipt or directly linked archive file is
rewritten by this workflow. Final scientific values remain conditional on the
completed selection and its documented validation, rather than a default recipe.

Numerical evidence and remaining scientific limits:
  - Selected spatial comparisons are longitude144-to192 at the original
    baseline; latitude 32-to-40 at both 96 and 128 radial cells; and radial
    128-to-156 at 40 latitude cells. Every pair passes original 10/5/10 percent density,
    speed and incident-flux targets over the full pointing and the separately
    registered PN mean 2/1/2, frame 5/2/5, and integrated-difference 5/2/5 targets.
    The final radial pair changes PN means by 1.4602/.2695/1.1773 percent and
    maximum frame means by 3.5364/.4396/3.1865 percent. These are measured changes,
    not absolute error bars. Detailed definitions and source hashes are in
    validation/ct_convergence_plan.json and ct_convergence_summary.json.
  - Coarse 16-to-32 latitude refinement fails the pointwise density/flux and
    individual PN-frame criteria. Radial 96-to-128 at 32 latitude cells passes
    the original pointwise targets but fails separate PN mean/frame targets.
    Radial 96-to-128 at 40 latitude cells also fails the PN mean/frame targets;
    refining to 156 resolves the selected criteria without erasing that failure.
    A passing pair qualifies only the levels actually tested. The
    32-to-40 latitude ratio is only 1.25, so a small change is weak evidence of
    asymptotic convergence and is not an absolute fine-grid error bound.
  - Final-volume native CT flux incidence, positivity and the registered
    thermal diagnostic pass; no floor was activated. Minimum final temperature
    is 10813 K and minimum entropy-proxy/bound ratio is 1.05859. This is not a
    proven discrete entropy inequality or a temperature audit at every prior
    cell/time. Separate native traces and actual ghost/work checks are retained.
  - Domain, time-step, spinup, longitude and input controls are at their actual
    recorded baseline meshes. Their passes cannot establish every interaction
    of resolution, physical inputs and boundary geometry on the final mesh.
  - A 2.3-to-2.85 AU outer extension passes at unchanged radial spacing. Both
    3.125 AU attempts abort with negative pressure; the second uses half CFL.
    The moderate-extension pass never validates the failed larger domain.
  - Half-temperature and unretuned gamma=5/3 controls abort before the XMM
    window, as do their single half-CFL retries. No flux is extrapolated from
    those attempts and no thermal-insensitivity claim is made. Changing gamma
    also changes the prescribed initial adiabatic radial-temperature profile.
  - Low-density and slower-boundary controls finish, but fail the registered
    local boundary-energy-work criterion. Their raw curves are unqualified
    diagnostics and cannot supply physical uncertainty bounds. The low-density
    mismatch is 0.9399, not 0.9399 percent. Small integrated signed work can
    conceal cancellation and does not override this local failure.
  - Qualified hotter, denser and faster boundary controls change coarse PN
    incident-flux means by about +54%, +37% and +31%. These deliberately finite
    scenarios show substantial closure/input dependence; they are not a
    probability distribution, confidence interval or guarantee that omitted
    physics is negligible. Native spacecraft timing/amplitude residuals and
    differences from CCMC remain empirical accuracy limitations.
    In the selected post-calibration STEREO-A comparison, hourly proton-flux
    Pearson r is -0.0900 and median absolute fractional error is 45.0%; the
    fixed 600 km/s stream crossing is 32 hours late. CCMC ambient and CME PN
    incident-flux estimates are about 0.332 times the selected estimate.
  - Heavy-ion composition/charge states, coma density, mass loading and charge
    exchange are not independently reconstructed. The primary product is the
    upstream incident proton flux, not a unique X-ray brightness prediction.

Replay is offline in this recorded workspace. Actual configuration paths are
absolute and input hashes are checked. Moving the project to another location
requires explicit path rebasing and a new provenance record; silently altering
or repinning a frozen receipt is not supported.
