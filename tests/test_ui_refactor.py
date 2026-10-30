from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from ui.calculation import calculate_current


ROOT = Path(__file__).resolve().parents[1]


class UIRefactorTests(unittest.TestCase):
    def load_app(self):
        app = AppTest.from_file(str(ROOT / "tests/fixtures/panel_components.py"))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        return app

    def test_main_loading_and_settings_keep_existing_widgets(self):
        app = self.load_app()
        self.assertEqual(app.session_state["rr_result"]["overall"], 100)
        app.button[0].click().run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(
            [tab.label for tab in app.tabs],
            ["제품군·가정", "44개 원본 경로", "추가 소재·출처", "실제 위치·근거",
             "확장 소재·우회", "물류 병목", "계산 비교"],
        )

    def test_submit_bypass_toggle_and_reset_preserve_scores(self):
        app = self.load_app()
        app.text_input(key="rr_issue_text").input("일본 포토레지스트 공급 100% 중단 30일")
        app.button[-1].click().run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["rr_result"]["overall"], 60)
        self.assertEqual(app.session_state["rr_days"], 30)
        result = app.session_state["rr_result"]
        self.assertTrue(all(row["포토"] == 100 for row in result["timeline"][:14]))
        self.assertTrue(all(row["포토"] == 60 for row in result["timeline"][14:]))
        self.assertEqual(result["first_hit"]["포토"], 15)
        app.checkbox(key="rr_bypass").uncheck().run(timeout=30)
        self.assertEqual(app.session_state["rr_result"]["overall"], 0)
        app.button[1].click().run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["rr_events"], [])
        self.assertEqual(app.session_state["rr_result"]["overall"], 100)

    def test_invalid_future_parser_output_cannot_change_events(self):
        app = self.load_app()
        before = deepcopy(app.session_state["rr_events"])
        app.text_input(key="rr_issue_text").input("공급 차질")
        with patch("ui.state.interpret_issue", return_value={"action": "apply"}):
            app.button[-1].click().run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(app.session_state["rr_error"])
        self.assertEqual(app.session_state["rr_events"], before)

    def test_preserves_issue_period_without_mutating_saved_events(self):
        saved = [{"kind": "supply", "targets": ["a"], "rate": 1.0, "days": 3}]
        before = deepcopy(saved)
        state = SimpleNamespace(
            rr_events=saved,
            rr_days=60,
            rr_inventory=True,
            rr_bypass=False,
        )
        with patch("ui.calculation.st", SimpleNamespace(session_state=state)):
            with patch("ui.calculation.scopes_from_state", return_value=[]):
                with patch("ui.calculation.calculate_supply_shock", return_value={}) as calculate:
                    calculate_current({})
        self.assertEqual(calculate.call_args.args[1][0]["days"], 3)
        self.assertEqual(calculate.call_args.args[2], 60)
        self.assertEqual(saved, before)

    def test_main_import_does_not_load_legacy_modules(self):
        code = """
import sys
import resilience_ui
assert not any(name == "legacy" or name.startswith("legacy.") for name in sys.modules)
assert "simulation.engine" not in sys.modules
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
