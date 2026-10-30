from copy import deepcopy
import json
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from resilience_data import build_network
from simulation.resilience import calculate_supply_shock, interpret_issue
from simulation.reporting import score_view, period_bottleneck
from ui.calculation import calculate_sensitivity
from ui.process_comparison import comparison_rows, report_payload
from ui.timeline import build_timeline

ROOT = Path(__file__).resolve().parents[1]


class ProcessReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()

    def run_issue(self, text, horizon=None, inventory=True, bypass=True):
        event = interpret_issue(text, self.network)
        return calculate_supply_shock(self.network, [event], horizon or event['days'], inventory, bypass)

    def test_material_shortage_keeps_customer_views_separate_and_mean_is_fifty(self):
        result=self.run_issue('머크 박막 전구체 공급 중단 30일',inventory=False,bypass=False)
        process='증착·이온주입'
        self.assertEqual(score_view(result,'samsung')['scores'][process],100)
        self.assertEqual(score_view(result,'tsmc')['scores'][process],0)
        self.assertEqual(score_view(result,'worst')['scores'][process],0)
        self.assertEqual(score_view(result,'mean')['scores'][process],50)
        self.assertEqual(result['scores']['금속배선'],100)

    def test_symmetric_partial_and_simultaneous_material_shocks(self):
        event=dict(kind='supply',targets=['mix:samsung:oxygen'],rate=.5,days=30)
        result=calculate_supply_shock(self.network,[event],30,False,False)
        self.assertEqual(score_view(result,'samsung')['overall'],50)
        self.assertEqual(score_view(result,'tsmc')['overall'],100)
        self.assertEqual(score_view(result,'mean')['overall'],75)
        event=dict(kind='supply',targets=['upstream:ceria'],rate=.75,days=30)
        result=calculate_supply_shock(self.network,[event],30,False,False)
        self.assertEqual(score_view(result,'worst')['overall'],25)
        self.assertEqual(score_view(result,'mean')['overall'],25)

    def test_unsupported_processes_are_none_and_never_in_mean_denominator(self):
        result = self.run_issue('TSMC 공급 중단 30일')
        self.assertIsNone(score_view(result, 'samsung')['scores']['패키징'])
        self.assertIsNone(score_view(result, 'tsmc')['average_scores']['패키징'])
        self.assertIsNone(score_view(result, 'ase')['scores']['포토'])
        self.assertIsNone(score_view(result, 'mean')['scores']['패키징'])
        self.assertNotIn('패키징', score_view(result, 'samsung')['first_hit'])
        rows = comparison_rows(result)
        self.assertEqual(rows[-1]['삼성전자'], '— 미산정')
        self.assertTrue(all(row['등록 기업 수'] == 2 for row in rows))
        self.assertEqual(len(result['company_processes']['samsung']), 7)
        self.assertEqual(result['company_processes']['ase'], ['패키징'])

    def test_packaging_mean_uses_ase_and_amkor_only(self):
        network=deepcopy(self.network)
        key='test:ase:material'
        network['nodes'][key]=dict(network['nodes']['upstream:tin'],id=key,requires=[],scope='core',inventory_days=0,alt_vendor=None)
        network['nodes'][network['operations'][('ase','패키징')]]['requires'].append(key)
        result=calculate_supply_shock(network,[dict(kind='supply',targets=[key],rate=1,days=30)],30,False,False,scopes=['package_tin'])
        self.assertEqual(score_view(result,'ase')['scores']['패키징'],0)
        self.assertEqual(score_view(result,'amkor')['scores']['패키징'],100)
        self.assertEqual(score_view(result,'mean')['scores']['패키징'],50)
        self.assertEqual(score_view(result,'mean')['scores']['포토'],100)

    def test_daily_recovery_and_first_hits_are_specific_to_each_view(self):
        result = self.run_issue('머크 박막 전구체 공급 중단 3일', horizon=60, inventory=False, bypass=False)
        mean = score_view(result, 'mean')
        tsmc = score_view(result, 'tsmc')
        samsung = score_view(result, 'samsung')
        self.assertTrue(all(row['증착·이온주입'] == 50 for row in mean['timeline'][:3]))
        self.assertTrue(all(row['증착·이온주입'] == 100 for row in mean['timeline'][3:]))
        self.assertEqual(mean['first_hit']['증착·이온주입'], 1)
        self.assertEqual(tsmc['first_hit']['증착·이온주입'], 1)
        self.assertEqual(samsung['first_hit'], {})
        self.assertAlmostEqual(mean['average_scores']['증착·이온주입'], 97.5)
        self.assertAlmostEqual(period_bottleneck(mean), 97.5)
        self.assertEqual(mean['overall'], 100)
        self.assertEqual(len(tsmc['timeline']), 60)

    def test_company_specific_coverage_is_not_copied_from_worst_view(self):
        result = calculate_supply_shock(self.network)
        self.assertIn('포토', score_view(result, 'samsung')['incomplete_processes'])
        samsung_gaps = score_view(result, 'samsung')['incomplete_processes']['포토']
        tsmc_gaps = score_view(result, 'tsmc')['incomplete_processes'].get('포토', [])
        self.assertTrue(any(':photoresist:' in key for key in samsung_gaps))
        self.assertFalse(any(':photoresist:' in key for key in tsmc_gaps))
        self.assertFalse(tsmc_gaps)
        self.assertIn('산화', score_view(result, 'tsmc')['incomplete_processes'])
        self.assertIn('식각', score_view(result, 'tsmc')['incomplete_processes'])
        self.assertIn('패키징', score_view(result, 'ase')['incomplete_processes'])
        self.assertNotIn('패키징', score_view(result, 'samsung')['incomplete_processes'])
        self.assertEqual(score_view(result, 'worst')['incomplete_processes'], result['incomplete_processes'])

    def test_worst_view_matches_all_legacy_statistics_exactly(self):
        result = self.run_issue('일본 포토레지스트 공급 중단 30일')
        worst = score_view(result, 'worst')
        for key in ('scores', 'overall', 'timeline', 'first_hit', 'average_scores'):
            self.assertEqual(worst[key], result[key])
        with self.assertRaises(ValueError):
            score_view(result, 'unregistered-company')

    def test_timeline_uses_selected_values_and_keeps_missing_process_blank(self):
        result = self.run_issue('머크 박막 전구체 공급 중단 30일', inventory=False, bypass=False)
        for key, expected in [('samsung', 100), ('tsmc', 0), ('mean', 50)]:
            figure = build_timeline(score_view(result, key))
            photo = next(t for t in figure.data if t.mode == 'lines+markers' and t.legendgroup == '증착·이온주입')
            self.assertEqual(set(photo.y), {expected})
        figure = build_timeline(score_view(result, 'samsung'))
        package = next(t for t in figure.data if t.legendgroup == '패키징')
        self.assertTrue(all(value is None for value in package.y))
        self.assertIn('미산정', package.name)

    def test_sensitivity_reports_both_aggregations_and_uses_period_means(self):
        events = [interpret_issue('머크 박막 전구체 공급 중단 3일', self.network)]
        rows = calculate_sensitivity(self.network, events, 60, False, False, [])
        self.assertEqual(rows[0]['overall'], 100)
        self.assertEqual(rows[0]['mean_overall'], 100)
        self.assertAlmostEqual(rows[0]['average'], 95)
        self.assertAlmostEqual(rows[0]['mean_average'], 97.5)
        network = deepcopy(self.network)
        for node in network['nodes'].values():
            if node.get('scope', 'core') == 'core':
                node['inventory_days'] *= 0.5
        direct = calculate_supply_shock(network, events, 60,False,False)
        self.assertAlmostEqual(rows[1]['mean_average'], period_bottleneck(score_view(direct, 'mean')))

    def test_report_export_preserves_nulls_scope_and_event_duration(self):
        result = self.run_issue('TSMC 공급 중단 3일', horizon=60)
        events = [interpret_issue('TSMC 공급 중단 3일', self.network)]
        payload = json.loads(json.dumps(report_payload(result, events), ensure_ascii=False))
        self.assertEqual(payload['duration_days'], 60)
        self.assertEqual(payload['events'][0]['days'], 3)
        self.assertIsNone(payload['process_views']['samsung']['scores']['패키징'])
        self.assertEqual(len(payload['company_names']), 4)
        self.assertIn('생산량/시장점유율 가중평균 아님', payload['aggregation_note'])

    def test_reporting_keeps_inventory_and_reserve_boundary_exact(self):
        def node(**values):
            fields = dict(requires=[], inventory_days=0, alt_vendor=None, alt_capacity=0, scope='core')
            fields.update(values)
            return fields
        network = dict(nodes={'pool': node(), 'a': node(inventory_days=2, alt_vendor='pool', alt_capacity=0.2), 'b': node()}, process_outputs={'p': ['a', 'b']})
        before = deepcopy(network)
        events = [dict(kind='supply', targets=['a'], rate=0.5, days=6)]
        result = calculate_supply_shock(network, events, 6)
        self.assertEqual([row['p'] for row in result['timeline'][:4]], [100] * 4)
        self.assertTrue(all(abs(row['p'] - 70) < 1e-7 for row in result['timeline'][4:]))
        self.assertTrue(all(abs(row['p'] - 85) < 1e-7 for row in score_view(result, 'mean')['timeline'][4:]))
        self.assertEqual(result['first_hit']['p'], 5)
        self.assertAlmostEqual(result['nodes']['a']['stock_remaining'], 0)
        self.assertAlmostEqual(result['nodes']['a']['primary'], 0.5)
        self.assertAlmostEqual(result['nodes']['a']['backup'], 0.2)
        self.assertEqual(network, before)

    def test_app_switches_chart_and_opens_company_comparison_without_exception(self):
        app = AppTest.from_file(str(ROOT / 'app.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        app.text_input(key='rr_issue_text').input('머크 박막 전구체 공급 중단 30일')
        app.button[-1].click().run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        app.selectbox(key='rr_score_view').select('samsung').run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state['rr_score_view'], 'samsung')
        rendered = '\n'.join(element.value for element in app.markdown)
        self.assertIn('삼성전자 100*', rendered)
        self.assertIn('TSMC 0*', rendered)
        self.assertIn('일별 삼성전자', rendered)
        next(b for b in app.button if b.label == '기업별 공정 점수·모델 범위').click().run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any('SK하이닉스·인텔·마이크론 등은 미포함' in item.value for item in app.caption))


if __name__ == '__main__':
    unittest.main()
