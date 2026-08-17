"""
Interactive road-condition map (N5 / N-55 segments)
Run with:  streamlit run app.py
"""

import os
import math

import geopandas as gpd
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

NODATA_SENTINEL = -99

DATASETS = {
    "N5": os.path.join("data", "segments_N5.gpkg"),
    "N-55": os.path.join("data", "segments_N55.gpkg"),
}

COUNTS_PATH = os.path.join("data", "counts_N5_N55.gpkg")

# Maps the highway label used in DATASETS/the sidebar to the value found in
# the counts file's "Road.ID" column, so the counts layer can be filtered to
# match whichever road(s) are currently selected.
ROAD_ID_MAP = {
    "N5": "N-5",
    "N-55": "N55",
}

# Remaining service life category bins: (lower_inclusive, upper_exclusive, label, color)
RSL_CATEGORIES = [
    (0, 1, "Very Poor <1 year", "#d73027"),
    (1, 2, "Poor 1-2 years", "#fc8d59"),
    (2, 4, "Fair 2-4 years", "#fee08b"),
    #(3, 4, "Fair", "#fee08b"),
    (4, float("inf"), "Good >=4 years", "#1a9850"),
]
NODATA_LABEL = "No data"
NODATA_COLOR = "#888888"
GEOMETRY_SIMPLIFY_TOLERANCE = 0.00015
TRAFFIC_SHARE_BANDS = [
    ("Low", 0.15, "#1a9850", "#e8f5ec", "#b8dfc4"),
    ("Moderate", 0.25, "#d9a300", "#fff7d6", "#f0d36b"),
    ("High", 0.35, "#e85d2a", "#fff0e8", "#f3b59b"),
    ("Very high", float("inf"), "#c92a2a", "#ffe8e8", "#eba3a3"),
]

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
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Road Condition Map")
st.caption("Interactive Highway Condition Monitoring")

st.markdown(
    """
    <div style='padding:0.35rem 0 1rem 0;'>
        <span style='display:inline-block;padding:0.25rem 0.65rem;border-radius:999px;background:#eaf2ff;color:#1d4ed8;font-weight:600;font-size:0.8rem;'>Network monitoring</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
def classify_rsl(value):
    """Map a remaining-service-life value to (label, color)."""
    if value == NODATA_SENTINEL:
        return NODATA_LABEL, NODATA_COLOR
    for lo, hi, label, color in RSL_CATEGORIES:
        if lo <= value < hi:
            return label, color
    return NODATA_LABEL, NODATA_COLOR


def _is_valid_rsl(value):
    return pd.notna(value) and value != NODATA_SENTINEL


def average_rsl_value(north_value, south_value):
    north_valid = _is_valid_rsl(north_value)
    south_valid = _is_valid_rsl(south_value)

    if north_valid and south_valid:
        return (north_value + south_value) / 2
    if north_valid:
        return north_value
    if south_valid:
        return south_value
    return NODATA_SENTINEL


def popup_html(feature, label, direction_choice):
    if direction_choice == "Average (both directions)":
        north_value = feature["north_value"]
        south_value = feature["south_value"]
        north_valid = _is_valid_rsl(north_value)
        south_valid = _is_valid_rsl(south_value)

        if north_valid and south_valid:
            note = "average of both lanes"
        elif north_valid:
            note = "north bound only - south bound missing"
        elif south_valid:
            note = "south bound only - north bound missing"
        else:
            note = "no data on either lane"

        north_text = f"{north_value:.1f}" if north_valid else "No data"
        south_text = f"{south_value:.1f}" if south_valid else "No data"

        return f"""
        <b>km {feature['km']:.0f}</b><br>
        Remaining service life (average): {label}<br>
        <span style="font-size:11px;color:#555;">
        North: {north_text} yrs &nbsp;|&nbsp; South: {south_text} yrs<br>
        ({note})
        </span>
        """

    return f"""
    <b>km {feature['km']:.0f}</b><br>
    Remaining service life ({direction_choice}): {label}
    """


@st.cache_data(show_spinner="Loading road data...", max_entries=4)
def prepare_road_data(path):
    gdf = gpd.read_file(path)
    bounds = tuple(float(value) for value in gdf.total_bounds)

    if GEOMETRY_SIMPLIFY_TOLERANCE:
        display_gdf = gdf.copy()
        display_gdf["geometry"] = display_gdf.geometry.simplify(
            GEOMETRY_SIMPLIFY_TOLERANCE,
            preserve_topology=True,
        )
    else:
        display_gdf = gdf

    features = []
    for row in display_gdf.itertuples(index=False):
        geometry = row.geometry
        if geometry is None or geometry.is_empty:
            continue

        coords = tuple((lat, lon) for lon, lat in geometry.coords)
        if not coords:
            continue

        north_value = row.remaining_service_life_north
        south_value = row.remaining_service_life_south
        average_value = average_rsl_value(north_value, south_value)
        north_label, north_color = classify_rsl(north_value)
        south_label, south_color = classify_rsl(south_value)
        average_label, average_color = classify_rsl(average_value)
        features.append(
            {
                "km": float(row.km),
                "coords": coords,
                "length": float(geometry.length),
                "north_value": north_value,
                "north_label": north_label,
                "north_color": north_color,
                "south_value": south_value,
                "south_label": south_label,
                "south_color": south_color,
                "average_label": average_label,
                "average_color": average_color,
            }
        )

    distance_markers = build_distance_markers(gdf)
    return {
        "bounds": bounds,
        "features": features,
        "distance_markers": distance_markers,
    }


def build_distance_markers(gdf):
    """Precompute distance marker positions once per source file."""
    if "km" not in gdf.columns or gdf.empty:
        return []

    km_min = float(gdf["km"].min())
    km_max = float(gdf["km"].max())
    if km_max <= km_min:
        return []

    start = int(math.ceil(km_min / 50.0) * 50)
    if start == 0:
        start = 50  # skip the 0 km marker, it clutters the start of the road

    markers = []
    for target_km in range(start, int(km_max) + 1, 50):
        idx = (gdf["km"] - target_km).abs().idxmin()
        row = gdf.loc[idx]
        coords = list(row.geometry.coords)
        lon, lat = coords[len(coords) // 2]
        markers.append({"km": target_km, "lat": lat, "lon": lon})
    return markers


def add_distance_markers(fmap, markers, road_label=""):
    """Add a circular badge with the km reading every 50 km along a road."""
    for marker in markers:
        target_km = marker["km"]
        title_attr = f"{target_km} km" + (f" ({road_label})" if road_label else "")

        badge_html = (
            '<div title="' + title_attr + '" style="'
            "width:32px;height:32px;border-radius:50%;background:white;"
            "border:2px solid #333;display:flex;flex-direction:column;"
            "align-items:center;justify-content:center;line-height:1;"
            'box-shadow:1px 1px 4px rgba(0,0,0,0.35);">'
            f'<span style="font-size:10px;font-weight:bold;color:#222;">{target_km}</span>'
            '<span style="font-size:6px;color:#555;">km</span>'
            "</div>"
        )

        folium.map.Marker(
            [marker["lat"], marker["lon"]],
            icon=folium.DivIcon(html=badge_html, icon_size=(32, 32), icon_anchor=(16, 16)),
        ).add_to(fmap)


def heavy_share_style(share):
    """Return label and colors for a count station's heavy-traffic share."""
    if share is None or pd.isna(share):
        return {
            "label": "No data",
            "color": "#64748b",
            "background": "#f1f5f9",
            "border": "#cbd5e1",
        }

    for label, upper_bound, color, background, border in TRAFFIC_SHARE_BANDS:
        if share < upper_bound:
            return {
                "label": label,
                "color": color,
                "background": background,
                "border": border,
            }


def format_count(value):
    if value >= 1000:
        return f"{value / 1000:.1f}k"
    return f"{value:.0f}"


def build_count_marker_html(station):
    return f"""
    <div style="position:relative;display:flex;align-items:center;gap:5px;
        font-family:Inter,Segoe UI,Arial,sans-serif;transform:translate(-14px,-14px);">
        <div style="width:22px;height:22px;border-radius:50%;background:{station['color']};
            border:3px solid white;box-shadow:0 2px 8px rgba(15,23,42,.35);
            display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <div style="width:7px;height:7px;border-radius:50%;background:white;"></div>
        </div>
        <div style="background:rgba(255,255,255,.96);border:1px solid {station['border']};
            border-left:3px solid {station['color']};border-radius:7px;padding:2px 7px 3px 6px;
            box-shadow:0 2px 8px rgba(15,23,42,.22);line-height:1;white-space:nowrap;">
            <div style="font-size:9px;color:#64748b;font-weight:700;letter-spacing:.03em;">AADT</div>
            <div style="font-size:12px;color:#0f172a;font-weight:800;margin-top:1px;">{station['adt_compact']}</div>
        </div>
    </div>
    """


def safe_num(row, col):
    val = row.get(col)
    try:
        return float(val) if pd.notna(val) else 0.0
    except (TypeError, ValueError):
        return 0.0


def build_counts_popup(row):
    adt = safe_num(row, "ADT")
    heavy = safe_num(row, "heavy_traffic")
    heavy_share = row.get("heavy_share")
    heavy_pct = f"{float(heavy_share) * 100:.1f}%" if pd.notna(heavy_share) else "N/A"

    cars = safe_num(row, "cars")
    mc = safe_num(row, "mc")
    rickshaws = safe_num(row, "rickshaws")
    light_pickup = safe_num(row, "light_pickup")
    mini_bus = safe_num(row, "mini_bus")
    large_bus = safe_num(row, "large_bus")

    return f"""
    <div style="font-family:Inter,Segoe UI,Arial,sans-serif;min-width:300px;color:#0f172a;">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;">
            <div style="border:1px solid #e2e8f0;border-radius:8px;padding:10px;background:#f8fafc;">
                <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.04em;">ADT</div>
                <div style="font-size:24px;font-weight:800;margin-top:3px;">{adt:,.0f}</div>
            </div>
            <div style="border:1px solid #f3b59b;border-radius:8px;padding:10px;background:#fff0e8;">
                <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.04em;">Heavy share</div>
                <div style="font-size:24px;font-weight:800;margin-top:3px;color:#e85d2a;">{heavy_pct}</div>
            </div>
        </div>
        <div style="font-size:13px;color:#64748b;font-weight:700;margin-bottom:7px;">Vehicle breakdown</div>
        <div style="display:grid;grid-template-columns:1fr auto;gap:5px 18px;font-size:13px;line-height:1.25;">
            <span>Heavy vehicles</span><b>{heavy:,.0f}</b>
            <span>Cars</span><b>{cars:,.0f}</b>
            <span>Motorcycles</span><b>{mc:,.0f}</b>
            <span>Rickshaws</span><b>{rickshaws:,.0f}</b>
            <span>Light trucks / pickups</span><b>{light_pickup:,.0f}</b>
            <span>Mini buses</span><b>{mini_bus:,.0f}</b>
            <span>Large buses</span><b>{large_bus:,.0f}</b>
        </div>
    </div>
    """


@st.cache_data(show_spinner="Loading traffic count stations...", max_entries=1)
def prepare_count_stations(path):
    gdf = gpd.read_file(path)
    stations = []
    for _, row in gdf.iterrows():
        row_data = row.to_dict()
        geometry = row_data.pop("geometry")
        if geometry is None or geometry.is_empty:
            continue

        heavy_share = row_data.get("heavy_share")
        adt = safe_num(row_data, "ADT")
        traffic_style = heavy_share_style(heavy_share)
        stations.append(
            {
                "road_id": row_data.get("Road.ID"),
                "lat": float(geometry.y),
                "lon": float(geometry.x),
                "color": traffic_style["color"],
                "border": traffic_style["border"],
                "traffic_label": traffic_style["label"],
                "heavy_share_text": f"{float(heavy_share) * 100:.1f}%" if pd.notna(heavy_share) else "N/A",
                "adt_text": f"{adt:,.0f}",
                "adt_compact": format_count(adt),
                "popup": build_counts_popup(row_data),
            }
        )
    return stations


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Controls")

    available_datasets = {name: path for name, path in DATASETS.items() if os.path.exists(path)}
    if not available_datasets:
        st.error(
            "No dataset files found. Place the .gpkg files in a subfolder named 'data'"
        )
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
    roads = {label: prepare_road_data(available_datasets[label]) for label in selected_labels}

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
    show_distance_markers = st.toggle("Distance markers", value=True, help="Show road markers every 50 km.")
    show_counts = st.toggle("Traffic count stations", value=False, help="Show traffic count markers for the selected road(s).")

    if show_rsl:
        sidebar_legend_rows = "".join(
            f'<div style="display:flex;align-items:center;margin:2px 0;">'
            f'<span style="display:inline-block;width:12px;height:12px;'
            f'background:{color};margin-right:6px;border-radius:2px;"></span>'
            f'<span style="font-size:13px;">{label}</span></div>'
            for _, _, label, color in RSL_CATEGORIES
        )
        sidebar_legend_rows += (
            f'<div style="display:flex;align-items:center;margin:2px 0;">'
            f'<span style="display:inline-block;width:12px;height:12px;'
            f'background:{NODATA_COLOR};margin-right:6px;border-radius:2px;"></span>'
            f'<span style="font-size:13px;">{NODATA_LABEL}</span></div>'
        )
        st.markdown(sidebar_legend_rows, unsafe_allow_html=True)

    count_stations = []
    if show_counts:
        if os.path.exists(COUNTS_PATH):
            wanted_road_ids = [ROAD_ID_MAP.get(lbl) for lbl in selected_labels]
            count_stations = [
                station
                for station in prepare_count_stations(COUNTS_PATH)
                if station["road_id"] in wanted_road_ids
            ]
            if not count_stations:
                st.caption("No count stations found for this selection.")
            else:
                st.caption(f"{len(count_stations)} traffic count station(s) shown.")
                traffic_legend_rows = "".join(
                    f'<div style="display:flex;align-items:center;margin:2px 0;">'
                    f'<span style="display:inline-block;width:10px;height:10px;'
                    f'background:{color};margin-right:6px;border-radius:50%;"></span>'
                    f'<span style="font-size:13px;">{label} heavy share</span></div>'
                    for label, _, color, _, _ in TRAFFIC_SHARE_BANDS
                )
                st.markdown(traffic_legend_rows, unsafe_allow_html=True)
        else:
            st.warning(f"Counts file not found: {COUNTS_PATH}")

    if show_rsl:
        st.caption("Road colors reflect remaining service life thresholds.")

# ---------------------------------------------------------------------------
# Build map
# ---------------------------------------------------------------------------
bounds_list = [roads[label]["bounds"] for label in selected_labels]  # minx, miny, maxx, maxy
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

# Categorical remaining-service-life view, one road at a time
for label in selected_labels:
    road = roads[label]

    if show_rsl:
        for feature in road["features"]:
            rsl_label = feature[f"{direction_key}_label"]
            color = feature[f"{direction_key}_color"]
            dash = "5,5" if rsl_label == NODATA_LABEL else None
            weight = 3 if rsl_label == NODATA_LABEL else 5
            opacity = 0.6 if rsl_label == NODATA_LABEL else 0.9

            tooltip_text = f"km {feature['km']:.0f} | {rsl_label}"
            if len(selected_labels) > 1:
                tooltip_text = f"{label} | " + tooltip_text

            line_kwargs = dict(
                color=color,
                weight=weight,
                opacity=opacity,
                tooltip=tooltip_text,
                popup=folium.Popup(
                    popup_html(feature, rsl_label, direction_choice),
                    max_width=270,
                ),
            )
            if dash:
                line_kwargs["dash_array"] = dash

            folium.PolyLine(feature["coords"], **line_kwargs).add_to(m)
    else:
        # RSL layer hidden: still draw a plain road line for context
        for feature in road["features"]:
            folium.PolyLine(
                feature["coords"],
                color="#4a4a4a",
                weight=3,
                opacity=0.7,
            ).add_to(m)

    if show_distance_markers:
        add_distance_markers(
            m,
            road["distance_markers"],
            road_label=label if len(selected_labels) > 1 else "",
        )

# Traffic count stations: styled markers with compact AADT chips.
if count_stations:
    for station in count_stations:
        folium.Marker(
            location=[station["lat"], station["lon"]],
            icon=folium.DivIcon(
                html=build_count_marker_html(station),
                icon_size=(92, 34),
                icon_anchor=(12, 12),
            ),
            popup=folium.Popup(station["popup"], max_width=300),
        ).add_to(m)

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
with st.container(border=True):
    st_folium(m, width=None, height=680, returned_objects=[])

if show_rsl:
    caption_text = (
        "Grey dashed segments indicate missing data (sentinel value -99 in the source data). "
        "Click a colored segment to see its remaining service life category. "
        "Circular badges show distance along the road every 50 km. "
        "The legend shows what share of the displayed road length falls in each condition category."
    )
else:
    caption_text = (
        "Road condition (remaining service life) layer is hidden. "
        "Circular badges show distance along the road every 50 km."
    )
if count_stations:
    caption_text += (
        " Labeled markers are traffic count stations, color-coded by heavy-traffic share "
        "(green = low, red = high) — click a station marker for ADT, heavy traffic, and the full "
        "vehicle-type breakdown."
    )
st.caption(caption_text)
