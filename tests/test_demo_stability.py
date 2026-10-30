from copy import deepcopy
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from resilience_data import build_network
from ui.demo_session import choose_case,commit_case,reset_presentation,initialize_presentation,clear_selection
from ui.demo_interaction import prepare_map,accept_pick,selection_description
from ui.logistics_demo import demo_cases
from ui.demo import demo_results
from ui.response_review import review_payload,review_profile


class PresentationStabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.network=build_network();cls.cases=demo_cases()

    def test_case_switch_reset_and_duplicate_submission_are_atomic(self):
        state={'rr_events':[{'keep':'detailed'}],'demo_review_product':'EUV','demo_show_candidate':False}
        initialize_presentation(state,self.cases)
        self.assertTrue(commit_case(state,self.network,self.cases[1],60,100))
        rev=state['demo_revision'];state['demo_transitioning']=False
        self.assertFalse(commit_case(state,self.network,self.cases[1],60,100))
        self.assertEqual(state['demo_revision'],rev)
        state.update(demo_review_product='EUV',demo_inspection={'old':True},demo_review={'old':True})
        choose_case(state,self.cases,2)
        self.assertIsNone(state['demo_applied']);self.assertNotIn('demo_inspection',state)
        self.assertNotIn('demo_review',state);self.assertEqual(state['demo_days'],30)
        self.assertEqual(state['demo_review_product'],'전체 제품군')
        self.assertTrue(state['demo_show_candidate'])
        reset_presentation(state,self.cases)
        self.assertEqual(state['demo_case'],1);self.assertEqual(state['demo_step'],1)
        self.assertEqual(state['rr_events'],[{'keep':'detailed'}])
        old=deepcopy(state)
        self.assertFalse(commit_case(state,self.network,self.cases[0],0,100))
        self.assertEqual(state['demo_applied'],old['demo_applied'])

    def test_old_context_and_hidden_candidate_clicks_cannot_change_selection(self):
        case=self.cases[1];result=demo_results(self.network,None)
        state={'demo_revision':1,'demo_step':3,'demo_active_case_id':case['id']}
        data=prepare_map(review_payload(self.network,result,case,True,'ArF'),state)
        event={'kind':'marker','id':'dongjin','context':data['context']}
        self.assertTrue(accept_pick(state,event,data))
        data=prepare_map(data,state)
        detail=selection_description(data,case,review_profile(self.network,case,'ArF'))
        self.assertEqual(detail['role'],'alternative')
        self.assertIn('ArF',detail['subtitle'])
        clear_selection(state)
        self.assertFalse(accept_pick(state,event,data))
        euv=prepare_map(review_payload(self.network,result,case,True,'EUV'),state)
        forged=dict(event,context=euv['context'])
        self.assertFalse(accept_pick(state,forged,euv));self.assertNotIn('demo_inspection',state)
        state['demo_active_case_id']='wafer'
        self.assertFalse(accept_pick(state,dict(kind='marker',id='jsr',context=euv['context']),euv))

    def test_three_case_rehearsal_and_detail_mode_return(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        for case in self.cases:
            if any(b.key=='demo_back_impact' for b in app.button):app.button(key='demo_back_impact').click().run()
            if any(b.key=='demo_previous' for b in app.button):app.button(key='demo_previous').click().run()
            app.selectbox(key='demo_case').select(next(i for i,c in enumerate(demo_cases()) if c['id']==case['id'])).run()
            self.assertIsNone(app.session_state.demo_applied)
            app.button(key='demo_apply').click().run()
            revision=app.session_state.demo_revision
            app.button(key='demo_next').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state.demo_review['kind'],'logistics' if case.get('kind')=='logistics' else 'material')
            if case['id']=='photoresist':
                app.selectbox(key='demo_review_product').select('EUV').run()
                self.assertTrue(app.session_state.demo_review['candidate_eligible'])
                self.assertFalse(any(m['id']=='dongjin' for m in app.session_state.demo_current_map['markers']))
            self.assertGreaterEqual(app.session_state.demo_revision,revision)
        app.button(key='demo_map_mode').click().run()
        self.assertTrue(app.get('plotly_chart'));self.assertFalse(app.exception)
        app.button(key='demo_advanced').click().run()
        app.button(key='rr_back_demo').click().run()
        self.assertEqual(app.session_state.demo_case,len(self.cases)-1)
        self.assertEqual(app.session_state.demo_applied['id'],self.cases[-1]['id'])
        self.assertEqual(app.session_state.rr_events,[])
        app.button(key='demo_reset').click().run()
        self.assertEqual(app.session_state.demo_step,1)
        self.assertEqual(app.session_state.demo_case,1)
        self.assertEqual(app.session_state.demo_review_product,'전체 제품군')
        self.assertFalse(app.exception)
