from copy import deepcopy
import json
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest
from resilience_data import build_network
from resilience_globe import build_network_globe
from simulation.resilience import calculate_supply_shock
from ui.selection import select_flow_process


ROOT = Path(__file__).resolve().parents[1]


class UIReadabilityReviewTests(unittest.TestCase):
    def test_unmapped_intermediate_does_not_hide_mapped_related_routes(self):
        network = build_network()
        result = calculate_supply_shock(network)
        before_network, before_result = deepcopy(network), deepcopy(result)
        figure = build_network_globe(network, result, focus='raw:quartz')
        paths = [trace for trace in figure.data if trace.meta and 'network_state' in trace.meta]
        self.assertTrue(any(not trace.meta['dimmed'] for trace in paths))
        self.assertTrue(any(trace.meta['dimmed'] for trace in paths))
        self.assertEqual(network, before_network)
        self.assertEqual(result, before_result)

    def test_deselecting_current_flow_pill_keeps_a_valid_shared_process(self):
        state = {'rr_process': '포토', 'rr_flow_process': '포토', 'rr_flow_picker': None}
        select_flow_process(state, 'rr_flow_picker')
        self.assertEqual(state['rr_flow_picker'], '포토')
        self.assertEqual(state['rr_process'], '포토')
        self.assertEqual(state['rr_flow_process'], '포토')

    def test_initial_detail_click_and_both_requested_scenarios_keep_shared_selection(self):
        app = AppTest.from_file(str(ROOT / 'tests/fixtures/panel_components.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=60)
        def pills(key):
            return next(item for item in app.get('button_group') if item.key == key)
        self.assertFalse(app.exception)
        self.assertEqual(pills('rr_process').value, '전체')
        self.assertIsNone(pills('rr_flow_picker').value)
        pills('rr_flow_picker').select('포토').run(timeout=60)
        self.assertEqual(pills('rr_process').value, '포토')
        for issue, processes in [('일본 포토레지스트 공급 100% 중단 30일', ['포토']),
                                 ('말라카 해협 봉쇄 30일', ['포토', '식각'])]:
            app.button[1].click().run(timeout=60)
            app.text_input(key='rr_issue_text').input(issue)
            app.button[-1].click().run(timeout=60)
            calculation = deepcopy(app.session_state['rr_result'])
            for process in processes:
                pills('rr_process').select(process).run(timeout=60)
                self.assertFalse(app.exception)
                self.assertEqual(pills('rr_flow_picker').value, process)
                self.assertEqual(app.session_state['rr_flow_data']['process'], process)
                figure = json.loads(app.get('plotly_chart')[0].proto.spec)
                self.assertEqual(figure['layout']['meta']['process'], process)
                self.assertTrue(any(process + ' 공정 공급망' in item.value for item in app.markdown))
                app.selectbox(key='rr_name_company').select('samsung').run(timeout=60)
                self.assertEqual(app.session_state['rr_flow_data']['selected'], 'samsung')
                company = app.session_state['rr_network']['entities']['samsung']
                self.assertTrue(any(company['name'] in item.value and company['map_location']['name'] in item.value
                                    for item in app.markdown if '선택 기업:' in item.value))
                flow_expander = next(item for item in app.expander if item.label == '공정 상세 흐름 · 추가 정보')
                self.assertFalse(flow_expander.proto.expanded)
                self.assertEqual(app.session_state['rr_result'], calculation)
        pills('rr_process').select('전체').run(timeout=60)
        self.assertIsNone(pills('rr_flow_picker').value)
        pills('rr_flow_picker').select('식각').run(timeout=60)
        self.assertEqual(pills('rr_process').value, '식각')
        self.assertFalse(app.exception)
