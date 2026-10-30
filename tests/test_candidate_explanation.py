import unittest
from resilience_data import build_network
from ui.process_catalog import process_map_payload
from ui.candidate_explanation import candidate_from_pick, explain_candidate


class CandidateExplanationTests(unittest.TestCase):
    def test_marker_and_route_explain_candidate_without_changing_origin(self):
        data, entries, group = process_map_payload(build_network(), 'dry-etch', '브이엠')
        entry = next(e for e in entries if e['name'] == 'Tokyo Electron')
        route = next(r for r in data['routes'] if r['start'] == entry['map_id'])
        for kind, identity in [('marker', entry['map_id']), ('route', route['id'])]:
            event = dict(context=data['context'], kind=kind, id=identity)
            self.assertEqual(candidate_from_pick(data, entries, '브이엠', event), 'Tokyo Electron')
        self.assertIsNone(candidate_from_pick(data, entries, '브이엠', dict(context='stale', id=entry['map_id'])))
        explanation = explain_candidate('dry-etch', group, '브이엠', entry)
        self.assertIn('브이엠', explanation['supply'])
        self.assertIn('건식 식각 장비', explanation['reason'])
        self.assertIn(group['condition'], explanation['conditions'])
        self.assertTrue(explanation['sources'])
        self.assertIn('미확인', explanation['limit'])

    def test_material_specific_conditions_and_products(self):
        data, entries, group = process_map_payload(build_network(), 'hf', 'DAIKIN')
        entry = next(e for e in entries if e['name'] == '솔브레인')
        explanation = explain_candidate('hf', group, 'DAIKIN', entry)
        self.assertEqual(explanation['products'], entry['products'])
        self.assertIn('농도', explanation['conditions'][0])
        self.assertNotIn('노광', explanation['conditions'][0])
