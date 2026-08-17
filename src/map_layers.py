import folium
from branca.element import MacroElement, Template

from src.config import (
    DISTANCE_MARKER_MIN_ZOOM,
    NODATA_COLOR,
    NODATA_LABEL,
    PROBLEM_RSL_LABELS,
    RSL_CATEGORIES,
)
from src.popups import build_count_marker_html


def road_overlay_weight(rsl_label):
    if rsl_label == NODATA_LABEL:
        return 4
    if rsl_label in PROBLEM_RSL_LABELS:
        return 7
    return 6


def to_geojson_line(coords):
    return [[lon, lat] for lat, lon in coords]


def add_geojson_lines(fmap, features):
    if not features:
        return

    folium.GeoJson(
        {
            "type": "FeatureCollection",
            "features": features,
        },
        style_function=lambda feature: {
            "color": feature["properties"]["color"],
            "weight": feature["properties"]["weight"],
            "opacity": feature["properties"]["opacity"],
            "dashArray": feature["properties"].get("dashArray"),
            "lineCap": feature["properties"].get("lineCap", "round"),
            "lineJoin": "round",
        },
        smooth_factor=1.4,
    ).add_to(fmap)


def add_road_casing(fmap, paths):
    features = []
    for coords in paths:
        if len(coords) >= 2:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": to_geojson_line(coords),
                    },
                    "properties": {
                        "color": "#ffffff",
                        "weight": 8,
                        "opacity": 0.96,
                        "lineCap": "round",
                    },
                }
            )
    add_geojson_lines(fmap, features)


def add_condition_corridor(fmap, road, direction_key):
    features = []
    for run in road["condition_runs"][direction_key]:
        if len(run["coords"]) < 2:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": to_geojson_line(run["coords"]),
                },
                "properties": {
                    "color": run["color"],
                    "weight": road_overlay_weight(run["label"]),
                    "opacity": 0.92 if run["label"] != NODATA_LABEL else 0.7,
                    "dashArray": "6,6" if run["label"] == NODATA_LABEL else None,
                    "lineCap": "butt",
                },
            }
        )
    add_geojson_lines(fmap, features)


def add_condition_legend(fmap, percentages, direction_choice):
    rows = []
    for _, _, label, color in RSL_CATEGORIES:
        rows.append(
            f"""
            <div style="display:flex;align-items:center;gap:8px;margin:3px 0;">
                <span style="display:inline-block;width:13px;height:13px;background:{color};"></span>
                <span>{label} - {percentages.get(label, 0)}%</span>
            </div>
            """
        )

    rows.append(
        f"""
        <div style="display:flex;align-items:center;gap:8px;margin:3px 0;">
            <span style="display:inline-block;width:13px;height:13px;background:{NODATA_COLOR};"></span>
            <span>{NODATA_LABEL} - {percentages.get(NODATA_LABEL, 0)}%</span>
        </div>
        """
    )

    legend = MacroElement()
    legend._template = Template(
        f"""
        {{% macro html(this, kwargs) %}}
        <div style="
            position: fixed;
            right: 34px;
            bottom: 38px;
            z-index: 9999;
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid rgba(15, 23, 42, 0.18);
            border-radius: 6px;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.18);
            padding: 12px 14px;
            color: #1f2937;
            font-family: Inter, Segoe UI, Arial, sans-serif;
            font-size: 14px;
            line-height: 1.2;
            min-width: 270px;
        ">
            <div style="font-weight:700;margin-bottom:7px;">
                Remaining service life ({direction_choice})
            </div>
            {''.join(rows)}
        </div>
        {{% endmacro %}}
        """
    )
    fmap.get_root().add_child(legend)


def add_plain_road_corridor(fmap, road):
    add_road_casing(fmap, road["plain_paths"])
    features = []
    for coords in road["plain_paths"]:
        if len(coords) >= 2:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": to_geojson_line(coords),
                    },
                    "properties": {
                        "color": "#475569",
                        "weight": 5,
                        "opacity": 0.82,
                        "lineCap": "round",
                    },
                }
            )
    add_geojson_lines(fmap, features)


def add_distance_markers(fmap, markers, road_label=""):
    for marker in markers:
        target_km = marker["km"]
        title_attr = f"{target_km} km" + (f" ({road_label})" if road_label else "")

        badge_html = (
            '<div class="distance-marker-badge" title="' + title_attr + '" style="'
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


def add_distance_marker_zoom_toggle(fmap, min_zoom=DISTANCE_MARKER_MIN_ZOOM):
    zoom_toggle = MacroElement()
    zoom_toggle._template = Template(
        f"""
        {{% macro script(this, kwargs) %}}
        (function() {{
            var map = {fmap.get_name()};
            var minZoom = {min_zoom};

            function updateDistanceMarkers() {{
                var visible = map.getZoom() >= minZoom;
                document.querySelectorAll(".distance-marker-badge").forEach(function(badge) {{
                    var markerIcon = badge.closest(".leaflet-marker-icon");
                    if (markerIcon) {{
                        markerIcon.style.display = visible ? "" : "none";
                    }}
                }});
            }}

            map.on("zoomend", updateDistanceMarkers);
            map.whenReady(updateDistanceMarkers);
            setTimeout(updateDistanceMarkers, 0);
        }})();
        {{% endmacro %}}
        """
    )
    fmap.get_root().add_child(zoom_toggle)


def add_station_markers(fmap, count_stations):
    for station in count_stations:
        folium.Marker(
            location=[station["lat"], station["lon"]],
            icon=folium.DivIcon(
                html=build_count_marker_html(station),
                icon_size=(76, 34),
                icon_anchor=(12, 12),
            ),
            popup=folium.Popup(station["popup"], max_width=300),
        ).add_to(fmap)
