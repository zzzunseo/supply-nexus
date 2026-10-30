# 1단계: 공급 흐름 데이터

`flow_data.build_flow(network, result, process='포토', selected=None)`는 UI를
불러오거나 계산을 실행하지 않는 순수 함수다. 두 입력을 변경하지 않고 새 객체를 반환한다.

## 반환 형식

- `process`: 선택한 공정. 생략 또는 `None`이면 포토. 미등록 공정은 `ValueError`.
- `selected`: 표시된 대상의 network 노드 ID. 카드 ID를 입력해도 노드 ID로 정규화한다.
  선택이 없거나 대상이 해당 공정에 없으면 `None`이며 흐름 전체를 유지한다.
- `columns`: 공급 기업 → 소재 → 공정 → 영향 기업 순서의 4개 열.
  열은 `id`, `name`, `cards`를 가진다.
- `connections`: 카드 ID를 `from`, `to`로 연결하는 목록.

카드는 `id`, `kind` (`company` / `material` / `process`), `name`, `status`,
`reduction_pct`, `node_id`, `result_node_id`를 가진다. 이름은 축약하지 않는다.
공급 기업과 영향 기업에 같은 회사가 있어도 열별 ID를 써서 충돌을 막는다.
공정 카드는 등록된 기업·공정별 operation을 그대로 사용한다.
영향 기업 카드의 상태도 선택 공정의 operation 결과를 읽는다.

연결은 `id`, `from`, `to`, `status`, `reduction_pct`, `excluded`, `assumption`,
`exclusion_reason`, `source_edge_id`, `result_node_id`를 가진다.
원본 납품 관계는 원본 backbone ID를 유지한다. 상품 생산, 소재 의존성,
기업·공정 출력 연결에는 해당 노드에서 만든 구분 가능한 ID를 사용한다.

## 범위와 상태

선택 공정으로 표시된 납품 관계 중 계산 결과의 활성 scope에 속한 관계만 선택한다.
그 소재의 직접·상위 소재 의존성과 공급 기업도 포함한다. 재고를 가진 운송 노드는
별도 카드로 추가하지 않고, 소재 간 연결이 그 운송 결과의 ID를 보존한다.
이전 공정 operation을 재귀적으로 펼쳐서 다른 공정의 전체 투입재를 섞지 않는다.
기존 제품 노드인 장비도 정해진 4열 구조의 소재 열에 포함된다.

상태는 `normal`, `reduced`, `stopped`, `excluded`, `unknown`이다.
감소율은 기존 결과의 `effective`를 `100 × (1 - effective)`로 표시 단위만 변환한다.
납품 연결은 개별 route 결과를 우선 사용하고, 직접 소재 경로는 운송 결과 또는
해당 소재 결과를 사용한다. 다른 소재까지 합친 mix 평균을 개별 납품률로 쓰지 않는다.
결과 누락은 `unknown`, 감소율 `None`으로 둔다.

기존 계산 제외 결정과 `calculation_included=False`를 보존한다.
제외 관계는 연결에 `excluded=True`, 상태 `excluded`, 감소율 `None`으로 남긴다.
관계 결정 정보가 없는 원본 관계는 기존 근거 정책을 조회한다.
`model_share_pct` 또는 가정 비중을 사용하는 실제 mix가 있는 연결은
`assumption=True`다. 일반 생산·의존성·출력 연결에 점유율 가정 배지를 일괄 붙이지 않는다.

## 검증 범위

`tests/test_flow_data.py`는 8개 공정의 포함 범위, 연결 끝점과 영향 기업까지의 연결,
제외 관계, 점유율 가정, 활성 소재 scope, 상위 소재, 선택 누락, 결과 누락,
기업·공정별 상태, 납품별 상태, 입력 불변성, JSON 직렬화를 검사한다.

아래 시나리오의 **데이터 생성**도 검사한다.

- 일본 포토레지스트 공급 100% 중단 30일: 포토.
- 말라카 해협 봉쇄 30일: 포토, 식각.

1단계는 순수 데이터 함수와 테스트의 범위다. 이어진 2단계 UI 연결과 검증 범위는
`FLOW_UI.md`에 기록한다. 선택 강조, 재고·우회 배지는 후속 단계다.
