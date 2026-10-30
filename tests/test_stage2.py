from copy import deepcopy
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from resilience_data import build_network
from simulation.resilience import calculate_supply_shock, interpret_issue, apply_issue
from ui.calculation import calculate_sensitivity
from ui.issues import change_issue_duration, delete_issue
from ui.timeline import build_timeline

ROOT = Path(__file__).resolve().parents[1]


class Stage2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()

    def event(self, text):
        return apply_issue([], interpret_issue(text, self.network))

    def test_short_issue_recovers_with_sixty_day_observation(self):
        events = self.event('일본 포토레지스트 공급 중단 3일')
        result = calculate_supply_shock(self.network, events, 60, False, False)
        self.assertEqual(events[0]['days'], 3)
        self.assertEqual(len(result['timeline']), 60)
        self.assertTrue(all(row['포토'] == 0 for row in result['timeline'][:3]))
        self.assertTrue(all(row['포토'] == 100 for row in result['timeline'][3:]))

    def test_long_issue_is_not_truncated_to_horizon(self):
        events = self.event('일본 포토레지스트 공급 중단 90일')
        before = deepcopy(events)
        result = calculate_supply_shock(self.network, events, 20)
        self.assertEqual(len(result['timeline']), 20)
        self.assertEqual(result['scores']['포토'], 60)
        self.assertEqual(events, before)

    def test_different_issue_durations_and_same_target_replacement(self):
        events = self.event('일본 포토레지스트 공급 중단 3일')
        events = apply_issue(events, interpret_issue('독일 NF3 공급 중단 60일', self.network))
        self.assertEqual([e['days'] for e in events], [3, 60])
        events = apply_issue(events, interpret_issue('일본 포토레지스트 공급 중단 20일', self.network))
        self.assertEqual(sorted(e['days'] for e in events), [20, 60])
        self.assertEqual(len(events), 2)

    def test_delete_and_edit_are_independent_and_do_not_mutate(self):
        events = self.event('일본 포토레지스트 공급 중단 30일')
        events += self.event('독일 NF3 공급 중단 60일')
        before = deepcopy(events)
        edited = change_issue_duration(events, 0, 3)
        self.assertEqual([e['days'] for e in edited], [3, 60])
        deleted = delete_issue(edited, 0)
        self.assertEqual(deleted, [events[1]])
        self.assertEqual(events, before)
        self.assertEqual(delete_issue(deleted, 0), [])
        for days in (0, 366, 2.5, True):
            with self.assertRaises(ValueError):
                change_issue_duration(events, 0, days)
        with self.assertRaises(ValueError):
            delete_issue(events, -1)

    def test_sensitivity_matches_direct_recalculation_and_preserves_inputs(self):
        network = deepcopy(self.network)
        events = self.event('일본 포토레지스트 공급 중단 30일')
        before = deepcopy(network)
        event_before = deepcopy(events)
        rows = calculate_sensitivity(network, events, 30, True, True, [])
        self.assertEqual(network, before)
        self.assertEqual(rows[0]['overall'], 60)
        reduced = deepcopy(network)
        for node in reduced['nodes'].values():
            if node.get('scope', 'core') == 'core':
                node['alt_capacity'] *= 0.5
        expected = calculate_supply_shock(reduced, events, 30)
        self.assertAlmostEqual(rows[3]['overall'], expected['overall'])
        self.assertAlmostEqual(rows[3]['delta'], expected['overall'] - rows[0]['overall'])
        for node in network['nodes'].values():
            if node.get('scope', 'core') == 'core':
                node['inventory_days'] = min(365, node['inventory_days'] * 1.5)
        direct = calculate_supply_shock(network, events, 30)
        self.assertEqual(rows[2]['overall'], direct['overall'])
        expected_average = sum(min(row[p] for p in direct['scores'] if row[p] is not None) for row in direct['timeline']) / 30
        self.assertAlmostEqual(rows[2]['average'], expected_average)
        self.assertEqual(events, event_before)
        self.assertEqual(self.network, before)

    def test_sensitivity_disabled_controls_and_recovery(self):
        events = self.event('일본 포토레지스트 공급 중단 30일')
        rows = calculate_sensitivity(self.network, events, 60, False, False, [])
        self.assertTrue(all(row['overall'] == 100 for row in rows))
        self.assertTrue(all(row['delta'] == row['average_delta'] == 0 for row in rows))
        rows = calculate_sensitivity(self.network, events, 60, True, True, [])
        self.assertTrue(all(row['overall'] == 100 for row in rows))
        self.assertNotEqual(rows[1]['average'], rows[0]['average'])

    def test_timeline_has_eight_named_styles_and_first_hit_markers(self):
        result = calculate_supply_shock(self.network, self.event('일본 포토레지스트 공급 중단 30일'), 30)
        fig = build_timeline(result)
        lines = [trace for trace in fig.data if trace.mode == 'lines+markers']
        self.assertEqual([t.name.removesuffix(' *').removesuffix(' · 미산정') for t in lines], list(result['scores']))
        self.assertEqual(len({(t.line.dash, t.marker.symbol) for t in lines}), 8)
        hits = [trace for trace in fig.data if trace.mode == 'markers']
        self.assertEqual(len(hits), len(result['first_hit']))
        self.assertTrue(all(list(t.x) == [15] for t in hits))
        self.assertEqual(tuple(fig.layout.yaxis.range), (0, 100))

    def test_app_observation_period_does_not_change_issue_default_or_duration(self):
        app = AppTest.from_file(str(ROOT / 'tests/fixtures/panel_components.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        app.number_input(key='rr_days').set_value(60).run(timeout=30)
        app.text_input(key='rr_issue_text').input('일본 포토레지스트 공급 중단 3일')
        app.button[-1].click().run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state['rr_days'], 60)
        self.assertEqual(app.session_state['rr_events'][0]['days'], 3)
        self.assertEqual(len(app.session_state['rr_result']['timeline']), 60)
        app.text_input(key='rr_issue_text').input('일본 포토레지스트 공급 중단')
        app.button[-1].click().run(timeout=30)
        self.assertEqual(app.session_state['rr_events'][0]['days'], 30)
        self.assertEqual(app.session_state['rr_days'], 60)

    def test_app_issue_editor_and_deletion_recalculate(self):
        app = AppTest.from_file(str(ROOT / 'tests/fixtures/panel_components.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        app.text_input(key='rr_issue_text').input('일본 포토레지스트 공급 중단 30일')
        app.button[-1].click().run(timeout=30)
        next(b for b in app.button if '기간 수정 / 삭제' in b.label).click().run(timeout=30)
        next(n for n in app.number_input if n.label == '이슈 지속 기간 · 일').set_value(3).run(timeout=30)
        next(b for b in app.button if b.label == '기간 저장').click().run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state['rr_events'][0]['days'], 3)
        self.assertEqual(app.session_state['rr_result']['overall'], 100)
        next(b for b in app.button if '기간 수정 / 삭제' in b.label).click().run(timeout=30)
        next(b for b in app.button if b.label == '삭제').click().run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state['rr_events'], [])
        self.assertEqual(app.session_state['rr_days'], 30)


if __name__ == '__main__':
    unittest.main()

