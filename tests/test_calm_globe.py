from copy import deepcopy
import unittest

from resilience_data import build_network
from resilience_globe import build_globe, build_network_globe, COLORS
from simulation.resilience import calculate_supply_shock, interpret_issue


class CalmGlobeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()
        cls.result = calculate_supply_shock(cls.network)

    def test_calm_overview_keeps_all_existing_paths_and_readable_route_hierarchy(self):
        reference = build_globe(self.network, self.result, level='기업')
        figure = build_network_globe(self.network, self.result)
        paths = [trace for trace in figure.data if trace.meta and 'network_state' in trace.meta]
        expected = {(tuple(trace.lat), tuple(trace.lon)) for trace in reference.data if trace.mode == 'lines'}
        self.assertEqual({(tuple(trace.lat), tuple(trace.lon)) for trace in paths}, expected)
        normal = [trace for trace in paths if trace.meta['network_state'] == 'normal']
        reference_paths = [trace for trace in paths if trace.meta['network_state'] == 'reference']
        self.assertTrue(normal)
        self.assertTrue(all(trace.line.width <= 1.5 and .65 <= trace.opacity <= .85 for trace in normal))
        self.assertTrue(all(trace.opacity < min(item.opacity for item in normal) for trace in reference_paths))
        labels = [text for trace in figure.data if trace.mode == 'text' for text in trace.text]
        self.assertLessEqual(len(labels), 10)
        self.assertFalse(figure.layout.geo.lonaxis.showgrid)
        self.assertFalse(figure.layout.geo.lataxis.showgrid)

    def test_material_focus_keeps_owner_label_and_a_distinct_selected_path(self):
        figure = build_network_globe(self.network, self.result, process='웨이퍼 제조',
                                     focus='supply:sumco:polished-wafer')
        labels = [text for trace in figure.data if trace.mode == 'text' for text in trace.text]
        self.assertLessEqual(len(labels), 8)
        self.assertTrue(any('SUMCO' in text for text in labels))
        paths = [trace for trace in figure.data if trace.meta and trace.meta.get('network_state') == 'normal']
        self.assertTrue(any(not trace.meta['dimmed'] and trace.line.width > 1.2 for trace in paths))
        self.assertTrue(any(trace.meta['dimmed'] and trace.opacity == .12 for trace in paths))

    def test_closure_still_has_red_dashed_paths_and_no_data_or_result_mutation(self):
        event = interpret_issue('말라카 해협 봉쇄 30일', self.network)
        result = calculate_supply_shock(self.network, [event], 30)
        before_network, before_result = deepcopy(self.network), deepcopy(result)
        figure = build_network_globe(self.network, result, process='웨이퍼 제조')
        stopped = [trace for trace in figure.data if trace.meta and trace.meta.get('network_state') == 'stopped']
        self.assertTrue(stopped)
        self.assertTrue(all(trace.line.color == COLORS['stopped'] and trace.line.dash == 'dash' for trace in stopped))
        self.assertEqual(self.network, before_network)
        self.assertEqual(result, before_result)
