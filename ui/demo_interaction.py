"""Versioned, allowlisted map selection shared with the presentation cards."""
import hashlib
import json


def route_id(route):return route['kind']+'|'+route['start']+'|'+route['end']


def valid_pick(event,data):
    if not isinstance(event,dict) or event.get('context')!=data.get('context'):return None
    kind=event.get('kind');key=event.get('id')
    if kind=='clear':return dict(kind='clear',id=None,context=data['context'])
    allowed=([m['id'] for m in data['markers']] if kind=='marker' else
             [r['id'] for r in data['routes']] if kind=='route' else [])
    if not isinstance(key,str) or key not in allowed:return None
    return dict(kind=kind,id=key,context=data['context'])


def prepare_map(data,state):
    from .demo_scenarios import decorate
    from .demo_comparison import compare_view
    from copy import deepcopy
    data=deepcopy(data)
    case=state.get('demo_applied') or {}
    if case and case.get('id')==data.get('case_id'):data=decorate(data,case)
    data['revision']=state.get('demo_revision',0);data['step']=state.get('demo_step',1)
    data['camera_markers']=data.get('camera_markers',[(m['id'],m['lat'],m['lon']) for m in data['markers']])
    seed=[data['revision'],data['step'],data.get('case_id'),data.get('product_class'),
          data.get('event'),case.get('event'),data['camera_markers']]
    data['camera_context']=hashlib.sha256(json.dumps(seed,ensure_ascii=True).encode()).hexdigest()[:20]
    # A prepared baseline can pass through twice in the review layout.
    if data.get('comparison')=='적용 전':data['applied']=bool(case)
    data=compare_view(data,case,state.get('demo_compare','사건 적용'))
    data['routes']=[dict(r,id=route_id(r)) for r in data['routes']]
    frame=[data['camera_context'],data.get('comparison'),[r['id'] for r in data['routes']]]
    data['context']=hashlib.sha256(json.dumps(frame,ensure_ascii=True).encode()).hexdigest()[:20]
    selected=valid_pick(state.get('demo_inspection'),data)
    data['selected']=selected if selected and selected['kind']!='clear' else None
    if not data['selected']:state.pop('demo_inspection',None)
    state['demo_map_context']=data['context'];state['demo_current_map']=data
    return data


def accept_pick(state,event,data):
    if state.get('demo_revision',0)!=data.get('revision') or state.get('demo_step',1)!=data.get('step'):return False
    if state.get('demo_active_case_id')!=data.get('case_id') or state.get('demo_map_context')!=data.get('context'):return False
    selected=valid_pick(event,data)
    if not selected:return False
    if selected['kind']=='clear':state.pop('demo_inspection',None)
    else:state['demo_inspection']=selected
    return True


def selection_description(data,case,profile=None):
    selected=data.get('selected')
    if not selected:return None
    material=(profile or {}).get('material') or case.get('material_label') or ('폴리시드 웨이퍼' if case['id']=='wafer' else '포토레지스트')
    product=(profile or {}).get('product_class')
    scope=material+(' / '+product if product and product!='전체 제품군' else '')+' · '+case['process']
    if selected['kind']=='marker':
        marker=next(m for m in data['markers'] if m['id']==selected['id'])
        if marker.get('processes'):scope=material+' · '+' · '.join(marker['processes'])
        role=marker['role']
        labels={'supplier':'원래 공급사','recipient':'등록 수요기업','alternative':'대체 검토 후보','blocked_port':'차질 가정 항만','detour_port':'우회 검토 후보'}
        if data.get('comparison')=='적용 전':labels['blocked_port']='기존 경유 항만'
        text={'supplier':'선택 소재의 원래 공급 연결입니다. 표시된 회사 거점은 실제 출하 공장·운송 계약을 확정하지 않습니다.',
              'recipient':'선택 소재와 관련 공정의 등록 수요기업입니다. 회사 전체의 생산 중단을 뜻하지 않습니다.',
              'alternative':(profile or {}).get('summary','제품군 근거와 고객별 승인·증량 조건을 함께 확인해야 합니다.'),
              'blocked_port':'이 사건에서 차질을 가정한 경유점입니다. 실제 화물 경유·운송 계약은 별도 확인 대상입니다.',
              'detour_port':'지리적 우회 검토 후보입니다. 화물 취급·운항·통관·내륙 운송 조건을 확인해야 합니다.'}
        if role=='alternative' and marker.get('products'):
            text['alternative']='공개 제품: '+' · '.join(marker['products'])+'. 표시 위치: '+marker['site']+'. 고객별 규격·승인·추가 공급 여력과 실제 출하 공장은 별도 확인 대상입니다.'
        return dict(title=marker['name'],subtitle=labels.get(role,role)+' · '+scope,text=text.get(role,''),role=role)
    route=next(r for r in data['routes'] if r['id']==selected['id'])
    scope=route.get('material',material)+' · '+(route.get('process_label') or case['process'])
    nodes={m['id']:m for m in data['markers']}
    candidate=route['kind']!='primary'
    return dict(title=nodes[route['start']]['name']+' → '+nodes[route['end']]['name'],
                subtitle=('적용 전 등록 연결' if data.get('comparison')=='적용 전' else '검토 후보 경로' if candidate else '관세·비용 영향' if data.get('tariff') else '중단 가정 경로' if route.get('status')=='blocked' else '공급 제한 경로')+' · '+scope,
                text=((profile or {}).get('summary','실행 가능성을 확인할 후보 경로입니다.') if candidate else
                      '등록된 관계와 시나리오를 연결한 선입니다. 고객의 실제 사용 등급이나 실제 선박 항적을 확정하지 않습니다.'),
                role='candidate_route' if candidate else 'primary_route')
