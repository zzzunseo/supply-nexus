from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from news.article_chat import respond
from resilience_data import build_network


class ConversationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network=build_network()

    def test_context_filter_and_fact_question_keep_original_evidence(self):
        context,reply=respond(self.network,{},'JSR 화재 예시를 설명해줘')
        self.assertIn('가상 기사',reply)
        before=deepcopy(context)
        filtered,reply=respond(self.network,context,'그중 삼성과 연결된 경로만 보여줘')
        self.assertTrue(filtered['review']['routes'])
        self.assertTrue(all('Samsung' in r['recipient'] for r in filtered['review']['routes']))
        self.assertEqual(context,before)
        grounded,reply=respond(self.network,filtered,'공급 영향은 확인됐어?')
        self.assertIn('아직 확인되지 않았다',reply)
        self.assertEqual(grounded['review']['routes'],filtered['review']['routes'])
        restored,_=respond(self.network,grounded,'전체 경로')
        self.assertEqual(restored['review']['routes'],before['review']['routes'])
        mapped,_=respond(self.network,filtered,'지도 보여줘')
        self.assertEqual(mapped['action'],'open_map')
        after,_=respond(self.network,mapped,'공급 영향은 확인됐어?')
        self.assertNotIn('action',after)

    def test_missing_rate_is_not_assumed_and_complete_proposal_stays_unapplied(self):
        context,_=respond(self.network,{},'JSR 화재 예시')
        pending,reply=respond(self.network,context,'만약 출하가 20일 중단되면?')
        self.assertIn('감소율',reply)
        self.assertIsNone(pending['pending']['rate'])
        self.assertNotIn('proposal',pending)
        ready,reply=respond(self.network,pending,'40%')
        self.assertEqual(ready['proposal']['parsed']['rate'],0.4)
        self.assertEqual(ready['proposal']['parsed']['days'],20)
        self.assertIn('아직 점수는 바꾸지 않았습니다',reply)
        invalid,reply=respond(self.network,ready,'가정 140% 20일')
        self.assertNotIn('proposal',invalid)
        filtered,_=respond(self.network,ready,'삼성과 연결된 경로만')
        self.assertNotIn('proposal',filtered)

    def test_cost_equipment_filtered_routes_and_invalid_days_do_not_form_supply_proposals(self):
        for topic in ['관세 예시','ASML 장비 지연 예시']:
            context,_=respond(self.network,{},topic)
            result,_=respond(self.network,context,'만약 공급 40% 감소 20일')
            self.assertNotIn('proposal',result)
        context,_=respond(self.network,{},'JSR 화재 예시')
        filtered,_=respond(self.network,context,'삼성만')
        result,_=respond(self.network,filtered,'만약 40% 20일')
        self.assertNotIn('proposal',result)
        for question in ['만약 40% 1.5일','가정 - 3% 20일','가정 20% 366일','가정 20% 10일 20일']:
            result,_=respond(self.network,context,question)
            self.assertNotIn('proposal',result)

    def test_unsupported_company_and_live_search_are_not_fabricated(self):
        for question in ['TSMC 화재 영향','ASML 화재 영향','최신 뉴스 검색해줘']:
            context,reply=respond(self.network,{},question)
            self.assertNotIn('review',context)
            self.assertTrue('않' in reply)

    @patch.dict('os.environ',{'SUPPLY_ARTICLE_LLM_UI':'0'})
    def test_conversation_scenario_requires_button_and_updates_only_explicit_values(self):
        from streamlit.testing.v1 import AppTest
        with patch('news.article_llm.urlopen',side_effect=AssertionError('No API')) as api:
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'tests/fixtures/panel_components.py'))
            app.session_state['rr_workspace_mode'] = '상세 모드'
            app.session_state['rr_chat_mode'] = '기사 검토 · 모의 대화'
            app.run(timeout=30)
            app.selectbox(key='rr_chat_mode').set_value('기사 검토 · 모의 대화').run(timeout=30)
            before=deepcopy(app.session_state['rr_result'])
            def ask(text):
                app.text_input(key='rr_chat_text').set_value(text)
                next(b for b in app.button if b.label=='질문 보내기 · 모의 대화').click().run(timeout=30)
                self.assertFalse(app.exception)
            ask('JSR 화재 예시')
            self.assertEqual(app.session_state['rr_article_review']['status'],'대화용 모의 초안 · 미검토')
            ask('그중 삼성과 연결된 경로만')
            ask('공급 영향은 확인됐어?')
            self.assertEqual(app.session_state['rr_result'],before)
            ask('전체 경로')
            ask('만약 출하가 20일 중단되면?')
            self.assertEqual(app.session_state['rr_events'],[])
            self.assertNotIn('proposal',app.session_state['rr_chat_context'])
            ask('40%')
            self.assertEqual(app.session_state['rr_events'],[])
            next(b for b in app.button if b.label=='검토한 가정 적용').click().run(timeout=30)
            self.assertFalse(app.exception)
            event=app.session_state['rr_events'][-1]
            self.assertEqual(event['targets'],['jsr'])
            self.assertEqual(event['rate'],0.4)
            self.assertEqual(event['days'],20)
            self.assertNotIn('proposal',app.session_state['rr_chat_context'])
            self.assertEqual(api.call_count,0)


if __name__=='__main__':
    unittest.main()
