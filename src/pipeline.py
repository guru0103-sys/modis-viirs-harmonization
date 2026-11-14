
"""
Reusable MODIS–VIIRS upload processing pipeline.

Run through the Streamlit application or import run_pipeline()
from another Python module.

Outputs are written to a separate workspace:
    clean/
    matched/
    outputs/
"""

from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree


# Make existing src modules importable when this file is
# imported by Streamlit from the project root.
SRC_DIR = Path(__file__).resolve().parent

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import match as M
from config import MODIS_SATELLITE, MATCH_MINUTES, SEARCH_RADIUS_KM


EARTH_KM = 6371.0
KM_PER_DEG = 111.32

KEEP = [
    "sensor", "satellite", "time_utc",
    "latitude", "longitude", "scan", "track",
    "frp", "daynight", "conf_num", "conf_class"
]

PART_A_TIME_MINUTES = 15
PART_A_RADII_KM = (0.5, 0.75, 1.0, 1.5, 2.0, 3.5)

PART_B_TIME_MINUTES = 30
PART_B_DISTANCE_KM = 1.5

PROXY_DISTANCE_KM = 150.0
PROXY_TIME_MINUTES = 30


# ---------------------------------------------------------
# 1. INPUT VALIDATION AND CLEANING
# ---------------------------------------------------------

def clean_uploaded_frame(frame: pd.DataFrame, sensor: str) -> pd.DataFrame:
    """Clean one uploaded raw FIRMS CSV using the project rules."""

    sensor = sensor.upper()

    if sensor not in {"MODIS", "VIIRS"}:
        raise ValueError("Sensor must be MODIS or VIIRS.")

    if frame is None or frame.empty:
        raise ValueError(f"The uploaded {sensor} dataset is empty.")

    df = frame.copy()

    required = {
        "acq_date", "acq_time", "latitude", "longitude",
        "satellite", "scan", "track", "frp",
        "daynight", "confidence"
    }

    missing = sorted(required - set(df.columns))

    if missing:
        raise ValueError(
            f"{sensor} upload is missing required columns: {missing}"
        )

    # Convert acquisition time into the same HHMM format
    # used by the original cleaning script.
    acq_time = pd.to_numeric(df["acq_time"], errors="coerce")

    if acq_time.isna().any():
        raise ValueError(
            f"{sensor}: acq_time contains invalid values."
        )

    df["acq_time"] = (
        acq_time.astype(int).astype(str).str.zfill(4)
    )

    df["time_utc"] = pd.to_datetime(
        df["acq_date"].astype(str) + " " + df["acq_time"],
        format="%Y-%m-%d %H%M",
        errors="coerce"
    )

    if df["time_utc"].isna().any():
        raise ValueError(
            f"{sensor}: some acquisition dates or times are invalid."
        )

    df["sensor"] = sensor
    df["satellite"] = df["satellite"].astype(str).str.strip()

    for col in ["latitude", "longitude", "scan", "track", "frp"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if sensor == "MODIS":
        df["conf_num"] = pd.to_numeric(
            df["confidence"], errors="coerce"
        )
        df["conf_class"] = pd.NA
    else:
        df["conf_class"] = (
            df["confidence"]
            .astype(str)
            .str.strip()
            .str.lower()
            .str[0]
        )
        df["conf_num"] = pd.NA

    before = len(df)

    df = df.drop_duplicates(
        subset=["latitude", "longitude", "time_utc", "satellite"]
    )

    df = df.dropna(
        subset=[
            "latitude", "longitude", "frp",
            "scan", "track", "time_utc"
        ]
    )

    df = df[
        df["latitude"].between(-90, 90)
        & df["longitude"].between(-180, 180)
        & (df["scan"] > 0)
        & (df["track"] > 0)
        & (df["frp"] >= 0)
    ].copy()

    if sensor == "MODIS":
        df = df[
            df["satellite"].str.lower()
            == MODIS_SATELLITE.lower()
        ].copy()

        if df.empty:
            raise ValueError(
                f"No MODIS {MODIS_SATELLITE} observations remain. "
                "Check the satellite values in the uploaded file."
            )

    if df.empty:
        raise ValueError(
            f"{sensor}: no valid observations remain after cleaning."
        )

    print(
        f"{sensor}: {before:,} uploaded rows -> "
        f"{len(df):,} cleaned rows"
    )

    return df[KEEP].reset_index(drop=True)


# ---------------------------------------------------------
# 2. DISTANCE-ONLY MATCHING
# ---------------------------------------------------------

def distance_match(
    viirs: pd.DataFrame,
    modis: pd.DataFrame,
    radius_km: float,
    minutes: int
) -> np.ndarray:
    """Return nearest eligible MODIS index for each VIIRS row."""

    tree = BallTree(
        np.radians(modis[["latitude", "longitude"]].to_numpy()),
        metric="haversine"
    )

    v_xy = np.radians(
        viirs[["latitude", "longitude"]].to_numpy()
    )

    candidates, distances = tree.query_radius(
        v_xy,
        r=radius_km / EARTH_KM,
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

    for i, indices in enumerate(candidates):
        if len(indices) == 0:
            continue

        dt = np.abs(v_time[i] - m_time[indices]) / 60.0
        valid = dt <= minutes

        if valid.any():
            positions = np.flatnonzero(valid)
            nearest = positions[
                np.argmin(distances[i][valid])
            ]
            best[i] = indices[nearest]

    return best


# ---------------------------------------------------------
# 3. FRIDAY PART A: DISTANCE RADII VS PIXEL BOX
# ---------------------------------------------------------

def run_part_a(viirs, modis):
    """Reproduce the original 15-minute Part A comparison."""

    mt = (
        modis["time_utc"].to_numpy()
        .astype("datetime64[s]").astype("int64")
    )

    vt = (
        viirs["time_utc"].to_numpy()
        .astype("datetime64[s]").astype("int64")
    )

    m_xy = np.radians(
        modis[["latitude", "longitude"]].to_numpy()
    )

    v_xy = np.radians(
        viirs[["latitude", "longitude"]].to_numpy()
    )

    viirs_tree = BallTree(v_xy, metric="haversine")

    candidate_indices, candidate_distances = (
        viirs_tree.query_radius(
            m_xy,
            r=max(PART_A_RADII_KM) / EARTH_KM,
            return_distance=True
        )
    )

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
                distances[time_ok].min() * EARTH_KM
            )

    results = []

    for radius in PART_A_RADII_KM:
        count = int((min_distance_km <= radius).sum())

        results.append({
            "rule": "distance_only",
            "radius_km": radius,
            "time_limit_min": PART_A_TIME_MINUTES,
            "modis_with_viirs_partner": count,
            "modis_total": len(modis),
            "share_percent": round(
                100 * count / len(modis), 2
            )
        })

    original_minutes = M.MATCH_MINUTES

    try:
        M.MATCH_MINUTES = PART_A_TIME_MINUTES
        box_result = M.match(viirs, modis)
    finally:
        M.MATCH_MINUTES = original_minutes

    box_matched = box_result.loc[
        box_result["modis_idx"] >= 0, "modis_idx"
    ].nunique()

    box_share = 100 * box_matched / len(modis)

    results.append({
        "rule": "existing_pixel_box",
        "radius_km": np.nan,
        "time_limit_min": PART_A_TIME_MINUTES,
        "modis_with_viirs_partner": int(box_matched),
        "modis_total": len(modis),
        "share_percent": round(box_share, 2)
    })

    return pd.DataFrame(results)


# ---------------------------------------------------------
# 4. FRIDAY PART B: CO-OBSERVATION PROXY AND FRP
# ---------------------------------------------------------

def run_part_b(viirs, modis):
    """Reproduce the original 30-minute Part B diagnostics."""

    m_xy = np.radians(
        modis[["latitude", "longitude"]].to_numpy()
    )

    v_xy = np.radians(
        viirs[["latitude", "longitude"]].to_numpy()
    )

    mt = (
        modis["time_utc"].to_numpy()
        .astype("datetime64[s]").astype("int64")
    )

    vt = (
        viirs["time_utc"].to_numpy()
        .astype("datetime64[s]").astype("int64")
    )

    modis_tree = BallTree(m_xy, metric="haversine")

    # Broad eligibility proxy: 150 km and +/-30 minutes.
    proxy_candidates = modis_tree.query_radius(
        v_xy,
        r=PROXY_DISTANCE_KM / EARTH_KM
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

    # Existing pixel-box rule at 30 minutes.
    original_minutes = M.MATCH_MINUTES

    try:
        M.MATCH_MINUTES = PART_B_TIME_MINUTES
        box_result = M.match(viirs, modis)
    finally:
        M.MATCH_MINUTES = original_minutes

    detected_box = (
        box_result["modis_idx"].to_numpy() >= 0
    )

    # Independent 1.5 km distance-only rule.
    detected_distance = (
        distance_match(
            viirs,
            modis,
            PART_B_DISTANCE_KM,
            PART_B_TIME_MINUTES
        ) >= 0
    )

    flagged = viirs.copy()

    flagged["co_observed_proxy"] = co_observed.astype(int)
    flagged["modis_detected_box_30min"] = detected_box.astype(int)
    flagged["modis_detected_distance_1p5km_30min"] = (
        detected_distance.astype(int)
    )

    # FRP comparison table.
    bins = [0, 1, 2, 2.5, 3, 5, 10, 20, np.inf]

    labels = [
        "<1", "1-2", "2-2.5", "2.5-3",
        "3-5", "5-10", "10-20", ">20"
    ]

    analysis = pd.DataFrame({
        "frp": viirs["frp"],
        "co_observed": co_observed,
        "box_detected": detected_box,
        "distance_detected": detected_distance
    })

    analysis["frp_bin"] = pd.cut(
        analysis["frp"],
        bins=bins,
        labels=labels,
        right=False
    )

    eligible = analysis[analysis["co_observed"]].copy()

    if eligible.empty:
        table = pd.DataFrame(
            columns=["n", "pct_box", "pct_1p5km"]
        )
        table.index.name = "frp_bin"
    else:
        table = (
            eligible.groupby("frp_bin", observed=False)
            .agg(
                n=("box_detected", "size"),
                pct_box=("box_detected", "mean"),
                pct_1p5km=("distance_detected", "mean")
            )
        )

        table[["pct_box", "pct_1p5km"]] *= 100
        table[["pct_box", "pct_1p5km"]] = (
            table[["pct_box", "pct_1p5km"]].round(2)
        )

    summary = {
        "viirs_total": int(len(viirs)),
        "proxy_eligible": int(co_observed.sum()),
        "proxy_eligible_percent": round(
            100 * co_observed.mean(), 2
        ),
        "box_agreement_percent": (
            round(100 * detected_box[co_observed].mean(), 2)
            if co_observed.any() else None
        ),
        "distance_1p5km_agreement_percent": (
            round(
                100 * detected_distance[co_observed].mean(), 2
            )
            if co_observed.any() else None
        ),
        "proxy_distance_km": PROXY_DISTANCE_KM,
        "proxy_time_minutes": PROXY_TIME_MINUTES,
        "warning": (
            "The 150 km eligibility proxy is not verified "
            "MODIS swath coverage."
        )
    }

    return flagged, table, summary


# ---------------------------------------------------------
# 5. MAIN PIPELINE
# ---------------------------------------------------------

def run_pipeline(
    modis_raw: pd.DataFrame,
    viirs_raw: pd.DataFrame,
    output_dir
):
    """
    Process uploaded raw MODIS and VIIRS DataFrames.

    Returns paths, row counts, and processing summaries.
    Does not overwrite the original project datasets.
    """

    output_dir = Path(output_dir)

    clean_dir = output_dir / "clean"
    matched_dir = output_dir / "matched"
    outputs_dir = output_dir / "outputs"

    for folder in [clean_dir, matched_dir, outputs_dir]:
        folder.mkdir(parents=True, exist_ok=True)

    # Clean both uploaded datasets.
    modis = clean_uploaded_frame(modis_raw, "MODIS")
    viirs = clean_uploaded_frame(viirs_raw, "VIIRS")

    # Save cleaned data.
    modis.to_csv(clean_dir / "modis_clean.csv", index=False)
    viirs.to_csv(clean_dir / "viirs_clean.csv", index=False)

    # Run the baseline 30-minute pixel-box matching.
    original_minutes = M.MATCH_MINUTES

    try:
        M.MATCH_MINUTES = PART_B_TIME_MINUTES
        result = M.match(viirs, modis)
    finally:
        M.MATCH_MINUTES = original_minutes

    if len(result) != len(viirs):
        raise ValueError(
            "Matching output row count does not match VIIRS input."
        )

    flagged = pd.concat([viirs, result], axis=1)
    flagged["modis_detected"] = (
        flagged["modis_idx"] >= 0
    ).astype(int)

    flagged.to_csv(
        matched_dir / "viirs_flagged.csv",
        index=False
    )

    # Generate matched pairs with both sensors' attributes.
    pairs = flagged[
        flagged["modis_detected"] == 1
    ].copy()

    modis_prefixed = (
        modis.add_prefix("modis_")
        .reset_index()
        .rename(columns={"index": "modis_idx"})
    )

    pairs = pairs.merge(
        modis_prefixed,
        on="modis_idx",
        how="left"
    )

    pairs.to_csv(
        matched_dir / "matched_pairs.csv",
        index=False
    )

    # Matching summary.
    n_viirs = len(viirs)
    n_modis = len(modis)
    n_matched = int(flagged["modis_detected"].sum())

    unique_modis = int(
        flagged.loc[
            flagged["modis_detected"] == 1,
            "modis_idx"
        ].nunique()
    )

    match_summary = {
        "viirs_total": n_viirs,
        "viirs_matched_to_modis": n_matched,
        "viirs_only_modis_missed": n_viirs - n_matched,
        "pct_viirs_missed_by_modis": round(
            100 * (n_viirs - n_matched) / max(n_viirs, 1), 1
        ),
        "modis_total": n_modis,
        "modis_confirmed_by_viirs": unique_modis,
        "modis_only_not_confirmed": n_modis - unique_modis,
        "pct_modis_not_confirmed": round(
            100 * (n_modis - unique_modis) / max(n_modis, 1), 1
        ),
        "median_match_distance_km": (
            round(float(np.nanmedian(flagged["dist_km"])), 2)
            if n_matched else None
        ),
        "match_minutes": PART_B_TIME_MINUTES
    }

    # Run the original Friday diagnostics.
    part_a = run_part_a(viirs, modis)
    coobserved, frp_table, part_b_summary = run_part_b(
        viirs, modis
    )

    # Save all generated outputs.
    coobserved.to_csv(
        matched_dir / "viirs_coobserved.csv",
        index=False
    )

    part_a.to_csv(
        outputs_dir / "box_vs_distance.csv",
        index=False
    )

    frp_table.to_csv(
        outputs_dir / "detection_by_frp.csv"
    )

    (outputs_dir / "match_summary.json").write_text(
        json.dumps(match_summary, indent=2)
    )

    (outputs_dir / "diagnostics_summary.json").write_text(
        json.dumps(part_b_summary, indent=2)
    )

    # Basic output integrity checks.
    expected_viirs_files = [
        matched_dir / "viirs_flagged.csv",
        matched_dir / "viirs_coobserved.csv"
    ]

    for path in expected_viirs_files:
        check = pd.read_csv(path)

        if len(check) != len(viirs):
            raise ValueError(
                f"Output integrity check failed: {path.name}"
            )

    if len(pairs) != n_matched:
        raise ValueError(
            "Matched-pairs count does not agree with flagged VIIRS."
        )

    return {
        "output_dir": str(output_dir),
        "clean_dir": str(clean_dir),
        "matched_dir": str(matched_dir),
        "outputs_dir": str(outputs_dir),
        "modis_count": n_modis,
        "viirs_count": n_viirs,
        "matched_pair_count": len(pairs),
        "match_summary": match_summary,
        "diagnostics_summary": part_b_summary
    }
