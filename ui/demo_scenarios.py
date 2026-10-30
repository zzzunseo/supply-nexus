"""Explicit presentation selections derived from registered product relationships."""
from copy import deepcopy
from .logistics_demo import demo_cases
from simulation.evidence import relationship_decision


def connections(network,include_reference=False):
    rows=[]
    for edge in network['visual_edges']:
        product=network['nodes'].get(edge['from'],{})
        supplier=product.get('company_id')
        if edge['kind']!='backbone' or not supplier or not product.get('item_id'):continue
        if not include_reference and not relationship_decision(edge.get('evidence',{}))[0]:continue
        if not network['entities'].get(supplier,{}).get('map_location'):continue
        if not network['entities'].get(edge['to'],{}).get('map_location'):continue
        rows.append(dict(target=edge['from'],supplier=supplier,recipient=edge['to'],
                         material=edge.get('label',product['name']),item=product['item_id'],
                         processes=edge.get('processes',[]),evidence=edge.get('evidence',{})))
    return rows


def choices(network,category):
    rows=connections(network)
    if category=='항만·해협':return [(c['target'],c['name']) for c in demo_cases() if c.get('kind')=='logistics']
    ids=list(dict.fromkeys(r['supplier'] if category=='기업' else r['target'] for r in rows))
    return [(key,network['nodes'][key]['name']) for key in ids]


def selected_case(network,category,target,event):
    if category=='항만·해협':
        case=deepcopy(next(c for c in demo_cases() if c['target']==target));case['event']=event;return case
    rows=[r for r in connections(network) if (r['supplier'] if category=='기업' else r['target'])==target]
    if not rows:raise ValueError('표시할 등록 공급 연결이 없습니다.')
    # Retain the deeper curated comparison for the two reviewed product selections.
    curated=next((c for c in demo_cases()[:2] if c['target']==target),None) if category=='소재' else None
    case=deepcopy(curated) if curated else dict(id='selected:'+target,days=60,
        target=rows[0]['target'],recipients=list(dict.fromkeys(r['recipient'] for r in rows)),
        process=' · '.join(dict.fromkeys(p for r in rows for p in r['processes'])),
        evidence='등록된 기업 관계·제품 용도 자료를 연결한 검토 범위입니다. 개별 품목의 현행 계약을 확정하지 않습니다.',
        limits='기업 위치는 대표 거점입니다. 붉은 영역은 사건 위치 강조이며 실제 피해 면적·피해량이 아닙니다.',
        relationship_source=rows[0]['evidence'].get('relationship_source') or rows[0]['evidence'].get('source'),
        product_source=network['nodes'][rows[0]['target']].get('source'),connections=rows)
    case.update(name=network['nodes'][target]['name']+' · '+event,event=event,
                issue_target=target,selection_category=category,
                material_label=' · '.join(dict.fromkeys(r['material'] for r in rows)))
    return case


def decorate(data,case):
    """Scenario semantics are shared by WebGL and the basic map."""
    tariff=case.get('event')=='관세 부과'
    full=case.get('event') in ('공급 중단','완전 봉쇄') or case.get('percent')==100
    data.update(event=case.get('event','완전 봉쇄' if case.get('kind')=='logistics' and full else '공급 차질'),
                tariff=tariff,material=case.get('material_label','폴리시드 웨이퍼' if case['id']=='wafer' else '포토레지스트'))
    if data.get('logistics') and data.get('exposure') and not data.get('response'):
        data['material']=f"등록 경유 소재 {data['exposure']['materials']}종 · 경유 가정"
    for marker in data['markers']:
        origin=marker['role']==('blocked_port' if data.get('logistics') else 'supplier')
        marker['impact']=('cost' if tariff else 'origin' if origin else 'exposed') if data.get('applied') and (origin or marker['role']=='recipient') else 'normal'
    for route in data['routes']:
        route['status']=('cost' if tariff else 'blocked' if full else 'restricted') if data.get('applied') and route['kind']=='primary' else 'candidate' if route['kind']!='primary' else 'normal'
        route.setdefault('material',data['material'])
    return data


def custom_payload(network,case,applied):
    markers={};routes=[]
    for row in case['connections']:
        for key,role in ((row['supplier'],'supplier'),(row['recipient'],'recipient')):
            entity=network['entities'][key];place=entity['map_location']
            markers[key]=dict(id=key,name=entity['name'],site=place['name'],lat=place['lat'],lon=place['lon'],role=role,score=None)
        prior=next((r for r in routes if r['start']==row['supplier'] and r['end']==row['recipient']),None)
        if prior:prior['material']+=' · '+row['material']
        else:routes.append(dict(start=row['supplier'],end=row['recipient'],kind='primary',material=row['material']))
    return dict(markers=list(markers.values()),routes=routes,applied=applied,review=True,
                case_id=case['id'],title=case['name'],process=case['process'],loss=0,alternative=None,response=False)


def custom_profile(network,case):
    # Match documented products, never assumed reserve capacity or a customer contract.
    candidates=[]
    if case.get('event')!='관세 부과':
        rows=case.get('connections',[])
        for row in rows:
            for key,product in network['nodes'].items():
                supplier=product.get('company_id');proof=product.get('product_evidence',{})
                if product.get('kind')!='product' or product.get('item_id')!=row['item'] or supplier==row['supplier']:continue
                if proof.get('product_basis')!='documented' or not product.get('source'):continue
                if not network['entities'].get(supplier,{}).get('map_location'):continue
                entry=dict(company_id=supplier,recipient=row['recipient'],material=row['material'],source=product['source'])
                if entry not in candidates:candidates.append(entry)
    eligible=bool(candidates)
    return dict(kind='material',candidate_id=candidates[0]['company_id'] if candidates else None,candidates=candidates,
        candidate_eligible=eligible,name='제품군 기반 대체 검토' if eligible else '공급 연결과 대응 검토',
        material=case['material_label'],source=case.get('product_source'),
        rows=[('선택 범위','등록 연결',case['name']),
              ('관련 소재·공정','용도 연결',case['material_label']+' / '+case['process']),
              ('대응 방향','비용 검토' if case.get('event')=='관세 부과' else '대체 조달 검토',
               '품목·거래 국가·원산지·과세 기준 확인. 공급 단절로 처리하지 않습니다.' if case.get('event')=='관세 부과' else '공식 제품 근거가 있는 동일 품목 후보를 표시합니다. 규격·고객 승인·공급 여력은 별도 확인합니다.' if eligible else '제품 근거가 없는 품목은 대체 경로를 임의로 만들지 않습니다.')],
        summary='점선은 동일 품목의 제품 자료에 근거한 조달 검토 후보입니다. 고객 계약·등급 호환·공급 능력 또는 공급 회복을 확정하지 않습니다.' if eligible else '등록 공급 연결을 표시합니다. 추가 제품·후보 자료가 필요합니다.')


def legend(data):
    if data.get('comparison')=='적용 전':return '청록 실선: 적용 전 등록 연결 · 사건 효과·후보 숨김 · 오른쪽: 선택 사건 해설'
    if not data.get('applied'):return '청록: 기존 공급 연결 · 적용 전 미리보기'
    if data.get('tariff'):return '노랑: 관세·비용 영향 · 공급 단절 아님'
    return '빨강: 사건 발생·중단/제한 경로 · 주황: 영향 검토 기업 · 청록 점선: 대체 후보 · 파랑 점선: 물류 우회 후보'
