"""Preserve road sources and build validated, app-ready GeoPackages."""
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIELDS = ["km", "status_north", "status_south", "geometry"]


def apply_n5_conditions(frame):
    overrides = json.loads((DATA / "n5_condition_overrides.json").read_text(encoding="utf-8"))
    for section in overrides:
        mask = frame.km.between(section["start_km"], section["end_km"])
        frame.loc[mask, ["status_north", "status_south"]] = section["label"]
    return frame


def digest(path):
    with open(path, "rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def preserve(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if digest(source) != digest(target):
            raise ValueError(f"Preserved source differs: {target}")
    else:
        shutil.copy2(source, target)
    if digest(source) != digest(target):
        raise ValueError(f"Copy verification failed: {target}")


def unique_rows(frame, required, name):
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"{name}: missing columns {sorted(missing)}")
    frame = frame[required].copy()
    frame["km"] = pd.to_numeric(frame.km, errors="raise")
    if not np.isfinite(frame.km).all():
        raise ValueError(f"{name}: missing/nonfinite kilometer keys")
    frame = frame.drop_duplicates()
    if frame.km.duplicated().any():
        raise ValueError(f"{name}: conflicting duplicate kilometer keys")
    return frame


def read_geometry(path, columns):
    frame = gpd.read_file(path)
    if frame.crs is None:
        raise ValueError(f"{path}: missing CRS")
    return unique_rows(frame.to_crs(4326), columns, str(path))


def validate(frame, name, report, allowed_degenerate=()):
    if list(frame.columns) != FIELDS or frame.km.duplicated().any():
        raise ValueError(f"{name}: incorrect output schema or duplicate keys")
    if frame.crs.to_epsg() != 4326 or not frame.km.is_monotonic_increasing:
        raise ValueError(f"{name}: incorrect CRS or order")
    if frame.geometry.isna().any() or frame.geometry.is_empty.any():
        raise ValueError(f"{name}: missing/empty geometry")
    if not frame.geom_type.eq("LineString").all():
        raise ValueError(f"{name}: expected LineString geometry")
    invalid = frame.loc[~frame.is_valid]
    for row in invalid.itertuples():
        if row.km not in allowed_degenerate or row.geometry.length != 0:
            raise ValueError(f"{name}: invalid geometry at km {row.km}")
    report[name] = {
        "rows": len(frame), "km_min": float(frame.km.min()),
        "km_max": float(frame.km.max()),
        "preserved_zero_length_geometry_km": invalid.km.tolist(),
        "missing_north_status": int(frame.status_north.isna().sum()),
        "missing_south_status": int(frame.status_south.isna().sum()),
    }


def main():
    raw = DATA / "raw"
    original = ROOT / "New folder"
    for source in sorted(original.rglob("*")):
        if not source.is_file():
            continue
        group = "archives" if source.suffix == ".rar" else "N55" if source.suffix == ".csv" else "N5"
        preserve(source, raw / group / source.name)
    backup = DATA / "backup"
    for road in ("N5", "N55"):
        target = backup / f"segments_{road}.gpkg"
        if not target.exists():
            preserve(DATA / target.name, target)
    # The original N55 network is an immutable geometry source on every run.
    preserve(backup / "segments_N55.gpkg", raw / "N55" / "geometry_N55.gpkg")
    report = {}
    north = read_geometry(raw / "N5/sf_north1.gpkg", ["km", "status", "geometry"])
    south = read_geometry(raw / "N5/sf_south1.gpkg", ["km", "status", "geometry"])
    n5_geometry = gpd.read_file(raw / "N5/n5_line.gpkg").rename(columns={"seg_id": "km"})
    if n5_geometry.crs is None:
        raise ValueError("n5_line.gpkg: missing CRS")
    n5 = unique_rows(n5_geometry.to_crs(4326), ["km", "geometry"], "n5_line.gpkg")
    report["N5_geometry_source"] = "raw/N5/n5_line.gpkg (seg_id = km)"
    for direction, source in (("north", north), ("south", south)):
        report[f"N5_unmatched_{direction}_status_km"] = sorted(set(source.km) - set(n5.km))
        n5 = n5.merge(source[["km", "status"]].rename(columns={"status": f"status_{direction}"}),
                      on="km", how="left", validate="one_to_one")
    n5 = apply_n5_conditions(n5[FIELDS].copy())
    report["N5_direction_only_km"] = {
        "north": sorted(set(north.km) - set(south.km)),
        "south": sorted(set(south.km) - set(north.km)),
    }
    n55 = read_geometry(raw / "N55/geometry_N55.gpkg", ["km", "geometry"])
    for direction, filename in (("north", "N55_NB_24.08.26.csv"), ("south", "N55_SB_24.08.26.csv")):
        status = unique_rows(pd.read_csv(raw / "N55" / filename, usecols=["km", "status"]),
                             ["km", "status"], filename)
        report[f"N55_unmatched_{direction}_csv_km"] = sorted(set(status.km) - set(n55.km))
        n55 = n55.merge(status.rename(columns={"status": f"status_{direction}"}),
                        on="km", how="left", validate="one_to_one")
    outputs = {"N5": n5, "N55": n55[FIELDS]}
    # These are pre-existing collapsed lines, retained without inventing geometry.
    known_degenerate = {818, 935, 937, 939, 941, 943, 945, 947, 949, 985}
    with tempfile.TemporaryDirectory(prefix="prepare-", dir=DATA) as staging:
        for road, frame in outputs.items():
            frame = frame.sort_values("km").reset_index(drop=True)
            validate(frame, road, report, known_degenerate if road == "N55" else ())
            path = Path(staging) / f"segments_{road}.gpkg"
            frame.to_file(path, layer=f"segments_{road}", driver="GPKG", index=False)
            saved = gpd.read_file(path)
            pd.testing.assert_frame_equal(
                frame.drop(columns="geometry").fillna(pd.NA),
                saved.drop(columns="geometry").fillna(pd.NA), check_dtype=False)
            if not frame.geometry.geom_equals_exact(saved.geometry, tolerance=0).all():
                raise ValueError(f"{road}: geometry changed during export")
        # Both files are validated before either live output is replaced.
        for road in outputs:
            name = f"segments_{road}.gpkg"
            (Path(staging) / name).replace(DATA / name)
    (DATA / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
