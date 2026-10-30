import unittest
from company_evidence import evidence_bundle
from news.vendor_candidates import registered_candidates
from ui.research_map import map_matches
from resilience_data import build_network


class CandidateTests(unittest.TestCase):
    def test_question_diameter_and_wafer_type_exclude_wrong_products(self):
        candidates=registered_candidates(evidence_bundle(),'SUMCO 300mm PW 대체 기업')
        names={c['name'] for c in candidates}
        self.assertIn('SK siltron',names)
        self.assertNotIn('Silicon Works Tech (Wafer Works 게시)',names)
        for c in candidates:
            self.assertTrue(all('EPI' not in p for p in c['products']))
            for evaluation in c['evaluations']:
                if evaluation['product'] in c['products']:
                    self.assertNotEqual(evaluation['status'],'mismatch')
                    self.assertTrue(evaluation['evidence'])

    def test_question_purity_and_water_constraints(self):
        candidates=registered_candidates(evidence_bundle(),'NF3 순도 99.999% 이상 대체 공급사')
        self.assertNotIn('Linde',{c['name'] for c in candidates})
        audit=registered_candidates(evidence_bundle(),'NF3 수분 1 ppmv 이하 대체 공급사',include_rejected=True)
        linde=next(c for c in audit if c['name']=='Linde')
        self.assertTrue(linde['excluded'])
        self.assertTrue(any(check['state']=='mismatch' for e in linde['evaluations'] for check in e['checks']))

    def test_missing_diameter_stays_unknown(self):
        candidates=registered_candidates(evidence_bundle(),'SUMCO 300mm PW 대체 기업')
        shin=next(c for c in candidates if c['name']=='Shin-Etsu 그룹 · SEH')
        self.assertTrue(any(check['state']=='unknown' for e in shin['evaluations'] for check in e['checks']))

    def test_sumco_candidates_and_map(self):
        bundle=evidence_bundle()
        candidates=registered_candidates(bundle,'SUMCO 공급 중단')
        names={c['name'] for c in candidates}
        self.assertTrue({'Shin-Etsu 그룹 · SEH','Siltronic','SK siltron'}<=names)
        self.assertNotIn('SUMCO',names)
        self.assertTrue(all(c['source_ids'] for c in candidates))
        data=map_matches(build_network(),'SUMCO 공급 중단',candidates=candidates)
        self.assertEqual(next(m for m in data['markers'] if m['id']=='shinetsu')['role'],'alternative')
        self.assertEqual(data['routes'],[])

    def test_nf3_does_not_include_cf4_only_vendor(self):
        names={c['name'] for c in registered_candidates(evidence_bundle(),'NF3 대체 공급사')}
        self.assertIn('Linde',names)
        self.assertNotIn('Messer',names)
        self.assertEqual(registered_candidates(evidence_bundle(),'수에즈 우회'),[])
