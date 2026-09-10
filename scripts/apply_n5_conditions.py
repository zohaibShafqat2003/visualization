"""Update N5 condition fields, preserving a backup and verifying the export."""
import shutil
import tempfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

from prepare_data import DATA, apply_n5_conditions


def main():
    path = DATA / "segments_N5.gpkg"
    backup = DATA / "backup/segments_N5_before_project_conditions.gpkg"
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(path, backup)
    original = gpd.read_file(path)
    updated = apply_n5_conditions(original.copy())
    with tempfile.TemporaryDirectory(dir=DATA, prefix="n5-conditions-") as staging:
        output = Path(staging) / path.name
        updated.to_file(output, layer="segments_N5", driver="GPKG", index=False)
        saved = gpd.read_file(output)
        pd.testing.assert_frame_equal(updated.drop(columns="geometry"), saved.drop(columns="geometry"), check_dtype=False)
        assert original.geometry.geom_equals_exact(saved.geometry, tolerance=0).all()
        assert original.crs == saved.crs
        status_columns = ["status_north", "status_south"]
        changed = original[status_columns].fillna("").ne(saved[status_columns].fillna("")).any(axis=1)
        print(f"Updated {changed.sum()} N5 rows. Geometry and all exported fields verified.")
        output.replace(path)


if __name__ == "__main__":
    main()
