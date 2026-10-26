#!/usr/bin/env python3
"""Rebuild the report's matched spacecraft comparison from read-only originals.

Run: python -B mhd_agent_report/derive_validation.py
Requires numpy. Only writes matched_monitor_* files inside this report's derived/.
Does not import project modules, execute simulations, download data, or alter inputs.
"""

import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import struct

import numpy as np

REPORT = Path(__file__).resolve().parent
ROOT = REPORT.parent
OUT = REPORT / "derived"
PROBES = ("wind", "stereo_a")
WINDOWS = {
    "Dec1_to_Dec5_00UTC": (61010.0, 61014.0),
    "science_interval": (61012 + 43447 / 86400, 61013 + 36714 / 86400),
}


def main():
    sources, models, labels, model_sources = {}, {}, {}, {}

    def source(path, description, columns, model=None):
        p = ROOT / path
        content = p.read_bytes()
        sources[path] = dict(
            path=path, sha256=hashlib.sha256(content).hexdigest(), bytes=len(content),
            description=description, columns_and_time=columns,
        )
        if model:
            model_sources.setdefault(model, []).append(path)
        return p

    def readcsv(path, description, columns, model=None, delimiter=","):
        with source(path, description, columns, model).open(newline="") as f:
            return list(csv.DictReader(f, delimiter=delimiter))

    def put(name, probe, t, n, v, label):
        a = np.column_stack((t, n, v)).astype(float)
        a = a[np.argsort(a[:, 0])]
        assert np.all(np.diff(a[:, 0]) > 0), (name, probe, "duplicate model epochs")
        assert np.all(np.isfinite(a)) and np.all(a[:, 1:] > 0), (name, probe)
        models[name, probe] = np.column_stack((a, a[:, 1] * a[:, 2] * 1e5))
        labels[name, probe] = label

    name = "collaborative_argon"
    rows = readcsv(
        "mhd_llm/argon/outputs/runs/res_fine_224x48x240_probes.tsv",
        "Selected fine model3 output", "mjd_utc; probe; n_cm3; vmag_kms", name, "\t",
    )
    for probe in PROBES:
        z = [r for r in rows if r["probe"] == probe]
        put(name, probe, [r["mjd_utc"] for r in z], [r["n_cm3"] for r in z],
            [r["vmag_kms"] for r in z], "Assimilated nominal: in-sample observational reconstruction")

    name = "collaborative_claude"
    path = source(
        "mhd_llm/claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2/probes.bin",
        "Selected one-degree nominal",
        "Little-endian int32 nb,nf header; each record float64 seconds since2025-10-01UTC followed by float32[nb,nf]; body1earth,body2stereo_a; fields0n,1vr,2vt,3vp; cm^-3 and km/s",
        name,
    )
    with path.open("rb") as f:
        nb, nf = struct.unpack("<2i", f.read(8))
        raw = f.read()
    record_bytes = 8 + 4 * nb * nf
    assert len(raw) % record_bytes == 0
    buf = np.frombuffer(raw, np.uint8).reshape(-1, record_bytes)
    times = buf[:, :8].copy().view("<f8").ravel() / 86400 + 60949
    values = buf[:, 8:].copy().view("<f4").reshape(-1, nb, nf).astype(float)
    for probe, i in (("wind", 1), ("stereo_a", 2)):
        label = "Assimilated nominal: in-sample observational reconstruction"
        if probe == "wind":
            label += "; Earth trajectory for Wind"
        put(name, probe, times, values[:, i, 0], np.linalg.norm(values[:, i, 1:4], axis=1), label)

    name = "collaborative_codex"
    rows = readcsv(
        "mhd_llm/codex/results/ct156_w30_theta40_phi192/probe.csv",
        "Selected native CT solution",
        "day since2025-11-01UTC=MJD60980; probe_id1Wind,2STEREO-A; n_cm3; speed_kms", name,
    )
    for probe, i in (("wind", 1), ("stereo_a", 2)):
        z = [r for r in rows if int(float(r["probe_id"])) == i]
        label = ("Wind excluded from scalar calibration; descriptive validation" if probe == "wind"
                 else "Post-calibration temporal comparison; scalar source calibration used earlier STEREO-A")
        put(name, probe, [float(r["day"]) + 60980 for r in z], [r["n_cm3"] for r in z],
            [r["speed_kms"] for r in z], label)

    name = "competitive_argon"
    rows = readcsv(
        "mhd_llm_adversarial/argon/results/ts_argon_high.csv", "Selected high-grid model",
        "mjd_utc; wind_np,wind_vmag; stereo_a_np,stereo_a_vmag", name,
    )
    for probe in PROBES:
        put(name, probe, [r["mjd_utc"] for r in rows], [r[probe + "_np"] for r in rows],
            [r[probe + "_vmag"] for r in rows], "Assimilated/conditioned nominal: in-sample reconstruction")

    name = "competitive_claude"
    for probe, body in (("wind", "earth"), ("stereo_a", "stereo_a")):
        rows = readcsv(
            f"mhd_llm_adversarial/claude/runs/p2_med_d/probes/{body}.csv", "Selected nominal p2_med_d",
            "t_sec since2025-10-01UTC=MJD60949; n; vmag", name,
        )
        label = "Assimilated nominal, not leave-one-out: in-sample"
        if probe == "wind":
            label += "; Earth/OMNI trajectory proxy for Wind"
        put(name, probe, [float(r["t_sec"]) / 86400 + 60949 for r in rows],
            [r["n"] for r in rows], [r["vmag"] for r in rows], label)

    name = "competitive_codex"
    rows = readcsv(
        "mhd_llm_adversarial/codex/outputs/runs/nominal_full48_coupled224/samples.csv", "Selected nominal224",
        "time_day since2025-12-01UTC=MJD61010; target earth,stereo_a; n_cm3; speed_kms", name,
    )
    for probe, body in (("wind", "earth"), ("stereo_a", "stereo_a")):
        z = [r for r in rows if r["target"] == body]
        label = ("Wind excluded from fitting, but model selected after validation; Earth trajectory proxy"
                 if probe == "wind" else "Post-cutoff temporal holdout, but model selected after validation")
        put(name, probe, [float(r["time_day"]) + 61010 for r in z], [r["n_cm3"] for r in z],
            [r["speed_kms"] for r in z], label)

    name = "nasa_ccmc_ambient"
    for probe, body in (("wind", "earth"), ("stereo_a", "stereoa")):
        path = source(
            f"mhd_llm_adversarial/codex/data/solar/evo_{body}2amb_20251001T00.dat",
            "Actual archived NASA CCMC Jan_Deca_120925_SH_1 ambient",
            "Whitespace columns0MJD,5N,7:10Vr/Vt/Vn(km/s); use unscaled N proton-density proxy; MJD rather than rounded UTC text", name,
        )
        data = []
        for line in path.read_text().splitlines():
            if not line or line.startswith("#"):
                continue
            z = line.split()
            data.append((float(z[0]), float(z[5]), np.linalg.norm(np.array(z[7:10], float))))
        a = np.array(data)
        label = "Independent retrospective comparison; archived N is proton-density proxy with unresolved alpha convention"
        if probe == "wind":
            label += "; Earth trajectory proxy for Wind"
        put(name, probe, a[:, 0], a[:, 1], a[:, 2], label)

    order = list(dict.fromkeys(k[0] for k in models)) + ["persistence_24h"]
    coverage, paired, table = {}, [], []
    for probe in PROBES:
        path = f"mhd_llm_adversarial/codex/data/observations/{probe}.csv"
        rows = readcsv(path, "Fixed common native hourly reference curated from archived HAPI/preprint observations",
                       "utc,mjd_utc,density_cm3,speed_kms; positive finite n and speed; no smoothing/rescaling")
        model_sources.setdefault("persistence_24h", []).append(path)
        rows = [r for r in rows if all(np.isfinite(float(r[k])) and float(r[k]) > 0
                                      for k in ("density_cm3", "speed_kms"))]
        t, n, v = (np.array([float(r[k]) for r in rows]) for k in ("mjd_utc", "density_cm3", "speed_kms"))
        utc = np.array([r["utc"] for r in rows])
        before = (t >= 61009) & (t < 61010)
        pn, pv = float(np.median(n[before])), float(np.median(v[before]))
        put("persistence_24h", probe, [61009, 61014], [pn, pn], [pv, pv],
            "Precutoff24h median density and speed, held fixed; no fit to evaluation interval")
        requested = (t >= 61010) & (t < 61014)
        supported = requested.copy()
        for name in order:
            s = models[name, probe]
            supported &= (t >= s[0, 0]) & (t <= s[-1, 0])
        assert supported.sum() == 96, (probe, supported.sum())
        coverage[probe] = dict(
            native_valid_slots_in_requested_interval=int(requested.sum()), shared_valid_slots=int(supported.sum()),
            first_utc=utc[supported][0], last_utc=utc[supported][-1], excluded_utc=utc[requested & ~supported].tolist(),
            reference_prior24h_count=int(before.sum()), persistence_n_cm3=pn, persistence_speed_kms=pv, models={},
        )
        ot, on, ov, ou = t[supported], n[supported], v[supported], utc[supported]
        of = on * ov * 1e5
        for name in order:
            s = models[name, probe]
            pred = np.column_stack([np.interp(ot, s[:, 0], s[:, j]) for j in (1, 2, 3)])
            coverage[probe]["models"][name] = dict(
                first_mjd=float(s[0, 0]), last_mjd=float(s[-1, 0]),
                median_cadence_seconds=float(np.median(np.diff(s[:, 0])) * 86400),
                maximum_cadence_seconds=float(np.max(np.diff(s[:, 0])) * 86400), validation_status=labels[name, probe],
            )
            for i in range(len(ot)):
                paired.append(dict(model=name, probe=probe, utc=ou[i], mjd_utc=ot[i],
                                   observed_density_cm3=on[i], observed_speed_kms=ov[i], observed_bulk_flux_cm2_s=of[i],
                                   model_density_cm3=pred[i, 0], model_speed_kms=pred[i, 1], model_bulk_flux_cm2_s=pred[i, 2]))
            for window, (start, stop) in WINDOWS.items():
                mask = (ot >= start) & (ot < stop)
                row = dict(window=window, model=name, probe=probe, N=int(mask.sum()),
                           first_utc=ou[mask][0], last_utc=ou[mask][-1], validation_status=labels[name, probe])
                for field, truth, j in (("density_cm3", on, 0), ("speed_kms", ov, 1), ("bulk_flux_cm2_s", of, 2)):
                    x, y = truth[mask], pred[mask, j]
                    e = y - x
                    row[field + "_rmse"] = float(np.sqrt(np.mean(e**2)))
                    row[field + "_bias"] = float(np.mean(e))
                    row[field + "_pearson_r"] = None if np.std(y) < 1e-10 or np.std(x) < 1e-10 else float(np.corrcoef(x, y)[0, 1])
                    row[field + "_median_model_observed_ratio"] = float(np.median(y / x))
                    row[field + "_mae"] = float(np.mean(abs(e)))
                table.append(row)

    definitions = {
        "mhd_llm/claude/src/py/heliopy.py": "Binary reader schema inspected without import",
        "mhd_llm/claude/src/py/inputs.py": "Binary body order and epoch",
        "mhd_llm/codex/inputs/probe_ids.json": "Collaborative Codex probe identities",
        "mhd_llm_adversarial/claude/src/py/ephem.py": "Competitive Claude epoch",
        "mhd_llm_adversarial/codex/scripts/validate_monitors.py": "External profile schema independently reimplemented",
    }
    for path, description in definitions.items():
        source(path, description, "Provenance definition only; not executed/imported")
    metadata = dict(
        created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        scope="Matched descriptive comparison of six selected nominal reconstructions, actual NASA ambient, and persistence; not a controlled predictive leaderboard.",
        requested_interval_utc=["2025-12-01T00:00:00Z", "2025-12-05T00:00:00Z"], interval_half_open=True,
        science_interval_utc=["2025-12-03T12:04:07Z", "2025-12-04T10:11:54Z"],
        method=[
            "One fixed hourly reference per probe; all eight predictions use exactly the same96timestamps.",
            "No observation interpolation,smoothing,rescaling,phase fitting,light-time correction,gap filling,or model extrapolation.",
            "Recompute native bulk speed from full3-vector where needed; native bulkflux=n*|v|*1e5. Independently linearly interpolate density,speed,and native bulkflux to observed timestamps; do not multiply separately interpolated primitives.",
            "Native physical spacecraft times converted to MJDUTC. NASA MJD retained instead of rounded minute UTC text.",
            "No ICME mask: all valid hourly samples in fixed interval, identical across models.",
            "Native Earth or Wind model positions preserved. Claude selected nominals assimilate evaluated data; these are not leave-one-out outputs.",
            "NASA N left unscaled and labeled proton-density proxy; alpha-aware ASCII conversion unresolved.",
            "Correlated hourly slots are not96independent tests; retrospective tuning/training differs across models.",
            "No original modules imported or simulations run. Only this report's derived artifacts written.",
        ],
        model_order=order, units=dict(density="cm^-3", speed="km/s", bulk_flux="cm^-2 s^-1"),
        coverage=coverage, sources=sources, native_model_source_paths=model_sources,
        reproduction=dict(script="mhd_agent_report/derive_validation.py", numpy_version=np.__version__,
                          command="python -B mhd_agent_report/derive_validation.py"),
    )
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, rows in (("matched_monitor_metrics.csv", table), ("matched_monitor_pairs.csv", paired)):
        with (OUT / filename).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (OUT / "matched_monitor_provenance.json").write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n")
    print(f"Wrote {len(table)} metric rows and {len(paired)} paired rows under {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
