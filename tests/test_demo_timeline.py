from copy import deepcopy
import unittest
from resilience_data import build_network
from ui.demo import demo_results
from ui.logistics_demo import demo_cases
from ui.demo_timeline import timeline_data,timeline_html


class DemoTimelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.network=build_network()

    def test_observed_arrival_shortage_and_inventory_comparison(self):
        n=self.network;c=dict(next(c for c in demo_cases() if c['id']=='kaohsiung'),percent=100)
        baseline=demo_results(n,c,False,False)
        response=demo_results(n,c,True,False,True)
        inventory=demo_results(n,c,True,False)
        original=deepcopy(response)
        data=timeline_data(n,c,baseline,response,inventory)
        self.assertEqual(data['first_arrival'],4)
        self.assertEqual(data['first_shortage'],12)
        self.assertEqual(data['inventory_only_first'],8)
        self.assertEqual([e['day'] for e in data['events']],[1,4,12,30])
        self.assertEqual([r['value'] for r in data['after']],[r[c['process']] for r in response['process_views']['tsmc']['timeline']])
        self.assertIn('4일째',data['summary']);self.assertIn('8일째',data['summary'])
        self.assertEqual(response,original)

    def test_in_transit_is_not_an_arrival_and_single_day_renders(self):
        n=self.network;c=dict(next(c for c in demo_cases() if c['id']=='kaohsiung'),days=1,percent=100)
        baseline=demo_results(n,c,False,False)
        response=demo_results(n,c,False,False,True)
        data=timeline_data(n,c,baseline,response)
        self.assertIsNone(data['first_arrival'])
        self.assertFalse(any(e['kind']=='arrival' for e in data['events']))
        self.assertIn('도착이 없습니다',data['summary'])
        markup=timeline_html(data)
        self.assertNotIn('nan',markup.lower());self.assertNotIn('inf',markup.lower())
        self.assertIn('<circle',markup)

    def test_fully_buffered_material_has_no_fabricated_shortage(self):
        n=self.network;c=dict(demo_cases()[1],days=7,percent=100)
        baseline=demo_results(n,c,False,False)
        response=demo_results(n,c,True,True)
        data=timeline_data(n,c,baseline,response,response)
        self.assertIsNone(data['first_shortage']);self.assertIsNone(data['first_arrival'])
        self.assertFalse(any(e['kind']=='shortage' for e in data['events']))
        self.assertIn('관측 기간 내 소재 부족이 없습니다',data['summary'])
