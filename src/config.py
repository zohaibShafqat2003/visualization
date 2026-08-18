import os


NODATA_SENTINEL = -99

DATASETS = {
    "N5": os.path.join("data", "segments_N5.gpkg"),
    "N-55": os.path.join("data", "segments_N55.gpkg"),
}

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

NODATA_LABEL = "No data"
NODATA_COLOR = "#888888"
GEOMETRY_SIMPLIFY_TOLERANCE = 0.00015
ROAD_DATA_CACHE_VERSION = 2
TRAFFIC_MARKER_COLOR = "#c92a2a"
TRAFFIC_MARKER_BORDER = "#f1b6b6"
TRAFFIC_POPUP_CACHE_VERSION = 8
DISTANCE_MARKER_MIN_ZOOM = 8
PROBLEM_RSL_LABELS = {"Very Poor <1 year", "Poor 1-2 years"}
