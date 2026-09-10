import geopandas as gpd
import streamlit as st
from shapely.geometry import Point

from src.config import MAJOR_CITIES, ROAD_DATA_CACHE_VERSION
from src.data_loader import build_road_data


def nearest_km(network, lat, lon):
    point = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(network.crs).iloc[0]
    return float(network.loc[network.geometry.distance(point).idxmin(), 'km'])


@st.cache_data(show_spinner="Loading N5: Multan to Peshawar...", max_entries=2)
def prepare_n5_section(path, cache_version=ROAD_DATA_CACHE_VERSION):
    frame = gpd.read_file(path).to_crs(4326).sort_values('km').reset_index(drop=True)
    network = frame[['km', 'geometry']].to_crs(32643)
    endpoints = [next(c for c in MAJOR_CITIES if c['road'] == 'N5' and c['name'] == name)
                 for name in ('Multan', 'Peshawar')]
    limits = sorted(nearest_km(network, c['lat'], c['lon']) for c in endpoints)
    section = frame[frame.km.between(*limits)].copy()
    if section.empty:
        raise ValueError('No N5 segments found between Multan and Peshawar.')
    return build_road_data(section), network, limits


def points_in_section(points, network, limits):
    """Locate points on the full road so out-of-section points cannot snap to its ends."""
    return [point for point in points
            if limits[0] <= nearest_km(network, point['lat'], point['lon']) <= limits[1]]
