import io
import json
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from news.scenario_llm import llm_turn
from news.scenario_mock import mock_turn
from resilience_data import build_network


class ScenarioLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network=build_network()

    def transport(self, call, captured=None, **overrides):
        def send(request, timeout):
            if captured is not None:
                captured.append((json.loads(request.data),timeout,request.full_url))
            return io.BytesIO(json.dumps({'status':'completed','output':[call],**overrides}).encode())
        return send

    def test_real_adapter_request_and_validated_engine_result(self):
        source='가오슝항 30일 완전 봉쇄'
        call=mock_turn(self.network,None,source)['call']
        captured=[]
        result=llm_turn(self.network,None,source,'local-test-token',transport=self.transport(call,captured))
        self.assertTrue(result['result']['ready'])
        self.assertEqual(result['mode'],'openai_function_call')
        payload,timeout,url=captured[0]
        self.assertFalse(payload['store'])
        self.assertFalse(payload['parallel_tool_calls'])
        self.assertEqual(payload['model'],'gpt-4.1-mini')
        self.assertEqual(url,'https://api.openai.com/v1/responses')
        self.assertEqual(timeout,40)
        self.assertNotIn('local-test-token',json.dumps(result))

    def test_followup_context_and_completed_event_not_replayed(self):
        first=mock_turn(self.network,None,'가오슝항 30일 봉쇄')
        full=mock_turn(self.network,first,'완전 봉쇄로 가정해')
        ready=llm_turn(self.network,first,'완전 봉쇄로 가정해','test',transport=self.transport(full['call']))
        self.assertTrue(ready['result']['ready'])
        captured=[]
        clarification=mock_turn(self.network,None,'어느 공정에 영향이 가?')
        result=llm_turn(self.network,ready,'어느 공정에 영향이 가?','test',transport=self.transport(clarification['call'],captured))
        self.assertFalse(result['result']['ready'])
        self.assertIsNone(json.loads(captured[0][0]['input'])['request']['previous'])

    def test_rejects_bad_provider_outputs_and_fabricated_ids(self):
        source='가오슝항 30일 완전 봉쇄'
        call=mock_turn(self.network,None,source)['call']
        invalid=deepcopy(call)
        args=json.loads(invalid['arguments']); args['target_ids']=['made-up']
        invalid['arguments']=json.dumps(args)
        for output in ([],[call,call],[invalid],[{'type':'message','content':[{'type':'refusal'}]}]):
            with self.subTest(output=output),self.assertRaises(ValueError):
                llm_turn(self.network,None,source,'test',transport=self.transport(call,output=output))
        with self.assertRaises(ValueError):
            llm_turn(self.network,None,source,'test',transport=self.transport(call,status='incomplete'))

    def test_errors_are_sanitized_and_no_retry(self):
        for error in (HTTPError('url',401,'sensitive',{},None),HTTPError('url',429,'sensitive',{},None),URLError('sensitive'),TimeoutError('sensitive')):
            with patch('news.scenario_llm.urlopen',side_effect=error) as send:
                with self.assertRaises(ValueError) as caught:
                    llm_turn(self.network,None,'가오슝항','test')
                self.assertNotIn('sensitive',str(caught.exception))
                self.assertEqual(send.call_count,1)
        with patch('news.scenario_llm.urlopen') as send:
            with self.assertRaises(ValueError): llm_turn(self.network,None,'가오슝항','')
            send.assert_not_called()

    def test_ui_real_mode_success_and_failure_preserves_scenario(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'tests/fixtures/panel_components.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        app.selectbox(key='rr_chat_mode').set_value('실제 LLM 시뮬레이션').run(timeout=30)
        button=next(b for b in app.button if b.label=='질문 보내기 · 실제 LLM')
        self.assertTrue(button.disabled)
        app.text_input(key='rr_chat_api_key').set_value('local-test-token').run(timeout=30)
        source='가오슝항 30일 완전 봉쇄'
        response=mock_turn(self.network,None,source)
        response.update(mode='openai_function_call',model='gpt-4.1-mini')
        with patch('ui.article_chat.llm_turn',return_value=response) as send:
            app.text_input(key='rr_chat_text').set_value(source)
            next(b for b in app.button if b.label=='질문 보내기 · 실제 LLM').click().run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(send.call_count,1)
            self.assertEqual(app.session_state['rr_events'],[])
            next(b for b in app.button if b.label=='확인한 조건 적용').click().run(timeout=30)
            self.assertEqual(send.call_count,1)
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['rr_result']['nodes']['logistics:kaohsiung']['effective'],0)
        events=deepcopy(app.session_state['rr_events'])
        with patch('ui.article_chat.llm_turn',side_effect=ValueError('연결 실패')):
            app.text_input(key='rr_chat_text').set_value('부분 봉쇄')
            next(b for b in app.button if b.label=='질문 보내기 · 실제 LLM').click().run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['rr_events'],events)
        next(b for b in app.button if b.label=='API 키 지우기').click().run(timeout=30)
        self.assertFalse(app.session_state['rr_openai_key'])


if __name__=='__main__': unittest.main()
