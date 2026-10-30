from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from ui.factory_fire_case import FIRE
from ui.verified_globe import evidence_globe_data


class FactoryFireCaseTests(unittest.TestCase):
    def test_damage_and_replacement_keep_distinct_supplier_connections(self):
        damaged = evidence_globe_data('fire', 2, False)
        self.assertEqual(damaged['routes'][0]['start'], 'akm')
        self.assertEqual(damaged['routes'][0]['status'], 'blocked')
        self.assertEqual(damaged['routes'][0]['disruption_label'], '공장 화재 · 공급 제약')
        replaced = evidence_globe_data('fire', 3, True)
        self.assertEqual(replaced['routes'][0]['start'], 'ess')
        self.assertEqual(replaced['routes'][0]['end'], 'rme')
        self.assertNotIn('akm', {m['id'] for m in replaced['markers']})

    def test_representative_case_steps_and_return(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertFalse(any(b.key == 'demo_featured_case' for b in app.button))
        app.selectbox(key='verified_case').select(FIRE).run()
        for stage in (1, 2, 3):
            app.button(key='verified_step_' + str(stage)).click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state.verified_step, stage)
        app.segmented_control(key='verified_compare').set_value('대응 전').run()
        self.assertFalse(app.exception)
        app.segmented_control(key='verified_compare').set_value('대응 후').run()
        self.assertFalse(app.exception)
        app.button(key='demo_map_mode').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('plotly_chart')), 1)
        app.button(key='demo_map_mode').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('plotly_chart')), 0)
        app.selectbox(key='verified_case').select('기존 시나리오 보기').run()
        self.assertFalse(app.exception)
        self.assertTrue(any(b.key == 'demo_apply' for b in app.button))
