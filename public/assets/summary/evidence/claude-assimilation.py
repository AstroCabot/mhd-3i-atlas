import copy
import json

import numpy as np
import pandas as pd

import inputs as I
import run_helio as R


def kernel_field(lat, lon, slon, slat, val, wgt, sig_lon, sig_lat, w0):
    LA, LO = np.meshgrid(lat, lon, indexing="ij")
    num = np.zeros_like(LA)
    den = np.zeros_like(LA)
    for a, b, v, w in zip(slon, slat, val, wgt):
        dl = (LO - a + 180) % 360 - 180
        k = w * np.exp(-0.5 * (dl / sig_lon) ** 2 - 0.5 * ((LA - b) / sig_lat) ** 2)
        num += k * v
        den += k
    return num / (den + w0), den


def residuals(pr, bodies, t0, t1, skip_hours=0, obs_override=None):
    rows = []
    a, b = I.tsec(t0), I.tsec(t1)
    for bd in bodies:
        obs = obs_override[bd] if obs_override else R.insitu_hourly(R.SC_INSITU[bd])
        obs = obs[(obs.t >= a) & (obs.t <= b)].dropna(subset=["n", "v"])
        m = pr[bd]
        if "src_lon" not in m:
            raise RuntimeError("trace build required")
        ok = np.isfinite(m.v.to_numpy())
        mt = m.t.to_numpy()[ok]
        if ok.sum() < 10:
            continue
        g = lambda k: np.interp(obs.t, mt, m[k].to_numpy()[ok])
        cs, sn = g("src_cos"), g("src_sin")
        rows.append(pd.DataFrame({"body": bd, "t": obs.t.to_numpy(), "v_obs": obs.v.to_numpy(), "n_obs": obs.n.to_numpy(), "v_mod": g("v"), "n_mod": g("n"),
                                  "src_lon": np.degrees(np.arctan2(sn, cs)) % 360, "src_lat": g("src_lat"), "t_emit": g("t_emit")}))
    return pd.concat(rows, ignore_index=True)


def apply(maps, cv, cn):
    out = []
    for k, m in enumerate(maps):
        m2 = dict(m)
        a = cv[k] if cv.ndim == 3 else cv
        b = cn[k] if cn.ndim == 3 else cn
        m2["dv_corr"] = a.astype(np.float32)
        m2["n_fac"] = np.exp(b).astype(np.float32)
        out.append(m2)
    return out


def field_t(maps, rs, val, sig_lon, sig_lat, sig_t, w0):
    lat, lon = maps[0]["lat"], maps[0]["lon"]
    out = np.zeros((len(maps), len(lat), len(lon)))
    for k, m in enumerate(maps):
        w = np.exp(-0.5 * ((rs.t_emit.to_numpy() - m["t_s"]) / (sig_t * 86400)) ** 2)
        keep = w > 1e-3
        out[k], _ = kernel_field(lat, lon, rs.src_lon.to_numpy()[keep], rs.src_lat.to_numpy()[keep], np.asarray(val)[keep], w[keep], sig_lon, sig_lat, w0)
    return out


def assimilate(tag, maps, rule, bodies, t0="2025-11-12", t1="2025-12-08", n_iter=5, res="L0", relax_v=0.8, relax_n=0.6, sig_lon=4.0, sig_lat=8.0, sig_lon_n=8.0, w0=3.0,
               t_start="2025-10-25T00:00", t_end="2025-12-09T00:00", cme=True, density=True, log=None, extra=None, init_corr=None, sig_t=0.0, obs_override=None):
    lat, lon = maps[0]["lat"], maps[0]["lon"]
    shape = (len(maps), len(lat), len(lon)) if sig_t > 0 else (len(lat), len(lon))
    cv = np.zeros(shape)
    cn = np.zeros(shape)
    if init_corr:
        z = np.load(init_corr)
        cv, cn = z["cv"].copy(), z["cn"].copy()
    hist = []
    for it in range(n_iter + 1):
        if (R.RUNS / "STOP").exists() or (R.RUNS / f"STOP_{tag}").exists():
            break
        wd = R.build(f"{tag}_it{it}", apply(maps, cv, cn), rule, res=res, t_start=t_start, t_end=t_end, cme=cme, extra=extra)
        rc, el = R.run(wd, trace=True)
        pr = R.probes(wd)
        sc = R.score(pr, t0, t1, bodies=("earth", "stereo_a", "solar_orbiter"), obs_override=obs_override)
        cs = R.comet_stats(pr)
        sc_all = R.score(pr, t0, t1, bodies=("earth", "stereo_a", "solar_orbiter", "mars"), obs_override=obs_override)
        hist.append({"iter": it, "wall_s": el, "score": sc_all, "comet": {k: cs[k]["gti_mean"] for k in ("n", "v", "flux", "flux_rel")}})
        if log:
            log(f"{tag} it{it} wall {el:.0f}s " + " ".join(f"{b}:rmse={v['v_rmse']:.0f},nr={v['n_med_ratio']:.2f}" for b, v in sc.items()) + f" comet n={cs['n']['gti_mean']:.2f} v={cs['v']['gti_mean']:.0f}")
        if it == n_iter:
            break
        rs = residuals(pr, bodies, t0, t1, obs_override=obs_override)
        rs = rs[np.isfinite(rs.v_mod) & np.isfinite(rs.n_mod) & np.isfinite(rs.src_lat)]
        dv = (rs.v_obs - rs.v_mod).to_numpy()
        dn = np.log(rs.n_obs / rs.n_mod).to_numpy()
        if sig_t > 0:
            fv = field_t(maps, rs, dv, sig_lon, sig_lat, sig_t, w0)
            fn = field_t(maps, rs, dn, sig_lon_n, sig_lat, sig_t, w0) if density else 0.0
        else:
            fv, _ = kernel_field(lat, lon, rs.src_lon, rs.src_lat, dv, np.ones(len(rs)), sig_lon, sig_lat, w0)
            fn = kernel_field(lat, lon, rs.src_lon, rs.src_lat, dn, np.ones(len(rs)), sig_lon_n, sig_lat, w0)[0] if density else 0.0
        cv = cv + relax_v * fv
        if density:
            cn = np.clip(cn + relax_n * fn, np.log(1 / 4), np.log(4))
    np.savez(R.RUNS / f"{tag}_corr.npz", lat=lat, lon=lon, cv=cv, cn=cn)
    (R.RUNS / f"{tag}_hist.json").write_text(json.dumps(hist, indent=1))
    return wd, pr, cv, cn, hist
