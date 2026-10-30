"""Plotly orthographic geography with preserved backbone and dynamic bypasses."""
from collections import defaultdict
import html
import math
from flow_selection import related_paths
from flow_data import build_flow
import plotly.graph_objects as go
from resilience_locations import LOCATION_TYPES
from resilience_logistics import sea_route, CHOKEPOINTS

COLORS = dict(normal='#4FE4DB', buffer='#71F5B2', reduced='#FFBE60',
              stopped='#FF587B', bypass='#409CFF', muted='#28536B', reference='#839EB5')

LABEL_COLOR = '#E6F4FF'
LABEL_SHADOW = '0 0 3px #04101E, 0 0 5px #04101E, 1px 1px 2px #04101E'
SHORT_LABELS = {
    'seh-shirakawa': '신에츠 시라카와', 'sumco-imari': 'SUMCO 이마리',
    'samsung-giheung': '삼성 기흥', 'samsung-pyeongtaek': '삼성 평택',
    'tsmc-fab12a': 'TSMC Fab12A', 'tsmc-fab18': 'TSMC Fab18',
    'ase-k7': 'ASE 가오슝', 'sibelco-quartz': 'Sibelco 석영',
    'airliquide-hq': 'Air Liquide', 'airproducts-hq': 'Air Products',
    'applied-hq': 'Applied Materials', 'heraeus-hanau': 'Heraeus 하나우',
}


def great_circle(a, b, count=35):
    def vector(n):
        lat, lon = math.radians(n['lat']), math.radians(n['lon'])
        return (math.cos(lat)*math.cos(lon), math.cos(lat)*math.sin(lon), math.sin(lat))
    u, v = vector(a), vector(b)
    omega = math.acos(max(-1., min(1., sum(x*y for x,y in zip(u,v)))))
    lats, lons = [], []
    for i in range(count):
        t = i/(count-1)
        if abs(math.sin(omega)) < 1e-8:
            xyz = [(1-t)*x+t*y for x,y in zip(u,v)]
        else:
            xyz = [(math.sin((1-t)*omega)*x+math.sin(t*omega)*y)/math.sin(omega) for x,y in zip(u,v)]
        lats.append(math.degrees(math.atan2(xyz[2], math.hypot(xyz[0],xyz[1]))))
        lons.append(math.degrees(math.atan2(xyz[1],xyz[0])))
    return lats, lons


def entity_rate(key, network, result, process='전체'):
    if not network['nodes'][key].get('calculation_included', True):
        return 1.0
    value = result['nodes'][key]['effective']
    operations = [op for (company, name), op in network['operations'].items()
                  if company == key and (process == '전체' or name == process)]
    return min([value]+[result['nodes'][op]['effective'] for op in operations])


def process_edges(network, result, process):
    """Use the same local process inputs as the flow; omit prior operations.

    Retain excluded relationships as references. Active transport and reserve
    IDs are included for existing detour rendering, never to change calculations.
    """
    flow = build_flow(network, result, process)
    needed = {card['node_id'] for column in flow['columns'] for card in column['cards']}
    needed.update(edge['result_node_id'] for edge in flow['connections'])
    for key in tuple(needed):
        alternate = network['nodes'].get(key, {}).get('alt_vendor')
        if alternate:
            needed.add(alternate)
            needed.update(network['nodes'][alternate].get('requires', []))
    active = set(result['scopes'])
    edges = [edge for edge in network['visual_edges']
             if edge.get('scope', 'core') in active
             and (process in edge.get('processes', [])
                  or not edge.get('processes') and edge['calc_target'] in needed)]
    needed.update(key for edge in edges for key in edge.get('logistics_via', []))
    for edge in edges:
        route = result.get('logistics', {}).get('routes', {}).get(edge.get('transport_node'))
        if not route:
            continue
        if route['dispatched'] > 1e-10:
            needed.update(route['via'])
        if route['delivered'] > 1e-10:
            needed.update(key for via in route['arrival_vias'] for key in via)
    return needed, edges


def build_globe(network, result, process='전체', level='소재 연쇄', view='아시아', focus=None, label_limit=None):
    nodes, entities = network['nodes'], network['entities']
    active = set(result['scopes'])
    edges = list(network['visual_edges'])
    needed = set()
    if process != '전체':
        needed, edges = process_edges(network, result, process)
    visible = set()
    # All 44 are retained; filtering only changes display, never simulation.
    selected_edges=[]
    for e in edges:
        if e['scope'] not in active: continue
        if level == '기업' and process == '전체' and e['kind'] == 'upstream':
            continue
        if not all(entities[k].get('map_location_id') for k in (e['from'],e['to'])):continue
        selected_edges.append(e)
        visible.update((e['from'],e['to']))
    bypasses=[]
    seen_detours = set()
    for edge in selected_edges:
        key = edge.get('transport_node')
        route = result.get('logistics', {}).get('routes', {}).get(key)
        if not route:
            continue
        paths = []
        if route['dispatched'] > 1e-10:
            paths.append((route['via'], route['dispatched'], '우회 발송 · 추가 운송 ' + str(route['extra_days']) + '일'))
        if route['delivered'] > 1e-10:
            for via in {tuple(v) for v in route['arrival_vias']}:
                paths.append((list(via), route['delivered'], '우회 도착 · 오늘 공급 반영(해당 운송 경로 합계)'))
        for via, rate, phase in paths:
            identity = (key, edge['from'], edge['to'], tuple(via), phase)
            if identity in seen_detours:
                continue
            seen_detours.add(identity)
            bypasses.append(dict(edge, id='port:' + str(len(seen_detours)), kind='port_detour',
                                 key=key, logistics_via=via, detour_rate=rate, phase=phase))
    for key in result['bypass']:
        if process!='전체' and key not in needed: continue
        alt=nodes[key]['alt_vendor']
        destinations=[e['to'] for e in edges if (e['from']==key or e.get('transport_node')==key) and e['scope'] in active and e.get('calculation_included', True)]
        if not destinations and key in entities: destinations=[key]
        for dest in set(destinations):
            if alt!=dest and entities[alt].get('map_location_id') and entities[dest].get('map_location_id'):
                bypasses.append(dict(id=f'bypass:{alt}:{dest}:{key}', **{'from':alt,'to':dest},
                    key=key, kind='bypass', scope=nodes[key]['scope'],
                    logistics_via=sea_route(entities[alt]['country'],entities[dest]['country'])))
                visible.update((alt,dest))
    neighbors=set()
    if focus and focus in entities:
        neighbors={focus}
        if entities[focus]['kind']=='logistics':
            neighbors.update(k for e in selected_edges if focus in e.get('logistics_via',[]) for k in (e['from'],e['to']))
        seeds = {focus}
        if entities[focus]['kind'] == 'company':
            seeds.update(key for key, entity in entities.items() if entity.get('company_id') == focus)
        # Unlocated intermediate nodes can still connect a selected material to
        # existing mapped routes. Trace them without inventing map coordinates.
        selection_edges = [edge for edge in edges if edge['scope'] in active]
        reached, _ = related_paths(selection_edges, seeds)
        neighbors.update(reached)
    fig=go.Figure()
    groups=defaultdict(lambda:dict(lat=[],lon=[],text=[]))
    country_names={}
    if level=='국가':
        countries=defaultdict(list)
        for key in visible:
            n=entities[key]
            if n['kind']!='process':countries[n['country']].append(n)
        for country,ns in countries.items():
            anchor=min(ns,key=lambda n:(n['kind']!='company',n['map_location_id']))
            country_names[country]=dict(anchor,id='country:'+country,name=country,kind='country',
                country=country,location_scope='국가 집계 · 실제 대표 사업장: '+anchor['map_location']['name'])
    grouped_country={}
    all_edges=selected_edges+bypasses
    for e in all_edges:
        a,b=entities[e['from']],entities[e['to']]
        if level=='기업':
            a=entities.get(a.get('company_id'),a);b=entities.get(b.get('company_id'),b)
        if (a['lat'],a['lon'])==(b['lat'],b['lon']):continue
        is_bypass=e['kind'] in ('bypass', 'port_detour')
        is_port=e['kind']=='port_detour'
        reference_only = not e.get('calculation_included', True)
        if reference_only:
            rate = None
            state = 'reference'
        elif is_port:
            rate=e['detour_rate'];state='bypass'
        elif is_bypass:
            rate=result['nodes'][e['key']]['backup'];state='bypass'
        else:
            source=result['nodes'][e['calc_source']]
            target=result['nodes'][e['calc_target']]
            rate=min(source['primary'],target['primary'])
            state='stopped' if rate<1e-7 else 'reduced' if rate<1-1e-7 else 'normal'
        via = [] if reference_only else e.get('logistics_via', [])
        if via and not is_port:
            route_availability = min(result['nodes'][k]['effective'] for k in via)
            rate = min(rate, route_availability)
            if route_availability < 1e-7:
                state = 'stopped'
            elif route_availability < 1 - 1e-7:
                state = 'reduced'
        dim=bool(neighbors) and not (e['from'] in neighbors and e['to'] in neighbors)
        if level=='국가' and a['kind']!='process' and b['kind']!='process':
            ca,cb=a['country'],b['country']
            if ca==cb:continue
            a,b=country_names[ca],country_names[cb]
            gkey=(ca,cb,state,dim,tuple(via))
            if gkey in grouped_country:
                grouped_country[gkey][1]+=1
                continue
            grouped_country[gkey]=[e,1]
        lat,lon=[],[]
        waypoints=[a]+[nodes[k] for k in via]+[b]
        for start,end in zip(waypoints,waypoints[1:]):
            segment_lat,segment_lon=great_circle(start,end)
            lat+=segment_lat;lon+=segment_lon
        g=groups[(state,dim)]
        evidence=e.get('evidence',{})
        info=e['phase'] + ' · 운송 전환·처리량·운임 가정' if is_port else '우회 계약·등급 인증·예약량 가정' if is_bypass else (
            f"원본 44개 · {evidence.get('relationship_kind','')} · 품목 {evidence.get('item_status','확인 필요')}" if e['kind']=='backbone' else '추가 공정 의존성·납품 경로 가정')
        label=e.get('label',nodes[e['key']]['name'] if is_bypass else '')
        flow_label = '공급 계산 제외 · 참고 관계' if reference_only else f"{'명목 경로 수요 대비 우회 운송' if is_port else '우회 배분' if is_bypass else '기존 경로'} {rate * 100:.1f}%"
        if reference_only:
            info += ' · ' + e['exclusion_reason']
        tip=f"{html.escape(a['name'])} → {html.escape(b['name'])}<br>{html.escape(label)}<br>{html.escape(flow_label)}<br>{html.escape(info)}<br>기업 관계 표시 · 시설 간 실제 운송·납품 경로 미확인"
        if via:tip+='<br>해상 경유 가정: '+' → '.join(nodes[k]['name'] for k in via)+'<br>선은 개략 연결이며 실제 선박 항적·육지 회피 항로가 아님'
        g['lat']+=lat+[None];g['lon']+=lon+[None];g['text'] += [tip]*len(lat)+['']
    for (state,dim),g in groups.items():
        fig.add_trace(go.Scattergeo(**g,mode='lines',opacity=.3 if dim else .6 if state=='reference' else .95 if state!='normal' else .78,
            line=dict(color=COLORS[state] if state!='normal' else '#5793AC',
                      width=3.5 if state=='bypass' else 2.5 if state in ('stopped','reduced') else 1.5,
                      dash='dot' if state == 'reference' else 'dash' if state in ('stopped','reduced') else 'solid'),
            hovertemplate='%{text}<extra></extra>',showlegend=False))
    if level=='기업':
        visible={entities[k].get('company_id',k) for k in visible}
    records=[]
    if level=='국가':
        for country,n in country_names.items():
            keys=[k for k in visible if entities[k]['country']==country]
            r=min(entity_rate(k,network,result,process) for k in keys)
            records.append((n,r,6+min(10,math.sqrt(len(keys))*1.6),n['name'],keys[0]))
        records += [(entities[k],entity_rate(k,network,result,process),6,entities[k]['name'],k)
                    for k in visible if entities[k]['kind']=='process']
    else:
        colocated=defaultdict(list)
        for k in visible:colocated[entities[k]['map_location_id']].append(k)
        for location_id,keys in colocated.items():
            location=network['locations'][location_id]
            lead=min(keys,key=lambda k:(entities[k]['kind']!='company',entity_rate(k,network,result,process),k))
            n=dict(entities[lead],name=location['name'],model_keys=keys,map_location=location)
            r=min(entity_rate(k,network,result,process) for k in keys)
            records.append((n,r,7+min(4,math.sqrt(len(keys))),n['name'],lead))
        # Other sourced fabs are location references, not inferred delivery destinations.
        present=set(colocated)
        companies={entities[k].get('company_id',k) for k in visible}
        for location_id,location in network['locations'].items():
            if location_id in present or location['company_id'] not in companies:continue
            if location['location_type']!='chip_fab':continue
            if process!='전체' and process not in location['process_roles']:continue
            key=location['company_id']
            n=dict(entities[key],name=location['name'],lat=location['lat'],lon=location['lon'],
                map_location=location,map_location_id=location_id,reference_only=True,
                location_scope='공식 팹 위치 참고 · 공급 물량의 시설별 배분은 미확인')
            records.append((n,entity_rate(key,network,result,process),7,n['name'],key))
    states=defaultdict(list)
    for record in records:
        n,r,_,_,key=record
        buffered=(key in result['nodes'] and result['nodes'][key]['inventory']>0 and r>=1-1e-7)
        state='stopped' if r<1e-7 else 'reduced' if r<1-1e-7 else 'buffer' if buffered else 'normal'
        states[state].append(record)
    for state,rs in states.items():
        texts=[]
        for n,r,_,_,key in rs:
            place=n['map_location']
            kind=LOCATION_TYPES[place['location_type']]
            reference='위치 참고 · 시설별 공급량 미확인' if n.get('reference_only') else '선은 기업 관계·납품 후보 모델'
            role='본사 대표 위치 · 생산·출하 공장 미확인' if place['location_type'] in ('hq','hq_campus') else '시설 위치 확인 · 시설별 납품 비중 미확인'
            score='시설 가동률 미확인 · 기업 모델 참고' if n.get('reference_only') else f'기업·소재 모델 공급 충족 {r*100:.1f}% · 시설 가동률 아님'
            texts.append(f"{html.escape(n['name'])}<br>{html.escape(kind)} · {html.escape(place['country'])}<br>{score}<br>{html.escape(place['address'])}<br>{html.escape(place['coordinate_precision'])}<br>{role}<br>{reference}")
        fig.add_trace(go.Scattergeo(lat=[n['lat'] for n,*_ in rs],lon=[n['lon'] for n,*_ in rs],
            mode='markers',marker=dict(size=[s for _,_,s,_,_ in rs],color=COLORS[state],
                symbol=['circle-open' if n.get('reference_only') else 'square-open' if n['map_location']['location_type'] in ('hq','hq_campus') else 'circle' for n,*_ in rs],
                opacity=[.65 if n.get('reference_only') else 1 for n,*_ in rs],
                line=dict(width=.7,color='#C6F3FF')),
            selected=dict(marker=dict(opacity=1)),
            unselected=dict(marker=dict(opacity=1)),
            customdata=[n['id'] for n,*_ in rs],text=texts,
            hovertemplate='%{text}<extra></extra>',showlegend=False))
    # Chokepoints are scenario markers, never factories or production coordinates.
    enabled_stops = {point for config in network.get('port_detours', {}).values()
                     if config.get('enabled') for point in config['via']}
    port_label_positions = {'logistics:kaohsiung':'bottom left',
                            'logistics:keelung':'top right'}
    route_ids = {edge.get('transport_node') for edge in selected_edges}
    process_stops = {key for edge in all_edges for key in edge.get('logistics_via', [])}
    for key,place in network.get('logistics',{}).items():
        if process != '전체' and key not in process_stops:
            continue
        rate=result['nodes'][key]['effective']
        if key not in CHOKEPOINTS and key not in enabled_stops and rate >= 1-1e-7 and key != focus:
            continue
        color=COLORS['stopped'] if rate<1e-7 else COLORS['reduced'] if rate<1-1e-7 else '#B993FF'
        relevant = [route for route_id, route in network['logistics_routes'].items()
                    if key in route['via'] and route['scope'] in active
                    and (process == '전체' or route_id in route_ids)]
        fig.add_trace(go.Scattergeo(name='물류 병목(시나리오)',lat=[place['lat']],lon=[place['lon']],
            mode='markers+text',text=[place['name']],textposition=port_label_positions.get(key,'bottom center'),
            textfont=dict(color=color,size=11,weight=600,shadow=LABEL_SHADOW),
            selected=dict(marker=dict(opacity=1),textfont=dict(color=color)),
            unselected=dict(marker=dict(opacity=1),textfont=dict(color=color)),
            marker=dict(size=12 if rate<1-1e-7 else 9,color=color,symbol=['triangle-up'],line=dict(width=1,color='#E2DCFF')),
            customdata=[key],hovertext=[place['name']+f'<br>통항 가용률 {rate*100:.0f}% · 활성 경유 {len(relevant)}개<br>'+place['precision']+'<br>해상 경유·도착지 재고 7일은 가정'],
            hovertemplate='%{hovertext}<extra></extra>',showlegend=False))
    longitude,latitude={'아시아':(115,20),'유럽':(25,25),'미주':(-80,20),'이슈':(115,20)}[view]
    if view=='이슈':
        damaged=[entities[k] for k,r in result['nodes'].items() if r['direct']<1-1e-7
                 and k in entities and (entities[k].get('map_location_id') or entities[k]['kind']=='logistics')
                 and (process == '전체' or k in needed or k in process_stops)]
        if not damaged:damaged=[n for n,r,*_ in records if r<1-1e-7]
        if damaged:longitude,latitude=damaged[0]['lon'],damaged[0]['lat']
    # Pick geographically spaced labels worldwide, rather than only around the
    # initial camera. Plotly clips the back hemisphere as the user rotates, so
    # labels belonging to the newly visible region appear without a server rerun.
    # This spacing reduces clutter; it is not a screen-space collision solver.
    chosen=[]
    label_neighbors = {entities[key].get('company_id', key) for key in neighbors if key in entities}
    label_positions={'seh-shirakawa':'top right','sumco-imari':'bottom right',
        'samsung-giheung':'top left','tsmc-fab12a':'bottom left','ase-k7':'bottom right'}
    for record in sorted(records,key=lambda x:(x[0]['id']!=focus,x[1]>1e-7,x[1]>=1-1e-7,
            process not in x[0]['map_location']['process_roles'],
            x[0]['map_location']['location_type'] not in ('wafer_plant','chip_fab','chip_fab_hq'),
            x[0].get('reference_only',False),x[0]['name'])):
        n,r,_,label,key=record
        if label_limit is not None:
            if len(chosen) >= label_limit:
                break
            if focus and key not in label_neighbors and n['id'] != focus and r >= 1 - 1e-7:
                continue
        gap=12 if n.get('map_location_id') in label_positions else 150
        if all((n['lat']-m['lat'])**2+((((n['lon']-m['lon']+180)%360)-180)*.65)**2>gap for m in chosen):
            short = SHORT_LABELS.get(n.get('map_location_id'), label.replace(' 본사 캠퍼스','').replace(' 본사','').replace(' 사업장','').replace(' 공장',''))
            chosen.append(dict(n,label=('× ' if r<1e-7 else '△ ' if r<1-1e-7 else '')+short[:24],
                label_position=label_positions.get(n.get('map_location_id'),'top center')))
    fig.add_trace(go.Scattergeo(lat=[n['lat'] for n in chosen],lon=[n['lon'] for n in chosen],
        mode='text',text=[n['label'] for n in chosen],textposition=[n['label_position'] for n in chosen],
        textfont=dict(color=LABEL_COLOR,size=11,weight=500,shadow=LABEL_SHADOW),
        selected=dict(textfont=dict(color=LABEL_COLOR)),
        unselected=dict(textfont=dict(color=LABEL_COLOR)),
        hoverinfo='skip',showlegend=False))
    fig.update_geos(projection_type='orthographic',projection_rotation=dict(lon=longitude,lat=latitude),
        showland=True,landcolor='#12364D',showocean=True,oceancolor='#07182B',
        showlakes=True,lakecolor='#07182B',showcountries=True,countrycolor='#287F92',countrywidth=.5,
        showcoastlines=True,coastlinecolor='#31879B',coastlinewidth=.6,showframe=False,
        bgcolor='rgba(0,0,0,0)',resolution=110,
        lonaxis=dict(showgrid=True,gridcolor='#153A50',gridwidth=.45),
        lataxis=dict(showgrid=True,gridcolor='#153A50',gridwidth=.45))
    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',font=dict(color='#C7E9FA'),
        geo=dict(domain=dict(x=[0,1],y=[0,1])),height=None,dragmode='pan',
        uirevision=f'resilience-{view}-{longitude if view=="이슈" else "fixed"}',
        hoverlabel=dict(bgcolor='#0B1B2B',font_size=11),clickmode='event+select',
        meta={'process': process, 'display_edge_ids': [edge['id'] for edge in selected_edges]})
    return fig


def location_numbers(network):
    """Stable site numbers shared by the location globe and company cards."""
    return {key: str(index + 1) for index, key in enumerate(sorted(network['locations']))}


def build_location_globe(network, result, process='포토', view='아시아', focus=None):
    """A location-only projection; relationship math and the old builder stay intact."""
    figure = build_globe(network, result, process, '기업', view, focus)
    figure.data = tuple(trace for trace in figure.data if trace.mode in ('markers', 'markers+text'))
    numbers = location_numbers(network)
    coordinate_numbers = {
        (place['lat'], place['lon']): numbers[key]
        for key, place in network['locations'].items()
    }
    for index, key in enumerate(sorted(network.get('logistics', {})), len(numbers) + 1):
        place = network['logistics'][key]
        coordinate_numbers[(place['lat'], place['lon'])] = str(index)
    for trace in figure.data:
        if trace.mode == 'markers':
            trace.hovertext = trace.text
        trace.text = [coordinate_numbers.get((lat, lon), '') for lat, lon in zip(trace.lat, trace.lon)]
        trace.mode = 'markers+text'
        trace.textposition = 'top center'
        trace.textfont = dict(color=LABEL_COLOR, size=10, shadow=LABEL_SHADOW)
        trace.selected = dict(marker=dict(opacity=1), textfont=dict(color=LABEL_COLOR))
        trace.unselected = dict(marker=dict(opacity=1), textfont=dict(color=LABEL_COLOR))
        trace.hovertemplate = '%{hovertext}<extra></extra>'
    selected = network['entities'].get(focus)
    if selected and selected['kind'] == 'company' and selected.get('map_location'):
        place = selected['map_location']
        label = html.escape(selected['name']) + '<br>' + html.escape(place['name'])
        figure.add_trace(go.Scattergeo(
            lat=[place['lat']], lon=[place['lon']], mode='text', text=[label],
            textposition='bottom center', hoverinfo='skip', showlegend=False,
            textfont=dict(color=LABEL_COLOR, size=11, shadow=LABEL_SHADOW),
        ))
    return figure


def build_network_globe(network, result, view='아시아', focus=None, process='전체'):
    """Restore the network overview with names and visual emphasis, read-only."""
    base = build_globe(network, result, process=process, level='기업', view=view, focus=focus,
                       label_limit=8 if focus else 10)
    base.update_geos(landcolor='#102B47', oceancolor='#061426', lakecolor='#061426',
                     countrycolor='#29475E', countrywidth=.35,
                     coastlinecolor='#416985', coastlinewidth=.5,
                     lonaxis_showgrid=False, lataxis_showgrid=False)
    glows = []
    rings = []
    for index, trace in enumerate(base.data):
        if trace.mode == 'lines':
            color = trace.line.color
            state = next((key for key in ('bypass', 'stopped', 'reduced', 'reference')
                          if color == COLORS[key]), 'normal')
            trace.uid = f'network-route-{state}-{index}'
            dimmed = bool(focus) and trace.opacity == .3
            trace.meta = {'network_state': state, 'dimmed': dimmed}
            if state == 'normal':
                trace.line.color = '#78ADC8'
                trace.line.width = 1.5
                trace.opacity = .76
            elif state == 'bypass':
                trace.line.width = 4
                trace.opacity = .12 if dimmed else 1
                trace.line.dash = 'dash'
            elif state == 'reference':
                trace.line.width = 1
                trace.opacity = .32
            elif state in ('stopped', 'reduced'):
                trace.line.width = 2.6
            if focus:
                trace.opacity = .12 if dimmed else .98
                if not dimmed and state == 'normal':
                    trace.line.color = '#67E3F0'
                if not dimmed and state == 'reference':
                    trace.opacity = .45
                if not dimmed and state not in ('bypass', 'reference'):
                    trace.line.width += 1.2
            glows.append(go.Scattergeo(
                lat=trace.lat, lon=trace.lon, mode='lines',
                uid=f'network-glow-{state}-{index}',
                line=dict(color=trace.line.color, width=trace.line.width + 3),
                opacity=.008 if dimmed else .025 if state in ('normal', 'reference') and not focus else .10,
                hoverinfo='skip', showlegend=False,
            ))
        elif trace.mode in ('markers', 'markers+text'):
            color = trace.marker.color
            if color in (COLORS['stopped'], COLORS['reduced']):
                sizes = trace.marker.size
                if isinstance(sizes, (int, float)):
                    sizes = [sizes] * len(trace.lat)
                rings.append(go.Scattergeo(
                    lat=trace.lat, lon=trace.lon, mode='markers',
                    uid=f'network-ring-{index}',
                    marker=dict(size=[size + 8 for size in sizes], color=color,
                                symbol='circle-open', line=dict(width=1.5), opacity=.5),
                    hoverinfo='skip', showlegend=False,
                ))
        elif trace.mode == 'text':
            trace.textfont.size = 12
            trace.textfont.weight = 600
    figure = go.Figure(data=[*glows, *rings, *base.data], layout=base.layout)
    return figure
