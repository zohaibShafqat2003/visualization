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
    TRAFFIC_MARKER_BORDER,
    TRAFFIC_MARKER_COLOR,
)
from src.popups import build_counts_popup, format_count, safe_num


def classify_rsl(value):
    if value == NODATA_SENTINEL:
        return NODATA_LABEL, NODATA_COLOR
    for lo, hi, label, color in RSL_CATEGORIES:
        if lo <= value < hi:
            return label, color
    return NODATA_LABEL, NODATA_COLOR


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


def condition_percentages(roads, selected_labels, direction_key):
    totals = {label: 0.0 for _, _, label, _ in RSL_CATEGORIES}
    totals[NODATA_LABEL] = 0.0

    for label in selected_labels:
        for feature in roads[label]["features"]:
            condition_label = feature[f"{direction_key}_label"]
            totals[condition_label] = totals.get(condition_label, 0.0) + feature["length"]

    total_length = sum(totals.values())
    if total_length <= 0:
        return {label: 0 for label in totals}

    return {
        label: round((length / total_length) * 100)
        for label, length in totals.items()
    }


def build_distance_markers(gdf):
    if "km" not in gdf.columns or gdf.empty:
        return []

    km_min = float(gdf["km"].min())
    km_max = float(gdf["km"].max())
    if km_max <= km_min:
        return []

    start = int(math.ceil(km_min / 50.0) * 50)
    if start == 0:
        start = 50

    markers = []
    for target_km in range(start, int(km_max) + 1, 50):
        idx = (gdf["km"] - target_km).abs().idxmin()
        row = gdf.loc[idx]
        coords = list(row.geometry.coords)
        lon, lat = coords[len(coords) // 2]
        markers.append({"km": target_km, "lat": lat, "lon": lon})
    return markers


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
        stations.append(
            {
                "road_id": row_data.get("Road.ID"),
                "lat": float(geometry.y),
                "lon": float(geometry.x),
                "color": TRAFFIC_MARKER_COLOR,
                "border": TRAFFIC_MARKER_BORDER,
                "heavy_share_text": f"{float(heavy_share) * 100:.1f}%" if pd.notna(heavy_share) else "N/A",
                "adt_text": f"{adt:,.0f}",
                "adt_compact": format_count(adt),
                "popup": build_counts_popup(row_data),
            }
        )
    return stations
