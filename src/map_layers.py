import folium
from branca.element import MacroElement, Template

from src.config import DISTANCE_MARKER_MIN_ZOOM, NODATA_LABEL, PROBLEM_RSL_LABELS
from src.data_loader import is_valid_rsl
from src.popups import build_count_marker_html


def popup_html(feature, label, direction_choice):
    if direction_choice == "Average (both directions)":
        north_value = feature["north_value"]
        south_value = feature["south_value"]
        north_valid = is_valid_rsl(north_value)
        south_valid = is_valid_rsl(south_value)

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


def road_overlay_weight(rsl_label):
    if rsl_label == NODATA_LABEL:
        return 4
    if rsl_label in PROBLEM_RSL_LABELS:
        return 7
    return 6


def add_road_casing(fmap, paths):
    for coords in paths:
        if len(coords) < 2:
            continue

        folium.PolyLine(
            coords,
            color="#ffffff",
            weight=8,
            opacity=0.96,
            line_cap="round",
            line_join="round",
            smooth_factor=1.25,
        ).add_to(fmap)


def add_condition_corridor(fmap, road, direction_key):
    for run in road["condition_runs"][direction_key]:
        dash = "6,6" if run["label"] == NODATA_LABEL else None
        folium.PolyLine(
            run["coords"],
            color=run["color"],
            weight=road_overlay_weight(run["label"]),
            opacity=0.92 if run["label"] != NODATA_LABEL else 0.7,
            dash_array=dash,
            line_cap="butt",
            line_join="round",
            smooth_factor=1.4,
        ).add_to(fmap)


def add_plain_road_corridor(fmap, road):
    add_road_casing(fmap, road["plain_paths"])
    for coords in road["plain_paths"]:
        if len(coords) < 2:
            continue

        folium.PolyLine(
            coords,
            color="#475569",
            weight=5,
            opacity=0.82,
            line_cap="round",
            line_join="round",
            smooth_factor=1.25,
        ).add_to(fmap)


def add_road_hit_lines(fmap, features, direction_key, direction_choice, road_label="", show_rsl=True):
    for feature in features:
        rsl_label = feature[f"{direction_key}_label"] if show_rsl else "Road segment"
        tooltip_text = f"km {feature['km']:.0f} | {rsl_label}"
        if road_label:
            tooltip_text = f"{road_label} | " + tooltip_text

        folium.PolyLine(
            feature["coords"],
            color="#000000",
            weight=14,
            opacity=0,
            fill_opacity=0,
            line_cap="round",
            line_join="round",
            tooltip=tooltip_text,
            popup=folium.Popup(
                popup_html(feature, rsl_label, direction_choice),
                max_width=270,
            )
            if show_rsl
            else None,
        ).add_to(fmap)


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
