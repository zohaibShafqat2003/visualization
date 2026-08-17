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
    (0, 1, "Very Poor", "#d73027"),
    (1, 2, "Poor", "#fc8d59"),
    (2, 4, "Fair", "#fee08b"),
    #(3, 4, "Fair", "#fee08b"),
    (4, float("inf"), "Good", "#1a9850"),
]
NODATA_LABEL = "No data"
NODATA_COLOR = "#888888"

st.set_page_config(page_title="Road Condition Map", layout="wide")
st.title("Road Condition Map")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
@st.cache_data
def load_data(path):
    gdf = gpd.read_file(path)
    return gdf


@st.cache_data
def load_counts(path):
    gdf = gpd.read_file(path)
    return gdf


def classify_rsl(value):
    """Map a remaining-service-life value to (label, color)."""
    if value == NODATA_SENTINEL:
        return NODATA_LABEL, NODATA_COLOR
    for lo, hi, label, color in RSL_CATEGORIES:
        if lo <= value < hi:
            return label, color
    return NODATA_LABEL, NODATA_COLOR


def add_distance_markers(fmap, gdf, road_label=""):
    """Add a circular badge with the km reading every 50 km along a road."""
    if "km" not in gdf.columns or gdf.empty:
        return

    km_min = float(gdf["km"].min())
    km_max = float(gdf["km"].max())
    if km_max <= km_min:
        return

    start = int(math.ceil(km_min / 50.0) * 50)
    if start == 0:
        start = 50  # skip the 0 km marker, it clutters the start of the road

    for target_km in range(start, int(km_max) + 1, 50):
        idx = (gdf["km"] - target_km).abs().idxmin()
        row = gdf.loc[idx]
        coords = list(row.geometry.coords)
        lon, lat = coords[len(coords) // 2]

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
            [lat, lon],
            icon=folium.DivIcon(html=badge_html, icon_size=(32, 32), icon_anchor=(16, 16)),
        ).add_to(fmap)


def heavy_share_color(share):
    """Color-code a count station label by its heavy-traffic share."""
    if share is None or pd.isna(share):
        return "#888888"
    if share < 0.15:
        return "#1a9850"
    if share < 0.25:
        return "#fee08b"
    if share < 0.35:
        return "#fc8d59"
    return "#d73027"


def safe_num(row, col):
    val = row.get(col)
    try:
        return float(val) if pd.notna(val) else 0.0
    except (TypeError, ValueError):
        return 0.0


def clean_location(row):
    location_name = row.get("Location")
    if (
        not location_name
        or (isinstance(location_name, float) and pd.isna(location_name))
        or not str(location_name).strip()
    ):
        return "Unnamed station"
    return str(location_name)


def build_counts_popup(row):
    location_name = clean_location(row)

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
    <div style="font-size:13px; min-width:210px;">
        <b>{location_name}</b> ({row.get('Road.ID', '')})<br>
        <hr style="margin:4px 0;">
        <b>ADT:</b> {adt:,.0f}<br>
        <b>Heavy traffic:</b> {heavy:,.0f} ({heavy_pct})<br>
        <b>Cars:</b> {cars:,.0f}<br>
        <b>Motorcycles:</b> {mc:,.0f}<br>
        <b>Rickshaws:</b> {rickshaws:,.0f}<br>
        <b>Light trucks / pickups:</b> {light_pickup:,.0f}<br>
        <b>Mini buses:</b> {mini_bus:,.0f}<br>
        <b>Large buses:</b> {large_bus:,.0f}
    </div>
    """


def popup_html(row, label, direction_choice):
    return f"""
    <b>km {row['km']:.0f}</b><br>
    Remaining service life ({direction_choice}): {label}
    """


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
st.sidebar.header("Dataset")

available_datasets = {name: path for name, path in DATASETS.items() if os.path.exists(path)}
if not available_datasets:
    st.error(
        "No dataset files found. Place the .gpkg files in a subfolder named 'data'"
    )
    st.stop()

highway_labels = list(available_datasets.keys())
highway_options = highway_labels + (["Both"] if len(highway_labels) > 1 else [])
highway_choice = st.sidebar.radio("Highway", highway_options)

selected_labels = highway_labels if highway_choice == "Both" else [highway_choice]

gdfs = {label: load_data(available_datasets[label]) for label in selected_labels}

missing_files = [name for name in DATASETS if name not in available_datasets]
if missing_files:
    st.sidebar.caption(f"Not found: {', '.join(missing_files)}")

st.sidebar.header("Display options")

metric_choice = "Remaining Service Life"
metric_key = "remaining_service_life"
#st.sidebar.caption(
#    "Very Poor: 0–1  |  Poor: 1–2  |  Fair: 2–4  |  Good: ≥4 (years)"
#)

direction_choice = st.sidebar.radio(
    "Direction",
    ["North bound", "South bound"],
)

direction_key = "north" if direction_choice == "North bound" else "south"
column = f"{metric_key}_{direction_key}"

show_distance_markers = st.sidebar.checkbox("Show distance markers (every 50 km)", value=True)

st.sidebar.header("Road condition (RSL)")
show_rsl = st.sidebar.checkbox("Show road condition (remaining service life)", value=True)

st.sidebar.header("Traffic counts")
show_counts = st.sidebar.checkbox("Show traffic count stations", value=False)

counts_gdf = None
if show_counts:
    if os.path.exists(COUNTS_PATH):
        counts_all = load_counts(COUNTS_PATH)
        wanted_road_ids = [ROAD_ID_MAP.get(lbl) for lbl in selected_labels]
        counts_gdf = counts_all[counts_all["Road.ID"].isin(wanted_road_ids)].copy()
        if counts_gdf.empty:
            st.sidebar.caption("No count stations found for this selection.")
    else:
        st.sidebar.warning(f"Counts file not found: {COUNTS_PATH}")

#st.sidebar.markdown("---")
#st.sidebar.metric(
#    "Segments shown (KM)",
#    int((gdf[column] != NODATA_SENTINEL).sum()),
#)
#st.sidebar.metric(
#    "Missing data (KM)",
#    int((gdf[column] == NODATA_SENTINEL).sum()),
#)

# ---------------------------------------------------------------------------
# Build map
# ---------------------------------------------------------------------------
bounds_list = [gdfs[label].total_bounds for label in selected_labels]  # minx, miny, maxx, maxy
minx = min(b[0] for b in bounds_list)
miny = min(b[1] for b in bounds_list)
maxx = max(b[2] for b in bounds_list)
maxy = max(b[3] for b in bounds_list)
center_lat = (miny + maxy) / 2
center_lon = (minx + maxx) / 2
zoom_start = 6 if len(selected_labels) > 1 else 7

m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_start, tiles="CartoDB positron")

# Track total length per RSL category so the legend can show % of road length
category_labels_ordered = []
for _, _, lab, _ in RSL_CATEGORIES:
    if lab not in category_labels_ordered:
        category_labels_ordered.append(lab)
category_length = {lab: 0.0 for lab in category_labels_ordered}
category_length[NODATA_LABEL] = 0.0
total_length = 0.0

# Categorical remaining-service-life view, one road at a time
for label in selected_labels:
    road_gdf = gdfs[label]

    if show_rsl:
        for _, row in road_gdf.iterrows():
            coords = [(lat, lon) for lon, lat in row.geometry.coords]
            rsl_label, color = classify_rsl(row[column])
            dash = "5,5" if rsl_label == NODATA_LABEL else None
            weight = 3 if rsl_label == NODATA_LABEL else 5
            opacity = 0.6 if rsl_label == NODATA_LABEL else 0.9

            seg_length = row.geometry.length
            category_length[rsl_label] = category_length.get(rsl_label, 0.0) + seg_length
            total_length += seg_length

            tooltip_text = f"km {row['km']:.0f} | {rsl_label}"
            if len(selected_labels) > 1:
                tooltip_text = f"{label} | " + tooltip_text

            line_kwargs = dict(
                color=color,
                weight=weight,
                opacity=opacity,
                tooltip=tooltip_text,
                popup=folium.Popup(popup_html(row, rsl_label, direction_choice), max_width=250),
            )
            if dash:
                line_kwargs["dash_array"] = dash

            folium.PolyLine(coords, **line_kwargs).add_to(m)
    else:
        # RSL layer hidden: still draw a plain road line for context
        for _, row in road_gdf.iterrows():
            coords = [(lat, lon) for lon, lat in row.geometry.coords]
            folium.PolyLine(coords, color="#4a4a4a", weight=3, opacity=0.7).add_to(m)

    if show_distance_markers:
        add_distance_markers(m, road_gdf, road_label=label if len(selected_labels) > 1 else "")

# Traffic count stations: a small color-coded label, click for full details
if counts_gdf is not None and not counts_gdf.empty:
    for _, row in counts_gdf.iterrows():
        location_name = clean_location(row)
        dot_color = heavy_share_color(row.get("heavy_share"))
        adt_text = f"{safe_num(row, 'ADT'):,.0f}"

        label_html = (
            '<div style="display:flex;align-items:center;gap:4px;background:white;'
            "border:1px solid #333;border-radius:10px;padding:1px 6px;font-size:10px;"
            'font-weight:bold;white-space:nowrap;box-shadow:1px 1px 3px rgba(0,0,0,0.3);">'
            f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
            f'background:{dot_color};flex-shrink:0;"></span>'
            f"{adt_text}</div>"
        )

        folium.Marker(
            location=[row.geometry.y, row.geometry.x],
            icon=folium.DivIcon(html=label_html, icon_size=(120, 20), icon_anchor=(-4, 10)),
            tooltip=f"{location_name} — click for traffic details",
            popup=folium.Popup(build_counts_popup(row), max_width=260),
        ).add_to(m)

if show_rsl:
    # Build a categorical legend, with % of shown road length per category
    legend_items = []
    seen = set()
    for lo, hi, label, color in RSL_CATEGORIES:
        if label not in seen:
            legend_items.append((label, color))
            seen.add(label)
    legend_items.append((NODATA_LABEL, NODATA_COLOR))

    def pct_for(label):
        if total_length <= 0:
            return None
        return category_length.get(label, 0.0) / total_length * 100

    legend_rows = ""
    for label, color in legend_items:
        pct = pct_for(label)
        pct_text = f" — {pct:.0f}%" if pct is not None else ""
        legend_rows += (
            f'<span style="display:inline-block;width:12px;height:12px;'
            f'background:{color};margin-right:6px;"></span>{label}{pct_text}<br>'
        )

    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 30px; left: 30px;
        z-index: 9999;
        background: white;
        padding: 10px 14px;
        border: 1px solid #999;
        border-radius: 4px;
        font-size: 13px;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
    ">
        <b>Remaining service life ({direction_choice})</b><br>
        {legend_rows}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
st_folium(m, use_container_width=True, height=650, returned_objects=[])

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
if counts_gdf is not None and not counts_gdf.empty:
    caption_text += (
        " Labeled markers are traffic count stations, color-coded by heavy-traffic share "
        "(green = low, red = high) — click a label for ADT, heavy traffic, and the full "
        "vehicle-type breakdown."
    )
st.caption(caption_text)
