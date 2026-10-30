from copy import deepcopy
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from resilience_data import build_network
from core_cases import core_cases
from ui.demo import demo_results


class DemoTests(unittest.TestCase):
    def test_cases_compare_without_mutating_network_or_input(self):
        network=build_network()
        before=deepcopy(network)
        for case in core_cases():
            applied=dict(case,days=60,percent=100)
            original=deepcopy(applied)
            base=demo_results(network,applied,False,False)
            same=demo_results(network,applied,False,False)
            self.assertEqual(base['scores'],same['scores'])
            response=demo_results(network,applied,True,True)
            for company in case['recipients']:
                self.assertIsNotNone(response['process_views'][company]['scores'][case['process']])
            self.assertEqual(applied,original)
        self.assertEqual(network,before)

    def test_guided_flow_reset_and_advanced_mode(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        self.assertFalse(app.exception)
        app.button(key='demo_apply').click().run()
        self.assertEqual(app.session_state.demo_step,2)
        self.assertTrue(any(r['kind']=='alternative' for r in app.session_state.demo_current_map['routes']))
        self.assertEqual(app.session_state.rr_events,[])
        app.button(key='demo_next').click().run()
        self.assertFalse(app.exception)
        alternative_name=app.session_state.rr_network['entities']['dongjin']['name']
        self.assertTrue(any(alternative_name in m.value for m in app.markdown))
        self.assertIn('ArF',app.session_state.demo_review['common_classes'])
        app.selectbox(key='demo_review_product').select('EUV').run()
        self.assertTrue(app.session_state.demo_review['candidate_eligible'])
        self.assertFalse(any(m['id']=='dongjin' for m in app.session_state.demo_current_map['markers']))
        self.assertTrue(any(m['id']=='fujifilm' for m in app.session_state.demo_current_map['markers']))
        app.selectbox(key='demo_review_product').select('ArF').run()
        self.assertTrue(app.session_state.demo_review['candidate_eligible'])
        self.assertFalse(any('첫 부족일' in m.value or '말일 보충' in m.value for m in app.markdown))
        app.toggle(key='demo_show_candidate').set_value(False).run()
        self.assertEqual(app.session_state.demo_review['candidate_id'],'dongjin')
        self.assertEqual(app.session_state.rr_events,[])
        app.button(key='demo_reset').click().run()
        self.assertIsNone(app.session_state.demo_applied)
        app.selectbox(key='demo_case').select(0).run()
        app.button(key='demo_apply').click().run()
        self.assertEqual(app.session_state.demo_applied['id'],'wafer')
        app.button(key='demo_advanced').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.rr_events,[])
        app.button(key='rr_back_demo').click().run()
        self.assertEqual(app.session_state.demo_applied['id'],'wafer')
        self.assertFalse(app.exception)
