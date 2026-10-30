from copy import deepcopy
import unittest

from resilience_data import build_network
from resilience_globe import build_globe, build_network_globe, COLORS
from simulation.resilience import calculate_supply_shock, interpret_issue


class NetworkGlobeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()
        cls.normal = calculate_supply_shock(cls.network)

    def test_default_overview_restores_real_connections_and_visible_names(self):
        figure = build_network_globe(self.network, self.normal)
        original = build_globe(self.network, self.normal, level='기업')
        paths = [trace for trace in figure.data if trace.meta and 'network_state' in trace.meta]
        self.assertEqual(len(paths), sum(trace.mode == 'lines' for trace in original.data))
        self.assertEqual({(tuple(trace.lat), tuple(trace.lon)) for trace in paths},
                         {(tuple(trace.lat), tuple(trace.lon)) for trace in original.data if trace.mode == 'lines'})
        labels = [text for trace in figure.data if trace.mode == 'text' for text in trace.text]
        self.assertTrue(any('삼성' in text for text in labels))
        self.assertTrue(any('TSMC' in text for text in labels))
        reference = [trace for trace in paths if trace.meta['network_state'] == 'reference']
        self.assertTrue(reference)
        self.assertTrue(all(trace.line.dash == 'dot' for trace in reference))

    def test_closure_keeps_closed_paths_and_adds_rings_at_the_existing_points(self):
        event = interpret_issue('말라카 해협 봉쇄 30일', self.network)
        result = calculate_supply_shock(self.network, [event], 30)
        figure = build_network_globe(self.network, result)
        stopped = [trace for trace in figure.data if trace.meta and trace.meta.get('network_state') == 'stopped']
        self.assertTrue(stopped)
        self.assertTrue(all(trace.line.dash == 'dash' for trace in stopped))
        rings = [trace for trace in figure.data if trace.uid and trace.uid.startswith('network-ring-')]
        self.assertTrue(rings)
        place = self.network['logistics']['logistics:malacca']
        self.assertTrue(any((place['lat'], place['lon']) in set(zip(trace.lat, trace.lon)) for trace in rings))

    def test_enabled_port_detour_has_strong_blue_paths_at_its_actual_waypoint(self):
        network = deepcopy(self.network)
        network['port_detours']['logistics:kaohsiung'].update(enabled=True, capacity_units=100)
        event = interpret_issue('가오슝항 폐쇄 30일', network)
        result = calculate_supply_shock(network, [event], 30)
        figure = build_network_globe(network, result)
        detours = [trace for trace in figure.data if trace.meta and trace.meta.get('network_state') == 'bypass']
        self.assertTrue(detours)
        self.assertTrue(all(trace.line.color == COLORS['bypass'] and trace.line.width == 4 for trace in detours))
        place = network['logistics']['logistics:keelung']
        self.assertTrue(any(any(abs(lat-place['lat']) < 1e-6 and abs(lon-place['lon']) < 1e-6
                                   for lat, lon in zip(trace.lat, trace.lon) if lat is not None)
                            for trace in detours))

    def test_visual_emphasis_does_not_change_network_or_calculation_results(self):
        network = deepcopy(self.network)
        result = deepcopy(self.normal)
        before_network = deepcopy(network)
        before_result = deepcopy(result)
        build_network_globe(network, result)
        self.assertEqual(network, before_network)
        self.assertEqual(result, before_result)


if __name__ == '__main__':
    unittest.main()
