"""Second reviewed batch: product conditions, complete numeric units and scope."""

def extend(data):
    sources=data['sources'];records=data['records'];date=data['checked_at']
    def source(key,title,url,scope,sha=None):
        sources[key]=dict(id=key,title=title,url=url,checked_at=date,edition=None,scope=scope,status='reviewed',sha256=sha)
    def f(value,sid,locator,basis='catalog_spec',unit=None,operator=None):
        return dict(value=value,source_id=sid,locator=locator,basis=basis,unit=unit,operator=operator)
    def add(key,supplier,name,family,fields,nid=None,kind='product_family',notes=''):
        records.append(dict(id=key,supplier=supplier,name=name,family=family,record_kind=kind,
            supplier_network_id=nid,network_mapping='exact_company' if nid else 'catalog_only',checked_at=date,
            legacy=False,fields=fields,notes=notes,customer_qualification='unverified',additional_capacity='unverified',
            lead_time_days=None,manufacturing_site=None,customer_edges=[]))
    source('fuji_arf','FUJIFILM ArF 제품 시리즈','https://www.fujifilm.com/kr/en/business/semiconductor-materials/photoresists/arf','GAR Dry / FAiRS PTI·NTI의 노광 조건 구분')
    for suffix,name,mode,tone in [('gar','GAR Series','Dry','positive'),('fairs_pti','FAiRS PTI','Immersion','positive'),('fairs_nti','FAiRS NTI','Immersion','negative')]:
        add('fujifilm_'+suffix,'FUJIFILM',name,'photoresist',{
            'exposure':f('ArF','fuji_arf','ArF 제품 소개','catalog_family'),
            'exposure_mode':f(mode,'fuji_arf',name+' 설명','catalog_family'),
            'tone':f(tone,'fuji_arf',name+' / imaging tone','catalog_family'),
            'wavelength_nm':f(193,'fuji_arf','ArF 파장','catalog_family','nm')},'fujifilm')
    source('waferworks_dsp','Wafer Works 게시 Silicon Works Tech DSP 규격','https://www.waferworks.com/uploads/dsp_spec_eng.pdf','1쪽 직경별 두께·저항률·방향·TTV. 문서 표기 법인과 현재 거래 법인은 별도 확인','b900ce9f990fd1783c9baa9bfc534788d937a4c0e25e73913d53ccca086e0ebe')
    for diameter,thickness in [(150,375),(200,400)]:
        add('swt_dsp_'+str(diameter),'Silicon Works Tech (Wafer Works 게시)','DSP '+str(diameter)+' mm','silicon-wafer',{
            'wafer_type':f('PW','waferworks_dsp','DSP 규격 / 양면 연마 웨이퍼','catalog_family'),
            'diameter_mm':f(diameter,'waferworks_dsp','Diameter','catalog_spec','mm','eq'),
            'thickness_min_um':f(thickness,'waferworks_dsp',str(diameter)+' mm / Wafer thickness','catalog_range','um'),
            'thickness_max_um':f(1000,'waferworks_dsp',str(diameter)+' mm / Wafer thickness','catalog_range','um'),
            'resistivity_min_ohm_cm':f(0.0008,'waferworks_dsp','Resistivity','catalog_range','ohm-cm'),
            'resistivity_max_ohm_cm':f(100,'waferworks_dsp','Resistivity','catalog_range','ohm-cm'),
            'orientation':f(['100','111'],'waferworks_dsp','Crystal orientation','catalog_family'),
            'ttv_um':f(1,'waferworks_dsp','TTV','catalog_spec','um','lt')},kind='grade',notes='범위의 조합별 동시 공급 보증 아님. 발행일 미표기·정확한 등급·현행 공급·법인 추가 확인.')
    source('gnc_epi','GNC Materials EPI 제품 규격','https://gncmat.com/?page_id=1616','제품 페이지의 실리콘 EPI 공통 규격. 제조 공장·개별 모델·고객 승인 아님')
    add('gnc_epi','GNC Materials','실리콘 EPI 공개 범위','silicon-wafer',{
        'wafer_type':f('EPI','gnc_epi','제품 제목','catalog_family'),
        'diameter_min_mm':f(200,'gnc_epi','Diameter','catalog_range','mm'),
        'diameter_max_mm':f(300,'gnc_epi','Diameter','catalog_range','mm'),
        'epi_thickness_min_um':f(1,'gnc_epi','EPI Thickness','catalog_range','um'),
        'epi_thickness_max_um':f(100,'gnc_epi','EPI Thickness','catalog_range','um'),
        'epi_resistivity_min_ohm_cm':f(0.1,'gnc_epi','Resistivity / EPI','catalog_range','ohm-cm'),
        'epi_resistivity_max_ohm_cm':f(50,'gnc_epi','Resistivity / EPI','catalog_range','ohm-cm')},notes='제품 공급 카탈로그이며 제조사·출하공장·고객 계약의 확인 자료가 아님. 원문 페이지에 2021 편집 시각이 있어 현행 규격 재확인 필요.')
    source('matheson_cf4','MATHESON CF4 등급표','https://us.nipponsanso.com/pdfs/puregas/halocarbon-14.pdf','1쪽 등급·불순물 열 위치 시각 확인. ULSI CO+CO2 합산과 개별값 구분','6016d7c6b578a9002fbc4f165da92f0fb8e11ac2a7609980b522b332f09de4bb')
    for suffix,grade,purity,water in [('3n5','Semicon 3N5',99.95,10),('5n','ULSI 5N',99.999,2)]:
        fields={'chemical':f('CF4','matheson_cf4','표 제목','catalog_family'),
            'purity_pct':f(purity,'matheson_cf4',grade+' / Purity','catalog_grade','%','listed'),
            'water_ppmv':f(water,'matheson_cf4',grade+' / Water','catalog_spec','ppmv','le')}
        if suffix=='5n':fields['co_co2_ppmv']=f(1,'matheson_cf4','ULSI 5N / CO2 (+CO)','catalog_spec','ppmv','le')
        add('matheson_cf4_'+suffix,'MATHESON · Nippon Sanso','CF4 '+grade,'process-gas',fields,'matheson',kind='grade',notes='빈 불순물 칸은 미확인. 다른 화학종 가스의 대체재로 해석하지 않음.')
    source('messer_cf4','Messer CF4 5.0 제품 규격','https://www.messer.be/web/specialty-gases/tetrafluoromethane','Product Specification 원문을 로컬 HTTP로 확인. 표기 %와 ppmv 상한','2cc8ed644554bcf4bcccbea251cf54398329666a56512730279caab838dbb1a5')
    add('messer_cf4_5n','Messer','CF4 5.0','process-gas',{
        'chemical':f('CF4','messer_cf4','표 제목','catalog_family'),
        'purity_pct':f(99.999,'messer_cf4','Composition','catalog_spec','%','ge'),
        'water_ppmv':f(1,'messer_cf4','H2O','catalog_spec','ppmv','le'),
        'nitrogen_ppmv':f(5,'messer_cf4','N2','catalog_spec','ppmv','le'),
        'oxygen_ppmv':f(2,'messer_cf4','O2','catalog_spec','ppmv','le')},kind='grade',notes='벨기에 공식 판매 자료의 규격. 실제 제조 국가·납기·고객 인증은 미확인.')
    source('fuji_hybrid','FUJIFILM 첨단 패키징 CMP 출시 발표','https://www.fujifilm.com/au/en/news/hq/12973','2025-09-29 출시 발표 / Cu·oxide 공존 hybrid bonding 적용. 고객 실명 미공개')
    sources['fuji_hybrid']['edition']='2025-09-29'
    add('fujifilm_hybrid','FUJIFILM','Hybrid bonding CMP 발표 제품','cmp-slurry',{
        'target_film':f(['Cu','SiO2'],'fuji_hybrid','Cu와 oxide 공존 표면 / 발표 설명','catalog_family'),
        'application':f('hybrid_bonding','fuji_hybrid','첨단 패키징 hybrid bonding','catalog_family')},'fujifilm',notes='고객 채택 발표는 있으나 고객 실명·개별 규격·현행 납품은 미확인. 공개 제거율·선택비 수치는 없음.')
    # Preserve the source's generic oxide wording instead of assuming a formula.
    records[-1]['fields']['target_film']['value']=['Cu','oxide']
    source('linde_nf3_at','Linde Austria NF3 4.5 규격','https://produkte.linde.at/spezialgase/stickstofftrifluorid_45.html','순도 및 기상 vpm 불순물 상한. 원문은 이상 부피비=몰비로 명시')
    source('efc_nf3','EFC NF3 등급 규격','https://www.efcgases.com/product/nitrogen-trifluoride/','Grade 4.5 열. 수분 보증은 EFC 용기 준비 조건이며 총 불순물 기준 판매·개별 불순물 변동 유의')
    for sid in ('linde_nf3_at','efc_nf3'):
        sources[sid]['checked_at']='2026-10-29'
    for key,supplier,sid,water,cf4,operator,note in [
        ('linde_nf3_4n5','Linde','linde_nf3_at',5,20,'le','오스트리아 공개 판매 규격. vpm은 원문의 이상 부피비=몰비 설명에 따라 ppmv로 통일. 공급 국가·납기·고객 인증·실제 제조 공장은 미확인.'),
        ('efc_nf3_4n5','EFC Gases & Advanced Materials','efc_nf3',1,25,'lt','수분 보증은 EFC가 용기를 준비한 경우에 한함. 총 불순물 기준 판매이며 개별 불순물은 소폭 변동 가능하므로 CoA 및 구매 규격 확인 필요. 고객 인증·공급 여력·제조 공장 미확인.')]:
        add(key,supplier,'NF3 Grade 4.5','process-gas',{
            'chemical':f('NF3',sid,'제품 제목 / Formula','catalog_family'),
            'purity_pct':f(99.995,sid,'Grade 4.5 / Purity','catalog_grade','%','listed'),
            'water_ppmv':f(water,sid,'Grade 4.5 / H2O 또는 Water','catalog_spec','ppmv',operator),
            'cf4_ppmv':f(cf4,sid,'Grade 4.5 / CF4 또는 Carbon Tetrafluoride','catalog_spec','ppmv',operator)
        },kind='grade',notes=note)
        records[-1]['checked_at']='2026-10-29'
    source('sumco_usa_line','SUMCO USA 제품 직경','https://www.sumcousa.com/product-line-2/','200mm 및 300mm PW·EPI 제품군. 특정 공장별 제조 제품·고객별 출하 규격을 뜻하지 않음')
    source('sk_siltron_wafer','SK siltron Si Wafer 제품군','https://www.sksiltron.com/m/en/wafer/wafer.do','PW 및 EPI의 200mm·300mm 표기. 개별 두께·저항률·고객 인증 미공개')
    for sid in ('sumco_usa_line','sk_siltron_wafer'):
        sources[sid]['checked_at']='2026-10-29'
    for r in records:
        if r['id'] in ('sumco_pw','sumco_epi'):
            r['fields']['diameters_mm']=f([200,300],'sumco_usa_line','What We Manufacture / 200mm and 300mm Polished and Epitaxial Wafers','catalog_family','mm')
            r['checked_at']='2026-10-29'
            r['notes']+=' 직경은 SUMCO USA 제품군 공개 자료에서 보강. 특정 공장·고객의 제품 등급이나 출하 가능량은 미확인.'
    for kind in ('PW','EPI'):
        add('sk_siltron_'+kind.lower(),'SK siltron',kind+' 200·300 mm','silicon-wafer',{
            'wafer_type':f(kind,'sk_siltron_wafer',kind+' 제품 설명','catalog_family'),
            'diameters_mm':f([200,300],'sk_siltron_wafer',kind+' / 200mm·300mm 표기','catalog_family','mm')
        },notes='공개 제품군 기준. 두께·저항률·결함 기준·개별 공정 적합성·고객 인증·추가 공급량·납기는 별도 확인. 제품 자료로 고객 관계를 생성하지 않음.')
        records[-1]['checked_at']='2026-10-29'
    return data
