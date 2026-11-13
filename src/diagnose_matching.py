
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree
from config import CLEAN, SEARCH_RADIUS_KM

EARTH_KM = 6371.0
KM_PER_DEG = 111.32

modis = pd.read_csv(
    CLEAN / "modis_clean.csv", parse_dates=["time_utc"]
)
viirs = pd.read_csv(
    CLEAN / "viirs_clean.csv", parse_dates=["time_utc"]
)

print("MODIS:", len(modis))
print("VIIRS:", len(viirs))

if modis.empty:
    raise ValueError("MODIS dataset is empty")

tree = BallTree(
    np.radians(modis[["latitude", "longitude"]].to_numpy()),
    metric="haversine"
)

v_xy = np.radians(
    viirs[["latitude", "longitude"]].to_numpy()
)

candidates = tree.query_radius(
    v_xy, r=SEARCH_RADIUS_KM / EARTH_KM
)

m_lat = modis.latitude.to_numpy()
m_lon = modis.longitude.to_numpy()
m_scan = modis.scan.to_numpy()
m_track = modis.track.to_numpy()

v_lat = viirs.latitude.to_numpy()
v_lon = viirs.longitude.to_numpy()

m_time = (
    modis.time_utc.to_numpy()
    .astype("datetime64[s]").astype("int64")
)
v_time = (
    viirs.time_utc.to_numpy()
    .astype("datetime64[s]").astype("int64")
)

spatial_count = 0
footprint_count = 0
nearest_time_gaps = []

thresholds = [10, 30, 60, 90, 120]
matches = {t: 0 for t in thresholds}

for i, idx in enumerate(candidates):

    if len(idx) == 0:
        continue

    spatial_count += 1

    dy = (v_lat[i] - m_lat[idx]) * KM_PER_DEG
    dx = (
        (v_lon[i] - m_lon[idx])
        * KM_PER_DEG
        * np.cos(np.radians(v_lat[i]))
    )

    distance = np.hypot(dx, dy)

    dt = np.abs(v_time[i] - m_time[idx]) / 60.0

    inside = (
        (np.abs(dx) <= m_scan[idx] / 2)
        & (np.abs(dy) <= m_track[idx] / 2)
    )

    if inside.any():
        footprint_count += 1
        nearest_time_gaps.append(float(dt[inside].min()))

        for t in thresholds:
            if np.any(inside & (dt <= t)):
                matches[t] += 1

print("\n========== SPATIAL DIAGNOSTICS ==========")
print("VIIRS with MODIS candidate within radius:",
      spatial_count)
print("VIIRS inside MODIS pixel approximation:",
      footprint_count)

print("\n========== TIME GAP INSIDE FOOTPRINT ==========")

if nearest_time_gaps:
    gaps = np.array(nearest_time_gaps)

    print("Median time gap:",
          round(float(np.median(gaps)), 2), "minutes")

    for t in thresholds:
        count = matches[t]
        print(
            f"Within {t:3} minutes: "
            f"{count:,} "
            f"({count / len(viirs) * 100:.2f}%)"
        )
else:
    print("No spatial footprint candidates found.")

print("\n========== FINAL ==========")
print("Search radius:", SEARCH_RADIUS_KM, "km")
print("MODIS pixel approximation: scan x track")
print("Time thresholds:", thresholds)
