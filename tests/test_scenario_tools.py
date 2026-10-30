from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from news.scenario_mock import mock_turn
from news.scenario_tools import tool_definition,build_request,decode_call,TOOL_NAME
from resilience_data import build_network
from simulation.resilience import calculate_supply_shock
from resilience_globe import build_network_globe,COLORS


class ScenarioToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network=build_network()

    def test_schema_whitelists_ids_and_is_strict_without_provider_calls(self):
        tool=tool_definition(self.network)
        self.assertTrue(tool['strict'])
        p=tool['parameters']
        self.assertFalse(p['additionalProperties'])
        self.assertEqual(set(p['properties']),set(p['required']))
        ids=p['properties']['target_ids']['items']['enum']
        self.assertIn('logistics:kaohsiung',ids)
        self.assertNotIn('logistics:taiwan-strait',ids)
        self.assertFalse(build_request(self.network,'가오슝항 30일 봉쇄')['parallel_tool_calls'])

    def test_ambiguous_blockade_followup_completes_without_guessing_supply_loss(self):
        context=mock_turn(self.network,None,'대만 가오슝 항구 30일 봉쇄돼서 난리야')
        self.assertFalse(context['result']['ready'])
        self.assertEqual(context['draft']['target_ids'],['logistics:kaohsiung'])
        self.assertIsNone(context['draft']['loss_pct'])
        ready=mock_turn(self.network,context,'완전 봉쇄로 가정해')
        parsed=ready['result']['engine_issue']
        self.assertEqual(parsed['targets'],['logistics:kaohsiung'])
        self.assertEqual(parsed['rate'],1.)
        self.assertEqual(parsed['days'],30)
        self.assertNotIn('생산 100%',parsed['text'])

    def test_partial_unknown_target_fresh_target_and_report_never_borrow_numbers(self):
        partial=mock_turn(self.network,None,'가오슝항 부분 봉쇄 30일')
        self.assertFalse(partial['result']['ready'])
        ready=mock_turn(self.network,partial,'통항 40% 감소')
        self.assertEqual(ready['result']['engine_issue']['rate'],.4)
        self.assertFalse(mock_turn(self.network,ready,'가오슝항 60일 봉쇄')['result']['ready'])
        unknown=mock_turn(self.network,ready,'대만 해협 30일 완전 봉쇄')
        self.assertFalse(unknown['result']['ready'])
        self.assertFalse(unknown['draft']['target_ids'])
        report=mock_turn(self.network,None,'가오슝항 30일 완전 봉쇄 보도 확인해줘')
        self.assertFalse(report['result']['ready'])
        negated=mock_turn(self.network,None,'가오슝항 30일 완전 봉쇄가 아니야')
        self.assertFalse(negated['result']['ready'])
        self.assertFalse(mock_turn(self.network,ready,'어느 공정에 영향이 가?')['result']['ready'])

    def test_malformed_function_call_ids_quotes_numbers_and_duplicate_fields_are_rejected(self):
        context=mock_turn(self.network,None,'가오슝항 30일 완전 봉쇄')
        source='가오슝항 30일 완전 봉쇄'
        args=context['draft']
        patches=[{'target_ids':['logistics:taiwan-strait']},{'duration_days':True},
                 {'duration_days':366},{'loss_pct':float('nan')},
                 {'quotes':{**args['quotes'],'target':'말라카 해협'}},
                 {'quotes':{**args['quotes'],'closure':'봉쇄'}},
                 {'target_ids':['jsr']}, {'loss_pct':40,'quotes':{**args['quotes'],'loss':'40%'}}]
        for patch_args in patches:
            with self.subTest(patch=patch_args),self.assertRaises(ValueError):
                decode_call({'type':'function_call','name':TOOL_NAME,'arguments':json.dumps({**deepcopy(args),**patch_args})},self.network,source)
        for call in [{'type':'function_call','name':'run_anything','arguments':'{}'},
                     {'type':'function_call','name':TOOL_NAME,'arguments':'{"intent":"simulate","intent":"report"}'}]:
            with self.assertRaises(ValueError): decode_call(call,self.network,source)

    def test_engine_and_globe_use_validated_port_event_without_mutating_graph(self):
        before=deepcopy(self.network)
        parsed=mock_turn(self.network,None,'가오슝항 30일 완전 봉쇄')['result']['engine_issue']
        baseline=calculate_supply_shock(self.network)
        result=calculate_supply_shock(self.network,[{k:parsed[k] for k in ('kind','targets','rate','days','text')}],30)
        self.assertEqual(result['nodes']['logistics:kaohsiung']['effective'],0)
        self.assertEqual(result['nodes']['logistics:malacca']['effective'],1)
        self.assertLess(result['overall'],baseline['overall'])
        fig=build_network_globe(self.network,result,view='이슈',focus='logistics:kaohsiung')
        marks=[trace for trace in fig.data if trace.customdata and 'logistics:kaohsiung' in trace.customdata]
        self.assertTrue(marks)
        self.assertTrue(any(t.marker.color==COLORS['stopped'] for t in marks))
        self.assertEqual(self.network,before)

    @patch.dict('os.environ',{'SUPPLY_ARTICLE_LLM_UI':'0'})
    def test_chat_tool_mode_applies_only_after_clarification_and_preserves_engine_on_invalid_input(self):
        from streamlit.testing.v1 import AppTest
        with patch('news.article_llm.urlopen',side_effect=AssertionError('No API')) as api:
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
            app.session_state['rr_workspace_mode'] = '상세 모드'
            app.run(timeout=30)
            app.selectbox(key='rr_chat_mode').set_value('모의 시뮬레이션').run(timeout=30)
            def ask(text):
                app.text_input(key='rr_chat_text').set_value(text)
                next(b for b in app.button if b.label=='질문 보내기 · 모의 대화').click().run(timeout=30)
                self.assertFalse(app.exception)
            ask('대만 가오슝 항구 30일 봉쇄돼서 난리야')
            self.assertEqual(app.session_state['rr_events'],[])
            ask('완전 봉쇄로 가정해')
            self.assertEqual(app.session_state['rr_events'],[])
            next(b for b in app.button if b.label=='확인한 조건 적용').click().run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['rr_events'][-1]['targets'],['logistics:kaohsiung'])
            self.assertEqual(app.session_state['rr_result']['nodes']['logistics:kaohsiung']['effective'],0)
            self.assertEqual(app.session_state['rr_focus'],'logistics:kaohsiung')
            before=deepcopy(app.session_state['rr_events'])
            ask('가오슝항 400일 완전 봉쇄')
            self.assertEqual(app.session_state['rr_events'],before)
            self.assertIn('error',app.session_state['rr_function_last'])
            self.assertEqual(api.call_count,0)

    def test_review_edits_replace_only_confirmed_event_and_mode_change_clears_pending(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        app.selectbox(key='rr_chat_mode').set_value('모의 시뮬레이션').run(timeout=30)
        app.text_input(key='rr_chat_text').set_value('가오슝항 30일 완전 봉쇄')
        next(b for b in app.button if b.label=='질문 보내기 · 모의 대화').click().run(timeout=30)
        app.number_input(key='rr_review_days').set_value(60)
        app.number_input(key='rr_review_loss').set_value(40.)
        next(b for b in app.button if b.label=='확인한 조건 적용').click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['rr_events'][-1]['days'],60)
        self.assertEqual(app.session_state['rr_events'][-1]['rate'],.4)
        self.assertTrue(app.session_state['rr_function_last']['edited'])
        next(b for b in app.button if b.label=='추출 조건 다시 수정').click().run(timeout=30)
        app.selectbox(key='rr_review_target').set_value('logistics:malacca')
        next(b for b in app.button if b.label=='확인한 조건 적용').click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state['rr_events']),1)
        self.assertEqual(app.session_state['rr_events'][0]['targets'],['logistics:malacca'])
        app.text_input(key='rr_chat_text').set_value('가오슝항 30일 완전 봉쇄')
        next(b for b in app.button if b.label=='질문 보내기 · 모의 대화').click().run(timeout=30)
        self.assertTrue(app.session_state['rr_function_pending'])
        app.selectbox(key='rr_chat_mode').set_value('기사 검토 · 모의 대화').run(timeout=30)
        self.assertNotIn('rr_function_pending',app.session_state)
        self.assertEqual(len(app.session_state['rr_events']),1)


if __name__=='__main__':
    unittest.main()
