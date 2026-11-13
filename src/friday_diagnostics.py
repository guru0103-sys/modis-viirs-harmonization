
"""
FRIDAY DIAGNOSTICS
MODIS Aqua vs Suomi-NPP VIIRS

PART A:
Compare distance-only matching with the existing MODIS pixel-box
matching rule at a 15-minute time threshold.

PART B:
Explore co-detection agreement by VIIRS FRP using a broad
150 km / +/-30 minute eligibility proxy.

IMPORTANT:
The 150 km proxy does NOT establish actual MODIS swath coverage.
Part B results must not be described as true detection probabilities.
"""

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

import match as M
from config import CLEAN, MATCHED, OUT


# ============================================================
# CONFIGURATION
# ============================================================

EARTH_RADIUS_KM = 6371.0

PART_A_TIME_MINUTES = 15
PART_A_RADII_KM = (0.5, 0.75, 1.0, 1.5, 2.0, 3.5)

PART_B_TIME_MINUTES = 30
PART_B_DISTANCE_KM = 1.5

# Exploratory eligibility proxy only.
PROXY_DISTANCE_KM = 150.0
PROXY_TIME_MINUTES = 30


# ============================================================
# LOAD CLEAN DATA
# ============================================================

print("\nLoading cleaned datasets...")

modis = pd.read_csv(
    CLEAN / "modis_clean.csv",
    parse_dates=["time_utc"]
)

viirs = pd.read_csv(
    CLEAN / "viirs_clean.csv",
    parse_dates=["time_utc"]
)

if modis.empty or viirs.empty:
    raise ValueError("MODIS or VIIRS cleaned dataset is empty.")

required_columns = [
    "latitude", "longitude", "time_utc",
    "scan", "track", "frp"
]

for name, frame in [("MODIS", modis), ("VIIRS", viirs)]:
    missing = [col for col in required_columns if col not in frame.columns]
    if missing:
        raise ValueError(f"{name} dataset is missing columns: {missing}")

# Convert timestamps to integer seconds for efficient comparisons.
mt = (
    modis["time_utc"]
    .to_numpy()
    .astype("datetime64[s]")
    .astype("int64")
)

vt = (
    viirs["time_utc"]
    .to_numpy()
    .astype("datetime64[s]")
    .astype("int64")
)

# Coordinates in radians for BallTree haversine calculations.
m_xy = np.radians(
    modis[["latitude", "longitude"]].to_numpy()
)

v_xy = np.radians(
    viirs[["latitude", "longitude"]].to_numpy()
)

print(f"MODIS Aqua detections : {len(modis):,}")
print(f"VIIRS detections      : {len(viirs):,}")


# ============================================================
# PART A: DISTANCE RULE VS EXISTING BOX RULE
# ============================================================

print("\n" + "=" * 60)
print("PART A: DISTANCE RULE VS PIXEL-BOX RULE")
print("=" * 60)

# Build a tree of VIIRS detections.
viirs_tree = BallTree(v_xy, metric="haversine")

# Search up to the maximum radius needed.
candidate_indices, candidate_distances = viirs_tree.query_radius(
    m_xy,
    r=max(PART_A_RADII_KM) / EARTH_RADIUS_KM,
    return_distance=True
)

# For each MODIS detection, find the nearest VIIRS detection
# satisfying the 15-minute time condition.
min_distance_km = np.full(len(modis), np.inf)

for i, (indices, distances) in enumerate(
    zip(candidate_indices, candidate_distances)
):
    if len(indices) == 0:
        continue

    time_ok = (
        np.abs(vt[indices] - mt[i])
        <= PART_A_TIME_MINUTES * 60
    )

    if time_ok.any():
        min_distance_km[i] = (
            distances[time_ok].min() * EARTH_RADIUS_KM
        )

# Distance-only results.
distance_results = []

for radius in PART_A_RADII_KM:
    matched_count = int((min_distance_km <= radius).sum())

    distance_results.append({
        "rule": "distance_only",
        "radius_km": radius,
        "time_limit_min": PART_A_TIME_MINUTES,
        "modis_with_viirs_partner": matched_count,
        "modis_total": len(modis),
        "share_percent": round(
            100 * matched_count / len(modis), 2
        )
    })

# Existing box rule, using the actual matching implementation.
M.MATCH_MINUTES = PART_A_TIME_MINUTES

box_result = M.match(viirs, modis)

if "modis_idx" not in box_result.columns:
    raise ValueError(
        "match.py output does not contain 'modis_idx'. "
        "Check the matching implementation."
    )

box_matched = box_result.loc[
    box_result["modis_idx"] >= 0, "modis_idx"
].nunique()

box_share = 100 * box_matched / len(modis)

print("\nDistance-only matching:")
print(
    f"{'Radius':>10} {'MODIS matched':>16} "
    f"{'Share':>12}"
)

for result in distance_results:
    print(
        f"{result['radius_km']:>9.2f} km "
        f"{result['modis_with_viirs_partner']:>12,} "
        f"{result['share_percent']:>10.2f}%"
    )

print("\nExisting MODIS pixel-box rule:")
print(f"MODIS with VIIRS partner: {box_matched:,} / {len(modis):,}")
print(f"Share: {box_share:.2f}%")

# Save Part A results.
part_a_df = pd.DataFrame(distance_results)

box_row = pd.DataFrame([{
    "rule": "existing_pixel_box",
    "radius_km": np.nan,
    "time_limit_min": PART_A_TIME_MINUTES,
    "modis_with_viirs_partner": int(box_matched),
    "modis_total": len(modis),
    "share_percent": round(box_share, 2)
}])

part_a_df = pd.concat(
    [part_a_df, box_row],
    ignore_index=True
)

OUT.mkdir(parents=True, exist_ok=True)
MATCHED.mkdir(parents=True, exist_ok=True)

part_a_df.to_csv(
    OUT / "box_vs_distance.csv",
    index=False
)

print("\nSaved: outputs/box_vs_distance.csv")

print("\nPART A INTERPRETATION:")
distance_1p5 = part_a_df.loc[
    (part_a_df["rule"] == "distance_only")
    & (part_a_df["radius_km"] == 1.5),
    "share_percent"
].iloc[0]

print(f"1.5 km distance-only share : {distance_1p5:.2f}%")
print(f"Pixel-box rule share       : {box_share:.2f}%")
print(
    f"Difference                 : "
    f"{distance_1p5 - box_share:+.2f} percentage points"
)

print(
    "\nRemember: a higher distance-only result suggests the box "
    "geometry may be restrictive. It does not prove the distance "
    "rule represents the true MODIS pixel footprint."
)


# ============================================================
# PART B: BROAD CO-OBSERVATION PROXY
# ============================================================

print("\n" + "=" * 60)
print("PART B: FRP CO-DETECTION AGREEMENT")
print("=" * 60)

print(
    "\nEligibility proxy: at least one MODIS fire within "
    f"{PROXY_DISTANCE_KM:.0f} km and +/-{PROXY_TIME_MINUTES} minutes."
)

print(
    "WARNING: This is NOT verified MODIS swath coverage."
)

# Build MODIS tree.
modis_tree = BallTree(m_xy, metric="haversine")

# Broad proxy: MODIS fire within 150 km and +/-30 minutes.
proxy_candidates = modis_tree.query_radius(
    v_xy,
    r=PROXY_DISTANCE_KM / EARTH_RADIUS_KM
)

co_observed = np.zeros(len(viirs), dtype=bool)

for i, indices in enumerate(proxy_candidates):
    if len(indices) == 0:
        continue

    time_ok = (
        np.abs(mt[indices] - vt[i])
        <= PROXY_TIME_MINUTES * 60
    )

    co_observed[i] = time_ok.any()


# ------------------------------------------------------------
# Detection flags using the existing box rule
# ------------------------------------------------------------

M.MATCH_MINUTES = PART_B_TIME_MINUTES

box_result_30 = M.match(viirs, modis)

if len(box_result_30) != len(viirs):
    raise ValueError(
        "Matching output row count differs from VIIRS input. "
        "Cannot safely construct detection flags."
    )

# Ensure matching output is aligned with VIIRS input order.
detected_box = (
    box_result_30["modis_idx"].to_numpy() >= 0
)


# ------------------------------------------------------------
# Detection flags using 1.5 km distance-only rule
# ------------------------------------------------------------

local_candidates = modis_tree.query_radius(
    v_xy,
    r=PART_B_DISTANCE_KM / EARTH_RADIUS_KM
)

detected_distance = np.zeros(len(viirs), dtype=bool)

for i, indices in enumerate(local_candidates):
    if len(indices) == 0:
        continue

    time_ok = (
        np.abs(mt[indices] - vt[i])
        <= PART_B_TIME_MINUTES * 60
    )

    detected_distance[i] = time_ok.any()


# ------------------------------------------------------------
# Overall summary
# ------------------------------------------------------------

eligible_count = int(co_observed.sum())

print(f"\nTotal VIIRS detections       : {len(viirs):,}")
print(f"Proxy-eligible detections    : {eligible_count:,}")
print(
    f"Proxy-eligible share         : "
    f"{100 * eligible_count / len(viirs):.2f}%"
)

if eligible_count > 0:
    print(
        f"\nExisting box-rule agreement : "
        f"{100 * detected_box[co_observed].mean():.2f}%"
    )
    print(
        f"1.5 km distance agreement   : "
        f"{100 * detected_distance[co_observed].mean():.2f}%"
    )
else:
    print(
        "\nNo proxy-eligible detections. "
        "FRP agreement percentages cannot be calculated."
    )

# FRP minimum comparison.
modis_frp_floor = modis["frp"].min()

below_floor = (
    viirs["frp"] < modis_frp_floor
).mean() * 100

print(
    f"\nSmallest MODIS FRP in dataset: "
    f"{modis_frp_floor:.2f} MW"
)

print(
    f"VIIRS detections below this value: "
    f"{below_floor:.2f}%"
)

print(
    "Note: FRP values from the two sensors are not directly "
    "interchangeable; this is a descriptive comparison only."
)


# ============================================================
# FRP BIN ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("FRP CO-DETECTION AGREEMENT BY VIIRS FRP BIN")
print("=" * 60)

bins = [
    0, 1, 2, 2.5, 3, 5, 10, 20, np.inf
]

labels = [
    "<1",
    "1-2",
    "2-2.5",
    "2.5-3",
    "3-5",
    "5-10",
    "10-20",
    ">20"
]

df = pd.DataFrame({
    "frp": viirs["frp"],
    "co_observed": co_observed,
    "box_detected": detected_box,
    "distance_detected": detected_distance
})

df["frp_bin"] = pd.cut(
    df["frp"],
    bins=bins,
    labels=labels,
    right=False
)

# Only include detections passing the broad eligibility proxy.
eligible_df = df[df["co_observed"]].copy()

if eligible_df.empty:
    print("\nNo eligible detections. Skipping FRP table.")
    tab = pd.DataFrame(
        columns=[
            "n",
            "pct_box",
            "pct_1p5km"
        ]
    )
else:
    tab = (
        eligible_df
        .groupby("frp_bin", observed=False)
        .agg(
            n=("box_detected", "size"),
            pct_box=("box_detected", "mean"),
            pct_1p5km=("distance_detected", "mean")
        )
    )

    tab[["pct_box", "pct_1p5km"]] *= 100

    tab[["pct_box", "pct_1p5km"]] = (
        tab[["pct_box", "pct_1p5km"]].round(2)
    )

    print(
        tab.to_string()
    )

# Save FRP table.
tab.to_csv(
    OUT / "detection_by_frp.csv"
)

print("\nSaved: outputs/detection_by_frp.csv")


# ============================================================
# SAVE PER-VIIRS DIAGNOSTIC FLAGS
# ============================================================

flagged = viirs.copy()

flagged["co_observed_proxy"] = (
    co_observed.astype(int)
)

flagged["modis_detected_box_30min"] = (
    detected_box.astype(int)
)

flagged["modis_detected_distance_1p5km_30min"] = (
    detected_distance.astype(int)
)

flagged.to_csv(
    MATCHED / "viirs_coobserved.csv",
    index=False
)

print(
    "\nSaved: data/matched/viirs_coobserved.csv"
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("FRIDAY DIAGNOSTICS COMPLETE")
print("=" * 60)

print("Generated files:")
print("  outputs/box_vs_distance.csv")
print("  outputs/detection_by_frp.csv")
print("  data/matched/viirs_coobserved.csv")

print("\nInterpretation reminders:")
print("1. Part A compares spatial matching rules, not true pixel coverage.")
print("2. Part B uses a broad 150 km / 30 min eligibility proxy.")
print("3. FRP results are co-detection agreement, not true sensitivity.")
print("4. Do not overwrite the final frozen matching files with these outputs.")
print("\nNext step: inspect Part A before deciding the final matching rule.")
