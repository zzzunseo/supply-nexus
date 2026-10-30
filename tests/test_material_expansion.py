import unittest
from resilience_data import build_network
from resilience_materials import material_rows, scopes_for_targets
from simulation.resilience import calculate_supply_shock, interpret_issue, generations


class MaterialExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.n=build_network()

    def test_all_60_materials_are_resolvable_and_connected_to_processes(self):
        self.assertEqual(len(self.n['extended_materials']),60)
        self.assertEqual(len(material_rows(self.n)),104)
        generations(self.n['nodes'])
        for spec in self.n['extended_materials'].values():
            e=interpret_issue(spec['aliases'][0]+' 공급 중단 60일',self.n)
            self.assertTrue(set(spec['candidate_nodes']) & set(e['targets']),spec['name'])
            self.assertIn(spec['scope'],scopes_for_targets(self.n,e['targets']))
            self.assertTrue(any(x['scope']==spec['scope'] and x['to'] in ('samsung','tsmc','ase','amkor')
                for x in self.n['visual_edges']),spec['name'])
            self.assertTrue(all(s['source'].startswith('https://') for s in spec['suppliers']))

    def run_issue(self,q,bypass=True):
        e=interpret_issue(q,self.n)
        return calculate_supply_shock(self.n,[e],e['days'],use_bypass=bypass,
            scopes=scopes_for_targets(self.n,e['targets']))

    def test_every_new_material_can_affect_its_registered_process(self):
        for spec in self.n['extended_materials'].values():
            e=interpret_issue(spec['aliases'][0]+' 공급 중단 1일',self.n)
            r=calculate_supply_shock(self.n,[e],1,use_inventory=False,use_bypass=False,
                scopes=scopes_for_targets(self.n,e['targets']))
            self.assertTrue(any(r['scores'][p]<100 for p in spec['processes']),spec['name'])

    def test_extra_wafer_is_a_parallel_supplier_not_a_new_mandatory_input(self):
        e=interpret_issue('실트로닉 공급 중단 60일',self.n)
        r=calculate_supply_shock(self.n,[e],60,use_inventory=False,use_bypass=False,
            scopes=scopes_for_targets(self.n,e['targets']))
        self.assertAlmostEqual(r['scores']['웨이퍼 제조'],100*2/3)

    def test_country_scoped_nf3_has_parallel_supply_and_late_bypass(self):
        q='독일 NF3 공급 중단 60일'
        r=self.run_issue(q);off=self.run_issue(q,False)
        self.assertEqual(r['scores']['산화'],100)
        self.assertEqual(off['scores']['증착·이온주입'],50)
        self.assertEqual(r['scores']['증착·이온주입'],70)
        self.assertEqual(r['nodes']['extended:nf3:merck']['backup'],.4)

    def test_packaging_material_does_not_shutdown_frontend(self):
        r=self.run_issue('레조낙 DAF 공급 중단 90일')
        self.assertEqual(r['scores']['패키징'],70)
        self.assertTrue(all(v==100 for k,v in r['scores'].items() if k!='패키징' and v is not None))

    def test_shared_origin_shock_cannot_be_bypassed_by_same_origin(self):
        r=self.run_issue('중국 형석 공급 중단 60일')
        self.assertIn('material:nf3',r['scopes'])
        for k in self.n['extended_materials']['nf3']['candidate_nodes']:
            self.assertEqual(r['nodes'][k]['effective'],0)
        self.assertEqual(r['nodes']['reserve:extended:nf3']['effective'],0)

    def test_qualification_and_ramp_start_at_shortage_not_after_stock(self):
        nodes={
            'pool':dict(requires=[],inventory_days=0,alt_vendor=None,alt_capacity=0),
            'a':dict(requires=[],inventory_days=0,alt_vendor='pool',alt_capacity=.6,
                     alt_qualification_days=2,alt_ramp_days=3)}
        n=dict(nodes=nodes,process_outputs={'p':['a']})
        r=calculate_supply_shock(n,[dict(kind='supply',targets=['a'],rate=1,days=5)],5)
        self.assertEqual([round(v['p']) for v in r['timeline']],[0,0,20,40,60])
        nodes['a']['inventory_days']=3
        r=calculate_supply_shock(n,[dict(kind='supply',targets=['a'],rate=1,days=5)],5)
        self.assertEqual([round(v['p']) for v in r['timeline']],[100,100,100,40,60])

    def test_worldwide_full_material_stop_also_hits_alternative_grade(self):
        r=self.run_issue('NF3 공급 중단 60일')
        self.assertEqual(r['scores']['증착·이온주입'],0)
        self.assertEqual(r['nodes']['reserve:extended:nf3']['effective'],0)

    def test_no_fictitious_production_countries_or_coordinates(self):
        for row in material_rows(self.n):
            self.assertEqual(row['실제생산국'],'미확인')
            self.assertEqual(row['고객납품'],'가정·미확인')
        for vendor in self.n['extended_vendors']:
            self.assertIsNone(self.n['nodes'][vendor['id']]['map_location_id'])
        self.assertEqual(len(self.n['backbone']),44)

    def test_registered_supplier_fire_is_an_explicit_company_scenario(self):
        e=interpret_issue('헨켈 화재 60일',self.n)
        self.assertEqual(e['targets'],['henkel'])
        self.assertIn('가정',e['note'])
        self.assertIn('material:die-film',scopes_for_targets(self.n,e['targets']))


if __name__=='__main__':unittest.main()
