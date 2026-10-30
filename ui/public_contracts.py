"""Explicitly announced contracts, kept outside operational impact simulation."""
import json
from pathlib import Path
import streamlit as st
import plotly.graph_objects as go


def public_contracts():
    return json.loads((Path(__file__).resolve().parents[1]/'data/public_customer_contracts.json').read_text(encoding='utf-8'))


def render_public_contracts():
    rows=public_contracts()
    st.write('공식 계약 발표 · Air Liquide → 고객사 3곳')
    st.caption('원문 확인 2026-10-28.  \n신규 설비의 공급 계획입니다.  \n발표 당시 예정일이 지났어도 가동을 확정하지 않습니다.  \n공급 비율·재고·감소율은 미공개이며 영향 계산에 포함하지 않습니다.')
    fig=go.Figure(go.Scattergeo(lat=[r['lat'] for r in rows],lon=[r['lon'] for r in rows],
        text=[r['customer']+' · '+r['site'] for r in rows],mode='markers+text',
        marker=dict(size=12,color='#ffd166'),textposition='top center',hovertemplate='%{text}<extra>공급 대상 지역 · 계약 발표</extra>'))
    fig.update_layout(height=300,margin=dict(l=0,r=0,t=5,b=0),paper_bgcolor='#071324',font=dict(color='#dceaf8'),
        geo=dict(projection_type='natural earth',showland=True,landcolor='#193245',bgcolor='#071324',showcountries=True,countrycolor='#365267'))
    st.plotly_chart(fig,key='public_contract_map',width='stretch',theme=None,config=dict(displayModeBar=False,topojsonURL='/app/static/'))
    st.caption('점은 발표에 명시된 공급 대상 지역의 개략 위치입니다. 현지 생산 설비 계약이며 항만 경유를 추정하지 않습니다.')
    for row in rows:
        st.markdown('**'+row['supplier']+' → '+row['customer']+'** · '+row['published'])
        st.write(row['scope']+' / '+row['site'])
        st.caption(row['schedule'])
        st.markdown('[공식 계약 발표]('+row['source']+')')
    st.download_button('공개 계약 근거 내려받기',json.dumps(rows,ensure_ascii=False,indent=2),file_name='public-customer-contracts.json',mime='application/json',key='public_contract_download')
