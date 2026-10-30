import copy
from pathlib import Path
import unittest
from legacy.data_loader import load_demo
from legacy.simulation import load_model, build_simulation_payload
from legacy.simulation.overview import aggregate_countries
ROOT=Path(__file__).resolve().parents[1]

class OverviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_demo(ROOT/'data/demo.json')
        cls.model=load_model(ROOT/'data/simulation_demo.json',cls.data)
        cls.data['scenarios']+=cls.model.get('additional_scenarios',[])
    def payload(self,**options):
        return build_simulation_payload(self.data,self.model,options)
    def cell(self,overview,country,process):
        return next(c for r in overview['countries'] if r['country']==country for c in r['cells'] if c['process']==process)
    def test_hand_calculated_three_cells(self):
        overview=self.payload()['reports']['정상 상태']['overview']
        for country,process,expected in [('일본','포토',100),('네덜란드','포토',100),('일본','EDS',50)]:
            self.assertEqual(self.cell(overview,country,process)['value_pct'],expected)
        jp=self.cell(overview,'일본','포토')
        self.assertEqual([d['share_pct'] for d in jp['details']],[100,100])
    def test_absence_is_not_explicit_zero(self):
        report=self.payload()['reports']['정상 상태']
        self.assertIsNone(self.cell(report['overview'],'네덜란드','산화')['value_pct'])
        fake=copy.deepcopy(report)
        for s in fake['processes'][2]['inputs'][2]['suppliers']: s['share_pct']=0
        zero=self.cell(aggregate_countries(self.data,fake),'네덜란드','포토')
        self.assertTrue(zero['has_data']);self.assertEqual(zero['value_pct'],0)
    def test_partial_outage_keeps_exposure_and_changes_contribution(self):
        report=next(v for k,v in self.payload(severity=.5)['reports'].items() if '네덜란드' in k)
        cell=self.cell(report['overview'],'네덜란드','포토')
        self.assertEqual(cell['value_pct'],100);self.assertEqual(cell['loss_pct'],50)
        self.assertEqual(cell['status'],'warning');self.assertEqual(report['overall_score'],50)
        self.assertEqual(report['overview']['affected_process_count'],1)
    def test_pairs_unique_and_weights_conserved_excluding_domestic(self):
        report=self.payload()['reports']['정상 상태'];o=report['overview'];nodes={n['id']:n for n in self.data['nodes']}
        self.assertEqual(len({tuple(sorted((f['from'],f['to']))) for f in o['flows']}),len(o['flows']))
        self.assertEqual(sum(f['flow_weight'] for f in o['flows']),sum(e['model_share_pct'] for e in self.data['edges'] if nodes[e['from']]['country']!=nodes[e['to']]['country']))
        for row in o['countries']:
            expected=set(p for e in self.data['edges'] if row['country'] in [nodes[e['from']]['country'],nodes[e['to']]['country']] for p in e['processes'])
            self.assertEqual(row['process_count'],len(expected))
    def test_all_conditions_and_nonmutating_summary(self):
        for days in [7,14,30,60]:
            for severity in [0,.25,.5,1]:
                report=next(v for k,v in self.payload(duration_days=days,severity=severity,inventory=False,substitutes=True)['reports'].items() if '일본' in k and '대만' not in k)
                before=copy.deepcopy(report);o=aggregate_countries(self.data,report)
                self.assertEqual(report,before)
                self.assertEqual(o['overall_score'],report['overall_score'])
                self.assertEqual(o['affected_process_count'],sum(p['score']<100-1e-7 for p in report['processes']))
