import unittest,json,io
from copy import deepcopy
from pathlib import Path
from news.facility_scope import facility_scope,facility_map,load_facilities
from news.external_research import make_research_context,research_external
from company_evidence import evidence_bundle

class FacilityScopeTests(unittest.TestCase):
 def test_registry_sources_and_no_capacity_claims(self):
  data=load_facilities();self.assertEqual(len(data['facilities']),14)
  for f in data['facilities']:
   self.assertTrue(all(s in data['sources'] for s in f['source_ids']))
   self.assertIsNone(f['capacity_available']);self.assertIsNone(f['qualification'])
   self.assertFalse(f['disruption_confirmed'])
   self.assertIn('실제 공장 좌표 아님',f['coordinate_precision'])
 def test_company_only_does_not_pick_damaged_factory(self):
  scope=facility_scope('TSMC 공급 중단')
  self.assertIsNone(scope['selected']);self.assertFalse(scope['internal_options'])
  self.assertEqual(len(scope['facilities']),6)
 def test_specific_site_and_same_node_are_not_qualification(self):
  scope=facility_scope('TSMC Fab 14 중단되면?')
  self.assertEqual(scope['selected']['id'],'facility:tsmc-14')
  other=next(o for o in scope['internal_options'] if o['facility_id']=='facility:tsmc-16')
  self.assertIn('표기 공정 겹침',other['status']);self.assertFalse(other['transfer_confirmed'])
 def test_ingot_not_finished_wafer(self):
  scope=facility_scope('SUMCO 요네자와 중단')
  option=next(o for o in scope['internal_options'] if o['facility_id']=='facility:sumco-chitose')
  self.assertEqual(option['status'],'공개 생산 단계 다름')
 def test_nf3_does_not_promote_aggregate_plant(self):
  scope=facility_scope('효성 용연 NF3 중단')
  statuses={o['facility_id']:o['status'] for o in scope['internal_options']}
  self.assertIn('생산 품목 겹침',statuses['facility:hyosung-quzhou'])
  self.assertEqual(statuses['facility:hyosung-oksan'],'공장별 제품 근거 부족')
  self.assertFalse(facility_scope('SK specialty 영주 NF3 중단')['facilities'])
 def test_map_groups_region_and_has_no_supply_or_damage_edges(self):
  scope=facility_scope('SUMCO 구바라 중단');before=deepcopy(scope)
  data=facility_map(scope)
  self.assertEqual(scope,before);self.assertFalse(data['routes'])
  self.assertEqual(len(data['markers']),4)
  self.assertIn('camera_focus',data)
  self.assertTrue(all('impact' not in m for m in data['markers']))
 def test_public_scope_sent_and_choice_changes_context(self):
  a=make_research_context(evidence_bundle(),'TSMC 공급 중단')
  b=make_research_context(evidence_bundle(),'TSMC 공급 중단',facility_id='facility:tsmc-14')
  self.assertNotEqual(a['id'],b['id']);calls=[]
  def transport(request,timeout):
   calls.append(json.loads(request.data))
   return io.BytesIO(json.dumps(dict(status='completed',output=[dict(type='web_search_call',status='completed',action={}),dict(type='message',content=[dict(type='output_text',text='공장 검토',annotations=[dict(type='url_citation',url='https://www.tsmc.com/english',title='TSMC',start_index=0,end_index=5)])])])).encode())
  research_external(b,'synthetic-key',transport=transport,simple=True)
  public=json.loads(calls[0]['input']);self.assertEqual(public['facility_review']['selected_id'],'facility:tsmc-14')
  self.assertIn('기업 전체',public['facility_rule'])
 def test_ui_factory_choice(self):
  from streamlit.testing.v1 import AppTest
  app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=40).run()
  app.radio(key='demo_review_view').set_value('AI 분석').run()
  app.text_area(key='research_query').set_value('SUMCO 요네자와 공급 중단').run()
  self.assertFalse(app.exception)
  self.assertTrue(any('공장 · 내부 거점'==t.label for t in app.tabs))
  select=next(s for s in app.selectbox if str(s.key).startswith('research_facility_'))
  select.set_value('facility:sumco-chitose').run()
  self.assertFalse(app.exception)
  self.assertTrue(any('SUMCO 치토세' in m.value for m in app.markdown))
