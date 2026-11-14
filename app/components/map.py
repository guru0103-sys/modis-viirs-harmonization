
import pandas as pd
import streamlit as st
import pydeck as pdk


DARK_MAP_STYLE = (
    "https://basemaps.cartocdn.com/gl/"
    "dark-matter-gl-style/style.json"
)

MATCH_FLAG = "modis_detected_box_30min"

PLAYBACK_INDEX_KEY = "fire_playback_index"
PLAYBACK_STATE_KEY = "fire_playback_running"
PLAYBACK_SLIDER_KEY = "fire_playback_slider"
PLAYBACK_SIGNATURE_KEY = "fire_playback_signature"

LAYER_MATCHED_KEY = "map_show_viirs_matched"
LAYER_UNMATCHED_KEY = "map_show_viirs_unmatched"
LAYER_MODIS_KEY = "map_show_modis"
POINT_RADIUS_KEY = "map_point_radius"


def prepare_points(
    frame: pd.DataFrame,
    sensor: str,
) -> pd.DataFrame:
    """Prepare valid coordinates and tooltip fields."""

    if frame.empty:
        return pd.DataFrame()

    required = {"latitude", "longitude"}

    if not required.issubset(frame.columns):
        return pd.DataFrame()

    points = frame.copy()

    points["latitude"] = pd.to_numeric(
        points["latitude"], errors="coerce"
    )
    points["longitude"] = pd.to_numeric(
        points["longitude"], errors="coerce"
    )

    points = points.dropna(
        subset=["latitude", "longitude"]
    )

    if points.empty:
        return pd.DataFrame()

    points["sensor"] = sensor

    if sensor == "VIIRS":
        if MATCH_FLAG in points.columns:
            points["match_status"] = (
                pd.to_numeric(
                    points[MATCH_FLAG],
                    errors="coerce",
                )
                .fillna(0)
                .eq(1)
            )
        else:
            points["match_status"] = False

        points["status_label"] = points["match_status"].map(
            {
                True: "Candidate match",
                False: "No candidate match",
            }
        )

    else:
        points["match_status"] = False
        points["status_label"] = "MODIS detection"

    for column in [
        "time_utc",
        "frp",
        "daynight",
        "conf_class",
    ]:
        if column not in points.columns:
            points[column] = "N/A"

    points["frp"] = pd.to_numeric(
        points["frp"],
        errors="coerce",
    )

    return points


def get_available_dates(
    viirs: pd.DataFrame,
    modis: pd.DataFrame,
    selected_sensor: str,
) -> list:
    """Get sorted UTC observation dates."""

    frames = []

    if selected_sensor in ("Both", "VIIRS"):
        frames.append(viirs)

    if selected_sensor in ("Both", "MODIS"):
        frames.append(modis)

    available_dates = set()

    for frame in frames:
        if frame.empty or "time_utc" not in frame.columns:
            continue

        timestamps = pd.to_datetime(
            frame["time_utc"],
            errors="coerce",
            utc=True,
        )

        available_dates.update(
            timestamps.dropna().dt.date.tolist()
        )

    return sorted(available_dates)


def step_playback(direction: int, max_index: int) -> None:
    """Move playback by one observation date."""

    current = st.session_state.get(
        PLAYBACK_SLIDER_KEY,
        0,
    )

    new_index = max(
        0,
        min(max_index, current + direction),
    )

    st.session_state[PLAYBACK_INDEX_KEY] = new_index
    st.session_state[PLAYBACK_SLIDER_KEY] = new_index
    st.session_state[PLAYBACK_STATE_KEY] = False


def toggle_playback() -> None:
    """Toggle automatic playback."""

    st.session_state[PLAYBACK_STATE_KEY] = not (
        st.session_state.get(PLAYBACK_STATE_KEY, False)
    )


def filter_by_date(
    frame: pd.DataFrame,
    selected_date,
) -> pd.DataFrame:
    """Filter observations by UTC calendar date."""

    if frame.empty or "time_utc" not in frame.columns:
        return frame.iloc[0:0].copy()

    timestamps = pd.to_datetime(
        frame["time_utc"],
        errors="coerce",
        utc=True,
    )

    mask = timestamps.dt.date == selected_date

    return frame.loc[mask].copy()


def render_map(
    viirs: pd.DataFrame,
    modis: pd.DataFrame,
    selected_sensor: str,
    show_matched: bool,
    show_unmatched: bool,
    show_modis: bool,
    point_radius: int,
) -> None:
    """Render the independently controlled map layers."""

    layers = []
    displayed_count = 0

    viirs_points = pd.DataFrame()
    modis_points = pd.DataFrame()

    if selected_sensor in ("Both", "VIIRS"):
        viirs_points = prepare_points(viirs, "VIIRS")

        if not viirs_points.empty:

            matched_points = viirs_points[
                viirs_points["match_status"]
            ]

            unmatched_points = viirs_points[
                ~viirs_points["match_status"]
            ]

            if show_matched and not matched_points.empty:
                displayed_count += len(matched_points)

                layers.append(
                    pdk.Layer(
                        "ScatterplotLayer",
                        id="viirs-matched",
                        data=matched_points,
                        get_position="[longitude, latitude]",
                        get_fill_color=[235, 75, 65, 220],
                        get_radius=point_radius,
                        radius_min_pixels=3,
                        radius_max_pixels=13,
                        pickable=True,
                        auto_highlight=True,
                    )
                )

            if show_unmatched and not unmatched_points.empty:
                displayed_count += len(unmatched_points)

                layers.append(
                    pdk.Layer(
                        "ScatterplotLayer",
                        id="viirs-unmatched",
                        data=unmatched_points,
                        get_position="[longitude, latitude]",
                        get_fill_color=[255, 166, 55, 210],
                        get_radius=point_radius,
                        radius_min_pixels=3,
                        radius_max_pixels=13,
                        pickable=True,
                        auto_highlight=True,
                    )
                )

    if selected_sensor in ("Both", "MODIS") and show_modis:
        modis_points = prepare_points(modis, "MODIS")

        if not modis_points.empty:
            displayed_count += len(modis_points)

            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    id="modis-detections",
                    data=modis_points,
                    get_position="[longitude, latitude]",
                    get_fill_color=[65, 155, 255, 220],
                    get_radius=point_radius,
                    radius_min_pixels=3,
                    radius_max_pixels=13,
                    pickable=True,
                    auto_highlight=True,
                )
            )

    if not layers:
        st.info(
            "No visible hotspot layers. Enable a map layer "
            "or select another date."
        )
        return

    view_state = pdk.ViewState(
        latitude=30.5,
        longitude=75.5,
        zoom=6,
        pitch=0,
        bearing=0,
    )

    tooltip = {
        "html": """
        <div style="font-family: sans-serif; padding: 8px;">
            <b>{sensor}</b>
            <hr style="margin: 5px 0;">
            <b>Time:</b> {time_utc}<br/>
            <b>Latitude:</b> {latitude}<br/>
            <b>Longitude:</b> {longitude}<br/>
            <b>FRP:</b> {frp} MW<br/>
            <b>Day/Night:</b> {daynight}<br/>
            <b>Confidence:</b> {conf_class}<br/>
            <b>Matching:</b> {status_label}
        </div>
        """,
        "style": {
            "backgroundColor": "#172235",
            "color": "white",
            "border": "1px solid #34445c",
            "borderRadius": "8px",
        },
    }

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=DARK_MAP_STYLE,
        tooltip=tooltip,
    )

    st.pydeck_chart(
        deck,
        use_container_width=True,
        height=620,
    )

    st.markdown("**Visible map layers**")

    legend_items = []

    if selected_sensor in ("Both", "VIIRS"):
        if show_matched:
            legend_items.append("🔴 **VIIRS · Matched**")

        if show_unmatched:
            legend_items.append("🟠 **VIIRS · Unmatched**")

    if selected_sensor in ("Both", "MODIS") and show_modis:
        legend_items.append("🔵 **MODIS**")

    if legend_items:
        legend_cols = st.columns(len(legend_items))

        for column, label in zip(legend_cols, legend_items):
            column.markdown(label)

    st.caption(
        f"Displaying {displayed_count:,} visible hotspot locations. "
        "Candidate matches are algorithmic associations, "
        "not verified ground-truth detections."
    )


@st.fragment(run_every=1)
def render_playback(
    viirs: pd.DataFrame,
    modis: pd.DataFrame,
    selected_sensor: str,
    available_dates: list,
) -> None:
    """Render playback, layer controls and the historical map."""

    max_index = len(available_dates) - 1

    current_index = st.session_state.get(
        PLAYBACK_INDEX_KEY,
        0,
    )

    current_index = max(
        0,
        min(max_index, current_index),
    )

    if PLAYBACK_SLIDER_KEY not in st.session_state:
        st.session_state[PLAYBACK_SLIDER_KEY] = current_index

    st.markdown("**Historical observation playback**")

    st.slider(
        "Observation day",
        min_value=0,
        max_value=max_index,
        value=current_index,
        key=PLAYBACK_SLIDER_KEY,
    )

    selected_index = st.session_state[PLAYBACK_SLIDER_KEY]
    st.session_state[PLAYBACK_INDEX_KEY] = selected_index

    selected_date = available_dates[selected_index]

    st.caption(
        f"Selected observation date: "
        f"{selected_date.strftime('%d %B %Y')}"
    )

    control_cols = st.columns([1, 1, 1, 2])

    with control_cols[0]:
        st.button(
            "◀ Previous",
            use_container_width=True,
            disabled=selected_index == 0,
            on_click=step_playback,
            args=(-1, max_index),
        )

    with control_cols[1]:
        st.button(
            "▶ Play" if not st.session_state.get(
                PLAYBACK_STATE_KEY, False
            ) else "⏸ Pause",
            use_container_width=True,
            on_click=toggle_playback,
        )

    with control_cols[2]:
        st.button(
            "Next ▶",
            use_container_width=True,
            disabled=selected_index == max_index,
            on_click=step_playback,
            args=(1, max_index),
        )

    with control_cols[3]:
        st.markdown(
            f"**{selected_date.strftime('%d %B %Y')}**"
        )
        st.caption(
            f"Day {selected_index + 1} of {len(available_dates)}"
        )

    # ------------------------------------------------------
    # MAP LAYER CONTROLS
    # ------------------------------------------------------

    st.divider()
    st.markdown("**Map display controls**")

    layer_cols = st.columns(3)

    if selected_sensor in ("Both", "VIIRS"):

        with layer_cols[0]:
            st.checkbox(
                "VIIRS · Matched",
                value=True,
                key=LAYER_MATCHED_KEY,
            )

        with layer_cols[1]:
            st.checkbox(
                "VIIRS · Unmatched",
                value=True,
                key=LAYER_UNMATCHED_KEY,
            )

    if selected_sensor in ("Both", "MODIS"):

        with layer_cols[2]:
            st.checkbox(
                "MODIS detections",
                value=True,
                key=LAYER_MODIS_KEY,
            )

    point_radius = st.slider(
        "Hotspot point size",
        min_value=150,
        max_value=900,
        value=st.session_state.get(POINT_RADIUS_KEY, 450),
        step=50,
        key=POINT_RADIUS_KEY,
        help="Adjust the visual radius of the map markers.",
    )

    viirs_day = filter_by_date(viirs, selected_date)
    modis_day = filter_by_date(modis, selected_date)

    st.divider()

    render_map(
        viirs_day,
        modis_day,
        selected_sensor,
        st.session_state.get(LAYER_MATCHED_KEY, True),
        st.session_state.get(LAYER_UNMATCHED_KEY, True),
        st.session_state.get(LAYER_MODIS_KEY, True),
        point_radius,
    )

    # Advance one available observation date per second.
    if st.session_state.get(PLAYBACK_STATE_KEY, False):

        if selected_index < max_index:
            next_index = selected_index + 1

            st.session_state[PLAYBACK_INDEX_KEY] = next_index
            st.session_state[PLAYBACK_SLIDER_KEY] = next_index

        else:
            st.session_state[PLAYBACK_STATE_KEY] = False


def render_hotspot_map(
    viirs: pd.DataFrame,
    modis: pd.DataFrame,
    selected_sensor: str = "Both",
) -> None:
    """Render historical hotspot map with playback and layer controls."""

    available_dates = get_available_dates(
        viirs,
        modis,
        selected_sensor,
    )

    if not available_dates:
        st.warning(
            "No valid observation dates are available "
            "for the selected filters."
        )
        return

    signature = (
        str(available_dates[0]),
        str(available_dates[-1]),
        len(available_dates),
        selected_sensor,
    )

    if st.session_state.get(PLAYBACK_SIGNATURE_KEY) != signature:

        st.session_state[PLAYBACK_SIGNATURE_KEY] = signature
        st.session_state[PLAYBACK_INDEX_KEY] = 0
        st.session_state[PLAYBACK_SLIDER_KEY] = 0
        st.session_state[PLAYBACK_STATE_KEY] = False

    if len(available_dates) == 1:

        st.caption(
            f"Historical observations · "
            f"{available_dates[0].strftime('%d %B %Y')}"
        )

        st.markdown("**Map display controls**")

        layer_cols = st.columns(3)

        if selected_sensor in ("Both", "VIIRS"):
            with layer_cols[0]:
                st.checkbox(
                    "VIIRS · Matched",
                    value=True,
                    key=LAYER_MATCHED_KEY,
                )

            with layer_cols[1]:
                st.checkbox(
                    "VIIRS · Unmatched",
                    value=True,
                    key=LAYER_UNMATCHED_KEY,
                )

        if selected_sensor in ("Both", "MODIS"):
            with layer_cols[2]:
                st.checkbox(
                    "MODIS detections",
                    value=True,
                    key=LAYER_MODIS_KEY,
                )

        point_radius = st.slider(
            "Hotspot point size",
            min_value=150,
            max_value=900,
            value=st.session_state.get(POINT_RADIUS_KEY, 450),
            step=50,
            key=POINT_RADIUS_KEY,
        )

        render_map(
            filter_by_date(viirs, available_dates[0]),
            filter_by_date(modis, available_dates[0]),
            selected_sensor,
            st.session_state.get(LAYER_MATCHED_KEY, True),
            st.session_state.get(LAYER_UNMATCHED_KEY, True),
            st.session_state.get(LAYER_MODIS_KEY, True),
            point_radius,
        )

        return

    render_playback(
        viirs,
        modis,
        selected_sensor,
        available_dates,
    )

