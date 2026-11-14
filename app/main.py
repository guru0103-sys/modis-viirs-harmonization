
import streamlit as st
import pandas as pd
from pathlib import Path
import uuid

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
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline import run_pipeline


# ----------------------------------------------------------
# PAGE CONFIGURATION
# ----------------------------------------------------------

st.set_page_config(
    page_title="Punjab–Haryana Fire Intelligence",
    page_icon="🔥",
    layout="wide",
)

apply_theme()
render_mission_header()


# ----------------------------------------------------------
# DATA LOADING
# ----------------------------------------------------------

@st.cache_data
def get_data():
    return load_datasets()


def get_active_datasets():

    if "active_datasets" in st.session_state:
        return st.session_state["active_datasets"]

    return get_data()


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


# ----------------------------------------------------------
# INTELLIGENCE PANEL
# ----------------------------------------------------------

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
        if viirs_median is not None else "N/A",
    )

    col2.metric(
        "MODIS median",
        f"{modis_median:.1f} MW"
        if modis_median is not None else "N/A",
    )

    st.divider()

    st.markdown("**Active filters**")

    st.write(f"**Sensor:** {filters['sensor']}")
    st.write(f"**Day / Night:** {filters['daynight']}")
    st.write(f"**Confidence:** {filters['confidence']}")

    st.caption(
        "Displayed observations belong to the currently loaded dataset."
    )


# ----------------------------------------------------------
# UPLOAD AND PROCESS PAGE
# ----------------------------------------------------------

def render_upload_page():

    st.markdown("## Upload & Process")
    st.caption(
        "NEW REGION / NEW DATE RANGE / AUTOMATED PROCESSING"
    )

    st.write(
        "Upload raw NASA FIRMS MODIS Aqua and VIIRS CSV files. "
        "The processing pipeline will clean the data, perform "
        "matching, regenerate diagnostics, and load the results "
        "into the dashboard."
    )

    st.info(
        "Supported input: raw FIRMS CSV files containing "
        "acq_date, acq_time, latitude, longitude, satellite, "
        "scan, track, frp, daynight and confidence."
    )

    modis_file = st.file_uploader(
        "Upload MODIS Aqua CSV",
        type=["csv"],
        key="upload_modis",
    )

    viirs_file = st.file_uploader(
        "Upload VIIRS Suomi-NPP CSV",
        type=["csv"],
        key="upload_viirs",
    )

    if st.button(
        "Process datasets",
        type="primary",
        disabled=(modis_file is None or viirs_file is None),
    ):

        try:
            with st.spinner("Reading uploaded datasets..."):

                modis_raw = pd.read_csv(
                    modis_file,
                    dtype={"acq_time": str},
                )

                viirs_raw = pd.read_csv(
                    viirs_file,
                    dtype={"acq_time": str},
                )

            st.write("**Uploaded row counts**")

            col1, col2 = st.columns(2)
            col1.metric("MODIS raw rows", f"{len(modis_raw):,}")
            col2.metric("VIIRS raw rows", f"{len(viirs_raw):,}")

            session_id = st.session_state.get(
                "upload_session_id"
            )

            if session_id is None:
                session_id = str(uuid.uuid4())
                st.session_state["upload_session_id"] = session_id

            output_dir = (
                Path("/tmp")
                / f"modis_viirs_upload_{session_id}"
            )

            with st.spinner(
                "Cleaning, matching and generating diagnostics..."
            ):

                result = run_pipeline(
                    modis_raw,
                    viirs_raw,
                    output_dir,
                )

                clean_dir = Path(result["clean_dir"])
                matched_dir = Path(result["matched_dir"])

                processed_viirs = pd.read_csv(
                    matched_dir / "viirs_coobserved.csv"
                )

                processed_modis = pd.read_csv(
                    clean_dir / "modis_clean.csv"
                )

                processed_pairs = pd.read_csv(
                    matched_dir / "matched_pairs.csv"
                )

                st.session_state["active_datasets"] = (
                    processed_viirs,
                    processed_modis,
                    processed_pairs,
                )

                st.session_state["uploaded_dataset_active"] = True

            st.success("Datasets processed successfully!")

            st.markdown("### Processing results")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Clean MODIS",
                f"{result['modis_count']:,}",
            )

            col2.metric(
                "Clean VIIRS",
                f"{result['viirs_count']:,}",
            )

            col3.metric(
                "Candidate pairs",
                f"{result['matched_pair_count']:,}",
            )

            st.markdown("### Matching summary")

            st.json(result["match_summary"])

            st.markdown("### Diagnostic summary")

            st.json(result["diagnostics_summary"])

            st.caption(
                f"Generated files are stored in: {result['output_dir']}"
            )

            st.success(
                "The dashboard is now using your uploaded datasets. "
                "Open Overview or the other analytics pages."
            )

        except Exception as exc:

            st.error("Dataset processing failed.")
            st.exception(exc)

    st.divider()

    if st.session_state.get("uploaded_dataset_active", False):

        st.success("A processed upload is currently active.")

        if st.button("Restore original project datasets"):

            st.session_state.pop("active_datasets", None)
            st.session_state["uploaded_dataset_active"] = False

            st.rerun()


# ----------------------------------------------------------
# LOAD ACTIVE DATA
# ----------------------------------------------------------

try:

    viirs, modis, matched_pairs = get_active_datasets()

except Exception as exc:

    st.error(f"Could not load the project data: {exc}")

    st.info(
        "Check the CSV paths in the data folders "
        "and see README.md."
    )

    st.stop()


# ----------------------------------------------------------
# SINGLE SIDEBAR NAVIGATION
# ----------------------------------------------------------

page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Daily Fire Activity",
        "Data & Matching",
        "Data Explorer",
        "Upload & Process",
    ],
)

st.sidebar.divider()

st.sidebar.caption("MODIS–VIIRS HARMONIZATION")

if st.session_state.get("uploaded_dataset_active", False):
    st.sidebar.success("Uploaded dataset active")
else:
    st.sidebar.caption("Original project dataset active")

st.sidebar.caption("Historical observation mode")


# ----------------------------------------------------------
# UPLOAD PAGE
# ----------------------------------------------------------

if page == "Upload & Process":

    render_upload_page()


# ----------------------------------------------------------
# DASHBOARD FILTERS
# ----------------------------------------------------------

else:

    filters = render_filters(viirs, modis)

    viirs_filtered, modis_filtered = apply_filters(
        viirs,
        modis,
        filters,
    )

    # ======================================================
    # OVERVIEW
    # ======================================================

    if page == "Overview":

        st.markdown("## Observation overview")

        st.caption(
            "REGIONAL FIRE ACTIVITY / SATELLITE OBSERVATIONS"
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

        render_daily_activity(
            viirs_filtered,
            modis_filtered,
            full_width=True,
        )

    # ======================================================
    # DAILY FIRE ACTIVITY
    # ======================================================

    elif page == "Daily Fire Activity":

        st.markdown("## Temporal analytics")

        st.caption(
            "DAILY DETECTION TRENDS / FIRE RADIATIVE POWER"
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

    # ======================================================
    # DATA AND MATCHING
    # ======================================================

    elif page == "Data & Matching":

        st.markdown("## Data and matching laboratory")

        st.caption(
            "MATCHING DIAGNOSTICS / CANDIDATE ASSOCIATIONS"
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

    # ======================================================
    # DATA EXPLORER
    # ======================================================

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
st.sidebar.caption("Historical satellite data")

