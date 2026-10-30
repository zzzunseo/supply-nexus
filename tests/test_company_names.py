import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest


class CompanyNamesTests(unittest.TestCase):
    def test_selection_keeps_full_company_and_facility_names_after_rerun(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'tests/fixtures/panel_components.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        selector = app.selectbox(key='rr_name_company')
        options = selector.options
        self.assertGreater(len(options), 5)
        selector.select('samsung').run(timeout=30)
        self.assertEqual(app.session_state['rr_focus'], 'samsung')
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any('선택 기업:' in item.value and '시설:' in item.value for item in app.markdown))
        app.run(timeout=30)
        self.assertEqual(app.selectbox(key='rr_name_company').value, 'samsung')
        app.selectbox(key='rr_name_company').select(None).run(timeout=30)
        self.assertIsNone(app.session_state['rr_focus'])
        self.assertEqual(len(app.exception), 0)
