from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from news.article_briefing import article_briefing, briefing_markdown
from news.article_review import article_draft, review_article
from resilience_data import build_network


class BriefingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()

    def test_twelve_cases_keep_unknowns_and_never_mutate_review(self):
        cases = json.loads((Path(__file__).parent/'fixtures/article_llm_cases.json').read_text(encoding='utf-8'))
        for case in cases:
            with self.subTest(case=case['id']):
                draft = article_draft(self.network,'검증용 가상 기사',case['body'])
                fields = {'supply_status': dict(value=case['supply_status'],quote=case['body'] if case['supply_status'] else None)}
                review = review_article(self.network,draft,case['target'],case['body'],case['claim_type'],case['scope'],fields=fields)
                before = deepcopy(review)
                note = article_briefing(review)
                text = briefing_markdown(review)
                self.assertEqual(review,before)
                self.assertEqual(note['event_date'],'미확인')
                self.assertIn('API 미사용',text)
                self.assertIn(case['body'],text)
                self.assertIsNone(review['simulation_candidate'])
                if case['id']=='tariff':
                    self.assertIn('환산하지 않습니다',note['interpretation'])
                if case['id']=='partial_recovery':
                    self.assertIn('전체 고객 공급이 정상화',note['interpretation'])
                if case['target'] is None:
                    self.assertIn('연결을 보류',note['interpretation'])

    def test_inconsistent_manual_classification_requires_recheck(self):
        body='JSR의 출하가 중단됐다.'
        review=review_article(self.network,article_draft(self.network,'가상 기사',body),'jsr',body,
                              '제한 가능성·계획','특정 시설·제품',
                              fields={'supply_status':dict(value='공급 중단·감소 명시',quote=body)})
        self.assertIsNotNone(article_briefing(review)['caution'])

    @patch.dict('os.environ', {'SUPPLY_ARTICLE_LLM_UI':'0'})
    def test_offline_ui_hides_api_and_keeps_scenario_while_showing_briefing(self):
        from streamlit.testing.v1 import AppTest
        with patch('ui.article_llm.extract_article',side_effect=AssertionError('API must not run')) as api:
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
            app.session_state['rr_workspace_mode'] = '상세 모드'
            app.run(timeout=30)
            before=deepcopy(app.session_state['rr_result'])
            app.button(key='rr_article_open').click().run(timeout=30)
            body='JSR의 공장에서 화재가 발생했다. 출하 영향은 미확인이다.'
            app.text_area(key='rr_article_body').set_value(body)
            next(b for b in app.button if b.label=='원문에서 대상 후보 찾기').click().run(timeout=30)
            self.assertIn('rr_openai_key_input',[x.key for x in app.text_input])
            self.assertTrue(next(b for b in app.button if b.label=='LLM으로 검토 초안 추출').disabled)
            app.selectbox(key='rr_article_target').select('jsr')
            app.text_area(key='rr_article_quote').set_value(body)
            app.selectbox(key='rr_article_type').select('사건 발생 · 공급 영향 미확인')
            app.selectbox(key='rr_article_scope').select('특정 시설·제품')
            next(b for b in app.button if b.label=='검토 결과 저장 · 경로 확인').click().run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['rr_result'],before)
            self.assertEqual(api.call_count,0)
            markup=' '.join(x.value for x in app.markdown)
            for label in ['이슈 요약','현재 상태 · 기사 기준','해설','시설 사건과 출하 차질은 별개']:
                self.assertIn(label,markup)
            self.assertFalse(next(x for x in app.expander if x.label=='원문 근거 · 추가 확인').proto.expanded)


if __name__=='__main__':
    unittest.main()
