
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from config import CLEAN, SEARCH_RADIUS_KM

EARTH_KM = 6371.0

modis = pd.read_csv(CLEAN / "modis_clean.csv")
viirs = pd.read_csv(CLEAN / "viirs_clean.csv")

modis["time_utc"] = pd.to_datetime(modis["time_utc"])
viirs["time_utc"] = pd.to_datetime(viirs["time_utc"])

tree = BallTree(
    np.radians(modis[["latitude", "longitude"]].values),
    metric="haversine"
)

candidates = tree.query_radius(
    np.radians(viirs[["latitude", "longitude"]].values),
    r=SEARCH_RADIUS_KM / EARTH_KM
)

thresholds = [5, 10, 15, 30, 45, 60]

print("\nTIME THRESHOLD SENSITIVITY")
print("-" * 75)
print(
    f"{'Minutes':<12}{'VIIRS matched':<17}"
    f"{'Unique MODIS':<17}{'Median distance':<18}"
)

for threshold in thresholds:
    matched_viirs = 0
    matched_modis = set()
    distances = []

    for i, indices in enumerate(candidates):
        if len(indices) == 0:
            continue

        v = viirs.iloc[i]
        m = modis.iloc[indices]

        dx = (
            (v.longitude - m.longitude)
            * 111.32
            * np.cos(np.radians(v.latitude))
        )

        dy = (v.latitude - m.latitude) * 111.32

        inside = (
            (np.abs(dx) <= m.scan.values / 2)
            & (np.abs(dy) <= m.track.values / 2)
        )

        if not inside.any():
            continue

        m = m.iloc[np.where(inside)[0]]

        time_gap = (
            (m.time_utc - v.time_utc)
            .abs()
            .dt.total_seconds()
            / 60
        )

        valid = time_gap <= threshold

        if not valid.any():
            continue

        m = m.iloc[np.where(valid)[0]]

        dlat = (v.latitude - m.latitude.values) * 111.32
        dlon = (
            (v.longitude - m.longitude.values)
            * 111.32
            * np.cos(np.radians(v.latitude))
        )

        distance = np.sqrt(dlat**2 + dlon**2)

        best = np.argmin(distance)

        matched_viirs += 1
        matched_modis.add(m.index[best])
        distances.append(distance[best])

    median_distance = (
        np.median(distances) if distances else float("nan")
    )

    print(
        f"{threshold:<12}{matched_viirs:<17}"
        f"{len(matched_modis):<17}{median_distance:.3f} km"
    )
