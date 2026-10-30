# supply_globe

메인은 **Streamlit + Plotly orthographic 지구본 앱**입니다.
진입점은 `app.py` → `resilience_ui.py`이며, 이슈 입력은 외부 API를 호출하지 않는 규칙 기반 파서가 처리합니다.
`legacy/`의 이전 화면·엔진·JavaScript UI는 메인 앱에서 가져오지 않습니다.

## 실행

Python 3.10 이상에서 프로젝트 루트를 작업 폴더로 사용합니다.

```powershell
python -m pip install -r requirements.txt
python launch_server.py
```

기본 주소: http://127.0.0.1:8517/

직접 실행하려면 다음 명령을 사용합니다.

```powershell
python -m streamlit run app.py --server.port 8517
```

메인 앱 실행에는 Node.js와 legacy 프런트엔드 빌드가 필요하지 않습니다.

## 테스트

프로젝트 루트에서 실행합니다.

```powershell
python -m unittest discover -s tests
npm test
```

`npm test`는 보존된 legacy 프런트엔드의 JavaScript 회귀 검사를 실행합니다. Node.js가 필요하며 루트 패키지에는 설치할 의존성이 없습니다.

```powershell
npm test --prefix legacy/frontend
```

메인 로딩·설정창·상태 회귀를 포함한 Streamlit AppTest:

```powershell
python -m unittest discover -s tests -p test_ui_refactor.py
python -m unittest discover -s tests -p test_stage2.py
python -m unittest discover -s tests -p test_process_reporting.py
```

## 폴더 구조

```text
app.py                      Streamlit 진입점
resilience_ui.py             메인 레이아웃 조합
ui/
  resources.py               프로젝트 경로·CSS·예시·네트워크 캐시
  state.py                   initialize / submit / reset / 선택 범위
  calculation.py             기간 유지 계산·최악/기업평균 민감도 비교
  process_comparison.py      기업별 공정 표·지원 범위·결과 저장
  issues.py                  이슈별 삭제·기간 수정
  issue_manager.py           활성 이슈 목록·편집 창
  timeline.py                공정별 일별 차트·최초 부족 표시
  cards.py                   원인·대응 카드
  panels.py                  헤더·좌측·지구본·우측 패널
  settings.py                설정 대화상자
  settings_tabs.py           각 설정 탭
simulation/
  resilience.py              일 단위 DAG 엔진·규칙 파서·이슈 적용
  schema.py                  파서 출력 타입·validate_parsed
  evidence.py                관계별 계산 허용 규칙·누락 투입재 영향 추적
  reporting.py               일별 기업 결과·최악/동일 기업 비중 평균
resilience_data.py           계산망 구성
resilience_materials.py      확장 소재·공급 후보
resilience_locations.py      실제 위치 적용
resilience_logistics.py      가정 기반 물류 경유
resilience_globe.py          Plotly 지구본
resilience.css               100vh 화면 스타일
data/                       원본·소재·위치·근거 데이터
static/                     메인 앱의 로컬 지도 자료·귀속 정보
tests/                      메인 및 legacy 회귀 검사
legacy/
  app_legacy.py              이전 Globe.gl 화면
  app_plotly.py              이전 Plotly 시안
  app_chain_demo.py          이전 가상 연쇄 시연
  simulation/               구형 계산·대화·선택적 API 어댑터
  frontend/                 이전 JavaScript UI·빌드·검사 설정
  data_loader.py            이전 데이터 로더
  globe_component.py        이전 Streamlit 컴포넌트
  globe.py / theme.py        이전 시각화·테마
docs/                       보관 보고서·파서 출력 계약
launch_server.py             로컬 서버 실행 도우미
start.ps1                    의존성 설치·실행 도우미
package.json                legacy JavaScript 검사 진입점
```

파서 계약은 `docs/ISSUE_PARSER_SCHEMA.md`, 관계 계산 정책은 `docs/RELATIONSHIP_CALCULATION_POLICY.md`, 기업별 집계 계약은 `docs/PROCESS_REPORTING.md`에 있습니다. 기존 보고서는 `docs/`에 보존하며 과거 버전의 동작을 설명할 수 있습니다.

항만·항로 우회는 **가정 설정 → 물류 병목**에서 켜고 편집합니다. 가오슝→기룽, 말라카→롬복, 수에즈→희망봉 후보와 추가 운송일·공유 처리량·운임·해상 비중·도착 재고를 설정할 수 있습니다. 기본은 우회 꺼짐이며 대체 벤더 우회와 독립입니다. 설정 JSON 저장·불러오기와 일별 운송 결과를 지원합니다. 사용법·가정·계산 한계는 `docs/PORT_DETOURS.md`에 있습니다.

평소에는 **지구본 위의 항만별 간단 스위치**를 사용합니다. 저장된 보통값으로 즉시 계산하며, 상세 설정의 **이 값을 보통값으로 저장**으로 대표 가정을 로컬에 보존합니다. 값은 앱 재시작 뒤에도 유지되며 켬/끔 상태는 세션별입니다. 실측 평균을 뜻하지 않습니다. 저장 파일은 `data/quick_detour_profiles.json`입니다.
