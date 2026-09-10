import folium

from src.map_layers import to_geojson_line


N5_SECTION_LABELS = [
    {"label": "iRAP", "start_km": 1133, "end_km": 1283},
    {"label": "AIB", "start_km": 1566, "end_km": 1605},
    {"label": "AIB", "start_km": 1675, "end_km": 1706},
]


def add_section_labels(fmap, road):
    layer = folium.FeatureGroup(name="N5 section labels").add_to(fmap)
    for section in N5_SECTION_LABELS:
        start, end = section["start_km"], section["end_km"]
        features = [f for f in road["features"] if start <= f["km"] <= end]
        if not features:
            continue
        title = section["label"]
        detail = f"RD KM {start}–{end}"
        folium.GeoJson(
            {"type": "Feature", "properties": {}, "geometry": {
                "type": "MultiLineString",
                "coordinates": [to_geojson_line(f["coords"]) for f in features],
            }},
            style_function=lambda feature: {"weight": 14, "opacity": 0},
            tooltip=folium.Tooltip(f"<b>{title}</b><br>{detail}"),
        ).add_to(layer)
        middle = min(features, key=lambda f: abs(f["km"] - (start + end) / 2))
        coords = middle["coords"]
        folium.Marker(
            location=coords[len(coords) // 2],
            icon=folium.DivIcon(
                html=f'<div style="display:inline-block;margin-left:10px;padding:5px 9px;'
                f'background:rgba(255,255,255,.97);border:1px solid #94a3b8;border-radius:6px;'
                f'box-shadow:0 2px 6px #0f172a26;font-family:Inter,Segoe UI,Arial,sans-serif;'
                f'white-space:nowrap;color:#0f172a;line-height:1.3;">'
                f'<div style="font-size:13px;font-weight:800;">{title}</div>'
                f'<div style="font-size:10px;color:#475569;">{detail}</div></div>',
                icon_size=(135, 42), icon_anchor=(0, 21),
            ),
            tooltip=f"{title} · {detail}",
        ).add_to(layer)


