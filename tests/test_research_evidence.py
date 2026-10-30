import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legacy.data_loader import load_demo
from legacy.simulation import load_model, build_simulation_payload


class ResearchEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = load_demo(ROOT / 'data/demo.json')
        self.edges = {e['id']: e for e in self.data['edges']}

    def test_verified_countries_have_country_specific_primary_sources(self):
        companies = [n for n in self.data['nodes'] if n['type'] != 'country_hub']
        self.assertEqual(len(companies), 17)
        for node in companies:
            self.assertEqual(node['country_status'], '출처 있음')
            self.assertTrue(node['country_source'].startswith('https://'))
            self.assertIn('country_source_year', node)

    def test_corporate_relation_is_not_automatically_specific_item_supply(self):
        for eid in ['developer:fujifilm>samsung','metal-precursor:merck>samsung',
                    'polished-wafer:sumco>tsmc']:
            edge = self.edges[eid]
            self.assertEqual(edge['relationship_status'], '출처 있음')
            self.assertEqual(edge['item_status'], '확인 필요')
        self.assertEqual(self.edges['metal-precursor:merck>samsung']['relationship_kind'], 'service')

    def test_past_and_planned_evidence_is_explicit(self):
        past = self.edges['deposition-tool:applied>samsung']
        self.assertEqual(past['item_source_year'], 1999)
        self.assertEqual(past['temporal_status'], 'historical')
        self.assertEqual(self.edges['processed-wafer:tsmc>amkor']['temporal_status'], 'planned')
        self.assertEqual(self.edges['processed-wafer:samsung>ase']['temporal_status'], 'expired_certificate')

    def test_samsung_ct_and_shared_investors_do_not_prove_tok_electronics_supply(self):
        edge = self.edges['photoresist:tok>samsung']
        self.assertEqual(edge['status'], '확인 필요')
        self.assertIsNone(edge['source'])

    def test_disclosed_revenue_share_is_not_used_as_procurement_weight(self):
        metric = self.data['public_metrics'][0]
        self.assertEqual(metric['value'], 12.5)
        self.assertFalse(metric['usable_as_edge_share'])
        edge = self.edges['wafer-tester:teradyne>samsung']
        self.assertIsNone(edge['share_pct'])
        self.assertEqual(edge['model_share_pct'], 25)
        self.assertTrue(all(e['share_pct'] is None for e in self.data['edges']))

    def test_source_catalog_and_summary_counts_agree(self):
        catalog = {s['id'] for s in self.data['evidence_catalog']['sources']}
        for e in self.edges.values():
            self.assertTrue(set(e['evidence_ids']) <= catalog)
        summary = self.data['research_summary']
        self.assertEqual(summary['relationship_evidence_edges'], sum(e['relationship_status']=='출처 있음' for e in self.edges.values()))
        self.assertEqual(summary['item_evidence_edges'], sum(e['item_status']=='출처 있음' for e in self.edges.values()))

    def test_research_keeps_original_company_model_score_matrix(self):
        expected = json.loads((ROOT/'tests/fixtures/pre_research_scores.json').read_text(encoding='utf-8'))
        model = load_model(ROOT/'data/simulation_demo.json', self.data)
        self.data['scenarios'] += model['additional_scenarios']
        reports = build_simulation_payload(self.data, model)['reports']
        actual = {name:{'overall_score':r['overall_score'], 'bottlenecks':r['bottlenecks'],
            'scores':[p['score'] for p in r['processes']]} for name,r in reports.items()}
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
