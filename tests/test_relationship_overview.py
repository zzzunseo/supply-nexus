from pathlib import Path
from copy import deepcopy
import unittest
from company_relationships import relationship_rows,target_coverage,variant_scopes
from resilience_data import build_network
from simulation.resilience import calculate_supply_shock


class RelationshipOverviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.network=build_network()

    def test_company_coverage_distinguishes_no_score_change_reasons(self):
        expected={'samsung':'입고 소재 관측 기업','asml':'장비·참고 관계','five-n':'제품군 선택 필요',
                  'heraeus':'제품군 선택 필요','dongjin':'대체 공급 전용','jsr':'소재 공급 계산'}
        for key,status in expected.items():
            with self.subTest(key=key): self.assertEqual(target_coverage(self.network,key)['status'],status)
        self.assertEqual(set(variant_scopes(self.network,'five-n')),{'gallium','germanium'})

    def test_flow_direction_process_scope_and_references_are_kept_distinct(self):
        network=deepcopy(self.network)
        jsr=relationship_rows(network,target='jsr')
        self.assertTrue(any(r['recipient_id']=='tsmc' and r['included'] for r in jsr))
        self.assertTrue(any(r['recipient_id']=='samsung' and not r['included'] for r in jsr))
        self.assertTrue(all(r['recipient_id']=='tsmc' for r in relationship_rows(network,target='tsmc',direction='공급받는 경로')))
        self.assertTrue(all('포토' in r['processes'] for r in relationship_rows(network,target='tsmc',process='포토')))
        self.assertTrue(any(not r['active'] for r in relationship_rows(network,target='heraeus')))
        self.assertEqual(network,self.network)

    def test_explicit_specialty_selection_activates_company_path_and_changes_engine(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        app.selectbox(key='rr_manual_target').set_value('five-n').run(timeout=30)
        self.assertTrue(app.button(key='rr_manual_apply').disabled)
        app.selectbox(key='rr_manual_variant').set_value('gallium').run(timeout=30)
        app.number_input(key='rr_manual_days').set_value(60)
        app.button(key='rr_manual_apply').click().run(timeout=30)
        self.assertFalse(app.exception)
        result=app.session_state['rr_result']
        self.assertIn('gallium',result['scopes'])
        self.assertNotIn('germanium',result['scopes'])
        baseline=calculate_supply_shock(self.network,duration_days=60,scopes=['gallium','package_tin'])
        self.assertLess(result['overall'],baseline['overall'])
        app.selectbox(key='rr_manual_target').set_value('heraeus').run(timeout=30)
        app.selectbox(key='rr_manual_variant').set_value('package_gold').run(timeout=30)
        app.button(key='rr_manual_apply').click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertIn('package_gold',app.session_state['rr_result']['scopes'])

    def test_overview_paginates_without_modifying_events_and_selects_on_globe(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        app.button(key='rr_supply_overview').click().run(timeout=30)
        app.selectbox(key='rr_relationship_target').set_value('tsmc').run(timeout=30)
        before=deepcopy(app.session_state['rr_events'])
        self.assertGreater(len(app.session_state['rr_relationship_rows']),4)
        app.number_input(key='rr_relationship_page').set_value(2).run(timeout=30)
        app.selectbox(key='rr_relationship_process').set_value('포토').run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['rr_events'],before)
        self.assertEqual(app.number_input(key='rr_relationship_page').value,1)
        next(b for b in app.button if b.label=='지구본에서 선택').click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['rr_focus'],'tsmc')
        self.assertEqual(app.selectbox(key='detail_focus').value,'tsmc')
        app.run(timeout=30)
        self.assertEqual(app.session_state['rr_focus'],'tsmc')
        app.button(key='detail_process_0').click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertIsNone(app.session_state['rr_focus'])
        self.assertFalse(app.session_state['rr_relationship_open'])


if __name__=='__main__': unittest.main()
