# 이슈 파서 출력 계약

`simulation.resilience.interpret_issue(text, network, default_days, default_loss)`는 외부 API를 호출하지 않는 규칙 기반 파서입니다.
출력을 다른 파서로 교체할 때도 다음 형식을 사용합니다. `simulation.schema.validate_parsed(parsed, known_targets=None)`가 검사하며 잘못된 입력은 `ValueError`를 냅니다.
검증 함수는 값을 변환하거나 원본 dict를 수정하지 않고 그대로 반환합니다. UI에서는 상태 변경 및 `apply_issue` 호출 전에 검증합니다.

## 적용·대상 복구

`action=apply`와 `action=restore`는 다음 일곱 필드를 모두 포함합니다. 추가 필드는 허용하지 않습니다.

| 필드 | 형식 | 의미 |
|---|---|---|
| action | `apply` 또는 `restore` | 적용 또는 대상 복구 |
| kind | `supply` 또는 `tariff` | 공급 감소 또는 관세 |
| targets | 비어 있지 않은 중복 없는 문자열 리스트 | 등록된 계산 노드 ID. 시설명이나 임의로 만든 ID가 아님 |
| rate | 유한한 int/float, bool 제외 | 공급은 0~1, 관세는 0~5. 50%는 0.5 |
| days | 1~365의 int, bool 제외 | 파서가 해석한 이슈 일수 |
| text | 비어 있지 않은 문자열 | 입력 원문 |
| note | 비어 있지 않은 문자열 | 해석·가정 안내 |

```json
{
  "action": "apply",
  "kind": "supply",
  "targets": ["logistics:malacca"],
  "rate": 1.0,
  "days": 30,
  "text": "말라카 해협 봉쇄 30일",
  "note": "말라카 해협의 통항 중단을 가정합니다."
}
```

`known_targets=network["nodes"]`를 전달하면 노드 존재 여부도 검사합니다. 검증 자체는 공급망 관계나 피해율의 사실 여부를 보증하지 않습니다.
`restore`에서도 기존 출력과 동일하게 일곱 필드를 받습니다. `apply_issue`는 해당 대상의 이슈를 제거하며 복구용 rate/days를 별도 타격으로 적용하지 않습니다.

## 전체 초기화

기존 출력 형식과 동작을 유지하기 위해 `reset`은 다음 두 필드만 사용합니다. 공급 타격이 없으므로 targets/rate/days를 임의로 만들지 않습니다.

```json
{"action": "reset", "note": "모든 이슈를 해제했습니다."}
```

## 단계별 범위

2단계부터 `days`는 해당 이슈의 지속 기간입니다. 입력의 “N일”을 그대로 저장하며 기간 미기재 시 30일을 가정합니다. UI의 `rr_days`는 관측 기간(1~365일)으로만 사용하고 이슈를 덮어쓰지 않습니다. 각 이슈는 관측 1일째 시작하며, 공급 중단은 이슈 기간 종료 다음 날 직접 감소가 해제됩니다. 관측 기간보다 긴 이슈도 저장 기간을 유지합니다. 관세는 기존 엔진의 별도 조건부 비용 지수이며 일별 공급 차트에는 생산 감소로 반영하지 않습니다.
