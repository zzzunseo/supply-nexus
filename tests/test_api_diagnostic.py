import unittest
from unittest.mock import patch
from news.api_diagnostic import diagnose

class DiagnosticTests(unittest.TestCase):
    def test_same_credentials_small_requests(self):
        with patch('news.api_diagnostic._request',return_value={'status':'completed'}) as send:
            result=diagnose('synthetic-key','gpt-4.1-mini')
        self.assertEqual(send.call_count,2)
        for call in send.call_args_list:
            self.assertEqual(call.args[1],'synthetic-key')
            self.assertEqual(call.args[0]['max_output_tokens'],128)
            self.assertFalse(call.args[0]['store'])
        self.assertNotIn('text',send.call_args_list[0].args[0])
        self.assertIn('text',send.call_args_list[1].args[0])
        self.assertNotIn('synthetic-key',str(result))

    def test_first_failure_stops_spending(self):
        with patch('news.api_diagnostic._request',side_effect=ValueError('credit_balance_exhausted')) as send:
            result=diagnose('synthetic-key','gpt-4.1-mini')
        self.assertEqual(send.call_count,1)
        self.assertEqual(result['rows'][0]['결과'],'실패')

    def test_second_failure_keeps_first_success(self):
        with patch('news.api_diagnostic._request',side_effect=[{'status':'completed'},ValueError('429')]):
            result=diagnose('synthetic-key','gpt-4.1-mini')
        self.assertEqual([r['결과'] for r in result['rows']],['성공','실패'])
