"""
Interactive road-condition map (N5 / N-55 segments)
Run with:  streamlit run app.py
"""

import os

import folium
import streamlit as st
from src.route_section import prepare_n5_section, points_in_section
from streamlit_folium import st_folium

from src.config import (
    COUNTS_PATH,
    ETTM_COUNTS_PATH,
    DATASETS,
    DISTANCE_MARKER_MIN_ZOOM,
    MAJOR_CITIES,
    ROAD_ID_MAP,
    RSL_CATEGORIES,
    TRAFFIC_POPUP_CACHE_VERSION,
)
from src.data_loader import (
    condition_kilometers,
    prepare_count_stations,
    prepare_ettm_stations,
    road_status_categories,
    select_distance_markers,
)
from src.map_layers import (
    add_condition_legend,
    add_condition_corridor,
    add_distance_marker_zoom_toggle,
    add_distance_markers,
    add_major_city_markers,
    add_plain_road_corridor,
    add_station_markers,
)


EXCLUDED_COUNT_STATION_ADTS = {"4,630"}
EXCLUDED_ETTM_STATION_NAMES = {"Qutbal (ETTM)"}


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
        .stSelectbox > div, .stRadio > div, .stCheckbox > div {
            border-radius: 10px;
        }
        [data-testid="stSidebar"] button[aria-pressed="true"],
        [data-testid="stSidebar"] button[aria-selected="true"],
        [data-testid="stSidebar"] button[aria-pressed="true"] p,
        [data-testid="stSidebar"] button[aria-selected="true"] p,
        [data-testid="stSidebar"] button[aria-pressed="true"] span,
        [data-testid="stSidebar"] button[aria-selected="true"] span {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] .stSegmentedControl > div {
            background: rgba(148, 163, 184, 0.12);
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
            background: rgba(148, 163, 184, 0.12);
            border: 1px solid rgba(148, 163, 184, 0.32);
            border-radius: 10px;
        }
        .condition-key-title {
            font-size: 0.78rem;
            font-weight: 700;
            color: inherit;
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
            color: inherit;
            line-height: 1.2;
        }
        [data-testid="stAppViewContainer"][data-baseweb-theme="dark"] [data-testid="stSidebar"],
        [data-testid="stAppViewContainer"][data-theme="dark"] [data-testid="stSidebar"],
        html[data-baseweb-theme="dark"] [data-testid="stSidebar"],
        html[data-theme="dark"] [data-testid="stSidebar"],
        body[data-baseweb-theme="dark"] [data-testid="stSidebar"],
        body[data-theme="dark"] [data-testid="stSidebar"],
        [data-baseweb-theme="dark"] [data-testid="stSidebar"],
        [data-theme="dark"] [data-testid="stSidebar"],
        .stApp[data-baseweb-theme="dark"] [data-testid="stSidebar"],
        .stApp[data-theme="dark"] [data-testid="stSidebar"] {
            background: #111827 !important;
            border-right: 1px solid #334155 !important;
        }
        [data-testid="stAppViewContainer"][data-baseweb-theme="dark"] [data-testid="stSidebar"] :is(h1,h2,h3,p,label,span,div),
        [data-testid="stAppViewContainer"][data-theme="dark"] [data-testid="stSidebar"] :is(h1,h2,h3,p,label,span,div),
        html[data-baseweb-theme="dark"] [data-testid="stSidebar"] :is(h1,h2,h3,p,label,span,div),
        html[data-theme="dark"] [data-testid="stSidebar"] :is(h1,h2,h3,p,label,span,div),
        body[data-baseweb-theme="dark"] [data-testid="stSidebar"] :is(h1,h2,h3,p,label,span,div),
        body[data-theme="dark"] [data-testid="stSidebar"] :is(h1,h2,h3,p,label,span,div),
        [data-baseweb-theme="dark"] [data-testid="stSidebar"] :is(h1,h2,h3,p,label,span,div),
        [data-theme="dark"] [data-testid="stSidebar"] :is(h1,h2,h3,p,label,span,div),
        .stApp[data-baseweb-theme="dark"] [data-testid="stSidebar"] :is(h1,h2,h3,p,label,span,div),
        .stApp[data-theme="dark"] [data-testid="stSidebar"] :is(h1,h2,h3,p,label,span,div) {
            color: #f8fafc !important;
        }
        [data-testid="stAppViewContainer"][data-baseweb-theme="dark"] [data-testid="stSidebar"] .condition-key,
        [data-testid="stAppViewContainer"][data-theme="dark"] [data-testid="stSidebar"] .condition-key,
        html[data-baseweb-theme="dark"] [data-testid="stSidebar"] .condition-key,
        html[data-theme="dark"] [data-testid="stSidebar"] .condition-key,
        body[data-baseweb-theme="dark"] [data-testid="stSidebar"] .condition-key,
        body[data-theme="dark"] [data-testid="stSidebar"] .condition-key,
        [data-baseweb-theme="dark"] [data-testid="stSidebar"] .condition-key,
        [data-theme="dark"] [data-testid="stSidebar"] .condition-key,
        .stApp[data-baseweb-theme="dark"] [data-testid="stSidebar"] .condition-key,
        .stApp[data-theme="dark"] [data-testid="stSidebar"] .condition-key {
            background: rgba(31, 41, 55, 0.92) !important;
            border-color: rgba(148, 163, 184, 0.32) !important;
        }
        [data-testid="stAppViewContainer"][data-baseweb-theme="dark"] [data-testid="stSidebar"] button:not([aria-pressed="true"]):not([aria-selected="true"]),
        [data-testid="stAppViewContainer"][data-theme="dark"] [data-testid="stSidebar"] button:not([aria-pressed="true"]):not([aria-selected="true"]),
        html[data-baseweb-theme="dark"] [data-testid="stSidebar"] button:not([aria-pressed="true"]):not([aria-selected="true"]),
        html[data-theme="dark"] [data-testid="stSidebar"] button:not([aria-pressed="true"]):not([aria-selected="true"]),
        body[data-baseweb-theme="dark"] [data-testid="stSidebar"] button:not([aria-pressed="true"]):not([aria-selected="true"]),
        body[data-theme="dark"] [data-testid="stSidebar"] button:not([aria-pressed="true"]):not([aria-selected="true"]),
        [data-baseweb-theme="dark"] [data-testid="stSidebar"] button:not([aria-pressed="true"]):not([aria-selected="true"]),
        [data-theme="dark"] [data-testid="stSidebar"] button:not([aria-pressed="true"]):not([aria-selected="true"]),
        .stApp[data-baseweb-theme="dark"] [data-testid="stSidebar"] button:not([aria-pressed="true"]):not([aria-selected="true"]),
        .stApp[data-theme="dark"] [data-testid="stSidebar"] button:not([aria-pressed="true"]):not([aria-selected="true"]) {
            background: #111827 !important;
            border-color: #334155 !important;
        }
        [data-testid="stAppViewContainer"][data-baseweb-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]),
        [data-testid="stAppViewContainer"][data-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]),
        html[data-baseweb-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]),
        html[data-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]),
        body[data-baseweb-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]),
        body[data-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]),
        [data-baseweb-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]),
        [data-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]),
        .stApp[data-baseweb-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]),
        .stApp[data-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]) {
            background: #fb4b4b !important;
            border-color: #fb4b4b !important;
            color: #ffffff !important;
        }
        [data-testid="stAppViewContainer"][data-baseweb-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]) *,
        [data-testid="stAppViewContainer"][data-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]) *,
        html[data-baseweb-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]) *,
        html[data-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]) *,
        body[data-baseweb-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]) *,
        body[data-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]) *,
        [data-baseweb-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]) *,
        [data-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]) *,
        .stApp[data-baseweb-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]) *,
        .stApp[data-theme="dark"] [data-testid="stSidebar"] button:is([aria-pressed="true"],[aria-selected="true"]) * {
            color: #ffffff !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Road Condition Map")
st.caption("N5 · Multan to Peshawar")

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

    available_datasets = {name: path for name, path in DATASETS.items() if name == "N5" and os.path.exists(path)}
    if not available_datasets:
        st.error("No dataset files found. Place the .gpkg files in a subfolder named 'data'")
        st.stop()

    st.caption("N5 · Multan to Peshawar")
    selected_labels = ["N5"]
    section, n5_network, section_limits = prepare_n5_section(
        available_datasets["N5"],
        cache_version=(17, os.stat(available_datasets["N5"]).st_mtime_ns),
    )
    roads = {"N5": section}

    st.markdown("### Display options")

    direction_choice = st.pills(
        "Direction",
        ["North bound", "South bound"],
        default="North bound",
        selection_mode="single",
    )
    direction_choice = direction_choice or "North bound"
    direction_key = "north" if direction_choice == "North bound" else "south"

    st.markdown("### Layers")
    show_rsl = st.toggle("Road condition", value=True, help="Color roads by remaining service life.")
    show_distance_markers = st.toggle(
        "Distance markers",
        value=True,
        help="Show road kilometer badges at your selected interval.",
    )
    distance_marker_interval = 50
    if show_distance_markers:
        distance_marker_interval = st.slider(
            "Distance marker interval",
            min_value=5,
            max_value=100,
            value=50,
            step=5,
            format="%d km",
            help="Choose how often kilometer badges appear on the road.",
        )

    if show_rsl:
        sidebar_legend_rows = "".join(
            f'<div class="condition-key-row">'
            f'<span class="condition-key-line" style="border-top-color:{color};"></span>'
            f'<span class="condition-key-label">{label}</span></div>'
            for _, _, label, color in RSL_CATEGORIES
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

    show_major_cities = st.toggle(
        "Major cities",
        value=False,
        help="Highlight major cities along the selected highway(s).",
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
                and station["adt_text"] not in EXCLUDED_COUNT_STATION_ADTS
            ]

        else:
            st.warning(f"Counts file not found: {COUNTS_PATH}")
        if "N5" in selected_labels:
            if os.path.exists(ETTM_COUNTS_PATH):
                count_stations.extend(
                    station for station in prepare_ettm_stations(
                        ETTM_COUNTS_PATH, os.stat(ETTM_COUNTS_PATH).st_mtime_ns
                    )
                    if station["name"] not in EXCLUDED_ETTM_STATION_NAMES
                )
            else:
                st.warning(f"ETTM counts file not found: {ETTM_COUNTS_PATH}")
        count_stations = points_in_section(count_stations, n5_network, section_limits)
        if count_stations:
            st.caption(f"{len(count_stations)} traffic count station(s) shown.")
        else:
            st.caption("No count stations found for this selection.")

bounds_list = [roads[label]["bounds"] for label in selected_labels]
minx = min(b[0] for b in bounds_list)
miny = min(b[1] for b in bounds_list)
maxx = max(b[2] for b in bounds_list)
maxy = max(b[3] for b in bounds_list)
center_lat = (miny + maxy) / 2
center_lon = (minx + maxx) / 2
zoom_start = 6 if len(selected_labels) > 1 else 7

carto_key = st.secrets["CARTO_API_KEY"]

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=zoom_start,
    tiles=None,
    control_scale=True,
)

folium.TileLayer(
    tiles=f"https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png?key={carto_key}",
    attr="&copy; OpenStreetMap contributors &copy; CARTO",
    name="CARTO Positron",
    subdomains="abcd",
    max_zoom=20,
).add_to(m)

m.fit_bounds([[miny, minx], [maxy, maxx]], padding=(24, 24))

for label in selected_labels:
    road = roads[label]
    road_label = label if len(selected_labels) > 1 else ""

    if show_rsl:
        add_condition_corridor(m, road, direction_key)
    else:
        add_plain_road_corridor(m, road)

    if show_distance_markers:
        distance_markers = select_distance_markers(
            road["distance_markers"],
            distance_marker_interval,
        )
        add_distance_markers(
            m,
            distance_markers,
            road_label=road_label,
        )

if count_stations:
    add_station_markers(m, count_stations)

if show_major_cities:
    city_markers = [
        city
        for city in MAJOR_CITIES
        if city["road"] in selected_labels
    ]
    add_major_city_markers(m, points_in_section(city_markers, n5_network, section_limits))

if show_rsl:
    add_condition_legend(
        m,
        direction_choice,
        condition_kilometers(roads, selected_labels, direction_key),
        road_status_categories(roads, selected_labels, direction_key),
    )

if show_distance_markers:
    add_distance_marker_zoom_toggle(m)

with st.container(border=True):
    st_folium(
        m,
        width=None,
        height=680,
        returned_objects=[],
        key="road-map-N5-Multan-Peshawar",
    )

if show_rsl:
    distance_caption = (
        f"Distance badges appear every {distance_marker_interval} km when zoomed in to level {DISTANCE_MARKER_MIN_ZOOM} or closer. "
        if show_distance_markers
        else "Distance markers are hidden. "
    )
    caption_text = (
        "Grey dashed segments indicate missing data."
        f"{distance_caption}"
        "The legend shows displayed road length by supplied status category."
    )
else:
    distance_caption = (
        f"Distance badges appear every {distance_marker_interval} km when zoomed in to level {DISTANCE_MARKER_MIN_ZOOM} or closer."
        if show_distance_markers
        else "Distance markers are hidden."
    )
    caption_text = (
        "Road condition (remaining service life) layer is hidden. "
        f"{distance_caption}"
    )
if count_stations:
    caption_text += (
        " Traffic count stations are reduced when zoomed out and revealed progressively when "
        "zoomed in. Click a station marker for ADT, heavy traffic share, and vehicle categories."
    )
if show_major_cities:
    caption_text += " Major cities are highlighted along the selected highway route."
st.caption(caption_text)
