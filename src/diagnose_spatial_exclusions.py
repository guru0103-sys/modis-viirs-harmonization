
"""Identify why pixel-box and distance-only matching differ."""

import numpy as np
import pandas as pd

import match as M
from analyze_time_gaps import distance_match

def main():
    modis = pd.read_csv(
        M.CLEAN / "modis_clean.csv",
        parse_dates=["time_utc"]
    )
    viirs = pd.read_csv(
        M.CLEAN / "viirs_clean.csv",
        parse_dates=["time_utc"]
    )

    minutes = 15

    original_minutes = M.MATCH_MINUTES
    try:
        M.MATCH_MINUTES = minutes
        box = M.match(viirs, modis)
    finally:
        M.MATCH_MINUTES = original_minutes

    box_idx = box["modis_idx"].to_numpy()

    dist_idx, dist_km = distance_match(
        viirs, modis, minutes
    )

    categories = []
    details = []

    for i in range(len(viirs)):
        b = box_idx[i]
        d = dist_idx[i]

        if b < 0 and d < 0:
            continue
        elif b >= 0 and d < 0:
            category = "pixel_box_only"
        elif b < 0 and d >= 0:
            category = "distance_only"
        elif b == d:
            category = "both_same_modis"
        else:
            category = "both_different_modis"

        categories.append(category)

        if category == "distance_only":
            v = viirs.iloc[i]
            m = modis.iloc[d]

            dx = (
                (v["longitude"] - m["longitude"])
                * M.KM_PER_DEG
                * np.cos(np.radians(v["latitude"]))
            )
            dy = (
                (v["latitude"] - m["latitude"])
                * M.KM_PER_DEG
            )

            outside_x = abs(dx) > m["scan"] / 2
            outside_y = abs(dy) > m["track"] / 2

            if outside_x and outside_y:
                reason = "outside_both_dimensions"
            elif outside_x:
                reason = "outside_east_west"
            elif outside_y:
                reason = "outside_north_south"
            else:
                reason = "inside_box_unexpected"

            details.append({
                "viirs_index": i,
                "modis_index": d,
                "distance_km": dist_km[i],
                "dx_km": dx,
                "dy_km": dy,
                "scan_km": m["scan"],
                "track_km": m["track"],
                "reason": reason
            })

    print("\nMATCH CATEGORY COUNTS")
    print(pd.Series(categories).value_counts())

    detail_df = pd.DataFrame(details)

    if not detail_df.empty:
        print("\nDISTANCE-ONLY EXCLUSIONS")
        print(detail_df["reason"].value_counts())

        print("\nEXCLUSION DETAILS")
        print(detail_df.head(15).to_string(index=False))

        detail_df.to_csv(
            M.OUT / "spatial_exclusions_15min.csv",
            index=False
        )

    print("\nSaved outputs/spatial_exclusions_15min.csv")


if __name__ == "__main__":
    main()
