import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legacy.data_loader import load_demo
from legacy.simulation import load_model, build_simulation_payload
from legacy.simulation.service import expand_country_scenario
from legacy.simulation.engine import calculate


class LinkedDataTests(unittest.TestCase):
    def setUp(self):
        self.data = load_demo(ROOT / 'data/demo.json')
        self.model = load_model(ROOT / 'data/simulation_demo.json', self.data)

    def validate_changed(self, change):
        data = copy.deepcopy(self.data)
        change(data)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'data.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            return load_demo(path)

    def test_legacy_hubs_and_core_counts_are_preserved(self):
        hubs = {n['id'] for n in self.data['nodes'] if n['type'] == 'country_hub'}
        self.assertTrue({'seoul','tokyo','taipei','singapore','eindhoven','dresden','sf','austin','penang'} <= hubs)
        self.assertTrue(all(3 <= len(c) <= 6 for c in self.data['core_companies'].values()))

    def test_unknown_real_shares_are_null_and_model_shares_explicit(self):
        for edge in self.data['edges']:
            self.assertIsNone(edge['share_pct'])
            self.assertEqual(edge['share_status'], '확인 필요')
            self.assertEqual(edge['model_status'], '가정값')
            self.assertIn('source_year', edge)
        with self.assertRaisesRegex(ValueError, '확인되지 않은'):
            self.validate_changed(lambda d: d['edges'][0].update(share_pct=25))

    def test_missing_company_identity_and_wrong_hub_rejected(self):
        with self.assertRaisesRegex(ValueError, 'company_name'):
            self.validate_changed(lambda d: next(n for n in d['nodes'] if n.get('company_name')).pop('company_name'))
        with self.assertRaisesRegex(ValueError, '국가 거점'):
            self.validate_changed(lambda d: next(n for n in d['nodes'] if n.get('company_name')).update(country_hub_id='tokyo'))

    def test_hub_scenario_expands_only_to_that_country(self):
        scenario = expand_country_scenario(self.data, self.data['scenarios'][1])
        lookup = {n['id']: n for n in self.data['nodes']}
        self.assertIn('jsr', scenario['affected'])
        self.assertTrue(all(lookup[n]['country'] == '일본' for n in scenario['affected']))
        self.assertEqual(expand_country_scenario(self.data, {'affected':['jsr']})['affected'], ['jsr'])

    def test_company_edge_engine_and_unchanged_bottleneck_formula(self):
        partial = calculate(self.data, self.model, {'name':'ASML 50%', 'affected':['asml']}, severity=.5)
        photo = next(p for p in partial['processes'] if p['name'] == '포토')
        self.assertEqual(photo['score'], 50)
        self.assertEqual(partial['overall_score'], min(p['score'] for p in partial['processes']))
        self.assertEqual(photo['score'], min(i['score'] for i in photo['inputs'] if i['critical']))
        self.assertTrue(all('requires' not in n for n in self.data['nodes']))

    def test_service_reports_expand_legacy_scenarios_and_recovery(self):
        self.data['scenarios'] += self.model['additional_scenarios']
        payload = build_simulation_payload(self.data, self.model)
        self.assertEqual(payload['baseline']['overall_score'], 100)
        report = payload['reports'][self.data['scenarios'][3]['name']]
        self.assertEqual(report['overall_score'], 0)
        self.assertEqual(report['affected_companies'], ['asml'])
        supplier = report['processes'][2]['inputs'][0]['suppliers'][0]
        self.assertEqual(supplier['status'], '가정값')
        self.assertEqual(supplier['share_basis'], 'model_share_pct')
        self.assertIsNone(supplier['actual_share_pct'])
        self.assertIn('source_year', supplier)
        recovered = build_simulation_payload(self.data, self.model, {'severity':0})
        self.assertTrue(all(r['overall_score'] == 100 for r in recovered['reports'].values()))


if __name__ == '__main__':
    unittest.main()
