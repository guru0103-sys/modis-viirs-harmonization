import pandas as pd
import streamlit as st

MATCH_FLAG = "modis_detected_box_30min"
DISTANCE_FLAG = "modis_detected_distance_1p5km_30min"


def count_matches(frame, column):
    if column not in frame.columns:
        return None

    return int(
        pd.to_numeric(frame[column], errors="coerce")
        .fillna(0)
        .eq(1)
        .sum()
    )


def render_metrics(
    viirs: pd.DataFrame,
    modis: pd.DataFrame,
    matched_pairs: pd.DataFrame = None,
) -> None:

    viirs_count = len(viirs)
    modis_count = len(modis)
    total_count = viirs_count + modis_count

    box_matches = count_matches(viirs, MATCH_FLAG)
    distance_matches = count_matches(viirs, DISTANCE_FLAG)

    unique_modis = (
        matched_pairs["modis_idx"].nunique()
        if matched_pairs is not None
        and not matched_pairs.empty
        and "modis_idx" in matched_pairs.columns
        else None
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total detections", f"{total_count:,}")
    col2.metric("VIIRS detections", f"{viirs_count:,}")
    col3.metric("MODIS detections", f"{modis_count:,}")

    col4.metric(
        "Pixel-box candidate matches",
        f"{box_matches:,}" if box_matches is not None else "N/A",
    )

    col5, col6 = st.columns(2)

    col5.metric(
        "Distance-only candidate matches",
        f"{distance_matches:,}" if distance_matches is not None else "N/A",
    )

    col6.metric(
        "Unique MODIS detections matched (full dataset)",
        f"{unique_modis:,}" if unique_modis is not None else "N/A",
    )

    st.caption(
        "Detection counts and candidate-match counts reflect the current "
        "filters. Unique MODIS detections matched is calculated from the "
        "complete matched-pairs dataset and is independent of the filters. "
        "Candidate matches are not verified ground-truth detections."
    )
