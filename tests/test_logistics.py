import unittest
from resilience_data import build_network
from resilience_globe import build_globe, COLORS
from resilience_logistics import sea_route
from simulation.resilience import calculate_supply_shock, interpret_issue, apply_issue


class LogisticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.n=build_network()

    def event(self,q):return interpret_issue(q,self.n)

    def test_route_order_and_unrelated_routes(self):
        self.assertEqual(sea_route('독일','대만'),['logistics:suez','logistics:malacca','logistics:kaohsiung'])
        self.assertEqual(sea_route('대만','독일'),list(reversed(sea_route('독일','대만'))))
        self.assertEqual(sea_route('미국','한국'),[])
        self.assertEqual(sea_route('일본','일본'),[])

    def test_named_and_generic_blockades_and_recovery(self):
        self.assertEqual(self.event('해협 봉쇄 30일')['targets'],['logistics:malacca'])
        self.assertIn('이름이 없어',self.event('해협 봉쇄 30일')['note'])
        for label,key in [('수에즈 운하','suez'),('말라카 해협','malacca'),('가오슝항','kaohsiung')]:
            e=self.event(label+' 봉쇄 30일')
            self.assertEqual(e['targets'],['logistics:'+key])
            self.assertEqual(apply_issue([e],self.event(label+' 복구')),[])

    def test_all_assigned_shipments_stop_and_unassigned_supply_does_not(self):
        e=self.event('수에즈 운하 봉쇄 30일')
        r=calculate_supply_shock(self.n,[e],30,use_inventory=False,use_bypass=False)
        for key,route in self.n['logistics_routes'].items():
            if 'logistics:suez' in route['via'] and route['scope']=='core':
                self.assertEqual(r['nodes'][key]['primary'],0)
        self.assertEqual(r['nodes']['logistics:kaohsiung']['effective'],1)
        self.assertEqual(r['nodes']['sumco']['effective'],1)

    def test_stock_protects_short_blockade_but_marker_and_arcs_close_immediately(self):
        e=self.event('말라카 해협 봉쇄 3일')
        r=calculate_supply_shock(self.n,[e],3)
        self.assertEqual(r['overall'],100)
        self.assertEqual(r['nodes']['logistics:malacca']['effective'],0)
        fig=build_globe(self.n,r)
        self.assertTrue(any(t.mode=='lines' and t.line.color==COLORS['stopped'] for t in fig.data))
        marker=next(t for t in fig.data if t.mode=='markers+text' and t.customdata[0]=='logistics:malacca')
        self.assertEqual(marker.marker.color,COLORS['stopped'])
        # A rendered blocked arc includes the chokepoint coordinates exactly.
        p=self.n['logistics']['logistics:malacca']
        self.assertTrue(any(any(abs(a-p['lat'])<1e-6 and abs(b-p['lon'])<1e-6
            for a,b in zip(t.lat,t.lon) if a is not None) for t in fig.data if t.mode=='lines'))

    def test_multiple_closures_partial_loss_and_original_records(self):
        events=[self.event('말라카 해협 통항 감소 50% 30일'),self.event('가오슝항 폐쇄 30일')]
        r=calculate_supply_shock(self.n,events,30)
        self.assertEqual(r['nodes']['logistics:malacca']['effective'],.5)
        self.assertEqual(r['nodes']['logistics:kaohsiung']['effective'],0)
        self.assertEqual(len(self.n['backbone']),44)
        self.assertEqual(len(self.n['locations']),27)
        self.assertEqual(len(self.n['logistics']),6)  # three original + three detour candidates

    def test_unblocked_alternative_delivery_can_serve_a_blocked_primary_route(self):
        edge=next(e for e in self.n['visual_edges'] if e['from']=='supply:airliquide:oxygen' and e['to']=='samsung')
        key=edge['transport_node'];node=self.n['nodes'][key]
        self.assertIn('logistics:suez',node['logistics_via'])
        self.assertNotIn('logistics:suez',node['alt_logistics_via'])
        e=self.event('수에즈 운하 봉쇄 30일')
        on=calculate_supply_shock(self.n,[e],30,use_inventory=False)
        off=calculate_supply_shock(self.n,[e],30,use_inventory=False,use_bypass=False)
        self.assertGreater(on['nodes'][key]['backup'],0)
        self.assertEqual(off['nodes'][key]['effective'],0)
        # Geography must render transport-level reserve allocations safely.
        build_globe(self.n,on)

    def test_shared_delivery_reserve_is_not_duplicated_and_blocked_alternative_cannot_pass(self):
        def node(**kw):
            d=dict(requires=[],inventory_days=0,alt_vendor=None,alt_capacity=0,scope='core');d.update(kw);return d
        nodes={'cp':node(),'supplier':node(),'pool':node(capacity_units=.6)}
        for k in ('a','b'):
            nodes[k]=node(kind='transport',requires=['supplier','cp'],logistics_via=['cp'],
                alt_vendor='pool',alt_capacity=.6,alt_logistics_via=[])
        n=dict(nodes=nodes,process_outputs={'p':['a','b']})
        events=[dict(kind='supply',targets=['cp'],rate=1,days=1)]
        r=calculate_supply_shock(n,events,1)
        self.assertAlmostEqual(sum(r['nodes'][k]['backup'] for k in ('a','b')),.6)
        for k in ('a','b'):nodes[k]['alt_logistics_via']=['cp']
        r=calculate_supply_shock(n,events,1)
        self.assertEqual(r['overall'],0)


if __name__=='__main__':unittest.main()
