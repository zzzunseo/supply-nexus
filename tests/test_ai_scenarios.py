"""Scenario routing and provider-boundary regressions; no live API calls."""
import io
import json
import unittest
from company_evidence import evidence_bundle
from news.external_research import (suggest_mode, question_intent, make_research_context,
    research_external, parse_search, ResearchError)

CASES=[
 ('희토류 관세가 반도체 공정에 미치는 영향은?', '공정 영향'),
 ('중국산 산화세륨 관세와 대체 공급사는?', '통합 검토'),
 ('SUMCO 공급이 중단되면 영향과 대체 기업은?', '대체 벤더'),
 ('불산 공급이 끊기면 식각 공정 영향과 대체 공급사는?', '통합 검토'),
 ('TSMC Fab 14가 멈추면 어떤 공정이 영향을 받아?', '공정 영향'),
 ('효성 용연 NF3 공장 화재를 가정하면 영향은?', '통합 검토'),
 ('NF3 공급이 끊기면 대체 공급사는?', '대체 벤더'),
 ('금과 구리 본딩 와이어를 비교해줘', '대체 벤더'),
 ('Soitec의 SOI 웨이퍼 공급 중단 영향은?', '통합 검토'),
 ('말라카 해협이 막히면 우회는?', '항로 우회'),
 ('관세와 수에즈 우회 운송 영향을 함께 봐줘', '통합 검토'),
 ('ArF 액침 Positive 레지스트 대체 공급사', '대체 벤더'),
]

def response(annotations=None,sources=None,text='모의 응답: 소재 용도와 전환 조건 검토'):
 return dict(status='completed',output=[
  dict(type='web_search_call',status='completed',action=dict(type='search',sources=sources)),
  dict(type='message',content=[dict(type='output_text',text=text,annotations=annotations)])])

class ScenarioTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.bundle=evidence_bundle()
 def test_twelve_question_routes_and_search_contract(self):
  for question,expected in CASES:
   with self.subTest(question=question):
    self.assertEqual(suggest_mode(question),expected)
    calls=[]
    def transport(request,timeout):
     calls.append(json.loads(request.data))
     return io.BytesIO(json.dumps(response([dict(type='url_citation',url='https://example.com/evidence',title='Synthetic evidence',start_index=0,end_index=5)])).encode())
    context=make_research_context(self.bundle,question,suggest_mode(question))
    result=research_external(context,'synthetic-key',transport=transport,simple=True)
    self.assertEqual(len(calls),1)
    self.assertEqual(result['search']['citation_count'],1)
    sent=json.loads(calls[0]['input'])
    self.assertEqual(sent['query'],question)
    self.assertTrue(sent['investigation_plan'])
    self.assertIn('web_search_call.action.sources',calls[0]['include'])
    if '관세' in question:self.assertTrue(any('정책:' in t for t in sent['investigation_plan']))
    if '공장' in question or 'Fab' in question:self.assertTrue(any('시설:' in t for t in sent['investigation_plan']))
 def test_policy_fact_vs_hypothetical(self):
  self.assertEqual(question_intent('현재 관세 시행 여부는?'),'실제 사건 확인')
  self.assertEqual(question_intent('관세가 시행되면 공정 영향은?'),'가정한 영향·대안 검토')
  self.assertEqual(question_intent('공장 화재가 난다면?'),'가정한 영향·대안 검토')
 def test_nullable_annotations_and_sources(self):
  with self.assertRaises(ResearchError) as error:parse_search(response())
  self.assertEqual(error.exception.search['diagnostics']['failure_reason'],'missing_sources')
 def test_rejected_urls_are_distinct_from_missing_metadata(self):
  with self.assertRaises(ResearchError) as error:
   parse_search(response([dict(type='url_citation',url='http://localhost/private')]))
  d=error.exception.search['diagnostics']
  self.assertEqual(d['received_citations'],1)
  self.assertEqual(d['rejected_urls'],1)
  self.assertEqual(d['failure_reason'],'urls_rejected')
 def test_missing_answer_preserves_sources_for_diagnosis(self):
  with self.assertRaises(ResearchError) as error:
   parse_search(response(sources=[dict(url='https://example.com/source')],text=''))
  self.assertEqual(error.exception.search['diagnostics']['failure_reason'],'missing_answer')
  self.assertEqual(len(error.exception.search['sources']),1)
 def test_plain_text_url_does_not_become_verified_source(self):
  with self.assertRaises(ResearchError):parse_search(response(text='근거 https://example.com/made-up'))
 def test_failed_search_not_accepted(self):
  r=response(sources=[dict(url='https://example.com/source')])
  r['output'][0]['status']='failed'
  with self.assertRaises(ValueError):parse_search(r)

class LiveEvaluationUITests(unittest.TestCase):
 def test_batch_keeps_four_results_and_stops_on_connection_error(self):
  from unittest.mock import patch
  from streamlit.testing.v1 import AppTest
  code="""
from ui.research_evaluation import render_evaluation
from company_evidence import evidence_bundle
render_evaluation(evidence_bundle(),'synthetic-key','synthetic-model')
"""
  result=dict(search=dict(text='모의 평가 결과',sources=[]))
  app=AppTest.from_string(code,default_timeout=30).run()
  with patch('ui.research_evaluation.research_external',return_value=result) as run:
   app.button(key='eval_basic_batch').click().run()
  self.assertFalse(app.exception)
  self.assertEqual(run.call_count,4)
  self.assertEqual(len(app.session_state.research_evaluations),4)
  self.assertTrue(all(c.kwargs['simple'] for c in run.call_args_list))
  app=AppTest.from_string(code,default_timeout=30).run()
  with patch('ui.research_evaluation.research_external',side_effect=ValueError('API 연결 실패')) as run:
   app.button(key='eval_basic_batch').click().run()
  self.assertFalse(app.exception)
  self.assertEqual(run.call_count,1)
  self.assertEqual(len(app.session_state.research_evaluations),1)
 def test_failure_keeps_search_diagnostics(self):
  from unittest.mock import patch
  from ui.research_evaluation import evaluate_case
  partial=dict(diagnostics=dict(failure_reason='missing_sources'),sources=[],text='초안')
  with patch('ui.research_evaluation.research_external',side_effect=ResearchError('출처 없음',partial)):
   result=evaluate_case(evidence_bundle(),'희토류 관세 영향','synthetic-key','synthetic-model')
  self.assertEqual(result['search'],partial)
  self.assertEqual(result['status'],'검색 근거 검토 필요')
