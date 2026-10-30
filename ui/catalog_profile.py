"""One catalog candidate profile shared by main-map routes and explanations."""
from .simulation_candidates import catalog_candidates, ITEM_RULES
from .research_map import map_matches


def has_photoresist(network,case):
    node=network['nodes'].get(case['target'],{})
    return node.get('item_id')=='photoresist' or any(r.get('item')=='photoresist' for r in case.get('connections',[]))


def enrich_catalog_profile(network,case,profile,product_class=None):
    if case.get('kind')=='logistics' or case.get('event')=='관세 부과':return profile
    node=network['nodes'].get(case['target'],{})
    rows=case.get('connections') or [dict(item=node.get('item_id') or node.get('material_id'),material=node.get('name',''))]
    covered={r['material'] for r in rows if r['item'] in ITEM_RULES}
    if not covered:return profile
    entries=catalog_candidates(network,case,product_class)
    candidates=[dict(c) for c in profile.get('candidates',[]) if c['material'] not in covered]
    index={}
    for entry in entries:
        record=entry['record']
        mapped=map_matches(network,'',candidates=[dict(name=record['supplier'],products=[record['name']])])
        marker=next((m for m in mapped['markers'] if m.get('candidate_name')==record['supplier']),None)
        key=marker['id'] if marker else record.get('supplier_network_id') or 'catalog:'+record['supplier']
        for recipient, material in entry['links']:
            token=(key,recipient,material)
            c=index.setdefault(token,dict(company_id=key,name=record['supplier'],recipient=recipient,material=material,
                source=entry['sources'][0]['url'],sources=[],products=[],location=marker))
            if record['name'] not in c['products']:c['products'].append(record['name'])
            for source in entry['sources']:
                if source['url'] not in c['sources']:c['sources'].append(source['url'])
    candidates.extend(index.values())
    names=list(dict.fromkeys(c.get('name') or network['entities'][c['company_id']]['name'] for c in candidates))
    mapped=[c for c in candidates if c.get('location') or network['entities'].get(c['company_id'],{}).get('map_location')]
    primary=(mapped or candidates or [None])[0]
    result=dict(profile,candidates=candidates,candidate_id=primary['company_id'] if primary else None,
        candidate_eligible=bool(candidates),name=' · '.join(names) if names else '등록 후보 없음',
        product_class=(product_class or '전체 제품군') if has_photoresist(network,case) else profile.get('product_class','전체 제품군'),common_classes=sorted({e['record']['fields']['exposure']['value'] for e in entries if 'exposure' in e['record']['fields']}),
        source=primary['source'] if primary else None,level='동일 제품군 후보',
        summary=('공개 제품 자료 기준 '+str(len(names))+'개 기업의 조달 검토 후보입니다. 점선은 고객별 규격·승인·여력 확인이 필요한 연결이며 실제 운송 경로나 공급 회복을 확정하지 않습니다.') if names else '선택 품목·제품군에서 후보 근거를 찾지 못했습니다. 대체 불가능 판정은 아닙니다.',
        rows=[('후보 범위','제품 자료 확인', ' · '.join(names) if names else '선택 범위 내 자료 부족'),
              ('지도 위치','위치 확인',str(len({c['company_id'] for c in mapped}))+'개 기업 위치 표시 · 본사 등 등록 거점'),
              ('제품 조건','추가 검증','규격·순도·노광/현상 방식·연마 대상 막을 대조합니다.'),
              ('전환 조건','추가 검증','고객 승인·증량 여력·납기·실제 출하 공장과 운송 경로를 확인합니다.')])
    # Old evidence tables compare one fixed vendor; keep that verdict out of multi-vendor cards.
    for key in ('evidence','sources','reviewed_at'):result.pop(key,None)
    return result
