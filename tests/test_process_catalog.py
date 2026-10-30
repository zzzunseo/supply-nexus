import unittest
from copy import deepcopy
from pathlib import Path
from streamlit.testing.v1 import AppTest
from resilience_data import build_network
from ui.process_catalog import load_process_catalog,group_offerings,process_map_payload
from ui.response_review import review_payload
from ui.demo import presentation_result
from ui.demo_scenarios import selected_case


class ProcessCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.network=build_network()

    def test_all_groups_keep_sources_and_no_fabricated_capacity_or_contracts(self):
        catalog=load_process_catalog();original=deepcopy(self.network)
        self.assertEqual(len(catalog['stages']),8)
        self.assertEqual(len(catalog['groups']),40)
        for gid in catalog['groups']:
            entries=group_offerings(self.network,gid)
            self.assertTrue(entries,gid)
            for e in entries:
                self.assertTrue(e['sources']);self.assertTrue(all(s.startswith('https://') for s in e['sources']))
                if e['location']:
                    self.assertTrue(e['location']['location_source'])
            origin=entries[0]['name']
            data,_,_=process_map_payload(self.network,gid,origin)
            ids={m['id'] for m in data['markers']}
            self.assertEqual(len(ids),len(data['markers']))
            self.assertTrue(all(m['score'] is None for m in data['markers']))
            for route in data['routes']:
                self.assertIn(route['start'],ids);self.assertIn(route['end'],ids)
                if route['kind']=='alternative':self.assertNotEqual(route['start'],entries[0]['map_id'])
        self.assertEqual(self.network,original)

    def test_new_user_list_companies_have_locations(self):
        catalog=load_process_catalog()
        found={e['name']:e for gid in catalog['groups'] for e in group_offerings(self.network,gid)}
        for name in ('Siltronic','SK siltron','Tokyo Electron','원익IPS','PSK','AP시스템','예스티','에스앤에스텍','에프에스티',
                     '브이엠','솔브레인','ENF테크놀로지','ASM','주성엔지니어링','유진테크','테스','케이씨텍',
                     '두산테스나','리노공업','와이씨','디아이','한미반도체','하나마이크론','네패스','SFA반도체','이오테크닉스'):
            self.assertTrue(found[name]['location'],name)

    def test_unrelated_process_roles_are_not_alternatives(self):
        names=lambda g:{e['name'] for e in group_offerings(self.network,g)}
        self.assertNotIn('PSK',names('oxidation-furnace'))
        self.assertNotIn('두산테스나',names('memory-tester'))
        self.assertNotIn('리노공업',names('memory-tester'))
        self.assertNotIn('한미반도체',names('osat'))
        self.assertNotIn('원익IPS',names('dry-etch'))
        data,_,_=process_map_payload(self.network,'euv-tool','ASML')
        self.assertFalse(any(r['kind']=='alternative' for r in data['routes']))

    def test_material_class_and_map_toggles(self):
        names=lambda g:{e['name'] for e in group_offerings(self.network,g)}
        self.assertTrue({'솔브레인','ENF테크놀로지','STELLA CHEMIFA'}<=names('hf'))
        self.assertTrue({'케이씨텍','솔브레인','Entegris'}<=names('cmp-tungsten'))
        names_euv={e['name'] for e in group_offerings(self.network,'photoresist','EUV')}
        self.assertIn('FUJIFILM',names_euv);self.assertNotIn('Dongjin Semichem',names_euv)
        before,_,_=process_map_payload(self.network,'dry-etch','브이엠',disrupted=False)
        after,_,_=process_map_payload(self.network,'dry-etch','브이엠')
        self.assertEqual(before['camera_context'],after['camera_context'])
        self.assertTrue(all(r['kind']=='primary' and r['status']=='normal' for r in before['routes']))
        comparison,_,_=process_map_payload(self.network,'dry-etch','브이엠',recipient=None)
        self.assertFalse(any(m['role']=='recipient' for m in comparison['markers']))
        self.assertTrue(all('비교선' in r['material'] for r in comparison['routes']))

    def test_existing_main_wafer_map_includes_new_siltronic_location(self):
        case=selected_case(self.network,'기업','sumco','공급 중단')
        data=review_payload(self.network,presentation_result(self.network),case)
        self.assertTrue(any(m['name']=='Siltronic' for m in data['markers']))

    def test_main_direct_company_selection_without_process_navigation(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        app.selectbox(key='demo_company_direct').select('브이엠').run()
        self.assertFalse(app.exception)
        self.assertFalse(any(r.key=='process_map_scope' for r in app.radio))
        data=app.session_state.demo_current_map
        self.assertIn('브이엠',data['scenario_summary'])
        self.assertEqual(len([r for r in data['routes'] if r['kind']=='alternative']),3)
        camera=data['camera_context']
        app.selectbox(key='process_candidate').select('Tokyo Electron').run()
        data=app.session_state.demo_current_map
        marker=next(m for m in data['markers'] if m['name']=='Tokyo Electron')
        self.assertEqual(data['selected']['id'],marker['id'])
        self.assertEqual(data['camera_context'],camera)
        self.assertIn('Tokyo Electron',app.session_state.process_candidate_explanation['title'])
        self.assertEqual(app.selectbox(key='demo_company_direct').value,'브이엠')
        app.toggle(key='process_cut').set_value(False).run()
        self.assertFalse(any(r['kind']=='alternative' for r in app.session_state.demo_current_map['routes']))
        app.selectbox(key='demo_company_direct').select('솔브레인').run()
        self.assertEqual(app.selectbox(key='process_group').value,'hf')
        app.selectbox(key='process_group').select('cmp-tungsten').run()
        app.toggle(key='process_cut').set_value(True).run()
        self.assertFalse(app.exception)
        self.assertTrue(any(m['name']=='케이씨텍' for m in app.session_state.demo_current_map['markers']))
        self.assertEqual(app.session_state.rr_events,[])
        app.button(key='demo_reset').click().run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.selectbox(key='demo_company_direct').value)

    def test_main_ui_process_map_switches_stages_and_keeps_detailed_state_clean(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        app.radio(key='process_map_scope').set_value('공정별 기업·소재').run()
        for stage,gid,origin in [('식각·세정','dry-etch','브이엠'),('증착·이온주입','ald','주성엔지니어링'),('EDS·검사','memory-tester','와이씨'),('패키징','osat','하나마이크론')]:
            app.selectbox(key='process_stage').select(stage).run()
            app.selectbox(key='process_group').select(gid).run()
            app.selectbox(key='process_origin').select(origin).run()
            self.assertFalse(app.exception)
            self.assertTrue(any(r['kind']=='alternative' for r in app.session_state.process_current_map['routes']))
            self.assertEqual(app.session_state.rr_events,[])
        app.toggle(key='process_cut').set_value(False).run()
        self.assertTrue(all(r['kind']=='primary' for r in app.session_state.process_current_map['routes']))
        app.button(key='demo_map_mode').click().run()
        self.assertTrue(app.get('plotly_chart'));self.assertFalse(app.exception)
        app.radio(key='process_map_scope').set_value('등록 공급관계').run()
        app.button(key='demo_apply').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any(r['kind']=='alternative' for r in app.session_state.demo_current_map['routes']))
