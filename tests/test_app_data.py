import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.config import DATASETS, NODATA_LABEL
from src.data_loader import (
    prepare_condition_road_data, prepare_n5_road_data, prepare_n55_road_data,
)


class AppDataTests(unittest.TestCase):
    def test_condition_colors_match_previous_loaders(self):
        previous = {
            "N5": prepare_n5_road_data("data/raw/N5/sf_north1.gpkg", "data/raw/N5/sf_south1.gpkg"),
            "N-55": prepare_n55_road_data("data/raw/N55/geometry_N55.gpkg",
                                         "data/raw/N55/N55_NB_24.08.26.csv",
                                         "data/raw/N55/N55_SB_24.08.26.csv"),
        }
        for road, path in DATASETS.items():
            expected = {f["km"]: f for f in previous[road]["features"]}
            actual = prepare_condition_road_data(path)
            self.assertEqual(len(actual["features"]), len(expected) + (2 if road == "N5" else 0))
            for feature in actual["features"]:
                if road == "N5" and feature["km"] in (1770, 1771):
                    self.assertEqual(feature["north_label"], NODATA_LABEL)
                    self.assertEqual(feature["south_label"], NODATA_LABEL)
                    continue
                keys = ["north_label", "north_color", "south_label", "south_color"]
                if road != "N5":
                    keys.append("coords")
                for key in keys:
                    self.assertEqual(feature[key], expected[feature["km"]][key])

    def test_road_direction_and_traffic_controls(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
        app.secrets["CARTO_API_KEY"] = "test"
        app.run()
        self.assertFalse(app.exception)
        for road in ("N5", "N-55", "Both"):
            for direction in ("North bound", "South bound"):
                app.get("button_group")[0].set_value(road)
                app.get("button_group")[1].set_value(direction)
                next(t for t in app.toggle if t.label == "Traffic count stations").set_value(True)
                app.run()
                self.assertFalse(app.exception)
                self.assertTrue(any("traffic count station(s) shown" in c.value for c in app.caption))


if __name__ == "__main__":
    unittest.main()
