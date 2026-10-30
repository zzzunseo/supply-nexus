import unittest
from copy import deepcopy
from resilience_data import build_network
from ui.logistics_demo import demo_cases
from ui.simulation_candidates import catalog_candidates
from ui.candidate_visuals import candidate_visual_data, candidate_diagram

class CandidateVisualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network=build_network()
        cls.case=dict(demo_cases()[1],percent=100,event='공급 중단')

    def test_fujifilm_selected_routes_and_focus(self):
        rows=catalog_candidates(self.network,self.case,'ArF')
        data,missing,focused=candidate_visual_data(self.network,self.case,rows,'fujifilm_gar')
        self.assertEqual(focused['id'],'fujifilm')
        alternatives=[r for r in data['routes'] if r['kind']=='alternative']
        self.assertTrue(alternatives)
        self.assertTrue(all(r['start']=='fujifilm' for r in alternatives))
        self.assertEqual({r['end'] for r in alternatives},set(self.case['recipients']))
        self.assertTrue(all(m['score'] is None for m in data['markers']))

    def test_separate_material_does_not_imply_customer_connection(self):
        case=dict(self.case,connections=[dict(item='hf',supplier='jsr',material='불산 HF')])
        rows=catalog_candidates(self.network,case)
        data,missing,focused=candidate_visual_data(self.network,case,rows,rows[0]['record']['id'],False)
        self.assertFalse(data['routes'])
        self.assertFalse(missing)  # HF suppliers now have verified city locations.
        self.assertTrue(data['markers'])
        self.assertNotIn('c0 [',candidate_diagram(self.network,rows,rows[0]['record']['id'],False))

    def test_visualization_does_not_mutate_model(self):
        before=deepcopy(self.network)
        rows=catalog_candidates(self.network,self.case,'EUV')
        candidate_visual_data(self.network,self.case,rows,'ff_euv')
        self.assertEqual(before,self.network)
        self.assertNotIn('Dongjin',candidate_diagram(self.network,rows,'ff_euv'))
