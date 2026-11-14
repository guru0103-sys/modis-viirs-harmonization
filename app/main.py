
import streamlit as st
import pandas as pd

from components.theme import apply_theme
from components.mission_header import render_mission_header
from utils.data_loader import load_datasets
from components.filters import render_filters, apply_filters
from components.metrics import render_metrics, count_matches
from components.charts import (
    render_daily_activity,
    render_frp_distribution,
    render_matching_comparison,
    render_daily_matching_trends,
)
from components.map import render_hotspot_map
from components.data_explorer import render_data_explorer


st.set_page_config(
    page_title="Punjab–Haryana Fire Intelligence",
    page_icon="🔥",
    layout="wide",
)

apply_theme()
render_mission_header()


@st.cache_data
def get_data():
    return load_datasets()


def get_median_frp(frame):
    if frame.empty or "frp" not in frame.columns:
        return None

    values = pd.to_numeric(
        frame["frp"],
        errors="coerce",
    ).dropna()

    if values.empty:
        return None

    return float(values.median())


def render_intelligence_panel(viirs, modis, filters):

    st.markdown("### Regional intelligence")
    st.caption("FILTERED OBSERVATIONS")

    st.markdown("**Sensor coverage**")

    col1, col2 = st.columns(2)

    col1.metric("VIIRS", f"{len(viirs):,}")
    col2.metric("MODIS", f"{len(modis):,}")

    st.divider()

    st.markdown("**Candidate matching**")

    box_matches = count_matches(
        viirs,
        "modis_detected_box_30min",
    )

    distance_matches = count_matches(
        viirs,
        "modis_detected_distance_1p5km_30min",
    )

    col1, col2 = st.columns(2)

    col1.metric(
        "Pixel-box",
        f"{box_matches:,}" if box_matches is not None else "N/A",
    )

    col2.metric(
        "Distance-only",
        f"{distance_matches:,}"
        if distance_matches is not None
        else "N/A",
    )

    st.caption(
        "Candidate associations under two matching rules. "
        "These are not verified detection rates."
    )

    st.divider()

    st.markdown("**Fire radiative power**")

    viirs_median = get_median_frp(viirs)
    modis_median = get_median_frp(modis)

    col1, col2 = st.columns(2)

    col1.metric(
        "VIIRS median",
        f"{viirs_median:.1f} MW"
        if viirs_median is not None
        else "N/A",
    )

    col2.metric(
        "MODIS median",
        f"{modis_median:.1f} MW"
        if modis_median is not None
        else "N/A",
    )

    st.divider()

    st.markdown("**Active filters**")

    st.write(f"**Sensor:** {filters['sensor']}")
    st.write(f"**Day / Night:** {filters['daynight']}")
    st.write(f"**Confidence:** {filters['confidence']}")

    st.caption(
        "Dataset period: October–November 2024. "
        "All displayed observations are historical."
    )


# ----------------------------------------------------------
# LOAD DATA
# ----------------------------------------------------------

try:
    viirs, modis, matched_pairs = get_data()

except Exception as exc:
    st.error(f"Could not load the project data: {exc}")
    st.info(
        "Check the CSV paths in the data/ folders "
        "and see README.md."
    )
    st.stop()


# ----------------------------------------------------------
# SIDEBAR FILTERS AND NAVIGATION
# ----------------------------------------------------------

filters = render_filters(viirs, modis)

viirs_filtered, modis_filtered = apply_filters(
    viirs,
    modis,
    filters,
)

page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Daily Fire Activity",
        "Data & Matching",
        "Data Explorer",
    ],
)

st.sidebar.divider()
st.sidebar.caption("MODIS–VIIRS HARMONIZATION")
st.sidebar.caption("Historical observation mode")
st.sidebar.caption("Punjab–Haryana · October–November 2024")


# ==========================================================
# OVERVIEW
# ==========================================================

if page == "Overview":

    st.markdown("## Observation overview")

    st.caption(
        "REGIONAL FIRE ACTIVITY  /  PUNJAB–HARYANA  /  2024"
    )

    render_metrics(
        viirs_filtered,
        modis_filtered,
        matched_pairs,
    )

    st.divider()

    map_column, intelligence_column = st.columns(
        [2.15, 1],
        gap="large",
    )

    with map_column:

        st.markdown("### Geospatial hotspot distribution")

        st.caption(
            "Interactive satellite detection locations"
        )

        render_hotspot_map(
            viirs_filtered,
            modis_filtered,
            filters["sensor"],
        )

    with intelligence_column:

        with st.container(
            border=True,
            key="intelligence_panel",
        ):
            render_intelligence_panel(
                viirs_filtered,
                modis_filtered,
                filters,
            )

    st.divider()

    st.markdown("### Temporal activity")

    st.caption(
        "Daily satellite detection counts across the selected period"
    )

    render_daily_activity(
        viirs_filtered,
        modis_filtered,
        full_width=True,
    )


# ==========================================================
# DAILY FIRE ACTIVITY
# ==========================================================

elif page == "Daily Fire Activity":

    st.markdown("## Temporal analytics")

    st.caption(
        "DAILY DETECTION TRENDS  /  FIRE RADIATIVE POWER"
    )

    st.markdown("### Daily detection activity")

    render_daily_activity(
        viirs_filtered,
        modis_filtered,
        full_width=True,
    )

    st.divider()

    st.markdown("### Fire radiative power")

    render_frp_distribution(
        viirs_filtered,
        modis_filtered,
    )

    st.divider()

    st.markdown("### Matching method comparison")

    render_matching_comparison(
        viirs_filtered,
        chart_key="daily_matching_comparison",
    )

    st.divider()

    st.markdown("### Daily matching trends")

    render_daily_matching_trends(viirs_filtered)


# ==========================================================
# DATA AND MATCHING
# ==========================================================

elif page == "Data & Matching":

    st.markdown("## Data and matching laboratory")

    st.caption(
        "MATCHING DIAGNOSTICS  /  CANDIDATE ASSOCIATIONS"
    )

    st.markdown("### Matching rule comparison")

    render_matching_comparison(
        viirs_filtered,
        chart_key="data_matching_comparison",
    )

    st.divider()

    st.markdown("### Daily candidate matching trends")

    render_daily_matching_trends(viirs_filtered)

    st.divider()

    st.markdown("### Filtered dataset overview")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "VIIRS records",
        f"{len(viirs_filtered):,}",
    )

    col2.metric(
        "MODIS records",
        f"{len(modis_filtered):,}",
    )

    col3.metric(
        "Combined records",
        f"{len(viirs_filtered) + len(modis_filtered):,}",
    )

    st.caption(
        "Matching flags are read from existing scientific outputs. "
        "The frontend does not recalculate matching results."
    )


# ==========================================================
# DATA EXPLORER
# ==========================================================

elif page == "Data Explorer":

    render_data_explorer(
        viirs_filtered,
        modis_filtered,
        matched_pairs,
    )


# ----------------------------------------------------------
# SIDEBAR FOOTER
# ----------------------------------------------------------

st.sidebar.divider()
st.sidebar.caption("EARTH OBSERVATION ANALYTICS")
st.sidebar.caption("Historical data · 2024")

