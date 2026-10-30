import copy
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from legacy.data_loader import load_demo
from legacy.simulation import calculate,load_model,build_simulation_payload
from legacy.simulation.issues import offline_extract,assess_issue,scenario_from_assessment,validate_facilities
from legacy.simulation.dialogue import handle_request
from legacy.simulation.advice import build_advice
from legacy.simulation.llm_provider import configuration,extract_issue,research_issue
ROOT=Path(__file__).resolve().parents[1]

class DialogueTests(unittest.TestCase):
    def setUp(self):
        self.data=load_demo(ROOT/'data/demo.json');self.model=load_model(ROOT/'data/simulation_demo.json',self.data)
        self.options=dict(duration_days=14,severity=1,inventory=True,substitutes=False)
    def assess(self,text):
        return assess_issue(offline_extract(text,self.data),self.data)
    def test_asml_manual_half_loss_only_two_lithography_edges(self):
        a=self.assess('ASML 공급 능력 50% 감소, 14일')
        self.assertTrue(a['can_apply']);self.assertEqual(a['edge_count'],2)
        r=calculate(self.data,self.model,scenario_from_assessment(a),**(self.options|{'severity':.5}))
        self.assertEqual(r['overall_score'],50);self.assertEqual(r['bottlenecks'],['포토'])
        self.assertEqual(sum(v<1 for v in r['edge_availability'].values()),2)
    def test_french_oxygen_intersection_not_all_french_materials(self):
        a=self.assess('프랑스 산소 공급 30% 감소, 7일')
        self.assertTrue(a['can_apply']);self.assertEqual(a['edge_count'],2)
        edges={e['id']:e for e in self.data['edges']}
        self.assertTrue(all(edges[k]['item_id']=='oxygen' for k in a['edge_factors']))
        r=calculate(self.data,self.model,scenario_from_assessment(a),duration_days=7,severity=.3,inventory=False,substitutes=False)
        oxygen=next(i for p in r['processes'] for i in p['inputs'] if i['item_id']=='oxygen')
        self.assertAlmostEqual(oxygen['supply'],.85)
    def test_tariff_never_becomes_supply_shock(self):
        a=self.assess('트럼프 희토류 관세 20% 부과')
        self.assertFalse(a['can_apply']);self.assertIsNone(a['draft']['loss_pct']);self.assertIn('120',a['answer'])
        with self.assertRaises(ValueError):scenario_from_assessment(a)
    def test_unknown_factory_never_uses_japan_hq_coordinates(self):
        a=self.assess('일본 지진으로 Nokia 공장 차질 50% 14일')
        self.assertFalse(a['can_apply']);self.assertEqual(a['edge_count'],0)
        self.assertIn('Nokia',a['draft']['unresolved'])
    def test_locality_and_unknown_korean_company_block_country_fallback(self):
        for text in ['일본 구마모토 공급 50% 감소 14일','일본 키옥시아 공급 50% 감소 14일','일본 가상소재 공급 50% 감소 14일']:
            with self.subTest(text=text):self.assertFalse(self.assess(text)['can_apply'])
    def test_followup_retains_target_only_and_changes_numeric_conditions(self):
        previous=offline_extract('ASML 공급 50% 감소 14일',self.data)
        d=offline_extract('그럼 20%로 바꾸고 30일',self.data,previous)
        self.assertEqual(d['companies'],['asml']);self.assertEqual(d['loss_pct'],20);self.assertEqual(d['duration_days'],30)
        new=offline_extract('JSR 공급 감소',self.data,previous)
        self.assertIsNone(new['loss_pct']);self.assertIsNone(new['duration_days'])
    def test_missing_or_invalid_numbers_require_clarification(self):
        for text in ['ASML 공급 감소','ASML 공급 -10% 감소 14일','ASML 공급 120% 감소 14일','ASML 공급 10% 감소 0일','ASML 공급 20% 증가 14일']:
            with self.subTest(text=text):self.assertFalse(self.assess(text)['can_apply'])
        self.assertEqual(self.assess('ASML 가동률 80%, 14일')['draft']['loss_pct'],20)
    def test_inventory_comparison_does_not_create_equipment_stock(self):
        a=self.assess('ASML 공급 50% 감소 14일');scenario=scenario_from_assessment(a);opts=self.options|{'severity':.5}
        before=copy.deepcopy(self.model);r=calculate(self.data,self.model,scenario,**opts)
        advice=build_advice(self.data,self.model,scenario,opts,r)
        stock=next(v for v in advice['mitigations'] if v['id']=='stock')
        self.assertEqual(stock['score'],50);self.assertEqual(self.model,before)
    def test_request_deduplication_and_no_network_in_test_mode(self):
        request={'id':'one','action':'analyze','text':'ASML 공급 50% 감소 14일','mode':'test'}
        with patch('legacy.simulation.llm_provider.urlopen',side_effect=AssertionError('network forbidden')):
            state=handle_request(request,self.data,self.model,{},self.options)
            self.assertEqual(state['analysis']['preview']['score'],50)
            self.assertEqual(handle_request(request,self.data,self.model,state,self.options),state)
            applied=handle_request({'id':'two','action':'apply'},self.data,self.model,state,self.options)
            self.assertTrue(applied['custom_scenario']['custom_issue']);self.assertEqual(applied['applied_selection']['severity'],.5)
    def test_failed_new_request_removes_previous_apply_draft(self):
        state=handle_request({'id':'a','action':'analyze','text':'ASML 공급 50% 감소 14일'},self.data,self.model,{},self.options)
        with patch('legacy.simulation.dialogue.extract_issue',side_effect=ValueError('connection failed')):
            state=handle_request({'id':'b','action':'analyze','text':'new','mode':'openai'},self.data,self.model,state,self.options)
        self.assertIsNone(state['analysis'])
    def test_api_configuration_is_opt_in_and_structured_payload_is_valid(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertFalse(configuration()['openai_available'])
            with self.assertRaises(ValueError):research_issue('factory')
        draft=offline_extract('ASML 공급 50% 감소 14일',self.data)
        import json
        response={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(draft)}]}]}
        with patch('legacy.simulation.llm_provider.request_response',return_value=response) as call:
            result=extract_issue('ASML 공급 50% 감소 14일',self.data)
            self.assertEqual(result,draft)
            self.assertEqual(call.call_args.args[0]['text']['format']['type'],'json_schema')
    def test_facility_needs_sourced_edge_share_and_applies_fraction(self):
        edge='lithography:asml>samsung'
        facility={'id':'fixture-only','name':'검사 전용 가상 시설','company_id':'asml','country':'일본','region':'검사 지역',
            'lat':1,'lon':2,'status':'출처 있음','source':'https://example.org/fixture','source_year':2026,
            'edge_capacity_shares':{edge:{'fraction':.4,'source':'https://example.org/fixture-share','source_year':2026}}}
        d=copy.deepcopy(self.data);d['facilities']=validate_facilities([facility],d)
        a=assess_issue(offline_extract('검사 전용 가상 시설 공급 50% 감소 14일',d),d)
        self.assertTrue(a['can_apply']);r=calculate(d,self.model,scenario_from_assessment(a),**(self.options|{'severity':.5}))
        self.assertAlmostEqual(r['edge_availability'][edge],.8)
        bad=copy.deepcopy(facility);bad['edge_capacity_shares'][edge].pop('source')
        with self.assertRaises(ValueError):validate_facilities([bad],d)
    def test_invalid_edge_shock_cannot_silently_enter_engine(self):
        for factors in [{'invented':1},{self.data['edges'][0]['id']:float('nan')},{self.data['edges'][0]['id']:2}]:
            with self.assertRaises(ValueError):calculate(self.data,self.model,{'name':'bad','affected':[],'edge_impact_factors':factors})

    def test_explanation_followup_keeps_current_draft_and_calls_no_api(self):
        state=handle_request({'id':'one','action':'analyze','text':'ASML 공급 50% 감소 14일'},self.data,self.model,{},self.options)
        before=copy.deepcopy(state['analysis'])
        with patch('legacy.simulation.llm_provider.urlopen',side_effect=AssertionError('network forbidden')):
            result=handle_request({'id':'two','action':'analyze','text':'원인과 대응책 알려줘'},self.data,self.model,state,self.options)
        self.assertEqual(result['analysis'],before)
        self.assertIn('노광 장비',result['messages'][-1]['text'])
