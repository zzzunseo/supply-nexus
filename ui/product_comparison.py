"""Public product facts for review; no compatibility or recovery certification."""
import json
import streamlit as st
from product_comparison import load_comparison_data,compare_record,coverage_rows,field_text,FAMILIES,LABELS,STATUS


def render_candidates(data,records,results):
    candidates=[r for r in records if results[r['id']]['status'] in ('meets_documented','insufficient')
        and any(c['state']=='match' for c in results[r['id']]['checks'])]
    st.subheader('기업·소재 검토 후보')
    st.caption('공개 자료에서 공통 조건이 확인된 후보입니다. 고객 인증·공정 호환성·납기·공급 여력은 추가 확인 대상입니다.')
    if not candidates:
        st.info('현재 입력 조건에서 공통 근거가 확인된 후보가 없습니다. 아래 전체 비교에서 차이와 부족한 자료를 확인하세요.')
        return
    st.dataframe([{'기업':r['supplier'],'제품·소재':r['name'],
        '검토 근거':' · '.join(c['field'] for c in results[r['id']]['checks'] if c['state']=='match'),
        '자료 범위':'입력 조건 일치' if results[r['id']]['status']=='meets_documented' else '일부 조건 확인 · 추가 자료 필요'} for r in candidates],
        hide_index=True,width='stretch',height=min(320,38+len(candidates)*36))
    ids=[r['id'] for r in candidates]
    if st.session_state.get('comparison_candidate') not in ids:st.session_state.comparison_candidate=ids[0]
    selected=st.selectbox('후보별 근거 보기',ids,format_func=lambda k:next(r['supplier']+' · '+r['name'] for r in candidates if r['id']==k),key='comparison_candidate')
    record=next(r for r in candidates if r['id']==selected)
    with st.container(border=True):
        st.markdown('**'+record['supplier']+' · '+record['name']+'**')
        st.markdown('**선정 근거**')
        for check in results[selected]['checks']:
            if check['state']=='match':st.write(check['field']+' · '+check['reason'])
        missing=[c['field'] for c in results[selected]['checks'] if c['state']=='unknown']
        if missing:st.write('추가 자료 필요: '+' · '.join(missing))
        if record['notes']:st.caption(record['notes'])
        for sid in sorted({f['source_id'] for f in record['fields'].values()}):
            source=data['sources'][sid]
            st.link_button(source['title'],source['url'])
            st.caption('열람일 '+source['checked_at']+' · '+(source.get('edition') or '발행 시점 미표기'))


def comparison_matrix(records,results):
    columns={r['id']:r['supplier']+' · '+r['name']+' ['+r['id']+']' for r in records}
    rows=[{'비교 항목':'입력 조건 판정',**{columns[r['id']]:STATUS[results[r['id']]['status']] for r in records}}]
    for key in dict.fromkeys(k for r in records for k in r['fields']):
        row={'비교 항목':LABELS.get(key,key)}
        for r in records:
            fact=r['fields'].get(key)
            row[columns[r['id']]]=field_text(fact)+(' · 예시 평가 조건' if fact['basis']=='example_condition' else '') if fact else '자료 미확인'
        rows.append(row)
    rows.append({'비교 항목':'고객 승인·여유 공급량·납기',**{name:'미확인 · 별도 확인 필요' for name in columns.values()}})
    return rows


def render_side_by_side(records,results,network=None):
    st.markdown('**제품 규격 나란히 비교**')
    ids=[r['id'] for r in records]
    old=st.session_state.get('comparison_side_ids')
    if old is None or any(k not in ids for k in old):
        order={'meets_documented':0,'insufficient':1,'mismatch':2}
        st.session_state.comparison_side_ids=sorted(ids,key=lambda k:order.get(results[k]['status'],3))[:3]
    by_id={r['id']:r for r in records}
    selected=st.multiselect('나란히 볼 제품 · 최대 4개',ids,key='comparison_side_ids',max_selections=4,
        format_func=lambda k:by_id[k]['supplier']+' · '+by_id[k]['name'])
    if not selected:
        st.info('비교할 제품을 선택하세요.');return
    chosen=[by_id[k] for k in selected]
    st.dataframe(comparison_matrix(chosen,results),hide_index=True,width='stretch')
    st.caption('자료 미확인은 불일치가 아닙니다. 예시 평가 조건과 보증 규격은 구분해 확인하세요. 처음 표시되는 제품 순서는 최적 공급사 순위가 아닙니다.')
    if network is not None:
        if st.checkbox('선택 제품의 공급기업 위치 보기',key='comparison_show_locations'):
            from .research_map import render_research_map
            suppliers=list(dict.fromkeys(r['supplier'] for r in chosen))
            focus=st.selectbox('지도에서 볼 공급기업',suppliers,key='comparison_map_supplier')
            candidates=[dict(name=name,aliases=[],products=[r['name'] for r in chosen if r['supplier']==name]) for name in suppliers]
            st.caption('등록 기업의 위치 참고입니다. 해당 제품의 실제 생산·출하 공장이나 신규 공급 관계를 확정하지 않습니다.')
            render_research_map(network,'','',candidates=candidates,selected_candidate=focus)


def render_product_comparison(enable_ai=False,network=None):
    data=load_comparison_data()
    with st.expander('대체 검토 후보 · 기업과 소재 찾기',expanded=True):
        st.caption('확인일 '+data['checked_at']+' · 제품군·등급·수치 규격과 예시 평가 조건을 구분합니다. 고객 승인·계약·여유 생산량은 별도 확인 대상입니다.')
        family=st.selectbox('비교 소재군',list(FAMILIES),format_func=FAMILIES.get,key='comparison_family')
        a,b=st.columns(2)
        required={}
        with a:
            if family=='photoresist':
                required['exposure']=st.selectbox('필요 노광 제품군',['ArF','KrF','EUV','i-line'],key='comparison_exposure')
                mode=st.selectbox('노광 방식',['지정 안 함','Dry','Immersion'],key='comparison_mode')
                if mode!='지정 안 함':required['exposure_mode']=mode
                tone=st.selectbox('이미징 타입',['지정 안 함','positive','negative'],key='comparison_tone')
                if tone!='지정 안 함':required['tone']=tone
            elif family=='silicon-wafer':
                required['wafer_type']=st.selectbox('필요 웨이퍼',['PW','EPI'],key='comparison_wafer')
                diameter=st.selectbox('직경 요구',['지정 안 함','150 mm','200 mm','300 mm'],key='comparison_diameter')
                if diameter!='지정 안 함':required['diameter_mm']=int(diameter.split()[0])
                if st.checkbox('두께·저항률 범위도 비교',key='comparison_wafer_specs'):
                    if required['wafer_type']=='PW':
                        required['thickness_um']=st.number_input('요구 기판 두께 · µm',100.,1500.,725.,key='comparison_thickness')
                        required['resistivity_ohm_cm']=st.number_input('요구 기판 저항률 · Ω·cm',0.0001,10000.,10.,format='%.4f',key='comparison_resistivity')
                    else:
                        required['epi_thickness_um']=st.number_input('요구 EPI 층 두께 · µm',0.1,200.,5.,key='comparison_epi_thickness')
                        required['epi_resistivity_ohm_cm']=st.number_input('요구 EPI 저항률 · Ω·cm',0.001,10000.,1.,format='%.3f',key='comparison_epi_resistivity')
            elif family=='process-gas':
                required['chemical']=st.selectbox('가스 화학종',['NF3','CF4','SiH4','SF6','C4F8'],key='comparison_gas')
                required['min_purity_pct']=st.number_input('요구 등급 순도 · % 이상',min_value=99.0,max_value=100.0,value=99.995,step=0.001,format='%.3f',key='comparison_purity')
                if required['chemical']=='NF3' and st.checkbox('CF4 불순물 상한도 비교',key='comparison_check_cf4'):
                    required['max_cf4_ppmv']=st.number_input('요구 CF4 상한 · ppmv 이하',0,2000,25,key='comparison_cf4')
                if st.checkbox('수분 상한도 비교',key='comparison_check_water'):
                    required['max_water_ppmv']=st.number_input('요구 수분 상한 · ppmv 이하',0.1,100.,1.,step=0.1,key='comparison_water')
            elif family=='wet-chemical':
                required['chemical']=st.selectbox('약액 종류',['HF','BHF'],key='comparison_wet_chemical')
                required['product_form']=st.selectbox('제품 형태',['aqueous','anhydrous','buffered'],format_func=lambda v:{'aqueous':'수용액','anhydrous':'무수','buffered':'완충액'}[v],key='comparison_form')
                if st.checkbox('용액 농도 비교',key='comparison_concentration_on'):
                    required['concentration_pct']=st.number_input('HF 질량 농도 · mass%',min_value=0.0,max_value=100.0,value=49.0,key='comparison_concentration')
                if st.checkbox('총 금속 불순물 규격 요구',key='comparison_metal_on'):
                    required['max_metal_ppb']=st.number_input('총 금속 상한 · ppb',min_value=0.0,value=1.0,key='comparison_metal')
                st.caption('농도는 불순물 순도가 아닙니다. 고순도 등급·금속·입자·CoA·고객 승인은 추가 확인 대상입니다.')
            elif family=='cmp-abrasive':
                required['chemical']='CeO2'
                required['product_form']=st.selectbox('비교 제품 형태',['abrasive','finished-slurry'],format_func=lambda v:'연마재' if v=='abrasive' else '완성 슬러리',key='comparison_abrasive_form')
                application=st.selectbox('요구 CMP 용도',['지정 안 함','STI','ILD'],key='comparison_abrasive_application')
                if application!='지정 안 함':required['application']=application
                st.caption('연마재 자료는 완성 슬러리의 대체 승인 근거가 아닙니다. 원산지·관세 적용은 별도 확인합니다.')
            else:
                required['target_film']=st.selectbox('연마 대상 막',['Cu','barrier','Co','W','Mo','SiO2','oxide'],key='comparison_film')
                if st.checkbox('Hybrid bonding 적용 근거 요구',key='comparison_hybrid'):
                    required['application']='hybrid_bonding'
        with b:
            st.markdown('**판정 읽는 법**')
            st.write('조건 일치: 공개한 항목이 입력 조건과 일치합니다. 즉시 대체·인증 완료가 아닙니다.')
            st.write('자료 부족: 필요한 항목이 없거나 비교 기준이 다릅니다. 미생산·불가능 판정이 아닙니다.')
            st.caption('이 화면은 수집한 자료의 규칙 비교입니다. 실제 AI 호출·모델 평가 결과가 아닙니다.')
        legacy=st.checkbox('과거 카탈로그도 참고로 표시',key='comparison_legacy')
        records=[r for r in data['records'] if r['family']==family and (legacy or not r['legacy'])]
        results={r['id']:compare_record(r,required) for r in records}
        render_candidates(data,records,results)
        render_side_by_side(records,results,network)
        st.markdown('**전체 조건 비교**')
        counts=st.columns(3)
        for col,status,label in zip(counts,['meets_documented','insufficient','mismatch'],['조건 일치 항목','자료 부족 항목','조건 불일치 항목']):
            col.metric(label,sum(r['status']==status for r in results.values()))
        st.dataframe([{'기업':r['supplier'],'제품·등급':r['name'],'결과':STATUS[results[r['id']]['status']],
            '확인 항목':' / '.join(c['field']+': '+c['reason'] for c in results[r['id']]['checks'])} for r in records],hide_index=True,width='stretch',height=250)
        with st.expander('제품별 원문·규격 상세',expanded=False):
            if st.session_state.get('comparison_record') not in {r['id'] for r in records}:
                st.session_state.comparison_record=records[0]['id']
            selected=st.selectbox('제품별 원문·조건 확인',[r['id'] for r in records],format_func=lambda k:next(r['supplier']+' · '+r['name'] for r in records if r['id']==k),key='comparison_record')
            record=next(r for r in records if r['id']==selected)
            st.dataframe([{'항목':LABELS.get(key,key),'공개 값':field_text(f),
                '자료 성격':'예시 평가 조건' if f['basis']=='example_condition' else '공개 규격·등급' if f['basis'] in ('catalog_spec','catalog_grade') else '공개 항목·자료 범위',
                '자료 위치':f['locator'],'출처':data['sources'][f['source_id']]['url']} for key,f in record['fields'].items()],hide_index=True,
                column_config={'출처':st.column_config.LinkColumn('공식 원문')})
            if record['notes']:st.caption(record['notes'])
        st.caption('현재 고객 승인·추가 공급량·납기·출하 공장: 미확인. 제품 자료를 추가해도 지도 고객 연결과 계산 가정은 자동 생성하지 않습니다.')
        with st.expander('확보 범위·제외 자료·내려받기'):
            st.dataframe(coverage_rows(data),hide_index=True)
            st.caption('제품항목은 제품군·제품·등급을 함께 센 수입니다. 수치포함항목에는 예시 조건도 포함하며, 수치 비교 가능률·독립 계약 수를 의미하지 않습니다.')
            for source in data['excluded_sources']:st.write(source['reason'])
            st.download_button('출처 포함 제품 비교 데이터',json.dumps(data,ensure_ascii=False,indent=2),file_name='product-comparison-data.json',mime='application/json',key='comparison_download')
        if enable_ai:
            from .alternative_ai import render_alternative_ai
            render_alternative_ai(data,family,required,records,results)
