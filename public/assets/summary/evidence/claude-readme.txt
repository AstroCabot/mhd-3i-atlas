# Solar wind at 3I/ATLAS during the XMM-Newton visit: 3D MHD with in-situ data assimilation

Agent: **claude** (Anthropic Claude Opus 5.5, `claude-opus-5-5`). This workspace is self-contained apart from the conda env `mhd_claude` (python 3.12, numpy, scipy, astropy, sunpy, numba, matplotlib, pandas) and nvcc 12.0 / g++ 13.3.

## Result

XMM window: frame-bound window 2025-12-03T12:04–12-04T10:12, accepted EPIC-pn GTIs 21.36 ks (Dec 3 13:04–Dec 4 09:56). Comet at r = 1.873 AU, solar latitude −6.45°, 25° east of STEREO-A.

| quantity at 3I/ATLAS | **1° reference** (best estimate) | **DA-design ensemble** (12 members, transferred onto the 1° reference): median [68%] (full range) | raw 4° ensemble median [68%] | CCMC ENLIL `Jan_Deca_120925_SH_1` | preprint ballistic (STEREO-A) |
|---|---|---|---|---|---|
| n_p, PN-GTI mean [cm⁻³] | **3.40** (window 0.92–11.9) | 3.4 [2.0, 4.6] (1.3–6.4) | 4.3 [2.7, 4.7] | 1.05 (ρ/m_p 1.26) | — |
| \|v\|, PN-GTI mean [km/s] | **478** (window 427–583) | 481 [408, 500] (403–540) | 470 [369, 490] | 407 | — |
| proton flux n\|v\|, PN-GTI mean [cm⁻² s⁻¹] | **1.59e8** (window 5.4e7–5.6e8) | 1.58e8 [0.86e8, 2.2e8] (0.52–3.1e8) | 1.9e8 [1.3e8, 2.2e8] | 4.3e7 | 8.3e7 (window median) |
| comet-frame flux n\|v−v_c\|, GTI mean | **1.45e8** | 1.45e8 [0.78e8, 2.0e8] | 1.75e8 | — | — |
| heavy-ion flux f·n\|v−v_c\|, f = (3–10)×10⁻⁴ | **8.7e4** at f = 6e-4; 4.4e4–1.45e5 over f | 2.3e4–2.0e5 (f range × 68% band) | — | — | prior N(1.0e5, 3.8e4) |

Frame-bound window medians are lower (1° reference: n 1.98, v 495, flux 9.9e7), because the SIR spike is narrow. The GTI-weighted values are the ones to use with the X-ray data. Ensemble members are transferred by applying each member's SIR timing offset (−7 h to +20 h) and amplitude ratio (0.76–1.22), both measured against the reference member at the same 4° resolution, to the 1° reference. This removes the 4° resolution timing bias (the 4° SIR arrives ~6 h late) while keeping the DA-design spread.

**Physical picture.**
- STEREO-A saw a weak shock (Nov 26.8, from the Nov 23 CMEs omitted by the CCMC cone list), dense slow wind and a stream interface at Nov 28.7, then a 650–780 km/s high-speed stream. It is 1.1° from the comet in latitude and its source band is ~1.8 d upstream in corotation, which makes it the decisive constraint.
- In the assimilated MHD, the slow wind ahead of that stream is compressed between 0.97 and 1.87 AU into an SIR. The SIR crosses the comet during the XMM visit: n rises to ≈ 8–14 cm⁻³ and the flux rises ×3–10 within the window (ensemble median ×3; 1° reference ×10).
- In the 1° reference the SIR density spike (n ≈ 12 cm⁻³, flux ≈ 5.6e8) crosses the comet at ≈ Dec 3.85, mid-window. The speed then rises 430 → 585 km/s by Dec 4.2.
- The arrival time is uncertain by about −7 h to +20 h across DA designs. That timing, not the amplitude, sets the spread in the GTI-weighted means.
- The preprint's ballistic-corotation remap cannot represent fast-overtakes-slow compression.
  - Applied to this model's *own* STEREO-A series at 2°, it gives a window median of 8.31e7, reproducing the preprint's 8.34e7 from the real data, while the MHD delivers 1.61e8 at the comet. Ratios to the MHD window median are 0.52 (STEREO-A-based), 0.37 (L1-based) and 0.53 (SolO-based) at 2°, and 0.6–0.9 at 1°.
  - Within the window the remap has no skill (r ≈ −0.4…0.4; rms 0.3 dex). It misses the SIR spike entirely.
- Speed is the most robust quantity: GTI means of 403–540 km/s across members, rising to ≈ 600+ km/s after the window.

**Implication for the preprint.**
- The GTI-weighted proton flux at the comet (1.6e8; 68% 0.9–2.2e8) is ≈ 1.9× the ballistic STEREO-A median and ≈ 3.7× ENLIL.
- The comet-frame flux is 9% lower than the heliocentric value, because 3I/ATLAS was receding at 43 km/s.
- With f = (3–10)×10⁻⁴, the heavy-ion flux is ≈ (2–20)×10⁴ cm⁻² s⁻¹ (central 8.7e4), consistent with the preprint's prior N(1.0e5, 3.8e4).
- The flux varies ×≈10 within the window in the reference (×≈3 in the ensemble median). Q ∝ Φ^−1/2 inversions should use the GTI-weighted value and carry the timing spread.
- **Caveat:** the modeled proton flux is *anti-correlated* with the EPIC-pn light curve (r ≈ −0.75 for the 1° and 2° references; `figs/lightcurve_vs_model.png`). The SIR spike falls in the X-ray minimum around Dec 3.8. Proton flux alone therefore does not explain the X-ray variability. Charge-state/composition changes (e.g. ICME material from the Nov 23 CMEs, which have no contemporaneous composition data) or SIR timing within the ensemble spread must matter. The light curve was not used to tune the model.

## Products

| file | content |
|---|---|
| `figs/timeseries_3i_atlas.png` / `.pdf` / `.csv` / `.json` | **Product 1.** Time vs density, speed, proton flux (heliocentric and comet-frame), heavy-ion flux at 3I/ATLAS, Nov 30–Dec 7. Transferred-ensemble bands, 1°/2°/4° references, CCMC ENLIL, preprint ballistic maps, XMM pointing and PN GTIs |
| `figs/timeseries_3i_atlas_raw4deg.*` | Same with the raw 4° ensemble bands |
| `figs/animation_flux_ecliptic.mp4` / `.gif` | **Product 2.** Top-down ecliptic-plane proton flux n·v from the 1° run, 0.1–2.49 AU, 3-hourly, Nov 20–Dec 8, with planets, spacecraft and the comet track |
| `figs/animation_flux_r2_ecliptic.mp4` | Same, colormap n v r² (structure contrast) |
| `figs/lightcurve_vs_model.png` | Model comet-frame flux vs EPIC-pn 0.2–1 keV light curve (context only; not used for tuning) |
| `bench/out_*` | Benchmark figures and JSON (below) |

## Remote-sensing and in-situ inputs (leading order first)

Full memo: `data/remote_sensing_memo.md`.
1. **Photospheric magnetograms → WSA speed at 21.5 R☉.** CCMC/iSWA WSA 5.4 maps from GONG zero-corrected (`mrzqs`) daily-updated synoptic maps (identical to the reviewer's ENLIL run). An independent in-house PFSS + SCS + WSA from GONG `mrzqs` reproduces them (speed r = 0.93, rms 49 km/s, polarity 99.75%). ADAPT-GONG: archived maps assimilated no data from Oct 8 to Nov 18 2025, so they are not used.
2. **In-situ plasma** (CDAWeb HAPI, hourly): STEREO-A PLASTIC, Wind/OMNI (OMNI = 100% Wind here), Solar Orbiter SWA-PAS, ACE SWEPAM K1 (preliminary; speed and timing only), MAVEN SWIA (validation only), PSP (no plasma in window). These are the same series as the preprint caches (verified to ≤1%). They enter by data assimilation.
3. **CMEs:** DONKI most-accurate cone analyses (121 cones, including the Nov 23 pair aimed within 7° of the comet). CCMC-list and no-CME variants are ensemble members.
4. Second order or unused: EUV coronal holes, IPS (ISEE; sparse in the comet sector), heliospheric imagers (CME kinematics only), HMI flux scaling. No contemporaneous heavy-ion composition exists (ACE SWICS ends 2025-03-16; SolO HIS L3 ends 2023-04), so f is a prior range.

## Model

**Frame and units.** Heliocentric inertial frame (HCI: solar equator, X at the ascending node). Boundary maps are in Carrington longitude, rotating at the fitted sidereal 14.18442°/day. ρ = n_p m_p(1+4x_α), p = n_p kT(2+3x_α), x_α = 0.05.

**Numerics** (`src/mhd/`):
- Spherical r–θ–φ finite volume carrying Cartesian momentum and B, so there are no geometric source terms.
- Analytic face vector-areas (Σ_faces S = 0 to 4e-8).
- Stencil states are rotated into the face basis before PLM (MC limiter); radial reconstruction acts on r²-scaled ρ, p, B.
- HLLD with an exact GLM (B_n, ψ) sub-solve. c_h is capped by the local Courant limit everywhere: 0.95 max(Σ(|v|+c_f)/Δx)/max(Σ1/Δx).
- Dual-energy entropy switch where e_th < 10⁻³ E.
- SSP-RK2, CFL 0.8 on the summed directional Courant number. float32.
- 2.7 ns per cell per RK2 step on the RTX 4080 SUPER, uncontended.

**Grid and boundaries.**
- r 0.1–2.5 AU, latitude ±60°, full longitude. Resolution levels: L0 128×30×90 (4°), L1 256×60×180 (2°), L2 512×120×360 (1°).
- Inner boundary super-sonic, with ghost B_φ = −B_r Ω r sinθ/v_r.
- Outer extrapolation B_r ∝ r⁻², B_t ∝ r⁻¹, ρ ∝ r⁻², p ∝ ρ^γ. This is required because GLM waves propagate upstream at c_h.
- Latitude edges copy spherical components.

**Boundary rule (prior).**
- Speed: WSA v clipped to [200, 700], v_r = v − (75 − 50(v−200)/500).
- Density and temperature: n v_r² = const (n_p = 250 cm⁻³ at 700 km/s), nT = const (1.5 MK at 700 km/s). These are interpolated as v, n v², nT (flux form), so momentum flux and pressure balance hold between map vertices.
- Field: B_r = 4×WSA B_r, which reproduces the observed |B| at 1 AU (6.4/7.3/7.9 nT vs 6.5/7.0/7.4 at L1/STA/SolO). The 0.1 AU boundary is then super-sonic but sub-Alfvénic (M_A ≈ 0.85), as near the real Alfvén surface. A 332 nT super-Alfvénic member is in the ensemble.
- +9° longitude shift (the ENLIL convention, measured from ENLIL's first cell).

**Passive tracers.** Source WSA speed, cos/sin of source Carrington longitude, source latitude, emission time. They give the exact MHD source point of every probe sample.

**Data assimilation** (`src/py/da.py`).
- Hourly residuals at STEREO-A, L1 and SolO over Nov 12–Dec 8 (speed, and log density) are mapped through the tracers to their source (lon, lat, emission time).
- Each daily boundary map gets its own correction: Gaussian kernels with σ_lon 4°, σ_lat 8°, emission-time window σ_t = 4 d, prior weight 3. The corrections are additive in speed and multiplicative in density (pressure balance kept).
- The model is rerun and iterated (6 times at 4°, then 3 more at 2° for the reference).

## Benchmarks

**Verification** (`bench/out_1d`, `bench/out_sphere`).
- Linear MHD waves (Stone+2008 state), float64 twin: L1 order 1.82–1.87 for fast, Alfvén, slow and entropy waves. Float32 reaches a 2e-3·amplitude floor.
- Sod: order 0.87 vs exact. Brio–Wu: order 0.87 vs an N=8192 self-reference, Bx exact.
- Free-stream preservation to 1.3e-4 after 278 steps (float32 rounding of the 6-face sum).
- Adiabatic Bernoulli wind with gravity: mass-flux drift 6.4e-3 → 8.4e-5 for Δφ = 22.5° → 2.8° (2nd order); v error 5e-4.
- Parker spiral: B_r r² flat to 0.15%; B_φ/B_r 1.7% below Parker (not resolution-converged; slow ∇·B drift). This is a known limitation of cell-centered GLM.

**Literature replication** (`bench/out_literature`).

| Pizzo (1978) 3D hydrodynamic stream, 1 AU | this code | published |
|---|---|---|
| slow-wind v / n / T | 401.0 / 6.8 / 78 kK | 401 / 7.1 / 80 kK |
| peak v / peak n / min n | 630 / 18.2 / 4.20 | 625 / 18.0 / 4.2 |
| u_φ range | +28 / −22 | +28 / −18 |

| Wiengarten+2014 / Pizzo (1982) MHD CIR, 1 AU | this code | published |
|---|---|---|
| \|B\|max / p_T,max | 15.05 nT / 161 pPa | 15 / 155 |
| n_max | 20.9 | 22.5–23.5 |
| fast plateau | 616 | 600–615 |
| E–W deflection | +10.7° / −6.7° | +10 / −7.5 |
| corotating field angle slow / fast | −50.0° / −38.5° | −50 / −36 |
| rarefaction n_min | 1.27 | 0.3–0.5 (stream half-width ambiguous in the paper) |

Both runs at 1°. Shocks are present at 1 AU, as published.

**Empirical trends** (`bench/out_empirical`, reference member vs Nov 12–Dec 8 data).

| | L1 | STEREO-A | SolO |
|---|---|---|---|
| log n vs log v slope, model / obs | −1.41 / −1.24 | −1.71 / −1.81 | −1.32 / −1.51 |
| log T vs log v slope, model / obs | 2.4 / 2.4 | 3.0 / 2.1 | 2.75 / 2.4 |

Proton T is ~3× too cold (γ = 5/3, no heating; γ = 1.5 member changes the comet flux by −4%). Radial trends from the 1° run (ecliptic plane, Nov 20–Dec 8): the n r² spread (p90/p10) grows ×1.56 from 1 to 2 AU and the speed standard deviation shrinks ×0.88. These are the classic stream-interaction compression and damping trends (cf. SIR peak-pressure growth and shock occurrence rising beyond 1 AU). T ∝ r^−1.17 (0.3–1 AU) and r^−1.69 (1–2.3 AU), against observed −0.6…−0.9, which is the adiabatic limitation.

**Calibration against the preprint's spacecraft data.** The assimilated reference reproduces the same STEREO-A, Wind and SolO series the preprint used.
- At 4°: speed RMSE 37/59/50 km/s, r = 0.91/0.90/0.93, density median ratio 0.95/1.08/0.88, log-n r ≈ 0.73.
- At 2° after refinement: 48/70/48 km/s.
- At 1° with the same corrections: 51/95/67 km/s. The STEREO-A fit, the comet-relevant one, is stable; L1 and SolO degrade because their corrections were tuned at 2°. Held-out (leave-one-out) speed-RMSE reductions with the 4D DA are +15% (STEREO-A), +24% (L1), +15% (SolO), comparable to BRaVDA's 18–31%. Static DA gives −8/+19/−12%, which is why the 4D variant is adopted. MAVEN at Mars (1.47 AU, never assimilated) is not improved (RMSE ≈ 125 km/s).

**OSSE** (twin experiments with the real observing geometry; `bench/out_da`). Comet GTI-flux error after DA is +14%, +0.2%, −9% for three random truths, against +53% when STEREO-A is withheld. The method recovers the comet site to ≈ 10% in the model world.

**CCMC ENLIL comparison** (`bench/out_ccmc`).
- My solver driven by the identical CCMC WSA maps, exact a6b1 rules, 9° shift, 332 nT field and 64 cones (4° grid) tracks ENLIL: speed r = 0.89 (Earth), 0.68 (STA), 0.62 (comet), mean bias +4–9 km/s once the thermal-pressure convention is matched (ENLIL effectively p = (ρ/m_p)kT), density ×0.62–0.83.
- Both have little skill against observations over Nov 15–Dec 8: ENLIL speed r = 0.06/0.08, RMSE 174/121 km/s, density ×0.53. The assimilated model reaches r = 0.90/0.91.
- At the comet in the frame window (medians): ENLIL 1.05 cm⁻³, 407 km/s, 4.3e7. Replica 0.82, 411, 3.4e7. Assimilated 1° reference 1.98, 495, 9.9e7 (GTI mean 3.40, 478, 1.59e8).
- Caveat: ENLIL's "N" is ρ/m_p (1.26 at the comet); the proton value is ρ/(1.2 m_p).

**Preprint ballistic method in the model world** (`bench/out_ballistic`). See Result. Ratio of ballistic to MHD comet flux is 0.37–0.53; within-window correlation ≈ 0; rms 0.22–0.32 dex.

## Convergence

| test | comet GTI-mean flux change |
|---|---|
| spatial, identical final boundary: 4° → 2° → 1° (GTI mean) | 1.64e8 → 1.55e8 → 1.59e8 (+3%, −2.5% vs 1°); n 3.74 → 3.42 → 3.40; v 433 → 458 → 478 |
| spatial, frame-window mean / SIR peak time | 2°→1°: +17% / spike ~3 h earlier at 1° (4°: ~6 h later); within the −7…+20 h DA spread |
| temporal, CFL 0.8 → 0.4 (4° / 2°) | −0.04% / +0.23% |
| latitude domain ±60° → ±45° / ±75° | +3% / −0.7% |
| start date Oct 25 → Nov 1 | −0.2% |
| γ 5/3 → 1.5 | −4% |
| CMEs: comet-directed → none / CCMC list | +13% / +13% |
| boundary B: 4×WSA → 332 nT (super-Alfvénic) | −10% (window mean) |
| coronal model: CCMC WSA → in-house PFSS/WSA | +20% |
| DA design (σ_t, density prior, spacecraft subsets, boundary source, CMEs, B, γ): 12 members | 68%: 0.54–1.40×; full range 0.33–1.96× (dominant) |

Every resolution, time-step, domain and physics change is smaller than the DA-design spread, which is driven by SIR timing. Further resolution or physics would therefore not materially change the estimate. Its accuracy is limited by how well the inner-heliosphere observations constrain the SIR geometry 25° east of STEREO-A at 1.87 AU.

## Limitations and deviations

- Hydrodynamic cone CMEs leave near-vacuum wakes behind the fastest clouds.
  - At 2°, floor activations are localized to inertial longitudes 303–309° and 11–13° (fast Nov 4–6 and Dec 7–8 cones), 230° from the comet (`floormap.bin`).
  - At 1°, the Nov 14 overlapping 1534/1082 km/s cones drove v_A ≈ 9000 km/s and collapsed dt. An Alfvén-speed limiter ρ ≥ B²/v_A,max² (v_A,max = 3000 km/s, velocity preserved) fixes this. It is bit-for-bit inactive at 4° and 2°. At 1° it acts in ~10⁻⁴ of cell-updates, in wakes; the comet's window values show no floor signature (n ≥ 0.92 cm⁻³).
- Cell-centered GLM: ∇·B is not zero to roundoff (mean h|∇·B|/|B| ≈ 1e-5 in smooth tests, ~1e-2 with current sheets). The Parker-spiral angle is ~2% low.
- Protons are too cold (γ = 5/3, no heating). No pickup ions and no composition evolution.
- f (heavy ions per proton) is not modeled; it is the preprint's prior range.
- MAVEN at Mars (120° from the comet) is not improved by assimilation.

## Reproduction

```bash
cd src/mhd && make                                   # helio, helio_trace, test1d, test1d_d
PY=~/miniconda3/envs/mhd_claude/bin/python
cd ../../bench && $PY test1d_suite.py && $PY test_sphere.py && $PY literature.py C && $PY literature.py A A_1deg
cd ../src/py && $PY run_da.py da3_ccmc_prod_t4 base=prod n_iter=6 sig_t=4      # reference DA at 4°
$PY production.py refine da3_ccmc_prod_t4 L1 3                                 # 3 more iterations at 2°
$PY production.py forward L2 1 da3_ccmc_prod_t4_L1ref                          # 1° run with ecliptic slices
./finalize.sh                                                                  # product charts, animations, benchmarks on the 1° reference
$PY product_timeseries.py ../../figs/timeseries_3i_atlas.png "1°_reference=prod_da3_ccmc_prod_t4_L1ref_L2" "transfer:da3_ccmc_prod_t4_it6>prod_da3_ccmc_prod_t4_L1ref_L2" <12 member runs>
```
Ensemble member configurations are in `runs/<tag>_config.json`, corrections in `runs/<tag>_corr.npz`, histories in `runs/<tag>_hist.json`.

## Compute record

From `monitor/status.json`, `monitor/log.tsv` and `monitor/gpu_accounting.json` (updated every 2 min by `monitor/monitor.py`):
- Wall time: ≈ 4.7 h from the first prompt to the final products.
- Solver: 204 runs, 2.97×10¹² cell-updates, 10.6 h of time-shared solver wall time on the shared RTX 4080 SUPER (≈ 2.2 GPU-hours exclusive-equivalent at 2.7 ns per cell-update). Peak device memory per run ≈ 3.8 GB (1°).
- CPU: ≈ 25 core-hours, mostly the single host thread per solver process.
- Host RAM: < 1 GB per process (systemd-run scopes capped at 3–6 GB).
- Tokens (this session plus 5 subagents, deduplicated by message id): ≈ 5.2 M fresh (input + cache writes + output, of which ≈ 0.54 M output) and ≈ 340 M cache reads.
