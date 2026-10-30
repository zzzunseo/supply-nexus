"""One bounded port-blockade presentation, backed by the existing transit engine."""
from core_cases import core_cases


def port_scope(network,port):
    from .demo_scenarios import connections
    registered={(e['from'],e['to']) for e in network['visual_edges'] if port in e.get('logistics_via',[])}
    rows=[r for r in connections(network) if (r['target'],r['recipient']) in registered]
    return dict(rows=rows,suppliers=len({r['supplier'] for r in rows}),
                customers=len({r['recipient'] for r in rows}),materials=len({r['item'] for r in rows}))


def port_overview(network,case):
    scope=port_scope(network,case['target']);markers={};routes={}
    for row in scope['rows']:
        for key,role in ((row['supplier'],'supplier'),(row['recipient'],'recipient'),(case['target'],'blocked_port')):
            entity=network['entities'][key]
            place=network['logistics'].get(key) if role=='blocked_port' else entity.get('map_location')
            if place:markers[key]=dict(id=key,name=entity['name'],site=place['name'],lat=place['lat'],lon=place['lon'],role=role,score=None)
        for start,end in ((row['supplier'],case['target']),(case['target'],row['recipient'])):
            if start not in markers or end not in markers:continue
            edge=routes.setdefault((start,end),dict(start=start,end=end,kind='primary',materials=[],assumed=True))
            if row['material'] not in edge['materials']:edge['materials'].append(row['material'])
    for edge in routes.values():edge['material']=' · '.join(edge.pop('materials'))
    return list(markers.values()),list(routes.values()),scope


def demo_cases():
    cases=[*core_cases(),dict(id='kaohsiung',kind='logistics',
        name='가오슝항 → 기룽항 · 경로 검토',target='logistics:kaohsiung',
        material_target='supply:jsr:photoresist',material_label='포토레지스트',
        process='포토',recipients=['tsmc'],days=30,
        evidence='항만 위치는 공식 자료의 대표 좌표입니다. 지도는 공급 관계 근거가 있고 가오슝을 경유하도록 설정된 복수 품목 경로를 보여줍니다. 공정 상세 해석은 JSR → TSMC 포토레지스트 대표 사례입니다.',
        limits='가오슝 경유·기룽 우회 적합성·해상 비중·용량·추가 운송일은 시뮬레이션 가정입니다. 봉쇄는 같은 항만을 경유하도록 등록된 다른 소재에도 적용됩니다.',
        relationship_source='https://www.twport.com.tw/zh-tw/business/PortInfo?a=512',
        product_source='https://www.twport.com.tw/business/PortInfo?a=311')]

    from resilience_logistics import CHOKEPOINTS,DETOUR_POINTS,DETOUR_CANDIDATES
    for name in ('malacca','suez'):
        target='logistics:'+name;alternate=DETOUR_CANDIDATES[target]
        origin=CHOKEPOINTS[target];candidate=DETOUR_POINTS[alternate]
        cases.append(dict(id=name,kind='logistics',name=origin['name']+' → '+candidate['name'].removesuffix(' 우회')+' · 경로 검토',
            target=target,material_target='supply:airliquide:oxygen',material_label='고순도 산소',
            process='산소 사용 등록 공정',recipients=['samsung'],days=30,
            evidence='항만·해협 위치 자료와 기업 관계 근거를 연결한 시연입니다. 상세는 Air Liquide → Samsung 산소 대표 연결입니다.',
            limits='해당 화물의 실제 경유·선사 운항·우회 적합성·용량·일수·비용은 미확인 또는 모델 가정입니다.',
            relationship_source=origin['source'],product_source=candidate['source']))
    from resilience_data import build_network
    from .demo_scenarios import connections
    network=build_network()
    rows=[r for r in connections(network) if r['target']=='supply:shinetsu:polished-wafer']
    cases.append(dict(id='shirakawa',name='신에츠 시라카와 공장 지진 피해 · 역사 사례 재현',
        target='supply:shinetsu:polished-wafer',material_label='실리콘 웨이퍼',process='웨이퍼 제조',
        recipients=list(dict.fromkeys(r['recipient'] for r in rows)),days=30,connections=rows,
        historical=True,event='공급 감소',default_percent=50,
        history='2011.03.11 동일본대지진 이후 시라카와 공장 복구 작업. 2011.04.11 재고 출하·타 생산거점 활용 발표. 2011.07.01 생산능력 복구 발표.',
        evidence='공식 발표에 시라카와 공장 피해·복구와 재고 출하·타 거점 활용이 기록되어 있습니다. 지도 고객 연결은 별도 시점의 저장된 관계 근거를 활용한 재현 가정입니다.',
        limits='입력 30일·감소율은 실제 사건의 공급 감소율이나 공장 가동중단 기간이 아닙니다. 현재 기업 관계를 2011년 계약으로 소급하지 않으며 Samsung·TSMC의 당시 생산 피해를 확정하지 않습니다.',
        incident_source='https://www.shinetsu.co.jp/en/news/others/shin-etsu-group-current-situation-impacted-by-the-2011-off-the-pacific-coast-of-tohoku-earthquake-8th-report/',
        recovery_source='https://www.shinetsu.co.jp/en/news/others/updated-current-situations-at-the-shin-etsu-groups-plants-impacted-by-the-great-east-japan-earthquake-11th-report/',
        relationship_source=rows[0]['evidence']['relationship_source'],product_source=network['nodes'][rows[0]['target']]['source']))
    return cases



def representative_route(network,case):
    for key,route in network['logistics_routes'].items():
        if route['source']!=case['material_target']:continue
        for edge in network['visual_edges']:
            if edge.get('transport_node')==key and edge['to'] in case['recipients']:
                return key,route
    raise ValueError('대표 물류 경로가 현재 공급망에 등록되어 있지 않습니다.')


def detour_summary(network,result,case):
    key,_=representative_route(network,case)
    route=result['logistics']['routes'][key]
    setting=result['logistics']['settings'][case['target']]
    return dict(key=key,via=route['via'],dispatched=route['dispatched'],delivered=route['delivered'],
                pending=route['pending'],extra_days=route['extra_days'],enabled=setting['enabled'],
                limit=setting['max_fraction']*100,
                arrival_vias=route['arrival_vias'])


def logistics_payload(network,result,case,applied,response):
    _,route=representative_route(network,case)
    product=network['nodes'][route['source']]
    supplier=product['company_id']; customer=case['recipients'][0]
    points=[]
    for key,role in ((supplier,'supplier'),(customer,'recipient'),(case['target'],'blocked_port')):
        entity=network['entities'][key]
        place=network['logistics'].get(key) if role=='blocked_port' else entity.get('map_location')
        if place:
            points.append(dict(id=key,name=entity['name'],site=place.get('name',entity['name']),
                               lat=place['lat'],lon=place['lon'],role=role,score=None))
    routes=[]
    ids={p['id'] for p in points}
    if {supplier,customer,case['target']}<=ids:
        routes=[dict(start=supplier,end=case['target'],kind='primary'),dict(start=case['target'],end=customer,kind='primary')]
    summary=detour_summary(network,result,case)
    # Display dispatched detour as in-transit, or actually arriving detour as delivered.
    vias=[]
    if response and summary['dispatched']>1e-7:vias.append(summary['via'])
    if response and summary['delivered']>1e-7:vias.extend(summary['arrival_vias'])
    for via in vias:
        path=[]
        for key in via:
            if key==case['target']:continue
            place=network['logistics'].get(key)
            if not place:continue
            if key not in ids:
                points.append(dict(id=key,name=place['name'],site=place['precision'],lat=place['lat'],lon=place['lon'],role='detour_port',score=None));ids.add(key)
            path.append(key)
        full=[supplier,*path,customer]
        if path and all(key in ids for key in full):
            for start,end in zip(full,full[1:]):
                edge=dict(start=start,end=end,kind='detour')
                if edge not in routes:routes.append(edge)
    scope=port_scope(network,case['target'])
    if not response:points,routes,scope=port_overview(network,case)
    return dict(markers=points,routes=routes,exposure=scope,applied=applied,response=response,alternative=None,
                title=case['name'],process=case['process'],loss=case.get('percent',0) if applied else 0,
                logistics=True,detour=summary)
