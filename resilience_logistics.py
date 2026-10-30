"""Explicit, schematic maritime routing assumptions, independent of plant geography."""
CHOKEPOINTS = {
    'logistics:kaohsiung':dict(name='가오슝항',country='대만',lat=22+37/60+1/3600,lon=120+15/60+25/3600,
        aliases=['가오슝','가오슝항','가오슝 항구','kaohsiung'],
        source='https://kh.twport.com.tw/en/port/Articles?a=918',
        precision='공식 제1항 입구 좌표 · 가상 경유 노드'),
    'logistics:malacca':dict(name='말라카 해협',country='말레이시아',lat=2.5,lon=101.,
        aliases=['말라카','말라카 해협','말라카해협','malacca'],
        source='https://www.mpa.gov.sg/docs/mpalibraries/mpa-documents-files/hydrographic/spi-2024_1-oct-2024.pdf?sfvrsn=e9d7957e_1',
        precision='해협 내 시나리오 대표점 · 실제 항로 측위 아님'),
    'logistics:suez':dict(name='수에즈 운하',country='이집트',lat=29.931389,lon=32.562778,
        aliases=['수에즈','수에즈 운하','수에즈운하','suez'],
        source='https://www.suezcanal.gov.eg/English/Navigation/Pages/NavigationSystem.aspx',
        precision='남측 입구 부근 시나리오 대표점 · 실제 선박 항적 아님'),
}

# Candidate geography is sourced; suitability, transit time and capacity are not.
DETOUR_POINTS = {
    'logistics:keelung': dict(name='기룽항', country='대만', lat=25+9/60+26.5/3600,
        lon=121+44/60+22.5/3600, aliases=['기룽', '기룽항', '지룽항', 'keelung'],
        source='https://www.twport.com.tw/business/PortInfo?a=311',
        precision='공식 항만 대표 좌표 · 대체 출입항·내륙 운송은 가정'),
    'logistics:lombok': dict(name='롬복 해협', country='인도네시아', lat=-8.5, lon=115.75,
        aliases=['롬복', '롬복 해협', 'lombok'],
        source='https://www.eia.gov/international/content/analysis/special_topics/World_Oil_Transit_Chokepoints/',
        precision='해협 내 시나리오 대표점 · 화물별 운항 가능성 미확인'),
    'logistics:cape': dict(name='희망봉 우회', country='남아프리카공화국', lat=-35.5, lon=18.,
        aliases=['희망봉', 'cape of good hope'],
        source='https://www.eia.gov/international/content/analysis/special_topics/World_Oil_Transit_Chokepoints/wotc.pdf',
        precision='남아공 남쪽 해상 시나리오 대표점 · 실제 항적 아님'),
}
DETOUR_CANDIDATES = dict(zip(CHOKEPOINTS, DETOUR_POINTS))


def default_detours():
    return {key: dict(enabled=False, via=[alternate], max_fraction=.5,
                     capacity_units=1., extra_days=days, cost_rate=cost)
            for key, alternate, days, cost in (
                ('logistics:kaohsiung', 'logistics:keelung', 3, .2),
                ('logistics:malacca', 'logistics:lombok', 5, .3),
                ('logistics:suez', 'logistics:cape', 14, .5))}


def sea_route(a,b):
    """Corporate country is a scenario grouping, never inferred factory/export origin."""
    if not a or not b or a==b:return []
    europe={'독일','프랑스','네덜란드'};asia={'한국','일본','대만','싱가포르'}
    east={'한국','일본','대만'}
    route=[]
    if a=='대만':route.append('logistics:kaohsiung')
    if a in europe and b in asia:route+=['logistics:suez','logistics:malacca']
    elif a in asia and b in europe:route+=['logistics:malacca','logistics:suez']
    elif (a=='싱가포르' and b in east) or (b=='싱가포르' and a in east):route+=['logistics:malacca']
    if b=='대만':route.append('logistics:kaohsiung')
    return route


def add_logistics(network,add):
    nodes=network['nodes'];network['logistics']={**CHOKEPOINTS, **DETOUR_POINTS}
    network['port_detours'] = default_detours()
    for key,p in network['logistics'].items():
        add(key,p['name'],'logistics',p['country'],p['lat'],p['lon'],aliases=p['aliases'],
            source=p['source'],source_note=p['precision'],buffer_direct=False,
            assumption_note='가상 물류 경유점. 실제 운송 계약·해상 비중은 미확인.')
    routes={};bindings={}
    for edge in network['visual_edges']:
        if not edge.get('calculation_included', True):
            continue
        a,b=edge['from'],edge['to'];src,dst=edge['calc_source'],edge['calc_target']
        if src==dst or (src not in nodes[dst]['requires'] and (src,dst) not in bindings):continue
        via=sea_route(nodes[a]['country'],nodes[b]['country'])
        if not via:continue
        pair=(src,dst)
        if pair not in bindings:
            key='transport:'+str(len(routes))
            scope=edge['scope']
            add(key,'수입재 도착 재고 · '+nodes[src]['name'],'transport',nodes[b]['country'],None,None,
                requires=[src,*via],visible=False,scope=scope,inventory_days=7.,
                source_note='해상 경유·도착지 재고 7일 가정. 출발지 재고와 별도.',
                logistics_via=via,assumption_note='실제 선박 경로·운송 수단·현장 재고 미확인')
            nodes[key]['route_dependencies'] = [DETOUR_CANDIDATES[c] for c in via]
            # A delivery loss can trigger the same shared reserve pool even when
            # the original factory is healthy. Route that reserve from its own
            # provider, rather than through the blocked primary supplier's route.
            pool=nodes[src].get('alt_vendor')
            if pool:
                nodes[key].update(alt_vendor=pool,alt_capacity=nodes[src]['alt_capacity'],
                    alt_qualification_days=nodes[src].get('alt_qualification_days',0),
                    alt_ramp_days=nodes[src].get('alt_ramp_days',0),
                    alt_logistics_via=sea_route(nodes[pool]['country'],nodes[b]['country']))
            nodes[dst]['requires']=[key if k==src else k for k in nodes[dst]['requires']]
            # Preserve positional weights when replacing one mix input.
            bindings[pair]=key
            routes[key]=dict(via=via,scope=scope,source=src,target=dst,edges=[])
        key=bindings[pair]
        edge.update(logistics_via=routes[key]['via'],transport_node=key)
        routes[key]['edges'].append(edge['id'])
    network['logistics_routes']=routes
    network['route_settings'] = {key: dict(sea_fraction=1., inventory_days=7.) for key in routes}
    # apply_locations deliberately strips unverified geography. Only explicitly
    # schematic logistics markers recover their own scenario coordinates here.
    for key,p in network['logistics'].items():
        nodes[key].update(lat=p['lat'],lon=p['lon'],location_status='시나리오 경유점',
            location_scope=p['precision'])
    return network


def logistics_rows(network):
    return [dict(경로=key,출발=network['nodes'][r['source']]['name'],
        도착=network['nodes'][r['target']]['name'],
        경유=' → '.join(CHOKEPOINTS[c]['name'] for c in r['via']),
        적용범위=r['scope'],해상비중=network['route_settings'][key]['sea_fraction'],
        도착지재고일=network['nodes'][key]['inventory_days'],
        근거상태='실제 운송 경로·비중 미확인') for key,r in network['logistics_routes'].items()]
