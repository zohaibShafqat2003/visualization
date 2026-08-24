import math

import geopandas as gpd
import pandas as pd
import streamlit as st

from src.config import (
    GEOMETRY_SIMPLIFY_TOLERANCE,
    NODATA_COLOR,
    NODATA_LABEL,
    NODATA_SENTINEL,
    RSL_CATEGORIES,
    STATUS_CATEGORY_COLORS,
    STATUS_CATEGORY_ORDER,
    TRAFFIC_MARKER_BORDER,
    TRAFFIC_MARKER_COLOR,
    ROAD_DATA_CACHE_VERSION,
)
from src.popups import build_counts_popup, format_count, safe_num


def classify_rsl(value):
    if value == NODATA_SENTINEL:
        return NODATA_LABEL, NODATA_COLOR
    for lo, hi, label, color in RSL_CATEGORIES:
        if lo <= value < hi:
            return label, color
    return NODATA_LABEL, NODATA_COLOR


def classify_status(status):
    """Keep the supplied status category and assign it a stable map color."""
    normalized = str(status).strip().casefold() if pd.notna(status) else ""
    labels = {
        "very poor": "Very Poor",
        "poor": "Poor",
        "fair": "Fair",
        "good": "Good",
        "under construction": "Under construction",
        "underconstruction": "Under construction",
        "rehabilitation project": "Rehabilitation Project",
        "dlc": "DLC",
        "lda": "LDA",
        "pda": "PDA",
        "rigid pavement": "Rigid Pavement",
        "milling": "Under construction",
        "no data": "No data",
    }
    label = labels.get(normalized, "No data")
    return label, STATUS_CATEGORY_COLORS.get(label, NODATA_COLOR)


def is_valid_rsl(value):
    return pd.notna(value) and value != NODATA_SENTINEL


def average_rsl_value(north_value, south_value):
    north_valid = is_valid_rsl(north_value)
    south_valid = is_valid_rsl(south_value)

    if north_valid and south_valid:
        return (north_value + south_value) / 2
    if north_valid:
        return north_value
    if south_valid:
        return south_value
    return NODATA_SENTINEL


def same_point(point_a, point_b, tolerance=1e-7):
    return (
        abs(point_a[0] - point_b[0]) <= tolerance
        and abs(point_a[1] - point_b[1]) <= tolerance
    )


def merged_coords(base_coords, next_coords):
    if same_point(base_coords[-1], next_coords[0]):
        return base_coords + list(next_coords[1:])
    if same_point(base_coords[-1], next_coords[-1]):
        return base_coords + list(reversed(next_coords[:-1]))
    if same_point(base_coords[0], next_coords[-1]):
        return list(next_coords[:-1]) + base_coords
    if same_point(base_coords[0], next_coords[0]):
        return list(reversed(next_coords[1:])) + base_coords
    return None


def contiguous_road_paths(features):
    paths = []
    current_path = []
    for feature in features:
        coords = list(feature["coords"])
        if not coords:
            continue
        if not current_path:
            current_path = coords
            continue

        merged_path = merged_coords(current_path, coords)
        if merged_path:
            current_path = merged_path
        else:
            paths.append(current_path)
            current_path = coords

    if current_path:
        paths.append(current_path)
    return paths


def condition_runs(features, direction_key):
    runs = []
    current_run = None

    for feature in features:
        label = feature[f"{direction_key}_label"]
        color = feature[f"{direction_key}_color"]
        coords = list(feature["coords"])
        if not coords:
            continue

        if current_run and current_run["label"] == label and current_run["color"] == color:
            merged_path = merged_coords(current_run["coords"], coords)
            if merged_path:
                current_run["coords"] = merged_path
                continue

        current_run = {
            "label": label,
            "color": color,
            "coords": coords,
        }
        runs.append(current_run)

    return runs


def assign_segment_lengths(features):
    if not features:
        return features

    positive_diffs = [
        abs(features[index + 1]["km"] - features[index]["km"])
        for index in range(len(features) - 1)
        if abs(features[index + 1]["km"] - features[index]["km"]) > 0
    ]
    if positive_diffs:
        sorted_diffs = sorted(positive_diffs)
        fallback_length = sorted_diffs[len(sorted_diffs) // 2]
    else:
        fallback_length = 1.0

    for index, feature in enumerate(features):
        if index < len(features) - 1:
            segment_length = abs(features[index + 1]["km"] - feature["km"])
        elif index > 0:
            segment_length = abs(feature["km"] - features[index - 1]["km"])
        else:
            segment_length = fallback_length

        if segment_length <= 0:
            segment_length = fallback_length
        feature["length_km"] = segment_length

    return features


def condition_kilometers(roads, selected_labels, direction_key):
    totals = {}

    for label in selected_labels:
        for feature in roads[label]["features"]:
            condition_label = feature[f"{direction_key}_label"]
            totals[condition_label] = totals.get(condition_label, 0.0) + feature.get("length_km", 0.0)

    return totals


def road_status_categories(roads, selected_labels, direction_key):
    present_labels = {
        feature[f"{direction_key}_label"]
        for road_label in selected_labels
        for feature in roads[road_label]["features"]
    }
    ordered_labels = [label for label in STATUS_CATEGORY_ORDER if label in present_labels]
    return [
        (label, STATUS_CATEGORY_COLORS.get(label, NODATA_COLOR))
        for label in ordered_labels
    ]


def build_distance_markers(gdf):
    if "km" not in gdf.columns or gdf.empty:
        return []

    marker_gdf = gdf[["km", "geometry"]].dropna(subset=["km", "geometry"]).sort_values("km")
    if marker_gdf.empty:
        return []

    km_values = marker_gdf["km"].astype(float).to_numpy()
    km_min = float(km_values[0])
    km_max = float(km_values[-1])
    if km_max <= km_min:
        return []

    start = int(math.ceil(km_min))
    if start == 0:
        start = 1

    markers = []
    for target_km in range(start, int(km_max) + 1):
        insert_at = km_values.searchsorted(target_km)
        if insert_at == 0:
            idx = marker_gdf.index[0]
        elif insert_at >= len(km_values):
            idx = marker_gdf.index[-1]
        else:
            before_idx = marker_gdf.index[insert_at - 1]
            after_idx = marker_gdf.index[insert_at]
            before_delta = abs(km_values[insert_at - 1] - target_km)
            after_delta = abs(km_values[insert_at] - target_km)
            idx = before_idx if before_delta <= after_delta else after_idx
        row = marker_gdf.loc[idx]
        coords = list(row.geometry.coords)
        lon, lat = coords[len(coords) // 2]
        markers.append({"km": target_km, "lat": lat, "lon": lon})
    return markers


@st.cache_data(show_spinner=False, max_entries=32)
def select_distance_markers(markers, interval):
    return [
        marker
        for marker in markers
        if int(marker["km"]) % int(interval) == 0
    ]


def build_road_data(gdf):
    """Turn normalized road geometry and status columns into map-ready features."""
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

        north_status = getattr(row, "status_north", None)
        south_status = getattr(row, "status_south", None)
        north_label, north_color = classify_status(north_status)
        south_label, south_color = classify_status(south_status)
        features.append(
            {
                "km": float(row.km),
                "coords": coords,
                "length": float(geometry.length),
                "north_status": north_status,
                "north_label": north_label,
                "north_color": north_color,
                "south_status": south_status,
                "south_label": south_label,
                "south_color": south_color,
            }
        )

    assign_segment_lengths(features)
    return {
        "bounds": bounds,
        "features": features,
        "plain_paths": contiguous_road_paths(features),
        "condition_runs": {
            "north": condition_runs(features, "north"),
            "south": condition_runs(features, "south"),
        },
        "distance_markers": build_distance_markers(gdf),
    }


@st.cache_data(show_spinner="Loading road data...", max_entries=4)
def prepare_road_data(path, cache_version=ROAD_DATA_CACHE_VERSION):
    _ = cache_version
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
    assign_segment_lengths(features)

    return {
        "bounds": bounds,
        "features": features,
        "plain_paths": contiguous_road_paths(features),
        "condition_runs": {
            "north": condition_runs(features, "north"),
            "south": condition_runs(features, "south"),
            "average": condition_runs(features, "average"),
        },
        "distance_markers": build_distance_markers(gdf),
    }


@st.cache_data(show_spinner="Loading updated N5 road data...", max_entries=1)
def prepare_n5_road_data(north_path, south_path, cache_version=ROAD_DATA_CACHE_VERSION):
    _ = cache_version
    north = gpd.read_file(north_path).to_crs("EPSG:4326")
    south = gpd.read_file(south_path).to_crs("EPSG:4326")

    north = north[["km", "status", "geometry"]].rename(columns={"status": "status_north"})
    south = south[["km", "status", "geometry"]].rename(columns={"status": "status_south"})
    south_status = south.drop(columns="geometry")

    # Northbound geometry is used where present; the southbound geometry covers
    # any km values that are available only in the southbound source.
    combined = north.merge(south_status, on="km", how="outer")
    south_geometry = south[["km", "geometry"]]
    combined = combined.merge(south_geometry, on="km", how="left", suffixes=("", "_south"))
    combined["geometry"] = combined["geometry"].where(
        combined["geometry"].notna(), combined["geometry_south"]
    )
    combined = gpd.GeoDataFrame(combined.drop(columns="geometry_south"), geometry="geometry", crs="EPSG:4326")
    combined = combined.sort_values("km").reset_index(drop=True)
    return build_road_data(combined)


@st.cache_data(show_spinner="Loading updated N55 road data...", max_entries=1)
def prepare_n55_road_data(geometry_path, north_status_path, south_status_path, cache_version=ROAD_DATA_CACHE_VERSION):
    _ = cache_version
    geometry = gpd.read_file(geometry_path)
    north_status = pd.read_csv(north_status_path, usecols=["km", "status"])
    south_status = pd.read_csv(south_status_path, usecols=["km", "status"])

    north_status = north_status.rename(columns={"status": "status_north"})
    south_status = south_status.rename(columns={"status": "status_south"})
    combined = geometry[["km", "geometry"]].merge(north_status, on="km", how="left")
    combined = combined.merge(south_status, on="km", how="left")
    combined = gpd.GeoDataFrame(combined, geometry="geometry", crs=geometry.crs)
    return build_road_data(combined)


@st.cache_data(show_spinner="Loading traffic count stations...", max_entries=1)
def prepare_count_stations(path, popup_cache_version):
    _ = popup_cache_version
    gdf = gpd.read_file(path)
    stations = []
    for _, row in gdf.iterrows():
        row_data = row.to_dict()
        geometry = row_data.pop("geometry")
        if geometry is None or geometry.is_empty:
            continue

        heavy_share = row_data.get("heavy_share")
        adt = safe_num(row_data, "ADT")
        rd_value = row_data.get("RD")
        try:
            rd_km = float(rd_value)
        except (TypeError, ValueError):
            rd_km = None

        stations.append(
            {
                "road_id": row_data.get("Road.ID"),
                "lat": float(geometry.y),
                "lon": float(geometry.x),
                "rd_km": rd_km,
                "color": TRAFFIC_MARKER_COLOR,
                "border": TRAFFIC_MARKER_BORDER,
                "heavy_share_text": f"{float(heavy_share) * 100:.1f}%" if pd.notna(heavy_share) else "N/A",
                "adt_text": f"{adt:,.0f}",
                "adt_compact": format_count(adt),
                "popup": build_counts_popup(row_data),
            }
        )
    return stations
