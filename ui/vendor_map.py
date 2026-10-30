"""Product catalog geography, with only registered relationship overlays."""
import streamlit as st
import plotly.graph_objects as go
from .demo_scenarios import connections


def vendor_map_data(network,item,catalog):
    vendors={r['supplier_id'] for r in catalog if r['product_group']==item}
    rows=[r for r in connections(network) if r['item']==item and r['supplier'] in vendors]
    linked={r['supplier'] for r in rows}
    customers={r['recipient'] for r in rows}
    markers=[]
    for key in sorted(vendors|customers):
        entity=network['entities'][key];place=entity.get('map_location')
        if not place:continue
        role='customer' if key in customers else 'linked' if key in linked else 'product'
        markers.append(dict(id=key,name=entity['name'],lat=place['lat'],lon=place['lon'],role=role))
    return dict(markers=markers,rows=rows,vendors=len(vendors),customers=len(customers),
                missing=len((vendors|customers)-{m['id'] for m in markers}))


def render_vendor_map(network,item,catalog):
    data=vendor_map_data(network,item,catalog)
    st.write(f"선택 소재 · 벤더 {data['vendors']}곳 / 등록 고객 {data['customers']}곳")
    st.caption('청록: 공급 관계 근거가 있는 벤더 · 금색: 제품 자료만 있는 벤더 · 파랑: 등록 고객.  \n선은 기업 관계와 제품 용도를 연결한 검토 경로이며 현재 품목 계약·물량은 별도 확인합니다.')
    figure=go.Figure();lookup={m['id']:m for m in data['markers']}
    for row in data['rows']:
        if row['supplier'] not in lookup or row['recipient'] not in lookup:continue
        a,b=lookup[row['supplier']],lookup[row['recipient']]
        figure.add_trace(go.Scattergeo(lat=[a['lat'],b['lat']],lon=[a['lon'],b['lon']],mode='lines',
            line=dict(color='#4fe4db',width=2),text=[a['name']+' → '+b['name']]*2,
            hovertemplate='%{text}<extra>등록 관계 검토 경로</extra>',showlegend=False))
    for role,label,color in [('linked','공급 관계 근거','#4fe4db'),('product','제품 자료 · 고객 미연결','#ffd166'),('customer','등록 고객','#68adff')]:
        points=[m for m in data['markers'] if m['role']==role]
        if not points:continue
        figure.add_trace(go.Scattergeo(lat=[m['lat'] for m in points],lon=[m['lon'] for m in points],
            text=[m['name'] for m in points],mode='markers+text',name=label,textposition='top center',
            marker=dict(size=10,color=color),hovertemplate='%{text}<extra>'+label+'</extra>'))
    figure.update_layout(height=360,margin=dict(l=0,r=0,t=10,b=0),paper_bgcolor='#071324',
        font=dict(color='#dceaf8',size=11),legend=dict(orientation='h'),
        geo=dict(projection_type='natural earth',bgcolor='#071324',showland=True,landcolor='#193245',
                 showocean=True,oceancolor='#071324',showcountries=True,countrycolor='#365267'))
    st.plotly_chart(figure,key='audit_vendor_map',width='stretch',theme=None,
                    config=dict(displayModeBar=False,topojsonURL='/app/static/'))
    st.caption('기업 대표 거점입니다. 생산 공장·출하항·실제 화물 경로를 뜻하지 않습니다.'+ (f" 위치 미등록 {data['missing']}곳은 목록에서 확인하세요." if data['missing'] else ''))

    from .public_contracts import public_contracts
    announced=[r for r in public_contracts() if item in r['materials'] and any(v['supplier_id']==r['supplier_id'] for v in catalog)]
    if announced:
        st.write(f'별도 공개 계약 발표 · 고객사 {len(announced)}곳 · 공급 가동 미확인')
        for row in announced:
            st.markdown('['+row['supplier']+' → '+row['customer']+']('+row['source']+') · '+row['published'])
            st.caption(row['scope']+' / '+row['schedule'])
