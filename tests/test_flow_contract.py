"""Integration contract requested before the SVG UI phase."""
from copy import deepcopy
import random
import unittest

from flow_data import build_flow
from resilience_data import build_network
from simulation.resilience import calculate_supply_shock, interpret_issue


class FlowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()
        cls.normal = calculate_supply_shock(cls.network)
        event = interpret_issue('말라카 해협 봉쇄 30일', cls.network)
        cls.malacca = calculate_supply_shock(cls.network, [event], 30)

    def flows(self):
        for label, result in [('normal', self.normal), ('malacca', self.malacca)]:
            for process in self.network['processes']:
                yield label, result, process

    def test_eight_processes_times_two_scenarios_generate_complete_columns(self):
        count = 0
        for label, result, process in self.flows():
            with self.subTest(scenario=label, process=process):
                flow = build_flow(self.network, result, process)
                self.assertEqual(flow['process'], process)
                self.assertEqual([column['id'] for column in flow['columns']],
                                 ['suppliers', 'materials', 'processes', 'recipients'])
                self.assertTrue(flow['connections'])
                count += 1
        self.assertEqual(count, 16)

    def test_every_connection_endpoint_exists_in_every_scenario(self):
        for label, result, process in self.flows():
            with self.subTest(scenario=label, process=process):
                flow = build_flow(self.network, result, process)
                ids = {card['id'] for column in flow['columns'] for card in column['cards']}
                for edge in flow['connections']:
                    self.assertIn(edge['from'], ids)
                    self.assertIn(edge['to'], ids)

    def test_empty_recipient_column_returns_empty_flow_and_clears_selection(self):
        network = deepcopy(self.network)
        network['process_outputs']['포토'] = []
        flow = build_flow(network, self.normal, '포토', selected='tsmc')
        self.assertEqual(len(flow['columns']), 4)
        self.assertTrue(all(not column['cards'] for column in flow['columns']))
        self.assertEqual(flow['connections'], [])
        self.assertIsNone(flow['selected'])

    def test_card_ids_are_stable_across_scenarios_repeated_calls_and_selection(self):
        def ids(flow):
            return [(column['id'], [card['id'] for card in column['cards']])
                    for column in flow['columns']]

        for process in self.network['processes']:
            with self.subTest(process=process):
                expected = ids(build_flow(self.network, self.normal, process))
                self.assertEqual(expected, ids(build_flow(self.network, self.normal, process)))
                self.assertEqual(expected, ids(build_flow(self.network, self.malacca, process)))
                self.assertEqual(expected, ids(build_flow(self.network, self.malacca, process, 'tsmc')))

    def test_sorting_is_deterministic_when_source_order_changes(self):
        shuffled = deepcopy(self.network)
        rng = random.Random(726)
        rng.shuffle(shuffled['visual_edges'])
        for node in shuffled['nodes'].values():
            if node.get('mode') != 'mix':
                rng.shuffle(node['requires'])
        shuffled['nodes'] = dict(reversed(list(shuffled['nodes'].items())))
        for label, result, process in self.flows():
            with self.subTest(scenario=label, process=process):
                self.assertEqual(build_flow(self.network, result, process),
                                 build_flow(shuffled, result, process))

    def test_all_sixteen_builds_leave_both_inputs_unchanged(self):
        network_before = deepcopy(self.network)
        normal_before = deepcopy(self.normal)
        malacca_before = deepcopy(self.malacca)
        for _, result, process in self.flows():
            build_flow(self.network, result, process)
        self.assertEqual(self.network, network_before)
        self.assertEqual(self.normal, normal_before)
        self.assertEqual(self.malacca, malacca_before)

    def test_excluded_etch_connections_include_unconfirmed_customer_gas_supply(self):
        expected = {'etch-tool:lam>samsung', 'etch-tool:lam>tsmc',
                    'product:supply:lam:etch-tool', 'etch-gas:airliquide>tsmc'}
        for result in (self.normal, self.malacca):
            flow = build_flow(self.network, result, '식각')
            excluded = {edge['source_edge_id']: edge for edge in flow['connections'] if edge['excluded']}
            self.assertEqual(set(excluded), expected)
            for edge in excluded.values():
                self.assertIs(edge['excluded'], True)
                self.assertEqual(edge['status'], 'excluded')
                self.assertIsNone(edge['reduction_pct'])
                self.assertTrue(edge['exclusion_reason'])

    def test_three_original_excluded_relationships_keep_their_decisions(self):
        cases = [('포토', 'photoresist:tok>samsung'),
                 ('포토', 'photoresist:jsr>samsung'),
                 ('식각', 'etch-tool:lam>samsung')]
        for process, relationship in cases:
            with self.subTest(relationship=relationship):
                flow = build_flow(self.network, self.malacca, process)
                edge = next(edge for edge in flow['connections']
                            if edge['source_edge_id'] == relationship)
                self.assertIs(edge['excluded'], True)
                self.assertFalse(self.network['relationship_decisions'][relationship]['included'])


if __name__ == '__main__':
    unittest.main()
