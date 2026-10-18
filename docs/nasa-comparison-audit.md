# NASA comparison: extraction and interpretation

The comparison uses the archived CCMC run [Jan_Deca_120925_SH_1](https://ccmc.gsfc.nasa.gov/ror/results/viewrun.php?runnumber=Jan_Deca_120925_SH_1), WSA 5.4 / ENLIL 2.8f. Its recorded grid is 576 radial × 24 latitude × 90 longitude cells, spanning 0.1–3.1 AU and ±48° latitude. Time-dependent GONGZ/WSA input and a 64-entry cone catalogue cover the full 1 October–9 December 2025 run. The catalogue count does not imply that 64 eruptions encounter the comet during the XMM observation. Metadata checked 18 October 2026.

`scripts/build_reference_comparison.py` reads the immutable native archive and the selected application data. It does not run a solver. The resulting `public/data/nasa-comparison.json` includes original-source paths, byte counts and SHA-256 receipts.

## Density correction

The high-precision exports in `claude/ref/ccmc/timeseries/enlil_*.csv` label the archive's mass density divided by proton mass as `n_cm3`. With the archived alpha-to-proton number ratio of 0.05, the conversion is:

```text
N = rho / mp = np + 4*nalpha = 1.2*np
np = N / 1.2
speed = sqrt(vr**2 + vlon**2 + vlat**2)
proton_flux = np * speed_kms * 1e5
```

Apply the factor once. Argon's lower-precision `ccmc_extracted.npz` came from a different, already converted product. Dividing its density by 1.2 a second time made the previous NASA overlay too low. For example, the native CSV at geometric MJD 61013 gives N = 1.268947 cm⁻³, or np = 1.057456 cm⁻³; the rounded NPZ already reports about 1.06 cm⁻³.

The corrected overlay now uses the higher-precision native CSV. `scripts/build_science.py` uses the same extraction for future rebuilds. This correction changes the NASA overlay only; the selected Argon, Codex and Claude reconstructions, their spacecraft metrics, and the X-ray results remain intact.

## Spacecraft comparison

The archived trajectories are STEREO-A, Earth and Solar Orbiter. Earth is a near-Earth proxy for Wind, rather than Wind's exact trajectory. Native ENLIL values are interpolated to the existing hourly spacecraft timestamps. For each quantity, one positive finite mask includes the observation and all four models. Speed RMSE, signed bias, Pearson correlation and density/flux median ratios are recomputed on those masks.

The reconstructions used spacecraft information in calibration, with different fitting and holdout policies. The NASA reference is remotely driven. Residuals on common timestamps permit a quantitative comparison, but do not establish independent forecast skill or determine the unmeasured plasma at the comet. Each model's calibration and validation scope remains documented in Model physics and the submitted writeups.

## Comet comparison and CME control

All four curves and the exposure table compare **heliocentric** proton flux np|v|. The X-ray section uses **comet-relative incident** flux np|v − vcomet|; these are different quantities. Both are in cm⁻² s⁻¹ before the displayed scaling by 10⁸.

Tabulated density, speed and flux means come from the native piecewise-linear series integrated over the same accepted EPIC-pn good-time intervals. Geometric emission times are converted to photon-arrival times using the comet–Earth distance; Codex's already supplied arrival times are retained. Display interpolation does not determine the tabulated means.

The high-precision comet CME and ambient blocks give mean heliocentric fluxes of approximately 4.37984×10⁷ and 4.37534×10⁷ cm⁻² s⁻¹, a difference of 0.103%. This result applies to the archived input catalogue, comet geometry and these exposure intervals. Missing or uncertain eruptions and a different observation window can change the conclusion.

## Limits of the reference

Input-map uncertainty, prescribed CME geometry, finite resolution and numerical choices affect a heliospheric reconstruction. NASA describes [WSA–ENLIL input and cone-model caveats](https://ccmc.gsfc.nasa.gov/models/WSA-Enlil-at-SWPC~3/); these are general interpretive caveats, not evidence that every operational configuration matches this archived run. The [ENLIL 2.8f description](https://ccmc.gsfc.nasa.gov/models/ENLIL~2.8f/) identifies the specific model family used here.

ENLIL is a comparison model, not ground truth. None of these plasma calculations supplies the neutral coma, heavy-ion charge-state distribution, charge-exchange yields and instrument response required for an absolute X-ray count-rate prediction.
