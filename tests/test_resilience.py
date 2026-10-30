import json
from pathlib import Path
import unittest
from resilience_data import build_network
from resilience_globe import build_globe
from simulation.resilience import calculate_supply_shock, interpret_issue, apply_issue


def node(requires=(), **extra):
    return dict(requires=list(requires),inventory_days=0.,alt_capacity=0.,alt_vendor=None,
                mode='min',scope='core',**extra)


class ResilienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.graph=build_network()

    def test_original_44_records_preserved_including_status_and_null_share(self):
        original=json.loads((Path(__file__).resolve().parents[1]/'data/demo.json').read_text(encoding='utf-8'))
        self.assertEqual(self.graph['backbone'],original['edges'])
        self.assertEqual(len(self.graph['backbone']),44)
        records=[e['backbone_id'] for e in self.graph['visual_edges'] if e['kind']=='backbone']
        self.assertEqual(set(records),{e['id'] for e in original['edges']})
        self.assertEqual(len(records),44)

    def test_all_nodes_have_editable_resilience_metadata(self):
        for n in self.graph['nodes'].values():
            for f in ('alt_vendor','alt_capacity','inventory_days','source','source_year','parameter_status'):
                self.assertIn(f,n)
        self.assertEqual(len(self.graph['upstream_products']),14)
        self.assertTrue(all(v==100 for v in calculate_supply_shock(self.graph)['scores'].values() if v is not None))

    def test_exact_inventory_boundary_and_consumption_not_reset_each_day(self):
        n=node();n['inventory_days']=3
        g=dict(nodes={'x':n},process_outputs={'p':['x']})
        e=[dict(kind='supply',targets=['x'],rate=1,days=10)]
        self.assertEqual(calculate_supply_shock(g,e,3)['overall'],100)
        self.assertEqual(calculate_supply_shock(g,e,4)['overall'],0)
        self.assertEqual(calculate_supply_shock(g,e,4)['average_scores']['p'],75)

    def test_partial_loss_uses_stock_by_actual_deficit(self):
        n=node();n['inventory_days']=2
        g=dict(nodes={'x':n},process_outputs={'p':['x']})
        e=[dict(kind='supply',targets=['x'],rate=.5,days=10)]
        self.assertEqual(calculate_supply_shock(g,e,4)['overall'],100)
        self.assertEqual(calculate_supply_shock(g,e,5)['overall'],50)

    def test_40_percent_backup_and_zero_without_backup(self):
        n=node();n.update(alt_vendor='pool',alt_capacity=.4)
        g=dict(nodes={'pool':node(),'x':n},process_outputs={'p':['x']})
        e=[dict(kind='supply',targets=['x'],rate=1,days=5)]
        self.assertEqual(calculate_supply_shock(g,e,5)['overall'],40)
        self.assertEqual(calculate_supply_shock(g,e,5,use_bypass=False)['overall'],0)
        e.append(dict(kind='supply',targets=['pool'],rate=1,days=5))
        self.assertEqual(calculate_supply_shock(g,e,5)['overall'],0)

    def test_shared_pool_never_double_counted(self):
        nodes={'pool':node()}
        for k in ('a','b'):
            nodes[k]=node();nodes[k].update(alt_vendor='pool',alt_capacity=.6)
        g=dict(nodes=nodes,process_outputs={'p':['a','b']})
        r=calculate_supply_shock(g,[dict(kind='supply',targets=['a','b'],rate=1,days=1)],1)
        self.assertAlmostEqual(sum(r['nodes'][k]['backup'] for k in ('a','b')),1.)
        self.assertEqual(r['overall'],50)

    def test_japan_pr_propagates_and_can_be_defended(self):
        e=interpret_issue('일본 포토레지스트 중단 30일',self.graph)
        self.assertEqual(set(e['targets']),{'supply:jsr:photoresist','supply:tok:photoresist'})
        r=calculate_supply_shock(self.graph,[e],30)
        self.assertEqual(r['scores']['포토'],60)
        self.assertEqual(r['scores']['금속배선'],100)
        self.assertEqual(len(r['bypass']),2)
        self.assertEqual(calculate_supply_shock(self.graph,[e],30,use_bypass=False)['scores']['포토'],0)

    def test_mineral_cascade_does_not_invent_unconfirmed_packaging_supply(self):
        e=interpret_issue('미국 고순도 석영 공급 중단 60일',self.graph)
        self.assertEqual(e['targets'],['raw:quartz'])
        r=calculate_supply_shock(self.graph,[e],60)
        self.assertEqual(r['scores']['웨이퍼 제조'],0)
        self.assertTrue(all(v==100 for p,v in r['scores'].items() if p!='웨이퍼 제조' and v is not None))
        self.assertIsNone(r['scores']['패키징'])
        self.assertIn('패키징', r['incomplete_processes'])
        self.assertEqual(calculate_supply_shock(self.graph,[e],7)['overall'],100)

    def test_tariff_changes_cost_index_only(self):
        e=interpret_issue('중국 갈륨 관세 20%',self.graph)
        r=calculate_supply_shock(self.graph,[e],30,scopes=['gallium'])
        self.assertEqual(r['overall'],100);self.assertEqual(r['tariffs'][0]['index'],120)

    def test_specialty_recipe_is_not_universal_dependency(self):
        e=interpret_issue('중국 갈륨 공급 중단',self.graph)
        self.assertEqual(calculate_supply_shock(self.graph,[e],30)['overall'],100)
        self.assertEqual(calculate_supply_shock(self.graph,[e],30,scopes=['gallium'])['scores']['웨이퍼 제조'],35)

    def test_company_material_intersection_and_restore(self):
        e=interpret_issue('JSR 포토레지스트 중단',self.graph)
        self.assertEqual(e['targets'],['supply:jsr:photoresist'])
        ce=interpret_issue('중국 희토류 통제',self.graph)
        events=apply_issue(apply_issue([],e),ce)
        events=apply_issue(events,interpret_issue('JSR 포토레지스트 복구',self.graph))
        self.assertEqual(events[0]['targets'],['raw:ceria']);self.assertEqual(len(events),1)

    def test_unknown_factory_ambiguous_country_and_invalid_percent_blocked(self):
        for q in ('일본 지진 Nokia 공장 차질','일본 구마모토 공급 중단','중국 갈륨 관세',
                  '중국 갈륨 공급 -20% 감소','포토레지스트 110% 중단'):
            with self.subTest(q=q),self.assertRaises(ValueError):interpret_issue(q,self.graph)

    def test_cycles_and_unknown_shocks_rejected(self):
        g=dict(nodes={'x':node(['x'])},process_outputs={'p':['x']})
        with self.assertRaises(ValueError):calculate_supply_shock(g)
        with self.assertRaises(ValueError):calculate_supply_shock(self.graph,[dict(kind='supply',targets=['missing'],rate=1)])

    def test_plotly_orthographic_and_bypass_visible(self):
        e=interpret_issue('일본 포토레지스트 중단 30일',self.graph)
        r=calculate_supply_shock(self.graph,[e],30)
        f=build_globe(self.graph,r)
        self.assertEqual(f.layout.geo.projection.type,'orthographic')
        self.assertTrue(any(t.line.color=='#409CFF' for t in f.data if t.mode=='lines'))
        self.assertTrue(any(t.line.dash=='dash' for t in f.data if t.mode=='lines'))
        for level in ('국가','기업'):
            self.assertTrue(build_globe(self.graph,r,level=level).data)


if __name__=='__main__':unittest.main()
