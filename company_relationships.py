"""Read-only company/material relationships and explicit simulation coverage."""
from collections import defaultdict

VARIANTS={'gallium':'갈륨 화합물 확장','germanium':'게르마늄계 확장',
          'package_gold':'금 본딩 와이어','package_palladium':'Pd 코팅 와이어',
          'package_silver':'은 소결 접합','package_tin':'주석 솔더'}


def variant_scopes(network,target):
    return sorted({node.get('scope') for key,node in network['nodes'].items()
                   if (key==target or node.get('company_id')==target) and node.get('scope') in VARIANTS})


def relationship_rows(network,result=None,target=None,process='전체',direction='전체'):
    nodes=network['nodes']; scopes=set((result or {}).get('scopes',['core']))
    children=defaultdict(set)
    for key,node in nodes.items():
        for parent in node.get('requires',[]): children[parent].add(key)
    reached=set(); pending=[target] if target in nodes else []
    while pending:
        key=pending.pop()
        if key in reached: continue
        reached.add(key)
        if nodes[key]['kind'] not in ('operation','process'): pending.extend(children[key])
    rows=[]; seen=set()
    for edge in network['visual_edges']:
        source=nodes.get(edge['from'],{}); recipient=nodes.get(edge['to'],{})
        if recipient.get('kind')!='company' or source.get('kind') not in ('company','product','material','resource'):
            continue
        evidence=edge.get('evidence',{})
        supplier=evidence.get('from') or source.get('company_id') or edge['from']
        if supplier==edge['to']: continue
        processes=edge.get('processes',[])
        if process!='전체' and process not in processes: continue
        outgoing=target in (supplier,edge['from']) or edge['from'] in reached or edge.get('transport_node') in reached
        incoming=target==edge['to']
        via=edge.get('logistics_via',[])
        if target and not (outgoing or incoming or target in via): continue
        if target and direction=='공급받는 경로' and not incoming: continue
        if target and direction=='공급하는 경로' and not outgoing: continue
        material=evidence.get('item') or source.get('name',edge.get('label','소재'))
        token=(supplier,edge['to'],material,tuple(processes))
        if token in seen: continue
        seen.add(token)
        included=edge.get('calculation_included',True) and not source.get('score_excluded',False)
        basis='공급관계 근거' if edge['kind']=='backbone' and included else '참고·계산 제외' if not included else '용도 기반 경로 가정'
        active=edge.get('scope','core') in scopes
        metric=edge.get('transport_node') or edge.get('calc_target') or edge['from']
        value=(result or {}).get('nodes',{}).get(metric,{}).get('effective')
        rows.append(dict(id=edge['id'],supplier_id=supplier,recipient_id=edge['to'],material_id=edge['from'],
            supplier=nodes.get(supplier,source).get('name',supplier),recipient=recipient['name'],material=material,
            processes=list(processes),via=list(via),scope=edge.get('scope','core'),active=active,included=included,
            basis=basis,source=evidence.get('relationship_source') or edge.get('source') or source.get('source'),
            fulfillment=value*100 if included and active and value is not None else None,
            origin=nodes.get(supplier,source).get('country','미확인'),destination=recipient.get('country','미확인')))
    grouped={}
    for row in rows:
        token=(row['supplier_id'],row['recipient_id'],row['material'],row['scope'],row['included'],tuple(row['via']),row['basis'])
        if token not in grouped:
            grouped[token]=row
        else:
            previous=grouped[token]
            previous['processes']=list(dict.fromkeys(previous['processes']+row['processes']))
            values=[v for v in (previous['fulfillment'],row['fulfillment']) if v is not None]
            previous['fulfillment']=min(values) if values else None
    return sorted(grouped.values(),key=lambda r:(not r['included'],not r['active'],r['basis']!='공급관계 근거',r['supplier'],r['recipient'],r['material'],r['id']))


def target_coverage(network,target):
    node=network['nodes'][target]
    rows=relationship_rows(network,target=target)
    outgoing=[r for r in rows if r['supplier_id']==target or r['material_id']==target]
    included=[r for r in outgoing if r['included']]
    incoming=[r for r in rows if r['recipient_id']==target]
    variants=variant_scopes(network,target)
    reserves=[key for key,n in network['nodes'].items() if n['kind']=='reserve' and target in n.get('requires',[])]
    if node['kind']=='logistics': status='물류 경유 제약'; reason='등록된 경유 공급 경로에 통항 조건을 적용합니다.'
    elif variants: status='제품군 선택 필요'; reason='관련 제품군을 선택하면 해당 소재 경로를 계산에 포함합니다.'
    elif included: status='소재 공급 계산'; reason=f'등록된 소재 공급 경로 {len(included)}개에 연결됩니다. 재고·대체 공급에 따라 점수 변화가 달라집니다.'
    elif any(company==target for company,_ in network.get('operations',{})):
        status='입고 소재 관측 기업'; reason='이 기업의 점수는 공급받는 소재 기준입니다. 기업 가동 중단 자체를 소재 부족으로 환산하지 않습니다.'
    elif outgoing: status='장비·참고 관계'; reason='장비·참고 공급관계가 등록되어 있으며 소재 점수를 낮추지 않습니다.'
    elif incoming: status='공급관계 참고 등록'; reason='관련 입고 관계만 등록되어 있으며 이 기업의 공정별 소재 점수는 미등록입니다.'
    elif reserves: status='대체 공급 전용'; reason='대체 공급이 실제 사용되는 조건에서만 영향을 줍니다. 정상 공급 경로는 등록되지 않았습니다.'
    else: status='공급 품목 미연결'; reason='대상은 등록돼 있지만 계산에 사용할 공급 품목·고객 경로가 연결되지 않았습니다.'
    return dict(status=status,reason=reason,outgoing=len(outgoing),incoming=len(incoming),variants=variants)
