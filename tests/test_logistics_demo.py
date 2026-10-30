from copy import deepcopy
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from resilience_data import build_network
from ui.demo import demo_results
from ui.logistics_demo import demo_cases,detour_summary
from ui.night_globe import globe_payload


class LogisticsDemoTests(unittest.TestCase):
    def test_overview_has_multiple_evidenced_vendors_and_assumed_routes(self):
        from ui.logistics_demo import port_overview,port_scope
        from ui.response_review import review_payload
        n=build_network(); c=dict(next(c for c in demo_cases() if c['id']=='kaohsiung'),percent=100)
        markers,routes,scope=port_overview(n,c)
        self.assertEqual((scope['suppliers'],scope['customers'],scope['materials']),(6,1,6))
        self.assertEqual(len({m['id'] for m in markers if m['role']=='supplier'}),6)
        self.assertTrue(all(r['assumed'] and r['material'] for r in routes))
        self.assertEqual({r['recipient'] for r in scope['rows']},{'tsmc'})
        self.assertEqual(port_scope(n,'unregistered')['rows'],[])
        result=demo_results(n,c,False,False)
        shown=review_payload(n,result,c,True)
        hidden=review_payload(n,result,c,False)
        self.assertEqual(len([r for r in shown['routes'] if r['kind']=='detour']),7)
        self.assertFalse(any(r['kind']=='detour' for r in hidden['routes']))

    def test_detour_changes_delivery_without_changing_saved_network(self):
        n=build_network(); original=deepcopy(n)
        c=dict(next(c for c in demo_cases() if c['id']=='kaohsiung'),percent=100)
        baseline=demo_results(n,c,False,False)
        response=demo_results(n,c,False,False,True)
        self.assertEqual(baseline['process_views']['tsmc']['scores']['포토'],0)
        self.assertEqual(response['process_views']['tsmc']['scores']['포토'],50)
        summary=detour_summary(n,response,c)
        self.assertEqual(summary['extra_days'],3)
        self.assertEqual(summary['delivered'],.5)
        data=globe_payload(n,response,c,True,True)
        detours=[r for r in data['routes'] if r['kind']=='detour']
        self.assertIn(dict(start='jsr',end='logistics:keelung',kind='detour'),detours)
        self.assertIn(dict(start='logistics:keelung',end='tsmc',kind='detour'),detours)
        self.assertFalse(any(m['role']=='alternative' for m in data['markers']))
        off=globe_payload(n,baseline,c,True,True)
        self.assertFalse(any(r['kind']=='detour' for r in off['routes']))
        self.assertEqual(n,original)

    def test_dispatch_is_not_reported_as_arrival_and_partial_blockade_works(self):
        n=build_network(); c=dict(next(c for c in demo_cases() if c['id']=='kaohsiung'),percent=100,days=1)
        early=demo_results(n,c,False,False,True)
        summary=detour_summary(n,early,c)
        self.assertGreater(summary['dispatched'],0)
        self.assertEqual(summary['delivered'],0)
        self.assertEqual(early['process_views']['tsmc']['scores']['포토'],0)
        partial=demo_results(n,dict(c,percent=40,days=30),False,False,True)
        self.assertGreater(partial['process_views']['tsmc']['scores']['포토'],0)

    def test_port_case_is_selectable_and_review_toggle_only_changes_visibility(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        app.selectbox(key='demo_case').select(2).run()
        self.assertEqual(app.number_input(key='demo_days').value,30)
        app.button(key='demo_apply').click().run()
        app.button(key='demo_next').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('화물 취급 적합성' in m.value and '미확인' in m.value for m in app.markdown))
        self.assertEqual(app.session_state.demo_review['candidate_id'],'logistics:keelung')
        self.assertFalse(any('우회 첫 도착' in m.value for m in app.markdown))
        assumptions=next(e for e in app.expander if e.label=='기존 모델의 시연 가정값 · 실측 아님')
        self.assertTrue(any('추가 3일' in m.value for m in assumptions.markdown))
        app.toggle(key='demo_show_candidate').set_value(False).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.demo_review['kind'],'logistics')
        self.assertEqual(app.session_state.rr_events,[])
