#!/usr/bin/env python3
"""Extract compact, provenance-bearing science products without running MHD.

All input access is read-only. Run from anywhere with Python + numpy/scipy/pandas/
astropy installed. JSON uses null for absent or out-of-domain samples. Native
equations and binary layouts are transcribed from the archived producer scripts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.interpolate import RegularGridInterpolator
from astropy.coordinates import get_body_barycentric
from astropy.time import Time

APP = Path(__file__).resolve().parents[1]
SRC = APP.parent / 'mhd_llm'
OUT = APP / 'public/data'
IDS = ('argon', 'codex', 'claude')
PROVENANCE = {}
FIELDS = ('density', 'speed', 'flux', 'incidentFlux')
NATIVE = {}


def source(rel):
    p = SRC / rel
    if rel not in PROVENANCE:
        h = hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda: f.read(1024 * 1024), b''):
                h.update(block)
        PROVENANCE[rel] = {'path': rel, 'bytes': p.stat().st_size, 'sha256': h.hexdigest()}
    return p


def js(rel):
    return json.loads(source(rel).read_text())


def table(rel, sep=','):
    return pd.read_csv(source(rel), sep=sep)


def mjd(utc):
    dt = pd.to_datetime(utc, utc=True)
    # Pandas 3 may infer microsecond rather than nanosecond datetime storage.
    return np.asarray((dt - pd.Timestamp('1970-01-01', tz='UTC')) / pd.Timedelta(days=1)) + 40587


def clean(o):
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, (np.floating, float)):
        # MJD epochs require full precision: nine significant figures would
        # move short GTI endpoints by seconds and corrupt exact integration.
        return float(o) if math.isfinite(o) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o


def write(name, data):
    p = OUT / name
    p.write_text(json.dumps(clean(data), separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n')
    print(f'{p.relative_to(APP)}: {p.stat().st_size:,} bytes', flush=True)


def interp(t, y, q):
    """No extrapolation and no bridging native missing values."""
    t, y, q = np.asarray(t), np.asarray(y), np.asarray(q)
    finite_time = np.isfinite(t)
    t, y = t[finite_time], y[finite_time]
    if not len(t):
        return np.full(q.shape, np.nan)
    if np.any(np.diff(t) <= 0):
        raise ValueError('Interpolation epochs must increase strictly')
    return np.interp(q, t, y, left=np.nan, right=np.nan)


def exact_mean(t, y, intervals):
    total = exposure = 0.0
    for a, b in intervals:
        if a < t[0] or b > t[-1]:
            raise ValueError('GTI leaves native model coverage')
        x = np.r_[a, t[(t > a) & (t < b)], b]
        vals = interp(t, y, x)
        if not np.isfinite(vals).all():
            raise ValueError('GTI crosses absent model data')
        total += np.trapezoid(vals, x)
        exposure += b - a
    return total / exposure


def claude_probes():
    rel = 'claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2/probes.bin'
    with source(rel).open('rb') as f:
        nb, nf = struct.unpack('2i', f.read(8))
        raw = np.frombuffer(f.read(), np.uint8)
    rec = 8 + 4 * nb * nf
    buf = raw[:len(raw) // rec * rec].reshape(-1, rec)
    ts = buf[:, :8].copy().view(np.float64).ravel() / 86400 + 60949
    v = buf[:, 8:].copy().view(np.float32).reshape(-1, nb, nf)
    # Body and field orders in src/py/{inputs,heliopy}.py.
    out = {}
    for name, b in [('comet', 0), ('wind', 1), ('stereo_a', 2), ('solar_orbiter', 3)]:
        a = v[:, b]
        vel = np.linalg.norm(a[:, 1:4], axis=1)
        out[name] = {'timeMjd': ts, 'density': a[:, 0], 'speed': vel, 'flux': a[:, 0] * vel * 1e5}
    e = table('claude/data/ephem/3i_atlas.csv')
    te = mjd(e.utc)
    xyz = e[['x_hci_km', 'y_hci_km', 'z_hci_km']].to_numpy()
    th = np.arccos(xyz[:, 2] / np.linalg.norm(xyz, axis=1))
    ph = np.unwrap(np.arctan2(xyz[:, 1], xyz[:, 0]))
    th, ph = interp(te, th, ts), interp(te, ph, ts)
    st, ct, sp, cp = np.sin(th), np.cos(th), np.sin(ph), np.cos(ph)
    vr, vt, vp = v[:, 0, 1:4].T
    vv = np.column_stack([vr * st * cp + vt * ct * cp - vp * sp,
                          vr * st * sp + vt * ct * sp + vp * cp,
                          vr * ct - vt * st])
    vc = np.column_stack([interp(te, e[k], ts) for k in ('vx_hci', 'vy_hci', 'vz_hci')])
    out['comet']['incidentFlux'] = out['comet']['density'] * np.linalg.norm(vv - vc, axis=1) * 1e5
    return out


def native_models():
    arg = table('argon/outputs/runs/res_fine_224x48x240_probes.tsv', '\t')
    cod = table('codex/results/ct156_w30_theta40_phi192/probe.csv')
    cla = claude_probes()
    for name, pid in [('comet', 0), ('wind', 1), ('stereo_a', 2), ('solar_orbiter', 3)]:
        a = arg[arg.probe == name]
        c = cod[cod.probe_id == pid]
        NATIVE.setdefault('argon', {})[name] = {'timeMjd': a.mjd_utc.to_numpy(), 'density': a.n_cm3.to_numpy(),
                    'speed': a.vmag_kms.to_numpy(), 'flux': a.flux_helio_cm2s.to_numpy(), 'incidentFlux': a.flux_rel_cm2s.to_numpy()}
        NATIVE.setdefault('codex', {})[name] = {'timeMjd': c.day.to_numpy() + 60980, 'density': c.n_cm3.to_numpy(),
                    'speed': c.speed_kms.to_numpy(), 'flux': c.flux_cm2_s.to_numpy()}
    # Exact final-product incident flux, already on the arrival clock. Keep its
    # emission epoch to prevent applying light travel time twice.
    product = table('codex/results/comet_timeseries.csv')
    NATIVE['codex']['comet'] = {'timeMjd': product.comet_emission_day.to_numpy() + 60980,
        'arrivalMjd': product.day.to_numpy() + 60980, 'density': product.density_cm3.to_numpy(),
        'speed': product.speed_heliocentric_kms.to_numpy(), 'flux': product.flux_heliocentric_cm2_s.to_numpy(),
        'incidentFlux': product.incident_flux_cm2_s.to_numpy()}
    NATIVE['claude'] = cla


def ephemerides():
    # Codex vector ephemerides are already fixed-J2000 ecliptic, but use actual
    # Earth from the copied Argon Horizons request for the light travel proxy.
    tracks = {}
    for name in ['comet', 'wind', 'stereo_a', 'solar_orbiter']:
        d = table(f'codex/observations/ephemeris_{name}.tsv', '\t')
        tracks[name] = (d.mjd_utc.to_numpy(), d[['x_au', 'y_au', 'z_au']].to_numpy())
    e = table('argon/data/raw/ephemeris/earth.csv')
    tracks['earth'] = (e.JD_UT.to_numpy() - 2400000.5, e[['x_au', 'y_au', 'z_au']].to_numpy())
    return tracks


def arrival_time(t, tracks):
    def at(name):
        tt, xx = tracks[name]
        return np.column_stack([interp(tt, xx[:, j], t) for j in range(3)])
    # Geometric Earth position is evaluated at emission, matching Codex's
    # documented Earth-proxy convention to sub-second precision here.
    return t + np.linalg.norm(at('comet') - at('earth'), axis=1) * 499.004783836 / 86400


def comet_product(tracks):
    tgrid = np.arange(61009, 61016 + 1e-8, 1 / 48)
    series = {}
    for id in IDS:
        m = NATIVE[id]['comet']
        ta = m.get('arrivalMjd', arrival_time(m['timeMjd'], tracks))
        m['arrivalMjd'] = ta
        series[id] = {k: interp(ta, m[k], tgrid) for k in FIELDS}
    e = np.load(source('argon/data/processed/ccmc_extracted.npz'))
    te = e['3I-Atlas1_mjd']
    ta = arrival_time(te, tracks)
    # Native ASCII ENLIL N is rho/mp. Divide by 1.2 for x_alpha=.05 to
    # compare proton number density (the native agents used different rules).
    proton = e['3I-Atlas1_n_cm3'] / 1.2
    series['enlil'] = {'density': interp(ta, proton, tgrid),
        'speed': interp(ta, e['3I-Atlas1_vmag_kms'], tgrid),
        'flux': interp(ta, proton * e['3I-Atlas1_vmag_kms'] * 1e5, tgrid)}
    # Preserve Claude's transferred design spread as a separate nonprobabilistic
    # band. It is not pooled with other agents or treated as a confidence interval.
    cl = table('claude/figs/timeseries_3i_atlas.csv')
    tc = arrival_time(mjd(cl.utc), tracks)
    bands = {}
    for key, col in [('density', 'n'), ('speed', 'v'), ('flux', 'flux'), ('incidentFlux', 'flux_rel')]:
        bands[key] = {'lower': interp(tc, cl[col + '_p16'], tgrid),
                      'median': interp(tc, cl[col + '_median'], tgrid),
                      'upper': interp(tc, cl[col + '_p84'], tgrid)}
    return {'timeMjd': tgrid, 'clock': 'Photon-arrival UTC at the geometric Earth proxy',
        'series': series, 'claudeDesignBand': bands,
        'bandQualification': 'Claude: transferred 12-member assimilation-design 16th–84th percentiles. Probability coverage has not been calibrated.',
        'units': {'density': 'cm⁻³', 'speed': 'km s⁻¹', 'flux': 'cm⁻² s⁻¹', 'incidentFlux': 'cm⁻² s⁻¹'},
        'limits': {'density': [0, 16], 'speed': [300, 850], 'flux': [0, 8e8], 'incidentFlux': [0, 8e8]},
        'references': {'argon': 'res_fine_224x48x240', 'codex': 'ct156_w30_theta40_phi192', 'claude': 'prod_da3_ccmc_prod_t4_L1ref_L2', 'enlil': 'Jan_Deca_120925_SH_1; N/1.2 proton correction'},
        'notes': ['Linear resampling at 30-minute intervals; null outside native coverage. Exact native samples, not display resampling, are used for metrics.',
                  'Argon and Claude geometric UTC are mapped to arrival UTC using copied Horizons Earth–comet separation. Codex retains its recorded arrival UTC.',
                  'Native published PN means differ in clock and integration convention; use the homogenized exact-GTI table for direct comparison.',
                  'ENLIL is an independent remote-driven model, not an observation of the comet. Density is converted from rho/mp to proton density assuming 5% alpha particles.']}


def xray_product():
    x = table('argon/data/raw/spacecraft/lightcurve.tsv', '\t')
    g = table('argon/data/raw/spacecraft/xmm_gtis.tsv', '\t')
    pn = g[g.detector == 'pn']
    intervals = pn[['start_mjd_utc', 'stop_mjd_utc']].to_numpy()
    obs = []
    for r in x.itertuples():
        gg = pn[pn.frame == r.frame]
        obs.append({'frame': r.frame, 'timeMjd': float(mjd(pd.Series([r.midpoint_utc]))[0]),
                    'rate': r.rate_ct_s, 'error': r.error_ct_s, 'exposureSeconds': r.gti_s,
                    'intervals': gg[['start_mjd_utc', 'stop_mjd_utc']].to_numpy()})
    rates = x.rate_ct_s.to_numpy()
    exposure = np.array([sum(b-a for a,b in o['intervals']) * 86400 for o in obs])
    rate_mean = np.average(rates, weights=exposure)
    model = {}
    argon_native=js('argon/outputs/summary_results.json')['mhd_runs']['res_fine_224x48x240']['pn_gti']['flux_rel_mean_cm2s']
    claude_native=js('claude/figs/timeseries_3i_atlas.json')['ref::1° reference']['flux_rel']['gti_mean']
    codex_native=js('codex/results/summary.json')['cases']['ct156_w30_theta40_phi192']['PN_GTI_weighted_mean']['f_incident']
    native_reported={'argon':argon_native,'claude':claude_native,'codex':codex_native}
    for id in IDS:
        m = NATIVE[id]['comet']
        t = m['arrivalMjd']
        frameflux = np.array([exact_mean(t, m['incidentFlux'], o['intervals']) for o in obs])
        allmean = exact_mean(t, m['incidentFlux'], intervals)
        normalized = frameflux / allmean
        # A one-parameter normalization is only a shape diagnostic, not an
        # absolute SWCX forward model or a fit used to tune wind parameters.
        scale = rate_mean / allmean
        proxy = frameflux * scale
        model[id] = {'incidentFlux': frameflux, 'normalizedFlux': normalized,
            'rateScaledProxy': proxy, 'pearsonR': np.corrcoef(frameflux, rates)[0, 1],
            'shapeRmse': np.sqrt(np.mean((normalized - rates / rate_mean) ** 2)),
            'gtiMeans': {k: exact_mean(t, m[k], intervals) for k in FIELDS},
            'normalizationRate': rate_mean, 'normalizationFlux': allmean,
            'scaleMeaning': 'PN exposure-weighted mean count rate / PN exposure-weighted model incident flux'}
        geometric=exact_mean(m['timeMjd'],m['incidentFlux'],intervals)
        model[id]['nativeMeanComparison']={'reportedPnMean':native_reported[id],
            'exactGeometricPnMean':geometric,'exactArrivalPnMean':allmean,
            'quadratureFraction':geometric/native_reported[id]-1 if id!='codex' else None,
            'lightTimeFraction':allmean/geometric-1,
            'explanation': {'argon':'Native report averages 10-minute rows selected by a GTI mask. Exact endpoint integration gives 2.16876e8 on the geometric clock (+3.06%); the ~15.7-minute photon delay gives 2.21305e8 on the common arrival clock (+2.04% further).',
                'claude':'Native report uses a fine midpoint GTI quadrature on geometric UTC. Exact geometric integration reproduces 1.45478e8; the ~15.7-minute photon delay changes the sampled SIR spike to 1.40065e8 on arrival UTC (−3.72%).',
                'codex':'Native final report already uses exact PN GTI integration and the observer-arrival clock. The common value reproduces the native selected CT report.'}[id]}
    return {'observations': obs, 'models': model, 'rateUnit': 'counts s⁻¹',
        'observedNormalized': rates / rate_mean, 'observedNormalizedError': x.error_ct_s.to_numpy() / rate_mean,
        'totalPnExposureSeconds': (intervals[:, 1] - intervals[:, 0]).sum() * 86400,
        'pnIntervals': intervals, 'window': [61012.50286, 61013.42493],
        'qualification': 'The curves are flux-driven X-ray shape proxies, each scaled to the observed exposure-weighted mean. None of the models predicts absolute counts: heavy-ion charge states, abundance, neutral coma and instrumental response remain unconstrained. The eight observed rates were not used to tune the wind. Pearson r measures shape agreement; it is not empirical plasma accuracy or a statistical model probability.',
        'integration': 'Exact trapezoidal integration of each native piecewise-linear curve over every accepted PN GTI, with exact endpoints and no extrapolation. Common photon-arrival UTC for all agents.',
        'rateUnitEvidence':'Manuscript Supplement, solar-wind/lightcurve discussion: net rate spans 0.55–4.29 counts s−1. The 10⁻³ surface-brightness contour unit elsewhere is a different quantity.',
        'source': 'Copied preprint EPIC-pn 0.2–1 keV background/oot-corrected lightcurve and accepted GTIs; ObsID 0963720201.'}


def spacecraft_product():
    out = []
    for name, title in [('stereo_a', 'STEREO-A / PLASTIC'), ('wind', 'Wind / SWE'), ('solar_orbiter', 'Solar Orbiter / SWA-PAS')]:
        o = table(f'argon/data/raw/spacecraft/plasma_{name}.tsv', '\t')
        o = o[(o.mjd_utc >= 60998) & (o.mjd_utc <= 61014)].copy()
        t = o.mjd_utc.to_numpy()
        observed = {'density': o.density_cm3.to_numpy(), 'speed': o.speed_km_s.to_numpy(), 'flux': o.proton_flux_cm2_s.to_numpy()}
        models = {}
        for id in IDS:
            m = NATIVE[id][name]
            models[id] = {k: interp(m['timeMjd'], m[k], t) for k in ('density', 'speed', 'flux')}
        metrics = {}
        # The same timestamps and positive finite observed/model values are
        # used for each agent's scalar metric, eliminating changing test sets.
        masks = {k: np.isfinite(observed[k]) & (observed[k] > 0) for k in observed}
        for k in masks:
            for id in IDS:
                masks[k] &= np.isfinite(models[id][k]) & (models[id][k] > 0)
        for id in IDS:
            vs = masks['speed']; ns = masks['density']; fs = masks['flux']
            a, b = models[id]['speed'][vs], observed['speed'][vs]
            metrics[id] = {'speedN': int(vs.sum()), 'speedRmse': np.sqrt(np.mean((a - b) ** 2)),
                'speedBias': np.mean(a - b), 'speedR': np.corrcoef(a, b)[0, 1],
                'densityN': int(ns.sum()), 'densityMedianRatio': np.median(models[id]['density'][ns] / observed['density'][ns]),
                'densityLogR': np.corrcoef(np.log10(models[id]['density'][ns]), np.log10(observed['density'][ns]))[0, 1],
                'fluxN': int(fs.sum()), 'fluxMedianRatio': np.median(models[id]['flux'][fs] / observed['flux'][fs])}
        out.append({'id': name, 'label': title, 'timeMjd': t, 'observed': observed, 'models': models,
                    'metrics': metrics, 'clock': 'Physical geometric UTC',
                    'qualification': 'The models are compared with spacecraft measurements on the same finite hourly samples, 19 Nov–5 Dec 2025. Argon and Claude assimilated these spacecraft; Codex also used spacecraft data in calibration. These residuals therefore include calibration performance. Ratios give model / observation.'})
    return out


def read_snap(rel):
    with source(rel).open('rb') as f:
        nr, nt, nphi, nf = struct.unpack('4i', f.read(16))
        rin, rout, latmax, t = struct.unpack('4d', f.read(32))
        a = np.frombuffer(f.read(), np.float32).reshape(nf, nr, nt, nphi)
    r = rin + (np.arange(nr) + .5) * (rout - rin) / nr
    th = np.pi / 2 - latmax + (np.arange(nt) + .5) * 2 * latmax / nt
    return r, th, a


def bernoulli(r):
    # Exact native Claude benchmark convention: 5% alpha particles, gamma=5/3.
    mp, kb, gm, au, gam = 1.67262192e-24, 1.380649e-16, 1.32712440018e26, 1.495978707e13, 5/3
    rho0 = 300 * mp * 1.2; p0 = 300 * kb * 1e6 * 2.15
    K = p0 / rho0 ** gam; mdot = rho0 * 4e7 * (.1 * au) ** 2
    E = .5 * 4e7 ** 2 + gam / (gam - 1) * p0 / rho0 - gm / (.1 * au)
    v = np.full(len(r), 4e7)
    for _ in range(100):
        rho = mdot / (v * (r * au) ** 2)
        f = .5 * v ** 2 + gam / (gam - 1) * K * rho ** (gam - 1) - gm / (r * au) - E
        v -= f / (v - K * gam * rho ** (gam - 1) / v)
    return v / 1e5


def benchmark_product():
    charts = []; metrics = []
    ar = table('argon/outputs/benchmarks/bw_brio_wu_1600.tsv', '\t')
    cr = table('codex/solver/tests/athena_reference/reference.csv')
    x = np.linspace(.001, .999, 750)
    charts.append({'id': 'brio-wu', 'title': 'Brio–Wu shock tube: retained native density profiles',
        'xLabel': 'Position x (dimensionless)', 'yLabel': 'Density ρ (code units)',
        'series': [{'model': 'argon', 'label': 'Argon N=1600', 'x': x, 'y': interp(ar.x, ar.rho, x)},
                   {'model': 'codex', 'label': 'Codex native Athena CT N=8192 (PPM/RK3 benchmark)', 'x': x, 'y': interp(cr.x, cr.rho, x)}],
        'notes': 'Standard gamma=2, t=0.1 setup. Claude retained a plot and error table but no numerical 1D profile; its refinement errors are shown separately. Codex uses the production CT kernel with higher-order PPM/RK3 reconstruction and time integration; production uses PLM/RK2. Brio–Wu admits multiple compound-wave branches, so the plotted references are identified by method and resolution.'})
    am = js('argon/outputs/benchmarks/bw_brio_wu_metrics.json')
    cm = js('claude/bench/out_1d/results.json')
    charts.append({'id': 'shock-convergence', 'title': 'Shock-tube density error under refinement',
        'xLabel': 'Number of cells N', 'yLabel': 'L₁ density error (code units)', 'logX': True, 'logY': True,
        'series': [{'model': 'argon', 'label': 'Argon Brio–Wu vs N=1600 self-reference', 'x': [400, 800], 'y': [am['l1_rho_400_vs_1600'], am['l1_rho_800_vs_1600']]},
                   {'model': 'claude', 'label': 'Claude Brio–Wu vs N=8192 self-reference', 'x': [int(k) for k in cm['briowu']['L1_density_vs_N8192']], 'y': list(cm['briowu']['L1_density_vs_N8192'].values())},
                   {'model': 'claude', 'label': 'Claude Sod vs analytic solution', 'x': [int(k) for k in cm['sod']['L1_density']], 'y': list(cm['sod']['L1_density'].values())}],
        'notes': 'The test definitions and self-reference resolutions differ between models. Compare refinement trends within each series. Shock discontinuities reduce global convergence order toward one. The Codex series includes only the selected CT formulation.'})
    # Each wind benchmark is normalized to its own analytic reference; their
    # initial thermodynamic states differ and must not be overplotted raw.
    ar = table('argon/outputs/benchmarks/parker_192_parker_profile.tsv', '\t')
    r = ar.r_au.to_numpy(); gam=1.5; vr0=4.; rho0=700.; pin=rho0*5e5/6.0554e5
    mf=.01*rho0*vr0; bf=.01*300/45.8506; ent=pin/rho0**gam
    def rhs(rr, vv):
        rho=mf/(rr*rr*vv[0]); cs=gam*ent*rho**(gam-1); bp=-bf*.042914/(rr*vv[0]); ca=bp*bp/rho
        return [(2*cs/rr+ca/rr-.088713/rr**2)/(vv[0]-(cs+ca)/vv[0])]
    exact=solve_ivp(rhs,[.1,float(r[-1])],[4.],t_eval=r,rtol=1e-9,atol=1e-11).y[0]*100
    rc, _, ac = read_snap('claude/bench/out_sphere/wind_nr512/snap_0001728000.bin')
    vc=ac[1].mean(axis=(1,2)); ec=bernoulli(rc)
    charts.append({'id':'parker','title':'Spherical steady wind: error against analytic radial solution',
        'xLabel':'Heliocentric radius (AU)','yLabel':'Speed / analytic speed − 1',
        'series':[{'model':'argon','label':'Argon Parker/Weber–Davis, γ=1.5','x':r,'y':ar.vr_kms.to_numpy()/exact-1},
                  {'model':'claude','label':'Claude adiabatic Bernoulli wind, γ=5/3','x':rc,'y':vc/ec-1}],
        'notes':'Each analytic reference uses its benchmark’s archived boundary and pressure convention. The two setups differ. Codex verifies its final CT implementation through separate flux/geometry audits and the recorded numerical controls below.'})
    ps=js('claude/bench/out_sphere/results.json')
    ct=js('codex/validation/ct_literature_benchmark.json')
    metrics += [{'model':'argon','test':'Brio–Wu density refinement','metric':'L₁(400)/L₁(800)','value':am['convergence_ratio'],'unit':'ratio','qualification':'N=1600 numerical self-reference'},
                {'model':'claude','test':'Brio–Wu density refinement','metric':'Measured order','value':cm['briowu']['order'],'unit':'order','qualification':'N=8192 numerical self-reference'},
                {'model':'claude','test':'Sod shock tube','metric':'Measured order','value':cm['sod']['order'],'unit':'order','qualification':'Analytic hydrodynamic solution'},
                {'model':'codex','test':'Brio–Wu native CT','metric':'Largest plateau relative error','value':ct['diagnostics']['maximum_absolute_relative_error_across_two_plateaus_and_six_fields'],'unit':'fraction','qualification':'Two published plateau samples; PPM/RK3 benchmark, not production PLM/RK2; no retrospective pass threshold'},
                {'model':'claude','test':'Free-stream preservation','metric':'Maximum relative density error','value':ps['free_stream']['max_rel_density_error'],'unit':'fraction','qualification':'Float32 after 40 simulation days'},
                {'model':'claude','test':'Parker spiral','metric':'RMS spiral-angle ratio error','value':ps['spiral']['rms_rel_spiral_err'],'unit':'fraction','qualification':'GLM divergence drift remains; not converged to roundoff'}]
    waves = cm['linear_waves_f64']
    charts.append({'id':'linear-waves','title':'Claude linear MHD waves: double-precision verification',
        'xLabel':'Number of cells N','yLabel':'L₁ error','logX':True,'logY':True,
        'series':[{'model':'claude','label':f'{k.capitalize()} wave (p={v["order"]:.2f})','x':[int(n)for n in v['L1']],'y':list(v['L1'].values())}for k,v in waves.items()],
        'notes':'Amplitude 10⁻⁶. Float64 twin establishes nominal second-order accuracy; production float32 reaches a small-amplitude rounding floor.'})
    # Compact final CT directional comparisons, including failures outside the
    # selected pairs rather than silently declaring global convergence.
    cs=js('codex/validation/ct_convergence_summary.json')
    selected=js('codex/results/reference_selection.json')
    convergence=[]
    for category in ('spatial','temporal','domain','initial_condition','outer_extent'):
        section=cs.get(category,{})
        rows=section.get('comparisons',[]) if isinstance(section,dict) else []
        for row in rows:
            convergence.append({'model':'codex','category':category,'left':row.get('left'),'right':row.get('right'),
                'passed':row.get('qualified_pass', row.get('passed')),'valid':row.get('availability') == 'complete',
                'maximumRelativeDifferences':{k:v['maximum_relative_difference'] for k,v in row.get('comparison',{}).items() if isinstance(v,dict) and 'maximum_relative_difference' in v},
                'pnMeanRelativeChanges':row.get('PN_GTI_mean_relative_change'),
                'exposurePassed':row.get('exposure_observables',{}).get('qualified_pass'),
                'targets':row.get('targets'),'qualification':'Only this recorded pair and geometry; a pass is not an absolute discretization error bound.'})
    # Argon and Claude record different exposure-integration and clock rules;
    # preserve native controls, label them rather than forcing fake equivalence.
    arg=js('argon/outputs/summary_results.json')
    runs=arg['mhd_runs']; fine=runs['res_fine_224x48x240']['pn_gti']['flux_rel_mean_cm2s']
    nativeConvergence={'argon':[{'run':k,'label':v['label'],'incidentFluxPnMean':v['pn_gti']['flux_rel_mean_cm2s'],
             'fractionVsFine':v['pn_gti']['flux_rel_mean_cm2s']/fine-1}for k,v in runs.items()],
        'claude':js('claude/bench/out_convergence/final_resolution.json')}
    return {'charts':charts,'metrics':metrics,'convergence':convergence,'nativeConvergence':nativeConvergence,
        'notes':'Each panel identifies its benchmark, reference solution, precision, pressure convention and aggregation rule. These differences limit comparisons of error magnitude across models.'}


def remote_product():
    c=table('claude/data/boundary/qc/ccmc_compare.csv')
    d=np.load(source('codex/external_model/boundaries.npz'))
    idx=int(np.argmin(abs(d['obs_mjd']-61004)))
    # Daily maps have a different Carrington longitude origin. Sort each actual
    # map's stored longitude rather than pretending a fixed observer frame.
    lon=d['carrington_longitude_deg'][idx]; order=np.argsort(lon)
    speed=d['speed_kms'][idx][:,order]
    b=d['br_nT'][idx][:,order]
    return {'coronalReplication':{'timeMjd':mjd(c.map_time_utc),'speedR':c.v_corr.to_numpy(),
        'speedRmse':c.v_rms_kms.to_numpy(),'polarityAgreement':c.polarity_agree.to_numpy(),
        'title':'Independent PFSS/SCS/WSA versus archived CCMC WSA 5.4/GONGz',
        'qualification':'Claude’s independently computed PFSS/SCS/WSA boundary is compared pixel by pixel with archived WSA maps derived from remote sensing. This tests coronal-model agreement. Argon and Codex use the archived maps as input and have no separate coronal replication.'},
        'boundaryMap':{'timeMjd':d['obs_mjd'][idx],'longitudeDeg':lon[order],'latitudeDeg':d['latitude_deg'],
            'speed':speed,'radialField':b,'units':{'speed':'km s⁻¹','radialField':'nT'},
            'title':'Remote-derived WSA boundary before heliospheric propagation',
            'qualification':'GONG photospheric magnetograms constrain PFSS/SCS topology. WSA converts open-field expansion and coronal-hole distance into an empirical speed map near 0.1 AU. All three reconstruction families use this modeled boundary input.'},
        'evidence':[
            {'input':'Photospheric GONG magnetograms → PFSS/SCS/WSA','models':['argon','codex','claude'],'role':'Inner-boundary speed and magnetic polarity','limit':'Coronal mapping and closure uncertainties propagate to comet timing and density.'},
            {'input':'CCMC ENLIL Jan_Deca_120925_SH_1','models':['argon','codex','claude'],'role':'Independent remote-driven model comparator','limit':'Different boundary pressure/density conventions; low spacecraft skill in this interval.'},
            {'input':'DONKI / coronagraph cone analyses','models':['argon','codex','claude'],'role':'Transient geometry and sensitivity scenarios','limit':'Final Argon and Codex references omit explicit CMEs; Claude includes selected cones. Composition is not predicted.'},
            {'input':'Heavy-ion abundance / charge states','models':['argon','codex','claude'],'role':'Unmeasured prior or passive proxy','limit':'No contemporaneous heavy-ion composition constraint at the comet; cannot validate absolute SWCX counts.'}]}


def periodic_sample(r, p, a, rr, pp):
    pe=np.r_[p[-1]-2*np.pi,p,p[0]+2*np.pi]
    ae=np.concatenate([a[:,-1:],a,a[:,:1]],axis=1)
    return RegularGridInterpolator((r,pe),ae,bounds_error=False,fill_value=np.nan)(np.column_stack([rr.ravel(),pp.ravel()])).reshape(rr.shape)


def animation_product(tracks):
    """A projected comparison of actual retained planes, never fabricated MHD."""
    n=128; axis=np.linspace(-2.4,2.4,n); xx,yy=np.meshgrid(axis,axis)
    rr=np.hypot(xx,yy); pp=np.arctan2(yy,xx)%(2*np.pi)
    times=np.arange(61006.25,61014+1e-8,.25)
    # Native MHD epochs are not synchronized perfectly: bounded interpolation
    # onto the exact common 6-hour UTC sequence is explicit in metadata.
    models={}
    rels=sorted((SRC/'argon/outputs/runs').glob('model3_assimilated_slice_*.bin'))
    at=[]; aa=[]
    for path in rels:
        with source(str(path.relative_to(SRC))).open('rb')as f:
            at.append(struct.unpack('d',f.read(8))[0]);aa.append(np.frombuffer(f.read(),np.float32).reshape(4,160,180)[2])
    # The native CUDA producer samples latitude=-6.455 degrees, a conical
    # surface at the comet latitude. Its older plotting script treated r as
    # a planar radius; use the actual 3D sampling coordinates here instead.
    R=np.array(js('codex/observations/coordinate_system.json')['ecliptic_to_solar_equatorial_matrix'])
    lat=np.deg2rad(-6.455)
    # q=A h_xy + d h_z, h_z=tan(lat)|h_xy|. Invert the projected cone
    # analytically using a positive quadratic root for |h_xy|.
    plane=R.T[:2,:2]; inv=np.linalg.inv(plane)
    u=np.column_stack([xx.ravel(),yy.ravel()])@inv.T
    k=inv@R.T[:2,2]*np.tan(lat)
    dot=u@k;den=1-k@k
    s=(-dot+np.sqrt(dot*dot+den*np.sum(u*u,axis=1)))/den
    hxy=u-s[:,None]*k[None,:]
    ar=(s/np.cos(lat)).reshape(xx.shape)
    ap=np.arctan2(hxy[:,1],hxy[:,0]).reshape(xx.shape)%(2*np.pi)
    def sample_time(t, nt, arrays, sampler):
        if t<nt[0] or t>nt[-1]:raise ValueError('Animation time extrapolation')
        hi=min(np.searchsorted(nt,t,side='right'),len(nt)-1);lo=max(0,hi-1)
        w=(t-nt[lo])/(nt[hi]-nt[lo]) if hi!=lo else 0
        return sampler(arrays[lo])*(1-w)+sampler(arrays[hi])*w
    ra=.1+(np.arange(160)+.5)*2.3/160;pa=(np.arange(180)+.5)*2*np.pi/180
    af=[sample_time(t,np.array(at),aa,lambda a:periodic_sample(ra,pa,a,ar,ap))for t in times]
    models['argon']={'nativePlane':'Constant solar latitude −6.455° (conical shell), projected to J2000 ecliptic x/y',
        'definition':'n_p |v|, heliocentric bulk proton flux','reference':'model3_assimilated (160×32×180)',
        'qualification':'Retained movie slices are available for the 160-cell baseline run. The quantitative comet comparison uses the 224-cell fine run. The animation samples the solar-latitude cone at −6.455° and projects it onto the display axes; an ecliptic slice would require additional output.',
        'nativeTimeMjd':at,'frames':af,'radiusForContrast':ar}
    # Claude stores ecliptic polar samples with n and radial velocity only.
    rel='claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2/slices.bin'
    with source(rel).open('rb')as f:
        nr,np_,nf=struct.unpack('3i',f.read(12));ri,ro=struct.unpack('2f',f.read(8));rec=8+4*nr*np_*nf
        count=(source(rel).stat().st_size-20)//rec
        ct=[];ca=[]
        for i in range(count):
            t=struct.unpack('d',f.read(8))[0]/86400+60949
            a=np.frombuffer(f.read(rec-8),np.float32).reshape(nf,nr,np_)
            ct.append(t);ca.append(a[0]*a[1]*1e5)
    rc=ri+(np.arange(nr)+.5)*(ro-ri)/nr;pc=(np.arange(np_)+.5)*2*np.pi/np_
    cf=[sample_time(t,np.array(ct),ca,lambda a:periodic_sample(rc,pc,a,rr,pp))for t in times]
    models['claude']={'nativePlane':'True J2000 ecliptic z=0','definition':'n_p v_r, radial proton-flux proxy',
        'reference':'prod_da3_ccmc_prod_t4_L1ref_L2 (512×120×360)',
        'qualification':'The retained density and radial-speed slices give radial proton flux n_p v_r. The full velocity vector required for n_p |v| was not retained.',
        'nativeTimeMjd':ct,'frames':cf,'radiusForContrast':rr}
    base='codex/results/ct156_w30_theta40_phi192/'
    cc=table(base+'snapshots.csv');ct=cc.day.to_numpy()+60980
    cx=np.load(source(base+'ecliptic_x_au.npy'));cy=np.load(source(base+'ecliptic_y_au.npy'))
    ca=[np.load(source(base+f))for f in cc.file]
    def samp(a):
        return RegularGridInterpolator((cy,cx),a,bounds_error=False,fill_value=np.nan)(np.column_stack([yy.ravel(),xx.ravel()])).reshape(xx.shape)
    ff=[sample_time(t,ct,ca,samp)for t in times]
    models['codex']={'nativePlane':'True J2000 ecliptic z=0','definition':'n_p |v|, heliocentric bulk proton flux',
        'reference':'ct156_w30_theta40_phi192 (156×40×192)',
        'qualification':'Native double-precision CT conserved-state interpolation. Missing outside retained cell-center support, including r≳2.293 AU. No density/speed auxiliary slices were retained.',
        'nativeTimeMjd':ct,'frames':ff,'radiusForContrast':rr}
    for id in IDS:
        m=models[id];frames=np.asarray(m.pop('frames'));radius=m.pop('radiusForContrast')
        # Fixed two-byte logarithmic encoding keeps data small and reversible
        # within 0.0002 dex. Zero is missing. Colors are a separate UI concern.
        def encode(a):
            valid=np.isfinite(a)&(a>0)
            e=np.zeros(a.shape,dtype=np.uint16)
            e[valid]=np.clip(np.rint((np.log10(a[valid])-3)*5000)+1,1,65535).astype(np.uint16)
            return e.reshape(len(times),-1)
        m['flux']=encode(frames)
        m['contrast']=encode(frames*radius[None,:,:]**2)
        m['url']=f'/data/solarwind-{id}.json'
        write(f'solarwind-{id}.json',{'model':id,'width':n,'height':n,'timeMjd':times,
            'encoding':{'missing':0,'decode':'value = 10 ** (3 + (code - 1) / 5000)','log10Offset':3,'log10Scale':5000},
            'flux':m.pop('flux'),'contrast':m.pop('contrast')})
    projectedTracks={}
    for name,(tt,pos)in tracks.items():
        projectedTracks[name]={'x':interp(tt,pos[:,0],times),'y':interp(tt,pos[:,1],times)}
    # Only built-in ephemeris evaluation, no network. Extra planets are context.
    epochs=Time(times,format='mjd',scale='utc');sun=get_body_barycentric('sun',epochs)
    eps=np.deg2rad(84381.448/3600);rot=np.array([[1,0,0],[0,np.cos(eps),np.sin(eps)],[0,-np.sin(eps),np.cos(eps)]])
    for name in ['mercury','venus','mars']:
        pos=(get_body_barycentric(name,epochs)-sun).xyz.value.T@rot.T
        projectedTracks[name]={'x':pos[:,0],'y':pos[:,1]}
    return {'timeMjd':times,'width':n,'height':n,'extentAu':[-2.4,2.4,-2.4,2.4],
        'sampling':'Uniform x/y nodes including endpoints; flat frame index = yIndex * width + xIndex, y increases upward.',
        'projection':'Sun-centered J2000 ecliptic x/y, viewed from ecliptic north; vernal equinox to the right.',
        'timeConvention':'Physical geometric UTC; common exact 6-hour cadence, bounded linear temporal interpolation between native slices.',
        'models':models,'tracks':projectedTracks,
        'units':'cm⁻² s⁻¹','fluxLimits':[1e7,3e10],'contrastLimits':[1e7,2e9],
        'contrastDefinition':'Native proton flux multiplied by the squared heliocentric radius in its source sampling surface, in AU². This compensates for radial geometric dilution to show stream structure.',
        'qualification':'Colors, spatial display limits, frame timestamps and tracks are shared. Native planes and flux definitions differ and are labeled. Projection cannot supply a missing physical slice; values are not cross-model difference maps. Null/zero-code pixels are unavailable, not zero wind. No simulation has been rerun.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--skip-animation',action='store_true');args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    for rel in ['argon/scripts/analyze_and_plot.py','argon/scripts/make_heliosphere_animation.py',
        'argon/src/heliomhd3d.cu','claude/src/mhd/helio.cu','claude/ref/main.txt',
        'claude/src/py/heliopy.py','claude/src/py/run_helio.py','claude/src/py/inputs.py','claude/src/py/animate.py',
        'claude/bench/test_sphere.py','codex/scripts/animate.py']:
        source(rel)
    native_models();tracks=ephemerides()
    comet=comet_product(tracks);xray=xray_product();spacecraft=spacecraft_product()
    benchmarks=benchmark_product();remote=remote_product()
    if args.skip_animation:
        if (OUT/'science.json').exists():
            previous=json.loads((OUT/'science.json').read_text())
            animation=previous['animation']
            # Preserve original animation-source hashes when reusing its
            # cached fields. A changed source remains detectable by tests.
            for row in previous['provenance']:
                PROVENANCE.setdefault(row['path'],row)
        else:
            raise ValueError('--skip-animation requires an existing full product')
    else:
        animation=animation_product(tracks)
    result={'schemaVersion':1,
        'meta':{'title':'3I/ATLAS comparative heliospheric reconstruction','immutableSource':'../mhd_llm',
            'dateWindow':'2025-12-03–04','obsId':'0963720201','sourcePolicy':'Quantitative comparisons are extracted from unchanged archived runs. Claude’s finer-cadence animation is regenerated separately with unchanged numerical kernels and retained boundary inputs, using an output-only host hook; its verification is recorded in the animation provenance.',
            'rebuild':'python scripts/build_science.py','software':{'numpy':np.__version__,'pandas':pd.__version__}},
        'models':[{'id':'argon','name':'Argon','reference':'res_fine_224x48x240'},
                  {'id':'codex','name':'Codex','reference':'ct156_w30_theta40_phi192'},
                  {'id':'claude','name':'Claude','reference':'prod_da3_ccmc_prod_t4_L1ref_L2'}],
        'comet':comet,'xray':xray,'validation':{'spacecraft':spacecraft,'remote':remote},
        'benchmarks':benchmarks,'animation':animation,'provenance':list(PROVENANCE.values()),
        'homogenization':{'units':'Proton number density cm⁻³; speed km s⁻¹; proton flux cm⁻² s⁻¹; all time axes MJD UTC.',
            'missingData':'JSON null; animation encoding 0. Never extrapolated or replaced with synthetic plasma.',
            'quality':'Spacecraft metrics use the same positive finite observed/model timestamps for all three final references. In-sample calibration is explicitly separated from benchmark verification and independent forecast accuracy.',
            'xray':'Common exact PN GTIs, photon-arrival UTC, exposure-weighted mean normalization. Counts are illustrative flux-driven shape proxies, not absolute SWCX predictions.',
            'nativeMeans':'Native report values may differ because clocks, GTI quadrature, resolutions and alpha corrections differ. The common exact-GTI table is recomputed from retained native outputs.',
            'knownInconsistencies':['Argon prose holdout metrics disagree with machine-readable summary_results.json; this application prioritizes native numeric files.',
                'Argon movie uses base160 while comet reference uses fine224; final Codex movie has no separate speed or density channels.',
                'Claude movie is radial n v_r, while Argon/Codex movies use n |v|. Native plane projection differences cannot be removed without new 3D output.']}}
    write('science.json',result)


if __name__=='__main__':
    main()
