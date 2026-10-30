from copy import deepcopy
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from resilience_data import build_network
from ui.demo import presentation_result
from ui.logistics_demo import demo_cases
from ui.demo_scenarios import selected_case
from ui.demo_comparison import change_comparison
from ui.demo_interaction import prepare_map,accept_pick
from ui.response_review import review_payload


class MapComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.network=build_network();cls.result=presentation_result(cls.network)

    def test_comparison_preserves_case_and_camera_but_removes_effects_and_candidates(self):
        cases=[dict(c,percent=100) for c in demo_cases()]
        cases.append(dict(selected_case(self.network,'소재','supply:jsr:photoresist','관세 부과'),days=30,percent=25))
        for case in cases:
            with self.subTest(case=case['name']):
                raw=review_payload(self.network,self.result,case)
                original=deepcopy(raw)
                state={'demo_applied':case,'demo_compare':'사건 적용','demo_step':3,'demo_active_case_id':case['id'],'demo_revision':1}
                after=prepare_map(raw,state);saved=deepcopy(state['demo_applied'])
                state['demo_compare']='적용 전';change_comparison(state)
                before=prepare_map(raw,state)
                self.assertEqual(before['camera_context'],after['camera_context'])
                self.assertNotEqual(before['context'],after['context'])
                self.assertTrue(all(r['kind']=='primary' and r['status']=='normal' for r in before['routes']))
                self.assertTrue(all(m['impact']=='normal' for m in before['markers']))
                self.assertEqual(prepare_map(before,state)['camera_context'],before['camera_context'])
                self.assertEqual(prepare_map(before,state)['scenario_summary'],before['scenario_summary'])
                self.assertIn(str(case['days'])+'일 가정',before['scenario_summary'])
                self.assertFalse(accept_pick(state,dict(kind='marker',id=after['markers'][0]['id'],context=after['context']),after))
                state['demo_compare']='사건 적용'
                restored=prepare_map(raw,state)
                self.assertEqual(restored['routes'],after['routes'])
                self.assertEqual(state['demo_applied'],saved)
                self.assertEqual(raw,original)

    def test_app_comparison_does_not_reset_applied_case_or_hide_event_explanation(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        app.button(key='demo_apply').click().run();app.button(key='demo_next').click().run()
        original=deepcopy(app.session_state.demo_applied)
        camera=app.session_state.demo_current_map['camera_context']
        app.session_state.demo_compare='적용 전';app.run()
        self.assertFalse(app.exception)
        self.assertFalse(app.session_state.demo_current_map['applied'])
        self.assertEqual(app.session_state.demo_current_map['camera_context'],camera)
        self.assertTrue(app.toggle(key='demo_show_candidate').disabled)
        self.assertEqual(app.session_state.demo_applied,original)
        app.session_state.demo_compare='사건 적용';app.run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state.demo_current_map['applied'])
        self.assertTrue(any(r['kind']=='alternative' for r in app.session_state.demo_current_map['routes']))
        if any(b.key=='demo_back_impact' for b in app.button):app.button(key='demo_back_impact').click().run()
        if any(b.key=='demo_previous' for b in app.button):app.button(key='demo_previous').click().run()
        app.selectbox(key='demo_case').select(0).run()
        self.assertEqual(app.session_state.demo_compare,'사건 적용')
