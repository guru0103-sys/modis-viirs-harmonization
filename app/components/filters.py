import pandas as pd
import streamlit as st


def _options(series):
    if series is None:
        return []
    return sorted(series.dropna().astype(str).unique().tolist())


def render_filters(viirs: pd.DataFrame, modis: pd.DataFrame) -> dict:
    """Render common sidebar filters. Date filtering uses time_utc."""
    st.sidebar.header("Filters")

    all_dates = []
    for frame in (viirs, modis):
        if "time_utc" in frame.columns:
            dates = pd.to_datetime(frame["time_utc"], errors="coerce").dropna()
            if not dates.empty:
                all_dates.extend([dates.min().date(), dates.max().date()])

    if all_dates:
        min_date, max_date = min(all_dates), max(all_dates)
        date_value = st.sidebar.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(date_value, tuple) and len(date_value) == 2:
            start_date, end_date = date_value
        elif isinstance(date_value, tuple) and len(date_value) == 1:
            start_date = end_date = date_value[0]
        else:
            start_date = end_date = date_value
    else:
        start_date = end_date = None
        st.sidebar.warning("No valid time_utc values found.")

    sensor = st.sidebar.selectbox("Sensor", ["Both", "VIIRS", "MODIS"])
    daynight_options = sorted(
        set(_options(viirs.get("daynight")) + _options(modis.get("daynight")))
    )
    daynight = st.sidebar.selectbox(
        "Day / Night", ["Both"] + daynight_options
    )

    confidence_options = sorted(
        set(_options(viirs.get("conf_class")) + _options(modis.get("conf_class")))
    )
    confidence = st.sidebar.selectbox(
        "Confidence", ["All"] + confidence_options
    )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "sensor": sensor,
        "daynight": daynight,
        "confidence": confidence,
    }


def apply_filters(
    viirs: pd.DataFrame, modis: pd.DataFrame, filters: dict
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the same date/day-night/confidence choices to both datasets."""
    def filter_frame(frame):
        result = frame.copy()

        if filters["start_date"] is not None and "time_utc" in result.columns:
            timestamps = pd.to_datetime(result["time_utc"], errors="coerce", utc=True)
            # Compare calendar dates in UTC, matching the time_utc column contract.
            dates = timestamps.dt.date
            mask = (
                (dates >= filters["start_date"])
                & (dates <= filters["end_date"])
            )
            result = result.loc[mask]

        if filters["daynight"] != "Both" and "daynight" in result.columns:
            result = result[
                result["daynight"].astype(str).str.upper()
                == filters["daynight"].upper()
            ]

        if filters["confidence"] != "All" and "conf_class" in result.columns:
            result = result[
                result["conf_class"].astype(str).str.lower()
                == filters["confidence"].lower()
            ]

        return result

    viirs_filtered = filter_frame(viirs)
    modis_filtered = filter_frame(modis)

    if filters["sensor"] == "VIIRS":
        modis_filtered = modis_filtered.iloc[0:0]
    elif filters["sensor"] == "MODIS":
        viirs_filtered = viirs_filtered.iloc[0:0]

    return viirs_filtered, modis_filtered
