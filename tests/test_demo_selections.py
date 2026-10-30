from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from resilience_data import build_network
from ui.demo_scenarios import choices,selected_case,decorate,connections
from ui.demo_session import commit_case
from ui.demo import presentation_result
from ui.response_review import review_payload,review_profile


class ExplicitPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.network=build_network();cls.result=presentation_result(cls.network)

    def test_every_registered_company_and_material_maps_only_registered_links(self):
        for category in ('기업','소재'):
            for target,_ in choices(self.network,category):
                with self.subTest(category=category,target=target):
                    case=selected_case(self.network,category,target,'공급 중단')
                    state={};self.assertTrue(commit_case(state,self.network,case,30,100))
                    applied=state['demo_applied'];data=decorate(review_payload(self.network,self.result,applied),applied)
                    self.assertTrue(any(m['impact']=='origin' for m in data['markers']))
                    self.assertTrue(all(r['status']=='blocked' for r in data['routes'] if r['kind']=='primary'))
                    for route in data['routes']:
                        self.assertIn('material',route)
                        if route['kind']=='alternative':self.assertNotEqual(route['start'],self.network['nodes'][case['target']]['company_id'])
                    self.assertTrue(all(m['score'] is None for m in data['markers']))

    def test_tariff_is_cost_only_and_never_shows_damage_or_break(self):
        case=selected_case(self.network,'소재','supply:jsr:photoresist','관세 부과')
        state={};self.assertTrue(commit_case(state,self.network,case,30,125))
        applied=state['demo_applied'];data=decorate(review_payload(self.network,self.result,applied),applied)
        self.assertTrue(data['tariff']);self.assertTrue(all(r['status']=='cost' for r in data['routes']))
        self.assertFalse(any(m['impact']=='origin' for m in data['markers']))
        self.assertFalse(review_profile(self.network,applied)['candidate_eligible'])

    def test_direct_selection_event_switch_apply_and_reset(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        app.radio(key='demo_input_mode').set_value('직접 선택').run()
        app.selectbox(key='demo_target').select('supply:jsr:photoresist').run()
        app.selectbox(key='demo_event').select('관세 부과').run()
        app.number_input(key='demo_percent').set_value(125).run()
        app.button(key='demo_apply').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state.demo_current_map['tariff'])
        app.button(key='demo_next').click().run();self.assertFalse(app.exception)
        app.button(key='demo_reset').click().run()
        app.radio(key='demo_input_mode').set_value('직접 선택').run()
        app.selectbox(key='demo_category').select('기업').run()
        app.selectbox(key='demo_target').select('sumco').run()
        app.selectbox(key='demo_event').select('공급 중단').run()
        app.button(key='demo_apply').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.demo_applied['issue_target'],'sumco')
        routes=app.session_state.demo_current_map['routes']
        self.assertTrue(all(r['status']=='blocked' for r in routes if r['kind']=='primary'))
        self.assertTrue(any(r['kind']=='alternative' for r in routes))
        app.button(key='demo_next').click().run();self.assertFalse(app.exception)
        self.assertTrue(app.session_state.demo_review['candidate_eligible'])
