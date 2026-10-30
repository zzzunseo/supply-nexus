from copy import deepcopy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from product_comparison import load_comparison_data,compare_record
from news.alternative_ai import comparison_context,validate_comparison,explain_alternatives


class AlternativeAITests(unittest.TestCase):
    def setUp(self):
        self.data=load_comparison_data()
        self.context=comparison_context(self.data,'process-gas',{'chemical':'CF4','min_purity_pct':99.999,'max_water_ppmv':1},
            ['matheson_cf4_5n','messer_cf4_5n'],'공정 조건과 수분 상한을 우선 비교')
        self.proposal=dict(overview='공개 규격을 비교했으며 실제 고객 승인은 별도입니다.',candidates=[
            dict(record_id=r['id'],explanation='공개 수분 규격을 요구 조건과 대조하고 공급 가능 여부를 별도 확인합니다.',
                evidence_refs=[r['id']+'::water_ppmv']) for r in self.context['records']],next_checks=[
            dict(topic='qualification',reason='규격 비교가 고객 인증 완료를 뜻하지 않으므로 샘플과 CoA를 확인합니다.',evidence_refs=['messer_cf4_5n::purity_pct'])])

    def test_numeric_differences_and_application_scope(self):
        records={r['id']:r for r in self.data['records']}
        self.assertEqual(self.context['records'][0]['rule_result']['status'],'mismatch')
        self.assertEqual(self.context['records'][1]['rule_result']['status'],'meets_documented')
        required={'wafer_type':'PW','diameter_mm':200,'thickness_um':725,'resistivity_ohm_cm':10}
        self.assertEqual(compare_record(records['swt_dsp_200'],required)['status'],'meets_documented')
        self.assertEqual(compare_record(records['swt_dsp_150'],required)['status'],'mismatch')
        self.assertEqual(compare_record(records['sumco_pw'],required)['status'],'insufficient')
        required={'target_film':'Cu','application':'hybrid_bonding'}
        self.assertEqual(compare_record(records['fujifilm_hybrid'],required)['status'],'meets_documented')
        self.assertEqual(compare_record(records['fujifilm_cu'],required)['status'],'insufficient')
        self.assertEqual(compare_record(records['fujifilm_hybrid'],{'target_film':'SiO2'})['status'],'insufficient')

    def test_context_changes_with_requirements_goal_and_catalog(self):
        for kind in ('requirements','goal','catalog'):
            data=deepcopy(self.data);req=dict(self.context['requirements']);goal=self.context['goal']
            if kind=='requirements':req['max_water_ppmv']=2
            elif kind=='goal':goal='현행 규격 확인 우선'
            else:data['sources']['messer_cf4']['edition']='changed'
            changed=comparison_context(data,'process-gas',req,['matheson_cf4_5n','messer_cf4_5n'],goal)
            self.assertNotEqual(changed['id'],self.context['id'])

    def test_status_is_computed_not_assigned_by_ai(self):
        result=validate_comparison(self.context,self.proposal)
        self.assertEqual([r['status'] for r in result['candidates']],['mismatch','meets_documented'])
        self.assertNotIn('provenance',result)

    def test_new_products_cross_product_citations_and_missing_candidates_rejected(self):
        for change in ('new','cross_ref','missing','fake_ref','certainty','number'):
            proposal=deepcopy(self.proposal)
            if change=='new':proposal['candidates'][0]['record_id']='invented'
            elif change=='cross_ref':proposal['candidates'][0]['evidence_refs']=['messer_cf4_5n::water_ppmv']
            elif change=='missing':proposal['candidates'].pop()
            elif change=='fake_ref':proposal['candidates'][0]['evidence_refs']=['matheson_cf4_5n::capacity']
            elif change=='certainty':proposal['candidates'][0]['explanation']='즉시 대체 가능합니다.'
            else:proposal['candidates'][0]['explanation']='공급 회복률은 87.123%입니다.'
            with self.subTest(change=change),self.assertRaises(ValueError):validate_comparison(self.context,proposal)

    def test_live_request_schema_secret_and_no_retry(self):
        calls=[]
        def transport(request,timeout):
            calls.append(1);body=json.loads(request.data)
            self.assertFalse(body['store']);self.assertTrue(body['text']['format']['strict'])
            self.assertNotIn('synthetic-secret',request.data.decode())
            return io.BytesIO(json.dumps(dict(status='completed',output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(self.proposal))])])).encode())
        result=explain_alternatives(self.context,'synthetic-secret',transport=transport)
        self.assertEqual(len(calls),1);self.assertEqual(result['provenance']['method'],'live_api')
        self.assertNotIn('synthetic-secret',json.dumps(result))
        def fail(request,timeout):raise HTTPError(request.full_url,429,'synthetic-secret',{},None)
        with self.assertRaises(ValueError) as error:explain_alternatives(self.context,'synthetic-secret',transport=fail)
        self.assertNotIn('synthetic-secret',str(error.exception))

    def test_ui_live_hook_and_stale_condition_invalidation(self):
        from streamlit.testing.v1 import AppTest
        with patch.dict('os.environ',{'SUPPLY_AI_API_KEY':'synthetic-test-only'}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
            app.radio(key='demo_review_view').set_value('AI 분석').run()
            app.radio(key='ai_workspace_task').set_value('기업·소재 조건 비교').run()
            self.assertFalse(app.exception)
            def fake(context,key,model):
                proposal=dict(overview='테스트용 해설',candidates=[dict(record_id=r['id'],explanation='테스트 응답이며 실제 AI가 생성하지 않았습니다.',evidence_refs=[next(iter(r['facts']))]) for r in context['records']],next_checks=[])
                result=validate_comparison(context,proposal);result['provenance']=dict(method='live_api',model='synthetic-model');return result
            with patch('ui.alternative_ai.explain_alternatives',side_effect=fake) as mocked:
                app.button(key='alternative_run').click().run()
                self.assertEqual(mocked.call_count,1)
            self.assertFalse(app.exception)
            self.assertIn('alternative_result',app.session_state)
            app.selectbox(key='comparison_exposure').select('EUV').run()
            self.assertFalse(app.exception)
            self.assertNotIn('alternative_result',app.session_state)
            self.assertTrue(any('euv' in k for k in app.session_state.alternative_records))
            for family in ('process-gas','silicon-wafer','cmp-slurry'):
                app.selectbox(key='comparison_family').select(family).run()
                self.assertFalse(app.exception)

