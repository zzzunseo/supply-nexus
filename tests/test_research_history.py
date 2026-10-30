import unittest
from ui.research_history import remember,export_html
from news.vendor_candidates import question_requirements,registered_candidates
from company_evidence import evidence_bundle

class ReplayTests(unittest.TestCase):
 def test_bounded_redacted_replay_and_safe_html(self):
  records=[]
  for n in range(7):
   records=remember(records,dict(context_id=str(n),question='<script>question</script>',secret='never-save',search=dict(text='<img src=x>',sources=[dict(title='official',url='https://example.com/source')])) )
  self.assertEqual(len(records),5);self.assertNotIn('secret',str(records));self.assertNotIn('never-save',str(records))
  page=export_html(records[0]);self.assertNotIn('<script>',page);self.assertIn('&lt;img',page)
 def test_multiple_types_not_silently_accepted(self):
  req,notes=question_requirements('SUMCO 300mm PW EPI 대체')
  self.assertNotIn('wafer_type',req);self.assertTrue(any('여러 개' in n for n in notes))
  candidates=registered_candidates(evidence_bundle(),'SUMCO 300mm PW EPI 대체')
  self.assertTrue(candidates)
  self.assertTrue(all(e['status']!='meets_documented' for c in candidates for e in c['evaluations']))
 def test_history_ui(self):
  from streamlit.testing.v1 import AppTest
  app=AppTest.from_string('from ui.research_history import render_history\nrender_history()').run()
  app.session_state['research_answer_history']=remember([],dict(context_id='1',question='test',search=dict(text='saved answer',sources=[dict(title='source',url='https://example.com')])) )
  app.run();self.assertFalse(app.exception)
  self.assertTrue(any('saved answer' in t.value for t in app.text))
