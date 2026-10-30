"""Curated official-source facts. Rebuild only the comparison seed, never graph edges."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CHECKED='2026-10-29'


def build():
    sources={}
    def source(key,title,url,scope,edition=None,legacy=False,sha256=None):
        sources[key]=dict(id=key,title=title,url=url,checked_at=CHECKED,edition=edition,
            scope=scope,status='legacy_reference' if legacy else 'reviewed',sha256=sha256)
    source('jsr_business','JSR 전자재료 제품군','https://www.jsr.co.jp/jsr_e/products/em/biz/','광원별 PR 목록 · 개별 제품 규격 아님')
    source('jsr_arf','JSR ArF 제품 카탈로그','https://www.jsr.co.jp/jsr_e/products/assets/pdf/JSR%20Photoresist%20Materials_ArF_21.pdf','1쪽 제품명·Dry 표기 · CD 도표는 호환성 수치로 사용하지 않음',sha256='77c6733912fcfe9834717d20a8dab2f40f51667e3a649f7d6b25e967fc27cff0')
    source('dongjin','동진쎄미켐 반도체 소재','https://www.dongjin.com/en/business/semiconductor.php','Introduction의 PR 세부 제품군')
    source('tok_arf','TOK ArF 제품·예시 조건','https://www.tok-pr.com/en/products/photoresist/arf.html','TARF-P6111의 예시 평가 조건 · 허용 공정창 아님')
    source('tok_krf','TOK KrF 제품·예시 조건','https://www.tok-pr.com/en/products/photoresist/krf.html','TDUR-P3435의 예시 평가 조건 · 보증 성능 아님')
    source('tok_euv','TOK EUV 제품군','https://www.tok-pr.com/en/products/photoresist/euv.html','EUV 광원 및 사업 소개 · 특정 고객 승인 아님')
    source('sumco','SUMCO 웨이퍼 목록','https://www.sumcosi.com/english/products/lineup.html','완성 웨이퍼 종류 · 슬라이싱 약 1mm를 완성품 두께로 사용하지 않음')
    source('seh','Shin-Etsu 웨이퍼 목록','https://www.shinetsu.co.jp/en/products/semiconductor-silicon-business/silicon-wafers/','Series Name · 원료 순도와 잉곳 치수는 완성 웨이퍼 규격으로 사용하지 않음')
    source('siltronic_pw','Siltronic PW','https://www.siltronic.com/en/products/polished-wafers.html','공개 직경 범위·성장법 · 개별 등급 보증 아님')
    source('siltronic_epi','Siltronic 실리콘 EPI','https://www.siltronic.com/en/products/epitaxial-wafers.html','실리콘 EPI 최대 직경 · GaN 개발 항목과 구분')
    source('al_nf3','Air Liquide Singapore 전자 가스','https://sg.airliquide.com/buy-high-purity-electronic-gases-singapore','NF3 제품 순도·용기 · 싱가포르 판매 페이지, 제조 공장 자료 아님')
    source('matheson_nf3','MATHESON NF3 등급표','https://us.nipponsanso.com/pdfs/puregas/nitrogen-trifluoride.pdf','1쪽 3개 등급의 순도·불순물 한도 · PDF 열 위치 시각 확인',sha256='60319a007a8ac0c6e95fba0f201a5ce694e2d11c31bd835a39a1814cea28de97')
    source('sk_nf3','SK specialty 표기 NF3 규격','https://skspecialty.com/new/eng/html/products/nf3.asp','제품 표의 명시 수치 · 기존 SK materials 그룹 노드와 법인 동일성은 미확정')
    source('fuji_cmp','FUJIFILM CMP 제품군','https://www.fujifilm.com/us/en/business/semiconductor-materials/cmp','구리·배리어·코발트 적용 구분 · 수치 성능 미공개')
    source('fujimi_topics','FUJIMI 금속막 CMP 소개','https://www.fujimiinc.co.jp/english/service/cmp/topics.html','금속막 Cu/W 적용 제품군 · 개별 모델 규격 아님')
    source('fujimi_old','FUJIMI PLANERLITE 과거 카탈로그','https://www.fujimiinc.co.jp/service/catalog/file/planerlite.pdf','1~2쪽 대상 막·연마재 · 현행 공급 여부 미확인',edition='H23.06 ver1.2 (2011-06)',legacy=True,sha256='33d6131fae0d1d544ed7271020a8c822219419a6897db661881774781026ab4d')
    records=[]
    def fact(value,sid,locator,basis='catalog_family',unit=None,operator=None):
        return dict(value=value,source_id=sid,locator=locator,basis=basis,unit=unit,operator=operator)
    def record(key,supplier,name,family,kind,fields,network_id=None,mapping='exact_company',legacy=False,notes=''):
        records.append(dict(id=key,supplier=supplier,name=name,family=family,record_kind=kind,
            supplier_network_id=network_id,network_mapping=mapping if network_id else 'catalog_only',
            checked_at=CHECKED,legacy=legacy,fields=fields,notes=notes,
            customer_qualification='unverified',additional_capacity='unverified',lead_time_days=None,
            manufacturing_site=None,customer_edges=[]))
    def pr(key,supplier,name,exposure,sid,nid,mode=None,extra=None):
        f={'exposure':fact(exposure,sid,'제품군 또는 해당 제품 항목')}
        if mode:f['exposure_mode']=fact(mode,sid,'Dry / Immersion 표기')
        f.update(extra or {})
        record(key,supplier,name,'photoresist','named_product' if key.startswith(('jsr_ar2772','tok_t')) else 'product_family',f,nid)
    pr('jsr_ar2772','JSR','AR2772JN','ArF','jsr_arf','jsr','Dry')
    pr('jsr_krf','JSR','KrF 제품군','KrF','jsr_business','jsr')
    pr('jsr_euv','JSR','EUV 제품군','EUV','jsr_business','jsr')
    for key,label,exposure,mode in [('arf_dry','ArF Dry','ArF','Dry'),('arf_immersion','ArF Immersion','ArF','Immersion'),('krf','KrF','KrF',None),('iline','i-Line','i-line',None)]:
        pr('dongjin_'+key,'Dongjin Semichem',label+' 제품군',exposure,'dongjin','dongjin',mode)
    pr('tok_tarf_p6111','Tokyo Ohka Kogyo','TARF-P6111','ArF','tok_arf','tok',extra={
        'tone':fact('positive','tok_arf','Positive ArF Resist for Lines'),
        'pattern':fact('line','tok_arf','TARF-P6111의 적용 구분'),
        'example_film_nm':fact(250,'tok_arf','TARF-P6111 / Resist Thickness','example_condition','nm'),
        'example_pab_c':fact(130,'tok_arf','TARF-P6111 / P.A.B','example_condition','degC'),
        'example_peb_c':fact(130,'tok_arf','TARF-P6111 / P.E.B','example_condition','degC'),
        'example_bake_s':fact(60,'tok_arf','TARF-P6111 / P.A.B, P.E.B','example_condition','s'),
        'example_developer_pct':fact(2.38,'tok_arf','TARF-P6111 / TMAH','example_condition','%')})
    pr('tok_tdur_p3435','Tokyo Ohka Kogyo','TDUR-P3435','KrF','tok_krf','tok',extra={
        'tone':fact('positive','tok_krf','Positive KrF Resist for Lines'),
        'pattern':fact('line','tok_krf','TDUR-P3435의 적용 구분'),
        'example_film_nm':fact([190,250],'tok_krf','TDUR-P3435 / Resist Thickness','example_condition','nm'),
        'example_pab_c':fact(100,'tok_krf','TDUR-P3435 / Pre-bake','example_condition','degC'),
        'example_peb_c':fact(110,'tok_krf','TDUR-P3435 / P.E.B','example_condition','degC')})
    pr('tok_euv','Tokyo Ohka Kogyo','EUV 제품군','EUV','tok_euv','tok',extra={'wavelength_nm':fact(13.5,'tok_euv','본문 EUV 파장','catalog_family','nm')})
    for supplier,nid,sid in [('SUMCO','sumco','sumco'),('Shin-Etsu 그룹 · SEH','shinetsu','seh'),('Siltronic','siltronic','siltronic_pw')]:
        for wafer in ('PW','EPI'):
            src='siltronic_epi' if nid=='siltronic' and wafer=='EPI' else sid
            fields={'wafer_type':fact(wafer,src,'제품 종류')}
            if nid=='siltronic':
                if wafer=='PW':fields.update(diameter_min_mm=fact(200,src,'공개 직경 범위','catalog_range','mm'),diameter_max_mm=fact(300,src,'공개 직경 범위','catalog_range','mm'),growth_methods=fact(['CZ','FZ'],src,'성장법'))
                else:fields['diameter_max_mm']=fact(300,src,'실리콘 EPI 최대 직경','catalog_range','mm')
            record(nid+'_'+wafer.lower(),supplier,wafer+' 실리콘 웨이퍼','silicon-wafer','product_family',fields,nid,
                mapping='group_reference' if nid=='shinetsu' else 'exact_company',notes='직경·저항률·결정 방향·결함·고객 승인 규격은 제품별 추가 확인. 원료 순도·잉곳 직경을 전용하지 않음.')
    record('al_nf3_sg','Air Liquide','NF3 · Singapore 공개 제품','process-gas','grade',{
        'chemical':fact('NF3','al_nf3','공급 옵션 표'),
        'purity_pct':fact(99.995,'al_nf3','NF3 행','catalog_grade','%','listed'),
        'cylinder_l':fact(47,'al_nf3','NF3 행','catalog_spec','L','listed')},'airliquide')
    for suffix,grade,purity,oxygen,nitrogen,cf4 in [('2n7','Semicon 2N7',99.7,None,700,1500),('4n','ULSI 4N',99.99,10,10,40),('4n5','ULSI 4N5',99.995,5,5,25)]:
        fields={'chemical':fact('NF3','matheson_nf3','표 제목'),'purity_pct':fact(purity,'matheson_nf3',grade+' / Purity','catalog_grade','%','listed'),
            'water_ppmv':fact(1,'matheson_nf3',grade+' / Water','catalog_spec','ppmv','le'),
            'nitrogen_ppmv':fact(nitrogen,'matheson_nf3',grade+' / Nitrogen','catalog_spec','ppmv','le'),
            'cf4_ppmv':fact(cf4,'matheson_nf3',grade+' / Carbon Tetrafluoride','catalog_spec','ppmv','le')}
        if oxygen is not None:fields['oxygen_ppmv']=fact(oxygen,'matheson_nf3',grade+' / Oxygen','catalog_spec','ppmv','le')
        else:fields['oxygen_argon_ppmv']=fact(700,'matheson_nf3',grade+' / Oxygen and Argon','catalog_spec','ppmv','le')
        record('matheson_nf3_'+suffix,'MATHESON · Nippon Sanso','NF3 '+grade,'process-gas','grade',fields,'matheson',notes='등급별 불순물 표의 빈 칸은 0이 아닌 미확인. 현행 판매·납기는 별도 확인.')
    record('sk_nf3','SK specialty (자료 표기)','NF3 99.999% 공개 규격','process-gas','grade',{
        'chemical':fact('NF3','sk_nf3','SPECIFICATION'),
        'purity_pct':fact(99.999,'sk_nf3','NF3 행','catalog_grade','%','listed'),
        'water_ppmv':fact(1,'sk_nf3','H2O 행','listed_value','ppmv','listed'),
        'cf4_ppmv':fact(10,'sk_nf3','CF4 행','listed_value','ppmv','listed')},'sk-materials',mapping='group_reference',notes='불순물 표의 비교 연산자가 없어 자동 상한 충족 판정은 보류. 기존 그룹 노드와 개별 법인의 동일성·현재 공급은 미확정.')
    for suffix,target,label in [('cu','Cu','Copper'),('barrier','barrier','Barrier'),('co','Co','Cobalt')]:
        record('fujifilm_'+suffix,'FUJIFILM',label+' CMP 제품군','cmp-slurry','product_family',{
            'target_film':fact(target,'fuji_cmp',label+' 제품 설명')},'fujifilm',notes='제거율·선택비·결함·패드·희석 조건의 수치 자료는 추가 확보 필요.')
    record('fujimi_metal','FUJIMI','Cu/W 금속막 CMP 제품군','cmp-slurry','product_family',{
        'target_film':fact(['Cu','W'],'fujimi_topics','금속막 연마 항목')},notes='새 벤더 제품 자료만 확보. 기존 고객 계약·지도 연결을 추가하지 않음.')
    for series,target,page in [('4000','SiO2',1),('7000','Cu',2),('8000','barrier',2)]:
        record('fujimi_'+series,'FUJIMI','PLANERLITE-'+series+' series','cmp-slurry','product_family',{
            'target_film':fact(target,'fujimi_old',str(page)+'쪽 / 해당 시리즈'),
            'abrasive':fact('silica','fujimi_old',str(page)+'쪽 / 해당 시리즈')},legacy=True,notes='2011-06 판 카탈로그. 현행 제품·공급 여부 확인 전 기본 비교에서 제외.')
    return dict(schema_version=1,checked_at=CHECKED,sources=sources,records=records,
        excluded_sources=[
            dict(url='https://tw.airliquide.com/sites/al_tw/files/2022-06/alfe-0049-cf4-v10-20220221.pdf',reason='SDS의 >=99% 성분 표기를 반도체 등급 순도 보증으로 사용할 수 없어 수치 비교에서 제외'),
            dict(url='https://lifesciences.entegris.com/content/dam/shared-product-assets/holistic-solutions/brochure-synergies-to-improve-cmp-yield-11649.pdf',reason='다른 페이지로 리디렉션되어 본문 재확인 실패. 검색 요약만으로 현행 제품 데이터를 추가하지 않음'),
            dict(url='https://www.fujimi.com/catalog/planerlite-7000/',reason='원문 재접속 시간 초과. 별도로 확인한 공식 제품군·과거 카탈로그와 구분')],
        limits=['공개 제품 자료의 비교이며 인증·계약·재고·공급 여력·즉시 대체 가능성을 입증하지 않음',
            '미등록·미기재는 미생산·불가능·수치 0을 의미하지 않음','예시 평가 조건은 보증 성능·허용 공정창이 아님',
            'checked_at은 열람일이며 자료 발행일·현재 출하 가능 여부와 다름'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    from extend_comparison_seed import extend
    data=extend(build())
    path=ROOT/'data/product_comparison.json'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Saved',len(data['records']),'product records and',len(data['sources']),'sources:',path)
