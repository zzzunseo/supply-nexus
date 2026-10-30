# SUPPLY NEXUS

AI 기반 반도체 공급망 분석 및 대체 공급처 탐색 시스템입니다.
기업·소재·공정 정보를 지도에서 살펴보고 공급 차질 가정에 따른 영향과 대체 후보를 검토합니다.

## 주요 기능
- Plotly 및 Three.js 기반 공급망 지도
- 공급 차질 시나리오 및 재고 조건에 따른 영향 검토
- 동일 제품군의 후보 탐색 및 제품 조건 비교
- AI 기반 사건·기사 분석과 근거 정리
- 항만·해협 및 우회 물류 시나리오 비교

## 실행
Python 3.10 이상을 사용합니다. 프로젝트 폴더에서 실행하세요.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port 8701
```

브라우저에서 http://localhost:8701 로 접속합니다. 지도 실행에 필요한 로컬 시각화 자산을 포함합니다.
AI 기능은 별도의 OpenAI API 키와 네트워크 연결이 필요하며 API 사용료가 발생할 수 있습니다.
앱의 API 설정에서 키를 입력하거나 `SUPPLY_AI_API_KEY` 또는 `OPENAI_API_KEY` 환경변수를 설정하세요. 키를 소스에 작성하거나 커밋하지 마세요.

## 구성
- `app.py`, `resilience_ui.py`: 앱 진입점
- `ui/`: 화면과 사용자 설정
- `simulation/`: 시뮬레이션 엔진
- `news/`: 기사·AI 분석
- `data/`: 기업·제품·공정·근거 자료
- `night_globe/`, `static/`: 지도와 시각화 자산
- `tests/`: 회귀 검사
- `docs/`: 기능 설명과 과거 개발 기록
- `legacy/`: 이전 구현 및 관련 검사

## 검증
```sh
python -m unittest discover -s tests
```
2026-10-30 기준 Windows / Python 3.12 환경에서 536개 검사를 실행하여 502개 통과, 9개 실패, 25개 오류를 확인했습니다. 현재 버전은 전체 검증을 통과하지 않았습니다. 상세 결과와 확인된 문제는 [검증 보고서](docs/VALIDATION.md)를 참고하세요. 과거 개발 문서는 현재 화면과 다를 수 있습니다.

## 해석 범위
공개 자료와 사용자가 설정한 가정을 구분합니다. 지도상의 연결은 실제 거래·운송 경로를 확정하지 않으며, 대체 후보는 즉시 전환 가능한 공급처를 의미하지 않습니다. 규격·고객 승인·공급 여력·납기를 별도로 확인해야 합니다.
AI는 조사와 설명을 보조하며 계산은 시뮬레이션 엔진이 수행합니다. 기업 내부 데이터 연계는 향후 확장 방향입니다.

## 프로젝트 소개
https://supply-nexus-guide.nutmegberry11.chatgpt.site

외부 자료와 시각화 자산의 출처·귀속 표기는 각 데이터 및 `ATTRIBUTION` 파일을 참고하세요. 저장소 공개가 외부 자산의 재배포 조건을 변경하지 않습니다.
