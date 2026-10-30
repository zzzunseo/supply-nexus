import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from resilience_data import build_network
from ui.logistics_demo import demo_cases
from ui.response_review import review_profile


class DetailWorkspaceTests(unittest.TestCase):
    def test_strait_candidates_match_selected_case(self):
        network=build_network()
        for name,candidate in [('malacca','logistics:lombok'),('suez','logistics:cape')]:
            case=next(c for c in demo_cases() if c['id']==name)
            self.assertEqual(review_profile(network,case)['candidate_id'],candidate)

    def test_detail_calculation_and_return_without_llm_panels(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        app.button(key='demo_advanced').click().run()
        self.assertFalse(app.exception)
        self.assertEqual([t.label for t in app.tabs],['8대 공정','소재 60종','원료 연결','시설 위치','관계 근거','재고·대체 가정','물류 설정','계산 검증'])
        self.assertFalse(app.chat_input)
        materials=[c['id'] for col in app.session_state.rr_flow_data['columns'] for c in col['cards'] if c['kind']=='material']
        for material in materials[:3]:
            app.selectbox(key='detail_compact_material').select(material).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state.detail_selected_material_node,app.session_state.detail_alternative_material)
        for i in range(8):
            app.button(key='detail_process_'+str(i)).click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state.rr_flow_data['process'],app.session_state.rr_flow_process)
            self.assertEqual(len(app.session_state.rr_flow_data['columns']),4)
        app.selectbox(key='detail_check_case').select(4).run()
        app.button(key='detail_run_check').click().run()
        self.assertFalse(app.exception)
        app.button(key='rr_back_demo').click().run()
        self.assertFalse(app.exception)
