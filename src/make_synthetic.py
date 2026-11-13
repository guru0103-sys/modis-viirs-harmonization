"""OFFLINE TEST DATA: develop and test the pipeline before the real download finishes.

Run:  python src/make_synthetic.py
Truth: VIIRS sees every fire; MODIS sees a fire with probability rising with FRP.
WARNING: delete data/raw/*.csv and re-download before producing any real result.
"""
import numpy as np
import pandas as pd

from config import RAW, REGION, MODIS_SOURCE, VIIRS_SOURCE, REGIONS

rng = np.random.default_rng(42)
w, s, e, n = REGIONS[REGION]
N = 6000
lat = rng.uniform(s, n, N)
lon = rng.uniform(w, e, N)
frp = rng.lognormal(mean=1.6, sigma=0.9, size=N)
t = pd.Timestamp("2024-10-10 08:00") + pd.to_timedelta(rng.integers(0, 40 * 24 * 60, N), unit="m")

v = pd.DataFrame({
    "latitude": lat + rng.normal(0, 0.0005, N), "longitude": lon + rng.normal(0, 0.0005, N),
    "bright_ti4": 330 + rng.normal(0, 8, N), "scan": rng.uniform(0.375, 0.7, N),
    "track": rng.uniform(0.375, 0.7, N), "acq_date": t.strftime("%Y-%m-%d"),
    "acq_time": (t.hour * 100 + t.minute).astype(int), "satellite": "N", "instrument": "VIIRS",
    "confidence": rng.choice(["l", "n", "h"], N, p=[0.1, 0.8, 0.1]), "version": "2.0NRT",
    "bright_ti5": 295.0, "frp": frp, "daynight": np.where(t.hour < 12, "D", "N"),
})
p_see = 1 / (1 + np.exp(-(np.log(frp) - np.log(8.0)) * 1.5))
seen = rng.random(N) < p_see
tm = t + pd.to_timedelta(rng.integers(-15, 15, N), unit="m")
m = pd.DataFrame({
    "latitude": lat + rng.normal(0, 0.002, N), "longitude": lon + rng.normal(0, 0.002, N),
    "brightness": 320 + rng.normal(0, 6, N), "scan": rng.uniform(1.0, 4.5, N),
    "track": rng.uniform(1.0, 2.0, N), "acq_date": tm.strftime("%Y-%m-%d"),
    "acq_time": (tm.hour * 100 + tm.minute).astype(int), "satellite": "Aqua", "instrument": "MODIS",
    "confidence": rng.integers(30, 100, N), "version": "6.1NRT", "bright_t31": 300.0,
    "frp": frp * rng.uniform(0.8, 1.4, N), "daynight": np.where(tm.hour < 12, "D", "N"),
})[seen]
k = 150
fa = m.sample(k, random_state=1).copy()
fa["latitude"] = rng.uniform(s, n, k); fa["longitude"] = rng.uniform(w, e, k)
m = pd.concat([m, fa], ignore_index=True)

RAW.mkdir(parents=True, exist_ok=True)
m.to_csv(RAW / f"{MODIS_SOURCE}_{REGION}.csv", index=False)
v.to_csv(RAW / f"{VIIRS_SOURCE}_{REGION}.csv", index=False)
print(f"synthetic MODIS {len(m):,} rows, VIIRS {len(v):,} rows; true MODIS detection rate ~{seen.mean():.1%}")
