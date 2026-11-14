
import pandas as pd
import streamlit as st
import plotly.express as px


BOX_FLAG = "modis_detected_box_30min"
DISTANCE_FLAG = "modis_detected_distance_1p5km_30min"


def _daily_counts(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    """Count detections by UTC calendar date."""

    if frame.empty or "time_utc" not in frame.columns:
        return pd.DataFrame(columns=["date", label])

    dates = pd.to_datetime(
        frame["time_utc"],
        errors="coerce",
        utc=True,
    ).dt.date

    counts = dates.dropna().value_counts().sort_index()

    return counts.rename_axis("date").reset_index(name=label)


def _frp_values(frame: pd.DataFrame) -> pd.Series:
    """Return valid numeric FRP values."""

    if frame.empty or "frp" not in frame.columns:
        return pd.Series(dtype="float64")

    values = pd.to_numeric(frame["frp"], errors="coerce")

    return (
        values
        .replace([float("inf"), float("-inf")], float("nan"))
        .dropna()
    )


def _flag_counts_by_date(
    frame: pd.DataFrame,
    flag_column: str,
    label: str,
) -> pd.DataFrame:
    """Count candidate matches by UTC date."""

    if (
        frame.empty
        or "time_utc" not in frame.columns
        or flag_column not in frame.columns
    ):
        return pd.DataFrame(columns=["date", label])

    dates = pd.to_datetime(
        frame["time_utc"],
        errors="coerce",
        utc=True,
    ).dt.date

    flags = pd.to_numeric(
        frame[flag_column],
        errors="coerce",
    ).fillna(0).eq(1)

    daily = pd.DataFrame({
        "date": dates,
        "matched": flags,
    }).dropna(subset=["date"])

    counts = (
        daily[daily["matched"]]
        .groupby("date")
        .size()
        .rename(label)
        .reset_index()
    )

    return counts


def render_daily_activity(
    viirs: pd.DataFrame,
    modis: pd.DataFrame,
    full_width: bool = False,
) -> None:
    """Compare daily VIIRS and MODIS detection activity."""

    viirs_daily = _daily_counts(viirs, "VIIRS")
    modis_daily = _daily_counts(modis, "MODIS")

    daily = pd.merge(
        viirs_daily,
        modis_daily,
        on="date",
        how="outer",
    ).fillna(0)

    if daily.empty:
        st.info(
            "No date-wise activity is available "
            "for the current filters."
        )
        return

    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date")

    chart_data = daily.melt(
        id_vars="date",
        value_vars=["VIIRS", "MODIS"],
        var_name="Sensor",
        value_name="Detections",
    )

    fig = px.line(
        chart_data,
        x="date",
        y="Detections",
        color="Sensor",
        markers=True,
        title="Daily Satellite Fire Detection Activity",
        labels={
            "date": "Observation date (UTC)",
            "Detections": "Number of detections",
        },
    )

    fig.update_layout(
        hovermode="x unified",
        legend_title="Satellite sensor",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="daily_activity_chart",
    )

    st.caption(
        "Daily counts are grouped by UTC calendar date. "
        "A detection count is not an estimate of unique fires."
    )


def render_frp_distribution(
    viirs: pd.DataFrame,
    modis: pd.DataFrame,
) -> None:
    """Compare FRP distributions and descriptive statistics."""

    frames = []

    for frame, sensor_name in [
        (viirs, "VIIRS"),
        (modis, "MODIS"),
    ]:
        values = _frp_values(frame)

        if not values.empty:
            frames.append(
                pd.DataFrame({
                    "FRP (MW)": values,
                    "Sensor": sensor_name,
                })
            )

    if not frames:
        st.info(
            "No FRP values available for the current filters."
        )
        return

    frp_data = pd.concat(frames, ignore_index=True)

    fig = px.histogram(
        frp_data,
        x="FRP (MW)",
        color="Sensor",
        nbins=40,
        barmode="overlay",
        opacity=0.65,
        title="Fire Radiative Power Distribution",
        labels={
            "count": "Number of detections",
            "FRP (MW)": "Fire Radiative Power (MW)",
        },
    )

    fig.update_layout(
        xaxis_title="Fire Radiative Power (MW)",
        yaxis_title="Number of detections",
        legend_title="Satellite sensor",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="frp_distribution_chart",
    )

    # Descriptive statistics for each sensor.
    statistics = []

    for sensor_name in ["VIIRS", "MODIS"]:
        sensor_values = frp_data.loc[
            frp_data["Sensor"] == sensor_name,
            "FRP (MW)",
        ]

        if sensor_values.empty:
            continue

        statistics.append({
            "Sensor": sensor_name,
            "Observations": len(sensor_values),
            "Mean FRP (MW)": round(sensor_values.mean(), 2),
            "Median FRP (MW)": round(sensor_values.median(), 2),
            "Maximum FRP (MW)": round(sensor_values.max(), 2),
        })

    st.markdown("**FRP summary statistics**")

    st.dataframe(
        pd.DataFrame(statistics),
        hide_index=True,
        use_container_width=True,
    )

    st.caption(
        "FRP is reported in megawatts. Statistics describe the "
        "currently filtered detections; they are not calibrated "
        "cross-sensor estimates."
    )


def render_matching_comparison(
    viirs: pd.DataFrame,
    chart_key: str = "matching_comparison_chart",
) -> None:
    """Compare the two VIIRS-to-MODIS candidate matching rules."""

    required = {BOX_FLAG, DISTANCE_FLAG}

    if not required.issubset(viirs.columns):
        st.info(
            "Matching flags are unavailable in the supplied VIIRS data."
        )
        return

    if viirs.empty:
        st.info(
            "Select Both or VIIRS in the sensor filter "
            "to view the matching comparison."
        )
        return

    box_flags = pd.to_numeric(
        viirs[BOX_FLAG],
        errors="coerce",
    ).fillna(0).eq(1)

    distance_flags = pd.to_numeric(
        viirs[DISTANCE_FLAG],
        errors="coerce",
    ).fillna(0).eq(1)

    total = len(viirs)

    box_count = int(box_flags.sum())
    distance_count = int(distance_flags.sum())

    comparison = pd.DataFrame({
        "Matching method": [
            "Pixel-box (30 min)",
            "Distance-only (1.5 km, 30 min)",
        ],
        "Candidate matches": [
            box_count,
            distance_count,
        ],
    })

    fig = px.bar(
        comparison,
        x="Matching method",
        y="Candidate matches",
        text="Candidate matches",
        title="MODIS–VIIRS Candidate Matching Comparison",
    )

    fig.update_traces(textposition="outside")

    fig.update_layout(
        yaxis_title="Number of VIIRS detections",
        xaxis_title="Matching method",
        showlegend=False,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key=chart_key,
    )

    col1, col2 = st.columns(2)

    box_percentage = (
        box_count / total * 100 if total else 0
    )

    distance_percentage = (
        distance_count / total * 100 if total else 0
    )

    col1.metric(
        "Pixel-box candidates",
        f"{box_count:,}",
        f"{box_percentage:.2f}% of filtered VIIRS",
    )

    col2.metric(
        "Distance-only candidates",
        f"{distance_count:,}",
        f"{distance_percentage:.2f}% of filtered VIIRS",
    )

    st.caption(
        "Percentages describe the share of filtered VIIRS detections "
        "flagged by each rule. These are candidate co-detection counts, "
        "not verified ground-truth detection rates."
    )


def render_daily_matching_trends(
    viirs: pd.DataFrame,
) -> None:
    """Compare daily candidate-match counts under both rules."""

    if viirs.empty:
        st.info(
            "No VIIRS observations are available "
            "for the current filters."
        )
        return

    box_daily = _flag_counts_by_date(
        viirs,
        BOX_FLAG,
        "Pixel-box (30 min)",
    )

    distance_daily = _flag_counts_by_date(
        viirs,
        DISTANCE_FLAG,
        "Distance-only (1.5 km, 30 min)",
    )

    if box_daily.empty and distance_daily.empty:
        st.info(
            "Daily matching trends cannot be calculated "
            "because the required matching flags are unavailable."
        )
        return

    daily = pd.merge(
        box_daily,
        distance_daily,
        on="date",
        how="outer",
    ).fillna(0)

    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date")

    chart_data = daily.melt(
        id_vars="date",
        var_name="Matching method",
        value_name="Candidate matches",
    )

    fig = px.line(
        chart_data,
        x="date",
        y="Candidate matches",
        color="Matching method",
        markers=True,
        title="Daily MODIS–VIIRS Candidate Matching Trends",
        labels={
            "date": "Observation date (UTC)",
            "Candidate matches": "Candidate matches",
        },
    )

    fig.update_layout(
        hovermode="x unified",
        legend_title="Matching method",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="daily_matching_trends_chart",
    )

    st.caption(
        "Daily candidate-match counts are based on VIIRS observation "
        "dates. The two methods represent alternative matching rules, "
        "not independent ground-truth validation."
    )

