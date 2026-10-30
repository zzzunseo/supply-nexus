import unittest
from copy import deepcopy
from resilience_data import build_network
from ui.demo import demo_results
from ui.logistics_demo import demo_cases
from ui.response_review import review_profile,review_payload,review_rows_html


class ResponseReviewTests(unittest.TestCase):
    def test_candidates_are_not_dependent_on_assumed_backup_and_have_no_scores(self):
        network=build_network(); original=deepcopy(network)
        for case in demo_cases():
            applied=dict(case,days=1,percent=100)
            result=demo_results(network,applied,False,False)
            profile=review_profile(network,applied)
            if case.get('connections'):
                # Historical/custom connections use item-level product evidence,
                # not the curated two-vendor product-class comparison.
                self.assertTrue(profile['candidate_eligible'])
                self.assertIn('고객',profile['summary'])
                for candidate in profile['candidates']:
                    self.assertTrue(candidate['source'].startswith('https://'))
                    self.assertNotEqual(candidate['company_id'],case['connections'][0]['supplier'])
            elif case.get('kind')=='logistics':
                self.assertEqual(len(profile['rows']),5)
                self.assertEqual([row[1] for row in profile['rows']],['자료 확인','미확인','미확인','미확인','검토 필요'])
            else:
                self.assertEqual(len(profile['rows']),4)
                self.assertTrue(profile['candidate_eligible'])
                self.assertEqual(profile['rows'][0][1],'제품 자료 확인')
                self.assertIn('추가 검증',[row[1] for row in profile['rows']])
            data=review_payload(network,result,applied,True)
            self.assertTrue(data['review'])
            self.assertTrue(any(m['id']==profile['candidate_id'] for m in data['markers']))
            self.assertTrue(all(m['score'] is None for m in data['markers']))
            self.assertTrue(any(r['kind'] in ('alternative','detour') for r in data['routes']))
            off=review_payload(network,result,applied,False)
            self.assertFalse(any(r['kind'] in ('alternative','detour') for r in off['routes']))
            self.assertIsNone(data['alternative'])
            markup=review_rows_html(profile)
            self.assertNotIn('%',markup)
        self.assertEqual(network,original)

    def test_unknown_product_is_not_marked_as_verified_for_same_company(self):
        network=build_network();case=demo_cases()[1]
        network['nodes'][case['target']]['item_id']='unverified-grade'
        profile=review_profile(network,case)
        self.assertEqual(profile['rows'][0][1],'미확인')
        self.assertIsNone(profile['source'])
        self.assertFalse(profile['candidate_eligible'])

    def test_unlocated_candidate_keeps_review_but_has_no_fabricated_route(self):
        network=build_network();case=demo_cases()[1]
        result=demo_results(network,None)
        network['entities']['dongjin']['map_location']=None
        profile=review_profile(network,case)
        self.assertTrue(any(c['company_id']=='dongjin' for c in profile['candidates']))
        data=review_payload(network,result,case)
        self.assertFalse(any(m['id']=='dongjin' for m in data['markers']))
        self.assertFalse(any(r['start']=='dongjin' for r in data['routes']))
        self.assertTrue(any(r['kind']=='alternative' for r in data['routes']))

    def test_product_scope_gates_candidate_without_claiming_no_production(self):
        network=build_network();case=demo_cases()[1];result=demo_results(network,None)
        for product in ('ArF','KrF','i-line'):
            profile=review_profile(network,case,product)
            self.assertTrue(profile['candidate_eligible'])
            self.assertIn(product,profile['common_classes'])
            data=review_payload(network,result,case,True,product)
            self.assertTrue(any(r['kind']=='alternative' for r in data['routes']))
        euv=review_profile(network,case,'EUV')
        self.assertTrue(euv['candidate_eligible'])
        data=review_payload(network,result,case,True,'EUV')
        self.assertTrue(any(r['kind']=='alternative' and r['start']=='fujifilm' for r in data['routes']))
        self.assertFalse(any(m['id']=='dongjin' for m in data['markers']))

    def test_wafer_relationship_is_group_scoped_not_product_qualification(self):
        network=build_network();profile=review_profile(network,demo_cases()[0])
        self.assertEqual(profile['product_class'],'PW')
        self.assertTrue(any('GlobalWafers' in c.get('name','') for c in profile['candidates']))
        self.assertIn('고객별 규격·승인·여력 확인',profile['summary'])
        self.assertEqual(profile['rows'][2][1],'추가 검증')
        self.assertNotIn('승인 완료',review_rows_html(profile))
