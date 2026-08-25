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
    MAJOR_CITIES,
    N5_NORTH_PATH,
    N5_SOUTH_PATH,
    N55_GEOMETRY_PATH,
    N55_NORTH_STATUS_PATH,
    N55_SOUTH_STATUS_PATH,
    NUMERIC_RSL_PREVIEW_DATASETS,
    ROAD_ID_MAP,
    ROAD_DATA_CACHE_VERSION,
    RSL_CATEGORIES,
    RSL_DEFAULT_THRESHOLDS,
    TRAFFIC_POPUP_CACHE_VERSION,
)
from src.data_loader import (
    build_rsl_categories,
    condition_kilometers,
    prepare_count_stations,
    prepare_road_data,
    prepare_n5_road_data,
    prepare_n55_road_data,
    road_status_categories,
    select_distance_markers,
    validate_rsl_thresholds,
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


st.set_page_config(
    page_title="Road Condition Map",
    page_icon=":material/map:",
    layout="wide",
)

st.session_state.setdefault("criteria_preview_active", False)
st.session_state.setdefault("criteria_preview_thresholds", RSL_DEFAULT_THRESHOLDS)

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
        .built-by-watermark {
            position: fixed;
            left: max(1rem, 22rem);
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
        @media (max-width: 760px) {
            .built-by-watermark {
                left: 0.75rem;
                right: auto;
                max-width: calc(100vw - 1.5rem);
            }
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
    roads = {}
    for label in selected_labels:
        if label == "N5":
            roads[label] = prepare_n5_road_data(
                N5_NORTH_PATH,
                N5_SOUTH_PATH,
                ROAD_DATA_CACHE_VERSION,
            )
        else:
            roads[label] = prepare_n55_road_data(
                N55_GEOMETRY_PATH,
                N55_NORTH_STATUS_PATH,
                N55_SOUTH_STATUS_PATH,
                ROAD_DATA_CACHE_VERSION,
            )

    missing_files = [name for name in DATASETS if name not in available_datasets]
    if missing_files:
        st.caption(f"Not found: {', '.join(missing_files)}")

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
        value=highway_choice != "Both",
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
            ]

            if not count_stations:
                st.caption("No count stations found for this selection.")
            else:
                st.caption(f"{len(count_stations)} traffic count station(s) shown.")
        else:
            st.warning(f"Counts file not found: {COUNTS_PATH}")

preview_paths = {
    label: NUMERIC_RSL_PREVIEW_DATASETS[label]
    for label in selected_labels
    if os.path.exists(NUMERIC_RSL_PREVIEW_DATASETS.get(label, ""))
}
preview_map_active = (
    st.session_state.criteria_preview_active
    and len(preview_paths) == len(selected_labels)
)
if preview_map_active:
    roads = {
        label: prepare_road_data(
            preview_paths[label],
            ROAD_DATA_CACHE_VERSION,
            st.session_state.criteria_preview_thresholds,
        )
        for label in selected_labels
    }

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
    add_major_city_markers(m, city_markers)

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
        key=(
            f"road-map-{'-'.join(selected_labels)}-"
            f"{'preview' if preview_map_active else 'live'}-"
            f"{','.join(str(value) for value in st.session_state.criteria_preview_thresholds)}"
        ),
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
        " Traffic count stations group when zoomed out and separate when zoomed in. Click an "
        "individual station marker for ADT, heavy traffic share, and vehicle categories."
    )
if show_major_cities:
    caption_text += " Major cities are highlighted along the selected highway route."
if preview_map_active:
    caption_text += (
        " Criteria preview map is active and uses the separate numeric RSL reference files. "
        "Reset preview to return to the live status-based map."
    )
st.caption(caption_text)

st.markdown("### Criteria preview")
show_criteria_preview = st.toggle(
    "Preview different service-life criteria",
    value=False,
    help="Run a read-only comparison using the numeric RSL reference files. This does not change the active map or source data.",
)

if show_criteria_preview:
    missing_preview_paths = [label for label in selected_labels if label not in preview_paths]

    with st.container(border=True):
        st.caption(
            "Read-only scenario analysis. The preview uses the separate numeric RSL reference files in "
            "data/ and does not change the active status-based map or any data files."
        )

        with st.form("criteria_preview_form", border=False):
            st.markdown("#### Scenario thresholds")
            preview_very_poor_end = st.number_input(
                "Very Poor ends before (years)",
                min_value=0.5,
                max_value=100.0,
                value=float(st.session_state.criteria_preview_thresholds[0]),
                step=0.5,
            )
            preview_poor_end = st.number_input(
                "Poor ends before (years)",
                min_value=0.5,
                max_value=100.0,
                value=float(st.session_state.criteria_preview_thresholds[1]),
                step=0.5,
            )
            preview_fair_end = st.number_input(
                "Fair ends before (years)",
                min_value=0.5,
                max_value=100.0,
                value=float(st.session_state.criteria_preview_thresholds[2]),
                step=0.5,
            )
            run_preview = st.form_submit_button("Run preview")

        if missing_preview_paths:
            st.warning(
                "Numeric preview data is unavailable for: "
                + ", ".join(missing_preview_paths)
                + "."
            )
        elif run_preview:
            scenario_thresholds = (
                preview_very_poor_end,
                preview_poor_end,
                preview_fair_end,
            )
            try:
                scenario_thresholds = validate_rsl_thresholds(scenario_thresholds)
            except ValueError as error:
                st.error(str(error))
            else:
                st.session_state.criteria_preview_thresholds = scenario_thresholds
                st.session_state.criteria_preview_active = True
                st.rerun()

        if st.session_state.criteria_preview_active and not missing_preview_paths:
            if st.button("Reset preview"):
                st.session_state.criteria_preview_active = False
                st.session_state.criteria_preview_thresholds = RSL_DEFAULT_THRESHOLDS
                st.rerun()

            scenario_thresholds = st.session_state.criteria_preview_thresholds
            baseline_thresholds = RSL_DEFAULT_THRESHOLDS
            baseline_categories = build_rsl_categories(baseline_thresholds)
            scenario_categories = build_rsl_categories(scenario_thresholds)
            baseline_roads = {
                label: prepare_road_data(
                    preview_paths[label],
                    ROAD_DATA_CACHE_VERSION,
                    baseline_thresholds,
                )
                for label in selected_labels
            }
            scenario_roads = {
                label: prepare_road_data(
                    preview_paths[label],
                    ROAD_DATA_CACHE_VERSION,
                    scenario_thresholds,
                )
                for label in selected_labels
            }
            baseline_totals = condition_kilometers(
                baseline_roads,
                selected_labels,
                direction_key,
            )
            scenario_totals = condition_kilometers(
                scenario_roads,
                selected_labels,
                direction_key,
            )
            baseline_poor_label = baseline_categories[1][2]
            scenario_poor_label = scenario_categories[1][2]
            baseline_poor_km = baseline_totals.get(baseline_poor_label, 0.0)
            scenario_poor_km = scenario_totals.get(scenario_poor_label, 0.0)

            metric_cols = st.columns(3)
            metric_cols[0].metric("Baseline poor", f"{baseline_poor_km:,.1f} km")
            metric_cols[1].metric("Scenario poor", f"{scenario_poor_km:,.1f} km")
            metric_cols[2].metric(
                "Change",
                f"{scenario_poor_km - baseline_poor_km:+,.1f} km",
            )

            preview_rows = []
            for baseline_category, scenario_category in zip(
                baseline_categories,
                scenario_categories,
            ):
                baseline_label = baseline_category[2]
                scenario_label = scenario_category[2]
                baseline_km = baseline_totals.get(baseline_label, 0.0)
                scenario_km = scenario_totals.get(scenario_label, 0.0)
                preview_rows.append(
                    {
                        "Category": scenario_label,
                        "Baseline km": f"{baseline_km:,.1f}",
                        "Scenario km": f"{scenario_km:,.1f}",
                        "Change km": f"{scenario_km - baseline_km:+,.1f}",
                    }
                )
            st.dataframe(preview_rows, hide_index=True, width="stretch")
