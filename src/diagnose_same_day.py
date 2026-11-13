
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from config import CLEAN, SEARCH_RADIUS_KM

EARTH_KM = 6371.0

modis = pd.read_csv(CLEAN / "modis_clean.csv")
viirs = pd.read_csv(CLEAN / "viirs_clean.csv")

modis["time_utc"] = pd.to_datetime(modis["time_utc"], utc=True)
viirs["time_utc"] = pd.to_datetime(viirs["time_utc"], utc=True)

print("MODIS:", len(modis))
print("VIIRS:", len(viirs))

tree = BallTree(
    np.radians(modis[["latitude", "longitude"]].values),
    metric="haversine"
)

v_coords = np.radians(
    viirs[["latitude", "longitude"]].values
)

radius = SEARCH_RADIUS_KM / EARTH_KM
candidate_lists = tree.query_radius(v_coords, r=radius)

nearest_gaps = []
same_day_count = 0
inside_count = 0

for i, candidates in enumerate(candidate_lists):
    if len(candidates) == 0:
        continue

    v = viirs.iloc[i]
    m = modis.iloc[candidates]

    dy = (v.latitude - m.latitude) * 111.32
    dx = (
        (v.longitude - m.longitude)
        * 111.32
        * np.cos(np.radians(v.latitude))
    )

    inside = (
        (np.abs(dx) <= m.scan.values / 2)
        & (np.abs(dy) <= m.track.values / 2)
    )

    m = m.iloc[np.where(inside)[0]]

    if len(m) == 0:
        continue

    inside_count += 1

    same_day = (
        m.time_utc.dt.date.values
        == v.time_utc.date()
    )

    m = m.iloc[np.where(same_day)[0]]

    if len(m) == 0:
        continue

    same_day_count += 1

    gaps = (
        (m.time_utc - v.time_utc)
        .abs()
        .dt.total_seconds()
        / 60
    )

    nearest_gaps.append(gaps.min())

print("\n========== SAME-DAY DIAGNOSTICS ==========")
print("VIIRS inside approximate MODIS footprint:", inside_count)
print("VIIRS with same-day footprint candidate:", same_day_count)

if nearest_gaps:
    gaps = np.array(nearest_gaps)

    print("Median same-day time gap:", round(np.median(gaps), 2), "minutes")

    for threshold in [5, 10, 15, 30, 45, 60]:
        count = np.sum(gaps <= threshold)
        print(
            f"Within {threshold:2} minutes: "
            f"{count} ({count / len(gaps) * 100:.2f}%)"
        )
else:
    print("No same-day footprint candidates found.")
