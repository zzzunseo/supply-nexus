import copy
import unittest
from legacy import app_chain_demo as demo

class ChainDemoTests(unittest.TestCase):
    def setUp(self): self.network=demo.make_network()
    def test_normal_all_processes_100(self):
        r=demo.calculate_supply_shock(self.network)
        self.assertEqual(len(self.network['tier1']),16)
        self.assertEqual(list(r['scores']),demo.PROCESSES)
        self.assertTrue(all(s==100 for s in r['scores'].values()))
        self.assertFalse(r['bypass'])
    def test_material_vendor_core_process_cascade_and_sixty_point_defense(self):
        r=demo.calculate_supply_shock(self.network,{'m00':1})
        self.assertEqual(r['raw']['v00'],0)
        self.assertEqual(r['tier1']['c00'],dict(primary=0,backup=.6,effective=.6))
        self.assertEqual(r['scores']['포토'],60)
        self.assertEqual(sum(s<100 for s in r['scores'].values()),1)
        self.assertEqual(demo.calculate_supply_shock(self.network,{'m00':1},False)['scores']['포토'],0)
    def test_partial_primary_and_alt_capacity_add_not_floor(self):
        r=demo.calculate_supply_shock(self.network,{'m01':.8})
        self.assertAlmostEqual(r['tier1']['c01']['effective'],.6)
        self.assertEqual(r['scores']['포토'],60)
        full=demo.calculate_supply_shock(self.network,{'m01':1})
        self.assertEqual(full['scores']['포토'],40)
    def test_disrupted_alternative_not_invented_supply(self):
        r=demo.calculate_supply_shock(self.network,{'m00':1,'am00':1})
        self.assertEqual(r['scores']['포토'],0)
        self.assertNotIn('c00',r['bypass'])
    def test_shared_vendor_pool_not_double_counted(self):
        n=copy.deepcopy(self.network)
        n['tier1']['c01']['alt_vendor']=n['tier1']['c00']['alt_vendor']
        n['nodes']['av00']['capacity']=.5
        r=demo.calculate_supply_shock(n,{'c00':1,'c01':1})
        self.assertAlmostEqual(r['tier1']['c00']['backup'],.3)
        self.assertAlmostEqual(r['tier1']['c01']['backup'],.2)
        self.assertAlmostEqual(sum(r['tier1'][c]['backup'] for c in ['c00','c01']),.5)
    def test_cycles_unknown_shocks_and_invalid_numbers_rejected(self):
        for shocks in [{'missing':1},{'m00':float('nan')},{'m00':-1},{'m00':True}]:
            with self.assertRaises(ValueError):demo.calculate_supply_shock(self.network,shocks)
        n=copy.deepcopy(self.network);n['nodes']['m00']['requires']=['v00']
        with self.assertRaises(ValueError):demo.calculate_supply_shock(n)
    def test_named_alternative_not_parent_name_substring(self):
        targets,loss,action,_=demo.interpret_issue('대체용 감광 원료 A 공급 100% 감소',self.network)
        self.assertEqual(targets,['am00']);self.assertEqual(loss,1);self.assertEqual(action,'apply')
        targets,_,_,_=demo.interpret_issue('규슈 소재 100% 중단',self.network)
        self.assertEqual(set(targets),{'m00','m08','m14'})
    def test_unknown_factory_and_tariff_do_not_create_supply_shocks(self):
        for text in ['일본 지진 Nokia 공장 중단','희토류 관세 20% 부과']:
            targets,_,action,_=demo.interpret_issue(text,self.network)
            self.assertEqual(action,'blocked');self.assertFalse(targets)
    def test_figures_only_have_backup_trace_when_supply_allocated(self):
        normal=demo.build_globe(self.network,demo.calculate_supply_shock(self.network))
        hit=demo.build_globe(self.network,demo.calculate_supply_shock(self.network,{'m00':1}))
        self.assertNotIn('우회 공급',[t.name for t in normal.data])
        self.assertIn('우회 공급',[t.name for t in hit.data])
        self.assertEqual(hit.layout.scene.camera.projection.type,'orthographic')
