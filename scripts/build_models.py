#!/usr/bin/env python3
"""Build the curated model guide from the immutable research archive.

Only this application's public/data/models.json is written. Scientific prose is
curated against the final source code and receipts; resource numbers are read
from their recorded accounting scopes. This script never launches a solver.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


APP = Path(__file__).resolve().parents[1]


def section(title, body):
    return {"title": title, "body": body}


def equation(label, latex, explanation):
    return {"label": label, "latex": latex, "explanation": explanation}


def source(label, path=None, url=None):
    return {k: v for k, v in {"label": label, "path": path, "url": url}.items() if v}


def resource(label, value, unit, scope, path, status="recorded"):
    return {"label": label, "value": value, "unit": unit, "scope": scope,
            "source": path, "status": status}


def build(root):
    def read(path):
        return json.loads((root / path).read_text())

    argon = read("argon/outputs/summary_results.json")
    argon_monitor = read("argon/monitor_status.json")
    claude_monitor = read("claude/monitor/status.json")
    claude_gpu = read("claude/monitor/gpu_accounting.json")
    claude_reference = read("claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2.json")
    codex_monitor = read("codex/monitoring/summary.json")
    codex_summary = read("codex/results/summary.json")
    codex_reference = read("codex/results/ct156_w30_theta40_phi192/runner_usage.json")
    argon_fine = argon["mhd_runs"]["res_fine_224x48x240"]["meta"]
    argon_base = argon["mhd_runs"]["model3_assimilated"]["meta"]

    common_equations = [
        equation("Conservation of mass",
                 r"\frac{\partial\rho}{\partial t}+\nabla\!\cdot(\rho\mathbf v)=0",
                 "Plasma density changes as wind flows into or out of a volume. A steady radial wind with constant speed has density proportional to 1/r²."),
        equation("Momentum, magnetic pressure and solar gravity",
                 r"\frac{\partial(\rho\mathbf v)}{\partial t}+\nabla\!\cdot\left[\rho\mathbf v\mathbf v+\left(p+\frac{B^2}{2\mu_0}\right)\mathbf I-\frac{\mathbf B\mathbf B}{\mu_0}\right]=-\rho\frac{GM_\odot\mathbf r}{r^3}",
                 "Gas pressure and magnetic stresses accelerate or redirect the wind, while solar gravity decelerates it. Fast wind can catch slow wind and form a compressed stream interaction region."),
        equation("Total energy",
                 r"E=\frac{p}{\gamma-1}+\frac{\rho |\mathbf v|^2}{2}+\frac{B^2}{2\mu_0},\qquad\frac{\partial E}{\partial t}+\nabla\!\cdot\left[\left(E+p+\frac{B^2}{2\mu_0}\right)\mathbf v-\frac{(\mathbf v\!\cdot\!\mathbf B)\mathbf B}{\mu_0}\right]=-\rho GM_\odot\frac{\mathbf v\!\cdot\!\mathbf r}{r^3}",
                 "Internal, kinetic and magnetic energy evolve together. The adopted gamma controls expansion cooling; these gamma-law fluids do not resolve separate electron heating or heat conduction."),
        equation("Ideal magnetic induction",
                 r"\frac{\partial\mathbf B}{\partial t}=\nabla\!\times(\mathbf v\times\mathbf B),\qquad\nabla\!\cdot\mathbf B=0",
                 "The field is transported by the conducting plasma. Argon and Claude add a divergence-cleaning field; Codex uses staggered constrained transport to preserve discrete magnetic flux balance."),
        equation("Flux incident on the moving comet",
                 r"\Phi_{p,\mathrm{helio}}=n_p|\mathbf v_{\mathrm{SW}}|,\qquad\Phi_{p,\mathrm{incident}}=n_p|\mathbf v_{\mathrm{SW}}-\mathbf v_c|",
                 "Density in cm⁻³ and speed in km s⁻¹ require a factor 10⁵ to produce cm⁻² s⁻¹. The comet's outward radial motion reduces the incident speed; the full vector difference also includes its tangential motion."),
        equation("Exposure-weighted comparison",
                 r"\langle\Phi\rangle_{\mathrm{GTI}}=\frac{\sum_k\int_{t_{k,\mathrm{start}}}^{t_{k,\mathrm{stop}}}\Phi(t)\,dt}{\sum_k(t_{k,\mathrm{stop}}-t_{k,\mathrm{start}})}",
                 "Average over the detector's accepted good-time intervals, including exact endpoints. A continuous-window mean or median weights a transient differently and must be labeled separately."),
        equation("From upstream ions to charge-exchange X-rays",
                 r"I_X\ \propto\ \int n_{\mathrm{neutral}}\sum_q n_q\,v_{\mathrm{rel}}\,\sigma_q(v_{\mathrm{rel}})\,Y_q\,d\ell",
                 "X-ray brightness also requires the neutral coma, ion abundances and charge states, charge-exchange cross sections and yields, viewing geometry and instrumental response. Proton flux alone is an upstream driver, not an absolute X-ray prediction."),
    ]

    argon_resources = [
        resource("Project elapsed time", argon_monitor["runtime_seconds"] / 3600, "h",
                 "Elapsed first-prompt-to-monitor time; 2026-10-16 23:52:51 UTC snapshot.", "argon/monitor_status.json"),
        resource("Reference solver wall time", argon_fine["wall_time_s"], "s",
                 "Fine 224×48×240 run only; shared RTX 4080 SUPER.", "argon/outputs/runs/res_fine_224x48x240_run_meta.json"),
        resource("Baseline solver wall time", argon_base["wall_time_s"], "s",
                 "160×32×180 run supplying native movie slices and the original summary's spacecraft validation.", "argon/outputs/runs/model3_assimilated_run_meta.json"),
        resource("CPU core time", None, "core h", "No attributed project CPU integral in the final monitor.", "argon/monitor_status.json", "not recorded"),
        resource("GPU exclusive time", None, "h", "System GPU utilization samples are shared and do not establish agent-specific GPU time.", "argon/monitor_history.jsonl", "not recorded"),
        resource("Peak attributed host RAM", None, "MiB", "The monitor reports system RAM, not a per-process peak.", "argon/monitor_status.json", "not recorded"),
        resource("Peak attributed VRAM", None, "MiB", "The monitor reports total shared-device VRAM; no reference-run allocation receipt is present.", "argon/monitor_status.json", "not recorded"),
        resource("Input tokens", argon_monitor["tokens_consumed"]["project_total"]["input_tokens"], "tokens", "Monitor-derived session counter.", "argon/monitor_status.json"),
        resource("Output tokens", argon_monitor["tokens_consumed"]["project_total"]["output_tokens"], "tokens", "Monitor-derived session counter.", "argon/monitor_status.json"),
        resource("Cache-read tokens", argon_monitor["tokens_consumed"]["project_total"]["cache_read_tokens"], "tokens", "Repeated cached context reads are included; this is not fresh generation.", "argon/monitor_status.json"),
    ]

    claude_resources = [
        resource("Project elapsed time", claude_monitor["runtime_h"], "h", "First prompt to 2026-10-17 03:15:13 UTC monitor snapshot.", "claude/monitor/status.json"),
        resource("Reference solver wall time", claude_reference["wall_s"], "s", "1° 512×120×360 reference, including time sharing of the shared GPU.", "claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2.json"),
        resource("CPU core time", claude_monitor["cpu_core_h_claude"], "core h", "Accumulated attributed CPU estimate from the project monitor.", "claude/monitor/status.json"),
        resource("Sum of solver wall times", claude_gpu["solver_wall_hours_sum"], "h", "204 completed solver runs; concurrent/time-shared run durations, not elapsed time or exclusive GPU occupancy.", "claude/monitor/gpu_accounting.json"),
        resource("GPU exclusive-equivalent time", claude_gpu["cell_updates"] * 2.7e-9 / 3600, "h", "Derived from recorded cell-updates × 2.7 ns uncontended benchmark; estimate rather than an occupancy measurement.", "claude/README.md", "estimated"),
        resource("Reference GPU allocation", 3.83, "GB", "Solver-reported device allocation at run startup, not whole-device usage or a measured lifetime peak.", "claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2/stdout.txt"),
        resource("Peak attributed host RAM", None, "MiB", "The README gives <1 GB per process; the selected reference has no recorded peak measurement.", "claude/README.md", "not recorded"),
        resource("Fresh tokens", claude_monitor["tokens"]["fresh"], "tokens", "Input + cache writes + output; monitor deduplicates message IDs across tracked transcripts.", "claude/monitor/status.json"),
        resource("Output tokens", claude_monitor["tokens"]["output"], "tokens", "Part of the fresh-token total.", "claude/monitor/status.json"),
        resource("Cache-read tokens", claude_monitor["tokens"]["cache_read"], "tokens", "Cached context reads; not fresh generation or a cross-provider billing equivalent.", "claude/monitor/status.json"),
    ]

    codex_resources = [
        resource("Project elapsed time", codex_monitor["elapsed_project_seconds_at_last_sample"] / 3600, "h", "Monitor start to last sample at 2026-10-17 06:26:06 UTC.", "codex/monitoring/summary.json"),
        resource("Reference solver wall time", codex_reference["wall_seconds_including_inputs"], "s", "Selected CT reference, four CPU threads, CPU backend; includes input handling.", "codex/results/ct156_w30_theta40_phi192/runner_usage.json"),
        resource("Reference CPU core time", (codex_reference["user_seconds"] + codex_reference["system_seconds"]) / 3600, "core h", "GNU time user+system CPU for the selected native process.", "codex/results/ct156_w30_theta40_phi192/runner_usage.json"),
        resource("Recorded CT campaign CPU", codex_monitor["CT_CPU_seconds_including_recorded_failed_attempts"] / 3600, "core h", "Current-case receipts including recorded failed attempts; excludes archived attempts, builds, pilots, tests, and historical GLM.", "codex/monitoring/summary.json"),
        resource("Reference peak native RSS", codex_reference["maxrss_kb"] / 1024, "MiB", "GNU time native-process peak RSS. Process-tree sampled peak is a separate diagnostic.", "codex/results/ct156_w30_theta40_phi192/runner_usage.json"),
        resource("Reference GPU time", 0, "h", "Selected native CT backend is CPU-only. Earlier GLM development used CUDA; no all-project GPU total is claimed.", "codex/README.txt"),
        resource("Tool-reported goal tokens", codex_monitor["latest_tool_token_capture"]["reported_goal_usage"]["goal"]["tokensUsed"], "tokens", "Goal-counter snapshot at 2026-10-17 06:25:46 UTC; not a provider billing or fresh/cache token audit.", "codex/monitoring/summary.json"),
    ]

    models = [
        {
            "id": "argon", "name": "Argon", "subtitle": "Custom CUDA · HLL + GLM",
            "status": "Archived MHD reference",
            "summary": "Argon uses a spherical GPU MHD solver with a rotating WSA boundary and spacecraft-based speed and density corrections. The fine reference predicts a trailing compression during the first half of the XMM observation, followed by fast, rarefied wind. Archived animations use the coarser baseline run.",
            "selection": {
                "reference": "res_fine_224x48x240", "displayedSeries": "res_fine_224x48x240",
                "animation": "model3_assimilated",
                "description": "The comet and spacecraft comparisons use the fine 224×48×240 run. The archived animation uses the separate 160×32×180 baseline run.",
            },
            "nativePlane": {
                "kind": "constant solar latitude cone",
                "latitudeDeg": -6.455,
                "description": "The animation samples a constant heliographic latitude of approximately −6.455°, forming a cone through the comet's latitude. The display projects this conical surface onto the common ecliptic axes.",
                "source": "argon/src/heliomhd3d.cu",
            },
            "sourceNativeMeans": {
                "label": "Archived fine-reference PN-GTI summary",
                "densityCm3": argon["mhd_runs"]["res_fine_224x48x240"]["pn_gti"]["n_mean_cm3"],
                "speedKms": argon["mhd_runs"]["res_fine_224x48x240"]["pn_gti"]["vmag_mean_kms"],
                "heliocentricFluxCm2S": argon["mhd_runs"]["res_fine_224x48x240"]["pn_gti"]["flux_helio_mean_cm2s"],
                "incidentFluxCm2S": argon["mhd_runs"]["res_fine_224x48x240"]["pn_gti"]["flux_rel_mean_cm2s"],
                "timeConvention": "physical geometric UTC",
                "averagingNote": "Native summary averages the 10-minute samples falling inside accepted GTIs. It does not perform the application's exact GTI endpoint integration or photon-arrival relabeling. Use the separately computed common means for direct comparisons.",
                "source": "argon/outputs/summary_results.json",
            },
            "physics": [
                section("Magnetized flow and gravity", "Three-dimensional ideal MHD evolves mass, momentum, total energy and the magnetic field in a solar-equatorial inertial frame, with solar gravity and spherical curvature terms. Gamma = 1.5 is an effective thermodynamic closure. Magnetic pressure and tension moderate stream compression; the B = 0 control changes the baseline GTI incident flux by about +75%."),
                section("Composition carried as a tracer", "A passive heavy-ion fraction follows an empirical boundary speed rule and is advected with the fluid. The prescribed fraction ranges from roughly 7.5×10⁻⁴ in slow wind to 3.8×10⁻⁴ in fast wind. The calculation omits charge-state evolution, the neutral coma and charge-exchange emission."),
                section("Input hierarchy", "Model 1 uses an uncalibrated WSA/CCMC-scale density. Model 2 raises the density normalization using spacecraft momentum-flux estimates. Model 3 blends observed speed and density structure into the WSA map. A separate holdout excludes Wind and ACE while retaining STEREO-A and Solar Orbiter."),
            ],
            "equations": [
                equation("Divergence-cleaning extension", r"\partial_t\mathbf B=\nabla\times(\mathbf v\times\mathbf B)-\nabla\psi,\qquad\partial_t\psi+c_h^2\nabla\cdot\mathbf B=-\frac{\psi}{\tau}", "GLM transports and damps numerical magnetic divergence; it does not make the cell-centered field exactly solenoidal."),
                equation("Passive heavy-ion fraction", r"\partial_t(\rho f_{\mathrm{hi}})+\nabla\cdot(\rho f_{\mathrm{hi}}\mathbf v)=0,\qquad\Phi_{\mathrm{hi}}=f_{\mathrm{hi}}\Phi_{p,\mathrm{incident}}", "The inferred heavy-ion flux inherits the assumed boundary abundance and does not resolve individual ion charge states."),
                equation("Momentum-flux boundary closure", r"n_{p,0}=100\,n_{400}\left(\frac{400\ \mathrm{km\,s^{-1}}}{v_0}\right)^2,\qquad T_0=1.2\times10^6\left(\frac{v_0}{650\ \mathrm{km\,s^{-1}}}\right)^2\ \mathrm K", "For Model 3 at 0.1 AU, v₀ is the blended map speed minus 30 km s⁻¹, clipped to 220–720 km s⁻¹. Bᵣ is 3.5 times the averaged WSA field. These prescriptions are calibration choices."),
            ],
            "numerics": {
                "method": "Custom CUDA C++ finite-volume solver; float32; HLL flux with an exact (Bnormal, psi) GLM sub-solve; piecewise-linear MC-limited reconstruction; SSP-RK2. Exact spherical volume/face factors and explicit geometric/gravity sources.",
                "grid": "Fine: 224 × 48 × 240 = 2,580,480 cells; baseline/movie: 160 × 32 × 180 = 921,600 cells. The fine longitude spacing is 1.5° and latitude spacing is 2.5°.",
                "domain": "Uniform radial mesh, 0.10–2.40 AU; latitude ±60°; full periodic longitude.",
                "parameters": "Gamma 1.5; CFL 0.35; 10-day relaxation in the recorded suite. Fine weighted h|div B|/|B| diagnostic ≈ 0.00521, baseline ≈ 0.00744; these are native diagnostics, not directly comparable to CT flux-incidence residuals.",
                "boundary": "One rotating Carrington map is built by Gaussian-weighting 25 WSA maps in time. Spacecraft samples are ballistically back-projected into that map, with longitude/latitude kernels of 12°/7° and maximum blend 0.85. Inner Parker Bphi and radial extrapolation are imposed in ghost cells; the outer ghosts use density/Br ∝ r⁻² and transverse B ∝ r⁻¹.",
            },
            "calibration": {
                "body": "Model 3 assimilates STEREO-A, Wind, ACE and Solar Orbiter observations over the retrospective source interval. Residuals against those observations measure calibration performance. A separate holdout run excludes Wind and ACE from map construction to test transfer. The static map omits temporal changes within the source interval.",
                "validation": "Verification includes Brio–Wu shock tubes against a finer self-reference, spherical magnetized steady wind against an integrated ODE, and a rotating CIR experiment. Recorded controls vary the grid, CFL number, latitude extent, gravity, gamma, magnetic field and cone CMEs. Medium/fine GTI differences measure sensitivity to those two resolutions.",
                "limitations": "The report and machine-readable summary disagree on several spacecraft, window and light-curve numbers. The application uses archived numeric series/JSON for quantitative comparisons and preserves the discrepancy as provenance.",
            },
            "findings": [
                "Assimilated stream compression produces more comet-incident proton flux than the uncalibrated WSA/CCMC-scale control. Input calibration and stream phase matter more than the last spatial refinement.",
                "The trailing compression reaches the comet early in the observation in this implementation. That timing differs from Claude's narrow mid-window peak and Codex's smoother late increase.",
                "The B = 0, no-gravity and gamma controls demonstrate model dependence. Their differences do not prove a single physical cause or establish a calibrated confidence interval.",
            ],
            "caveats": [
                "The spacecraft calibration and holdout comparisons use different input datasets. Only the holdout excludes the tested spacecraft from assimilation.",
                "GLM leaves finite div B and the solver uses density/pressure floors; no complete floor-activation receipt accompanies the selected fine result.",
                "The reported estimate uses the fine grid; the archived animation uses the baseline grid. Latitude and longitude spacings differ, so a single angular-resolution label is incomplete.",
                "The movie samples a constant −6.455° solar-latitude cone. An ecliptic slice would require additional simulation output.",
                "A speed-dependent heavy-ion tracer cannot establish contemporaneous charge states or uniquely explain X-ray variability.",
                "The source report's X-ray interpretation exceeds the constraints from upstream proton flux. The application retains the measured frame uncertainties and integrates each model over the same accepted exposures.",
            ],
            "resources": {"rows": argon_resources},
            "sources": [
                source("Final research report", "argon/REPORT.md"),
                source("Native numerical summary", "argon/outputs/summary_results.json"),
                source("Solver source", "argon/src/heliomhd3d.cu"),
                source("Boundary construction", "argon/scripts/prepare_inputs.py"),
                source("Recorded run suite", "argon/scripts/run_mhd_suite.sh"),
                source("Final monitor", "argon/monitor_status.json"),
            ],
        },
        {
            "id": "claude", "name": "Claude", "subtitle": "Custom CUDA · HLLD + GLM · 4D assimilation",
            "status": "Archived MHD reference",
            "summary": "Claude uses a GPU MHD solver and passive source tracers to map spacecraft residuals back to daily coronal boundaries. Its 1° reference predicts a narrow compression peak during the XMM observation. A 12-member design ensemble varies arrival-time and calibration assumptions.",
            "selection": {
                "reference": "prod_da3_ccmc_prod_t4_L1ref_L2", "displayedSeries": "prod_da3_ccmc_prod_t4_L1ref_L2",
                "animation": "prod_da3_ccmc_prod_t4_L1ref_L2",
                "description": "The final forward run uses a 1° 512×120×360 grid with boundary corrections refined at 2°. The displayed band transfers relative timing and amplitude differences from twelve 4° ensemble members onto the 1° reference.",
            },
            "nativePlane": {
                "kind": "ecliptic plane",
                "description": "The producer samples a Cartesian ecliptic basis expressed in the solar-equatorial frame. This plane is distinct from Argon's constant solar-latitude cone and from the actual out-of-plane comet probe.",
                "source": "claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2/cfg.txt",
            },
            "sourceNativeMeans": {
                "label": "Archived 1° reference PN-GTI summary",
                "densityCm3": claude_reference["comet"]["n"]["gti_mean"],
                "speedKms": claude_reference["comet"]["v"]["gti_mean"],
                "heliocentricFluxCm2S": claude_reference["comet"]["flux"]["gti_mean"],
                "incidentFluxCm2S": claude_reference["comet"]["flux_rel"]["gti_mean"],
                "timeConvention": "physical geometric UTC",
                "averagingNote": "The native summary uses a GTI-midpoint approximation on geometric UTC. The application integrates the accepted intervals on the photon-arrival clock. This changes the mean most strongly near the narrow compression peak.",
                "source": "claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2.json",
            },
            "physics": [
                section("Ideal MHD and hydrogen–helium composition", "Solar gravity and ideal MHD evolve a gamma = 5/3 fluid without explicit solar-wind heating. A fixed alpha-to-proton number ratio of 0.05 gives mass density ρ = 1.2 mₚ nₚ and total thermal pressure p = 2.15 nₚ kBT. This density convention must be respected when comparing ENLIL mass-density products."),
                section("Evolving coronal and CME inputs", "Daily WSA maps prescribe the rotating coronal structure. The reference includes selected DONKI hydrodynamic cone transients. No-CME and CCMC-list variants test catalogue choice. Cone geometry can perturb stream timing, but the cones do not reconstruct a magnetic flux rope or measured ion charge states."),
                section("Source tracing and inverse correction", "Passive tracers carry source longitude, latitude, emission time and WSA speed. They connect each simulated spacecraft sample to its boundary source, allowing iterative speed/log-density residual corrections with Gaussian kernels in longitude, latitude and source time."),
            ],
            "equations": [
                equation("Hydrogen and helium fluid convention", r"\rho=m_pn_p(1+4x_\alpha),\qquad p=n_pk_BT(2+3x_\alpha),\qquad x_\alpha=0.05", "Proton number density is mass density divided by 1.2 mₚ; a plotted ρ/mₚ value would be 20% larger."),
                equation("Boundary residual assimilation", r"w_i\propto\exp\!\left[-\frac12\left(\frac{\Delta\phi_i^2}{\sigma_\phi^2}+\frac{\Delta\lambda_i^2}{\sigma_\lambda^2}+\frac{\Delta t_{\mathrm{src},i}^2}{\sigma_t^2}\right)\right],\quad\sigma_\phi=4^\circ,\ \sigma_\lambda=8^\circ,\ \sigma_t=4\ \mathrm d", "The reference uses a prior weight of 3 and repeats the forward-model/correction cycle six times at 4°, then three times at 2°. Speed corrections are additive and density corrections multiplicative."),
                equation("Assumed heavy-ion range", r"\Phi_{\mathrm{hi}}=f_{\mathrm{hi}}\Phi_{p,\mathrm{incident}},\qquad f_{\mathrm{hi}}\in[3,10]\times10^{-4}", "The heavy-ion fraction is an assumed abundance range. Ion composition is not evolved, and the range has no assigned probability coverage."),
            ],
            "numerics": {
                "method": "Custom CUDA finite volume on spherical cells carrying Cartesian momentum and B; analytic vector face areas; face-basis MC/PLM reconstruction; HLLD with exact GLM sub-solve; SSP-RK2; float32. A dual-energy entropy switch is used when thermal energy falls below 10⁻³ of total energy.",
                "grid": "1° reference: 512 × 120 × 360 = 22,118,400 cells. Refinement levels are 128×30×90 (4°), 256×60×180 (2°), and 512×120×360 (1°).",
                "domain": "Uniform radial mesh, 0.10–2.50 AU; latitude ±60°; full longitude. Native slice products extend to 2.49 AU.",
                "parameters": "Gamma 5/3; summed-direction CFL 0.8. An Alfvén-speed limiter at 3000 km s⁻¹ adds density in extreme cone wakes in the 1° run. It is reported inactive at 4°/2° and localized away from the comet sector at 1°.",
                "boundary": "WSA speed is clipped and reduced to account for outward acceleration; density is initialized with n v² constant and nT pressure balance. Bᵣ = 4×WSA. A +9° longitude shift follows the compared ENLIL convention. Outer ghosts use Br ∝ r⁻², transverse B ∝ r⁻¹ and adiabatic pressure scaling; latitude edges copy spherical components.",
            },
            "calibration": {
                "body": "Hourly STEREO-A, L1 and Solar Orbiter speed/log-density residuals over Nov 12–Dec 8 are assimilated retrospectively. The 1° forward run reuses the final 2° boundary corrections. Leave-one-out tests and synthetic observing-system experiments assess transfer beyond the assimilated measurements.",
                "validation": "Linear MHD waves, Sod, Brio–Wu, uniform-flow geometry, a Bernoulli/gravity wind and the Parker spiral test the equations and implementation. Pizzo and Wiengarten stream experiments provide separate literature comparisons. Leave-one-out speed improvements are reported at 4°; MAVEN at Mars is never assimilated and is not improved.",
                "limitations": "The 12-member design ensemble supplies 4° timing and amplitude differences that are transferred onto the 1° reference. Its parameter choices have no posterior probability weights. The boundary is not retuned at 1°, and L1/Solar Orbiter residuals increase on refinement.",
            },
            "findings": [
                "Stream interaction compresses slow wind ahead of a high-speed stream; a ballistic remap cannot reproduce that nonlinear density spike.",
                "The reference spike crosses around Dec 3.85, near the X-ray minimum. Its proton-flux curve is anti-correlated with the eight PN frames (native report r ≈ −0.75), so proton supply alone does not explain the X-ray variability.",
                "Arrival-time shifts of roughly −7 to +20 hours across assimilation designs dominate the exposure-weighted estimate. The transferred ensemble retains that timing spread after removing the coarse-grid timing bias.",
            ],
            "caveats": [
                "Gamma = 5/3 without explicit heating makes protons too cold relative to spacecraft measurements; no pickup ions or composition evolution are included.",
                "Cell-centered GLM leaves finite magnetic divergence and a known roughly 2% Parker-spiral angle error. This is distinct from Codex's CT incidence diagnostic.",
                "The finest run uses a density/Alfvén-speed limiter in extreme CME wakes. The reported inactive comet sector does not establish global conservation without qualification.",
                "The transferred 1° band measures sensitivity to the selected 4° assimilation designs. Probability coverage has not been calibrated.",
                "The wind was reconstructed without fitting the X-ray light curve. Heavy-ion charge states, neutral-coma evolution and stream timing remain unresolved contributors to the observed variability.",
            ],
            "resources": {"rows": claude_resources},
            "sources": [
                source("Final model and limitations", "claude/README.md"),
                source("Selected reference summary", "claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2.json"),
                source("Reference configuration", "claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2/cfg.txt"),
                source("Solver source", "claude/src/mhd/helio.cu"),
                source("Remote-sensing provenance", "claude/data/remote_sensing_memo.md"),
                source("Literature benchmark definitions", "claude/ref/literature_benchmarks.md"),
                source("Final monitor", "claude/monitor/status.json"),
                source("Completed solver accounting", "claude/monitor/gpu_accounting.json"),
                source("Wiengarten et al. MHD CIR benchmark", url="https://arxiv.org/abs/1406.0293"),
                source("Pizzo hydrodynamic stream benchmark", url="https://ntrs.nasa.gov/api/citations/19780020088/downloads/19780020088.pdf"),
            ],
        },
        {
            "id": "codex", "name": "Codex", "subtitle": "Athena++ CPU · HLLD + constrained transport",
            "status": "Archived CT reference",
            "summary": "Codex uses a double-precision Athena++ solver with staggered constrained transport, a calibrated rotating boundary and compatible edge electric fields. The selected reference passes the recorded numerical criteria. Spacecraft comparisons retain substantial timing and proton-flux residuals.",
            "selection": {
                "reference": "ct156_w30_theta40_phi192", "displayedSeries": "ct156_w30_theta40_phi192",
                "animation": "ct156_w30_theta40_phi192",
                "description": "The final reference is selected in results/reference_selection.json. The displayed curves, animation and numerical controls all use this CT implementation. Earlier GLM/Janhunen runs remain in the development archive.",
            },
            "nativePlane": {
                "kind": "ecliptic plane",
                "description": "The selected CT movie samples the geometric ecliptic plane using the archived ecliptic-to-solar matrix. Physical movie epochs remain geometric UTC; the selected comet comparison curve uses photon-arrival UTC.",
                "source": "codex/results/ct156_w30_theta40_phi192/run.cfg",
            },
            "sourceNativeMeans": {
                "label": "Archived selected CT PN-GTI summary",
                "densityCm3": codex_summary["cases"][codex_summary["reference_case"]]["PN_GTI_weighted_mean"]["n"],
                "speedKms": codex_summary["cases"][codex_summary["reference_case"]]["PN_GTI_weighted_mean"]["v"],
                "heliocentricFluxCm2S": codex_summary["cases"][codex_summary["reference_case"]]["PN_GTI_weighted_mean"]["f"],
                "incidentFluxCm2S": codex_summary["cases"][codex_summary["reference_case"]]["PN_GTI_weighted_mean"]["f_incident"],
                "timeConvention": "observer photon-arrival UTC at geometric Earth proxy",
                "averagingNote": "The selected CT summary already integrates exact accepted PN intervals with endpoints on the observer-arrival clock. It should agree with the application's common integration up to interpolation and numerical rounding.",
                "source": "codex/results/summary.json",
            },
            "physics": [
                section("Ideal MHD with effective thermodynamics", "The selected model evolves three-dimensional ideal compressible MHD with solar gravity, gamma = 1.5 and a pure-hydrogen equal-electron/proton-temperature closure p = 2nₚkBTₚ. The effective gamma describes adopted thermodynamics; separate electron/proton heating, conduction and kinetic plasma effects are not resolved."),
                section("A divergence-consistent magnetic boundary", "WSA/GONG maps supply changing radial-field targets at about 0.1 AU. A full-sphere monopole removal and consumer-grid area averages define the target; interval changes are fitted with compatible edge electric fields around a Parker base. Active face-normal magnetic flux evolves through native CT. This explicit boundary closure is qualified numerically, not shown to be physically unique."),
                section("Ambient reference and conditional controls", "The final reference is ambient-only. Separate 12/24-hour cone-CME variants, field-free, frozen-map, density, speed and temperature controls are sensitivities. Several colder/gamma controls abort or fail qualification, so they cannot define an uncertainty envelope or establish thermal insensitivity."),
            ],
            "equations": [
                equation("Staggered magnetic flux update", r"\frac{d\Phi_{B,f}}{dt}=-\sum_{e\in\partial f}s_{fe}\,\mathcal E_e\,\ell_e,\qquad(\nabla\cdot\mathbf B)_V=\frac{1}{V}\sum_{f\in\partial V}s_{Vf}\Phi_{B,f}", "A shared edge electric field makes neighboring face updates cancel around each volume. This is the discrete CT constraint; it does not determine whether the coronal forcing is empirically correct."),
                equation("Selected thermal and density closure", r"p=2n_pk_BT_p,\qquad n_{1\mathrm{AU}}=\frac{C}{v^2},\qquad T_0=Dv^2", "The selected boundary uses C = 1,320,464.187 cm⁻³(km s⁻¹)² and D = 5.985098 K/(km s⁻¹)². Calibration sets the instrument-balanced normalization, magnetic-field scale and speed adjustment."),
                equation("Photon-arrival comparison clock", r"t_{\mathrm{arrival}}=t_{\mathrm{emission}}+\frac{|\mathbf x_c(t_{\mathrm{emission}})-\mathbf x_\oplus(t_{\mathrm{arrival}})|}{c}", "The selected comet series evaluates wind and comet velocity at the same emission epoch, then labels it by photon arrival at a geometric Earth proxy. The median delay is about 938 s; spacecraft checks and movies retain physical geometric UTC."),
            ],
            "numerics": {
                "method": "Pinned Athena++ native double-precision HLLD transport, PLM reconstruction, SSP-RK2 and spherical finite volumes with staggered CT. The project adds boundary sampling/EMFs, physical ghost cells, probes and passive conservation audits. Four radial MeshBlocks and four OpenMP threads supply the final CPU parallelism.",
                "grid": "156 × 40 × 192 = 1,198,080 cells; longitude 1.875°, latitude 1.5°. Selected directional refinements are checked individually.",
                "domain": "Uniform radial mesh, 0.099985–2.30 AU; latitude ±30°; full longitude. The selected time interval is Nov 10–Dec 5, with earlier-start and wider-domain controls retained.",
                "parameters": "Gamma 1.5; CFL 0.25; order 2; four CPU threads. Selected final fields are finite and positive, no floor activation is recorded, and final-volume weighted h|div B|/|B| ≈ 1.7×10⁻¹⁴. This final-volume audit is not a temperature proof at every earlier stage/time.",
                "boundary": "WSA/GONG phase and map WCS share the inertial solar-pole basis with the probes. Instrument-balanced density/temperature normalizations and Br multiplier 2.357 set the nominal boundary; the tabulated speed includes a −50 km s⁻¹ correction. Compatible surface edge electric fields enforce the prescribed evolving Br target.",
            },
            "calibration": {
                "body": "STEREO-A and Solar Orbiter between Nov 10 and Nov 25 calibrate normalization. Wind/OMNI is excluded from that normalization fit. Later comparisons also influenced model-family choices, so they cannot be treated as a blind test of the eventual family.",
                "validation": "Local tests include uniform Cartesian field, radial adiabatic/gravity outflow, manufactured time-varying magnetic targets, map-knot behavior and strict floor-abort negative controls. Selected longitude, latitude and radial pairs pass pointwise and separate PN mean/frame/integral criteria. A linked 1D Brio–Wu literature plateau check uses PPM/SSPRK3, distinct from production PLM/SSPRK2.",
                "limitations": "Selected post-calibration STEREO-A proton-flux correlation is approximately −0.09 with median absolute fractional error 45%, and the fixed 600 km s⁻¹ crossing is 32 hours late. Passing numerical criteria cannot remove those timing/amplitude residuals or supply a calibrated comet prediction interval.",
            },
            "findings": [
                "The selected PN incident-flux estimate is about three times the compared CCMC ambient/CME estimate. Spacecraft timing and amplitude residuals remain large, limiting confidence in its accuracy at the comet.",
                "The selected proton-flux evolution is much smoother than the X-ray light curve: the native eight-frame incident-flux dynamic range is 1.45 versus an observed count-rate range of 7.87; native Pearson r ≈ 0.28.",
                "Qualified hotter, denser and faster boundary scenarios change coarse-grid PN incident-flux means by roughly +54%, +37% and +31%. This substantial closure dependence is separate from selected-grid numerical convergence.",
            ],
            "caveats": [
                "Earlier GLM/Janhunen curves, movies and fixed-method flags are superseded; they do not qualify the selected CT model.",
                "Half-temperature and unretuned gamma = 5/3 attempts, including half-CFL retries, abort before the observation. No XMM flux is extrapolated from them.",
                "Low-density and slower-boundary controls complete but fail the local boundary-energy-work criterion. Their raw curves are unqualified diagnostics.",
                "A 2.85 AU extension passes at matched spacing; two 3.125 AU attempts fail with negative pressure. The successful moderate extension does not validate the failed larger domain.",
                "The 32→40 latitude refinement is only a factor 1.25. Small finite differences are weaker evidence than an established asymptotic error bound; most controls are on coarser recorded meshes.",
                "The calculation omits contemporaneous heavy-ion composition, the coma, mass loading and charge-exchange emission. The scenario range measures sensitivity to the selected inputs; it has no calibrated probability coverage.",
            ],
            "resources": {"rows": codex_resources},
            "sources": [
                source("Final model guide", "codex/README.txt"),
                source("Final report", "codex/report.html"),
                source("Explicit final selection", "codex/results/reference_selection.json"),
                source("Selected run configuration", "codex/results/ct156_w30_theta40_phi192/run.cfg"),
                source("Reference resource receipt", "codex/results/ct156_w30_theta40_phi192/runner_usage.json"),
                source("Registered numerical comparisons", "codex/validation/ct_convergence_summary.json"),
                source("Light-curve comparison", "codex/validation/manuscript_benchmark.json"),
                source("Final accounting and limits", "codex/monitoring/summary.json"),
                source("Athena++ pinned upstream", url="https://github.com/PrincetonUniversity/athena/tree/e47fabb7dd5efb22e1e2c7ff193148d723e3e952"),
                source("Stone et al. Athena++ methods", url="https://arxiv.org/abs/2005.06651"),
                source("Miyoshi & Kusano HLLD method", url="https://www.sciencedirect.com/science/article/pii/S0021999105001142"),
                source("Dao & Nazarov Brio–Wu plateau comparison", url="https://arxiv.org/html/2206.09568v2#S4.T1"),
            ],
        },
    ]

    rows = [
        {"metric": "Project elapsed", "unit": "h", "argon": round(argon_monitor["runtime_seconds"] / 3600, 3), "claude": claude_monitor["runtime_h"], "codex": round(codex_monitor["elapsed_project_seconds_at_last_sample"] / 3600, 3), "scope": "Different project scopes; each value ends at its own final monitoring snapshot."},
        {"metric": "Reference solver wall", "unit": "s", "argon": argon_fine["wall_time_s"], "claude": round(claude_reference["wall_s"], 3), "codex": round(codex_reference["wall_seconds_including_inputs"], 3), "scope": "Fine selected runs only. GPU/CPU backends, grid sizes, step counts, forcing and contention differ; these values are not a performance ranking."},
        {"metric": "Reference cells", "unit": "cells", "argon": 224 * 48 * 240, "claude": 512 * 120 * 360, "codex": 156 * 40 * 192, "scope": "Spatial cell count alone does not describe numerical work or accuracy."},
        {"metric": "Reference backend", "unit": "", "argon": "CUDA GPU / float32", "claude": "CUDA GPU / float32", "codex": "4-thread CPU / float64", "scope": "Shared RTX 4080 SUPER for GPU runs; Codex final CT uses the CPU."},
        {"metric": "Attributed CPU", "unit": "core h", "argon": None, "claude": claude_monitor["cpu_core_h_claude"], "codex": round(codex_monitor["CT_CPU_seconds_including_recorded_failed_attempts"] / 3600, 3), "scope": "Claude monitor project estimate; Codex current CT receipt subtotal including failures, not all-project CPU. Argon unrecorded."},
        {"metric": "Reference peak host RSS", "unit": "MiB", "argon": None, "claude": None, "codex": round(codex_reference["maxrss_kb"] / 1024, 2), "scope": "Only Codex has a reference GNU-time peak receipt. Missing values are unknown, not zero."},
        {"metric": "Reference device allocation", "unit": "GB", "argon": None, "claude": 3.83, "codex": 0, "scope": "Claude startup allocation, not whole-device peak. Argon unrecorded. Zero means CPU-only for Codex final reference."},
        {"metric": "Fresh / uncached+output tokens", "unit": "tokens", "argon": argon_monitor["tokens_consumed"]["project_total"]["un_cached_plus_output_tokens"], "claude": claude_monitor["tokens"]["fresh"], "codex": None, "scope": "Argon input+output; Claude input+cache-write+output. Provider/accounting definitions differ; Codex goal counter does not separate fresh/cache."},
        {"metric": "Cache-read tokens", "unit": "tokens", "argon": argon_monitor["tokens_consumed"]["project_total"]["cache_read_tokens"], "claude": claude_monitor["tokens"]["cache_read"], "codex": None, "scope": "Repeated cached-context reads; not comparable to newly generated tokens or billable cost without provider rates."},
        {"metric": "Tool-reported goal tokens", "unit": "tokens", "argon": None, "claude": None, "codex": codex_monitor["latest_tool_token_capture"]["reported_goal_usage"]["goal"]["tokensUsed"], "scope": "Codex tool snapshot only; not a provider usage invoice and not the same definition as the other agents' transcript-derived counters."},
    ]

    document = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceRoot": "../mhd_llm (read-only)",
        "comparisonPolicy": [
            "Normalize physical units, plotting limits, UTC labels and exposure integration before comparing curves. Preserve each model's forcing, calibration history and native numerical definitions.",
            "The three reconstructions use different forcing, calibration histories and numerical configurations. Benchmark errors and runtimes must be interpreted within each recorded setup.",
            "Numerical verification tests the implementation; finite refinement tests numerical sensitivity; withheld spacecraft test empirical transfer. None directly measures plasma at the comet.",
            "Ensemble and physical-control ranges describe sensitivity to the selected scenarios; their probability coverage has not been calibrated. Missing resource telemetry is recorded as unknown.",
        ],
        "sharedPhysics": [
            section("Three-dimensional stream interaction", "Fast solar wind catches slower wind, forming a stream interaction region (SIR; a corotating interaction region when recurrent). Compression redistributes density, speed and magnetic pressure. Straight-line ballistic propagation cannot reproduce the nonlinear compression or the associated timing changes."),
            section("Modeled domain and variables", "All three implementations solve ideal, single-fluid solar-wind transport from about 0.1 AU to beyond the comet at roughly 1.87 AU. They differ in coronal-map handling, assimilation, thermal closure, magnetic-divergence control and resolution. They calculate the incident wind and omit the cometary plasma interaction."),
            section("Arrival time and accepted XMM exposure", "The EPIC-pn observation accepts 45 good-time intervals, totaling 21,362.284 s across eight frames. A narrow compression peak can fall in rejected time or a different frame after a shift of a few hours. The accepted-exposure mean, continuous-frame-window mean and whole-pointing mean are different quantities."),
        ],
        "commonEquations": common_equations,
        "observationalContext": [
            {"title": "Photospheric magnetograms → coronal maps", "body": "GONG synoptic magnetic maps feed WSA estimates of radial field and speed near 21.5 solar radii. These remote-sensing-derived boundary models do not directly measure wind at the comet; far-side history and coronal closure remain uncertainties.", "sourceUrls": ["https://gong.nso.edu/data/magmap/QR/zqs/", "https://iswa.gsfc.nasa.gov/iswa_data_tree/model/solar/WSA5.4/R21.5/"]},
            {"title": "Spacecraft plasma constraints", "body": "STEREO-A is especially relevant because its heliographic latitude is close to the comet's. Wind/OMNI and Solar Orbiter constrain other sampled sectors. Each model uses some of these measurements in calibration; an assimilated residual must be labeled separately from a withheld prediction.", "sourceUrls": ["https://cdaweb.gsfc.nasa.gov/hapi/"]},
            {"title": "Independent coronal-model checks", "body": "Claude compares an in-house PFSS/Schatten/WSA reconstruction with the archived WSA maps and audits magnetogram age. Its memo excludes stale archived ADAPT-GONG inputs and describes IPS/EUV/coronagraph information as secondary constraints. These checks test the forcing chain, not a direct density measurement at 1.87 AU.", "sourceUrls": ["https://gong.nso.edu/adapt/maps/gong/", "https://stsw1.isee.nagoya-u.ac.jp/ips_data-e.html"]},
            {"title": "CCMC reference and CME provenance", "body": "The comparison archive is Jan_Deca_120925_SH_1 (WSA 5.4 / ENLIL 2.8f). DONKI cone catalogues and the reference CCMC cone selection differ. The three implementations do not agree on the resulting transit/stream effects, so a small CME change in one calculation does not settle the event's physical importance.", "sourceUrls": ["https://ccmc.gsfc.nasa.gov/ror/results/viewrun.php?runnumber=Jan_Deca_120925_SH_1", "https://ccmc.gsfc.nasa.gov/DONKI/WS/get/CMEAnalysis"]},
            {"title": "Comet trajectory and observation clock", "body": "JPL Horizons ephemerides supply the comet's trajectory and velocity. Its outward motion reduces incident proton flux relative to heliocentric flux. Codex explicitly applies photon light time to its XMM comparison, whereas native movie and spacecraft epochs are geometric UTC; this clock distinction must remain visible.", "sourceUrls": ["https://ssd.jpl.nasa.gov/horizons/manual.html"]},
        ],
        "models": models,
        "resourceComparison": {
            "columns": [{"key": "metric", "label": "Recorded quantity"}, {"key": "argon", "label": "Argon"}, {"key": "claude", "label": "Claude"}, {"key": "codex", "label": "Codex"}, {"key": "unit", "label": "Unit"}, {"key": "scope", "label": "Scope / interpretation"}],
            "rows": rows,
            "notes": ["The recorded runtimes cover the original workloads, including hardware contention. A common workload was not executed for this application, so relative solver throughput cannot be inferred.", "Concurrent solver wall times must not be added to infer elapsed project time or exclusive GPU-hours.", "System-wide RAM, GPU utilization and VRAM samples include other concurrent work and cannot be attributed to a model.", "Token counters have different definitions and coverage. Cached context, fresh tokens and tool-reported goal tokens are displayed separately; no dollar-cost comparison is inferred."],
        },
        "sourceDiscrepancies": [
            {"model": "argon", "issue": "The report says the Wind holdout speed RMSE is 67.3 km s⁻¹ with r = 0.728; the machine-readable summary records 95.4305 km s⁻¹ with r = 0.691858. Several other native spacecraft/window numbers also differ.", "evidence": ["argon/REPORT.md", "argon/outputs/summary_results.json"], "policy": "Use source-series recomputation or labeled machine-readable metrics; do not silently repeat the prose as final numeric truth."},
            {"model": "argon", "issue": "The report describes dynamic WSA maps, a generalized-minmod limiter and Rusanov/HLL transport. The actual preparation code produces one time-weighted 2D rotating map, while the solver uses an MC limiter and HLL flux with a GLM sub-solve.", "evidence": ["argon/scripts/prepare_inputs.py", "argon/src/heliomhd3d.cu", "argon/REPORT.md"], "policy": "Describe the actual implementation, and keep the original report accessible as a historical artifact."},
            {"model": "argon", "issue": "The X-ray narrative states an early 4.28 ± 0.01 count s⁻¹ point and implies a sufficient explanation of emission. The archived frame record used by Codex gives 4.28868696 ± 0.03659342 count s⁻¹; proton flux alone cannot determine X-ray brightness.", "evidence": ["argon/REPORT.md", "codex/validation/manuscript_benchmark.json"], "policy": "Render the numeric observation record with its uncertainty and present model correspondence as a diagnostic, not a unique emission explanation."},
            {"model": "codex", "issue": "Custom GLM/Janhunen development artifacts coexist with the final Athena++ CT model. Their convergence flags and GPU usage describe a different formulation.", "evidence": ["codex/README.txt", "codex/results/reference_selection.json"], "policy": "Use the explicit selected CT case; retain older work only in its historical context."},
        ],
    }

    paths = {s["path"] for model in models for s in model["sources"] if "path" in s}
    paths.update(row["source"] for model in models for row in model["resources"]["rows"])
    paths.update(model["sourceNativeMeans"]["source"] for model in models)
    paths.update(p for issue in document["sourceDiscrepancies"] for p in issue["evidence"])
    document["provenance"] = []
    for path in sorted(paths):
        data = (root / path).read_bytes()
        document["provenance"].append({"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=APP.parent / "mhd_llm")
    parser.add_argument("--output", type=Path, default=APP / "public/data/models.json")
    args = parser.parse_args()
    document = build(args.source.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {args.output}: {len(document['models'])} models, {len(document['provenance'])} source receipts")


if __name__ == "__main__":
    main()
