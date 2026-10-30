from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from news.article_mock import cases, load_mock, attach_mock_commentary
from news.article_briefing import article_briefing, briefing_markdown
from news.article_review import review_article
from resilience_data import build_network


class MockArticleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()

    def reviewed(self, draft, saved):
        proposal = saved['value']
        review = review_article(self.network,draft,proposal['target'],proposal['quote'],
                                proposal['claim_type'],proposal['scope'],fields=proposal['fields'])
        review['extraction']={'method':'mock_assisted_human_review','case_id':saved['case_id']}
        attach_mock_commentary(review,saved)
        return review

    def test_all_twelve_authored_responses_share_real_validation_and_never_use_network(self):
        before=deepcopy(self.network)
        with patch('news.article_llm.urlopen',side_effect=AssertionError('No network')):
            for case in cases():
                with self.subTest(case=case['id']):
                    draft,saved=load_mock(self.network,case['id'])
                    review=self.reviewed(draft,saved)
                    self.assertIn(review['mock_commentary']['text'],article_briefing(review)['interpretation'])
                    self.assertIn('모의 LLM 응답',briefing_markdown(review))
                    self.assertIsNone(review['simulation_candidate'])
                    self.assertIsNone(review['reported_rate'])
                    self.assertEqual(self.network,before)

    def test_editing_classification_discards_stale_authored_commentary(self):
        draft,saved=load_mock(self.network,'tariff')
        proposal=saved['value']
        review=review_article(self.network,draft,proposal['target'],proposal['quote'],
                              '미분류 · 검토 필요',proposal['scope'],fields=proposal['fields'])
        attach_mock_commentary(review,saved)
        self.assertNotIn('mock_commentary',review)
        self.assertIn('mock_commentary_omitted',review)

    @patch.dict('os.environ',{'SUPPLY_ARTICLE_LLM_UI':'0'})
    def test_mock_to_save_to_map_preserves_scenario_and_keeps_real_api_disabled(self):
        from streamlit.testing.v1 import AppTest
        with patch('ui.article_llm.extract_article',side_effect=AssertionError('No API')) as api:
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
            app.session_state['rr_workspace_mode'] = '상세 모드'
            app.run(timeout=30)
            before=deepcopy(app.session_state['rr_result'])
            app.button(key='rr_article_open').click().run(timeout=30)
            app.selectbox(key='rr_mock_case').select('factory_unknown')
            next(b for b in app.button if b.label=='가상 기사와 모의 응답 불러오기').click().run(timeout=30)
            app.text_input(key='rr_openai_key_input').set_value('synthetic-key-not-real').run(timeout=30)
            self.assertTrue(next(b for b in app.button if b.label=='LLM으로 검토 초안 추출').disabled)
            next(b for b in app.button if b.label=='제안을 아래 검토 양식에 채우기').click().run(timeout=30)
            self.assertEqual(app.selectbox(key='rr_article_target').value,'jsr')
            self.assertEqual(app.selectbox(key='rr_fact_supply_status').value,'공급 영향 미확인 명시')
            next(b for b in app.button if b.label=='검토 결과 저장 · 경로 확인').click().run(timeout=30)
            self.assertFalse(app.exception)
            review=app.session_state['rr_article_review']
            self.assertEqual(review['extraction']['method'],'mock_assisted_human_review')
            self.assertIn('mock_commentary',review)
            self.assertEqual(app.session_state['rr_result'],before)
            markup=' '.join(x.value for x in [*app.markdown,*app.caption])
            self.assertIn('모의 LLM 응답',markup)
            self.assertIn('JSR 전체 공급 중단으로 확대하지 않고',markup)
            app.button(key='rr_article_map_button').click().run(timeout=30)
            self.assertFalse(app.exception)
            self.assertTrue(app.session_state['rr_article_map_open'])
            self.assertEqual(app.session_state['rr_result'],before)
            self.assertEqual(api.call_count,0)


if __name__=='__main__':
    unittest.main()
