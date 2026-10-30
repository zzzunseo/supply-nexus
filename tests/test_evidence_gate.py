from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from streamlit.testing.v1 import AppTest
from resilience_data import build_network
from resilience_globe import build_globe, entity_rate, COLORS
from simulation.evidence import relationship_decision
from simulation.resilience import calculate_supply_shock, interpret_issue
from ui.calculation import calculate_sensitivity
from ui.cards import advice_cards
from ui.settings_tabs import source_rows

ROOT = Path(__file__).resolve().parents[1]


class EvidenceGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()
        cls.original = json.loads((ROOT / 'data/demo.json').read_text(encoding='utf-8'))

    def variant(self, edits):
        original = deepcopy(self.original)
        for edge in original['edges']:
            edge.update(edits.get(edge['id'], {}))
        with TemporaryDirectory() as folder:
            Path(folder, 'demo.json').write_text(json.dumps(original, ensure_ascii=False), encoding='utf-8')
            return build_network(folder)

    def test_reference_and_historical_records_are_excluded_from_dag_and_logistics(self):
        network = self.network
        decisions = network['relationship_decisions']
        self.assertEqual(sum(d['included'] for d in decisions.values()), 24)
        excluded = [e for e in network['backbone'] if not decisions[e['id']]['included']]
        self.assertEqual(len(excluded), 20)
        self.assertEqual(sum(e['relationship_kind'] != 'supply' for e in excluded), 16)
        for edge in excluded:
            self.assertNotIn('route:' + edge['id'], network['nodes'])
            visual = next(e for e in network['visual_edges'] if e.get('backbone_id') == edge['id'])
            self.assertFalse(visual['calculation_included'])
            self.assertNotIn('transport_node', visual)
            self.assertNotIn('logistics_via', visual)
        self.assertEqual(network['backbone'], self.original['edges'])
        self.assertTrue(all(e['share_pct'] is None for e in network['backbone']))

    def test_missing_or_unknown_metadata_never_establishes_supply(self):
        good = next(e for e in self.original['edges'] if self.network['relationship_decisions'][e['id']]['included'])
        self.assertTrue(relationship_decision(good)[0])
        for field in ('relationship_kind', 'temporal_status', 'relationship_status', 'relationship_source'):
            for value in (None, '', 'future_unknown_value'):
                candidate = dict(good, **{field: value})
                self.assertFalse(relationship_decision(candidate)[0], (field, value))
        for temporal in ('historical', 'expired_certificate', 'planned'):
            self.assertFalse(relationship_decision(dict(good, temporal_status=temporal))[0])

    def test_reference_only_wafer_shock_does_not_enter_process_scores(self):
        event = dict(kind='supply', targets=['supply:samsung:processed-wafer', 'supply:tsmc:processed-wafer'], rate=1, days=30)
        baseline = calculate_supply_shock(self.network, duration_days=30, use_inventory=False, use_bypass=False)
        shocked = calculate_supply_shock(self.network, [event], 30, False, False)
        self.assertEqual(shocked['timeline'], baseline['timeline'])
        self.assertEqual(shocked['first_hit'], baseline['first_hit'])
        self.assertEqual(entity_rate('supply:samsung:processed-wafer', self.network, shocked), 1)
        figure = build_globe(self.network, shocked)
        markers = [t for t in figure.data if t.mode == 'markers' and 'samsung' in t.customdata]
        self.assertTrue(markers)
        self.assertTrue(all(t.marker.color == COLORS['normal'] for t in markers))
        for key in event['targets']:
            self.assertFalse(self.network['nodes'][key]['calculation_included'])

    def test_shared_product_can_supply_one_customer_without_inventing_another(self):
        event = dict(kind='supply', targets=['supply:merck:film-precursor'], rate=1, days=30)
        result = calculate_supply_shock(self.network, [event], 30, False, False)
        self.assertEqual(result['nodes']['operation:samsung:증착·이온주입']['effective'], 1)
        self.assertEqual(result['nodes']['operation:tsmc:증착·이온주입']['effective'], 0)
        self.assertNotIn('route:film-precursor:merck>samsung', self.network['nodes'])
        self.assertIn('route:film-precursor:merck>tsmc', self.network['nodes'])

    def test_remaining_suppliers_are_renormalized_without_unknown_share(self):
        excluded_id = 'oxygen:airproducts>samsung'
        self.assertIn(excluded_id, self.network['relationship_decisions'])
        network = self.variant({excluded_id: dict(relationship_kind='unconfirmed')})
        mix = network['nodes']['mix:samsung:oxygen']
        self.assertEqual(len(mix['requires']), 1)
        self.assertEqual(mix['weights'], [1.0])
        event = dict(kind='supply', targets=['supply:airliquide:oxygen'], rate=1, days=1)
        previous = calculate_supply_shock(self.network, [event], 1, False, False)
        corrected = calculate_supply_shock(network, [event], 1, False, False)
        self.assertEqual(previous['nodes']['mix:samsung:oxygen']['effective'], 0.5)
        self.assertEqual(corrected['nodes']['mix:samsung:oxygen']['effective'], 0)

    def test_missing_input_groups_are_traced_and_not_presented_as_complete(self):
        network = self.network
        gaps = network['coverage_gaps']
        self.assertTrue(any(g['company'] == 'samsung' and g['item_id'] == 'photoresist' for g in gaps))
        self.assertEqual({g['company'] for g in gaps if g['item_id'] == 'processed-wafer'}, {'ase', 'amkor'})
        self.assertNotIn('웨이퍼 제조', network['incomplete_processes'])
        self.assertIn('산화', network['incomplete_processes'])
        self.assertIn('포토', network['incomplete_processes'])
        self.assertNotIn('EDS', network['incomplete_processes'])
        self.assertIsNone(calculate_supply_shock(network)['scores']['EDS'])
        self.assertIn('패키징', network['incomplete_processes'])
        result = calculate_supply_shock(network)
        self.assertEqual(result['coverage_gaps'], gaps)
        self.assertEqual(result['incomplete_processes'], network['incomplete_processes'])
        result['coverage_gaps'].clear()
        self.assertTrue(network['coverage_gaps'])

    def test_reference_only_products_cannot_consume_shared_reserve(self):
        edits = {e['id']: dict(relationship_kind='unconfirmed') for e in self.original['edges'] if e['from'] == 'jsr'}
        network = self.variant(edits)
        product = network['nodes']['supply:jsr:photoresist']
        self.assertIsNone(product['alt_vendor'])
        self.assertEqual(product['alt_capacity'], 0)
        event = dict(kind='supply', targets=['supply:jsr:photoresist'], rate=1, days=30)
        result = calculate_supply_shock(network, [event], 30, False, True)
        self.assertEqual(result['nodes']['supply:jsr:photoresist']['backup'], 0)
        self.assertEqual(result['overall'], 100)

    def test_reference_arcs_remain_grey_dotted_without_supply_percent(self):
        event = dict(kind='supply', targets=['supply:merck:film-precursor'], rate=1, days=30)
        result = calculate_supply_shock(self.network, [event], 30, False, False)
        card = advice_cards(self.network, result)
        self.assertEqual(result['overall'],0)
        self.assertIn('0%</strong>', card)
        self.assertNotIn('부족 없음', card)
        for level in ('소재 연쇄', '기업', '국가'):
            figure = build_globe(self.network, result, level=level)
            reference = [t for t in figure.data if t.mode == 'lines' and t.line.color == COLORS['reference']]
            self.assertTrue(reference, level)
            for trace in reference:
                self.assertEqual(trace.line.dash, 'dot')
                for tip in trace.text:
                    if tip:
                        self.assertIn('공급 계산 제외', tip)
                        self.assertNotIn('기존 경로', tip)
                        self.assertNotIn('%', tip)

    def test_bypass_uses_eligible_customer_only_and_stays_blue_through_open_port(self):
        event = interpret_issue('일본 포토레지스트 공급 중단 30일', self.network)
        result = calculate_supply_shock(self.network, [event], 30)
        figure = build_globe(self.network, result)
        blue = [t for t in figure.data if t.mode == 'lines' and t.line.color == COLORS['bypass']]
        self.assertTrue(blue)
        for trace in blue:
            for tip in trace.text:
                if tip:
                    self.assertIn('TSMC', tip)
                    self.assertNotIn('Samsung', tip)

    def test_source_rows_expose_inclusion_and_exclusion_reasons(self):
        rows = source_rows(self.network)
        self.assertEqual(len(rows), 44)
        self.assertEqual(sum(row['계산포함'] for row in rows), 19)
        self.assertTrue(all(row['계산판정'] for row in rows))

    def test_sensitivity_scales_direct_single_stage_assumptions(self):
        def node(**values):
            return dict(requires=[], inventory_days=0, alt_vendor=None, alt_capacity=0, scope='core', **values)
        network = dict(nodes={'pool': node(), 'input': node()}, process_outputs={'process': ['input']})
        network['nodes']['input'].update(alt_vendor='pool', alt_capacity=0.6)
        events = [dict(kind='supply', targets=['input'], rate=1, days=30)]
        rows = calculate_sensitivity(network, events, 30, False, True, [])
        self.assertEqual(rows[0]['overall'], 60)
        self.assertEqual(rows[3]['overall'], 30)
        self.assertAlmostEqual(rows[4]['overall'], 90)

    def test_app_explains_why_reference_only_wafer_input_has_no_supply_effect(self):
        app = AppTest.from_file(str(ROOT / 'app.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        app.text_input(key='rr_issue_text').input('삼성 가공 웨이퍼 공급 중단 30일')
        app.button[-1].click().run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertIn('참고 관계에만 연결된', app.session_state['rr_reply'])
        self.assertEqual(app.session_state['rr_result']['overall'], 100)
        self.assertIn('패키징', app.session_state['rr_result']['incomplete_processes'])

    def test_app_shows_partial_model_and_coverage_warning_without_exception(self):
        app = AppTest.from_file(str(ROOT / 'app.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        rendered = '\n'.join(element.value for element in app.markdown)
        self.assertIn('최저 소재 충족도', rendered)
        self.assertIn('범위 불완전 6/8', rendered)
        self.assertIn('소재 경로 19 · 참고 25', rendered)
        self.assertIn('100도 정상 보장이 아닙니다', rendered)
        self.assertNotIn('생산 공급 충족도 100%', rendered)


if __name__ == '__main__':
    unittest.main()
