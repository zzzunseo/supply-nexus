from copy import deepcopy
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
from streamlit.testing.v1 import AppTest
from flow_data import build_flow
from flow_selection import related_paths, flow_emphasis
from resilience_data import build_network
from resilience_globe import build_network_globe
from simulation.resilience import calculate_supply_shock
from ui.flow_svg import render_flow_svg
from ui.selection import select_globe_event


class FlowSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()
        cls.result = calculate_supply_shock(cls.network)

    def test_bidirectional_paths_exclude_siblings_and_terminate_cycles(self):
        edges = [dict(zip(('from', 'to'), pair)) for pair in
                 [('a', 'm'), ('m', 'p'), ('b', 'p'), ('p', 'c'), ('c', 'p')]]
        nodes, selected = related_paths(edges, {'m'})
        self.assertEqual(nodes, {'a', 'm', 'p', 'c'})
        self.assertEqual(selected, {0, 1, 3, 4})

    def test_material_selection_includes_supplier_and_recipient_without_mutation(self):
        flow = build_flow(self.network, self.result, '포토')
        selected = flow['columns'][1]['cards'][0]['node_id']
        flow = build_flow(self.network, self.result, '포토', selected)
        before = deepcopy(flow)
        cards, edges = flow_emphasis(flow)
        self.assertTrue(any(card['id'] in cards for card in flow['columns'][0]['cards']))
        self.assertTrue(any(card['id'] in cards for card in flow['columns'][3]['cards']))
        self.assertLess(len(cards), sum(len(col['cards']) for col in flow['columns']))
        root = ET.fromstring(render_flow_svg(flow))
        self.assertNotIn('onclick', render_flow_svg(flow))
        paths = root.findall('{http://www.w3.org/2000/svg}path')
        self.assertTrue(any(path.get('stroke-width') == '3.2' for path in paths))
        self.assertTrue(any(path.get('opacity') == '.18' for path in paths))
        self.assertEqual(flow, before)

    def test_company_seeds_both_display_columns_and_invalid_selection_shows_all(self):
        flow = build_flow(self.network, self.result, '포토', 'samsung')
        cards, _ = flow_emphasis(flow)
        self.assertTrue(all(card['id'] in cards for column in flow['columns'] for card in column['cards']
                            if card['node_id'] == 'samsung'))
        flow = build_flow(self.network, self.result, '포토', 'missing')
        self.assertEqual(len(flow_emphasis(flow)[0]), sum(len(col['cards']) for col in flow['columns']))

    def test_globe_focus_has_bright_and_dim_routes(self):
        figure = build_network_globe(self.network, self.result, focus='samsung')
        paths = [trace for trace in figure.data if trace.meta and 'network_state' in trace.meta]
        self.assertTrue(any(trace.meta['dimmed'] and trace.opacity == .12 for trace in paths))
        self.assertTrue(any(not trace.meta['dimmed'] and trace.opacity == .98 for trace in paths))

    def test_chart_callback_changes_focus_and_ignores_invalid_or_stale_events(self):
        state = {'rr_focus': 'samsung', 'rr_globe_click': {'picked': 'tsmc'}}
        select_globe_event(state, self.network['entities'])
        self.assertEqual(state['rr_focus'], 'tsmc')
        for value in (None, 'missing', ['samsung']):
            state['rr_globe_click']['picked'] = value
            select_globe_event(state, self.network['entities'])
            self.assertEqual(state['rr_focus'], 'tsmc')

    def test_material_box_chart_focus_and_process_change_stay_synchronized(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=60)
        material = build_flow(self.network, self.result)['columns'][1]['cards'][0]['node_id']
        app.selectbox(key='rr_name_company').select(material).run(timeout=60)
        self.assertEqual(app.session_state['rr_focus'], material)
        self.assertEqual(app.session_state['rr_flow_data']['selected'], material)
        app.session_state['rr_focus'] = 'tsmc'
        app.run(timeout=60)
        self.assertEqual(app.selectbox(key='rr_name_company').value, 'tsmc')
        app.selectbox(key='rr_name_company').select('samsung').run(timeout=60)
        app.run(timeout=60)
        self.assertEqual(app.session_state['rr_focus'], 'samsung')
        app.session_state['rr_flow_process'] = '식각'
        app.run(timeout=60)
        self.assertEqual(app.selectbox(key='rr_name_company').value, 'samsung')
        self.assertEqual(len(app.exception), 0)
