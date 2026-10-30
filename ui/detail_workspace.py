"""Evidence and model inspection; no presentation, news or LLM workflow."""
import streamlit as st
from .settings_tabs import source_rows,render_assumptions_tab,render_logistics_tab,render_materials_tab,render_upstream_tab,render_locations_tab


def render_detail_workspace(network):
    st.markdown('<style>.block-container{overflow-y:auto!important;padding:20px 28px!important}.block-container [data-testid="stLayoutWrapper"]{flex-shrink:0!important}</style>',unsafe_allow_html=True)
    st.button('← 영향 검토',key='rr_back_demo',on_click=lambda:st.session_state.update(rr_workspace_mode='시연 모드'))
    st.title('SUPPLY NEXUS · 상세 분석')
    st.caption('8대 공정과 공급 소재·기업·대체 경로를 함께 살펴보고, 근거와 가정을 검토합니다.')
    analysis,materials,upstream,locations,evidence,assumptions,logistics,validation=st.tabs(['8대 공정',f"소재 {len(network['extended_materials'])}종",'원료 연결','시설 위치','관계 근거','재고·대체 가정','물류 설정','계산 검증'])
    with analysis:
        from .detail_analysis import render_detail_analysis
        render_detail_analysis(network)
    with materials:
        st.subheader('소재별 공급사와 대체 경로')
        from .product_comparison import render_product_comparison
        render_product_comparison(network=network)
        render_materials_tab(network)
    with upstream:render_upstream_tab(network)
    with locations:render_locations_tab(network)
    with evidence:
        rows=source_rows(network)
        status=st.radio('근거 범위',['전체','계산 포함','참고·제외'],horizontal=True,key='detail_source_scope')
        query=st.text_input('기업·소재·공정 검색',key='detail_source_search').strip().casefold()
        shown=[r for r in rows if (status=='전체' or bool(r['계산포함'])==(status=='계산 포함')) and (not query or query in str(r).casefold())]
        st.write(f'표시 {len(shown)}개 / 전체 {len(rows)}개')
        st.caption('기업 관계 근거가 있어도 품목별 현행 계약·공급 비중·실제 물류 경유를 확정하지 않습니다.')
        st.dataframe(shown,hide_index=True,column_config={'출처':st.column_config.LinkColumn('관계 원문'),'소재출처':st.column_config.LinkColumn('품목 원문')})
    with assumptions:render_assumptions_tab(network)
    with logistics:render_logistics_tab(network)
    with validation:
        from .logistics_demo import demo_cases
        cases=demo_cases()
        index=st.selectbox('검증 사례',range(len(cases)),format_func=lambda i:cases[i]['name'],key='detail_check_case')
        days=st.number_input('계산 기간 · 일',1,365,30,key='detail_check_days')
        percent=st.slider('공급·통항 감소 가정 · %',1,100,100,key='detail_check_percent')
        inventory=st.checkbox('모델 재고 반영',value=True,key='detail_check_inventory')
        detour=st.checkbox('등록 우회 가정 반영',key='detail_check_detour',disabled=cases[index].get('kind')!='logistics')
        st.caption('조건부 모델 검증입니다. 점수는 등록 입력의 충족도이며 실제 생산률·실측 지연·매출 손실이 아닙니다.')
        if st.button('현재 가정으로 계산',key='detail_run_check'):
            from .demo import demo_results
            case=dict(cases[index],days=days,percent=percent)
            result=demo_results(network,case,inventory,False,detour)
            data=[{'기업':network['nodes'][company]['name'],'공정':process,'모델 충족도':score}
                  for company,view in result['process_views'].items() if company in network['nodes'] for process,score in view['scores'].items()]
            st.dataframe(data,hide_index=True)
            st.caption('입력: '+case['name']+f' · {days}일 · 감소 {percent}% · 재고 '+('적용' if inventory else '미적용')+' · 우회 '+('적용' if detour else '미적용'))
