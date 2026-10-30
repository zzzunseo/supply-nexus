import unittest
from streamlit.testing.v1 import AppTest
from ui.api_credentials import session_key

class CredentialsTest(unittest.TestCase):
    def test_migrate_working_key_and_clear(self):
        state={'research_secret':'working-test','alternative_key':'stale-test'}
        self.assertEqual(session_key(state),'working-test')
        state['ai_api_secret']=''
        self.assertEqual(session_key(state),'')

    def test_switch_and_edit_and_clear(self):
        app=AppTest.from_string("""
import streamlit as st
from ui.api_credentials import render_credentials,api_key
panel=st.radio('Panel',['research','alternative','factory'])
render_credentials(panel)
st.session_state['test_current']=api_key()
""").run()
        app.text_input[0].set_value('test-session-secret').run()
        for panel in ['alternative','factory','research']:
            app.radio[0].set_value(panel).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['test_current'],'test-session-secret')
        app.text_input[0].set_value('test-replacement').run()
        app.radio[0].set_value('factory').run()
        self.assertEqual(app.session_state['test_current'],'test-replacement')
        app.button[0].click().run()
        app.radio[0].set_value('alternative').run()
        self.assertEqual(app.session_state['test_current'],'')
        self.assertFalse(app.exception)

    def test_shared_model_survives_panel_switch(self):
        app=AppTest.from_string("""
import streamlit as st
from ui.api_credentials import render_model,api_model
if 'research_model' not in st.session_state: st.session_state.research_model='gpt-4.1-mini'
panel=st.radio('Panel',['research','alternative','factory'])
render_model(panel)
st.session_state['chosen_model']=api_model()
""").run()
        self.assertEqual(app.session_state['chosen_model'],'gpt-4.1-mini')
        app.text_input[0].set_value('gpt-4.1').run()
        for panel in ['alternative','factory','research']:
            app.radio[0].set_value(panel).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['chosen_model'],'gpt-4.1')

    def test_safe_429_diagnostics(self):
        import io,json
        from urllib.error import HTTPError
        from news.external_research import _request
        for code in ['insufficient_quota','organization_usage_limit_exceeded','rate_limit_exceeded']:
            calls=[]
            def transport(request,timeout):
                calls.append(1)
                body=json.dumps({'error':{'code':code,'type':'insufficient_quota','message':'secret-key-never-display'}}).encode()
                raise HTTPError(request.full_url,429,'Too many',{},io.BytesIO(body))
            with self.assertRaises(ValueError) as error:
                _request({'model':'gpt-4.1-mini','text':{'format':{'name':'product_comparison'}}},'secret-key-never-display',transport)
            self.assertIn('code: '+code,str(error.exception))
            self.assertIn('기업·소재 비교',str(error.exception))
            self.assertNotIn('secret-key-never-display',str(error.exception))
            self.assertEqual(len(calls),1)
