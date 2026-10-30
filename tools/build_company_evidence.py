"""Reviewed statements and dated response records, independent of model edges."""
import json
from pathlib import Path


def build():
    sources={}
    def source(key,title,url,edition,scope):
        sources[key]=dict(id=key,title=title,url=url,edition=edition,checked_at='2026-10-29',scope=scope,status='reviewed')
    source('company_tsmc_2025','TSMC 2025 공급사 발표','https://pr.tsmc.com/english/news/3274','2025-11-26','공급사 수상 관계. 특정 품목·등급·공장·현행 물량의 계약 아님')
    source('company_sumco_awards','SUMCO 고객 발표','https://www.sumcosi.com/english/corporate/evaluation.html','2025','TSMC·Samsung·Kioxia·Sony 관련 고객 수상·지원 기록')
    source('company_akm_fire','AKM 공장 화재 안내','https://www.akm.com/jp/ja/about-us/news/information/20201030-information/','2020-10-30','노베오카 화재·조기 복구 어려움·대체 생산 준비')
    source('company_rme_manual','RME ADI-2 DAC 매뉴얼','https://www.rme-audio.de/download/adi2dacr_e.pdf',None,'4쪽에 기록된 기존 AKM 칩과 ESS 칩 전환. 최신 모든 제품 아님')
    source('route_maersk_2026','Maersk ME11·MECL 우회 안내','https://www.maersk.com/~/media_sc9/maersk/Local%20information/Files/West%20Central%20Asia/Pakistan/overview/customer-advisory-re-routing-me11-and-mecl-service.pdf','2026-03-01','해당 날짜 서비스 우회 발표. 현재 운항편·반도체 화물 취급 보증 아님')
    source('route_hapag_gemini','Hapag-Lloyd Gemini 네트워크 안내','https://www.hapag-lloyd.com/en/services-information/news/2024/10/gemini-network-update.html','2024-10','2025-02 희망봉 네트워크 도입 결정 발표. 현재 운항 상황 별도 확인')
    source('route_wallenius_2024','Wallenius Wilhelmsen 홍해 우회 발표','https://www.walleniuswilhelmsen.com/news/red-sea-situation-vessels-re-routing-amid-safety-concerns','2024-01-09','과거 우회 결정. 자동차·장비 해상운송 사업과 반도체 화물 적합성 구분')
    profiles=[]
    for name,role,sids in [
        ('TSMC','반도체 고객·파운드리',['company_tsmc_2025']),('Samsung Electronics','반도체 고객',['company_sumco_awards']),
        ('Kioxia','메모리 고객',['company_sumco_awards']),('Sony Semiconductor Solutions','이미지센서 고객',['company_sumco_awards']),
        ('AKM','반도체 부품 제조사',['company_akm_fire']),('RME','오디오 제품 고객',['company_rme_manual']),('ESS Technology','대체 DAC 칩 제조사 기록',['company_rme_manual']),
        ('Merck','공급사 관계 발표',['company_tsmc_2025']),('Resonac','공급사 관계 발표',['company_tsmc_2025']),('Lam Research','장비 공급사 관계 발표',['company_tsmc_2025']),
        ('Maersk','컨테이너 선사 우회 발표',['route_maersk_2026']),('Hapag-Lloyd','선사 네트워크 발표',['route_hapag_gemini']),
        ('Wallenius Wilhelmsen','차량·장비 해상운송 우회 발표',['route_wallenius_2024'])]:
        profiles.append(dict(name=name,role=role,aliases=[name],source_ids=sids))
    relationships=[]
    for supplier in ['JSR','Shin-Etsu 그룹 · SEH','SUMCO','Merck','Resonac','Lam Research']:
        relationships.append(dict(supplier=supplier,customer='TSMC',kind='supplier_award',year=2025,
            statement='공식 공급사 수상 명단에 포함된 기업 관계',source_ids=['company_tsmc_2025'],
            limit=('명단 법인은 Shin-Etsu Handotai이며 그룹 전체의 계약이 아님. ' if supplier=='Shin-Etsu 그룹 · SEH' else '장비 도입과 기존 설치 장비의 운전 영향을 구분. ' if supplier=='Lam Research' else '')+'특정 공장·제품 등급·현행 물량·사건 피해를 확인한 연결이 아님'))
    for customer,statement in [('Samsung Electronics','300mm 로직용 실리콘 웨이퍼 공급 관련 기록'),('Kioxia','300mm 메모리용 웨이퍼 품질·공급 지원 기록'),('Sony Semiconductor Solutions','이미지센서 기술 개발 지원·고객 수상 관계 기록')]:
        relationships.append(dict(supplier='SUMCO',customer=customer,kind='customer_announcement',year=2025,
            statement=statement,source_ids=['company_sumco_awards'],limit='PW/EPI 세부 구성·고객별 공장·물량·실제 피해는 별도 확인'))
    relationships.append(dict(supplier='AKM',customer='RME',kind='component_adoption',year=2020,
        statement='ADI-2 DAC의 기존 AKM 칩 사용과 화재 이후 조달 제약을 매뉴얼에 기록',source_ids=['company_rme_manual'],limit='특정 제품 계열의 과거 기록 · 고객 손실 미산정'))
    responses=[dict(id='akm_rme_ess',original='AKM',alternative='ESS Technology',customer='RME',
        statement='매뉴얼에 기록된 ADI-2 DAC 버전의 AK4493 → ES9028Q2M 부품 전환',
        source_ids=['company_rme_manual'],limit='다른 AKM 고객의 호환성·즉시 대체 가능성을 뜻하지 않음')]
    routes=[]
    for key,carrier,scope,sid in [('maersk_me11_mecl','Maersk','ME11·MECL 서비스','route_maersk_2026'),
        ('hapag_gemini','Hapag-Lloyd','Gemini 네트워크 도입 결정','route_hapag_gemini'),
        ('wallenius_redsea','Wallenius Wilhelmsen','당시 홍해 통항 예정 선박 우회 발표','route_wallenius_2024')]:
        routes.append(dict(id=key,carrier=carrier,original='홍해·수에즈 방향',alternative='희망봉 방향',scope=scope,
            source_ids=[sid],status='dated_announcement',limit='출발·도착·기항·화물 취급·운항일·예약 여력·운임은 새로 확인. 현재 추천 운항편이 아님'))
    return dict(schema_version=1,checked_at='2026-10-29',sources=sources,profiles=profiles,
        relationships=relationships,responses=responses,routes=routes,
        limits=['자료상 기업 관계와 사건으로 인한 실제 고객 피해를 구분','제품 자료가 있는 벤더는 인증·공급 여력 확인 전 검토 후보',
            '우회 발표는 해당 시점 기록이며 현재 운항·화물 적합성을 보증하지 않음','엔진·지도에 새로운 고객 관계를 자동 생성하지 않음'])


if __name__=='__main__':
    data=build();path=Path(__file__).resolve().parents[1]/'data/company_response_evidence.json'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Saved',len(data['relationships']),'company relations and',len(data['routes']),'dated route records')
