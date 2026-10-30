# 반도체 공급망 소재 확장 · 2026-10-26

## 반영 규모

신규 투입재 60종, 공급사–품목 후보 104개, 신규 기업 10곳을 추가했습니다. 기존 44개 원본 관계와 14개 상류 경로는 보존했습니다. 현재 계산망은 노드 493개·시각 관계 490개입니다. 이 숫자는 실제 납품 계약의 건수가 아닙니다.

확장 소재 중 36종은 복수 공급 후보와 추가 예약 우회풀을 등록했습니다. 나머지는 대체 후보 미등록으로 표시합니다.

- 특수가스: 22종
- 세정·습식 화학품: 13종
- CMP 소모재: 6종
- 패키징 소재: 6종
- 웨이퍼 대체 후보: 2종
- 금속 타깃: 6종
- 증착 전구체: 5종

## 작동 방식

- 등록 소재명·약어·공급사로 이슈를 입력하면 관련 확장 레시피를 자동 활성화합니다. 기본 화면에서는 기존 레시피를 유지합니다.
- 정상 공급 후보는 균등 조달 비중 가정으로 병렬 합산합니다. 웨이퍼 추가 후보는 기존 웨이퍼 공급사와 병렬로 계산합니다.
- 각 제품의 재고가 부족분을 먼저 방어합니다. 대체 공급은 첫 부족 발생일부터 인증 대기일을 계산하고, 이후 공급 확대 기간 동안 점진 증가합니다.
- 예약풀은 같은 소재의 요청이 공유합니다. 공통 상류 원료가 차단되면 예약풀도 영향을 받습니다.
- 임의로 다른 화학물질을 서로 대체하지 않습니다. F2·NF3 등 화학 대체는 호환성 검증 없이 자동 적용하지 않습니다.
- 확장 소재·우회 탭에 분류·검색·출처·관계도·저장 기능을 추가했습니다.
- 신규 공급사 10곳은 위치 근거 미확인으로 지도에서 숨기며 비지리적 관계도와 표에서 확인합니다. 기존 위치 27곳은 유지합니다.

## 해석 범위

제품 카탈로그·제품군 자료는 제품 존재와 용도를 뒷받침합니다. 고객별 납품·실제 구매 비중·시설 생산국·재고·인증 기간·추가 생산 여력은 확인된 실측값이 아닙니다. 특히 국가 입력은 등록 기업 소속국을 사용하며 실제 공장 소재국과 다릅니다.

가격·관세 지수는 생산 공급 점수와 구분됩니다. 지역만 있는 지진·항만 폐쇄·미등록 소재를 자동으로 특정 시설 피해로 환산하지 않습니다. 입력 해석은 오프라인 등록명·별칭 규칙이며 일반 자연어/실시간 뉴스 분석기가 아닙니다.

## 입력과 결과 예시

각 행은 다른 이슈가 없는 초기 상태에서 실행했습니다. 모든 수치는 모델 가정에 따른 마지막 날 공급 충족도입니다.

| 입력 | 우회 켬 전체 | 우회 끔 전체 |
|---|---:|---:|
| 독일 NF3 공급 중단 60일 | 70.0 | 50.0 |
| 간토화학 PGMEA 공급 중단 60일 | 70.0 | 50.0 |
| 인테그리스 구리 CMP 공급 중단 60일 | 80.0 | 66.7 |
| 레조낙 DAF 공급 중단 90일 | 70.0 | 50.0 |
| 헬륨 공급 감소 50% 30일 | 60.0 | 50.0 |
| 중국 형석 공급 중단 60일 | 0.0 | 0.0 |
| 실트로닉 공급 중단 60일 | 66.7 | 66.7 |
| 헨켈 화재 60일 | 50.0 | 50.0 |
| 루테늄 공급 중단 60일 | 0.0 | 0.0 |
| TEOS 공급 감소 50% 60일 | 56.7 | 50.0 |

## 신규 소재 전체 목록

| 소재 | 분류 | 연결 공정 | 공급 후보 | 제품 자료 |
|---|---|---|---|---|
| 고순도 질소(N2) | 특수가스 | 산화 / 증착·이온주입 / 금속배선 | Linde Electronics / Nippon Sanso Matheson / Air Liquide | [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) / [Nippon Sanso Matheson](https://us.nipponsanso.com/industries/electronics/) / [Air Liquide](https://my.airliquide.com/gas-application/semiconductor-and-electronics-manufacturing) |
| 고순도 아르곤(Ar) | 특수가스 | 증착·이온주입 / 금속배선 | Linde Electronics / Nippon Sanso Matheson / Air Liquide | [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) / [Nippon Sanso Matheson](https://us.nipponsanso.com/industries/electronics/) / [Air Liquide](https://my.airliquide.com/gas-application/semiconductor-and-electronics-manufacturing) |
| 고순도 헬륨(He) | 특수가스 | 식각 | Linde Electronics / Nippon Sanso Matheson | [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) / [Nippon Sanso Matheson](https://us.nipponsanso.com/industries/electronics/) |
| 모노실란(SiH4) | 특수가스 | 증착·이온주입 | Air Liquide / Linde Electronics / Nippon Sanso Matheson | [Air Liquide](https://electronics.airliquide.com/offer-brands/our-offer/electronics-specialty-materials) / [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) / [Nippon Sanso Matheson](https://us.nipponsanso.com/industries/electronics/) |
| 디실란(Si2H6) | 특수가스 | 증착·이온주입 | Linde Electronics / Nippon Sanso Matheson | [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) / [Nippon Sanso Matheson](https://us.nipponsanso.com/industries/electronics/) |
| 디클로로실란(DCS) | 특수가스 | 증착·이온주입 | Air Liquide / Linde Electronics | [Air Liquide](https://electronics.airliquide.com/offer-brands/our-offer/electronics-specialty-materials) / [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) |
| 고순도 암모니아(NH3) | 특수가스 | 증착·이온주입 | Air Liquide / Linde Electronics | [Air Liquide](https://electronics.airliquide.com/offer-brands/our-offer/electronics-specialty-materials) / [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) |
| 아산화질소(N2O) | 특수가스 | 산화 / 증착·이온주입 | Air Liquide / Linde Electronics | [Air Liquide](https://electronics.airliquide.com/offer-brands/our-offer/electronics-specialty-materials) / [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) |
| 포스핀(PH3) | 특수가스 | 증착·이온주입 | Air Liquide / Linde Electronics / Nippon Sanso Matheson | [Air Liquide](https://electronics.airliquide.com/offer-brands/our-offer/electronics-specialty-materials) / [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) / [Nippon Sanso Matheson](https://us.nipponsanso.com/industries/electronics/) |
| 아르신(AsH3) | 특수가스 | 증착·이온주입 | Air Liquide / Linde Electronics / Nippon Sanso Matheson | [Air Liquide](https://electronics.airliquide.com/offer-brands/our-offer/electronics-specialty-materials) / [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) / [Nippon Sanso Matheson](https://us.nipponsanso.com/industries/electronics/) |
| 디보란(B2H6) | 특수가스 | 증착·이온주입 | Air Liquide / Linde Electronics / Nippon Sanso Matheson | [Air Liquide](https://electronics.airliquide.com/offer-brands/our-offer/electronics-specialty-materials) / [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) / [Nippon Sanso Matheson](https://us.nipponsanso.com/industries/electronics/) |
| 삼불화붕소(BF3) | 특수가스 | 증착·이온주입 | Air Liquide / Linde Electronics | [Air Liquide](https://electronics.airliquide.com/offer-brands/our-offer/electronics-specialty-materials) / [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) |
| 삼염화붕소(BCl3) | 특수가스 | 식각 | Linde Electronics / Nippon Sanso Matheson | [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) / [Nippon Sanso Matheson](https://us.nipponsanso.com/industries/electronics/) |
| 브롬화수소(HBr) | 특수가스 | 식각 | Linde Electronics / Nippon Sanso Matheson | [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) / [Nippon Sanso Matheson](https://us.nipponsanso.com/industries/electronics/) |
| 고순도 염소(Cl2) | 특수가스 | 식각 | Linde Electronics | [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) |
| 삼불화질소(NF3) | 특수가스 | 증착·이온주입 | Merck KGaA / Linde Electronics | [Merck KGaA](https://www.merckgroup.com/content/dam/web/corporate/non-images/business-specifics/electronics/semiconductors/us/05_media/05b_technical-resources/EMD_Global%20Semiconductor%20Solutions%20Insights_Apr%202023.pdf) / [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) |
| 육불화에탄(C2F6) | 특수가스 | 식각 | Merck KGaA / Linde Electronics | [Merck KGaA](https://www.merckgroup.com/content/dam/web/corporate/non-images/business-specifics/electronics/semiconductors/us/05_media/05b_technical-resources/EMD_Global%20Semiconductor%20Solutions%20Insights_Apr%202023.pdf) / [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) |
| 육불화황(SF6) | 특수가스 | 식각 | Merck KGaA / Linde Electronics | [Merck KGaA](https://www.merckgroup.com/content/dam/web/corporate/non-images/business-specifics/electronics/semiconductors/us/05_media/05b_technical-resources/EMD_Global%20Semiconductor%20Solutions%20Insights_Apr%202023.pdf) / [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) |
| 옥타플루오로사이클로부탄(C4F8) | 특수가스 | 식각 | Linde Electronics | [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) |
| 트리플루오로메탄(CHF3) | 특수가스 | 식각 | Linde Electronics | [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) |
| 게르만(GeH4) | 특수가스 | 증착·이온주입 | Linde Electronics | [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) |
| 고순도 황산(H2SO4) | 세정·습식 화학품 | 산화 / 포토 | Kanto Chemical / Fujifilm | [Kanto Chemical](https://www.kanto.co.jp/english/products/denshi/ultra_pure_chemicals.html) / [Fujifilm](https://asset.fujifilm.com/master/hq/files/2023-05/03668b3ec4771d2a252242530f04be77/pdf_news_9390_en.pdf) |
| 과산화수소(H2O2) | 세정·습식 화학품 | 산화 / 식각 | Kanto Chemical / Fujifilm | [Kanto Chemical](https://www.kanto.co.jp/english/products/denshi/ultra_pure_chemicals.html) / [Fujifilm](https://asset.fujifilm.com/master/hq/files/2023-05/03668b3ec4771d2a252242530f04be77/pdf_news_9390_en.pdf) |
| 세정용 염산(HCl) | 세정·습식 화학품 | 산화 | Kanto Chemical / Fujifilm | [Kanto Chemical](https://www.kanto.co.jp/english/products/denshi/ultra_pure_chemicals.html) / [Fujifilm](https://asset.fujifilm.com/master/hq/files/2023-05/03668b3ec4771d2a252242530f04be77/pdf_news_9390_en.pdf) |
| 고순도 질산(HNO3) | 세정·습식 화학품 | 식각 | Kanto Chemical / Fujifilm | [Kanto Chemical](https://www.kanto.co.jp/english/products/denshi/ultra_pure_chemicals.html) / [Fujifilm](https://asset.fujifilm.com/master/hq/files/2023-05/03668b3ec4771d2a252242530f04be77/pdf_news_9390_en.pdf) |
| 암모니아수(NH4OH) | 세정·습식 화학품 | 산화 | Kanto Chemical / Fujifilm | [Kanto Chemical](https://www.kanto.co.jp/english/products/denshi/ultra_pure_chemicals.html) / [Fujifilm](https://asset.fujifilm.com/master/hq/files/2023-05/03668b3ec4771d2a252242530f04be77/pdf_news_9390_en.pdf) |
| 고순도 인산(H3PO4) | 세정·습식 화학품 | 식각 | Kanto Chemical / Fujifilm | [Kanto Chemical](https://www.kanto.co.jp/english/products/denshi/ultra_pure_chemicals.html) / [Fujifilm](https://asset.fujifilm.com/master/hq/files/2023-05/03668b3ec4771d2a252242530f04be77/pdf_news_9390_en.pdf) |
| 고순도 IPA | 세정·습식 화학품 | 포토 / 식각 | Kanto Chemical / Fujifilm | [Kanto Chemical](https://www.kanto.co.jp/english/products/denshi/ultra_pure_chemicals.html) / [Fujifilm](https://asset.fujifilm.com/master/hq/files/2023-05/03668b3ec4771d2a252242530f04be77/pdf_news_9390_en.pdf) |
| 포토용 PGMEA 용제 | 세정·습식 화학품 | 포토 | Kanto Chemical / Fujifilm | [Kanto Chemical](https://www.kanto.co.jp/english/products/denshi/ultra_pure_chemicals.html) / [Fujifilm](https://www.ccpc.ie/business/wp-content/uploads/sites/3/2023/06/M.23.026-Determination-Public.pdf) |
| 포토레지스트 박리액 | 세정·습식 화학품 | 식각 | Kanto Chemical / Fujifilm | [Kanto Chemical](https://www.kanto.co.jp/english/products/denshi.html) / [Fujifilm](https://asset.fujifilm.com/master/hq/files/2023-05/03668b3ec4771d2a252242530f04be77/pdf_news_9390_en.pdf) |
| 구리 CMP 슬러리 | CMP 소모재 | 금속배선 | Fujifilm / Entegris / Resonac | [Fujifilm](https://www.fujifilm.com/us/en/business/semiconductor-materials/cmp) / [Entegris](https://www.entegris.com/en/home/resources/industry-insights/chemical-mechanical-planarization.html) / [Resonac](https://eu.resonac.com/products-top/frontend/) |
| 텅스텐 CMP 슬러리 | CMP 소모재 | 금속배선 | Entegris / Fujifilm | [Entegris](https://www.entegris.com/en/home/resources/industry-insights/chemical-mechanical-planarization.html) / [Fujifilm](https://www.fujifilm.com/us/en/business/semiconductor-materials/cmp) |
| 절연막 CMP 슬러리 | CMP 소모재 | 산화 | Entegris / Fujifilm | [Entegris](https://www.entegris.com/en/home/resources/industry-insights/chemical-mechanical-planarization.html) / [Fujifilm](https://www.fujifilm.com/us/en/business/semiconductor-materials/cmp) |
| CMP 연마 패드 | CMP 소모재 | 산화 / 금속배선 | Entegris | [Entegris](https://www.entegris.com/en/home/resources/industry-insights/chemical-mechanical-planarization.html) |
| PVA CMP 세정 브러시 | CMP 소모재 | 금속배선 | Entegris | [Entegris](https://www.entegris.com/en/home/resources/industry-insights/chemical-mechanical-planarization.html) |
| Post-CMP 세정액 | CMP 소모재 | 금속배선 | Entegris / Fujifilm | [Entegris](https://www.entegris.com/en/home/resources/industry-insights/chemical-mechanical-planarization.html) / [Fujifilm](https://www.fujifilm.com/us/en/business/semiconductor-materials/cmp) |
| 에폭시 몰딩 컴파운드(EMC) | 패키징 소재 | 패키징 | Resonac | [Resonac](https://eu.resonac.com/products-top/backend/) |
| 다이 접착 페이스트 | 패키징 소재 | 패키징 | Resonac / Henkel | [Resonac](https://eu.resonac.com/products-top/backend/) / [Henkel](https://next.henkel-adhesives.com/uk/en/applications/electronic-component-protection-solutions/underfills.html) |
| 다이 접착 필름(DAF) | 패키징 소재 | 패키징 | Resonac / Henkel | [Resonac](https://eu.resonac.com/products-top/backend/) / [Henkel](https://www.henkel.com/press-and-media/press-releases-and-kits/2026-08-19-henkel-launches-loctite-ablestik-cdf900-series-conductive-die-attach-film-2223146) |
| 다이싱 테이프 | 패키징 소재 | 패키징 | Nitto Denko / Maxell | [Nitto Denko](https://www.nitto.com/us/en/markets/industry/electronic/semicon/) / [Maxell](https://biz.maxell.com/en/sliontec_tapes/list_semiconductor.html) |
| 패키징 폴리이미드(PI) | 패키징 소재 | 패키징 | Fujifilm | [Fujifilm](https://www.fujifilm.com/us/en/business/semiconductor-materials/polymides-and-pbos) |
| 플립칩 언더필 | 패키징 소재 | 패키징 | Resonac / Henkel | [Resonac](https://eu.resonac.com/products-top/backend/) / [Henkel](https://www.henkel.com/press-and-media/press-releases-and-kits/2026-08-19-henkel-launches-loctite-ablestik-cdf900-series-conductive-die-attach-film-2223146) |
| 실리콘 폴리시드 웨이퍼 추가 후보 | 웨이퍼 대체 후보 | 웨이퍼 제조 | Siltronic | [Siltronic](https://www.siltronic.com/en/products/epitaxial-wafers.html) |
| 실리콘 에피 웨이퍼 추가 후보 | 웨이퍼 대체 후보 | 웨이퍼 제조 | Siltronic | [Siltronic](https://www.siltronic.com/en/products/epitaxial-wafers.html) |
| 탄탈럼 스퍼터링 타깃 | 금속 타깃 | 금속배선 | JX Advanced Metals | [JX Advanced Metals](https://nmmjx-dc.com/en/products/ng-device/semiconductor.html) |
| 티타늄 스퍼터링 타깃 | 금속 타깃 | 금속배선 | JX Advanced Metals | [JX Advanced Metals](https://nmmjx-dc.com/en/products/ng-device/semiconductor.html) |
| 텅스텐 스퍼터링 타깃 | 금속 타깃 | 금속배선 | JX Advanced Metals / ULVAC Materials | [JX Advanced Metals](https://nmmjx-dc.com/en/products/ng-device/semiconductor.html) / [ULVAC Materials](https://www.ulvac.co.jp/en/products/materials/for_semiconductor/) |
| 코발트 스퍼터링 타깃 | 금속 타깃 | 금속배선 | JX Advanced Metals | [JX Advanced Metals](https://nmmjx-dc.com/en/products/ng-device/semiconductor.html) |
| 텅스텐·티타늄 합금 타깃(WTi) | 금속 타깃 | 금속배선 | JX Advanced Metals | [JX Advanced Metals](https://nmmjx-dc.com/en/products/ng-device/semiconductor.html) |
| 니켈·백금 합금 타깃(NiPt) | 금속 타깃 | 금속배선 | JX Advanced Metals | [JX Advanced Metals](https://nmmjx-dc.com/en/products/ng-device/semiconductor.html) |
| 코발트 증착 전구체 | 증착 전구체 | 증착·이온주입 / 금속배선 | Merck KGaA | [Merck KGaA](https://www.reports.emdgroup.com/en/annualreport/2025/management-report/fundamental-information-about-the-group/research-and-development/electronics.html) |
| 루테늄 증착 전구체 | 증착 전구체 | 증착·이온주입 / 금속배선 | Merck KGaA | [Merck KGaA](https://www.reports.emdgroup.com/en/annualreport/2025/management-report/fundamental-information-about-the-group/research-and-development/electronics.html) |
| 몰리브덴 증착 전구체 | 증착 전구체 | 증착·이온주입 / 금속배선 | Merck KGaA | [Merck KGaA](https://www.reports.emdgroup.com/en/annualreport/2025/management-report/fundamental-information-about-the-group/research-and-development/electronics.html) |
| TEOS 산화막 전구체 | 증착 전구체 | 증착·이온주입 | Merck KGaA / Fujifilm / Entegris | [Merck KGaA](https://www.emdgroup.com/content/dam/web/corporate/non-images/business-specifics/electronics/semiconductors/us/05_media/05b_technical-resources/M4Ward-datasheet-EN-US.pdf) / [Fujifilm](https://www.fujifilm.com/my/en/business/semiconductor-materials/cvd-precursors-chemical-delivery/dielectric-dopant-sources) / [Entegris](https://www.entegris.com/shop/en/USD/By-Industry/Microelectronics/Semiconductor/Deposition/Precursors/c/industries-microelectronics-semiconductor-deposition-precursors) |
| BTBAS 실리콘 전구체 | 증착 전구체 | 증착·이온주입 | Merck KGaA | [Merck KGaA](https://www.emdgroup.com/content/dam/web/corporate/non-images/business-specifics/electronics/semiconductors/us/05_media/05b_technical-resources/M4Ward-datasheet-EN-US.pdf) |
| HMDS 표면처리제 | 세정·습식 화학품 | 포토 | Fujifilm | [Fujifilm](https://www.ccpc.ie/business/wp-content/uploads/sites/3/2023/06/M.23.026-Determination-Public.pdf) |
| 고순도 아세톤 | 세정·습식 화학품 | 포토 / 식각 | Kanto Chemical | [Kanto Chemical](https://www.kanto.co.jp/english/products/denshi/ultra_pure_chemicals.html) |
| NMP 박리·용제 | 세정·습식 화학품 | 포토 / 식각 | Kanto Chemical | [Kanto Chemical](https://www.kanto.co.jp/english/products/denshi/ultra_pure_chemicals.html) |
| 고순도 메탄올 | 세정·습식 화학품 | 포토 / 식각 | Kanto Chemical | [Kanto Chemical](https://www.kanto.co.jp/english/products/denshi/ultra_pure_chemicals.html) |
| 챔버 세정 불소(F2) | 특수가스 | 증착·이온주입 | Linde Electronics | [Linde Electronics](https://www.linde-gas.com/products-and-services/gases/specialty-gases-for-electronics) |

## 검증

전체 검사 97개 통과. 신규 60종 모두 입력 인식·활성화·공정 영향 연결을 확인했습니다. 인증/램프 경계, 원료 동시 타격, 우회 끔, 패키징 이슈의 전공정 분리, 웨이퍼 병렬 대체, 누적 이슈·복구·설정 화면 실행을 확인했습니다.
