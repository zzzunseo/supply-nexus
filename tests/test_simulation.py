"""Hand-calculated cases, invariants, scenario contrasts and integration seam."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legacy.data_loader import load_demo
from legacy.simulation import calculate, calculate_input, load_model, validate_model, build_simulation_payload
from legacy.simulation.service import normalize_options


def item(name, suppliers, stock=0, substitute=0, lead=0, critical=True):
    return {'item_id': name, 'name': name, 'suppliers': suppliers, 'critical': critical,
            'buffer_days': stock, 'substitute_fraction': substitute,
            'substitute_lead_days': lead, 'source': 'unit test assumption', 'source_year': None}


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.data = load_demo(ROOT / 'tests' / 'fixtures' / 'legacy_demo.json')
        self.model = load_model(ROOT / 'tests' / 'fixtures' / 'legacy_model.json', self.data)
        self.data['scenarios'] += self.model['additional_scenarios']

    def report(self, index, **kwargs):
        return calculate(self.data, self.model, self.data['scenarios'][index], **kwargs)

    def test_three_inputs_hand_calculation(self):
        # Source x is at 50%, y at 100% for 10 days.
        # A = .6*.5 + .4*1 = .7
        # B = 1*.5 + .1 substitution + 1/10 inventory = .7
        # C = 1*1 = 1. AND score = 100*min(.7,.7,1) = 70.
        data = {'processes': ['공정'], 'nodes': [{'id': n} for n in ('x','y','z')],
                'edges': [{'id': rid, 'from': src, 'to': 'z', 'item': name, 'processes': ['공정']}
                          for rid, src, name in [('a1','x','A'),('a2','y','A'),('b1','x','B'),('c1','y','C')]]}
        inputs = [item('A', [{'edge_id':'a1','share_pct':60},{'edge_id':'a2','share_pct':40}]),
                  item('B', [{'edge_id':'b1','share_pct':100}], stock=1, substitute=.1),
                  item('C', [{'edge_id':'c1','share_pct':100}])]
        model = {'processes':[{'name':'공정','required_inputs':inputs}]}
        report = calculate(data, model, {'name':'half x','affected':['x']},
                           severity=.5, duration_days=10, substitutes=True)
        self.assertEqual(report['overall_score'],70)
        self.assertEqual(report['processes'][0]['limiting_items'],['A','B'])
        self.assertAlmostEqual(report['processes'][0]['inputs'][1]['inventory'],.1)

    def test_normal_is_100_and_has_no_bottleneck(self):
        report = self.report(0)
        self.assertEqual(report['overall_score'],100)
        self.assertEqual(report['bottlenecks'],[])
        self.assertEqual(report['affected_nodes'],[])
        self.assertTrue(all(p['score']==100 for p in report['processes']))

    def test_japan_scenario_manual_resist_and_gas_result(self):
        report = self.report(1, duration_days=14, substitutes=False)
        self.assertAlmostEqual(report['overall_score'],100*3/14,places=3)
        self.assertEqual(report['bottlenecks'],['포토','식각'])

    def test_netherlands_causes_downstream_serial_ceiling(self):
        report = self.report(3)
        self.assertEqual(report['bottlenecks'],['포토'])
        self.assertEqual(report['processes'][3]['score'],100)
        self.assertEqual(report['processes'][3]['serial_score'],0)
        self.assertEqual(report['processes'][0]['serial_score'],100)

    def test_partial_outage_has_warning_routes_and_fractional_score(self):
        report = self.report(3, severity=.5)
        self.assertEqual(report['overall_score'],50)
        self.assertEqual(report['edge_status']['r05'],'warning')
        self.assertEqual(report['edge_availability']['r05'],.5)

    def test_zero_severity_equals_recovery(self):
        report = self.report(4,severity=0)
        self.assertEqual(report['overall_score'],100)
        self.assertEqual(report['affected_nodes'],[])

    def test_input_availability_capped_at_100_without_double_count(self):
        config=item('test',[{'edge_id':'e','share_pct':100}],stock=100,substitute=.9)
        result=calculate_input(config,{'e':.5},7,substitutes=True)
        self.assertEqual(result['availability'],1)
        self.assertEqual(result['substitute'],.5)
        self.assertEqual(result['inventory'],0)

    def test_substitute_lead_time_after_horizon_gives_zero(self):
        config=item('test',[{'edge_id':'e','share_pct':100}],substitute=.5,lead=14)
        self.assertEqual(calculate_input(config,{'e':0},7,substitutes=True)['substitute'],0)
        self.assertEqual(calculate_input(config,{'e':0},14,substitutes=True)['substitute'],0)

    def test_inventory_disabled_removes_buffer(self):
        no_stock=self.report(1,inventory=False)
        with_stock=self.report(1,inventory=True)
        self.assertEqual(no_stock['overall_score'],0)
        self.assertGreater(with_stock['overall_score'],0)

    def test_longer_disruption_reduces_inventory_coverage(self):
        self.assertGreater(self.report(1,duration_days=7)['overall_score'],self.report(1,duration_days=30)['overall_score'])

    def test_substitution_is_separate_capacity_and_can_be_disabled(self):
        base=self.report(1,substitutes=False)
        alt=self.report(1,substitutes=True)
        self.assertGreater(alt['overall_score'],base['overall_score'])

    def test_duplicate_endpoint_outage_not_counted_twice(self):
        report=self.report(4,severity=.5)
        self.assertEqual(report['edge_availability']['r04'],.5)

    def test_invalid_shares_rejected(self):
        broken=copy.deepcopy(self.model)
        broken['processes'][0]['required_inputs'][0]['suppliers'][0]['share_pct']=99
        with self.assertRaisesRegex(ValueError,'배분율'):
            validate_model(self.data,broken)

    def test_invalid_numeric_conditions_rejected(self):
        for severity in [-.1,1.1,float('nan'),float('inf'),True]:
            with self.subTest(severity=severity),self.assertRaises(ValueError):
                self.report(1,severity=severity)
        with self.assertRaises(ValueError):self.report(1,duration_days=0)

    def test_scenario_report_does_not_mutate_input(self):
        before=json.dumps([self.data,self.model],ensure_ascii=False)
        self.report(4)
        self.assertEqual(before,json.dumps([self.data,self.model],ensure_ascii=False))
        self.assertEqual(self.report(0)['overall_score'],100)

    def test_five_scenarios_have_bounded_scores_and_match_minimum(self):
        for index in range(5):
            for severity in [0,.25,.5,1]:
                report=self.report(index,severity=severity)
                self.assertTrue(all(0<=p['score']<=100 for p in report['processes']))
                self.assertEqual(report['overall_score'],min(p['score'] for p in report['processes']))
                self.assertEqual(report['overall_score'],report['processes'][-1]['serial_score'])

    def test_payload_matches_controls_and_reports_all_scenarios(self):
        payload=build_simulation_payload(self.data,self.model,{'duration_days':30,'severity':.25,'inventory':False,'substitutes':True})
        self.assertEqual(len(payload['reports']),5)
        self.assertEqual(payload['options']['duration_days'],30)
        self.assertEqual(payload['reports'][self.data['scenarios'][3]['name']]['overall_score'],75)

    def test_controls_normalization(self):
        self.assertEqual(normalize_options({'duration_days':-1,'severity':True})['severity'],1.0)


if __name__=='__main__':unittest.main()
