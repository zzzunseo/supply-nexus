import unittest
from copy import deepcopy
from resilience_data import build_network
from ui.logistics_demo import demo_cases
from ui.simulation_candidates import catalog_candidates

class CatalogCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network=build_network()
        cls.cases=demo_cases()

    def test_wafer_expands_without_epi_or_disrupted_supplier(self):
        rows=catalog_candidates(self.network,self.cases[0])
        self.assertGreaterEqual(len({e['record']['supplier'] for e in rows}),4)
        for e in rows:
            self.assertEqual(e['record']['fields']['wafer_type']['value'],'PW')
            self.assertNotEqual(e['record']['supplier_network_id'],'sumco')
            self.assertFalse(e['record']['legacy'])

    def test_pr_filters_exposure_and_excludes_origin(self):
        case=self.cases[1]
        broad=catalog_candidates(self.network,case)
        self.assertGreaterEqual(len({e['record']['supplier'] for e in broad}),3)
        euv=catalog_candidates(self.network,case,'EUV')
        self.assertTrue(euv)
        for e in euv:
            self.assertEqual(e['record']['fields']['exposure']['value'],'EUV')
            self.assertNotEqual(e['record']['supplier_network_id'],'jsr')
        self.assertFalse(any(e['record']['supplier_network_id']=='dongjin' for e in euv))

    def test_does_not_modify_network_or_add_routes(self):
        before=deepcopy(self.network)
        catalog_candidates(self.network,self.cases[1],'ArF')
        self.assertEqual(before,self.network)
        tariff=dict(self.cases[1],event='관세 부과')
        self.assertEqual(catalog_candidates(self.network,tariff),[])
        self.assertEqual(catalog_candidates(self.network,self.cases[2]),[])

    def test_cf4_does_not_include_nf3(self):
        case={'target':'unused','connections':[{'item':'etch-gas','supplier':'unknown','material':'CF4'}]}
        rows=catalog_candidates(self.network,case)
        self.assertTrue(rows)
        self.assertTrue(all(e['record']['fields']['chemical']['value']=='CF4' for e in rows))
