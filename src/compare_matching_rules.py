
"""Compare pixel-box and 1.5 km distance rules at 15 and 30 minutes.

Does not overwrite the existing matching outputs.
Run from the repository root:
    python src/compare_matching_rules.py
"""

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

import match as M

EARTH_KM = 6371.0
DISTANCE_RADIUS_KM = 1.5


def distance_match(viirs, modis, minutes):
    """Nearest MODIS detection within 1.5 km and the time window."""
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

    for i, idx in enumerate(candidates):
        if len(idx) == 0:
            continue

        dt = np.abs(v_time[i] - m_time[idx]) / 60.0
        valid = dt <= minutes

        if valid.any():
            valid_positions = np.flatnonzero(valid)
            nearest_position = valid_positions[
                np.argmin(distances[i][valid])
            ]
            best[i] = idx[nearest_position]

    return best


def summarize(rule, minutes, indices, n_viirs, n_modis):
    matched = indices >= 0
    viirs_count = int(matched.sum())
    unique_modis = len(set(indices[matched]))

    return {
        "rule": rule,
        "time_window_minutes": minutes,
        "viirs_matched": viirs_count,
        "viirs_match_percent": round(
            100 * viirs_count / n_viirs, 2
        ),
        "unique_modis_matched": unique_modis,
        "modis_match_percent": round(
            100 * unique_modis / n_modis, 2
        )
    }


def main():
    modis = pd.read_csv(
        M.CLEAN / "modis_clean.csv",
        parse_dates=["time_utc"]
    )
    viirs = pd.read_csv(
        M.CLEAN / "viirs_clean.csv",
        parse_dates=["time_utc"]
    )

    results = []
    original_minutes = M.MATCH_MINUTES

    try:
        for minutes in [15, 30]:
            # Existing pixel-box rule
            M.MATCH_MINUTES = minutes
            box_result = M.match(viirs, modis)

            results.append(
                summarize(
                    "pixel_box",
                    minutes,
                    box_result["modis_idx"].to_numpy(),
                    len(viirs),
                    len(modis)
                )
            )

            # Independent 1.5 km distance-only rule
            distance_result = distance_match(
                viirs, modis, minutes
            )

            results.append(
                summarize(
                    "distance_1.5km",
                    minutes,
                    distance_result,
                    len(viirs),
                    len(modis)
                )
            )

    finally:
        M.MATCH_MINUTES = original_minutes

    comparison = pd.DataFrame(results)

    output = M.OUT / "rule_comparison_15_30.csv"
    comparison.to_csv(output, index=False)

    print("\n========== MATCHING RULE COMPARISON ==========")
    print(comparison.to_string(index=False))
    print(f"\nSaved to: {output}")

    print(
        "\nNOTE: These are algorithm-specific co-detection counts, "
        "not true sensor detection probabilities."
    )


if __name__ == "__main__":
    main()
