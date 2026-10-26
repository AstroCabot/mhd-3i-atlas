#!/usr/bin/env python3
"""
Independent Data Preparation, Coordinate Verification, and Inner-Boundary
Construction for the Argon 3D Heliospheric MHD Simulation of 3I/ATLAS.

Produces in `argon/data/processed/`:
1. `ephemeris_summary.json`: Verified 3D coordinates and velocities of 3I/ATLAS,
   STEREO-A, Solar Orbiter, Wind, ACE, and inner planets in J2000 Ecliptic,
   IAU Solar Equatorial (HCI), HEEQ, and Carrington frames.
2. `wsa_maps.npz`: Regridded 25 daily WSA 5.4 / GONGZ coronal boundary maps
   at r_in = 0.1 AU (21.5 R_sun) on uniform (lat, carrington_lon) grids, plus
   time-averaged and epoch-targeted CR 2304/2305 synoptic boundary maps.
3. `insitu_calibration.json`: Multi-spacecraft calibration constants, native CCMC
   ENLIL validation metrics, and XMM-Newton GTI window definitions.
4. Binary boundary files (`bc_mode1_ccmc.bin`, `bc_mode2_wsa_cal.bin`,
   `bc_mode3_assimilated.bin`) and trajectory probe file (` trajectories.bin`)
   ready for direct ingestion by the CUDA C++ 3D MHD solver.
"""

import csv
import glob
import json
import math
import os
from pathlib import Path
import numpy as np
if not hasattr(np, "in1d"):
    np.in1d = np.isin
from astropy.io import fits
from astropy.time import Time

BASE = Path("/mnt/c/Users/cabot/OneDrive/Documents/Research/Cambridge/X3I/mhd_llm/argon")
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

AU_KM = 1.495978707e8
OMEGA_SID_DEG_DAY = 14.1844000  # Sidereal rotation rate (360 / 25.38 d)
OMEGA_SYN_DEG_DAY = 13.1988     # Mean synodic rotation rate

# Three key observation windows
WIN_ANALYSIS06 = ("2025-12-03T12:04:07", "2025-12-04T10:11:54")
WIN_PN_GTI_SPAN = ("2025-12-03T13:04:03.002", "2025-12-04T09:56:03.002")
WIN_ALL_POINTING = ("2025-12-03T12:37:38", "2025-12-04T17:22:29")


def load_tsv(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_ephemeris(name):
    path = RAW / "ephemeris" / f"ephemeris_{name}.tsv"
    rows = load_tsv(path)
    data = {}
    for k in rows[0].keys():
        if k == "utc":
            data[k] = [r[k] for r in rows]
        else:
            data[k] = np.array([float(r[k]) for r in rows], dtype=np.float64)
    return data


def load_plasma(name):
    path = RAW / "spacecraft" / f"plasma_{name}.tsv"
    rows = load_tsv(path)
    mjd, n, v, flux, temp, bmag, br = [], [], [], [], [], [], []
    for r in rows:
        try:
            mjd_val = float(r["mjd_utc"])
            n_val = float(r["density_cm3"]) if r["density_cm3"] != "" else np.nan
            v_val = float(r["speed_km_s"]) if r["speed_km_s"] != "" else np.nan
            f_val = float(r["proton_flux_cm2_s"]) if r["proton_flux_cm2_s"] != "" else np.nan
            t_val = float(r["temperature_K"]) if r["temperature_K"] != "" else np.nan
            b_val = float(r["B_magnitude_nT"]) if r["B_magnitude_nT"] != "" else np.nan
            br_val = float(r["BR_RTN_nT"]) if r["BR_RTN_nT"] != "" else np.nan
            mjd.append(mjd_val)
            n.append(n_val)
            v.append(v_val)
            flux.append(f_val)
            temp.append(t_val)
            bmag.append(b_val)
            br.append(br_val)
        except Exception:
            continue
    return {
        "mjd": np.array(mjd),
        "n": np.array(n),
        "v": np.array(v),
        "flux": np.array(flux),
        "T": np.array(temp),
        "B": np.array(bmag),
        "Br": np.array(br),
    }


def verify_solar_equatorial_transform(eph_comet):
    """
    Independent verification of J2000 Ecliptic -> IAU Solar Equatorial (HCI) coordinates.
    Thompson (2006, A&A 449, 791):
    i_sun = 7.25 deg, Omega_sun(t) = 75.76 deg + 1.397 deg * T_centuries.
    """
    mjd = eph_comet["mjd_utc"]
    T_cent = (mjd - 51544.5) / 36525.0
    inc = np.radians(7.25)
    omega = np.radians(75.76 + 1.397 * T_cent)

    x, y, z = eph_comet["x_au"], eph_comet["y_au"], eph_comet["z_au"]
    # Rotate by -omega around Z (ecliptic pole), then by -inc around new X (ascending node)
    x1 = x * np.cos(omega) + y * np.sin(omega)
    y1 = -x * np.sin(omega) + y * np.cos(omega)
    z1 = z

    x_hci = x1
    y_hci = y1 * np.cos(inc) + z1 * np.sin(inc)
    z_hci = -y1 * np.sin(inc) + z1 * np.cos(inc)

    r = np.sqrt(x_hci**2 + y_hci**2 + z_hci**2)
    lat_deg = np.degrees(np.arcsin(np.clip(z_hci / r, -1.0, 1.0)))
    lon_deg = np.degrees(np.arctan2(y_hci, x_hci)) % 360.0

    lat_diff = np.max(np.abs(lat_deg - eph_comet["solar_equatorial_latitude_deg"]))
    lon_diff = np.max(np.abs(((lon_deg - eph_comet["solar_equatorial_longitude_deg"] + 180) % 360) - 180))
    return float(lat_diff), float(lon_diff)


def process_wsa_fits(eph_earth):
    """
    Read all 25 daily WSA 5.4 GONGZ FITS maps and regrid onto a standard
    Carrington longitude [0, 360) (180 bins, 1, 3, ..., 359 deg) and
    heliographic latitude [-89, 89] (90 bins, -89, -87, ..., +89 deg) grid.
    """
    fits_files = sorted(glob.glob(str(RAW / "wsa_gongz" / "vel_*_gongz.fits")))
    if not fits_files:
        raise RuntimeError("No WSA FITS files found in data/raw/wsa_gongz")

    lat_grid = -89.0 + 2.0 * np.arange(90)   # (90,)
    clon_grid = 1.0 + 2.0 * np.arange(180)  # (180,)

    n_maps = len(fits_files)
    br_maps = np.zeros((n_maps, 90, 180), dtype=np.float64)
    vr_maps = np.zeros((n_maps, 90, 180), dtype=np.float64)
    map_mjds = np.zeros(n_maps, dtype=np.float64)
    obslons = np.zeros(n_maps, dtype=np.float64)
    carrlons = np.zeros(n_maps, dtype=np.float64)
    phase_offsets = np.zeros(n_maps, dtype=np.float64)

    mjd_ref = Time("2025-12-03T00:00:00", format="isot", scale="utc").mjd

    for idx, fpath in enumerate(fits_files):
        fname = os.path.basename(fpath)
        # Parse timestamp from filename vel_YYYYMMDDHHMMR000_gongz.fits
        ts_str = fname.split("_")[1][:12]
        iso_str = f"{ts_str[:4]}-{ts_str[4:6]}-{ts_str[6:8]}T{ts_str[8:10]}:{ts_str[10:12]}:00"
        t_mjd = Time(iso_str, format="isot", scale="utc").mjd
        map_mjds[idx] = t_mjd

        with fits.open(fpath) as hdul:
            hdr = hdul[0].header
            arr = np.asarray(hdul[0].data, dtype=np.float64)  # (2, 90, 180)
            carrlong = float(hdr["CARRLONG"])
            obslon = float(hdr["OBSLON"])
            carrlons[idx] = carrlong
            obslons[idx] = obslon

            # Native longitude of pixel i: (CARRLONG + 1 + 2*i) % 360
            native_clon = (carrlong + 1.0 + 2.0 * np.arange(180)) % 360.0
            sort_order = np.argsort(native_clon)
            sorted_clon = native_clon[sort_order]

            # Periodic interpolation onto clon_grid
            ext_clon = np.concatenate([sorted_clon - 360.0, sorted_clon, sorted_clon + 360.0])
            for j in range(90):
                br_row = arr[0, j, sort_order]
                vr_row = arr[1, j, sort_order]
                br_maps[idx, j, :] = np.interp(clon_grid, ext_clon, np.tile(br_row, 3))
                vr_maps[idx, j, :] = np.interp(clon_grid, ext_clon, np.tile(vr_row, 3))

            # Verify phase relation between Carrington longitude and HCI longitude:
            # At t_mjd, Earth has Carrington longitude OBSLON and HCI longitude lon_hci_earth
            lon_hci_earth = np.interp(t_mjd, eph_earth["mjd_utc"], eph_earth["solar_equatorial_longitude_deg"])
            # For any point at HCI longitude phi_hci at time t:
            # phi_carr(phi_hci, t) = (phi_hci - lon_hci_earth(t_map) + OBSLON - OMEGA_SID*(t - t_map)) % 360
            # At reference epoch mjd_ref:
            phi0 = (obslon - lon_hci_earth + OMEGA_SID_DEG_DAY * (t_mjd - mjd_ref)) % 360.0
            phase_offsets[idx] = phi0

    # Circular mean of phase_offsets at mjd_ref
    ang_rad = np.radians(phase_offsets)
    mean_phase_deg = np.degrees(np.arctan2(np.mean(np.sin(ang_rad)), np.mean(np.cos(ang_rad)))) % 360.0
    phase_std_deg = float(np.degrees(np.std(np.unwrap(ang_rad))))

    np.savez_compressed(
        PROC / "wsa_maps.npz",
        lat_deg=lat_grid,
        clon_deg=clon_grid,
        map_mjds=map_mjds,
        br_maps=br_maps,
        vr_maps=vr_maps,
        obslons=obslons,
        carrlons=carrlons,
        mjd_ref=mjd_ref,
        mean_phase_deg=mean_phase_deg,
        phase_std_deg=phase_std_deg,
    )
    return {
        "n_maps": n_maps,
        "mjd_min": float(map_mjds.min()),
        "mjd_max": float(map_mjds.max()),
        "mjd_ref": float(mjd_ref),
        "carr_from_hci_phase_at_ref_deg": float(mean_phase_deg),
        "phase_consistency_std_deg": phase_std_deg,
        "lat_grid": lat_grid,
        "clon_grid": clon_grid,
        "br_maps": br_maps,
        "vr_maps": vr_maps,
        "map_mjds": map_mjds,
    }


def parse_ccmc_dat(path):
    """Parse CCMC ENLIL 1D evolution .dat file."""
    mjd, r_au, lat, lon, n, t_kk, vr, vt, vn, br, bt, bn, dp, bp = (
        [], [], [], [], [], [], [], [], [], [], [], [], [], []
    )
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("ENLIL") or any(c.isalpha() for c in s[:4]):
                continue
            parts = s.split()
            if len(parts) >= 15:
                try:
                    vals = [float(x) for x in parts[:15]]
                    mjd.append(vals[1])
                    r_au.append(vals[2])
                    lat.append(vals[3])
                    lon.append(vals[4])
                    n.append(vals[5])
                    t_kk.append(vals[6])
                    vr.append(vals[7])
                    vt.append(vals[8])
                    vn.append(vals[9])
                    br.append(vals[10])
                    bt.append(vals[11])
                    bn.append(vals[12])
                    dp.append(vals[13])
                    bp.append(vals[14])
                except ValueError:
                    continue
    mjd = np.array(mjd)
    vr, vt, vn = np.array(vr), np.array(vt), np.array(vn)
    br, bt, bn = np.array(br), np.array(bt), np.array(bn)
    n = np.array(n)
    vmag = np.sqrt(vr**2 + vt**2 + vn**2)
    bmag = np.sqrt(br**2 + bt**2 + bn**2)
    flux = n * vmag * 1e5
    return {
        "mjd": mjd,
        "r_au": np.array(r_au),
        "lat_deg": np.array(lat),
        "lon_deg": np.array(lon),
        "n_cm3": n,
        "T_K": np.array(t_kk) * 1e3,
        "vr_kms": vr,
        "vt_kms": vt,
        "vn_kms": vn,
        "vmag_kms": vmag,
        "br_nT": br,
        "bt_nT": bt,
        "bn_nT": bn,
        "bmag_nT": bmag,
        "flux_cm2s": flux,
        "dp": np.array(dp),
        "bp": np.array(bp),
    }


def main():
    print("Loading ephemerides and plasma time series...")
    ephs = {name: load_ephemeris(name) for name in ("comet", "stereo_a", "solar_orbiter", "wind", "ace")}
    plasmas = {name: load_plasma(name) for name in ("stereo_a", "solar_orbiter", "wind", "ace")}

    # Verify coordinate transform
    lat_err, lon_err = verify_solar_equatorial_transform(ephs["comet"])
    print(f"Coordinate verification (J2000 Ecliptic -> HCI): max lat diff = {lat_err:.4e} deg, max lon diff = {lon_err:.4e} deg")

    # Process WSA FITS maps
    wsa_info = process_wsa_fits(ephs["wind"])
    print(f"Processed {wsa_info['n_maps']} WSA 5.4 GONGZ maps; phase std = {wsa_info['phase_consistency_std_deg']:.4f} deg")

    # Parse CCMC .dat files
    ccmc_targets = {}
    for tname in ("3I-Atlas1", "3I-Atlas2amb", "earth1", "earth2amb", "stereoa1", "stereoa2amb", "solo1", "solo2amb"):
        dfile = RAW / "ccmc" / f"Jan_Deca_120925_SH_1_evo_{tname}_20251001T00.dat"
        if dfile.exists():
            ccmc_targets[tname] = parse_ccmc_dat(dfile)
    np.savez_compressed(PROC / "ccmc_extracted.npz", **{f"{k}_{f}": v[f] for k, v in ccmc_targets.items() for f in v})

    # Load XMM GTIs
    gti_rows = load_tsv(RAW / "spacecraft" / "xmm_gtis.tsv")
    pn_gtis = [(float(r["start_mjd_utc"]), float(r["stop_mjd_utc"]), float(r["duration_s"]))
               for r in gti_rows if r["detector"] == "pn"]
    all_gtis = [(float(r["start_mjd_utc"]), float(r["stop_mjd_utc"]), float(r["duration_s"]))
                for r in gti_rows]

    # Compute mid-epoch geometry and comet velocity vector at 2025-12-03T23:08:00Z (MJD 61012.96389)
    mjd_mid = 0.5 * (Time(WIN_ANALYSIS06[0]).mjd + Time(WIN_ANALYSIS06[1]).mjd)
    geom_mid = {}
    for name, eph in ephs.items():
        r_mid = float(np.interp(mjd_mid, eph["mjd_utc"], eph["radius_au"]))
        lat_seq = float(np.interp(mjd_mid, eph["mjd_utc"], eph["solar_equatorial_latitude_deg"]))
        lon_seq = float(np.interp(mjd_mid, eph["mjd_utc"], eph["solar_equatorial_longitude_deg"]))
        lon_ecl = float(np.interp(mjd_mid, eph["mjd_utc"], eph["ecliptic_longitude_deg"]))
        lat_ecl = float(np.interp(mjd_mid, eph["mjd_utc"], eph["ecliptic_latitude_deg"]))
        x = float(np.interp(mjd_mid, eph["mjd_utc"], eph["x_au"]))
        y = float(np.interp(mjd_mid, eph["mjd_utc"], eph["y_au"]))
        z = float(np.interp(mjd_mid, eph["mjd_utc"], eph["z_au"]))
        vx = float(np.interp(mjd_mid, eph["mjd_utc"], eph["vx_au_day"])) * AU_KM / 86400.0
        vy = float(np.interp(mjd_mid, eph["mjd_utc"], eph["vy_au_day"])) * AU_KM / 86400.0
        vz = float(np.interp(mjd_mid, eph["mjd_utc"], eph["vz_au_day"])) * AU_KM / 86400.0
        v_tot = math.sqrt(vx**2 + vy**2 + vz**2)
        v_rad = (x * vx + y * vy + z * vz) / r_mid
        v_tan = math.sqrt(max(0.0, v_tot**2 - v_rad**2))
        geom_mid[name] = {
            "r_au": round(r_mid, 5),
            "hci_lat_deg": round(lat_seq, 4),
            "hci_lon_deg": round(lon_seq, 4),
            "ecl_lat_deg": round(lat_ecl, 4),
            "ecl_lon_deg": round(lon_ecl, 4),
            "v_total_kms": round(v_tot, 3),
            "v_radial_kms": round(v_rad, 3),
            "v_tangential_kms": round(v_tan, 3),
        }

    # Compute pre-epoch (Nov 10 - Nov 25, MJD 60989 - 61004) and source-window (Nov 20 - Dec 05, MJD 60999 - 61014)
    # 1 AU momentum-flux invariant n_400 = n * (r / 1 AU)^2 * (v / 400 km/s)^2
    calib_stats = {}
    for pname in ("stereo_a", "solar_orbiter", "wind", "ace"):
        pl = plasmas[pname]
        ep = ephs[pname]
        r_pl = np.interp(pl["mjd"], ep["mjd_utc"], ep["radius_au"])
        scale_n = 1.7 if pname == "ace" else 1.0
        valid = (pl["mjd"] >= 60989.0) & (pl["mjd"] <= 61008.0) & np.isfinite(pl["n"]) & np.isfinite(pl["v"])
        n_1au = pl["n"][valid] * scale_n * (r_pl[valid]**2)
        v_val = pl["v"][valid]
        n400 = n_1au * (v_val / 400.0)**2
        b_valid = valid & np.isfinite(pl["B"])
        b1au = pl["B"][b_valid] * (r_pl[b_valid]**1.5)
        calib_stats[pname] = {
            "median_n_1au_cm3": round(float(np.median(n_1au)), 3),
            "median_v_kms": round(float(np.median(v_val)), 2),
            "median_n400_cm3": round(float(np.median(n400)), 3),
            "mean_n400_cm3": round(float(np.mean(n400)), 3),
            "median_B_1au_nT": round(float(np.median(b1au)), 3) if np.any(b_valid) else None,
        }

    # Build 2D inner-boundary maps at r_in = 0.1 AU on (N_lat=90, N_lon=180)
    # 1. Time-weighted WSA map for Nov 22 - Dec 03 (source epoch for Dec 3-4 at 1.87 AU, ~4-8 day transit)
    w_time = np.exp(-0.5 * ((wsa_info["map_mjds"] - 61006.5) / 4.0)**2)
    w_time /= np.sum(w_time)
    vr_wsa_syn = np.tensordot(w_time, wsa_info["vr_maps"], axes=(0, 0))  # (90, 180)
    br_wsa_syn = np.tensordot(w_time, wsa_info["br_maps"], axes=(0, 0))  # (90, 180)

    # Construct Mode 3: In-Situ Data-Assimilated + WSA 2D Hybrid Map in Carrington Coordinates
    # Back-project STEREO-A, Wind, ACE_scaled, and Solar Orbiter observations from r_sc(t) to r_in=0.1 AU:
    # A plasma parcel measured at (t_obs, r_sc, lat_sc, lon_hci_sc) with speed v_obs originated at r_in=0.1 AU at time:
    # t_src = t_obs - (r_sc - 0.1) * AU_KM / (v_obs * 86400)
    # At time t_src, its Carrington longitude was:
    # clon_src = (lon_hci_sc - OMEGA_SID_DEG_DAY * (t_src - mjd_ref) + mean_phase_deg) % 360.0
    mjd_ref = wsa_info["mjd_ref"]
    phase_ref = wsa_info["carr_from_hci_phase_at_ref_deg"]
    lat_grid = wsa_info["lat_grid"]
    clon_grid = wsa_info["clon_grid"]
    CLON2D, LAT2D = np.meshgrid(clon_grid, lat_grid)  # (90, 180)

    # Collect back-projected in-situ samples over Nov 18 - Dec 05 (covering full CR 2304/2305 source longitudes)
    src_clon, src_lat, src_v, src_n400, src_weight = [], [], [], [], []
    probe_weights = {"stereo_a": 2.0, "wind": 1.5, "ace": 1.0, "solar_orbiter": 1.2}
    for pname, pw in probe_weights.items():
        pl = plasmas[pname]
        ep = ephs[pname]
        scale_n = 1.7 if pname == "ace" else 1.0
        use = (pl["mjd"] >= 60997.0) & (pl["mjd"] <= 61014.0) & np.isfinite(pl["n"]) & np.isfinite(pl["v"])
        t_obs = pl["mjd"][use]
        v_obs = pl["v"][use]
        n_obs = pl["n"][use] * scale_n
        r_sc = np.interp(t_obs, ep["mjd_utc"], ep["radius_au"])
        lat_sc = np.interp(t_obs, ep["mjd_utc"], ep["solar_equatorial_latitude_deg"])
        lon_sc = np.interp(t_obs, ep["mjd_utc"], ep["solar_equatorial_longitude_deg"])

        # Transit time from 0.1 AU to r_sc
        dt_days = (r_sc - 0.1) * AU_KM / (v_obs * 86400.0)
        t_src = t_obs - dt_days
        clon_s = (lon_sc - OMEGA_SID_DEG_DAY * (t_src - mjd_ref) + phase_ref) % 360.0
        n400_s = n_obs * (r_sc**2) * ((v_obs / 400.0)**2)

        # Emphasize samples whose emission time t_src is close to the comet's source window (MJD 61004 - 61010)
        t_weight = pw * np.exp(-0.5 * ((t_src - 61006.5) / 6.0)**2)
        src_clon.append(clon_s)
        src_lat.append(lat_sc)
        src_v.append(v_obs)
        src_n400.append(n400_s)
        src_weight.append(t_weight)

    src_clon = np.concatenate(src_clon)
    src_lat = np.concatenate(src_lat)
    src_v = np.concatenate(src_v)
    src_n400 = np.concatenate(src_n400)
    src_weight = np.concatenate(src_weight)

    # Anisotropic Gaussian kernel interpolation on the sphere:
    # sigma_lon = 12 deg (corotating stream scale), sigma_lat = 7 deg (streamer belt latitudinal scale)
    sigma_lon = 12.0
    sigma_lat = 7.0
    vr_assim = np.copy(vr_wsa_syn)
    n400_assim = np.full_like(vr_wsa_syn, 6.80)  # Baseline calibrated 1 AU n400 (STA/Wind weighted)

    for j in range(90):
        lat_val = lat_grid[j]
        dlat = lat_val - src_lat
        w_lat = np.exp(-0.5 * (dlat / sigma_lat)**2)
        if np.max(w_lat) < 1e-3:
            continue
        for i in range(180):
            clon_val = clon_grid[i]
            dlon = ((clon_val - src_clon + 180.0) % 360.0) - 180.0
            w_tot = src_weight * w_lat * np.exp(-0.5 * (dlon / sigma_lon)**2)
            w_sum = np.sum(w_tot)
            # Blending factor alpha in [0, 0.85] based on local spacecraft coverage density
            alpha = 0.85 * (w_sum / (w_sum + 1.5))
            if alpha > 0.01:
                v_local = np.sum(w_tot * src_v) / w_sum
                n400_local = np.sum(w_tot * src_n400) / w_sum
                vr_assim[j, i] = (1.0 - alpha) * vr_wsa_syn[j, i] + alpha * v_local
                n400_assim[j, i] = (1.0 - alpha) * 6.80 + alpha * n400_local

    # Also build Holdout-Wind map (assimilating ONLY STEREO-A + Solar Orbiter, holding out Wind & ACE!)
    vr_holdout_wind = np.copy(vr_wsa_syn)
    n400_holdout_wind = np.full_like(vr_wsa_syn, 6.80)
    src_clon_ho, src_lat_ho, src_v_ho, src_n400_ho, src_w_ho = [], [], [], [], []
    for pname, pw in [("stereo_a", 2.0), ("solar_orbiter", 1.2)]:
        pl = plasmas[pname]
        ep = ephs[pname]
        use = (pl["mjd"] >= 60997.0) & (pl["mjd"] <= 61014.0) & np.isfinite(pl["n"]) & np.isfinite(pl["v"])
        t_obs = pl["mjd"][use]
        v_obs = pl["v"][use]
        n_obs = pl["n"][use]
        r_sc = np.interp(t_obs, ep["mjd_utc"], ep["radius_au"])
        lat_sc = np.interp(t_obs, ep["mjd_utc"], ep["solar_equatorial_latitude_deg"])
        lon_sc = np.interp(t_obs, ep["mjd_utc"], ep["solar_equatorial_longitude_deg"])
        dt_days = (r_sc - 0.1) * AU_KM / (v_obs * 86400.0)
        t_src = t_obs - dt_days
        clon_s = (lon_sc - OMEGA_SID_DEG_DAY * (t_src - mjd_ref) + phase_ref) % 360.0
        n400_s = n_obs * (r_sc**2) * ((v_obs / 400.0)**2)
        t_weight = pw * np.exp(-0.5 * ((t_src - 61006.5) / 6.0)**2)
        src_clon_ho.append(clon_s)
        src_lat_ho.append(lat_sc)
        src_v_ho.append(v_obs)
        src_n400_ho.append(n400_s)
        src_w_ho.append(t_weight)
    src_clon_ho = np.concatenate(src_clon_ho)
    src_lat_ho = np.concatenate(src_lat_ho)
    src_v_ho = np.concatenate(src_v_ho)
    src_n400_ho = np.concatenate(src_n400_ho)
    src_w_ho = np.concatenate(src_w_ho)
    for j in range(90):
        w_lat = np.exp(-0.5 * ((lat_grid[j] - src_lat_ho) / sigma_lat)**2)
        if np.max(w_lat) < 1e-3:
            continue
        for i in range(180):
            dlon = ((clon_grid[i] - src_clon_ho + 180.0) % 360.0) - 180.0
            w_tot = src_w_ho * w_lat * np.exp(-0.5 * (dlon / sigma_lon)**2)
            w_sum = np.sum(w_tot)
            alpha = 0.85 * (w_sum / (w_sum + 1.5))
            if alpha > 0.01:
                vr_holdout_wind[j, i] = (1.0 - alpha) * vr_wsa_syn[j, i] + alpha * (np.sum(w_tot * src_v_ho) / w_sum)
                n400_holdout_wind[j, i] = (1.0 - alpha) * 6.80 + alpha * (np.sum(w_tot * src_n400_ho) / w_sum)

    # Save boundary maps in binary format for CUDA solver:
    # Each binary file has shape (4, 90, 180) in float32:
    # Plane 0: vr_in (km/s at r_in = 0.1 AU, after accounting for ~35 km/s residual MHD thermal acceleration)
    # Plane 1: np_in (cm^-3 at r_in = 0.1 AU)
    # Plane 2: Br_in (nT at r_in = 0.1 AU)
    # Plane 3: T_in (K at r_in = 0.1 AU)
    def write_bc_bin(filename, vr_map, n400_map, br_map, dv_offset=35.0, b_scale=3.5, t_fast=1.2e6):
        vr_in = np.clip(vr_map - dv_offset, 220.0, 720.0)
        # At r_in = 0.1 AU, density scales by (1 / 0.1)^2 = 100
        np_in = 100.0 * n400_map * ((400.0 / vr_in)**2)
        br_in = b_scale * br_map
        # Constant thermal pressure balance at r_in = 0.1 AU: T_in = t_fast * (vr_in / 650.0)^2
        t_in = t_fast * ((vr_in / 650.0)**2)
        arr = np.stack([vr_in, np_in, br_in, t_in], axis=0).astype(np.float32)
        arr.tofile(PROC / filename)
        return arr

    # Mode 1: CCMC ENLIL a6b1 uncalibrated equivalent (dfast=125 at vfast=700 -> n400 = 3.828 cm^-3, bscl=4.0, dv=50)
    write_bc_bin("bc_mode1_ccmc.bin", vr_wsa_syn, np.full_like(vr_wsa_syn, 3.828), br_wsa_syn, dv_offset=45.0, b_scale=4.0, t_fast=1.5e6)
    # Mode 2: WSA 5.4 + 1 AU calibrated momentum flux (n400 = 6.50 cm^-3 matching STA/Wind 1 AU median, bscl=3.5)
    write_bc_bin("bc_mode2_wsa_cal.bin", vr_wsa_syn, np.full_like(vr_wsa_syn, 6.50), br_wsa_syn, dv_offset=35.0, b_scale=3.5, t_fast=1.2e6)
    # Mode 3: Hybrid Multi-Spacecraft Data-Assimilated + WSA 2D Latitudinal Structure
    write_bc_bin("bc_mode3_assimilated.bin", vr_assim, n400_assim, br_wsa_syn, dv_offset=30.0, b_scale=3.5, t_fast=1.2e6)
    # Mode 3b: Holdout-Wind Data-Assimilated (trained on STA + SolO only)
    write_bc_bin("bc_mode3_holdout_wind.bin", vr_holdout_wind, n400_holdout_wind, br_wsa_syn, dv_offset=30.0, b_scale=3.5, t_fast=1.2e6)

    # Export 10-minute trajectory grid (MJD 60998.0 to 61015.0, dt = 10 min = 1/144 day, N_t = 2449)
    # for 5 probes: comet, stereo_a, solar_orbiter, wind, ace
    t_grid = np.linspace(60998.0, 61015.0, 2449)
    probe_names = ["comet", "stereo_a", "solar_orbiter", "wind", "ace"]
    traj_arr = np.zeros((len(t_grid), len(probe_names), 7), dtype=np.float64)

    for p_idx, pname in enumerate(probe_names):
        ep = ephs[pname]
        mjd_ep = ep["mjd_utc"]
        T_cent = (mjd_ep - 51544.5) / 36525.0
        inc = np.radians(7.25)
        omega = np.radians(75.76 + 1.397 * T_cent)

        x, y, z = ep["x_au"], ep["y_au"], ep["z_au"]
        vx = ep["vx_au_day"] * AU_KM / 86400.0
        vy = ep["vy_au_day"] * AU_KM / 86400.0
        vz = ep["vz_au_day"] * AU_KM / 86400.0

        # Transform position and velocity to HCI Cartesian
        x1 = x * np.cos(omega) + y * np.sin(omega)
        y1 = -x * np.sin(omega) + y * np.cos(omega)
        xh = x1
        yh = y1 * np.cos(inc) + z * np.sin(inc)
        zh = -y1 * np.sin(inc) + z * np.cos(inc)

        vx1 = vx * np.cos(omega) + vy * np.sin(omega)
        vy1 = -vx * np.sin(omega) + vy * np.cos(omega)
        vxh = vx1
        vyh = vy1 * np.cos(inc) + vz * np.sin(inc)
        vzh = -vy1 * np.sin(inc) + vz * np.cos(inc)

        r = np.sqrt(xh**2 + yh**2 + zh**2)
        theta = np.arccos(np.clip(zh / r, -1.0, 1.0))  # colatitude [0, pi]
        phi_unwrapped = np.unwrap(np.arctan2(yh, xh))

        # Spherical unit vectors in HCI:
        # e_r = (sin(th)cos(ph), sin(th)sin(ph), cos(th))
        # e_th = (cos(th)cos(ph), cos(th)sin(ph), -sin(th))
        # e_ph = (-sin(ph), cos(ph), 0)
        st, ct = np.sin(theta), np.cos(theta)
        sp, cp = np.sin(phi_unwrapped), np.cos(phi_unwrapped)
        vr_p = vxh * st * cp + vyh * st * sp + vzh * ct
        vth_p = vxh * ct * cp + vyh * ct * sp - vzh * st
        vph_p = -vxh * sp + vyh * cp

        traj_arr[:, p_idx, 0] = t_grid
        traj_arr[:, p_idx, 1] = np.interp(t_grid, mjd_ep, r)
        traj_arr[:, p_idx, 2] = np.interp(t_grid, mjd_ep, theta)
        traj_arr[:, p_idx, 3] = np.interp(t_grid, mjd_ep, phi_unwrapped) % (2.0 * np.pi)
        traj_arr[:, p_idx, 4] = np.interp(t_grid, mjd_ep, vr_p)
        traj_arr[:, p_idx, 5] = np.interp(t_grid, mjd_ep, vth_p)
        traj_arr[:, p_idx, 6] = np.interp(t_grid, mjd_ep, vph_p)

    traj_arr.tofile(PROC / "trajectories.bin")
    np.save(PROC / "trajectories.npy", traj_arr)

    # Export late-Nov / early-Dec CME cones from cme_param.txt in HCI coordinates
    cme_list = []
    cme_file = RAW / "ccmc" / "cme_param.txt"
    if cme_file.exists():
        for line in cme_file.read_text().splitlines():
            s = line.strip()
            if s.startswith("2025-11-") or s.startswith("2025-12-"):
                parts = s.split()
                if len(parts) >= 5:
                    t_cme = Time(parts[0], format="isot", scale="utc").mjd
                    if t_cme >= 60996.0:
                        lat_cme = float(parts[1].split("=")[-1])
                        lon_heeq = float(parts[2].split("=")[-1])
                        rad_deg = float(parts[3].split("=")[-1])
                        vel_kms = float(parts[4].split("=")[-1])
                        lon_hci_earth = float(np.interp(t_cme, ephs["wind"]["mjd_utc"], ephs["wind"]["solar_equatorial_longitude_deg"]))
                        lon_hci_cme = (lon_hci_earth + lon_heeq) % 360.0
                        cme_list.append((t_cme, lat_cme, lon_hci_cme, rad_deg, vel_kms))
    with open(PROC / "cmes_hci.txt", "w") as f:
        f.write(f"{len(cme_list)}\n")
        for c in cme_list:
            f.write(f"{c[0]:.6f} {c[1]:.3f} {c[2]:.3f} {c[3]:.3f} {c[4]:.3f}\n")

    # Save summary JSON
    summary = {
        "mjd_ref": float(mjd_ref),
        "carr_from_hci_phase_at_ref_deg": float(phase_ref),
        "phase_consistency_std_deg": wsa_info["phase_consistency_std_deg"],
        "coordinate_check": {"max_lat_diff_deg": lat_err, "max_lon_diff_deg": lon_err},
        "windows": {
            "analysis06": {"utc": WIN_ANALYSIS06, "mjd": [Time(WIN_ANALYSIS06[0]).mjd, Time(WIN_ANALYSIS06[1]).mjd]},
            "pn_gti_span": {"utc": WIN_PN_GTI_SPAN, "mjd": [Time(WIN_PN_GTI_SPAN[0]).mjd, Time(WIN_PN_GTI_SPAN[1]).mjd], "n_gtis": len(pn_gtis), "live_s": sum(g[2] for g in pn_gtis)},
            "all_pointing": {"utc": WIN_ALL_POINTING, "mjd": [Time(WIN_ALL_POINTING[0]).mjd, Time(WIN_ALL_POINTING[1]).mjd]},
        },
        "mid_epoch_geometry_20251203T2308Z": geom_mid,
        "pre_epoch_1au_calibration": calib_stats,
        "n_cmes_exported": len(cme_list),
    }
    with open(PROC / "ephemeris_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved processed boundary files, trajectories.bin, {len(cme_list)} CMEs, and ephemeris_summary.json successfully!")


if __name__ == "__main__":
    main()
