from copy import deepcopy
from pathlib import Path
import unittest
from news.article_fields import validate_fields, FIELD_LABELS
from news.article_review import article_draft, review_article, CLAIM_TYPES, SCOPES
from resilience_data import build_network

BODY='2026년 10월 27일 보도. JSR A공장에서 2026-10-26 화재가 발생했다. 포토레지스트 ArF 등급 출하 영향은 확인 중이다.'

class ArticleFieldsTests(unittest.TestCase):
    def test_missing_fields_remain_unknown(self):
        fields=validate_fields(BODY)
        self.assertEqual(set(fields),set(FIELD_LABELS))
        self.assertTrue(all(c==dict(value=None,quote=None,basis='unknown') for c in fields.values()))

    def test_dates_and_facility_and_grade_preserve_separate_exact_evidence(self):
        supplied={
            'published_date':{'value':'2026-10-27','quote':'2026년 10월 27일 보도.'},
            'event_date':{'value':'2026-10-26','quote':'JSR A공장에서 2026-10-26 화재가 발생했다.'},
            'facility':{'value':'A공장','quote':'JSR A공장에서 2026-10-26 화재가 발생했다.'},
            'product':{'value':'포토레지스트 ArF 등급','quote':'포토레지스트 ArF 등급 출하 영향은 확인 중이다.'},
            'supply_status':{'value':'공급 영향 미확인 명시','quote':'포토레지스트 ArF 등급 출하 영향은 확인 중이다.'}}
        before=deepcopy(supplied)
        result=validate_fields(BODY,supplied)
        self.assertEqual(result['event_date']['value'],'2026-10-26')
        self.assertTrue(all(c['basis']=='user_cited' for c in result.values()))
        self.assertEqual(supplied,before)
        self.assertEqual(result['product']['quote'],supplied['product']['quote'])

    def test_invalid_date_relative_date_or_mismatched_date_are_rejected(self):
        for value,quote,body in [('2026-02-30',BODY,BODY),('2026-10-25',BODY,BODY),('2026-10-26','어제 화재 발생','어제 화재 발생'),('2026-10-27','2026-10-271 보도','2026-10-271 보도')]:
            with self.subTest(value=value,quote=quote),self.assertRaises(ValueError):
                validate_fields(body,{'event_date':{'value':value,'quote':quote}})

    def test_missing_or_invented_quote_and_unmentioned_facility_are_rejected(self):
        for value,quote in [('A공장',''),('B공장',BODY),('A공장','JSR A공장은 공급을 중단했다.')]:
            with self.subTest(value=value,quote=quote),self.assertRaises(ValueError):
                validate_fields(BODY,{'facility':{'value':value,'quote':quote}})

    def test_review_records_fields_without_generating_supply_parameters(self):
        network=build_network()
        draft=article_draft(network,'가상 구조화 검증',BODY)
        result=review_article(network,draft,'jsr',BODY,CLAIM_TYPES[2],SCOPES[1],fields={'facility':{'value':'A공장','quote':BODY}})
        self.assertEqual(result['fields']['facility']['value'],'A공장')
        self.assertNotIn('시설·사업장 미확인',result['unknowns'])
        self.assertIn('기사 발행일 미확인',result['unknowns'])
        self.assertIsNone(result['simulation_candidate'])
        self.assertIsNone(result['reported_rate'])

    def test_explicit_unknown_supply_does_not_accept_a_hidden_assertion(self):
        with self.assertRaises(ValueError):
            validate_fields(BODY,{'supply_status':{'value':'미확인','quote':BODY}})

class ArticleFieldsUITests(unittest.TestCase):
    def test_optional_structured_fields_save_with_provenance_and_preserve_scenario(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'tests/fixtures/panel_components.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.session_state['rr_chat_mode'] = '기사 검토 · 모의 대화'
        app.run(timeout=30)
        before=deepcopy(app.session_state['rr_result'])
        app.button(key='rr_article_open').click().run(timeout=30)
        app.text_area(key='rr_article_body').set_value(BODY)
        next(b for b in app.button if b.label=='원문에서 대상 후보 찾기').click().run(timeout=30)
        app.selectbox(key='rr_article_target').select('jsr')
        app.text_area(key='rr_article_quote').set_value(BODY)
        app.text_input(key='rr_fact_published_date').set_value('2026-10-27')
        app.text_input(key='rr_fact_published_date_quote').set_value('2026년 10월 27일 보도.')
        app.text_input(key='rr_fact_facility').set_value('A공장')
        app.text_input(key='rr_fact_facility_quote').set_value('JSR A공장에서 2026-10-26 화재가 발생했다.')
        next(b for b in app.button if b.label=='검토 결과 저장 · 경로 확인').click().run(timeout=30)
        self.assertFalse(app.exception)
        review=app.session_state['rr_article_review']
        self.assertEqual(review['fields']['published_date']['value'],'2026-10-27')
        self.assertEqual(review['fields']['facility']['value'],'A공장')
        self.assertIsNone(review['fields']['event_date']['value'])
        self.assertEqual(app.session_state['rr_result'],before)
        app.button(key='rr_article_details_button').click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any('시설·사업장: A공장' in m.value for m in app.markdown))
