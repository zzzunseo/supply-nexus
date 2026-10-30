import io
import json
import unittest
from copy import deepcopy
from urllib.error import HTTPError
from pathlib import Path
from unittest.mock import patch

from news.article_llm import extract_article, validate_suggestion
from news.article_review import article_draft, CLAIM_TYPES, SCOPES
from news.article_fields import FIELD_LABELS
from resilience_data import build_network


class ArticleLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()

    def setUp(self):
        self.body = 'JSR의 한 공장에서 화재가 발생했다. 출하 영향은 확인되지 않았다.'
        self.draft = article_draft(self.network, '가상 기사', self.body)
        self.proposal = dict(target='jsr', quote=self.body, claim_type=CLAIM_TYPES[2], scope=SCOPES[1],
                             fields={key: dict(value=None, quote=None) for key in FIELD_LABELS})

    def test_one_request_no_key_in_body_no_simulation(self):
        calls = []
        def transport(request, timeout):
            calls.append(request)
            payload = json.loads(request.data)
            self.assertFalse(payload['store'])
            self.assertNotIn('test-secret', request.data.decode())
            self.assertEqual(timeout, 40)
            return io.BytesIO(json.dumps({'status': 'completed', 'output': [
                {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(self.proposal)}]}]}).encode())
        self.assertEqual(extract_article(self.network, self.draft, 'test-secret', transport=transport), self.proposal)
        self.assertEqual(len(calls), 1)

    def test_hallucinated_target_quote_and_date_are_rejected(self):
        for patch in [dict(target='tsmc'), dict(quote='JSR은 공급을 완전히 중단했다.'),
                      dict(fields={**self.proposal['fields'], 'event_date': dict(value='2026-10-27', quote=self.body)})]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                validate_suggestion(self.network, self.draft, {**deepcopy(self.proposal), **patch})

    def test_http_failure_no_retry_no_secret_diagnostics(self):
        calls = []
        def transport(request, timeout):
            calls.append(1)
            raise HTTPError(request.full_url, 429, 'test-secret', {}, io.BytesIO(b'test-secret'))
        with self.assertRaises(ValueError) as raised:
            extract_article(self.network, self.draft, 'test-secret', transport=transport)
        self.assertNotIn('test-secret', str(raised.exception))
        self.assertIn('429', str(raised.exception))
        self.assertEqual(len(calls), 1)

    def test_incomplete_response_stops(self):
        def transport(request, timeout):
            return io.BytesIO(b'{"status":"incomplete"}')
        with self.assertRaises(ValueError):
            extract_article(self.network, self.draft, 'test-secret', transport=transport)

    def test_validated_values_are_normalized_before_form_prefill(self):
        self.proposal['fields']['supply_status'] = dict(value=' 공급 영향 미확인 명시 ', quote=' '+self.body+' ')
        checked = validate_suggestion(self.network, self.draft, self.proposal)
        self.assertEqual(checked['fields']['supply_status']['value'], '공급 영향 미확인 명시')
        self.assertEqual(checked['fields']['supply_status']['quote'], self.body)

    def test_malformed_fields_and_targets_fail_cleanly(self):
        for patch in [dict(target=[]), dict(fields={**self.proposal['fields'], 'facility': {'value': 3, 'quote': None}}),
                      dict(fields={**self.proposal['fields'], 'facility': {'value': None, 'quote': []}})]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                validate_suggestion(self.network, self.draft, {**self.proposal, **patch})

    def test_invalid_key_stops_before_network(self):
        def forbidden(*args, **kwargs):
            self.fail('Invalid key must not reach network')
        for key in ['키를여기에', 'test secret']:
            with self.subTest(key=key), self.assertRaises(ValueError):
                extract_article(self.network, self.draft, key, transport=forbidden)

    def test_refusal_invalid_json_and_oversize_do_not_retry(self):
        for raw in [b'not json', b'\xff', b'{}', b'[]', b'x'*2000001,
                    json.dumps({'status':'completed','output':[{'type':'message','content':[{'type':'refusal'}]}]}).encode()]:
            calls = []
            def transport(request, timeout):
                calls.append(1)
                return io.BytesIO(raw)
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                extract_article(self.network, self.draft, 'test-secret', transport=transport)
            self.assertEqual(len(calls),1)

    def test_twelve_case_expected_contracts_preserve_graph_and_unknown_quantities(self):
        # Synthetic expected responses test integration, NOT model accuracy.
        cases = json.loads((Path(__file__).parent/'fixtures/article_llm_cases.json').read_text(encoding='utf-8'))
        before = deepcopy(self.network)
        for case in cases:
            with self.subTest(case=case['id']):
                draft = article_draft(self.network, '검증용 가상 기사', case['body'])
                fields = {key: {'value': None, 'quote': None} for key in FIELD_LABELS}
                if case['supply_status']:
                    fields['supply_status'] = dict(value=case['supply_status'], quote=case['body'])
                proposal = dict(target=case['target'], quote=case['body'], claim_type=case['claim_type'],
                                scope=case['scope'], fields=fields)
                def transport(request, timeout):
                    return io.BytesIO(json.dumps({'status':'completed','output':[{'type':'message','content':[
                        {'type':'output_text','text':json.dumps(proposal)}]}]}).encode())
                result = extract_article(self.network, draft, 'test-secret', transport=transport)
                from news.article_review import review_article
                review = review_article(self.network, draft, result['target'], result['quote'],
                                        result['claim_type'],result['scope'],fields=result['fields'])
                self.assertIsNone(review['simulation_candidate'])
                self.assertIsNone(review['reported_rate'])
                self.assertIsNone(review['reported_duration_days'])
                self.assertEqual(review['fields']['event_date']['value'],None)
                self.assertEqual(self.network,before)


class ArticleLLMUITests(unittest.TestCase):
    @patch.dict('os.environ', {'SUPPLY_ARTICLE_LLM_UI': '1'})
    def test_apply_save_provenance_clear_key_and_keep_scenario_unchanged(self):
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'tests/fixtures/panel_components.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.session_state['rr_chat_mode'] = '기사 검토 · 모의 대화'
        app.run(timeout=30)
        app.button(key='rr_article_open').click().run(timeout=30)
        body = 'JSR의 공장에서 화재가 발생했다. 출하 영향은 미확인이다.'
        app.text_area(key='rr_article_body').set_value(body)
        next(b for b in app.button if b.label=='원문에서 대상 후보 찾기').click().run(timeout=30)
        before = deepcopy(app.session_state['rr_result'])
        key_field = app.text_input(key='rr_openai_key_input')
        self.assertEqual(key_field.proto.DESCRIPTOR.fields_by_name['type'].enum_type.values_by_number[key_field.proto.type].name,'PASSWORD')
        self.assertTrue(next(b for b in app.button if b.label=='LLM으로 검토 초안 추출').disabled)
        key_field.set_value('synthetic-key-not-a-real-credential').run()
        proposal = dict(target='jsr',quote=body,claim_type=CLAIM_TYPES[2],scope=SCOPES[1],
                        fields={key:dict(value=None,quote=None) for key in FIELD_LABELS})
        with patch('ui.article_llm.extract_article',return_value=proposal) as mocked:
            next(b for b in app.button if b.label=='LLM으로 검토 초안 추출').click().run(timeout=30)
            self.assertEqual(mocked.call_count,1)
        next(b for b in app.button if b.label=='제안을 아래 검토 양식에 채우기').click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['rr_article_target'],'jsr')
        next(b for b in app.button if b.label=='검토 결과 저장 · 경로 확인').click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['rr_result'],before)
        review = app.session_state['rr_article_review']
        self.assertEqual(review['extraction']['method'],'llm_assisted_human_review')
        self.assertNotIn('synthetic-key-not-a-real-credential',json.dumps(review))
        self.assertEqual(app.session_state['rr_openai_key'],'synthetic-key-not-a-real-credential')
        app.button(key='rr_article_open').click().run(timeout=30)
        self.assertEqual(app.text_input(key='rr_openai_key_input').value,'synthetic-key-not-a-real-credential')
        next(b for b in app.button if b.label=='세션에서 API 키 지우기').click().run(timeout=30)
        self.assertFalse(app.session_state['rr_openai_key'])
        self.assertFalse(app.text_input(key='rr_openai_key_input').value)
        next(b for b in app.button if b.label=='새 원문 입력 · 후보 다시 찾기').click().run(timeout=30)
        app.text_area(key='rr_article_body').set_value(body)
        next(b for b in app.button if b.label=='원문에서 대상 후보 찾기').click().run(timeout=30)
        self.assertNotIn('rr_llm_provenance',app.session_state)
        app.button(key='rr_article_details_button').click().run(timeout=30)
        self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()
