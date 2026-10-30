"""Shared output contract for the current rule parser and future parser adapters."""
from collections.abc import Collection
from math import isfinite
from typing import Literal, TypedDict


class ParsedIssue(TypedDict):
    action: Literal["apply", "restore"]
    kind: Literal["supply", "tariff"]
    targets: list[str]
    rate: float
    days: int
    text: str
    note: str


class ResetIssue(TypedDict):
    action: Literal["reset"]
    note: str


ParsedResult = ParsedIssue | ResetIssue
ISSUE_FIELDS = {"action", "kind", "targets", "rate", "days", "text", "note"}
RESET_FIELDS = {"action", "note"}


def validate_parsed(parsed: object, known_targets: Collection[str] | None = None) -> ParsedResult:
    """Validate without coercing or mutating the result; raise ValueError on failure.

    Reset keeps the existing two-field format. Apply/restore require all seven
    fields. Rates are fractions, days are positive integers, and target IDs may
    optionally be checked against a graph's registered node IDs.
    """
    if not isinstance(parsed, dict):
        raise ValueError("파서 결과는 dict여야 합니다.")
    action = parsed.get("action")
    if action not in ("apply", "restore", "reset"):
        raise ValueError("파서 action은 apply, restore, reset 중 하나여야 합니다.")
    fields = RESET_FIELDS if action == "reset" else ISSUE_FIELDS
    if set(parsed) != fields:
        raise ValueError("파서 결과의 필수 필드가 누락되었거나 알 수 없는 필드가 있습니다.")
    if not isinstance(parsed["note"], str) or not parsed["note"].strip():
        raise ValueError("파서 note는 비어 있지 않은 문자열이어야 합니다.")
    if action == "reset":
        return parsed
    if parsed["kind"] not in ("supply", "tariff"):
        raise ValueError("파서 kind는 supply 또는 tariff여야 합니다.")
    targets = parsed["targets"]
    if not isinstance(targets, list) or not targets:
        raise ValueError("파서 targets는 비어 있지 않은 ID 목록이어야 합니다.")
    if any(not isinstance(target, str) or not target.strip() for target in targets):
        raise ValueError("파서 대상 ID는 비어 있지 않은 문자열이어야 합니다.")
    if len(set(targets)) != len(targets):
        raise ValueError("파서 targets에 중복 ID가 있습니다.")
    if known_targets is not None and any(target not in known_targets for target in targets):
        raise ValueError("파서 결과에 등록되지 않은 대상 ID가 있습니다.")
    rate = parsed["rate"]
    limit = 1 if parsed["kind"] == "supply" else 5
    if type(rate) not in (int, float) or not 0 <= rate <= limit or not isfinite(rate):
        raise ValueError(f"파서 rate는 0~{limit} 범위의 유한한 비율이어야 합니다.")
    if type(parsed["days"]) is not int or not 1 <= parsed["days"] <= 365:
        raise ValueError("파서 days는 1~365 범위의 정수여야 합니다.")
    if not isinstance(parsed["text"], str) or not parsed["text"].strip():
        raise ValueError("파서 text는 비어 있지 않은 문자열이어야 합니다.")
    return parsed
