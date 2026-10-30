from copy import deepcopy
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from streamlit.testing.v1 import AppTest

from flow_data import build_flow
from resilience_data import build_network
from resilience_globe import build_location_globe, location_numbers
from simulation.resilience import calculate_supply_shock, interpret_issue
from ui.flow_svg import render_flow_svg


ROOT = Path(__file__).resolve().parents[1]
NS = {'s': 'http://www.w3.org/2000/svg'}


class FlowUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()
        cls.normal = calculate_supply_shock(cls.network)

    def test_all_processes_and_malacca_svg_have_valid_cards_and_nonoverlapping_rows(self):
        event = interpret_issue('말라카 해협 봉쇄 30일', self.network)
        for result in (self.normal, calculate_supply_shock(self.network, [event], 30)):
            for process in self.network['processes']:
                with self.subTest(process=process, scenario=bool(result['first_hit'])):
                    flow = build_flow(self.network, result, process)
                    svg = ET.fromstring(render_flow_svg(flow))
                    groups = svg.findall('s:g', NS)
                    expected = {card['id']: card for col in flow['columns'] for card in col['cards']}
                    self.assertEqual({group.attrib['data-card-id'] for group in groups}, set(expected))
                    columns = {}
                    for group in groups:
                        card = expected[group.attrib['data-card-id']]
                        name = ''.join(text.text or '' for text in group.findall('s:text', NS)
                                       if text.attrib.get('class') == 'flow-name')
                        self.assertEqual(name, card['name'])
                        y = float(group.attrib['data-y'])
                        height = float(group.attrib['data-height'])
                        for text in group.findall('s:text', NS):
                            self.assertGreater(float(text.attrib['y']), y)
                            self.assertLess(float(text.attrib['y']), y + height)
                        columns.setdefault(group.attrib['data-x'], []).append((y, y + height))
                    for rows in columns.values():
                        rows.sort()
                        self.assertTrue(all(a[1] < b[0] for a, b in zip(rows, rows[1:])))

    def test_card_kinds_have_distinct_shapes_labels_and_numeric_state_without_clicks(self):
        svg = ET.fromstring(render_flow_svg(build_flow(self.network, self.normal)))
        for group in svg.findall('s:g', NS):
            kind = group.attrib['data-kind']
            texts = group.findall('s:text', NS)
            self.assertEqual(texts[0].text, {'company': '기업', 'material': '소재', 'process': '공정'}[kind])
            if kind == 'process':
                self.assertIsNotNone(group.find('s:polygon', NS))
            else:
                rectangle = group.find('s:rect', NS)
                self.assertEqual(rectangle.attrib['rx'], '14' if kind == 'material' else '0')
            status = texts[-1].text
            self.assertTrue('%' in status or '제외' in status or '미확인' in status)
        self.assertFalse(svg.findall('.//s:a', NS))
        self.assertFalse(svg.findall('.//s:script', NS))
        self.assertFalse(any(key.startswith('on') for element in svg.iter() for key in element.attrib))

    def test_empty_recipient_flow_displays_an_explicit_empty_message(self):
        network = deepcopy(self.network)
        network['process_outputs']['포토'] = []
        flow = build_flow(network, self.normal)
        svg = ET.fromstring(render_flow_svg(flow))
        self.assertFalse(svg.findall('s:g', NS))
        self.assertIn('해당 공정에 표시할 공급 관계가 없습니다.', ''.join(svg.itertext()))

    def test_long_names_are_preserved_and_markup_is_escaped(self):
        flow = build_flow(self.network, self.normal)
        card = flow['columns'][0]['cards'][0]
        card['name'] = '긴기업이름을생략없이표시합니다 Samsung Electronics <script>alert(1)</script> & 소재'
        svg = ET.fromstring(render_flow_svg(flow))
        group = next(group for group in svg.findall('s:g', NS)
                     if group.attrib['data-card-id'] == card['id'])
        name = ''.join(text.text or '' for text in group.findall('s:text', NS)
                       if text.attrib.get('class') == 'flow-name')
        self.assertEqual(name, card['name'])
        self.assertFalse(svg.findall('.//s:script', NS))

    def test_location_globe_contains_only_points_and_numbers(self):
        figure = build_location_globe(self.network, self.normal)
        self.assertTrue(figure.data)
        self.assertTrue(all(trace.mode == 'markers+text' for trace in figure.data))
        self.assertTrue(all(text.isdigit() for trace in figure.data for text in trace.text))
        numbers = location_numbers(self.network)
        self.assertEqual(numbers, location_numbers(deepcopy(self.network)))

    def test_selected_company_has_full_company_and_site_label(self):
        figure = build_location_globe(self.network, self.normal, focus='samsung')
        labels = [text for trace in figure.data if trace.mode == 'text' for text in trace.text]
        self.assertEqual(len(labels), 1)
        self.assertIn(self.network['entities']['samsung']['name'], labels[0])
        self.assertIn(self.network['entities']['samsung']['map_location']['name'], labels[0])

    def test_process_pills_switch_flow_without_changing_calculation(self):
        app = AppTest.from_file(str(ROOT / 'app.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        pills = next(item for item in app.get('button_group') if item.key == 'rr_flow_picker')
        self.assertEqual(pills.options, self.network['processes'])
        self.assertIsNone(pills.value)
        self.assertEqual(app.session_state['rr_flow_data']['process'], '포토')
        before = deepcopy(app.session_state['rr_result'])
        next(item for item in app.get('button_group') if item.key == 'rr_flow_picker').select('식각').run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state['rr_flow_data']['process'], '식각')
        self.assertEqual(app.session_state['rr_result'], before)

    def test_requested_issues_load_flow_with_zero_app_exceptions(self):
        app = AppTest.from_file(str(ROOT / 'app.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        for text, processes in [
            ('일본 포토레지스트 공급 100% 중단 30일', ['포토']),
            ('말라카 해협 봉쇄 30일', ['포토', '식각']),
        ]:
            app.button[1].click().run(timeout=30)
            app.text_input(key='rr_issue_text').input(text)
            app.button[-1].click().run(timeout=30)
            for process in processes:
                next(item for item in app.get('button_group') if item.key == 'rr_flow_picker').select(process).run(timeout=30)
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(app.session_state['rr_flow_data']['process'], process)
                self.assertTrue(app.session_state['rr_flow_data']['connections'])


if __name__ == '__main__':
    unittest.main()
