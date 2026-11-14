import pandas as pd
import streamlit as st

# Agreed default matching flag for the "MODIS matches" card.
# Change this only after both teammates agree which scientific result to report.
MATCH_FLAG = "modis_detected_box_30min"


def render_metrics(viirs: pd.DataFrame, modis: pd.DataFrame) -> None:
    viirs_count = len(viirs)
    modis_count = len(modis)
    total_count = viirs_count + modis_count

    if MATCH_FLAG in viirs.columns:
        matched = (
            viirs[MATCH_FLAG]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["true", "1", "yes"])
            .sum()
        )
        match_label = "Candidate MODIS matches"
    else:
        matched = 0
        match_label = "Candidate matches (flag unavailable)"

    col1, col2, col3 = st.columns(3)
    col1.metric("Total detections", f"{total_count:,}")
    col2.metric(match_label, f"{int(matched):,}")
    col3.metric("VIIRS detections", f"{viirs_count:,}")

    st.caption(
        f"Total detections = filtered VIIRS rows + filtered MODIS rows. "
        f"Match card uses the existing {MATCH_FLAG} flag; it does not "
        "create a new scientific matching metric."
    )
