import unittest
from copy import deepcopy
from resilience_data import build_network
from ui.research_map import map_matches
from ui.catalog_profile import enrich_catalog_profile
from ui.demo import presentation_result
from ui.demo_scenarios import selected_case
from ui.response_review import review_payload


class CatalogMainMapTests(unittest.TestCase):
    def test_new_locations_have_traceable_sources_without_changing_network(self):
        network=build_network();before=deepcopy(network)
        for name in ('Entegris','REC Silicon','Solvay'):
            data=map_matches(network,'',candidates=[dict(name=name,products=[])])
            self.assertTrue(any(m.get('candidate_name')==name for m in data['markers']))
        self.assertEqual(before,network)

    def test_company_cut_has_connected_candidates_and_never_reuses_blocked_company(self):
        network=build_network();before=deepcopy(network)
        case=selected_case(network,'기업','jsr','공급 중단')
        data=review_payload(network,presentation_result(network),case,True,'EUV')
        ids={m['id'] for m in data['markers']}
        alternatives=[r for r in data['routes'] if r['kind']=='alternative']
        self.assertTrue(alternatives)
        self.assertIn('fujifilm',{r['start'] for r in alternatives})
        self.assertNotIn('jsr',{r['start'] for r in alternatives})
        self.assertNotIn('dongjin',{r['start'] for r in alternatives})
        for route in data['routes']:
            self.assertIn(route['start'],ids);self.assertIn(route['end'],ids)
        self.assertEqual(network,before)

    def test_candidate_materials_stay_with_their_original_recipients(self):
        network=build_network()
        case=dict(target='jsr',connections=[
            dict(item='photoresist',material='PR A',supplier='jsr',recipient='tsmc'),
            dict(item='photoresist',material='PR B',supplier='jsr',recipient='samsung')])
        profile=enrich_catalog_profile(network,case,{},'ArF')
        self.assertTrue(profile['candidates'])
        self.assertEqual({(c['recipient'],c['material']) for c in profile['candidates']},
                         {('tsmc','PR A'),('samsung','PR B')})
