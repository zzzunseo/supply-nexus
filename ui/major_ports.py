"""Port comparison with explicitly user-selected hypothetical routing."""
import json
from pathlib import Path
import streamlit as st
import plotly.graph_objects as go
from .demo_scenarios import connections


def major_ports():
    return json.loads((Path(__file__).resolve().parents[1]/'data/major_ports.json').read_text(encoding='utf-8'))


def render_major_ports(network,standalone=False):
    with st.container() if standalone else st.expander('주요 항만 비교 · 경유 가정 검토',expanded=False):
        if standalone:st.subheader('주요 항만 · 경유 가정 검토')
        ports={p['id']:p for p in major_ports()}
        key=st.selectbox('검토 항만',list(ports),format_func=lambda k:ports[k]['name'],key='major_port')
        port=ports[key]
        st.caption('가오슝·기룽은 공식 좌표, 나머지는 공식 항만 자료의 권역을 표시한 개략 대표점입니다.  \n실제 기업별 출하항·경유항·화물 취급 적합성은 미확인입니다.')
        rows=connections(network)
        labels={str(i):network['entities'][r['supplier']]['name']+' → '+network['entities'][r['recipient']]['name']+' / '+r['material'] for i,r in enumerate(rows)}
        chosen=st.multiselect('이 항만을 경유한다고 가정할 공급 연결',list(labels),format_func=labels.get,key='major_port_routes',
            help='기업 관계 근거가 있는 연결 중 검토할 대상을 직접 선택합니다. 항만 경유 근거가 확인되는 것은 아닙니다.')
        mode=st.radio('항만 비교 상태',['정상 경유 가정','통항 제한 가정'],horizontal=True,key='major_port_state')
        selected=[rows[int(i)] for i in chosen]
        st.write(f"{port['name']} · 공급사 {len({r['supplier'] for r in selected})}곳 · 고객사 {len({r['recipient'] for r in selected})}곳 · 소재 {len({r['item'] for r in selected})}종")
        color='#ff5264' if mode=='통항 제한 가정' else '#4fe4db'
        fig=go.Figure()
        used={k for r in selected for k in (r['supplier'],r['recipient'])}
        for r in selected:
            a=network['entities'][r['supplier']]['map_location'];b=network['entities'][r['recipient']]['map_location']
            fig.add_trace(go.Scattergeo(lat=[a['lat'],port['lat'],b['lat']],lon=[a['lon'],port['lon'],b['lon']],
                mode='lines',line=dict(color=color,width=2,dash='dash'),showlegend=False,
                text=[labels[str(rows.index(r))]+' · 경유 가정']*3,hovertemplate='%{text}<extra></extra>'))
        for k in sorted(used):
            e=network['entities'][k];p=e['map_location']
            fig.add_trace(go.Scattergeo(lat=[p['lat']],lon=[p['lon']],text=[e['name']],mode='markers+text',textposition='top center',marker=dict(color='#68adff',size=8),showlegend=False))
        fig.add_trace(go.Scattergeo(lat=[p['lat'] for p in ports.values()],lon=[p['lon'] for p in ports.values()],
            text=[p['name'] for p in ports.values()],mode='markers+text',textposition='bottom center',
            marker=dict(size=[15 if p['id']==key else 7 for p in ports.values()],color=[color if p['id']==key else '#889bb0' for p in ports.values()]),showlegend=False))
        fig.update_layout(height=520,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor='#071324',font=dict(color='#dceaf8',size=11),
            geo=dict(projection_type='natural earth',bgcolor='#071324',showland=True,landcolor='#193245',showcountries=True,countrycolor='#365267'))
        st.plotly_chart(fig,key='major_ports_map',width='stretch',theme=None,config=dict(displayModeBar=False,topojsonURL='/app/static/'))
        st.caption('점선은 선택한 경유 가정의 연결도입니다.  \n해상 항적이 아니며 직선이 육지를 통과할 수 있습니다.  \n통항 제한은 검토 상태 표시이며 공급 감소·지연 일수를 계산하지 않습니다.')
        st.markdown(f"[선택 항만 공식 자료]({port['source']}) · 확인 {port['checked_at']}")
        st.caption(f"{port['precision']} · {port['lat']:.5f}°N / {port['lon']:.5f}°E")
        st.info('가오슝 좌표는 공식 제1항 입구와 일치합니다. 기존 가오슝 → 기룽 우회도 화물별 운항·하역·내륙 운송 확인이 필요한 후보입니다.')
        with st.expander('전체 항만의 위치 근거'):
            for p in ports.values():st.markdown(f"[{p['name']}]({p['source']}) · {p['precision']}")
