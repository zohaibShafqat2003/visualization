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

RSL_CATEGORIES = [
    (0, 1, "Very Poor <1 year", "#d73027"),
    (1, 2, "Poor 1-2 years", "#facc15"),
    (2, 4, "Fair 2-4 years", "#2563eb"),
    (4, float("inf"), "Good >=4 years", "#1a9850"),
]

STATUS_CATEGORY_COLORS = {
    "Very Poor": "#d73027",
    "Poor": "#facc15",
    "Fair": "#2563eb",
    "Good": "#1a9850",
    "Under construction": "#8E24AA",
    "Rehabilitation Project": "#795548",
    "DLC": "#424242",
    "LDA": "#00897B",
    "PDA": "#9E9D24",
    "Rigid Pavement": "#475569",
    "No data/single carriageway": "#BDBDBD",
}

STATUS_CATEGORY_ORDER = list(STATUS_CATEGORY_COLORS)

NODATA_LABEL = "No data/single carriageway"
NODATA_COLOR = "#BDBDBD"
GEOMETRY_SIMPLIFY_TOLERANCE = 0.00015
ROAD_DATA_CACHE_VERSION = 7
TRAFFIC_MARKER_COLOR = "#c92a2a"
TRAFFIC_MARKER_BORDER = "#f1b6b6"
TRAFFIC_POPUP_CACHE_VERSION = 9
DISTANCE_MARKER_MIN_ZOOM = 8
PROBLEM_RSL_LABELS = {"Very Poor <1 year", "Poor 1-2 years", "Very Poor", "Poor"}
