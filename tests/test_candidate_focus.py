import unittest
from pathlib import Path
from unittest.mock import patch
from company_evidence import evidence_bundle
from resilience_data import build_network
from news.vendor_candidates import registered_candidates
from ui.research_map import map_matches,focus_candidate


class FocusTests(unittest.TestCase):
    def test_focus_and_missing_coordinates(self):
        q='SUMCO 300mm PW 대체 기업'
        candidates=registered_candidates(evidence_bundle(),q)
        data=map_matches(build_network(),q,candidates=candidates)
        focused,marker=focus_candidate(data,'SK siltron')
        self.assertEqual(focused['camera_focus']['lat'],marker['lat'])
        self.assertEqual(focused['selected']['id'],'research:sk-siltron')
        other,_=focus_candidate(data,'Shin-Etsu 그룹 · SEH')
        self.assertNotEqual(focused['camera_context'],other['camera_context'])
        missing,marker=focus_candidate(data,'Siltronic')
        self.assertIsNone(marker)
        self.assertNotIn('camera_focus',missing)
        self.assertNotIn('selected',data)
        overview,marker=focus_candidate(data,None)
        self.assertIsNone(marker)
        self.assertNotIn('camera_focus',overview)

    def test_shared_selection_renders_conditions_and_changes_focus(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=40).run()
        app.radio(key='demo_review_view').set_value('AI 분석').run()
        app.text_area(key='research_query').set_value('SUMCO 300mm PW 대체 기업').run()
        self.assertFalse(app.exception)
        with patch('ui.research_map.render_research_map') as render:
            app.selectbox(key='research_candidate_source').select('SK siltron').run()
            self.assertEqual(render.call_args.kwargs['selected_candidate'],'SK siltron')
        self.assertFalse(app.exception)
        self.assertTrue(any('요구 직경' in x.value for x in app.markdown))
        with patch('ui.research_map.render_research_map') as render:
            app.selectbox(key='research_candidate_source').select('Siltronic').run()
            self.assertEqual(render.call_args.kwargs['selected_candidate'],'Siltronic')
        self.assertFalse(app.exception)
