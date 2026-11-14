import pandas as pd
import streamlit as st


def _daily_counts(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    if "time_utc" not in frame.columns:
        return pd.DataFrame(columns=["date", label])

    dates = pd.to_datetime(frame["time_utc"], errors="coerce", utc=True).dt.date
    counts = dates.dropna().value_counts().sort_index()
    return counts.rename_axis("date").reset_index(name=label)


def render_daily_activity(
    viirs: pd.DataFrame,
    modis: pd.DataFrame,
    full_width: bool = False,
) -> None:
    viirs_daily = _daily_counts(viirs, "VIIRS")
    modis_daily = _daily_counts(modis, "MODIS")

    daily = pd.merge(viirs_daily, modis_daily, on="date", how="outer").fillna(0)
    if daily.empty:
        st.info("No date-wise activity is available for the current filters.")
        return

    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.set_index("date").sort_index()

    st.bar_chart(daily, use_container_width=True)
    st.caption("Counts are grouped by UTC calendar date from time_utc.")
