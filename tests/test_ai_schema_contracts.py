import unittest
from copy import deepcopy
from jsonschema import Draft202012Validator, ValidationError, validate
from news.alternative_ai import comparison_schema
from news.external_research import report_schema
from news.external_candidates import schema as candidate_schema
from news.factory_ai import factory_schema


class SchemaContracts(unittest.TestCase):
    def test_comparison_own_product_evidence_and_counts(self):
        context={'records':[{'id':'a','facts':{'a::purity':{}}},{'id':'b','facts':{'b::purity':{}}}]}
        schema=comparison_schema(context)
        good=dict(overview='비교', candidates=[dict(record_id=k,explanation='근거',evidence_refs=[k+'::purity']) for k in ('a','b')],next_checks=[])
        validate(good,schema)
        for kind in ('foreign','missing','long'):
            bad=deepcopy(good)
            if kind=='foreign':bad['candidates'][0]['evidence_refs']=['b::purity']
            elif kind=='missing':bad['candidates'].pop()
            else:bad['overview']='x'*1501
            with self.assertRaises(ValidationError):validate(bad,schema)

    def test_report_basis_sources_and_process_scope(self):
        schema=report_schema({'mode':'공정 영향'},['S1'])
        good=dict(summary='요약',source_statements=[],impact_review=[dict(entity='식각',statement='조건부 영향',basis='conditional',source_ids=['S1'])],vendor_options=[],route_options=[],unknowns=[])
        validate(good,schema)
        for key,value in [('basis','candidate'),('entity','새 공정'),('source_ids',['S9'])]:
            bad=deepcopy(good);bad['impact_review'][0][key]=value
            with self.assertRaises(ValidationError):validate(bad,schema)
        bad=deepcopy(good);bad['vendor_options']=[dict(entity='기업',statement='후보',basis='candidate',source_ids=['S1'])]
        with self.assertRaises(ValidationError):validate(bad,schema)

    def test_factory_registered_ids_lengths_and_status(self):
        schema=factory_schema(['E001'],{'companies':{'akm':{}},'routes':{}})
        Draft202012Validator.check_schema(schema)
        p=schema['properties']
        self.assertEqual(p['route_reviews']['maxItems'],0)
        with self.assertRaises(ValidationError):validate('invented',p['company_id'])
        with self.assertRaises(ValidationError):validate('대체 생산 중',p['fields']['properties']['supply_status']['properties']['value'])
        with self.assertRaises(ValidationError):validate('x'*1001,p['findings']['items']['properties']['interpretation'])
        dated=factory_schema({'E001':'2020년 10월 20일 화재. 2020년 2월 30일은 잘못된 날짜.'})
        dates=dated['properties']['fields']['properties']['event_date']['properties']['value']
        validate('2020-10-20',dates)
        with self.assertRaises(ValidationError):validate('2026-10-20',dates)
        with self.assertRaises(ValidationError):validate('2020-02-30',dates)

    def test_external_candidate_fields_do_not_share_constraints(self):
        schema=candidate_schema(['S1'])
        Draft202012Validator.check_schema(schema)
        p=schema['properties']['candidates']['items']['properties']
        validate('실제 기업명',p['name'])
        validate('제품명',p['product'])
        fields=p['fields']['items']['properties']
        validate('99.99',fields['value'])
        validate('ge',fields['operator'])
        with self.assertRaises(ValidationError):validate('unknown',fields['key'])
        with self.assertRaises(ValidationError):validate('S2',p['source_id'])
        self.assertEqual(candidate_schema([])['properties']['candidates']['maxItems'],0)
