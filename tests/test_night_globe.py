import unittest
from copy import deepcopy
from resilience_data import build_network
from core_cases import core_cases
from ui.demo import demo_results
from ui.night_globe import globe_payload


class NightGlobeTests(unittest.TestCase):
    def test_registered_locations_and_engine_scores_are_preserved(self):
        network=build_network()
        before=deepcopy(network)
        for case in core_cases():
            applied=dict(case,days=60,percent=100)
            result=demo_results(network,applied,False,False)
            data=globe_payload(network,result,applied,True)
            self.assertEqual({r['end'] for r in data['routes']},set(case['recipients']))
            for marker in data['markers']:
                place=network['entities'][marker['id']]['map_location']
                self.assertEqual((marker['lat'],marker['lon']),(place['lat'],place['lon']))
                if marker['role']=='recipient':
                    self.assertEqual(marker['score'],result['process_views'][marker['id']]['scores'][case['process']])
        self.assertEqual(network,before)

    def test_missing_location_is_omitted_without_invented_route(self):
        network=build_network()
        case=core_cases()[1]
        result=demo_results(network,None)
        network['entities']['tsmc']['map_location']=None
        data=globe_payload(network,result,case)
        self.assertEqual(data['routes'],[])
        self.assertEqual([m['id'] for m in data['markers']],['jsr'])
        self.assertFalse(data['applied'])

    def test_response_routes_follow_allocated_reserve_and_turn_off(self):
        network=build_network()
        for case in core_cases():
            applied=dict(case,days=60,percent=100)
            response=demo_results(network,applied,True,True)
            data=globe_payload(network,response,applied,True,response=True)
            reserve=network['nodes'][network['nodes'][case['target']]['alt_vendor']]
            expected=reserve['company_id']
            self.assertEqual(data['alternative']['company_id'],expected)
            self.assertEqual(data['alternative']['amount'],response['nodes'][case['target']]['backup']*100)
            routes=[r for r in data['routes'] if r['kind']=='alternative']
            self.assertEqual({r['start'] for r in routes},{expected})
            self.assertEqual({r['end'] for r in routes},set(case['recipients']))
            no_backup=demo_results(network,applied,True,False)
            off=globe_payload(network,no_backup,applied,True,response=True)
            self.assertIsNone(off['alternative'])
            self.assertFalse(any(r['kind']=='alternative' for r in off['routes']))
            # Short interruption is entirely stock-buffered: enabled != used.
            short=dict(applied,days=1)
            buffered=demo_results(network,short,True,True)
            self.assertIsNone(globe_payload(network,buffered,short,True,response=True)['alternative'])

    def test_unlocated_alternative_has_summary_but_no_fabricated_route(self):
        network=build_network(); case=dict(core_cases()[1],days=60,percent=100)
        result=demo_results(network,case,True,True)
        network['entities']['dongjin']['map_location']=None
        data=globe_payload(network,result,case,True,response=True)
        self.assertIsNotNone(data['alternative'])
        self.assertFalse(any(r['kind']=='alternative' for r in data['routes']))
