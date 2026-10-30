from copy import deepcopy
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from resilience_data import build_network
from ui.demo import presentation_result
from ui.logistics_demo import demo_cases
from ui.demo_scenarios import selected_case,choices,connections
from ui.response_review import review_profile,review_payload
from ui.impact_explanation import build_explanation,explanation_markdown,annotate_processes


class ImpactExplanationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.network=build_network()

    def test_every_company_and_product_has_only_its_registered_processes(self):
        for category in ('기업','소재'):
            for target,_ in choices(self.network,category):
                case=selected_case(self.network,category,target,'공급 중단')
                analysis=build_explanation(self.network,case,review_profile(self.network,case))
                rows=[r for r in connections(self.network) if (r['supplier'] if category=='기업' else r['target'])==target]
                self.assertEqual(set(analysis['processes']),{p for r in rows for p in r['processes']})
                self.assertIsNone(analysis['time_value']);self.assertIsNone(analysis['cost_value'])
                self.assertTrue(analysis['impacts'])

    def test_photoresist_is_photo_not_all_downstream_and_euv_candidates_match_catalog(self):
        case=demo_cases()[1]
        analysis=build_explanation(self.network,case,review_profile(self.network,case))
        self.assertEqual(analysis['processes'],['포토'])
        self.assertIn('도포',analysis['impacts'][0]['use'])
        self.assertIn('막두께',analysis['impacts'][0]['reason'])
        euv=build_explanation(self.network,case,review_profile(self.network,case,'EUV'))
        self.assertTrue(any(c['name']=='FUJIFILM' for c in euv['candidates']))
        self.assertFalse(any('Dongjin' in c['name'] for c in euv['candidates']))
        self.assertTrue(all('생산·출하 중단 자체는 해결하지 못함' in p['purpose'] for p in euv['ports']))

    def test_port_has_separate_procurement_and_routing_with_unpriced_time_breakdown(self):
        case=dict(demo_cases()[2],percent=100)
        profile=review_profile(self.network,case)
        analysis=build_explanation(self.network,case,profile)
        self.assertEqual(analysis['processes'],['포토'])
        self.assertTrue(any('동진' in c['name'] or 'Dongjin' in c['name'] for c in analysis['candidates']))
        self.assertEqual(analysis['ports'][0]['alternate'],'기룽항')
        self.assertIn('별도 확인',analysis['candidates'][0]['condition'])
        self.assertEqual(len(analysis['time_rows']),3);self.assertEqual(len(analysis['cost_rows']),3)
        report=explanation_markdown(case,analysis,profile)
        self.assertIn('실제 일수·금액: 미산정',report)
        self.assertIn('가정이며 실제',report)
        self.assertIn('통화',report)

    def test_equipment_and_tariff_do_not_claim_immediate_production_loss(self):
        case=selected_case(self.network,'기업','asml','공급 중단')
        equipment=build_explanation(self.network,case,review_profile(self.network,case))
        self.assertTrue(equipment['equipment'])
        self.assertIn('기존 설치 장비의 즉시 정지',equipment['impacts'][0]['reason'])
        case=selected_case(self.network,'소재','supply:jsr:photoresist','관세 부과')
        tariff=build_explanation(self.network,case,review_profile(self.network,case))
        self.assertTrue(tariff['tariff']);self.assertFalse(tariff['candidates'])
        self.assertIn('생산 감소를 산정하지 않습니다',tariff['impacts'][0]['reason'])

    def test_map_process_badges_and_compact_app_report_render(self):
        case=demo_cases()[1];result=presentation_result(self.network)
        raw=review_payload(self.network,result,case);saved=deepcopy(raw)
        mapped=annotate_processes(self.network,raw,case)
        self.assertEqual(next(m for m in mapped['markers'] if m['id']=='tsmc')['process_label'],'포토')
        self.assertEqual(raw,saved)
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        for case in demo_cases():
            if any(b.key=='demo_back_impact' for b in app.button):app.button(key='demo_back_impact').click().run()
            if any(b.key=='demo_previous' for b in app.button):app.button(key='demo_previous').click().run()
            app.selectbox(key='demo_case').select(next(i for i,c in enumerate(demo_cases()) if c['id']==case['id'])).run()
            app.button(key='demo_apply').click().run();app.button(key='demo_next').click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.session_state.demo_explanation['impacts'])
            self.assertTrue(any(e.label=='상세 해석 · 시간·비용 · 근거' for e in app.expander))
