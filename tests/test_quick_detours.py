from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from resilience_data import build_network
from simulation.quick_detours import (
    default_quick_profiles, read_profiles, write_profiles, save_profile, quick_setting,
)


class QuickDetourProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()

    def test_default_assumptions_cover_per_route_limits_without_claiming_measured_capacity(self):
        profiles = default_quick_profiles(self.network)
        for cp, profile in profiles.items():
            self.assertFalse(profile['enabled'])
            count = sum(cp in r['via'] for r in self.network['logistics_routes'].values())
            self.assertEqual(profile['capacity_units'], count * .5)
            self.assertEqual(profile['max_fraction'], .5)

    def test_durable_profile_save_preserves_other_ports_and_never_saves_enabled_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'usual.json'
            before = read_profiles(self.network, path)
            values = dict(before['logistics:kaohsiung'], enabled=True, extra_days=9, cost_rate=.12)
            saved = save_profile(self.network, 'logistics:kaohsiung', values, path)
            reopened = read_profiles(self.network, path)
            self.assertEqual(reopened, saved)
            self.assertEqual(reopened['logistics:kaohsiung']['extra_days'], 9)
            self.assertFalse(reopened['logistics:kaohsiung']['enabled'])
            self.assertEqual(reopened['logistics:suez'], before['logistics:suez'])
            self.assertEqual(list(Path(temporary).glob('*.tmp')), [])

    def test_invalid_save_does_not_replace_previous_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'usual.json'
            profiles = default_quick_profiles(self.network)
            write_profiles(self.network, profiles, path)
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                save_profile(self.network, 'logistics:kaohsiung',
                    dict(profiles['logistics:kaohsiung'], extra_days=-1), path)
            self.assertEqual(path.read_bytes(), original)

    def test_bad_file_fails_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'usual.json'
            path.write_text(json.dumps(dict(schema_version=1, profiles={})))
            with self.assertRaises(ValueError):
                read_profiles(self.network, path)

    def test_switch_loads_saved_values_and_off_preserves_numbers_without_mutation(self):
        current = dict(self.network['port_detours']['logistics:kaohsiung'], capacity_units=1.)
        profile = dict(default_quick_profiles(self.network)['logistics:kaohsiung'], extra_days=6)
        before = deepcopy((current, profile))
        on = quick_setting(current, profile, True)
        self.assertEqual(on['extra_days'], 6)
        self.assertTrue(on['enabled'])
        off = quick_setting(on, profile, False)
        self.assertFalse(off['enabled'])
        self.assertEqual(off['extra_days'], 6)
        self.assertEqual((current, profile), before)


class QuickDetourUITests(unittest.TestCase):
    def test_main_switch_immediately_recalculates_and_saved_usual_value_survives_new_session(self):
        from streamlit.testing.v1 import AppTest
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'usual.json'
            with patch('ui.quick_detours.read_profiles', side_effect=lambda n: read_profiles(n, path)), \
                 patch('ui.logistics.save_profile', side_effect=lambda n, cp, v: save_profile(n, cp, v, path)):
                app = AppTest.from_file(str(root / 'app.py'))
                app.session_state['rr_workspace_mode'] = '상세 모드'
                app.run(timeout=30)
                self.assertFalse(app.exception)
                self.assertEqual(len(app.toggle), 3)
                app.text_input(key='rr_issue_text').set_value('가오슝항 폐쇄 30일')
                next(b for b in app.button if b.label == '이슈 적용 → 소재 계산').click().run(timeout=30)
                self.assertEqual(app.session_state['rr_result']['overall'], 0)
                app.toggle(key='rr_quick_logistics_kaohsiung').set_value(True).run(timeout=30)
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state['rr_result']['overall'], 50)
                self.assertFalse(app.session_state['rr_network']['port_detours']['logistics:malacca']['enabled'])
                # The advanced editor can store the representative setting.
                app.button[0].click().run(timeout=30)
                next(v for v in app.number_input if v.label == '우회 추가 운송일 · 가정').set_value(6)
                next(b for b in app.button if b.label == '이 값을 보통값으로 저장').click().run(timeout=30)
                self.assertEqual(read_profiles(build_network(), path)['logistics:kaohsiung']['extra_days'], 6)
                app.toggle(key='rr_quick_logistics_kaohsiung').set_value(False).run(timeout=30)
                self.assertEqual(app.session_state['rr_result']['overall'], 0)
                app.toggle(key='rr_quick_logistics_kaohsiung').set_value(True).run(timeout=30)
                self.assertEqual(app.session_state['rr_network']['port_detours']['logistics:kaohsiung']['extra_days'], 6)
                fresh = AppTest.from_file(str(root / 'app.py'))
                fresh.session_state['rr_workspace_mode'] = '상세 모드'
                fresh.run(timeout=30)
                self.assertFalse(fresh.toggle(key='rr_quick_logistics_kaohsiung').value)
                fresh.toggle(key='rr_quick_logistics_kaohsiung').set_value(True).run(timeout=30)
                self.assertEqual(fresh.session_state['rr_network']['port_detours']['logistics:kaohsiung']['extra_days'], 6)
                self.assertFalse(fresh.exception)


if __name__ == '__main__':
    unittest.main()
