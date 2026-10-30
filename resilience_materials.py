"""Sourced product candidates; customer routes and resilience parameters are assumptions."""
import json
from pathlib import Path
from evidence_review import PRODUCT_LABELS


CATALOG = Path(__file__).parent/'data/materials_extension.json'


def extend_materials(network, add, line):
    catalog=json.loads(CATALOG.read_text(encoding='utf-8'))
    nodes=network['nodes']
    for vendor in catalog['vendors']:
        add(vendor['id'],vendor['name'],'company',vendor['country'],None,None,
            aliases=vendor['aliases'],source=vendor['source'],buffer_direct=False,
            source_note='기업 제품군 참고 자료. 개별 제품 종류·생산국·사업장·고객 계약은 별도 확인 필요.')
    material_ids=set()
    for spec in catalog['materials']:
        if spec['id'] in material_ids or not spec['suppliers']:
            raise ValueError('확장 소재 ID 중복 또는 공급 후보 누락')
        material_ids.add(spec['id'])
        scope='material:'+spec['id'];spec['scope']=scope
        candidates=[]
        for supplier in spec['suppliers']:
            company=supplier['company'];vendor=nodes[company]
            key=f"extended:{spec['id']}:{company}"
            deps=[company]
            if spec.get('upstream'):
                # Corporate origin sourcing is an explicit scenario dependency.
                deps.append('raw:'+spec['upstream'])
            add(key,vendor['name']+' · '+spec['name'],'material',vendor['country'],None,None,
                requires=deps,scope=scope,company_id=company,aliases=spec['aliases'],
                inventory_days=spec['inventory_days'],source=supplier['source'],
                source_note=supplier['evidence']+' '+spec['recipe_note'],
                material_id=spec['id'],production_country=None,actual_share_pct=None)
            candidates.append(key)
            line(company,key,calc_target=key,scope=scope,label=spec['name'],
                source=supplier['source'],processes=spec['processes'])
            if spec.get('upstream'):
                line('raw:'+spec['upstream'],key,calc_target=key,scope=scope,
                    label='원산지 연계 가정 · '+spec['name'],processes=spec['processes'])
        # Additional output capacity from a secondary product candidate. A
        # separate pool is shared by all requests for this specific grade family.
        pool=None
        if len(candidates)>1:
            provider=spec['suppliers'][-1]['company'];v=nodes[provider]
            pool='reserve:extended:'+spec['id']
            dependencies=[provider]
            if spec.get('upstream'):
                dependencies.append('raw:'+spec['upstream'])
            add(pool,spec['name']+' · 추가 예약 대체풀','reserve',v['country'],None,None,
                requires=dependencies,scope=scope,company_id=provider,
                capacity_units=.4,source=spec['suppliers'][-1]['source'],
                aliases=spec['aliases'],material_id=spec['id'],
                source_note='추가 예약 생산·인증·등급 호환성은 가정. 정상 공급량과 별도인 추가 여력만 계산.')
            for key in candidates:
                if nodes[key]['company_id']!=provider:
                    nodes[key].update(alt_vendor=pool,alt_capacity=spec['alt_capacity'],
                        alt_qualification_days=spec['qualification_days'],alt_ramp_days=spec['ramp_days'])
        for process in spec['processes']:
            for (company,p),op in network['operations'].items():
                if p!=process:continue
                if spec['group']=='웨이퍼 대체 후보':
                    item='polished-wafer' if spec['id']=='wafer-polished-extra' else 'epi-wafer'
                    mix=nodes[f'mix:{company}:{item}']
                    mix['requires'].extend(candidates)
                    mix['weights'].extend([1.]*len(candidates))
                    for key in candidates:
                        line(key,company,calc_target=mix['id'],scope=scope,processes=[p],
                            label=spec['name']+' · 병렬 대체 후보·균등 비중 가정')
                    continue
                mix=f"extended-mix:{spec['id']}:{company}:{p}"
                add(mix,spec['name']+' · 병렬 공급','mix',nodes[company]['country'],None,None,
                    requires=candidates,weights=[1.]*len(candidates),mode='mix',scope=scope,visible=False)
                nodes[op]['requires'].append(mix)
                for key in candidates:
                    line(key,company,calc_target=mix,scope=scope,processes=[p],
                        label=spec['name']+' · 구매 비중 균등 가정')
        spec['candidate_nodes']=candidates;spec['reserve_node']=pool
    network['extended_materials']={s['id']:s for s in catalog['materials']}
    network['extended_vendors']=catalog['vendors']
    return network


def scopes_for_targets(network, targets):
    targets=set(targets)
    scopes=set()
    for spec in network['extended_materials'].values():
        if targets.intersection(spec['candidate_nodes']) or spec['reserve_node'] in targets or any(
                s['company'] in targets for s in spec['suppliers']) or ('raw:'+str(spec.get('upstream'))) in targets:
            scopes.add(spec['scope'])
    return sorted(scopes)


def material_rows(network):
    rows=[]
    for spec in network['extended_materials'].values():
        for supplier in spec['suppliers']:
            v=network['nodes'][supplier['company']]
            node=network['nodes'][f"extended:{spec['id']}:{supplier['company']}"]
            alt=network['nodes'].get(node['alt_vendor'])
            basis = node.get('product_evidence', {})
            rows.append(dict(소재=spec['name'],분류=spec['group'],공정=' / '.join(spec['processes']),
                공급후보=v['name'],기업소속국=v['country'],실제생산국='미확인',
                제품근거=node.get('source'),근거범위=supplier['evidence'],고객납품='가정·미확인',
                제품종류확인=PRODUCT_LABELS.get(basis.get('product_basis'), '제품 종류 미확인'),
                공정용도='조건부 용도 근거' if basis.get('technical_use_basis') == 'documented' else '미확인',
                필수사용='미확인',현재품목계약='미확인',사용조건=basis.get('condition'),
                구매비중='균등 가정',재고일_가정=spec['inventory_days'],
                우회인증일_가정=node.get('alt_qualification_days') if alt else None,
                우회확대일_가정=node.get('alt_ramp_days') if alt else None,
                우회=(network['nodes'][alt['company_id']]['name']+' 추가 예약풀 가정') if alt else
                    '정상 병렬 공급만 유지 · 추가 예약 없음' if len(spec['suppliers'])>1 else '등록된 대체 후보 없음',
                검색어=' / '.join(spec['aliases']),적용조건=spec['recipe_note']))
    return rows
