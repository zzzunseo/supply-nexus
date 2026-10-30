from copy import deepcopy
import json
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest
from flow_data import build_flow
from resilience_data import build_network
from resilience_globe import build_network_globe, process_edges, entity_rate
from simulation.resilience import calculate_supply_shock, interpret_issue
from ui.selection import select_flow_process, select_globe_process


ROOT = Path(__file__).resolve().parents[1]


class ProcessGlobeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()
        cls.normal = calculate_supply_shock(cls.network)

    def test_all_eight_processes_and_malacca_filter_out_other_process_routes(self):
        event = interpret_issue('말라카 해협 봉쇄 30일', self.network)
        for result in (self.normal, calculate_supply_shock(self.network, [event], 30)):
            for process in self.network['processes']:
                with self.subTest(process=process, outage=bool(result['first_hit'])):
                    needed, edges = process_edges(self.network, result, process)
                    flow = build_flow(self.network, result, process)
                    self.assertTrue(edges)
                    self.assertTrue(all(key in needed for edge in edges for key in edge.get('logistics_via', [])))
                    self.assertTrue(all(card['node_id'] in needed for col in flow['columns'] for card in col['cards']))
                    self.assertTrue(all(not edge['processes'] or process in edge['processes'] for edge in edges))
                    figure = build_network_globe(self.network, result, process=process)
                    self.assertEqual(figure.layout.meta['process'], process)
                    eligible = {edge['id'] for edge in edges}
                    self.assertTrue(set(figure.layout.meta['display_edge_ids']) <= eligible)
                    self.assertTrue(any(trace.meta and 'network_state' in trace.meta for trace in figure.data))

    def test_eds_does_not_include_photo_or_etching_companies(self):
        figure = build_network_globe(self.network, self.normal, process='EDS')
        marker_ids = {key for trace in figure.data if trace.customdata is not None for key in trace.customdata}
        self.assertIn('advantest', marker_ids)
        self.assertIn('teradyne', marker_ids)
        self.assertFalse(marker_ids.intersection({'jsr', 'tok', 'lam', 'asml'}))

    def test_selected_process_enables_mapped_upstream_routes_and_keeps_exclusions(self):
        needed, edges = process_edges(self.network, self.normal, '포토')
        figure = build_network_globe(self.network, self.normal, process='포토')
        displayed = set(figure.layout.meta['display_edge_ids'])
        self.assertTrue(any(edge['kind'] == 'upstream' and edge['id'] in displayed for edge in edges))
        references = [trace for trace in figure.data if trace.meta and trace.meta.get('network_state') == 'reference']
        self.assertTrue(references)
        self.assertTrue(all(trace.line.dash == 'dot' for trace in references))

    def test_selected_process_marker_score_ignores_other_operation_shortage(self):
        result = deepcopy(self.normal)
        photo = self.network['operations'][('samsung', '포토')]
        etch = self.network['operations'][('samsung', '식각')]
        result['nodes'][photo]['effective'] = 1
        result['nodes'][etch]['effective'] = 0
        self.assertEqual(entity_rate('samsung', self.network, result, '포토'), 1)
        self.assertEqual(entity_rate('samsung', self.network, result, '전체'), 0)

    def test_port_detour_stays_in_selected_process_and_inputs_remain_unchanged(self):
        network = deepcopy(self.network)
        network['port_detours']['logistics:kaohsiung'].update(enabled=True, capacity_units=100)
        event = interpret_issue('가오슝항 폐쇄 30일', network)
        result = calculate_supply_shock(network, [event], 30)
        needed, _ = process_edges(network, result, '포토')
        self.assertIn('logistics:keelung', needed)
        before_network, before_result = deepcopy(network), deepcopy(result)
        figure = build_network_globe(network, result, process='포토')
        self.assertTrue(any(trace.meta and trace.meta.get('network_state') == 'bypass' for trace in figure.data))
        self.assertEqual(network, before_network)
        self.assertEqual(result, before_result)

    def test_process_callbacks_synchronize_in_both_directions(self):
        state = {'rr_process': '식각', 'rr_flow_process': '포토'}
        select_globe_process(state)
        self.assertEqual(state['rr_flow_process'], '식각')
        state['rr_flow_process'] = '포토'
        select_flow_process(state)
        self.assertEqual(state['rr_process'], '포토')
        state['rr_process'] = '전체'
        select_globe_process(state)
        self.assertEqual(state['rr_flow_process'], '포토')

    def test_app_globe_and_flow_process_controls_sync_without_changing_results(self):
        app = AppTest.from_file(str(ROOT / 'tests/fixtures/panel_components.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=60)
        self.assertEqual(len(app.exception), 0)
        before = deepcopy(app.session_state['rr_result'])
        def pills(key):
            return next(item for item in app.get('button_group') if item.key == key)
        self.assertEqual(pills('rr_process').value, '전체')
        pills('rr_process').select('포토').run(timeout=60)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(pills('rr_flow_picker').value, '포토')
        self.assertEqual(app.session_state['rr_flow_data']['process'], '포토')
        chart = app.get('plotly_chart')[0]
        self.assertEqual(json.loads(chart.proto.spec)['layout']['meta']['process'], '포토')
        pills('rr_flow_picker').select('식각').run(timeout=60)
        self.assertEqual(pills('rr_process').value, '식각')
        self.assertEqual(app.session_state['rr_result'], before)
        app.selectbox(key='rr_name_company').select('lam').run(timeout=60)
        pills('rr_process').select('EDS').run(timeout=60)
        self.assertEqual(len(app.exception), 0)
        self.assertIsNone(app.session_state['rr_focus'])
        self.assertNotIn('lam', app.selectbox(key='rr_name_company').options)
        pills('rr_process').select('전체').run(timeout=60)
        self.assertEqual(len(app.exception), 0)
        self.assertIsNone(pills('rr_flow_picker').value)
        self.assertEqual(app.session_state['rr_flow_process'], 'EDS')
