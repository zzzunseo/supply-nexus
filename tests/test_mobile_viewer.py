from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest


class MobileViewerTests(unittest.TestCase):
    def app(self,case=None):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30)
        app.query_params['view']='mobile'
        if case:app.query_params['case']=case
        return app.run()

    def test_summary_independent_of_presenter_and_sources_available(self):
        app=self.app()
        self.assertFalse(app.exception)
        self.assertNotIn('rr_network',app.session_state)
        self.assertNotIn('rr_events',app.session_state)
        self.assertEqual(app.title[0].value,'반도체 공급망, 연결에서 대응까지')
        self.assertTrue(any('노트북으로 시연' in item.value for item in app.info))
        self.assertFalse(app.button)
        self.assertFalse(app.segmented_control)
        self.assertTrue(any('PdCu' in item.value for item in app.markdown))
        self.assertTrue(any('희망봉' in item.value for item in app.markdown))
        self.assertEqual(len(app.get('link_button')),4)
        self.assertNotIn('rr_events',app.session_state)

    def test_case_deep_link_and_unknown_case(self):
        for case in ('route','invalid-case'):
            app=self.app(case)
            self.assertFalse(app.exception)
            self.assertTrue(any('AI 실시간 분석 결과가 아닙니다' in item.value for item in app.caption))


if __name__=='__main__':unittest.main()
