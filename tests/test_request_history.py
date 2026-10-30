import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from news.request_history import record_request
from news.external_research import _request


class RequestHistoryTests(unittest.TestCase):
    def test_session_capture_and_display(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_string('''
import io
from news.external_research import _request
from ui.api_credentials import render_request_history
_request({'model':'test','text':{'format':{'name':'factory_review'}}}, 'synthetic-key',
         lambda request,timeout: io.BytesIO(b'{"status":"completed"}'))
render_request_history()
''').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['ai_request_history'][0]['기능'], '기사 검토')
        self.assertEqual(len(app.dataframe), 1)

    def test_connection_comparison_and_no_content_leak(self):
        state = {}
        payload = {'model': 'gpt-4.1-mini', 'input': 'private article',
                   'text': {'format': {'name': 'product_comparison'}}}
        record_request(state, payload, 'secret-one', 'API 응답 완료')
        payload['text']['format']['name'] = 'factory_review'
        record_request(state, payload, 'secret-one', 'API 실패', ValueError('private response'))
        record_request(state, payload, 'secret-two', 'API 실패')
        rows = state['ai_request_history']
        self.assertEqual(rows[0]['연결 식별값'], rows[1]['연결 식별값'])
        self.assertNotEqual(rows[1]['연결 식별값'], rows[2]['연결 식별값'])
        self.assertEqual([r['기능'] for r in rows], ['기업·소재 비교', '기사 검토', '기사 검토'])
        for secret in ('secret-one', 'secret-two', 'private article', 'private response'):
            self.assertNotIn(secret, json.dumps(rows))

    def test_bounded_and_probe_distinct(self):
        state = {}
        for _ in range(35):
            record_request(state, {'instructions': 'Connectivity test. Respond briefly.'}, 'key', 'API 실패')
        self.assertEqual(len(state['ai_request_history']), 30)
        self.assertEqual(state['ai_request_history'][0]['기능'], '연결 진단')

    def test_real_request_outcomes_recorded_without_retry(self):
        calls = []
        def transport(request, timeout):
            calls.append(request)
            return io.BytesIO(b'{"status":"completed"}')
        with patch('news.request_history.session_record') as record:
            self.assertEqual(_request({'model': 'test'}, 'key', transport)['status'], 'completed')
            self.assertEqual(record.call_args.args[2], 'API 응답 완료')
        def failure(request, timeout):
            calls.append(request)
            raise HTTPError(request.full_url, 429, 'quota', {},
                            io.BytesIO(b'{"error":{"code":"credit_balance_exhausted"}}'))
        with patch('news.request_history.session_record') as record:
            with self.assertRaisesRegex(ValueError, 'credit_balance_exhausted'):
                _request({'model': 'test'}, 'key', failure)
            self.assertEqual(record.call_args.args[2], 'API 실패')
        self.assertEqual(len(calls), 2)
