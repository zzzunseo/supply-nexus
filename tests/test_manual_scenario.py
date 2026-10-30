from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from resilience_data import build_network
from simulation.manual_scenario import build_manual_issue,cases_for
from simulation.resilience import calculate_supply_shock,apply_issue


class ManualScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.network=build_network()

    def test_registered_cases_validate_without_natural_language_or_defaults(self):
        for target,case,rate in [('jsr','공급 중단',1.),('supply:jsr:photoresist','공급 감소',.4),
                                 ('jsr','수출 제한',.4),('jsr','화재·사고에 따른 공급 차질',.4),
                                 ('logistics:kaohsiung','완전 봉쇄',1.),('logistics:malacca','부분 통항 제한',.4),
                                 ('jsr','관세 부과',.4)]:
            with self.subTest(case=case):
                parsed=build_manual_issue(self.network,target,case,60,40.)
                self.assertEqual(parsed['rate'],rate)
                self.assertEqual(parsed['days'],60)
                self.assertEqual(parsed['targets'],[target])
        for target,case,days,percent in [('made-up','공급 감소',30,20),('jsr','완전 봉쇄',30,20),
                                        ('logistics:kaohsiung','부분 통항 제한',30,100),
                                        ('jsr','공급 감소',30,float('nan')),('jsr','공급 중단',366,100)]:
            with self.subTest(case=case),self.assertRaises(ValueError):
                build_manual_issue(self.network,target,case,days,percent)

    def test_port_material_tariff_equipment_and_selective_restore_have_distinct_effects(self):
        base=calculate_supply_shock(self.network)
        tariff=build_manual_issue(self.network,'jsr','관세 부과',30,20.)
        equipment=build_manual_issue(self.network,'asml','공급 중단',30,100.)
        for parsed in (tariff,equipment):
            result=calculate_supply_shock(self.network,apply_issue([],parsed))
            self.assertEqual(result['scores'],base['scores'])
        port=build_manual_issue(self.network,'logistics:kaohsiung','완전 봉쇄',30,100.)
        events=apply_issue(apply_issue([],tariff),port)
        result=calculate_supply_shock(self.network,events)
        self.assertEqual(result['nodes']['logistics:kaohsiung']['effective'],0)
        self.assertLess(result['overall'],base['overall'])
        restored=apply_issue(events,build_manual_issue(self.network,'logistics:kaohsiung','이 대상 이슈 해제',30,0))
        self.assertEqual(len(restored),1)
        self.assertEqual(restored[0]['kind'],'tariff')
        material=build_manual_issue(self.network,'supply:jsr:photoresist','공급 감소',60,40.)
        self.assertEqual(apply_issue([],material)[0]['targets'],['supply:jsr:photoresist'])

    def test_ui_direct_selection_applies_immediately_and_restores_without_api(self):
        from streamlit.testing.v1 import AppTest
        with patch('news.scenario_llm.urlopen',side_effect=AssertionError('No API')) as api:
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
            app.session_state['rr_workspace_mode'] = '상세 모드'
            app.run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox(key='rr_chat_mode').value,'직접 조건 선택')
            app.radio(key='rr_manual_category').set_value('항만·해협').run(timeout=30)
            app.selectbox(key='rr_manual_target').set_value('logistics:kaohsiung').run(timeout=30)
            app.selectbox(key='rr_manual_case').set_value('부분 통항 제한').run(timeout=30)
            app.number_input(key='rr_manual_days').set_value(60)
            app.number_input(key='rr_manual_percent').set_value(40.)
            self.assertEqual(app.session_state['rr_events'],[])
            app.button(key='rr_manual_apply').click().run(timeout=30)
            self.assertFalse(app.exception)
            event=app.session_state['rr_events'][0]
            self.assertEqual((event['rate'],event['days']),(.4,60))
            self.assertEqual(app.session_state['rr_days'],60)
            app.selectbox(key='rr_manual_case').set_value('완전 봉쇄').run(timeout=30)
            app.button(key='rr_manual_apply').click().run(timeout=30)
            self.assertEqual(len(app.session_state['rr_events']),1)
            self.assertEqual(app.session_state['rr_result']['nodes']['logistics:kaohsiung']['effective'],0)
            app.selectbox(key='rr_manual_case').set_value('이 대상 이슈 해제').run(timeout=30)
            app.button(key='rr_manual_apply').click().run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['rr_events'],[])
            self.assertEqual(api.call_count,0)

    def test_country_filter_and_company_material_changes_never_apply_on_selection(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        app.selectbox(key='rr_manual_country').set_value('일본').run(timeout=30)
        app.selectbox(key='rr_manual_target').set_value('jsr').run(timeout=30)
        baseline=deepcopy(app.session_state['rr_result']['scores'])
        app.selectbox(key='rr_manual_case').set_value('관세 부과').run(timeout=30)
        app.number_input(key='rr_manual_percent').set_value(20.)
        app.button(key='rr_manual_apply').click().run(timeout=30)
        self.assertEqual(app.session_state['rr_events'][0]['kind'],'tariff')
        self.assertEqual(app.session_state['rr_result']['scores'],baseline)
        app.radio(key='rr_manual_category').set_value('소재').run(timeout=30)
        app.selectbox(key='rr_manual_target').set_value('supply:jsr:photoresist').run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state['rr_events']),1)
        self.assertEqual(app.session_state['rr_events'][0]['targets'],['jsr'])


if __name__=='__main__': unittest.main()
