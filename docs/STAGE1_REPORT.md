# supply_globe 1단계 구조 정리 완료

범위: 요청한 1단계만 수행했습니다. 2단계 기간 분리·타임라인·이슈 관리·민감도 기능은 추가하지 않았습니다.

## 변경 파일

### legacy 이동

- `app_legacy.py` → `legacy\app_legacy.py`
- `app_plotly.py` → `legacy\app_plotly.py`
- `app_chain_demo.py` → `legacy\app_chain_demo.py`
- `globe_component.py` → `legacy\globe_component.py`
- `globe.py` → `legacy\globe.py`
- `theme.py` → `legacy\theme.py`
- `data_loader.py` → `legacy\data_loader.py`
- `simulation\advice.py` → `legacy\simulation\advice.py`
- `simulation\dialogue.py` → `legacy\simulation\dialogue.py`
- `simulation\engine.py` → `legacy\simulation\engine.py`
- `simulation\issues.py` → `legacy\simulation\issues.py`
- `simulation\llm_provider.py` → `legacy\simulation\llm_provider.py`
- `simulation\overview.py` → `legacy\simulation\overview.py`
- `simulation\service.py` → `legacy\simulation\service.py`
- `simulation\__init__.py` → `legacy\simulation\__init__.py`
- `frontend` → `legacy\frontend`

메인 데이터/계산망/지구본/물류/소재/위치 모듈은 원래 위치에 유지했습니다. `simulation/__init__.py`의 구형 엔진 재수출은 `legacy/simulation/__init__.py`로 이동했습니다. 메인 모듈만 가져오는 새 프로세스에서 legacy가 로딩되지 않음을 검사했습니다.

이동한 앱의 import 경로와 공유 data 경로를 수정했습니다. 구형 컴포넌트의 frontend 경로는 이동된 같은 폴더를 사용합니다. `legacy/frontend/package.json`의 검사 경로를 ../../tests로 변경했고 루트 package.json에 npm test 진입점을 추가했습니다. `.gitignore`는 이동한 node_modules 경로에 맞췄습니다.

### UI 분리

- `resilience_ui.py`: 페이지 설정·캐시 입력·3단 레이아웃 조합만 담당합니다.
- `ui/resources.py`: ROOT·CSS·기존 예시·cached_network.
- `ui/state.py`: initialize/submit/reset/scopes_from_state. submit은 파서 출력 검증 뒤 상태를 변경합니다.
- `ui/calculation.py`: calculate_current. 기존 rr_days 덮어쓰기 동작은 그대로 유지합니다.
- `ui/cards.py`: advice_cards.
- `ui/panels.py`: 헤더·좌측·중앙·우측 패널.
- `ui/settings.py`: 설정 대화상자와 기존 7개 탭 조합.
- `ui/settings_tabs.py`: 각 탭 함수와 source_rows.
- `ui/__init__.py`: UI 패키지.

위젯 라벨·키·생성 순서·기존 예시·설정 탭·계산식은 유지했습니다. 새 Python 소스에는 세미콜론으로 문장을 연결하지 않았습니다.

### 스키마·문서

- `simulation/schema.py`: ParsedIssue/ResetIssue 타입과 validate_parsed. 잘못된 필드·유형·범위·미등록 노드에 ValueError를 냅니다. 입력을 보정하거나 변경하지 않습니다.
- `docs/ISSUE_PARSER_SCHEMA.md`: apply/restore의 7개 필드와 기존 reset의 2개 필드 예외를 명시했습니다. reset 출력 형식은 기존 동작 유지를 위해 바꾸지 않았습니다.
- `README.md`: Plotly 메인 앱, 실행, 테스트, 폴더 구조로 통합했습니다.
- 기존 루트 보고서·가이드·모델 문서 16개는 `docs/`로 이동했습니다. static/frontend 귀속·라이선스 문서는 자산과 함께 유지합니다.

### 테스트 파일

신규: `tests/test_schema.py`(6개), `tests/test_ui_refactor.py`(5개).

다음 기존 파일은 legacy import/mock 경로 및 JS 모듈 경로만 조정했습니다. 테스트 메서드·assertion은 삭제하지 않았습니다. export 보조 스크립트의 보고서 출력 경로는 docs로 변경했습니다.

- `tests/test_chain_demo.py`
- `tests/test_data.py`
- `tests/test_dialogue.py`
- `tests/test_linked_data.py`
- `tests/test_overview.py`
- `tests/test_research_evidence.py`
- `tests/test_simulation.py`
- `tests/export_scenarios.py`
- `tests/view-model.test.mjs`
- `tests/linked-view.test.mjs`

## 검증 결과

| 확인 | 결과 |
|---|---|
| 변경 전 Python | 실제 파일 기준 104개 통과. 요청 현황의 102개와 차이 2개 |
| 변경 후 Python | `python -m unittest discover -s tests`: 115개 통과 |
| JavaScript | `npm test`: 기존 17개 통과 |
| 메인 AppTest | 로딩·설정 탭·PR 입력·우회 토글·복구·잘못된 파서 결과 거부: 예외 0개 |
| legacy AppTest | app_legacy.py / app_plotly.py / app_chain_demo.py 모두 로딩 예외 0개 |
| 엔진 보존 | simulation/resilience.py SHA-256이 변경 전과 동일 |
| 데이터 보존 | data/*.json 전체 해시 동일. share_pct/model_share_pct 구분 유지 |
| 시나리오 보존 | PR/NF3/말라카/초기화 파서 결과와 기존 계산 결과 스냅샷 동일 |
| 스타일 | 신규 UI·스키마·검사 소스에 세미콜론 문장 연결 없음 |

기존 테스트 104개를 모두 유지하고 11개를 추가했습니다. 검사 삭제나 검사 범위 축소는 없습니다. 오래된 Streamlit 인자 관련 경고 및 AppTest의 ScriptRunContext 경고는 예외가 아니며 legacy 코드의 기능 변경은 하지 않았습니다.

## 브라우저 확인과 보류 항목

| 시나리오 | 브라우저 결과 | 추가 확인 |
|---|---|---|
| 일본 포토레지스트 공급 100% 중단 30일 | 전체 60, 최초 부족 15일째 표시 확인 | AppTest timeline에서 포토 1~14일 100, 15~30일 60 확인. 브라우저 일별 차트는 미확인/2단계 미구현 |
| 독일 NF3 공급 중단 60일 | 전체 70, 증착 및 이후 공정 70 표시 확인 | 구조 변경 전과 동일 |
| 말라카 해협 봉쇄 30일 | 전체 0, 물류 노드·봉쇄 경유 궤적 및 원인 카드 표시 확인 | 기존 제품군/레시피 선택 상태는 정상 복구 후에도 유지하는 기존 동작을 유지 |
| 이슈 3일 + 관측 60일 | 미구현·브라우저 미확인 | 기간 분리는 2단계 지시를 기다립니다. 1단계에서 기존 덮어쓰기 동작을 유지하는 회귀 검사 추가 |

## 중단 지점

1단계 완료 후 중단합니다. 다음 단계 작업은 시작하지 않았습니다.
