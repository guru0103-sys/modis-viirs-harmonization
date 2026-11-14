import pandas as pd
import streamlit as st


def render_map_placeholder(viirs: pd.DataFrame) -> None:
    """Temporary Person 1 map view; Person 2 can replace this component."""
    required = {"latitude", "longitude"}
    if not required.issubset(viirs.columns):
        st.info("Map will appear when latitude and longitude columns are available.")
        return

    points = viirs[["latitude", "longitude"]].copy()
    points["latitude"] = pd.to_numeric(points["latitude"], errors="coerce")
    points["longitude"] = pd.to_numeric(points["longitude"], errors="coerce")
    points = points.dropna()

    if points.empty:
        st.info("No VIIRS coordinates remain after applying the filters.")
        return

    st.map(points, latitude="latitude", longitude="longitude")
    st.caption("Basic VIIRS point map. Person 2 will integrate the interactive hotspot map.")
