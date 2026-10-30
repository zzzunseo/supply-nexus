"""Process buttons and the read-only SVG supply-flow panel."""
import html
import base64
import streamlit as st

from flow_data import build_flow
from resilience_globe import location_numbers
from .flow_svg import render_flow_svg
from .selection import select_flow_process


def render_flow_panel(network, result, compact=False):
    process = st.session_state.rr_flow_process
    st.session_state.rr_flow_process = process
    st.session_state.rr_flow_picker = None if st.session_state.rr_process == '전체' else process
    st.pills('흐름 공정', network['processes'], key='rr_flow_picker',
             selection_mode='single', required=False, label_visibility='collapsed', width='stretch',
             on_change=select_flow_process, args=(st.session_state, 'rr_flow_picker'))
    flow = build_flow(network, result, process, st.session_state.rr_focus)
    st.session_state.rr_flow_data = flow
    message = '시뮬레이션 가정 · 실제 납품·필수 사용 미확인'
    if st.session_state.rr_focus and flow['selected'] is None:
        message = '시뮬레이션 가정 · 선택 대상은 이 공정에 없음'
    elif flow['selected']:
        message = '시뮬레이션 가정 · 관련 경로 강조'
    st.markdown('<div class="rr-flow-heading">' + html.escape(process) + ' 공급 흐름 <span>' + message + '</span></div>',
                unsafe_allow_html=True)
    numbers = location_numbers(network)
    company_numbers = {
        key: numbers[node['map_location_id']]
        for key, node in network['entities'].items()
        if node['kind'] == 'company' and node.get('map_location_id') in numbers
    }
    if compact:
        from copy import deepcopy
        full=flow
        materials=[c for col in flow['columns'] for c in col['cards'] if c['kind']=='material']
        if materials:
            options=[c['id'] for c in materials]
            names={c['id']:c['name'] for c in materials}
            if st.session_state.get('detail_compact_material') not in options:st.session_state.detail_compact_material=options[0]
            selected=st.selectbox('흐름도에서 볼 소재',options,format_func=names.get,key='detail_compact_material')
            st.session_state.detail_selected_material_node=next(c['node_id'] for c in materials if c['id']==selected)
            flow=deepcopy(full)
            removed={c['id'] for c in materials if c['id']!=selected}
            flow['connections']=[e for e in flow['connections'] if e['from'] not in removed and e['to'] not in removed]
            linked={k for e in flow['connections'] for k in (e['from'],e['to'])}
            for col in flow['columns']:col['cards']=[c for c in col['cards'] if c['id'] in linked]
            flow['selected']=None
            st.caption('선택 소재의 연결만 표시합니다. 소재를 바꾸면 공급사와 공정 연결이 바뀝니다. 전체 자료는 아래에서 펼칠 수 있습니다.')
        svg=render_flow_svg(flow,company_numbers,compact=True)
        encoded=base64.b64encode(svg.encode('utf-8')).decode('ascii')
        st.html('<div style="max-width:900px;margin:auto"><img style="display:block;width:100%;max-height:430px;object-fit:contain" alt="선택 소재 공급 흐름" src="data:image/svg+xml;base64,'+encoded+'"/></div>')
        with st.expander('전체 소재·근거 흐름 펼치기',expanded=False):
            full_svg=render_flow_svg(full,company_numbers)
            st.download_button('전체 흐름도 SVG 저장',full_svg,file_name='supply-flow.svg',mime='image/svg+xml',key='detail_flow_svg_download')
            st.html('<div class="rr-flow-scroll" style="max-height:450px"><img class="rr-flow-svg" alt="전체 소재 상세 흐름" src="data:image/svg+xml;base64,'+base64.b64encode(full_svg.encode('utf-8')).decode('ascii')+'"/></div>')
        return
    svg = render_flow_svg(flow, company_numbers)
    encoded = base64.b64encode(svg.encode('utf-8')).decode('ascii')
    names = ' → '.join(column['name'] + ': ' + ', '.join(card['name'] for card in column['cards'])
                       for column in flow['columns'])
    st.html('<div class="rr-flow-scroll" data-flow-process="' + html.escape(process, quote=True) + '">'
            '<img class="rr-flow-svg" src="data:image/svg+xml;base64,' + encoded + '" '
            'alt="' + html.escape(names, quote=True) + '"/></div>')
