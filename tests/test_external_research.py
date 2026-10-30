from copy import deepcopy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from company_evidence import evidence_bundle
from news.external_research import (make_research_context,parse_search,validate_report,research_external,
    ResearchError,safe_url,report_schema,format_research,formatter_input)


def search_response(cited=True,tool=True):
    blocks=[dict(type='output_text',text='신규 공급사 Example Vendor의 제품 자료를 조사했습니다.',annotations=[
        dict(type='url_citation',url='https://vendor.example.com/products',title='제품 자료',start_index=0,end_index=4)] if cited else [])]
    return dict(status='completed',output=([dict(type='web_search_call',status='completed',action=dict(type='search',sources=[]))] if tool else [])+
        [dict(type='message',content=blocks)])


def proposal():
    return dict(summary='신규 기업도 검색 근거에 포함한 검토 초안입니다.',source_statements=[],impact_review=[],
        vendor_options=[dict(entity='Example Vendor',statement='등록 목록 밖의 제품 후보이며 고객 승인과 공급 여력을 확인해야 합니다.',basis='candidate',source_ids=['S1'])],
        route_options=[],unknowns=['실제 고객 인증·납기 미확인'])


class ExternalResearchTests(unittest.TestCase):
    def setUp(self):
        self.bundle=evidence_bundle()
        self.context=make_research_context(self.bundle,'등록망 밖 공급사도 찾아서 근거와 함께 비교해 주세요.')

    def test_simple_answer_one_request_and_short_question(self):
        context=make_research_context(self.bundle,'NF3 대안?')
        calls=[]
        def transport(request,timeout):
            calls.append(json.loads(request.data))
            return io.BytesIO(json.dumps(search_response()).encode())
        result=research_external(context,'synthetic-key',transport=transport,simple=True)
        self.assertTrue(result['answer_only'])
        self.assertEqual(len(calls),1)
        self.assertEqual(result['provenance']['api_requests'],1)
        with self.assertRaises(ResearchError):
            research_external(context,'synthetic-key',simple=True,transport=lambda *a,**kw:io.BytesIO(json.dumps(search_response(False)).encode()))

    def test_company_library_expands_customers_without_inserting_graph_edges(self):
        names={p['name'] for p in self.bundle['profiles']}
        self.assertTrue({'Kioxia','Sony Semiconductor Solutions','Maersk','Hapag-Lloyd'}<=names)
        sumco={r['customer'] for r in self.bundle['relationships'] if r['supplier']=='SUMCO'}
        self.assertTrue({'TSMC','Samsung Electronics','Kioxia','Sony Semiconductor Solutions'}<=sumco)
        self.assertTrue(all(r['status']=='dated_announcement' for r in self.bundle['routes']))
        for r in self.bundle['relationships']+self.bundle['routes']:
            self.assertTrue(r['limit'])
            self.assertTrue(all(s in self.bundle['sources'] for s in r['source_ids']))

    def test_external_candidate_allowed_but_native_search_and_citations_required(self):
        search=parse_search(search_response())
        result=validate_report(self.context,search,proposal())
        self.assertEqual(result['vendor_options'][0]['entity'],'Example Vendor')
        self.assertEqual(result['vendor_options'][0]['origin'],'외부 검색 포함')
        for cited,tool in [(False,True),(True,False)]:
            with self.assertRaises(ValueError):parse_search(search_response(cited,tool))

    def test_source_invention_and_claim_promotion_rejected(self):
        search=parse_search(search_response())
        for bad in ('source','basis','link'):
            report=proposal()
            if bad=='source':report['vendor_options'][0]['source_ids']=['S999']
            elif bad=='basis':report['vendor_options'][0]['basis']='source_statement'
            else:report['vendor_options'][0]['statement']='https://fabricated.example.com'
            with self.subTest(bad=bad),self.assertRaises(ValueError):validate_report(self.context,search,report)

    def test_process_impact_scope_and_mocked_report(self):
        context=make_research_context(self.bundle,'ポ토레지스트 공장 중단을 가정하고 영향 공정을 검토해 주세요.','공정 영향')
        answer=proposal();answer['vendor_options']=[]
        answer['impact_review']=[dict(entity='포토',statement='포토레지스트의 노광 용도를 통한 공정 연결 검토이며 중단 품목과 공급 영향은 미확인입니다.',basis='conditional',source_ids=['S1'])]
        result=validate_report(context,parse_search(search_response()),answer)
        self.assertEqual(result['mode'],'공정 영향')
        self.assertEqual(result['impact_review'][0]['entity'],'포토')
        for bad in ('vendor','process'):
            changed=deepcopy(answer)
            if bad=='vendor':changed['vendor_options']=proposal()['vendor_options']
            else:changed['impact_review'][0]['entity']='모든 기업 생산중단'
            with self.subTest(bad=bad),self.assertRaises(ValueError):validate_report(context,parse_search(search_response()),changed)
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        app.radio(key='demo_review_view').set_value('AI 분석').run()
        app.radio(key='ai_workspace_task').set_value('사건·공정 영향 조사').run()
        app.selectbox(key='research_example').select('공장 중단 → 공정').run()
        app.button(key='research_load').click().run()
        self.assertEqual(app.session_state.research_mode,'공정 영향')
        app.text_input(key='shared_api_input_research').set_value('synthetic-key').run()
        with patch('ui.external_research.research_external',return_value=dict(result,provenance=dict(model='synthetic-model'))):
            app.button(key='research_run').click().run()
        self.assertFalse(app.exception)
        self.assertIn('영향 검토 공정',[t.label for t in app.tabs])
        self.assertNotIn('대체 벤더',[t.label for t in app.tabs])

    def test_two_calls_search_required_then_schema_and_no_secret_in_input(self):
        calls=[]
        def transport(request,timeout):
            body=json.loads(request.data);calls.append(body)
            self.assertNotIn('synthetic-secret',request.data.decode());self.assertFalse(body['store'])
            if len(calls)==1:
                self.assertEqual(body['tool_choice'],'required')
                self.assertEqual(body['tools'][0]['type'],'web_search')
                self.assertEqual(body['max_tool_calls'],3)
                answer=search_response()
            else:
                self.assertTrue(body['text']['format']['strict'])
                answer=dict(status='completed',output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(proposal()))])])
            return io.BytesIO(json.dumps(answer).encode())
        result=research_external(self.context,'synthetic-secret',transport=transport)
        self.assertEqual(len(calls),2)
        self.assertEqual(result['provenance']['api_requests'],2)
        self.assertNotIn('synthetic-secret',json.dumps(result))

    def test_no_citations_stops_before_second_request(self):
        calls=[]
        def transport(request,timeout):
            calls.append(1);return io.BytesIO(json.dumps(search_response(False)).encode())
        with self.assertRaises(ValueError):research_external(self.context,'synthetic-key',transport=transport)
        self.assertEqual(len(calls),1)

    def test_429_codes_sanitized_and_single_format_retry(self):
        search=parse_search(search_response())
        for code,kind,label in [('rate_limit_exceeded','tokens','속도 한도'),('credit_balance_exhausted','insufficient_quota','credit_balance_exhausted'),('unknown','unknown','원인을 확정')]:
            calls=[]
            def fail(request,timeout):
                calls.append(1)
                raise HTTPError(request.full_url,429,'synthetic-secret',{'retry-after':'20'},io.BytesIO(json.dumps(dict(error=dict(code=code,type=kind,message='synthetic-secret'))).encode()))
            with self.subTest(code=code),self.assertRaises(ResearchError) as raised:
                format_research(self.context,search,'synthetic-secret',transport=fail,reuse=True)
            self.assertIn(label,str(raised.exception))
            self.assertNotIn('synthetic-secret',str(raised.exception))
            self.assertEqual(len(calls),1)
        calls=[]
        def complete(request,timeout):
            body=json.loads(request.data);calls.append(body)
            self.assertNotIn('tools',body)
            return io.BytesIO(json.dumps(dict(status='completed',output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(proposal()))])])).encode())
        report=format_research(self.context,search,'synthetic-secret',transport=complete,reuse=True)
        self.assertEqual(len(calls),1)
        self.assertTrue(report['provenance']['search_reused'])
        self.assertEqual(report['provenance']['api_requests'],1)
        process=make_research_context(self.bundle,'NF3 공급중단에 따른 공정 영향을 검토해 주세요.','공정 영향')
        payload=formatter_input(process,search)
        self.assertLess(len(json.dumps(payload)),len(json.dumps(self.bundle))//3)

    def test_ui_partial_can_retry_only_formatting(self):
        from streamlit.testing.v1 import AppTest
        with patch.dict('os.environ',{'SUPPLY_AI_API_KEY':'synthetic-test-only'}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
            app.radio(key='demo_review_view').set_value('AI 분석').run()
            app.selectbox(key='research_mode').select('통합 검토').run()
            search=parse_search(search_response())
            with patch('ui.external_research.research_external',side_effect=ResearchError('HTTP 429',search)):
                app.button(key='research_run').click().run()
            def retry(context,search,key,model,reuse):
                return dict(validate_report(context,search,proposal()),provenance=dict(model='synthetic-model',search_reused=True,api_requests=1))
            with patch('ui.external_research.format_research',side_effect=retry) as formatter,patch('ui.external_research.research_external') as researcher:
                app.button(key='research_format_retry').click().run()
                self.assertEqual(formatter.call_count,1)
                self.assertEqual(researcher.call_count,0)
            self.assertFalse(app.exception)
            self.assertNotIn('research_partial',app.session_state)

    def test_consulted_tool_urls_are_kept_with_weaker_provenance(self):
        response=search_response(False)
        response['output'][0]['action']['sources']=[dict(type='url',url='https://vendor.example.com/products'),dict(url='http://localhost/')]
        search=parse_search(response)
        self.assertEqual(search['citation_count'],0)
        self.assertEqual(len(search['sources']),1)
        self.assertEqual(search['sources'][0]['origin'],'web_search_consulted')
        self.assertEqual(validate_report(self.context,search,proposal())['sources']['S1']['origin'],'web_search_consulted')
        # Inline citations take precedence for a URL present in both lists.
        response['output'][1]=search_response()['output'][1]
        self.assertEqual(parse_search(response)['sources'][0]['origin'],'web_search_citation')

    def test_missing_all_sources_preserves_partial_search_in_ui(self):
        with self.assertRaises(ResearchError) as raised:parse_search(search_response(False))
        self.assertFalse(raised.exception.search['sources'])
        self.assertTrue(raised.exception.search['text'])
        from streamlit.testing.v1 import AppTest
        with patch.dict('os.environ',{'SUPPLY_AI_API_KEY':'synthetic-test-only'}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
            app.radio(key='demo_review_view').set_value('AI 분석').run()
            with patch('ui.external_research.research_external',side_effect=raised.exception):
                app.button(key='research_run').click().run()
            self.assertFalse(app.exception)
            self.assertNotIn('research_report',app.session_state)
            self.assertIn('research_partial',app.session_state)
            self.assertTrue(any('반복 실행 전에 검색 진단' in i.value for i in app.info))

    def test_missing_sources_shows_registered_sumco_evidence_separately(self):
        from streamlit.testing.v1 import AppTest
        with self.assertRaises(ResearchError) as error:parse_search(search_response(False))
        self.assertEqual(error.exception.search['diagnostics']['accepted_sources'],0)
        with patch.dict('os.environ',{'SUPPLY_AI_API_KEY':'synthetic-test-only'}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
            app.radio(key='demo_review_view').set_value('AI 분석').run()
            app.text_area(key='research_query').set_value('SUMCO 공급 차질을 가정하고 관련 기업을 검토해 주세요.').run()
            with patch('ui.external_research.research_external',side_effect=error.exception):
                app.button(key='research_run').click().run()
            self.assertFalse(app.exception)
            self.assertNotIn('research_report',app.session_state)
            self.assertTrue(any('현재 질문에 연결된 등록 근거' in e.label for e in app.expander))
            self.assertTrue(any('Siltronic' in table.value.to_string() for table in app.dataframe))
            self.assertTrue(any('Kioxia' in table.value.to_string() for table in app.dataframe))

    def test_formatter_failure_keeps_search_draft_without_faking_complete_report(self):
        calls=[]
        def transport(request,timeout):
            calls.append(1)
            answer=search_response() if len(calls)==1 else dict(status='incomplete')
            return io.BytesIO(json.dumps(answer).encode())
        with self.assertRaises(ResearchError) as raised:research_external(self.context,'synthetic-key',transport=transport)
        self.assertEqual(len(calls),2);self.assertTrue(raised.exception.search['sources'])

    def test_bad_urls_and_stale_context(self):
        for url in ['http://example.com','https://127.0.0.1/','https://localhost/','https://user:pass@example.com','javascript:alert(1)']:
            with self.subTest(url=url),self.assertRaises(ValueError):safe_url(url)
        changed=make_research_context(self.bundle,self.context['query'],origin='Busan',destination='Rotterdam')
        self.assertNotEqual(changed['id'],self.context['id'])

    def test_ui_library_request_and_stale_input(self):
        from streamlit.testing.v1 import AppTest
        with patch.dict('os.environ',{'SUPPLY_AI_API_KEY':'synthetic-test-only'}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
            app.radio(key='demo_review_view').set_value('AI 분석').run()
            app.radio(key='ai_workspace_task').set_value('사건·공정 영향 조사').run()
            app.selectbox(key='research_mode').select('통합 검토').run()
            self.assertFalse(app.exception)
            app.selectbox(key='research_library_company').select('SUMCO').run()
            app.checkbox(key='research_library_graph').check().run()
            self.assertFalse(app.exception)
            def fake(context,key,model,on_progress=None,simple=False):
                result=validate_report(context,parse_search(search_response()),proposal())
                result['provenance']['model']='synthetic-model';return result
            with patch('ui.external_research.research_external',side_effect=fake) as mocked:
                app.button(key='research_run').click().run()
                self.assertEqual(mocked.call_count,1)
            self.assertFalse(app.exception)
            self.assertIn('research_report',app.session_state)
            app.text_input(key='research_origin').set_value('Busan').run()
            self.assertFalse(app.exception)
            self.assertNotIn('research_report',app.session_state)

    def test_ui_no_key_disabled_and_partial_draft_labeled(self):
        from streamlit.testing.v1 import AppTest
        with patch.dict('os.environ',{'SUPPLY_AI_API_KEY':'','OPENAI_API_KEY':''}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
            app.radio(key='demo_review_view').set_value('AI 분석').run()
            app.radio(key='ai_workspace_task').set_value('사건·공정 영향 조사').run()
            self.assertTrue(app.button(key='research_run').disabled)
            app.text_input(key='shared_api_input_research').set_value('synthetic-secret').run()
            self.assertFalse(app.button(key='research_run').disabled)
            with patch('ui.external_research.research_external',side_effect=ResearchError('보고서 정리 실패',parse_search(search_response()))):
                app.button(key='research_run').click().run()
            self.assertFalse(app.exception)
            self.assertNotIn('research_report',app.session_state)
            self.assertIn('research_partial',app.session_state)
            self.assertTrue(any('상세 카드 정리는 완료되지 않았습니다' in w.value for w in app.warning))
            app.button(key='clear_shared_research').click().run()
            self.assertTrue(app.button(key='research_run').disabled)
            self.assertFalse(app.session_state.ai_api_secret)



