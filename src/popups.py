import pandas as pd


def format_count(value):
    if value >= 1000:
        return f"{value / 1000:.1f}k"
    return f"{value:.0f}"


def safe_num(row, col):
    val = row.get(col)
    try:
        return float(val) if pd.notna(val) else 0.0
    except (TypeError, ValueError):
        return 0.0


def build_count_marker_html(station):
    return f"""
    <div style="position:relative;display:flex;align-items:center;gap:4px;
        font-family:Inter,Segoe UI,Arial,sans-serif;transform:translate(-13px,-13px);">
        <div style="width:22px;height:22px;border-radius:50%;background:#f97316;
            border:3px solid white;box-shadow:0 2px 8px rgba(15,23,42,.32);
            display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <div style="width:7px;height:7px;border-radius:50%;background:white;"></div>
        </div>
        <div style="background:rgba(255,255,255,.97);border:1px solid #fecaca;
            border-radius:6px;padding:2px 6px 3px 6px;
            box-shadow:0 2px 8px rgba(15,23,42,.22);line-height:1;white-space:nowrap;">
            <div style="font-size:9px;color:#64748b;font-weight:700;letter-spacing:.02em;">ADT</div>
            <div style="font-size:12px;color:#0f172a;font-weight:800;margin-top:1px;">{station['adt_compact']}</div>
        </div>
    </div>
    """


def build_counts_popup(row):
    adt = safe_num(row, "ADT")
    heavy = safe_num(row, "heavy_traffic")
    heavy_share = row.get("heavy_share")
    heavy_pct = f"{float(heavy_share) * 100:.1f}%" if pd.notna(heavy_share) else "N/A"

    cars = safe_num(row, "cars")
    mc = safe_num(row, "mc")
    rickshaws = safe_num(row, "rickshaws")
    light_pickup = safe_num(row, "light_pickup")
    mini_bus = safe_num(row, "mini_bus")
    trucks_pickups_mini_buses = light_pickup + mini_bus
    large_bus = safe_num(row, "large_bus")

    return f"""
    <div style="font-family:Inter,Segoe UI,Arial,sans-serif;min-width:300px;color:#0f172a;">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;">
            <div style="border:1px solid #e2e8f0;border-radius:8px;padding:10px;background:#f8fafc;">
                <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.04em;">Average daily traffic (ADT)</div>
                <div style="font-size:24px;font-weight:800;margin-top:3px;">{adt:,.0f}</div>
            </div>
            <div style="border:1px solid #f3b59b;border-radius:8px;padding:10px;background:#fff0e8;">
                <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.04em;">Heavy traffic share</div>
                <div style="font-size:24px;font-weight:800;margin-top:3px;color:#e85d2a;">{heavy_pct}</div>
            </div>
        </div>
        <div style="font-size:13px;color:#64748b;font-weight:700;margin-bottom:7px;">Vehicle categories</div>
        <div style="display:grid;grid-template-columns:1fr auto;gap:5px 18px;font-size:13px;line-height:1.25;">
            <span>Cars</span><b>{cars:,.0f}</b>
            <span>Motorcycles</span><b>{mc:,.0f}</b>
            <span>Rickshaws</span><b>{rickshaws:,.0f}</b>
            <span>Large buses</span><b>{large_bus:,.0f}</b>
            <span>Light trucks/mini bus</span><b>{trucks_pickups_mini_buses:,.0f}</b>
            <span>Trucks (2/3/4/5/6 axles)</span><b>{heavy:,.0f}</b>
        </div>
    </div>
    """
