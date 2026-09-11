import json
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
import folium

from src.config import DATASETS, STATUS_CATEGORY_COLORS
from src.data_loader import condition_kilometers, road_status_categories
from src.map_layers import add_condition_legend
from src.route_section import prepare_n5_section


class ProjectConditionTests(unittest.TestCase):
    def test_only_requested_status_rows_changed(self):
        frame = gpd.read_file(DATASETS['N5'])
        original = gpd.read_file('data/backup/segments_N5_before_project_conditions.gpkg')
        expected = original.copy()
        rules = json.loads(Path('data/n5_condition_overrides.json').read_text())
        for rule in rules:
            mask = expected.km.between(rule['start_km'], rule['end_km'])
            expected.loc[mask, ['status_north', 'status_south']] = rule['label']
        pd.testing.assert_frame_equal(frame.drop(columns='geometry'), expected.drop(columns='geometry'))
        self.assertTrue(frame.geometry.geom_equals_exact(original.geometry, tolerance=0).all())

    def test_categories_colors_and_map_key(self):
        road, _, _ = prepare_n5_section(DATASETS['N5'])
        roads = {'N5': road}
        for direction in ['north', 'south']:
            totals = condition_kilometers(roads, ['N5'], direction)
            self.assertEqual(totals['iRAP'], 55)
            for feature in road['features']:
                if 1260 <= feature['km'] <= 1280:
                    self.assertEqual(feature[f'{direction}_label'], 'LDA')
            self.assertEqual(totals['AIB'], 72)
            self.assertEqual(totals['Cantt/RDA'], 27)
            by_km = {feature['km']: feature[f'{direction}_label'] for feature in road['features']}
            self.assertNotEqual(by_km[1538], 'Cantt/RDA')
            self.assertTrue(all(by_km[km] == 'Cantt/RDA' for km in range(1539, 1566)))
            self.assertEqual(by_km[1566], 'AIB')
            categories = road_status_categories(roads, ['N5'], direction)
            for name in ['iRAP', 'AIB', 'LDA', 'Cantt/RDA']:
                self.assertIn((name, STATUS_CATEGORY_COLORS[name]), categories)
            fmap = folium.Map()
            add_condition_legend(fmap, direction, totals, categories)
            html = fmap.get_root().render()
            for name in ['iRAP', 'AIB', 'LDA', 'Cantt/RDA']:
                self.assertIn(name, html)
                self.assertIn(STATUS_CATEGORY_COLORS[name], html)


if __name__ == '__main__':
    unittest.main()
