import unittest
from copy import deepcopy
from unittest.mock import patch
from news.external_research import question_intent,make_research_context,suggest_mode
from news.external_candidates import validate_candidates,fetch_public_page
from ui.research_map import map_matches,focus_candidate
from company_evidence import evidence_bundle
from resilience_data import build_network

class ExternalCandidateTests(unittest.TestCase):
    def setUp(self):
        self.context=make_research_context(evidence_bundle(),'NF3 순도 99.999% 이상 대체 공급사')
        self.search={'sources':[dict(id='S1',url='https://vendor.example.com/products',origin='web_search_citation',title='Product')]}
        self.page='Example Vendor NF3 purity 99.999 % minimum. <script type="application/ld+json">{"address":"123 Example Street, Example City","geo":{"latitude":35.123,"longitude":139.123}}</script>'
        self.proposal={'candidates':[dict(name='Example Vendor',product='NF3',reason='NF3 제품 검토',source_id='S1',product_quote='NF3 purity 99.999 % minimum.',
            fields=[dict(key='purity_pct',value='99.999',unit='%',operator='ge',quote='NF3 purity 99.999 % minimum.',source_id='S1')],
            location=dict(site='Example office',address='123 Example Street, Example City',kind='본사',source_id='S1'))]}
    def validate(self):return validate_candidates(self.context,self.search,self.proposal,fetch=lambda u:self.page)
    def test_intent(self):
        self.assertEqual(question_intent('SUMCO 공급 중단'),'가정한 영향·대안 검토')
        self.assertEqual(question_intent('SUMCO 실제로 중단했어?'),'실제 사건 확인')
        self.assertEqual(question_intent('NF3 대체 공급사'),'공급사·제품 비교')
        self.assertEqual(question_intent('SUMCO 중단','실제 사건 확인'),'실제 사건 확인')
    def test_source_bound_comparison_map_and_no_mutation(self):
        candidates=self.validate();self.assertEqual(candidates[0]['evaluations'][0]['status'],'meets_documented')
        network=build_network();before=deepcopy(network)
        data=map_matches(network,'NF3 대체 공급사',candidates=candidates)
        focused,marker=focus_candidate(data,'Example Vendor')
        self.assertEqual(marker['lat'],35.123);self.assertEqual(network,before)
        self.assertFalse(data['routes'])
    def test_missing_source_quote_and_consulted_only_rejected(self):
        self.proposal['candidates'][0]['product_quote']='NF3 invented product'
        self.assertFalse(self.validate())
        self.proposal['candidates'][0]['product_quote']='NF3 purity 99.999 % minimum.'
        self.search['sources'][0]['origin']='web_search_consulted'
        self.assertFalse(self.validate())
    def test_missing_field_unknown_and_ambiguous_location_hidden(self):
        self.proposal['candidates'][0]['fields'][0]['value']='100'
        self.page=self.page.replace('123 Example Street','456 Other Street')
        result=self.validate()[0]
        self.assertEqual(result['evaluations'][0]['status'],'insufficient')
        self.assertNotIn('external_location',result)
    def test_mismatch_preserved_not_promoted(self):
        self.context=make_research_context(evidence_bundle(),'NF3 순도 99.9999% 이상 대체 공급사')
        self.assertEqual(self.validate()[0]['evaluations'][0]['status'],'mismatch')
    def test_private_source_blocked(self):
        with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ValueError):fetch_public_page('https://vendor.example.com/product')



class ExternalCandidateUITests(unittest.TestCase):
    def test_external_selection(self):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        fixture=ExternalCandidateTests();fixture.setUp()
        candidate=fixture.validate()[0]
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=40).run()
        app.radio(key='demo_review_view').set_value('AI 분석').run()
        q='NF3 순도 99.999% 이상 대체 공급사'
        app.text_area(key='research_query').set_value(q).run()
        context=make_research_context(evidence_bundle(),q,suggest_mode(q),external_candidates=True)
        app.session_state['research_report']=dict(context_id=context['id'],answer_only=True,question=q,search=dict(text='외부 후보 NF3 검토',sources=[],blocks=[],citation_count=1),external_candidates=[candidate])
        app.run()
        self.assertFalse(app.exception)
        with patch('ui.research_map.render_research_map') as render:
            app.selectbox(key='research_candidate_source').select('Example Vendor').run()
            self.assertEqual(render.call_args.kwargs['selected_candidate'],'Example Vendor')
        self.assertFalse(app.exception)
        self.assertTrue(any('외부 검색 후보' in x.value for x in app.caption))
