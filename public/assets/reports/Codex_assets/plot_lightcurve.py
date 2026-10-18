"""Draw the report figure from the copied, frozen eight-frame benchmark."""
from datetime import datetime, timezone
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
rows = json.loads((ROOT / "manuscript_benchmark.json").read_text())["rows"]
dates = [datetime.fromisoformat(row["midpoint_utc"]).replace(tzinfo=timezone.utc)
         for row in rows]
weights = np.array([row["gti_s"] for row in rows])
rates = np.array([row["pn_rate_ct_s"] for row in rows])
errors = np.array([row["pn_error_ct_s"] for row in rows])
flux = np.array([row["f_incident"] for row in rows])
rate_mean = np.average(rates, weights=weights)
flux_mean = np.average(flux, weights=weights)

with plt.rc_context({"font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False}):
    fig, ax = plt.subplots(figsize=(8.2, 3.8), layout="constrained")
    ax.plot(dates, flux / flux_mean, "o-", color="#1765a8", lw=2,
            label="Model incident proton flux", zorder=2)
    ax.errorbar(dates, rates / rate_mean, yerr=errors / rate_mean,
                fmt="o", color="#754db0", capsize=3, markersize=6,
                label="EPIC-pn count rate", zorder=3)
    ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 4, 8, 12, 16, 20]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b\n%H:%M", tz=timezone.utc))
    ax.set_xlabel("Photon-arrival UTC, 2025")
    ax.set_ylabel("Each series / its own\nexposure-weighted mean")
    ax.set_ylim(0, 2.05)
    ax.grid(axis="y", color="#dfe4e8", lw=0.8)
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    fig.savefig(ROOT / "lightcurve_comparison.png", dpi=180)
    plt.close(fig)
