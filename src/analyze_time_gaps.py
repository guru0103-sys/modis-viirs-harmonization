
"""Compare time gaps and distances across matching rules.

Run from repository root:
    python src/analyze_time_gaps.py

Original matching outputs are not modified.
"""

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

import match as M

EARTH_KM = 6371.0
DISTANCE_RADIUS_KM = 1.5

BINS = [0, 5, 10, 15, 30, 45, 60, 90,float("inf")]
LABELS = [
    "0-5", "5-10", "10-15", "15-30",
    "30-45", "45-60", "60-90", "90+"
]


def distance_match(viirs, modis, minutes):
    """Return nearest MODIS index and distance for each VIIRS point."""
    tree = BallTree(
        np.radians(modis[["latitude", "longitude"]].to_numpy()),
        metric="haversine"
    )

    v_xy = np.radians(
        viirs[["latitude", "longitude"]].to_numpy()
    )

    candidates, distances = tree.query_radius(
        v_xy,
        r=DISTANCE_RADIUS_KM / EARTH_KM,
        return_distance=True
    )

    m_time = (
        modis["time_utc"].to_numpy()
        .astype("datetime64[s]").astype("int64")
    )
    v_time = (
        viirs["time_utc"].to_numpy()
        .astype("datetime64[s]").astype("int64")
    )

    best = np.full(len(viirs), -1, dtype=int)
    best_dist = np.full(len(viirs), np.nan)

    for i, idx in enumerate(candidates):
        if len(idx) == 0:
            continue

        dt = np.abs(v_time[i] - m_time[idx]) / 60.0
        valid = dt <= minutes

        if valid.any():
            positions = np.flatnonzero(valid)
            nearest = positions[np.argmin(distances[i][valid])]

            best[i] = idx[nearest]
            best_dist[i] = distances[i][nearest] * EARTH_KM

    return best, best_dist


def make_records(viirs, modis, indices, distances, rule, minutes):
    """Build one record per matched VIIRS detection."""
    matched = indices >= 0
    v_positions = np.flatnonzero(matched)
    m_positions = indices[matched]

    v_times = pd.to_datetime(
        viirs.iloc[v_positions]["time_utc"]
    ).reset_index(drop=True)

    m_times = pd.to_datetime(
        modis.iloc[m_positions]["time_utc"]
    ).reset_index(drop=True)

    signed = (
        (v_times - m_times).dt.total_seconds() / 60
    )

    return pd.DataFrame({
        "rule": rule,
        "time_window_minutes": minutes,
        "viirs_index": viirs.index.to_numpy()[v_positions],
        "modis_index": m_positions,
        "time_gap_min": signed.abs(),
        "signed_gap_min": signed,
        "distance_km": distances[matched]
    })


def main():
    M.OUT.mkdir(parents=True, exist_ok=True)

    modis = pd.read_csv(
        M.CLEAN / "modis_clean.csv",
        parse_dates=["time_utc"]
    )
    viirs = pd.read_csv(
        M.CLEAN / "viirs_clean.csv",
        parse_dates=["time_utc"]
    )

    all_records = []
    original_minutes = M.MATCH_MINUTES

    try:
        for minutes in [15, 30]:

            # Pixel-box rule
            M.MATCH_MINUTES = minutes
            box = M.match(viirs, modis)

            all_records.append(
                make_records(
                    viirs,
                    modis,
                    box["modis_idx"].to_numpy(),
                    box["dist_km"].to_numpy(),
                    "pixel_box",
                    minutes
                )
            )

            # 1.5 km distance-only rule
            indices, distances = distance_match(
                viirs, modis, minutes
            )

            all_records.append(
                make_records(
                    viirs,
                    modis,
                    indices,
                    distances,
                    "distance_1.5km",
                    minutes
                )
            )

    finally:
        M.MATCH_MINUTES = original_minutes

    records = pd.concat(all_records, ignore_index=True)

    # Save individual matched records for further inspection.
    records.to_csv(
        M.OUT / "time_gap_matched_records.csv",
        index=False
    )

    summaries = []

    for (rule, minutes), group in records.groupby(
        ["rule", "time_window_minutes"],
        sort=False
    ):
        gap = group["time_gap_min"]
        signed = group["signed_gap_min"]
        distance = group["distance_km"]

        print(f"\n{'=' * 55}")
        print(f"{rule} | {minutes} minutes")
        print(f"Matched VIIRS detections: {len(group)}")
        print(f"Unique MODIS detections: {group['modis_index'].nunique()}")

        print("\nABSOLUTE TIME GAP (minutes)")
        print(gap.describe().round(2))

        print("\nSIGNED TIME DIFFERENCE (VIIRS - MODIS)")
        print(signed.describe().round(2))
        print("VIIRS earlier:", int((signed < 0).sum()))
        print("VIIRS later:", int((signed > 0).sum()))
        print("Same time:", int((signed == 0).sum()))

        print("\nSPATIAL DISTANCE (km)")
        print(distance.describe().round(3))

        gap_bins = pd.cut(
            gap,
            bins=BINS,
            labels=LABELS,
            include_lowest=True
        )

        print("\nTIME GAP BINS")
        print(gap_bins.value_counts(sort=False))

        summaries.append({
            "rule": rule,
            "time_window_minutes": minutes,
            "viirs_matched": len(group),
            "unique_modis_matched": group["modis_index"].nunique(),
            "median_gap_min": round(gap.median(), 2),
            "mean_gap_min": round(gap.mean(), 2),
            "median_signed_gap_min": round(signed.median(), 2),
            "median_distance_km": round(distance.median(), 3),
            "viirs_earlier": int((signed < 0).sum()),
            "viirs_later": int((signed > 0).sum())
        })

    summary = pd.DataFrame(summaries)
    summary.to_csv(
        M.OUT / "time_gap_rule_summary.csv",
        index=False
    )

    print("\n\n========== FINAL SUMMARY ==========")
    print(summary.to_string(index=False))

    print("\nSaved:")
    print("outputs/time_gap_matched_records.csv")
    print("outputs/time_gap_rule_summary.csv")

    print(
        "\nNOTE: These are algorithm-specific matches, "
        "not true sensor detection probabilities."
    )


if __name__ == "__main__":
    main()

