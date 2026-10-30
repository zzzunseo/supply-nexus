# 뉴스 입력 계약 — 1단계

LLM이나 뉴스 수집 없이 사건 입력을 검증하는 순수 함수입니다. 엔진 계산식과 앱 화면은 변경하지 않습니다.

## 입력
- schema_version: 1
- event_id, headline: 사건 식별자와 제목
- published_at: 시간대를 포함한 기사 발행 시각
- occurred_at: 사건 발생 시각. 모르면 null이며 계산 후보 생성은 보류합니다.
- event_type: supply_disruption, logistics_disruption, tariff, recovery, other
- sources: id, url, title, published_at을 가진 출처 목록
- claims: targets, rate, duration_days, impact_scope

각 claim은 value, basis, evidence를 갖습니다. basis는 reported(기사에 적힌 주장), assumption(가정), unknown(미확인)입니다. reported는 사실 인증을 뜻하지 않습니다. evidence에는 등록된 source_id와 quote가 필요합니다. URL 및 문장 형식 검증은 실제 기사 존재나 인용 정확성을 확인하지 않습니다.

영향률은 0~1, 관세율은 0~5, 기간은 1~365일입니다. 미확인 값은 null로 유지하며 평균값을 자동 대입하지 않습니다. 범위는 whole_entity, registered_route, facility, country, unknown입니다.

## 함수
validate_event(event)는 입력을 검증하고 독립된 복사본을 반환합니다.
assess_event(event, known_targets, reviewed=False, approved_assumptions=())는 reject/hold/ready와 사유를 반환합니다.

- reject: 형식 오류, 잘못된 숫자, 누락된 기사 근거 등
- hold: 미검토, 미확인 값, 미승인 가정, 미등록 대상, 시설·국가 범위, 복구·기타 사건 등
- ready: 외부 검토와 필요한 가정 승인을 거친 기존 엔진 입력 형식의 후보

검토와 가정 승인은 뉴스 본문 필드가 아닌 호출자 인자로 받습니다. ready도 실제 계산 적용이나 사실 인증을 의미하지 않습니다. 원 사건과 출처를 함께 반환합니다. 물류 사건은 registered_route 범위가 필요합니다.

## 아직 연결하지 않은 부분
경로 유형의 실제 데이터 대조, 출처 원문 확인, 달력 시점 반영, 화면 입력, 엔진 적용, LLM은 다음 단계입니다. 등록 ID 포함 여부만 확인하며 시설 뉴스를 기업 전체 중단으로 자동 확대하지 않습니다.

재고 소진일 기능은 추가하지 않습니다. 예제는 가상 데이터입니다.


## 이름 연결 — 2단계
news.entities.assess_named_event(event, network, reviewed=False, approved_assumptions=())를 통해 등록 ID 또는 이름·별칭을 연결한 뒤 검토합니다. 직접 assess_event를 호출하는 기존 함수는 ID 입력용입니다. 이름을 사용하는 호출자는 이 어댑터를 사용해야 합니다.

NFKC 유니코드 정규화, 대소문자와 공백만 통일하며 문장 부분 검색·유사 철자 추측은 하지 않습니다. 여러 대상에 연결되는 이름은 후보 목록과 함께 보류합니다. 국가명으로 모든 기업을 일괄 선택하지 않습니다. 물류 사건에는 logistics 대상만 허용하며 공급·관세 사건에 물류 대상이 섞이면 보류합니다. 현재 등록된 logistics는 항만·해협·우회 경유점이며 개별 운송 경로 transport 노드와 구분됩니다.

original_event에는 입력 이름과 기사 근거를 보존하고 mapping에 각 이름의 후보와 연결 ID를 기록합니다. 같은 대상으로 연결된 서로 다른 별칭은 후보의 targets에서 한 번만 사용합니다. 원본 입력과 네트워크는 변경하지 않습니다. 내부 reserve 노드는 이름 검색에서 제외합니다.

등록된 별칭 자체의 범위나 정확성을 자동 인증하지는 않습니다. 별칭이 한 곳으로 연결돼도 출처·시설 범위·감소율·기간 검토는 그대로 필요합니다. 달력 날짜를 시뮬레이션 시작일에 반영하는 처리는 다음 단계입니다.


## 사건 이력 — 3단계
news.lifecycle.empty_registry()로 기록을 만들고 transition(registry, event, network, operation=..., incident_id=..., expected_revision=..., reviewed=..., approved_assumptions=...)을 호출합니다. 순수 함수이며 입력을 변경하지 않고 새 registry를 반환합니다. 파일·DB 저장, UI 연결, 엔진 적용은 아직 없습니다. registry는 이 모듈이 생성한 신뢰할 수 있는 상태를 사용합니다.

- new: 새 사건을 생성합니다. 기존 사건 ID·버전을 지정하지 않습니다.
- report: 같은 사건을 보도한 추가 기사를 연결합니다. 영향 수치·기간·근거 종류·발생 시점이 달라지면 정정 검토를 위해 보류합니다.
- correct: 기존 사건의 현재 후보를 교체합니다. 대상·종류·범위를 바꾸는 정정은 보류합니다. 부분 복구도 이 작업으로 잔여 감소율을 명시해서 처리합니다.
- recover: 기존 사건을 복구 완료로 기록하고 해당 후보만 활성 목록에서 제거합니다. event_type=recovery, 잔여 감소율 0, 발생 시점·기간·범위의 검토가 필요합니다.

report/correct/recover에는 갱신할 incident_id와 현재 expected_revision이 필요합니다. 검토·가정 승인 조건은 이전 단계와 동일합니다. 복구 사건도 원 사건 종류로 대상·범위를 대조합니다. 오래된 기사로 최신 상태를 덮어쓰지 않으며 복구 시점이 원 사건 발생보다 빠르면 보류합니다. 기사 발행 시각 비교는 변경의 순서 확인용이며 실제 시뮬레이션의 달력 시간 변환을 구현한 것은 아닙니다.

처리 완료된 event_id는 같은 내용·작업·연결 ID로 재입력하면 duplicate를 반환합니다. event_id를 재사용하면서 내용이나 작업을 바꾸면 보류합니다. 기사 입력 ID와 사건 ID는 구분되며 최초 기사 입력 ID를 사건 ID로 사용합니다. 보류·거절은 처리 완료 기록을 남기지 않아서 검토 후 다시 입력할 수 있습니다.

다른 기사 입력 ID라도 대상·종류·범위·발생 시각이 같은 사건이 있으면 새 사건 추가를 보류합니다. 정정 이전의 발생 시각도 이 비교에 보존합니다. 시간대가 다른 동일 시각도 일치로 봅니다. 이는 중복 의심을 찾는 제한된 규칙이며 자연어 유사 기사 판별은 아닙니다. 발생 시각·대상이 다르게 추출된 중복 기사를 자동 검출하지 않습니다. 추가 기사를 같은 사건에 연결할지는 호출자가 검토합니다.

active_candidates(registry)는 활성 사건마다 후보 하나씩 정렬해 반환합니다. 정정은 교체하고 복구는 연결된 사건 하나만 제거하므로 같은 기업에 걸린 별개의 차질은 남습니다. 전체 후보 목록의 향후 엔진 연동은 기존 목록 교체 방식이어야 하며 재실행 때마다 추가하거나 기업 전체 restore로 변환하면 안 됩니다. 복구된 사건의 자동 재개는 보류합니다.

history에는 원문 사건·출처·이름 연결 결과·승인한 가정을 버전별로 보존합니다. 별도의 저장이나 사용자 화면은 다음 단계입니다.
