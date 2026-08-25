import os


NODATA_SENTINEL = -99

DATASETS = {
    "N5": os.path.join("New folder", "sf_north1.gpkg"),
    "N-55": os.path.join("data", "segments_N55.gpkg"),
}

N5_NORTH_PATH = os.path.join("New folder", "sf_north1.gpkg")
N5_SOUTH_PATH = os.path.join("New folder", "sf_south1.gpkg")
N55_GEOMETRY_PATH = os.path.join("data", "segments_N55.gpkg")
N55_NORTH_STATUS_PATH = os.path.join("New folder", "N55_NB_24.08.26.csv")
N55_SOUTH_STATUS_PATH = os.path.join("New folder", "N55_SB_24.08.26.csv")

COUNTS_PATH = os.path.join("data", "counts_N5_N55.gpkg")

ROAD_ID_MAP = {
    "N5": "N-5",
    "N-55": "N55",
}

MAJOR_CITIES = [
    {"name": "Karachi", "road": "N5", "lat": 24.8607, "lon": 67.0011},
    {"name": "Hyderabad", "road": "N5", "lat": 25.3960, "lon": 68.3578},
    {"name": "Moro", "road": "N5", "lat": 26.6652, "lon": 68.0016},
    {"name": "Sukkur", "road": "N5", "lat": 27.7052, "lon": 68.8574},
    {"name": "Rahim Yar Khan", "road": "N5", "lat": 28.4212, "lon": 70.2989},
    {"name": "Bahawalpur", "road": "N5", "lat": 29.3956, "lon": 71.6836},
    {"name": "Multan", "road": "N5", "lat": 30.1575, "lon": 71.5249},
    {"name": "Sahiwal", "road": "N5", "lat": 30.6682, "lon": 73.1114},
    {"name": "Lahore", "road": "N5", "lat": 31.5204, "lon": 74.3587},
    {"name": "Gujranwala", "road": "N5", "lat": 32.1877, "lon": 74.1945},
    {"name": "Jhelum", "road": "N5", "lat": 32.9345, "lon": 73.7310},
    {"name": "Rawalpindi", "road": "N5", "lat": 33.5651, "lon": 73.0169},
    {"name": "Peshawar", "road": "N5", "lat": 34.0151, "lon": 71.5249},
    {"name": "Kotri", "road": "N-55", "lat": 25.3660, "lon": 68.3122},
    {"name": "Sehwan", "road": "N-55", "lat": 26.4242, "lon": 67.8612},
    {"name": "Dadu", "road": "N-55", "lat": 26.7303, "lon": 67.7769},
    {"name": "Larkana", "road": "N-55", "lat": 27.5570, "lon": 68.2028},
    {"name": "Shikarpur", "road": "N-55", "lat": 27.9556, "lon": 68.6382},
    {"name": "Kandhkot", "road": "N-55", "lat": 28.2457, "lon": 69.1797},
    {"name": "Dera Ghazi Khan", "road": "N-55", "lat": 30.0561, "lon": 70.6348},
    {"name": "Dera Ismail Khan", "road": "N-55", "lat": 31.8327, "lon": 70.9024},
    {"name": "Kohat", "road": "N-55", "lat": 33.5889, "lon": 71.4429},
    {"name": "Peshawar", "road": "N-55", "lat": 34.0151, "lon": 71.5249},
]

RSL_CATEGORIES = [
    (0, 1, "Very Poor <1 year", "#d73027"),
    (1, 3, "Poor 1-3 years", "#facc15"),
    (3, 4, "Fair 3-4 years", "#2563eb"),
    (4, float("inf"), "Good >=4 years", "#1a9850"),
]

RSL_DEFAULT_THRESHOLDS = (1.0, 3.0, 4.0)
RSL_COLORS = ("#d73027", "#facc15", "#2563eb", "#1a9850")

STATUS_CATEGORY_COLORS = {
    "Very Poor": "#d73027",
    "Poor": "#facc15",
    "Fair": "#2563eb",
    "Good": "#1a9850",
    "Under construction": "#8E24AA",
    "Rehabilitation Project": "#795548",
    "DLC": "#424242",
    "LDA": "#00ACC1",
    "PDA": "#9E9D24",
    "Rigid Pavement": "#475569",
    "No data/single carriageway": "#BDBDBD",
}

STATUS_CATEGORY_ORDER = list(STATUS_CATEGORY_COLORS)

NODATA_LABEL = "No data/single carriageway"
NODATA_COLOR = "#BDBDBD"
GEOMETRY_SIMPLIFY_TOLERANCE = 0.00015
ROAD_DATA_CACHE_VERSION = 8
TRAFFIC_MARKER_COLOR = "#c92a2a"
TRAFFIC_MARKER_BORDER = "#f1b6b6"
TRAFFIC_POPUP_CACHE_VERSION = 9
DISTANCE_MARKER_MIN_ZOOM = 8
PROBLEM_RSL_LABELS = {"Very Poor <1 year", "Poor 1-2 years", "Very Poor", "Poor"}
