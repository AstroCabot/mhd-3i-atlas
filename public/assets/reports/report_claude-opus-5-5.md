# The solar wind at 3I/ATLAS: how the Claude model was built and why I trust it

*Claude (Anthropic Claude Opus 5.5, `claude-opus-5-5`). Research carried out 16–17 October 2026 in `mhd_llm/claude`; this account written 18 October 2026.*

The X-ray brightness of 3I/ATLAS is the product of two things: how much neutral gas the comet put out, and how many heavy ions the Sun threw at it. XMM-Newton measures the product. To learn about the gas you must divide by the ions, so whatever error you make in the solar-wind flux at the comet goes straight into the coma. The preprint estimated that flux by taking what STEREO-A measured and sliding it out along a Parker spiral to the comet, which gave $8.3\times10^{7}$ protons cm$^{-2}$ s$^{-1}$. A referee pointed to a NASA CCMC run of WSA–ENLIL (`Jan_Deca_120925_SH_1`) that gave $4.3\times10^{7}$. Two respectable methods, a factor of two apart. I set out to find which was closer, and why.

The trouble is that nobody measured the wind where the comet was. It sat at 1.87 AU, 6.5° below the solar equator and 25° east of STEREO-A. Between 1 and 2 AU, fast wind catches up with the slow wind in front of it. A ballistic remap lets every parcel coast at its own speed, so where a fast parcel would pass a slow one the remap returns two answers for the same place and time. Real plasma cannot pass through itself. It piles up into a stream interaction region (SIR), denser than either stream. To make one you need a model that carries pressure between parcels. That is the reason for doing MHD at all.

So I wrote a solver for ideal MHD with solar gravity and Dedner's divergence cleaning (Heaviside–Lorentz units, $p_T=p+B^2/2$):

$$\begin{aligned}
&\partial_t\rho+\nabla\cdot(\rho\mathbf v)=0,\\
&\partial_t(\rho\mathbf v)+\nabla\cdot\left[\rho\mathbf v\mathbf v+p_T\mathsf I-\mathbf B\mathbf B\right]=-\rho\,\frac{GM_\odot}{r^2}\,\hat{\mathbf r},\\
&\partial_t E+\nabla\cdot\left[(E+p_T)\mathbf v-(\mathbf v\cdot\mathbf B)\mathbf B\right]=-\rho\,\frac{GM_\odot}{r^2}\,\hat{\mathbf r}\cdot\mathbf v,\\
&\partial_t\mathbf B+\nabla\cdot\left(\mathbf v\mathbf B-\mathbf B\mathbf v+\psi\mathsf I\right)=0,\qquad \partial_t\psi+c_h^2\,\nabla\cdot\mathbf B=-\frac{c_h^2}{c_p^2}\,\psi .
\end{aligned}$$

The scalar $\psi$ carries divergence errors away at speed $c_h$ and damps them. The grid is spherical, 0.1 to 2.5 AU, ±60° in latitude, all longitudes. The method is finite-volume CUDA: piecewise-linear reconstruction, the HLLD Riemann solver, second-order Runge–Kutta, single precision. Two choices kept it honest. Momentum and field are stored as Cartesian components, so there are no geometric source terms to get wrong, and face areas are computed exactly, so a uniform flow stays uniform. The 1° grid has 22 million cells and runs 27 simulated days in 53 minutes on one RTX 4080 SUPER.

Before trusting it with the Sun I checked it on problems with known answers. Linear fast, Alfvén, slow and entropy waves converge at order 1.8–1.9 in a double-precision twin (single precision stops at $2\times10^{-3}$ of the amplitude). The Sod and Brio–Wu shock tubes converge at order 0.87, close to the first order expected with discontinuities. A steady wind with gravity holds its mass flux to $8\times10^{-5}$, and the Parker spiral comes out with $B_r r^2$ flat to 0.15%. Then I reran two classic calculations:

| at 1 AU | this code | published |
|---|---|---|
| Pizzo (1978) stream: peak speed, peak density | 630 km/s, 18.2 cm⁻³ | 625, 18.0 |
| Pizzo (1982) / Wiengarten et al. (2014) CIR: max $\lvert B\rvert$, max total pressure | 15.05 nT, 161 pPa | 15, 155 |

The code also broke twice, and each failure taught me something. At 2° it blew up in the small high-latitude cells next to the inner boundary. There the local fast speed is far below the fastest signal anywhere on the grid, and a cleaning speed set to that global maximum violated the local Courant condition. The cure is to cap it:

$$c_h=0.95\,\frac{\max\sum_d(|v_d|+c_{f,d})/\Delta x_d}{\max\sum_d 1/\Delta x_d}.$$

Then a tilted-dipole test sent 4% of cell updates to the pressure floor. That happens in cold, rarefied wind behind fast streams, where the thermal energy is a small difference of large numbers. I added an entropy equation and take the pressure from it wherever $e_{\rm th}<10^{-3}E$:

```cuda
float eth = U[EN] - 0.5f * d * (vx * vx + vy * vy + vz * vz) - 0.5f * b2;
float p = (gam - 1.f) * eth;
if (!(eth > ETA_DE * U[EN])) p = U[ENT] * powf(d, gam - 1.f);
```

Floor hits went from 57 million to zero.

The Sun enters at 0.1 AU, where the wind is already supersonic. The speed comes from the Wang–Sheeley–Arge relation, which CCMC evaluates daily on GONG magnetograms:

$$v=285+\frac{625}{(1+f_s)^{2/9}}\left[1-0.8\,e^{-(\theta_b/2^\circ)^2}\right]^3\ \mathrm{km\,s^{-1}},$$

where $f_s$ is how much a flux tube expands and $\theta_b$ is how far its foot lies from a coronal-hole edge. Density and temperature follow from $nv^2=$ const and $nT=$ const, and $B_\phi=-B_r\Omega r\sin\theta/v_r$ winds up the field. Those rules have a neat consequence. With $n\propto v^{-2}$ and uniform $|B_r|$, the Alfvén speed scales as $v$, so every stream leaves the boundary with the same Alfvén Mach number. Mine is 0.85, close to the $M_A\approx1$ that Parker Solar Probe finds near 20 solar radii. Coronal mass ejections come from NASA's DONKI catalog of coronagraph cone fits: 121 cones, each injected at its measured 21.5 R☉ time with its measured speed, direction and width.

My first real experiment was to drive the code with ENLIL's own inputs: the same maps, the same rules, the same 64 CMEs. If the two codes disagreed, there was a numerical problem to find before anything else. They agreed in speed (correlation 0.89 at Earth) once I matched one convention. ENLIL computes pressure as $(\rho/m_p)kT$, about 1.8 times smaller than $nkT(2+3x_\alpha)$ with 5% helium, and that alone had made my first replica 30 km/s too fast. Then I compared both with the spacecraft data for 15 November to 8 December, and found the thing that shaped everything afterward. Neither had any skill.

| hourly, Nov 15–Dec 8 | speed RMSE (km/s), STA / L1 | speed correlation, STA / L1 | flux, model/observed, STA / L1 |
|---|---|---|---|
| CCMC ENLIL | 121 / 174 | 0.08 / 0.06 | 0.58 / 0.54 |
| this model, 1° (fitted to these data) | 51 / 95 | 0.84 / 0.75 | 1.01 / 1.07 |

The two codes agree with each other and disagree with nature. ENLIL is set up for forecasting. Its density normalization is a factor of two low for this period, and it knows nothing of what the spacecraft measured in November. Its cone list keeps only CMEs faster than 600 km/s and wider than 30°, which dropped the two CMEs of 23 November aimed at the comet's sector, one of them within 7°. Codex audited DONKI independently and found the same omission. So the gap between the preprint and CCMC is not a question of MHD versus no MHD. It is a question of what you put in at the inner boundary.

To fix the boundary I let the spacecraft say what it should be. Every parcel in the model carries passive labels recording the longitude, latitude and time at which it left 0.1 AU. When STEREO-A, Wind or Solar Orbiter disagrees with the model at some hour, the labels say which patch of which day's boundary map made that plasma. The residuals are spread back onto every daily map $k$ with Gaussian weights,

$$\delta v_k(\lambda,\beta)=\frac{\sum_i K_{ik}\,\big(v^{\rm obs}_i-v^{\rm mod}_i\big)}{w_0+\sum_i K_{ik}},\qquad K_{ik}=\exp\!\left[-\frac{(t_i-t_k)^2}{2\sigma_t^2}-\frac{(\lambda-\lambda_i)^2}{2\sigma_\lambda^2}-\frac{(\beta-\beta_i)^2}{2\sigma_\beta^2}\right],$$

and likewise for $\ln n$. Here $\sigma_t=4$ d, $\sigma_\lambda=4^\circ$ (8° for density), $\sigma_\beta=8^\circ$ and $w_0=3$. Then the model is rerun: six iterations at 4°, three more at 2°. The core is a few lines:

```python
for a, b, v, w in zip(slon, slat, val, wgt):
    dl = (LO - a + 180) % 360 - 180
    k = w * np.exp(-0.5 * (dl / sig_lon) ** 2 - 0.5 * ((LA - b) / sig_lat) ** 2)
    num += k * v
    den += k
return num / (den + w0), den
```

You can always fit the data you are given. What matters is whether the fit knows anything about places it was not given. Leaving one spacecraft out at a time, the held-out speed errors fall by 15% (STEREO-A), 24% (L1) and 15% (Solar Orbiter). My first version used one correction for the whole month and made two of those held-out errors worse, by 8% and 12%. The Sun had changed during November, and the time weights fixed that. I also ran twin experiments: invent a solar wind, fly the real spacecraft through it, assimilate what they would have seen, and compare the recovered comet flux with the invented one. Errors were +14%, +0.2% and −9%, and +53% with STEREO-A withheld. STEREO-A is the key witness.

The other agents shaped the model. Codex showed that interpolating density and temperature separately between map points inflates the pressure there, by up to a factor of two. I now interpolate $v$, $nv^2$ and $nT$, which keeps both balances exact everywhere. Codex later hit the same low-pressure collapse I had seen, and I passed on the entropy fix. Argon's hydrodynamic control over-compressed the SIR by 75%, a good argument that the field must be in the model. Their final comet-frame fluxes, averaged over the EPIC-pn good time, bracket mine: Codex $1.19\times10^8$, mine $1.45\times10^8$, Argon $2.10\times10^8$. Three codes with different numerics and calibrations land three to five times above CCMC.

Convergence came next. Each test changes the comet's GTI-mean flux by less than the spread among twelve reasonable assimilation designs.

| change | GTI-mean flux |
|---|---|
| resolution 4° → 2° → 1° | 1.64 → 1.55 → 1.59 × 10⁸ |
| time step halved (4°, 2°) | −0.04%, +0.23% |
| latitude domain ±45°, ±75° | +3%, −0.7% |
| γ = 5/3 → 1.5 | −4% |
| comet-directed CMEs removed, or CCMC list instead | +13%, +13% |
| boundary field 332 nT; coronal model swapped | −10%; +20% |
| twelve assimilation designs | 68% range 0.54–1.40× |

The spread comes from timing. STEREO-A saw a dense slow stream followed by 650–780 km/s wind from 28 November. In the model the fast wind overtakes the slow wind between 1 and 1.9 AU. The resulting SIR crosses the comet in the middle of the XMM visit, and different assimilation designs place it anywhere from 7 hours earlier to 20 hours later.

![Proton flux at 3I/ATLAS (top) and the EPIC-pn light curve (bottom). Shaded strips are PN good-time intervals.](report_claude-opus-5-5_fig1.png)

| at 3I/ATLAS, PN-GTI mean | $n_p$ (cm⁻³) | $\lvert v\rvert$ (km/s) | $n\lvert v\rvert$ (cm⁻² s⁻¹) |
|---|---|---|---|
| CCMC ENLIL | 1.07 | 409 | 4.4 × 10⁷ |
| preprint ballistic (STEREO-A) | | | 9.3 × 10⁷ (window median 8.3 × 10⁷) |
| this model, 1° | 3.40 | 478 | 1.59 × 10⁸ |
| assimilation ensemble, 68% | 2.0–4.6 | 408–500 | 0.86–2.2 × 10⁸ |

In the comet's frame the flux is 9% lower ($1.45\times10^8$), because 3I/ATLAS was receding at 43 km/s. With heavy ions at $f=(3\text{–}10)\times10^{-4}$ of protons that is $(0.4\text{–}1.5)\times10^5$ cm$^{-2}$ s$^{-1}$, consistent with the preprint's prior. The ballistic method is not wrong because it lacks a factor. It cannot make an SIR. Applied to my model's own STEREO-A series, it reproduces the preprint's $8.3\times10^7$ while the MHD delivers about twice that at the comet.

Now the light curve, where I must be plain. Over the eight EPIC-pn frames the modeled flux is anti-correlated with the X-ray rate ($r\approx-0.75$). The SIR spike lands in the X-ray minimum. I did not tune to the light curve, and I will not claim it as support. Sliding the model in time, the correlation reaches +0.9 if the SIR arrives 15 hours earlier. That is outside the ensemble's early edge, and with eight points and dozens of trial shifts it proves nothing. Proton flux alone does not explain the X-ray variability. Either composition and charge-state changes matter, and no contemporaneous data exist to check them, or the SIR timing is worse than my ensemble admits.

So here is what I believe. The proton flux averaged over the observation is $1.6\times10^8$ cm$^{-2}$ s$^{-1}$, with a 68% range of $0.9$–$2.2\times10^8$. That is roughly twice the preprint's ballistic estimate and nearly four times the CCMC run, and the reason is understood: a compression region that ballistic mapping cannot form, fed by a boundary that CCMC left uncalibrated and underdense. The other two agents' independent codes land within a factor of 1.5 of mine. What I do not believe is the hour-by-hour shape inside the window. At 1.87 AU, 25° from the nearest spacecraft, the assimilation cannot place an SIR to better than about half a day.
