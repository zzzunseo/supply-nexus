from copy import deepcopy
from pathlib import Path
import unittest

from news.article_review import article_draft, candidate_ids, review_article, CLAIM_TYPES, SCOPES
from resilience_data import build_network


BODY = 'JSR은 한 포토레지스트 공장에서 화재가 발생했다고 밝혔다. 출하 영향과 복구 시점은 확인 중이다.'


class ArticleReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()

    def draft(self, body=BODY, url=''):
        return article_draft(self.network,'검증용 가상 기사',body,url)

    def test_mentions_are_candidates_not_an_automatic_company_or_supplier_decision(self):
        draft=self.draft()
        self.assertIn('jsr',candidate_ids(draft))
        material=next(m for m in draft['mentions'] if m['mention']=='포토레지스트')
        self.assertGreater(len(material['candidates']),1)
        review=review_article(self.network,draft,None)
        self.assertEqual(review['status'],'연결 보류')
        self.assertEqual(review['routes'],[])
        self.assertIsNone(review['simulation_candidate'])

    def test_factory_event_keeps_facility_scope_and_unknown_supply_quantities(self):
        review=review_article(self.network,self.draft(),'jsr',BODY,CLAIM_TYPES[2],SCOPES[1])
        self.assertEqual(review['scope'],'특정 시설·제품')
        self.assertEqual(review['claim_type'],'사건 발생 · 공급 영향 미확인')
        self.assertIsNone(review['reported_rate'])
        self.assertIsNone(review['reported_duration_days'])
        self.assertFalse(review['article']['source_verified'])
        self.assertTrue(all(r['impact_status']=='실제 고객 영향 미확인' for r in review['routes']))

    def test_nonexistent_quote_and_target_without_matching_mention_are_rejected(self):
        for quote in ('JSR이 전체 생산을 100% 중단했다.', '출하 영향과 복구 시점은 확인 중이다.'):
            with self.subTest(quote=quote),self.assertRaises(ValueError):
                review_article(self.network,self.draft(),'jsr',quote)
        with self.assertRaises(ValueError):
            review_article(self.network,self.draft(),'tsmc',BODY)

    def test_registered_supply_evidence_and_reference_paths_remain_distinct(self):
        rows=review_article(self.network,self.draft(),'jsr',BODY)['routes']
        tsmc=next(r for r in rows if r['recipient']=='TSMC')
        samsung=next(r for r in rows if r['recipient']=='Samsung Electronics')
        self.assertIn('현행 계약 미확인',tsmc['basis'])
        self.assertTrue(tsmc['source'].startswith('https://'))
        self.assertIn('참고 관계',samsung['basis'])
        self.assertFalse(samsung['scoring_included'])
        self.assertEqual(tsmc['supplier'],'JSR')

    def test_unknown_company_does_not_create_a_fabricated_path(self):
        draft=self.draft('등록하지않은회사에서 공급 차질이 발생했다.')
        self.assertEqual(candidate_ids(draft),[])
        self.assertEqual(review_article(self.network,draft,None)['routes'],[])

    def test_url_is_validated_without_fetching_and_article_remains_detached(self):
        for url in ('javascript:alert(1)','https://user:password@example.com'):
            with self.assertRaises(ValueError):self.draft(url=url)
        draft=self.draft(url='https://example.com/fictional')
        before=deepcopy(draft)
        review=review_article(self.network,draft,'jsr',BODY)
        review['article']['body']='changed'
        self.assertEqual(draft,before)

    def test_review_does_not_mutate_graph_or_turn_percentages_into_simulation_parameters(self):
        before=deepcopy(self.network)
        body=BODY+' 비교 대상 업체는 50%의 증가를 기록했다.'
        review=review_article(self.network,self.draft(body),'jsr',BODY)
        self.assertIsNone(review['simulation_candidate'])
        self.assertIsNone(review['reported_rate'])
        self.assertEqual(self.network,before)

    def test_logistics_review_finds_registered_material_routes_without_shutdown_inference(self):
        body='말라카 해협 통항 지연 가능성이 제기됐다.'
        review=review_article(self.network,self.draft(body),'logistics:malacca',body,CLAIM_TYPES[3],SCOPES[3])
        self.assertTrue(review['routes'])
        self.assertIsNone(review['simulation_candidate'])


class ArticleReviewUITests(unittest.TestCase):
    def test_article_to_review_to_sources_to_map_preserves_the_existing_scenario(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        app.text_input(key='rr_issue_text').set_value('일본 포토레지스트 공급 중단 30일')
        next(b for b in app.button if b.label=='이슈 적용 → 소재 계산').click().run(timeout=30)
        before=deepcopy(app.session_state['rr_result'])
        events=deepcopy(app.session_state['rr_events'])
        scopes=deepcopy(app.session_state['rr_material_scopes'])
        app.button(key='rr_article_open').click().run(timeout=30)
        app.text_input(key='rr_article_title').set_value('가상 기사 · 테스트')
        app.text_area(key='rr_article_body').set_value(BODY)
        next(b for b in app.button if b.label=='원문에서 대상 후보 찾기').click().run(timeout=30)
        app.selectbox(key='rr_article_target').select('jsr')
        app.text_area(key='rr_article_quote').set_value(BODY)
        app.selectbox(key='rr_article_type').select(CLAIM_TYPES[2])
        app.selectbox(key='rr_article_scope').select(SCOPES[1])
        next(b for b in app.button if b.label=='검토 결과 저장 · 경로 확인').click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['rr_result'],before)
        self.assertEqual(app.session_state['rr_events'],events)
        self.assertEqual(app.session_state['rr_material_scopes'],scopes)
        self.assertEqual(app.session_state['rr_article_review']['scope'],SCOPES[1])
        app.button(key='rr_article_map_button').click().run(timeout=30)
        self.assertTrue(app.session_state['rr_article_map_open'])
        self.assertIsNone(app.session_state['rr_focus'])
        self.assertEqual(app.session_state['rr_result'],before)
        app.button(key='rr_article_details_button').click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual([tab.label for tab in app.tabs],['원문·검토 내용','등록 경로·근거','미확인·추가 확인'])

    def test_details_with_repeated_source_urls_have_unique_link_controls(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        network=app.session_state['rr_network']
        body='Air Products는 산소와 수소 공급에 대해 설명했다.'
        draft=article_draft(network,'가상 다중 경로',body)
        review=review_article(network,draft,'airproducts',body)
        self.assertGreater(len(review['routes']),1)
        app.session_state['rr_article_review']=review
        app.run(timeout=30)
        app.button(key='rr_article_details_button').click().run(timeout=30)
        self.assertFalse(app.exception)


if __name__=='__main__':
    unittest.main()
