import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from ui.integrated_review import coverage


class IntegratedReviewTests(unittest.TestCase):
    def test_inventory_boundaries_and_sensitivity(self):
        self.assertEqual(coverage(30,0,0),100)
        self.assertEqual(coverage(30,100,0),0)
        self.assertEqual(coverage(30,100,30),100)
        self.assertEqual(coverage(30,50,0),50)
        self.assertGreater(coverage(15,100,7),coverage(30,100,7))

    def test_ports_details_assumptions_and_presentation(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        app.radio(key='demo_review_view').set_value('통합 검토 · 발표').run()
        self.assertFalse(app.exception)
        for port in ('busan','singapore','rotterdam','keelung','kaohsiung'):
            app.selectbox(key='integrated_port').select(port).run()
            self.assertFalse(app.exception)
        app.multiselect(key='integrated_rows').select(1).run()
        app.selectbox(key='integrated_detail').select(1).run()
        self.assertFalse(app.exception)
        app.number_input(key='integrated_stock').set_value(30).run()
        self.assertEqual(app.metric[2].value,'100.0%')
        app.toggle(key='integrated_poster').set_value(True).run()
        self.assertFalse(app.exception)
        self.assertTrue(any(e.label=='사건·연결·가정 설정' for e in app.expander))
        app.multiselect(key='integrated_rows').set_value([]).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)
