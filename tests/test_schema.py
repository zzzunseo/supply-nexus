from copy import deepcopy
import unittest

from resilience_data import build_network
from simulation.resilience import interpret_issue
from simulation.schema import validate_parsed


class ParsedSchemaTests(unittest.TestCase):
    def setUp(self):
        self.issue = {
            "action": "apply",
            "kind": "supply",
            "targets": ["registered"],
            "rate": 0.5,
            "days": 30,
            "text": "공급 감소 50% 30일",
            "note": "공급 감소 가정",
        }

    def test_valid_result_is_returned_without_mutation_or_coercion(self):
        before = deepcopy(self.issue)
        self.assertIs(validate_parsed(self.issue, {"registered"}), self.issue)
        self.assertEqual(self.issue, before)

    def test_real_parser_apply_restore_and_reset_outputs(self):
        network = build_network()
        for query in (
            "일본 포토레지스트 공급 100% 중단 30일",
            "독일 NF3 공급 중단 60일",
            "말라카 해협 봉쇄 30일",
            "말라카 해협 복구",
            "중국 갈륨 관세 20% 30일",
            "정상 복구",
        ):
            with self.subTest(query=query):
                parsed = interpret_issue(query, network)
                self.assertIs(validate_parsed(parsed, network["nodes"]), parsed)

    def test_invalid_containers_actions_and_fields_raise_value_error(self):
        for value in (None, [], "apply", {}, {"action": "unknown", "note": "설명"}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_parsed(value)
        for field in self.issue:
            issue = deepcopy(self.issue)
            issue.pop(field)
            with self.subTest(missing=field), self.assertRaises(ValueError):
                validate_parsed(issue)
        with self.assertRaises(ValueError):
            validate_parsed(dict(self.issue, extra="unsupported"))

    def test_rates_days_and_target_shapes_are_strict(self):
        invalid = {
            "kind": ["price", None, []],
            "rate": [True, "0.5", -0.1, 1.01, float("nan"), float("inf")],
            "days": [True, 0, 366, 30.0, "30", None],
            "targets": [[], "registered", [""], [1], ["registered", "registered"]],
            "text": [None, "", "  "],
            "note": [None, "", "  "],
        }
        for field, values in invalid.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    validate_parsed(dict(self.issue, **{field: value}))

    def test_tariff_restore_and_registered_target_limits(self):
        self.assertEqual(validate_parsed(dict(self.issue, kind="tariff", rate=5))["rate"], 5)
        self.assertEqual(validate_parsed(dict(self.issue, action="restore"))["action"], "restore")
        with self.assertRaises(ValueError):
            validate_parsed(dict(self.issue, kind="tariff", rate=5.01))
        with self.assertRaises(ValueError):
            validate_parsed(self.issue, {"different"})

    def test_reset_retains_compatible_two_field_contract(self):
        reset = {"action": "reset", "note": "모든 이슈를 해제했습니다."}
        self.assertIs(validate_parsed(reset), reset)
        with self.assertRaises(ValueError):
            validate_parsed(dict(reset, targets=[]))


if __name__ == "__main__":
    unittest.main()
