import unittest
from pathlib import Path
from company_evidence import evidence_bundle
from news.vendor_candidates import registered_candidates,question_requirements
from news.material_scope import material_scope
from product_comparison import load_comparison_data

class MaterialCoverageTests(unittest.TestCase):
 def test_arf_conditions_filter_variants(self):
  req,_=question_requirements('ArF 액침 Positive 대체 공급사')
  self.assertEqual(req['exposure_mode'],'Immersion');self.assertEqual(req['tone'],'positive')
  candidates=registered_candidates(evidence_bundle(),'ArF 액침 Positive 대체 공급사')
  fuji=next(c for c in candidates if c['name']=='FUJIFILM')
  self.assertEqual(fuji['products'],['FAiRS PTI'])
 def test_hf_concentration_not_purity(self):
  req,_=question_requirements('고순도 불화수소 수용액 농도 49%, 총 금속 1 ppb 이하 대체 공급사')
  self.assertEqual(req['concentration_pct'],49);self.assertNotIn('min_purity_pct',req)
  self.assertEqual(req['max_metal_ppb'],1)
  candidates=registered_candidates(evidence_bundle(),'고순도 불화수소 수용액 농도 49%, 총 금속 1 ppb 이하 대체 공급사')
  daikin=next(c for c in candidates if c['name']=='DAIKIN')
  self.assertEqual(daikin['products'],['Hydrofluoric Acid HF49%'])
  self.assertTrue(all(e['status']!='meets_documented' for c in candidates for e in c['evaluations']))
 def test_bhf_not_plain_hf(self):
  candidates=registered_candidates(evidence_bundle(),'완충 불화수소 BHF 대체 공급사')
  self.assertEqual([p for c in candidates for p in c['products']],['Ultra High Purity Buffered Hydrofluoric Acid'])
 def test_anhydrous_not_aqueous(self):
  candidates=registered_candidates(evidence_bundle(),'무수 HF 대체 공급사')
  self.assertFalse(candidates)
  rejected=registered_candidates(evidence_bundle(),'무수 HF 대체 공급사',include_rejected=True)
  self.assertTrue(rejected)
  self.assertTrue(all(c['excluded'] and not c['products'] for c in rejected))
 def test_ceria_is_not_finished_slurry(self):
  self.assertFalse(registered_candidates(evidence_bundle(),'산화세륨 완성 슬러리 대체 공급사'))
  candidates=registered_candidates(evidence_bundle(),'산화세륨 연마재 대체 공급사')
  self.assertEqual({c['name'] for c in candidates},{'Solvay','NYACOL'})
 def test_tariff_does_not_assume_cerium_or_origin(self):
  self.assertFalse(material_scope('희토류 관세')['specific'])
  self.assertTrue(material_scope('산화세륨 관세')['specific'])
  candidates=registered_candidates(evidence_bundle(),'중국산이 아닌 산화세륨 연마재 대체 공급사')
  self.assertTrue(candidates)
  self.assertTrue(all(e['status']=='insufficient' for c in candidates for e in c['evaluations']))
 def test_ui_all_materials(self):
  from streamlit.testing.v1 import AppTest
  app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=40).run()
  app.radio(key='demo_review_view').set_value('AI 분석').run()
  for q,candidate in [('ArF 액침 Positive 대체 공급사','FUJIFILM'),('고순도 불화수소 수용액 농도 49%, 총 금속 1 ppb 이하 대체 공급사','DAIKIN'),('산화세륨 연마재 대체 공급사','Solvay')]:
   app.text_area(key='research_query').set_value(q).run()
   self.assertFalse(app.exception)
   app.selectbox(key='research_candidate_source').select(candidate).run()
   self.assertFalse(app.exception)

 def test_manual_comparison_new_families(self):
  from streamlit.testing.v1 import AppTest
  app=AppTest.from_string('from ui.product_comparison import render_product_comparison\nrender_product_comparison()',default_timeout=30).run()
  for family in ('wet-chemical','cmp-abrasive'):
   app.selectbox(key='comparison_family').set_value(family).run()
   self.assertFalse(app.exception)
 def test_concentration_range_is_not_exact(self):
  req,_=question_requirements('HF 농도 49% 이상 대체 공급사')
  self.assertNotIn('concentration_pct',req)
  self.assertIn('concentration_range_unverified',req)
