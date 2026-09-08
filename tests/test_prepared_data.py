"""Run with python -m unittest discover -s tests."""
import unittest

import geopandas as gpd
import pandas as pd

from scripts.prepare_data import DATA, unique_rows


class PreparedDataTests(unittest.TestCase):
    def test_conflicting_duplicates_rejected(self):
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            unique_rows(pd.DataFrame({"km": [1, 1], "status": ["Good", "Poor"]}),
                        ["km", "status"], "test")

    def test_exact_duplicates_collapsed(self):
        result = unique_rows(pd.DataFrame({"km": [1, 1], "status": ["Good", "Good"]}),
                             ["km", "status"], "test")
        self.assertEqual(len(result), 1)

    def test_bad_keys_and_missing_columns_rejected(self):
        for frame in (pd.DataFrame({"km": [None], "status": ["Good"]}),
                      pd.DataFrame({"km": [float("inf")], "status": ["Good"]}),
                      pd.DataFrame({"km": [1]})):
            with self.assertRaises(ValueError):
                unique_rows(frame, ["km", "status"], "test")

    def test_source_status_and_geometry_preserved(self):
        for road in ("N5", "N55"):
            output = gpd.read_file(DATA / f"segments_{road}.gpkg").set_index("km")
            self.assertEqual(output.crs.to_epsg(), 4326)
            self.assertTrue(output.index.is_unique)
            self.assertTrue(output.index.is_monotonic_increasing)
            for direction, suffix in (("north", "NB"), ("south", "SB")):
                if road == "N5":
                    source = gpd.read_file(DATA / f"raw/N5/sf_{direction}1.gpkg").to_crs(4326).set_index("km")
                else:
                    source = pd.read_csv(DATA / f"raw/N55/N55_{suffix}_24.08.26.csv", usecols=["km", "status"]).set_index("km")
                expected = source.status.reindex(output.index)
                pd.testing.assert_series_equal(expected.fillna(pd.NA), output[f"status_{direction}"].fillna(pd.NA), check_names=False)
            geometry_source = gpd.read_file(DATA / ("raw/N5/n5_line.gpkg" if road == "N5" else "raw/N55/geometry_N55.gpkg")).to_crs(4326)
            geometry_source = geometry_source.set_index("seg_id" if road == "N5" else "km")
            self.assertEqual(set(output.index), set(geometry_source.index))
            self.assertTrue(output.geometry.geom_equals_exact(geometry_source.geometry.reindex(output.index), tolerance=0).all())
            if road == "N5":
                self.assertTrue(output.loc[[1770, 1771], ["status_north", "status_south"]].isna().all().all())


if __name__ == "__main__":
    unittest.main()
