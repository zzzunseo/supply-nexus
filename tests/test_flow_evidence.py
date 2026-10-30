from copy import deepcopy
import unittest
import xml.etree.ElementTree as ET
from flow_data import build_flow
from resilience_data import build_network
from simulation.resilience import calculate_supply_shock, interpret_issue
from ui.flow_svg import render_flow_svg, material_details


NS = {'s': 'http://www.w3.org/2000/svg'}


class FlowEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()
        cls.normal = calculate_supply_shock(cls.network)

    def test_material_values_are_copied_from_result_and_inputs_are_unchanged(self):
        result = deepcopy(self.normal)
        base = build_flow(self.network, result)
        key = base['columns'][1]['cards'][0]['node_id']
        result['nodes'][key].update(stock_remaining=3.25, backup=.12345)
        before = deepcopy(result)
        network = deepcopy(self.network)
        flow = build_flow(network, result)
        card = next(card for card in flow['columns'][1]['cards'] if card['node_id'] == key)
        self.assertEqual(card['evidence']['stock_remaining_days'], 3.25)
        self.assertEqual(card['evidence']['backup_active_pct'], 12.345)
        self.assertEqual(card['evidence']['metric_node_id'], key)
        self.assertEqual(result, before)
        self.assertEqual(network, self.network)

    def test_process_first_hit_is_never_used_as_a_material_depletion_date(self):
        result = deepcopy(self.normal)
        result['first_hit'] = {'포토': 7}
        flow = build_flow(self.network, result)
        for card in flow['columns'][1]['cards']:
            self.assertNotIn('depletion_day', card['evidence'])
            self.assertFalse(any('소진' in text for text in material_details(card)))
        self.assertNotIn('D+7', render_flow_svg(flow))

    def test_missing_invalid_or_nonfinite_metrics_show_unknown_not_zero(self):
        flow = build_flow(self.network, self.normal)
        key = flow['columns'][1]['cards'][0]['node_id']
        for invalid in (None, True, -1, float('nan'), float('inf'), '7'):
            result = deepcopy(self.normal)
            result['nodes'][key].update(stock_remaining=invalid, backup=invalid)
            card = next(card for card in build_flow(self.network, result)['columns'][1]['cards']
                        if card['node_id'] == key)
            self.assertIsNone(card['evidence']['stock_remaining_days'])
            self.assertIsNone(card['evidence']['backup_active_pct'])
            self.assertTrue(any('가정 재고 잔여 미확인' == detail for detail in material_details(card)))

    def test_disabled_bypass_is_zero_and_settings_do_not_become_active_values(self):
        event = interpret_issue('일본 포토레지스트 공급 100% 중단 30일', self.network)
        result = calculate_supply_shock(self.network, [event], 30, use_bypass=False)
        for card in build_flow(self.network, result)['columns'][1]['cards']:
            if card['status'] != 'excluded':
                self.assertEqual(card['evidence']['backup_active_pct'], 0)

    def test_excluded_material_does_not_display_simulated_stock_or_backup(self):
        network = deepcopy(self.network)
        key = build_flow(network, self.normal)['columns'][1]['cards'][0]['node_id']
        network['nodes'][key]['calculation_included'] = False
        card = next(card for card in build_flow(network, self.normal)['columns'][1]['cards']
                    if card['node_id'] == key)
        self.assertIsNone(card['evidence']['stock_remaining_days'])
        self.assertIsNone(card['evidence']['backup_active_pct'])
        self.assertEqual(material_details(card), ['재고·우회 계산 제외'])

    def test_each_excluded_and_assumed_connection_has_its_own_text_badge(self):
        flow = build_flow(self.network, self.normal, '식각')
        root = ET.fromstring(render_flow_svg(flow))
        badges = {(element.get('data-edge-badge'), element.get('data-badge'))
                  for element in root.findall('s:rect', NS) if element.get('data-edge-badge')}
        paths = {element.get('data-connection-id'): element for element in root.findall('s:path', NS)}
        self.assertEqual(sum(edge['excluded'] for edge in flow['connections']), 4)
        for edge in flow['connections']:
            self.assertEqual((edge['id'], '제외') in badges, edge['excluded'])
            self.assertEqual((edge['id'], '가정') in badges, edge['assumption'])
            self.assertEqual('stroke-dasharray' in paths[edge['id']].attrib, edge['excluded'])

    def test_badges_fit_between_columns_and_do_not_overlap_each_other(self):
        event = interpret_issue('말라카 해협 봉쇄 30일', self.network)
        for result in (self.normal, calculate_supply_shock(self.network, [event], 30)):
            for process in self.network['processes']:
                root = ET.fromstring(render_flow_svg(build_flow(self.network, result, process)))
                rectangles = [element for element in root.findall('s:rect', NS) if element.get('data-edge-badge')]
                for i, a in enumerate(rectangles):
                    ax, ay = float(a.get('x')), float(a.get('y'))
                    self.assertLessEqual(ax + float(a.get('width')), 720)
                    for b in rectangles[i+1:]:
                        bx, by = float(b.get('x')), float(b.get('y'))
                        overlap = ax < bx+30 and bx < ax+30 and ay < by+14 and by < ay+14
                        self.assertFalse(overlap, (process, a.attrib, b.attrib))
