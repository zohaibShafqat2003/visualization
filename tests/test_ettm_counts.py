import unittest
from pathlib import Path
from unittest.mock import patch

import folium
from streamlit.testing.v1 import AppTest

from src.config import ETTM_COUNTS_PATH
from src.data_loader import prepare_ettm_stations
from src.map_layers import add_station_markers
from src.popups import build_count_marker_html


class ETTMCountsTests(unittest.TestCase):
    def test_supplied_daily_counts_and_coordinates(self):
        stations = prepare_ettm_stations(ETTM_COUNTS_PATH, 0)
        self.assertEqual(len(stations), 13)
        self.assertEqual({s['road_id'] for s in stations}, {'N-5'})
        self.assertEqual(stations[0]['adt_text'], '10,324')
        self.assertIn('2,076', stations[0]['popup'])
        self.assertIn('Wagon/Jeep', stations[0]['popup'])
        self.assertIn('ETTM Toll Plaza', build_count_marker_html(stations[0]))
        approximate = [s for s in stations if 'Approximate coordinates' in s['popup']]
        self.assertEqual(len(approximate), 2)
        self.assertEqual(approximate[0]['lat'], 32.0337)

    def test_collocated_chenab_records_remain_accessible(self):
        stations = prepare_ettm_stations(ETTM_COUNTS_PATH, 0)
        fmap = folium.Map()
        add_station_markers(fmap, stations)
        cluster = next(c for c in fmap._children.values() if c.__class__.__name__ == 'MarkerCluster')
        self.assertEqual(len(cluster._children), 12)
        chenab = next(m for m in cluster._children.values() if m.location == [32.491634, 74.089487])
        popup = next(c for c in chenab._children.values() if isinstance(c, folium.Popup))
        for expected in ('Chenab SBC', 'Chenab NBC', '15,637', '15,893'):
            self.assertIn(expected, popup.html.render())

    def test_ettm_records_follow_route_section(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=40)
        app.secrets['CARTO_API_KEY'] = 'test'
        app.run()
        self.assertFalse(app.exception)
        for direction in ['North bound', 'South bound']:
            app.get('button_group')[0].set_value(direction)
            next(t for t in app.toggle if t.label == 'Traffic count stations').set_value(True)
            with patch('src.map_layers.add_station_markers', wraps=add_station_markers) as render:
                app.run()
            self.assertFalse(app.exception)
            stations = render.call_args.args[1]
            self.assertEqual(sum(s.get('label') == 'ETTM Toll Plaza' for s in stations), 12)
            self.assertNotIn('Khanbela', [s.get('name') for s in stations])
            self.assertEqual({s['road_id'] for s in stations}, {'N-5'})
            self.assertTrue(any('traffic count station(s) shown' in c.value for c in app.caption))


if __name__ == '__main__':
    unittest.main()
