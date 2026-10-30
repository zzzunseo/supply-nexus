from copy import deepcopy
import unittest
from resilience_data import build_network
from simulation.resilience import calculate_supply_shock, interpret_issue
from ui.explanation import current_explanation


class ExplanationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()

    def test_no_issue_describes_registered_calculation_without_claiming_real_normal_operation(self):
        result = calculate_supply_shock(self.network)
        text = current_explanation(self.network, result, {})
        self.assertIn('등록 소재에서 공급 부족이 계산되지 않았습니다', text)
        self.assertNotIn('정상 가동입니다', text)

    def test_shock_explains_actual_score_and_first_hit_without_changing_results(self):
        event = interpret_issue('일본 포토레지스트 공급 100% 중단 30일', self.network)
        result = calculate_supply_shock(self.network, [event], 30)
        before = deepcopy(result)
        text = current_explanation(self.network, result, {'rr_process': '포토', 'rr_events': [event]})
        self.assertIn(f"{result['scores']['포토']:.0f}/100", text)
        self.assertIn(f"{min(result['first_hit'].values())}일째", text)
        self.assertEqual(result, before)

    def test_unregistered_process_is_not_presented_as_zero_or_full_supply(self):
        result = calculate_supply_shock(self.network)
        text = current_explanation(self.network, result, {'rr_process': '포토', 'rr_score_view': 'ase'})
        self.assertIn('활성 소재 입력이 미등록이므로 미산정', text)
        self.assertNotIn('포토의 공급 충족도는 100', text)

    def test_selected_material_explains_the_actual_inventory_and_backup_contributions(self):
        result = calculate_supply_shock(self.network)
        focus = 'supply:sumco:polished-wafer'
        text = current_explanation(self.network, result, {'rr_focus': focus})
        self.assertIn('재고 보완', text)
        self.assertIn('우회 보완', text)
        self.assertIn(f"{result['nodes'][focus]['effective']*100:.0f}%", text)


class ExplanationPanelTests(unittest.TestCase):
    def test_details_start_collapsed_and_invalid_issue_keeps_explanation_and_existing_events(self):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'tests/fixtures/panel_components.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        details = {'공정·기업별 상세 점수', '가정 비교 · 계산 근거', '입력·적용 기록', '시연 예시 선택'}
        self.assertTrue(details.issubset({item.label for item in app.expander}))
        self.assertTrue(all(not item.proto.expanded for item in app.expander if item.label in details))
        app.text_input(key='rr_issue_text').set_value('공급 차질')
        next(button for button in app.button if button.label == '이슈 적용 → 소재 계산').click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state['rr_error'])
        self.assertEqual(app.session_state['rr_events'], [])
        self.assertTrue(any('rr-input-error' in item.value for item in app.markdown))
        self.assertTrue(any('rr-explanation' in item.value for item in app.markdown))
