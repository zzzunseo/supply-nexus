"""Eight-process overview and linked supply/alternative inspection."""
import streamlit as st
from .calculation import calculate_current
from .selection import select_globe_process
from .flow_panel import render_flow_panel
from .timeline import build_timeline
from flow_data import build_flow
from resilience_globe import build_network_globe
from relationship_audit import vendor_catalog


def choose_process(process):
    st.session_state.detail_focus=None
    st.session_state.rr_focus=None
    st.session_state.rr_process=process
    select_globe_process(st.session_state)


def render_detail_analysis(network):
    st.subheader('반도체 8대 공정 · 공급망 분석')
    with st.expander('분석 조건 · 수동 사건 적용',expanded=False):
        a,b,c=st.columns(3)
        with a:st.number_input('관측 기간 · 일',1,365,key='rr_days')
        with b:st.checkbox('재고 완충 적용',key='rr_inventory')
        with c:st.checkbox('등록 대체 공급 가정 적용',key='rr_bypass')
        from .manual_scenario import render_manual_scenario
        render_manual_scenario(network)
        from .issue_manager import render_active_issues
        if st.session_state.rr_events:render_active_issues()
        if st.session_state.rr_error:st.error(st.session_state.rr_reply)
    result=calculate_current(network)
    st.session_state.rr_result=result
    columns=st.columns(4)
    for index,process in enumerate(network['processes']):
        score=result['scores'][process]
        value='미산정' if score is None else f'{score:.0f}%'
        suffix=' *' if process in result.get('incomplete_processes',{}) else ''
        with columns[index%4]:
            st.button(process+' · '+value+suffix,key='detail_process_'+str(index),width='stretch',
                type='primary' if st.session_state.rr_flow_process==process else 'secondary',
                on_click=choose_process,args=(process,))
    st.caption('수치는 등록 소재 충족도이며, *는 누락된 투입재가 있는 공정입니다.  \n실제 생산률이 아니며 공정 간 생산 감소를 자동 전파하지 않습니다.  \n공정을 선택하면 지도·흐름·대체 후보가 함께 바뀝니다.')
    process=st.session_state.rr_flow_process
    flow=build_flow(network,result,process)
    options=[None,*sorted({c['node_id'] for col in flow['columns'] for c in col['cards'] if c['node_id'] in network['entities']},key=lambda k:network['nodes'][k]['name'])]
    selected=st.session_state.get('rr_focus')
    if selected in network['entities'] and selected not in options:options.append(selected)
    if st.session_state.get('detail_focus') not in options:st.session_state.detail_focus=None
    focus=st.selectbox('기업·소재 선택',options,key='detail_focus',format_func=lambda k:network['nodes'][k]['name'] if k else '선택 공정 전체 연결')
    st.session_state.rr_focus=focus
    map_process='전체' if focus and st.session_state.rr_process=='전체' else process
    figure=build_network_globe(network,result,st.session_state.rr_view,focus,process=map_process)
    st.plotly_chart(figure,key='detail_network_globe',height=480,width='stretch',theme=None,config=dict(displayModeBar=False,topojsonURL='/app/static/',scrollZoom=True))
    st.subheader('공급 기업 → 소재 → 공정 → 영향 기업')
    render_flow_panel(network,result,compact=True)
    from .relationship_view import open_relationships,relationship_dialog
    st.button('기업·소재 연결 전체 펼쳐보기',key='rr_supply_overview',on_click=open_relationships,width='stretch')
    if st.session_state.get('rr_relationship_open'):relationship_dialog(network,result)
    st.subheader('대체 공급과 전환 절차')
    material_ids=list(dict.fromkeys(c['node_id'] for col in flow['columns'] for c in col['cards'] if c['kind']=='material'))
    if material_ids:
        material=st.session_state.get('detail_selected_material_node')
        if material not in material_ids:material=material_ids[0]
        st.session_state.detail_alternative_material=material
        st.write('검토 소재: '+network['nodes'][material]['name'])
        st.caption('흐름도에서 소재를 바꾸면 아래 후보도 함께 바뀝니다.')
        node=network['nodes'][material];reserve=network['nodes'].get(node.get('alt_vendor'),{})
        st.write('등록 대체 경로: '+reserve.get('name','등록 없음'))
        st.caption(f"모델 가정: 재고 {node['inventory_days']:g}일 · 대체 한도 {node['alt_capacity']*100:g}% · 인증 {node.get('alt_qualification_days',0)}일 · 확대 {node.get('alt_ramp_days',0)}일")
        catalog=[v for v in vendor_catalog(network) if node.get('item_id') and v['product_group']==node['item_id'] and v['supplier_id']!=node.get('company_id')]
        if catalog:st.dataframe([{'후보 벤더':v['supplier'],'제품군':v['material'],'제품 원문':v['source'],'검토 상태':'등급·고객 승인·여력 미확인'} for v in catalog],hide_index=True,column_config={'제품 원문':st.column_config.LinkColumn('제품 원문')})
        else:st.info('현재 등록된 동일 품목 후보가 없습니다.')
        st.write('제품군 확인 → 규격·순도 대조 → 샘플 평가 → 고객 승인 → 공급 여력·납기 확인 → 출하·반입')
        st.caption('제품군이 같아도 바로 대체할 수는 없습니다. 등급·고객 승인·공급 여력을 확인해야 합니다.')
    with st.expander('일별 변화 · 기업별 공정 비교'):
        views=[k for k,v in result['process_views'].items() if k in network['nodes']]
        view=st.selectbox('계산 대상 기업',views,key='detail_timeline_company',format_func=lambda k:network['nodes'][k]['name'])
        st.plotly_chart(build_timeline(result['process_views'][view]),key='detail_process_timeline',height=220,width='stretch',theme=None)
        st.dataframe([{'기업':network['nodes'][k]['name'],**v['scores']} for k,v in result['process_views'].items() if k in network['nodes']],hide_index=True)
