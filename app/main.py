import streamlit as st
import pandas as pd

from utils.data_loader import load_datasets
from components.filters import render_filters, apply_filters
from components.metrics import render_metrics
from components.charts import render_daily_activity
from components.map import render_map_placeholder

st.set_page_config(
    page_title="Punjab–Haryana Fire Intelligence",
    page_icon="🔥",
    layout="wide",
)

st.title("🔥 Punjab–Haryana Fire Intelligence")
st.caption("HISTORICAL FIRE ACTIVITY · OCT–NOV 2024")
st.divider()

@st.cache_data
def get_data():
    return load_datasets()

try:
    viirs, modis, matched_pairs = get_data()
except Exception as exc:
    st.error(f"Could not load the project data: {exc}")
    st.info("Check the CSV paths in the data/ folders and see README.md.")
    st.stop()

filters = render_filters(viirs, modis)
viirs_filtered, modis_filtered = apply_filters(viirs, modis, filters)

page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Daily Fire Activity", "Data & Matching"],
)

if page == "Overview":
    st.subheader("Fire detection summary")
    render_metrics(viirs_filtered, modis_filtered)

    st.divider()
    left, right = st.columns([1.5, 1])
    with left:
        st.subheader("Daily fire activity")
        render_daily_activity(viirs_filtered, modis_filtered)
    with right:
        st.subheader("Fire hotspot map")
        render_map_placeholder(viirs_filtered)

elif page == "Daily Fire Activity":
    st.subheader("Date-wise fire activity")
    render_daily_activity(viirs_filtered, modis_filtered, full_width=True)

elif page == "Data & Matching":
    st.subheader("Filtered dataset overview")
    st.write(f"VIIRS rows after filters: **{len(viirs_filtered):,}**")
    st.write(f"MODIS rows after filters: **{len(modis_filtered):,}**")
    st.caption(
        "Matching flags are read from the existing scientific output. "
        "This frontend does not modify or recalculate the matching results."
    )
    st.subheader("VIIRS filtered data")
    st.dataframe(viirs_filtered, use_container_width=True)
    st.subheader("MODIS filtered data")
    st.dataframe(modis_filtered, use_container_width=True)

st.sidebar.divider()
st.sidebar.caption("MODIS–VIIRS Harmonization Project")
