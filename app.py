"""
Interactive road-condition map (N5 / N-55 segments)
Run with:  streamlit run app.py
"""

import os

import folium
import streamlit as st
from streamlit_folium import st_folium

from src.config import (
    COUNTS_PATH,
    DATASETS,
    DISTANCE_MARKER_MIN_ZOOM,
    NODATA_COLOR,
    NODATA_LABEL,
    ROAD_ID_MAP,
    ROAD_DATA_CACHE_VERSION,
    RSL_CATEGORIES,
    TRAFFIC_POPUP_CACHE_VERSION,
)
from src.data_loader import condition_percentages, prepare_count_stations, prepare_road_data
from src.map_layers import (
    add_condition_legend,
    add_condition_corridor,
    add_distance_marker_zoom_toggle,
    add_distance_markers,
    add_plain_road_corridor,
    add_station_markers,
)


st.set_page_config(
    page_title="Road Condition Map",
    page_icon=":material/map:",
    layout="wide",
)

st.markdown(
    """
    <style>
        .main > div {
            padding-top: 1.2rem;
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        .stSidebar {
            background: linear-gradient(180deg, #f4f7fb 0%, #edf3f8 100%);
        }
        .stSidebar .st-bq, .stSidebar .st-emotion-cache-1v0mbdj {
            background: rgba(255,255,255,0.7);
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 12px;
            padding: 0.75rem 0.8rem;
        }
        .stSelectbox > div, .stRadio > div, .stCheckbox > div {
            border-radius: 10px;
        }
        .stSegmentedControl > div {
            background: #eef4ff;
            border-radius: 12px;
            padding: 0.15rem;
        }
        .stMetric {
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 14px;
            padding: 0.8rem 1rem;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05);
        }
        .metric-label {
            font-size: 0.8rem;
            color: #475569;
            letter-spacing: 0.02em;
        }
        .metric-value {
            font-size: 1.6rem;
            font-weight: 700;
            color: #0f172a;
        }
        .condition-key {
            margin: 0.65rem 0 0.75rem 0;
            padding: 0.75rem 0.85rem;
            background: rgba(255, 255, 255, 0.58);
            border: 1px solid rgba(15, 23, 42, 0.12);
            border-radius: 10px;
        }
        .condition-key-title {
            font-size: 0.78rem;
            font-weight: 700;
            color: #475569;
            margin-bottom: 0.45rem;
        }
        .condition-key-row {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            margin: 0.32rem 0;
        }
        .condition-key-line {
            display: inline-block;
            width: 34px;
            border-top-width: 5px;
            border-top-style: solid;
            border-radius: 999px;
            flex: 0 0 34px;
        }
        .condition-key-label {
            font-size: 0.86rem;
            color: #0f172a;
            line-height: 1.2;
        }
        .built-by-watermark {
            position: fixed;
            right: 1.25rem;
            bottom: 0.85rem;
            z-index: 999;
            padding: 0.42rem 0.72rem;
            border: 1px solid rgba(15, 23, 42, 0.12);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.86);
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.10);
            color: #334155;
            font-size: 0.76rem;
            font-weight: 600;
            backdrop-filter: blur(8px);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Road Condition Map")
st.caption("Interactive Highway Condition Monitoring")

st.markdown(
    """
    <div class="built-by-watermark">
        Built by Zohaib Shafqat, AI Engineer
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style='padding:0.35rem 0 1rem 0;'>
        <span style='display:inline-block;padding:0.25rem 0.65rem;border-radius:999px;background:#eaf2ff;color:#1d4ed8;font-weight:600;font-size:0.8rem;'>Network monitoring</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Controls")

    available_datasets = {name: path for name, path in DATASETS.items() if os.path.exists(path)}
    if not available_datasets:
        st.error("No dataset files found. Place the .gpkg files in a subfolder named 'data'")
        st.stop()

    highway_labels = list(available_datasets.keys())
    highway_options = ["Both"] + highway_labels if len(highway_labels) > 1 else highway_labels
    highway_choice = st.segmented_control(
        "Highway",
        options=highway_options,
        default="Both" if len(highway_options) > 1 else highway_labels[0],
        selection_mode="single",
    )

    selected_labels = highway_labels if highway_choice == "Both" else [highway_choice]
    roads = {
        label: prepare_road_data(available_datasets[label], ROAD_DATA_CACHE_VERSION)
        for label in selected_labels
    }

    missing_files = [name for name in DATASETS if name not in available_datasets]
    if missing_files:
        st.caption(f"Not found: {', '.join(missing_files)}")

    st.markdown("### Display options")

    direction_choice = st.pills(
        "Direction",
        ["North bound", "South bound", "Average (both directions)"],
        default="North bound",
        selection_mode="single",
    )
    direction_choice = direction_choice or "North bound"
    if direction_choice == "Average (both directions)":
        st.caption(
            "Averages both lanes; if one lane is missing data, the other lane's "
            "value is used instead."
        )

    if direction_choice == "Average (both directions)":
        direction_key = "average"
    else:
        direction_key = "north" if direction_choice == "North bound" else "south"

    st.markdown("### Layers")
    show_rsl = st.toggle("Road condition", value=True, help="Color roads by remaining service life.")
    show_distance_markers = st.toggle(
        "Distance markers",
        value=highway_choice != "Both",
        help="Show road markers every 50 km.",
    )

    if show_rsl:
        sidebar_legend_rows = "".join(
            f'<div class="condition-key-row">'
            f'<span class="condition-key-line" style="border-top-color:{color};"></span>'
            f'<span class="condition-key-label">{label}</span></div>'
            for _, _, label, color in RSL_CATEGORIES
        )
        sidebar_legend_rows += (
            f'<div class="condition-key-row">'
            f'<span class="condition-key-line" style="border-top-color:{NODATA_COLOR};border-top-style:dashed;"></span>'
            f'<span class="condition-key-label">Single Carriageway</span></div>'
        )
        st.markdown(
            f"""
            <div class="condition-key">
                <div class="condition-key-title">Remaining Service Life</div>
                {sidebar_legend_rows}
            </div>
            """,
            unsafe_allow_html=True,
        )

    show_counts = st.toggle("Traffic count stations", value=False, help="Show traffic count markers for the selected road(s).")

    count_stations = []
    if show_counts:
        if os.path.exists(COUNTS_PATH):
            wanted_road_ids = [ROAD_ID_MAP.get(lbl) for lbl in selected_labels]
            count_stations = [
                station
                for station in prepare_count_stations(COUNTS_PATH, TRAFFIC_POPUP_CACHE_VERSION)
                if station["road_id"] in wanted_road_ids
            ]
            if not count_stations:
                st.caption("No count stations found for this selection.")
            else:
                st.caption(f"")
        else:
            st.warning(f"Counts file not found: {COUNTS_PATH}")

bounds_list = [roads[label]["bounds"] for label in selected_labels]
minx = min(b[0] for b in bounds_list)
miny = min(b[1] for b in bounds_list)
maxx = max(b[2] for b in bounds_list)
maxy = max(b[3] for b in bounds_list)
center_lat = (miny + maxy) / 2
center_lon = (minx + maxx) / 2
zoom_start = 6 if len(selected_labels) > 1 else 7

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=zoom_start,
    tiles="CartoDB positron",
    control_scale=True,
)

for label in selected_labels:
    road = roads[label]
    road_label = label if len(selected_labels) > 1 else ""

    if show_rsl:
        add_condition_corridor(m, road, direction_key)
    else:
        add_plain_road_corridor(m, road)

    if show_distance_markers:
        add_distance_markers(
            m,
            road["distance_markers"],
            road_label=road_label,
        )

if count_stations:
    add_station_markers(m, count_stations)

if show_rsl:
    add_condition_legend(
        m,
        condition_percentages(roads, selected_labels, direction_key),
        direction_choice,
    )

if show_distance_markers:
    add_distance_marker_zoom_toggle(m)

with st.container(border=True):
    st_folium(
        m,
        width=None,
        height=680,
        returned_objects=[],
        key="road-map",
    )

if show_rsl:
    distance_caption = (
        f"Distance badges appear every 50 km when zoomed in to level {DISTANCE_MARKER_MIN_ZOOM} or closer. "
        if show_distance_markers
        else "Distance markers are hidden. "
    )
    caption_text = (
        "Grey dashed segments indicate missing data."
        f"{distance_caption}"
        "The legend shows what share of the displayed road length falls in each condition category."
    )
else:
    distance_caption = (
        f"Distance badges appear every 50 km when zoomed in to level {DISTANCE_MARKER_MIN_ZOOM} or closer."
        if show_distance_markers
        else "Distance markers are hidden."
    )
    caption_text = (
        "Road condition (remaining service life) layer is hidden. "
        f"{distance_caption}"
    )
if count_stations:
    caption_text += (
        " Traffic count stations are shown as direct map markers. Click a station marker for ADT, "
        "heavy traffic share, and vehicle categories."
    )
st.caption(caption_text)
