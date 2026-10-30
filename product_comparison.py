"""Compare only cited, compatible field types. This is a data layer, not AI."""
import json
from pathlib import Path

PATH=Path(__file__).resolve().parent/'data/product_comparison.json'
FAMILIES={'photoresist':'포토레지스트','silicon-wafer':'실리콘 웨이퍼','process-gas':'공정 가스','cmp-slurry':'CMP 슬러리','wet-chemical':'습식 공정 약액','cmp-abrasive':'CMP 연마재'}
LABELS={'exposure':'노광 제품군','exposure_mode':'Dry·Immersion','tone':'포지·네거 타입','pattern':'패턴 용도',
    'wavelength_nm':'광원 파장','wafer_type':'웨이퍼 종류','diameter_mm':'요구 직경','diameter_min_mm':'공개 직경 범위 하한','diameter_max_mm':'공개 직경 범위 상한',
    'diameters_mm':'공개 직경 목록','growth_methods':'결정 성장법','chemical':'화학종','purity_pct':'표기 순도','water_ppmv':'수분 규격','nitrogen_ppmv':'질소 규격',
    'oxygen_ppmv':'산소 규격','oxygen_argon_ppmv':'산소+아르곤 규격','cf4_ppmv':'CF4 불순물 규격','cylinder_l':'용기 용적',
    'target_film':'연마 대상 막','abrasive':'연마재','example_film_nm':'예시 막두께','example_pab_c':'예시 PAB 온도',
    'example_peb_c':'예시 PEB 온도','example_bake_s':'예시 베이크 시간','example_developer_pct':'예시 현상액 농도'}
LABELS.update(product_form='제품 형태',concentration_pct='HF 용액 농도',grade_verified='고순도 등급·규격서',max_metal_ppb='총 금속 불순물 상한',max_metal_ppt='총 금속 불순물 상한',max_particle_nm='입자 크기 상한')
STATUS={'meets_documented':'공개 조건 일치 · 검토 후보','mismatch':'공개 조건 불일치','insufficient':'비교 자료 부족','reference_only':'과거 자료 · 참고 전용'}
LABELS.update(thickness_um='요구 기판 두께',thickness_min_um='기판 두께 하한',thickness_max_um='기판 두께 상한',
    resistivity_ohm_cm='요구 기판 저항률',resistivity_min_ohm_cm='기판 저항률 하한',resistivity_max_ohm_cm='기판 저항률 상한',
    epi_thickness_um='요구 EPI 층 두께',epi_thickness_min_um='EPI 층 두께 하한',epi_thickness_max_um='EPI 층 두께 상한',
    epi_resistivity_ohm_cm='요구 EPI 저항률',epi_resistivity_min_ohm_cm='EPI 저항률 하한',epi_resistivity_max_ohm_cm='EPI 저항률 상한',
    orientation='결정 방향',ttv_um='TTV 규격',co_co2_ppmv='CO+CO2 합산 규격',application='적용 공정')


def load_comparison_data():
    data=json.loads(PATH.read_text(encoding='utf-8'))
    validate_catalog(data)
    return data


def validate_catalog(data):
    if data.get('schema_version')!=1 or not isinstance(data.get('sources'),dict) or not isinstance(data.get('records'),list):
        raise ValueError('제품 비교 자료 형식을 확인하세요.')
    ids=set()
    for record in data['records']:
        if record['id'] in ids or record['family'] not in FAMILIES:
            raise ValueError('제품 ID 중복 또는 미지원 소재군입니다.')
        ids.add(record['id'])
        if record['customer_edges'] or record['customer_qualification']!='unverified' or record['additional_capacity']!='unverified':
            raise ValueError('제품 자료만으로 고객 관계·승인·공급 여력을 추가할 수 없습니다.')
        for field in record['fields'].values():
            source=data['sources'].get(field['source_id'])
            if not source or not source['url'].startswith('https://') or not field['locator'] or not source['checked_at']:
                raise ValueError('필드별 공식 출처·위치·확인일이 필요합니다.')
            if field['unit'] in ('%','ppmv','mm','nm','degC','s','L','um','ohm-cm','mass%','ppb','ppt'):
                values=field['value'] if isinstance(field['value'],list) else [field['value']]
                if any(isinstance(v,bool) or not isinstance(v,(int,float)) for v in values):
                    raise ValueError('수치 규격의 단위·값 형식을 확인하세요.')
            if source['status']=='legacy_reference' and not record['legacy']:
                raise ValueError('과거 자료는 참고 전용으로 표시해야 합니다.')


def compare_record(record,requirements):
    if record['legacy']:
        return dict(status='reference_only',checks=[dict(field='자료 시점',state='unknown',reason='과거 카탈로그 · 현행 제품·공급 여부 추가 확인')])
    fields=record['fields'];checks=[]
    def add(key,state,reason):checks.append(dict(field=LABELS.get(key,key),state=state,reason=reason))
    for key,wanted in requirements.items():
        if wanted is None:continue
        if key=='concentration_pct':
            field=fields.get(key)
            if not field or field.get('unit')!='mass%' or field.get('operator')!='eq':
                add(key,'unknown','질량 농도의 명시적인 표기가 없습니다. 순도·SDS 성분 범위로 대신 판단하지 않습니다.')
            else:
                add(key,'match' if field['value']==wanted else 'mismatch',f"표기 농도 {field['value']:g} mass% / 요구 {wanted:g} mass% · 보증 허용오차·CoA 별도 확인")
            continue
        if key in ('max_metal_ppb','max_metal_ppt','max_particle_nm'):
            field_key={'max_metal_ppb':'metal_ppb','max_metal_ppt':'metal_ppt','max_particle_nm':'particle_nm'}[key]
            field=fields.get(field_key);unit={'max_metal_ppb':'ppb','max_metal_ppt':'ppt','max_particle_nm':'nm'}[key]
            if not field or field.get('unit')!=unit or field.get('operator') not in ('le','lt') or field.get('basis')!='catalog_spec':
                add(key,'unknown','동일 단위·측정 기준의 보증 상한 자료 부족. 개별 금속과 총 금속, 대표값과 보증치를 구분해야 합니다.')
            else:add(key,'match' if field['value']<=wanted else 'mismatch',f"명시 상한 {field['value']} {unit} / 요구 {wanted} {unit} 이하")
            continue
        if key=='diameter_mm':
            listed=fields.get('diameters_mm',{}).get('value')
            if listed is not None:
                add(key,'match' if wanted in listed else 'mismatch','공개 직경 목록 '+str(listed)+' mm · 개별 등급·공급 여부 별도 확인');continue
            exact=fields.get('diameter_mm',{}).get('value')
            if exact is not None:
                add(key,'match' if wanted==exact else 'mismatch','직경 표기와 '+('일치' if wanted==exact else '불일치'));continue
            lo=fields.get('diameter_min_mm',{}).get('value');hi=fields.get('diameter_max_mm',{}).get('value')
            if hi is not None and wanted>hi or lo is not None and wanted<lo:add(key,'mismatch','요구 직경이 공개 범위를 벗어남')
            elif hi==wanted or lo is not None and hi is not None and lo<=wanted<=hi:add(key,'match','공개 직경 범위와 일치 · 개별 등급·공급 별도 확인')
            else:add(key,'unknown','요구 직경의 완성 웨이퍼 규격 자료 부족')
            continue
        ranges={'thickness_um':('thickness_min_um','thickness_max_um'),
            'resistivity_ohm_cm':('resistivity_min_ohm_cm','resistivity_max_ohm_cm'),
            'epi_thickness_um':('epi_thickness_min_um','epi_thickness_max_um'),
            'epi_resistivity_ohm_cm':('epi_resistivity_min_ohm_cm','epi_resistivity_max_ohm_cm')}
        if key in ranges:
            lo_key,hi_key=ranges[key];lo=fields.get(lo_key);hi=fields.get(hi_key)
            if not lo or not hi or lo['unit']!=hi['unit']:
                add(key,'unknown','동일 기준의 공개 범위 자료 부족')
            else:
                passed=lo['value']<=wanted<=hi['value']
                add(key,'match' if passed else 'mismatch',f"공개 범위 {lo['value']:g}~{hi['value']:g} {lo['unit']} / 요구 {wanted:g} · 조합별 공급 보증 아님")
            continue
        field_key={'min_purity_pct':'purity_pct','max_cf4_ppmv':'cf4_ppmv','max_water_ppmv':'water_ppmv'}.get(key,key)
        field=fields.get(field_key)
        if not field:
            add(field_key,'unknown','해당 항목을 이번 자료에서 확인하지 못함');continue
        if field['basis']=='example_condition':
            add(field_key,'unknown','예시 평가 조건은 보증 성능·허용 공정창으로 판정하지 않음');continue
        value=field['value']
        if key=='min_purity_pct':
            if field['unit']!='%' or field['basis'] not in ('catalog_grade','catalog_spec'):
                add(field_key,'unknown','등급 순도와 동일 기준으로 비교할 수 없음');continue
            passed=value>=wanted
            add(field_key,'match' if passed else 'mismatch',f'공개 등급 표기 {value:g}% / 요구 {wanted:g}% 이상 · CoA 별도 확인')
        elif key.startswith('max_'):
            if field['unit']!='ppmv' or field['operator'] not in ('le','lt'):
                add(field_key,'unknown','명시적인 ppmv 상한 규격이 없어 자동 충족 판단 보류');continue
            passed=value<=wanted
            sign='<' if field['operator']=='lt' else '≤'
            add(field_key,'match' if passed else 'mismatch',f'공개 상한 {sign}{value:g} ppmv / 요구 ≤{wanted:g} ppmv')
        else:
            if key=='target_film' and wanted=='SiO2' and (value=='oxide' or isinstance(value,list) and 'oxide' in value):
                add(field_key,'unknown','원문은 oxide로만 표기 · SiO2 적용을 별도로 확인');continue
            passed=wanted in value if isinstance(value,list) else wanted==value
            add(field_key,'match' if passed else 'mismatch','공개 제품 항목과 요구 조건 '+('일치' if passed else '불일치 · 해당 등록 항목에 대한 판단'))
    states={c['state'] for c in checks}
    status='mismatch' if 'mismatch' in states else 'insufficient' if not checks or 'unknown' in states else 'meets_documented'
    return dict(status=status,checks=checks)


def field_text(field):
    value=field['value']
    text=' / '.join(map(str,value)) if isinstance(value,list) else str(value)
    return {'le':'≤','lt':'<','ge':'≥','gt':'>'}.get(field['operator'],'')+text+(' '+field['unit'] if field['unit'] else '')


def coverage_rows(data):
    rows=[]
    for key,label in FAMILIES.items():
        records=[r for r in data['records'] if r['family']==key]
        numeric=[r for r in records if any(isinstance(f['value'],(int,float)) and not isinstance(f['value'],bool) for f in r['fields'].values())]
        rows.append(dict(소재군=label,벤더=len({r['supplier'] for r in records}),제품항목=len(records),수치포함항목=len(numeric),과거참고항목=sum(r['legacy'] for r in records)))
    return rows
