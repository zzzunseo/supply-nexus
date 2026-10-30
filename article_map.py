"""Read-only article associations, independent of all simulation results."""
import html
import math

import plotly.graph_objects as go
from resilience_globe import great_circle


STYLES = {
    'supply': ('#67E3F0', 'solid', '기업 간 공급관계 근거'),
    'reference': ('#96A7BB', 'dot', '참고 관계'),
    'assumption': ('#B7A1EE', 'dash', '추가 경로 가정'),
}


def registered_anchor(network, key):
    node = network['nodes'].get(key, {})
    if node.get('company_id'):
        node = network['nodes'].get(node['company_id'], {})
    location = network.get('locations', {}).get(node.get('map_location_id'))
    if not location or location.get('company_id') != node.get('id') or not location.get('source') or not location.get('coordinate_source'):
        return None
    lat, lon = location.get('lat'), location.get('lon')
    if type(lat) not in (int,float) or type(lon) not in (int,float):
        return None
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        return None
    return dict(id=node['map_location_id'], name=location['name'], company=node['name'],
                lat=lat, lon=lon, location_type=location['location_type'],
                source=location['source'], coordinate_source=location['coordinate_source'])


def article_map_data(network, review):
    """Resolve only reviewed route IDs against the current registered graph."""
    edges = {}
    for edge in network['visual_edges']:
        key = edge['backbone_id'] if edge['kind']=='backbone' else edge['id']
        if key in edges:
            raise ValueError('등록 경로 ID가 중복되어 기사 지도를 생성할 수 없습니다.')
        edges[key] = edge
    routes = []
    for saved in review.get('routes', []):
        edge = edges.get(saved['id'])
        if edge is None:
            routes.append(dict(id=saved['id'], mapped=False, reason='현재 등록 데이터에서 해당 경로를 찾을 수 없음',
                               label=saved['supplier']+' → '+saved['material']+' → '+saved['recipient']))
            continue
        evidence = edge.get('evidence', {})
        if edge['kind']=='backbone':
            source_id, target_id = evidence['from'], evidence['to']
            decision = network['relationship_decisions'][edge['backbone_id']]
            kind = 'supply' if decision['included'] else 'reference'
            source = evidence.get('relationship_source')
            material = evidence['item']
            reason = decision['reason']
        else:
            source_id, target_id = edge['from'], edge['to']
            kind, material = 'assumption', saved['material']
            source = edge.get('source') or network['nodes'][source_id].get('source')
            reason = '소재 용도에 따른 모델 추가 연결 · 실제 납품 관계 미확인'
        a, b = registered_anchor(network, source_id), registered_anchor(network, target_id)
        missing = [network['nodes'][key]['name'] for key,anchor in ((source_id,a),(target_id,b)) if anchor is None]
        same = bool(a and b and (a['lat'],a['lon'])==(b['lat'],b['lon']))
        supplier = network['nodes'][source_id]
        if supplier.get('company_id'):
            supplier = network['nodes'][supplier['company_id']]
        label = supplier['name']+' → '+material+' → '+network['nodes'][target_id]['name']
        routes.append(dict(id=saved['id'], label=label, supplier=supplier['name'], material=material,
                           recipient=network['nodes'][target_id]['name'], processes=list(edge.get('processes',[])),
                           kind=kind, basis=STYLES[kind][2], source=source, reason=reason,
                           mapped=bool(a and b and not same), anchors=[a,b],
                           missing=missing, coincident=same,
                           location_note='등록된 기업·사업장 위치 · 기사 속 사건 발생 장소로 확인된 위치가 아님'))
    return dict(routes=routes, article_id=review['article']['id'],
                article_quote=review.get('excerpt'), event_location_verified=False,
                notice='기사 관련 등록 관계만 표시 · 실제 고객 피해·공급량·사건 장소를 판정하지 않음')


def build_article_globe(payload, selected=None):
    fig = go.Figure()
    anchors = {}
    center = None
    mapped = [row for row in payload['routes'] if row['mapped']]
    for index,row in enumerate(mapped,1):
        a,b = row['anchors']
        anchors[a['id']], anchors[b['id']] = a,b
        lat,lon = great_circle(a,b,65)
        color,dash,basis = STYLES[row['kind']]
        picked = selected==row['id']
        tip = html.escape(row['label'])+'<br>'+basis+' · 해당 품목의 현행 계약·고객 피해 미확인<br>개략 관계선 · 실제 운송 경로 아님'
        fig.add_trace(go.Scattergeo(lat=lat,lon=lon,mode='lines',
            line=dict(color=color,dash=dash,width=3.5 if picked else 2),
            opacity=1 if picked or selected is None else .28,
            text=[tip]*len(lat),hovertemplate='%{text}<extra></extra>',showlegend=False,
            meta=dict(article_route_id=row['id'],basis=row['kind'])))
        middle=len(lat)//2
        fig.add_trace(go.Scattergeo(lat=[lat[middle]],lon=[lon[middle]],mode='markers+text',
            marker=dict(size=17 if picked else 13,color=color,symbol='diamond',line=dict(width=1,color='#E8F6FF')),
            text=[str(index)],textposition='top center',textfont=dict(size=12,color='#EDF6FF'),
            customdata=[row['id']],hovertext=[tip+'<br>이 선택점을 클릭하면 근거 표시'],
            hovertemplate='%{hovertext}<extra></extra>',showlegend=False,
            selected=dict(marker=dict(opacity=1)),unselected=dict(marker=dict(opacity=1))))
        if picked or center is None:
            center = (lon[middle],lat[middle])
    for anchor in anchors.values():
        tip = html.escape(anchor['company']+' · '+anchor['name'])+'<br>등록 위치 · 사건 발생 장소 미확인'
        fig.add_trace(go.Scattergeo(lat=[anchor['lat']],lon=[anchor['lon']],mode='markers+text',
            marker=dict(size=8,color='#D1DCEB',line=dict(width=1,color='#607B96')),
            text=[{'Samsung Electronics':'삼성전자'}.get(anchor['company'],anchor['company'])],textposition='bottom center',
            textfont=dict(size=11,color='#DBE9F5',shadow='0 0 4px #061426'),
            hovertext=[tip],hovertemplate='%{hovertext}<extra></extra>',showlegend=False))
    lon,lat = center or (105,25)
    points=list(anchors.values())
    separation=1.0
    for a in points:
        for b in points:
            la,lb=math.radians(a['lat']),math.radians(b['lat'])
            angle=math.sin(la)*math.sin(lb)+math.cos(la)*math.cos(lb)*math.cos(math.radians(a['lon']-b['lon']))
            separation=max(separation,math.degrees(math.acos(max(-1,min(1,angle)))))
    scale=min(3.0,max(1.0,55/separation)) if mapped else 1.0
    fig.update_geos(projection_type='orthographic',projection_scale=scale,projection_rotation=dict(lon=lon,lat=max(-60,min(60,lat))),
        showland=True,landcolor='#102B47',showocean=True,oceancolor='#061426',
        showcountries=True,countrycolor='#29475E',countrywidth=.35,
        showcoastlines=True,coastlinecolor='#416985',coastlinewidth=.5,
        showlakes=True,lakecolor='#061426',showframe=False,bgcolor='rgba(0,0,0,0)',
        lonaxis_showgrid=False,lataxis_showgrid=False)
    fig.update_layout(height=340,margin=dict(l=0,r=0,t=12,b=0),paper_bgcolor='rgba(0,0,0,0)',
        dragmode='pan',clickmode='event+select',
        uirevision='article-'+payload['article_id']+'-'+str(selected),
        meta=dict(article_id=payload['article_id'], selected_route=selected,
                  displayed_route_ids=[r['id'] for r in mapped], simulation_used=False,
                  event_location_verified=False))
    return fig


def select_article_route(state, allowed):
    chosen=state.get('rr_article_route_click',{}).get('picked')
    if isinstance(chosen,str) and chosen in allowed:
        state['rr_article_route']=chosen
