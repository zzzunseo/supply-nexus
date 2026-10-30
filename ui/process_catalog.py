"""Evidence-scoped process/vendor exploration, isolated from capacity simulation."""
import json
from pathlib import Path
from hashlib import sha256
from .research_map import map_matches
from .simulation_candidates import catalog_candidates

PATH=Path(__file__).resolve().parents[1]/'data/process_vendor_catalog.json'


def load_process_catalog():
    data=json.loads(PATH.read_text(encoding='utf-8'))
    seen=set()
    for row in data['offerings']:
        if row['id'] in seen or row['group'] not in data['groups']:
            raise ValueError('공정 후보 ID·품목 분류를 확인하세요.')
        seen.add(row['id'])
        if not row['source'].startswith('https://') or not row['checked_at']:
            raise ValueError('제품 출처·확인일이 필요합니다.')
        if row['customer_edges'] or row['customer_qualification']!='unverified' or row['additional_capacity']!='unverified':
            raise ValueError('제품 자료를 고객 계약·공급 여력으로 해석할 수 없습니다.')
    return data


def group_offerings(network,group_id,product_class=None,catalog=None):
    catalog=catalog or load_process_catalog()
    group=catalog['groups'][group_id]
    found={}
    if group['catalog_item']:
        case=dict(target='',connections=[dict(item=group['catalog_item'],material=group['name'],supplier=None)])
        rows=[dict(company_id=e['record']['supplier_network_id'],name=e['record']['supplier'],product=e['record']['name'],
                   source=e['sources'][0]['url'],sources=[s['url'] for s in e['sources']])
              for e in catalog_candidates(network,case,product_class)]
    else:rows=[r for r in catalog['offerings'] if r['group']==group_id]
    for row in rows:
        entry=found.setdefault(row['name'],dict(company_id=row['company_id'],name=row['name'],products=[],sources=[]))
        if row['product'] not in entry['products']:entry['products'].append(row['product'])
        for source in row.get('sources',[row['source']]):
            if source not in entry['sources']:entry['sources'].append(source)
    for entry in found.values():
        mapped=map_matches(network,'',candidates=[dict(name=entry['name'],products=entry['products'])])
        entry['location']=next((m for m in mapped['markers'] if m.get('candidate_name')==entry['name']),None)
        entry['map_id']=entry['location']['id'] if entry['location'] else 'unlocated:'+entry['name']
    return sorted(found.values(),key=lambda e:e['name'].casefold())


def company_groups(network):
    """Mapped companies available directly from the main simulation."""
    catalog=load_process_catalog();found={}
    for gid in catalog['groups']:
        for entry in group_offerings(network,gid,catalog=catalog):
            if entry['location']:
                found.setdefault(entry['name'],[]).append(gid)
    return dict(sorted(found.items(),key=lambda pair:pair[0].casefold()))


def process_map_payload(network,group_id,origin,recipient='tsmc',disrupted=True,product_class=None):
    catalog=load_process_catalog();group=catalog['groups'][group_id]
    entries=group_offerings(network,group_id,product_class,catalog)
    chosen=next(e for e in entries if e['name']==origin)
    identity=json.dumps([group_id,origin,recipient,product_class],ensure_ascii=False)
    camera=sha256(identity.encode()).hexdigest()[:18]
    context=camera+(':cut' if disrupted else ':before')
    markers=[];routes=[]
    for entry in entries:
        if not entry['location']:continue
        m=dict(entry['location'],products=entry['products'],sources=entry['sources'],score=None)
        is_origin=entry['name']==origin
        m.update(role='supplier' if is_origin else 'alternative',
                 role_label=('중단 기업 · 가정' if disrupted else '선택 공급사') if is_origin else '제품군 검토 후보',
                 impact='origin' if disrupted and is_origin else 'normal')
        markers.append(m)
    destination=None
    if recipient:
        entity=network['entities'][recipient];p=entity.get('map_location')
        if p:
            destination=recipient
            markers.append(dict(id=recipient,name=entity['name']+' · 가정 수요처',site=p['name'],lat=p['lat'],lon=p['lon'],
                                role='recipient',impact='exposed' if disrupted else 'normal',score=None,
                                role_label='사용자 가정 수요처 · 거래 미확인',location_source=p.get('source')))
    ids={m['id'] for m in markers}
    if chosen['map_id'] in ids and destination:
        routes.append(dict(start=chosen['map_id'],end=destination,kind='primary',status='blocked' if disrupted else 'normal',
                           material=group['name']+' · 공급 가정 (거래 미확인)',sources=chosen['sources']))
    if disrupted:
        for entry in entries:
            if entry['name']==origin or entry['map_id'] not in ids:continue
            end=destination or (chosen['map_id'] if chosen['map_id'] in ids else None)
            if end and entry['map_id']!=end:
                routes.append(dict(start=entry['map_id'],end=end,kind='alternative',status='candidate',
                    material=group['name']+(' · 대체 조달 가정' if destination else ' · 공급자 비교선 (운송 아님)'),
                    sources=entry['sources'],products=entry['products']))
    for route in routes:route['id']=route['kind']+'|'+route['start']+'|'+route['end']
    return dict(markers=markers,routes=routes,review=True,applied=disrupted,response=disrupted,alternative=None,loss=0,
                context=context,camera_context=camera,title=group['name'],process=group['stage'],
                status_label='제품군 기반 가정 · 실제 고객관계·운송경로 아님',
                scenario_summary=origin+' · '+group['name']+(' 공급 중단 가정' if disrupted else ' 적용 전'),
                missing_locations=[e['name'] for e in entries if not e['location']]),entries,group


def enrich_process_profile(network,case,profile):
    """Extend only registered exact item groups; never infer links by stage alone."""
    if case.get('kind')=='logistics' or case.get('event')=='관세 부과':return profile
    catalog=load_process_catalog()
    groups={item:key for key,g in catalog['groups'].items() if not g['catalog_item'] for item in g['item_ids']}
    rows=[r for r in case.get('connections',[]) if r['item'] in groups]
    if not rows:return profile
    candidates=list(profile.get('candidates',[]))
    blocked={r['supplier'] for r in case.get('connections',[])}
    for row in rows:
        for entry in group_offerings(network,groups[row['item']],catalog=catalog):
            if entry['company_id'] in blocked or not entry['location']:continue
            token=(entry['map_id'],row['recipient'],row['material'])
            if any((c['company_id'],c['recipient'],c['material'])==token for c in candidates):continue
            candidates.append(dict(company_id=entry['map_id'],recipient=row['recipient'],material=row['material'],
                                   name=entry['name'],source=entry['sources'][0],sources=entry['sources'],
                                   products=entry['products'],location=entry['location']))
    if not candidates:return profile
    names=list(dict.fromkeys(c.get('name') or network['entities'][c['company_id']]['name'] for c in candidates))
    return dict(profile,candidates=candidates,candidate_id=candidates[0]['company_id'],candidate_eligible=True,
                name=' · '.join(names),source=candidates[0]['source'],
                summary='공식 제품군 기준의 검토 후보입니다. 장비 방식·대상 막·공정 레시피·설치·고객 승인·납기 확인이 필요하며 즉시 교체나 생산 회복을 뜻하지 않습니다.')
