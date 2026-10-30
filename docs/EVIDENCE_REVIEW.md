# LLM 전 근거 재검토

2026-10-26 현재 코드에 등록된 확장 소재 60종·공급 후보 104개, 전체 제품·소재 노드 140개, 원본 기업 관계 44개를 분류했습니다. 웹 문서 열람 기록은 76개 URL이며 본문 접근 실패 9개를 포함합니다. 문서가 열린 것은 개별 주장이 입증됐다는 뜻이 아니며, 접근 실패는 제품이나 거래가 없다는 뜻이 아닙니다.

## 확인한 범위
- 제품 종류가 자료에 명시됨: 109개
- 관련 제품군 자료만 확인: 25개
- 이번 검토에서 제품 종류 근거를 확인하지 못함: 6개
- 현재 고객별 품목·등급 계약, 실제 고객별 구매 비중, 실제 재고, 실제 가용 대체량: 확인한 값 없음

109개는 공개 자료에 명시된 제품 종류의 근거입니다. 개별 등급 인증, 현재 판매 가능량, 고객사 사용, 필수 투입 여부 또는 109개의 실제 거래를 검증했다는 뜻이 아닙니다. 공정 그룹 매핑과 필수 레시피는 여전히 모델 가정입니다.

## 고친 출처
공급사가 다른 제품 자료를 공유하던 7개 제품 노드의 출처를 정정했습니다. SUMCO 2개는 SUMCO 제품 자료로, TOK는 TOK 자료로, Teradyne는 자사 검사 자료로 연결했습니다. Samsung 가공 웨이퍼는 삼성 파운드리 제품군 자료로 낮춰 표시했습니다. Air Products 산소·수소는 이번 도구에서 자사 페이지 본문을 확인하지 못했으므로 다른 기업인 Air Liquide를 근거로 쓰지 않고 미확인으로 표시했습니다.

## 계산에서 제외한 경로
원본 ID 44개를 삭제하지 않고 7개 관계 분류를 정정했습니다. 2022년 TSMC 보고서의 세계 주요 공급사 목록을 개별 분자의 TSMC 납품 근거로 쓰던 5개 관계를 미확인으로 바꿨습니다. Applied Materials–Samsung의 EPIC 발표에 기반한 2개 장비 관계는 공동 연구개발로 분류했습니다. 그중 1개는 이미 참고 관계였으므로, 새로 계산에서 빠진 경로는 6개입니다.

- 계산용 시나리오 경로: 30 → 24
- 참고·제외 관계: 14 → 20
- 입력 범위 누락이 전파되는 공정: 6/8 → 7/8

24개도 현재의 품목별 계약과 실제 비중이 모두 확인됐다는 뜻이 아닙니다. 공급 근거가 부족해진 제약을 빼면 지수가 높아질 수 있으므로 100을 정상 운영의 증거로 해석하면 안 됩니다. 화면은 이러한 범위 불완전을 표시합니다.

## 아직 남은 가정
- 공급사 제품이 특정 고객 팹의 필수 입력이라는 레시피
- 원산지·조달 경로, 기업 소속국과 실제 생산국의 연결
- 균등 구매 비중, 재고, 예약 생산량, 우회 한도와 인증·확대 기간
- 가상의 항만·해협 경유, 운송 시간·처리량·비용

이 값들은 실제 자료를 확보하지 못해 제거하거나 사실로 확정할 수 없습니다. 엔진에 사용하는 기존 값은 시나리오 가정으로 남겨 두고, 사실 필드의 실제 값은 null/미확인으로 구분했습니다. 따라서 현재 지수는 가정 시뮬레이션이며 실제 생산량 예측으로 검증되지 않았습니다. 가정을 모두 없앴다고 주장하지 않습니다.

## 기술적 범위
DUV 네온 용도를 EUV 광원 전체의 필수 가스로 일반화하지 않습니다. CMP 소재의 용도를 산화·증착 전체의 필수 입력으로 일반화하지 않습니다. NF3/F2의 챔버 세정·식각 용도와 성막의 필수 투입재를 구분합니다. 제품 카드에 제품 종류 근거, 조건부 용도, 실제 납품·필수 사용 미확인을 표시합니다. 다만 계산 DAG의 나머지 가정 레시피를 이번 단계에서 사실로 전환하거나 모두 삭제하지는 않았습니다.

## 주요 원문
- SUMCO 제품 목록: https://www.sumcosi.com/english/products/lineup.html
- TOK 제품·제조 공정: https://www.tok.co.jp/eng/products/semiconductor-pre
- TSMC 2022 보고서의 주요 소재 공급사 표: https://investor.tsmc.com/static/annualReports/2022/english/ebook/files/basic-html/page106.html
- Applied–Samsung EPIC 공동 연구: https://www.appliedmaterials.com/us/en/newsroom/press-releases/021126-applied-materials-announces-samsung-electronics-will-join-new-epic-center.html
- Linde 가스 목록과 용도: https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics
- Entegris CMP 제품과 용도: https://www.entegris.com/en/home/resources/industry-insights/chemical-mechanical-planarization.html

품목별 근거는 data/evidence_review.json, 열람 기록은 data/evidence_source_checks.json, 관계 정정 전후는 data/evidence_review_changes.json에서 확인할 수 있습니다. 검증 표시는 신뢰한 수동 검토 기록이며 LLM이 임의로 검증 상태를 승격하는 기능은 없습니다.

직접 브라우저 확인, 이름 겹침·잘림·실제 배치 확인은 미확인입니다. 계산식은 변경하지 않았고 재고 소진일은 추가하지 않았습니다.
