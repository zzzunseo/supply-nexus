from copy import deepcopy
from pathlib import Path
import unittest
from resilience_data import build_network
from ui.target_finder import choose_target,target_options


class TargetFinderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.network=build_network()

    def test_country_filters_candidates_without_creating_country_outage(self):
        options=target_options(self.network,'지역·물류','일본')
        self.assertIn('jsr',options)
        self.assertNotIn('tsmc',options)
        self.assertTrue(all(self.network['entities'][key]['country']=='일본' for key in options))
        state={'rr_events':[{'targets':['tsmc']}],'rr_days':30,'rr_material_scopes':[]}
        before=deepcopy(state)
        choose_target(state,self.network,'jsr')
        self.assertEqual(state['rr_events'],before['rr_events'])
        self.assertEqual(state['rr_material_scopes'],[])
        self.assertEqual(state['rr_focus'],'jsr')
        self.assertNotIn('rr_chat_text',state)

    def test_question_adds_only_name_clears_stale_draft_and_preserves_engine(self):
        state={'rr_events':[],'rr_days':60,'rr_function_pending':{'old':True},'rr_function_context':{'old':True}}
        choose_target(state,self.network,'logistics:kaohsiung',True)
        self.assertEqual(state['rr_chat_text'].strip(),'가오슝항')
        self.assertEqual(state['rr_events'],[])
        self.assertEqual(state['rr_days'],60)
        self.assertNotIn('rr_function_pending',state)
        with self.assertRaises(ValueError): choose_target(state,self.network,'일본',True)

    def test_dialog_selection_syncs_existing_map_search_and_question_without_api(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'tests/fixtures/panel_components.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        app.selectbox(key='rr_chat_mode').set_value('기사 검토 · 모의 대화').run(timeout=30)
        baseline=deepcopy(app.session_state['rr_result']['scores'])
        app.button(key='rr_target_find').click().run(timeout=30)
        app.radio(key='rr_finder_category').set_value('지역·물류').run(timeout=30)
        app.selectbox(key='rr_finder_country').set_value('일본').run(timeout=30)
        app.selectbox(key='rr_finder_target').set_value('jsr').run(timeout=30)
        app.button(key='rr_finder_question').click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['rr_focus'],'jsr')
        self.assertEqual(app.selectbox(key='rr_name_company').value,'jsr')
        self.assertEqual(app.text_input(key='rr_chat_text').value.strip(),'JSR')
        self.assertEqual(app.session_state['rr_events'],[])
        self.assertEqual(app.session_state['rr_result']['scores'],baseline)
        self.assertFalse(app.session_state['rr_target_finder_open'])
        app.button(key='rr_target_find').click().run(timeout=30)
        app.radio(key='rr_finder_category').set_value('소재').run(timeout=30)
        material=target_options(self.network,'소재')[0]
        app.selectbox(key='rr_finder_target').set_value(material).run(timeout=30)
        app.button(key='rr_finder_map').click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['rr_focus'],material)
        self.assertEqual(app.session_state['rr_events'],[])


if __name__=='__main__': unittest.main()
