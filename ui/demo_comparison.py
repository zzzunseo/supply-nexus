"""Presentation-only before/after views; never mutate applied conditions."""
from copy import deepcopy

BEFORE='적용 전'
AFTER='사건 적용'


def change_comparison(state):
    # Changing the display must not restart the flight or invalidate the case.
    if state.get('demo_compare') not in (BEFORE,AFTER):state['demo_compare']=AFTER
    state.pop('demo_inspection',None)


def compare_view(data,case,mode):
    data=deepcopy(data)
    enabled=bool(case and data.get('applied'))
    data['comparison']=mode if enabled else None
    if not enabled:return data
    origin=next((m['name'] for m in data['markers'] if m['role']==('blocked_port' if data.get('logistics') else 'supplier')),'선택 대상')
    material=data.get('material','선택 품목')
    event=case.get('event') or ('완전 봉쇄' if case.get('kind')=='logistics' and case['percent']==100 else '부분 통항 제한' if case.get('kind')=='logistics' else '공급 중단' if case['percent']==100 else '공급 감소')
    amount='' if event in ('공급 중단','완전 봉쇄') else f" · {case['percent']:g}%"
    data['scenario_summary']=f"{origin} · {material} | {event}{amount} · {case['days']}일 가정"
    if mode==BEFORE:
        data['routes']=[r for r in data['routes'] if r['kind']=='primary']
        ids={key for r in data['routes'] for key in (r['start'],r['end'])}
        data['markers']=[m for m in data['markers'] if m['id'] in ids]
        for marker in data['markers']:marker['impact']='normal'
        for route in data['routes']:route['status']='normal'
        data.update(applied=False,tariff=False,selected=None)
    return data
