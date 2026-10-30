"""Curated demonstration scope; presentation filtering never changes the engine."""
import json
from pathlib import Path
from simulation.resilience import calculate_supply_shock


def core_cases():
    return json.loads((Path(__file__).parent/'data/core_cases.json').read_text(encoding='utf-8'))['cases']


def core_ids(network):
    items={item for case in core_cases() for item in case['item_ids']}
    ids=set()
    for edge in network['visual_edges']:
        evidence=edge.get('evidence',{})
        if edge['kind']=='backbone' and edge.get('calculation_included') and evidence.get('item_id') in items:
            ids.update((edge['from'],evidence['from']))
    return ids


def case_for_target(network,target):
    for case in core_cases():
        ids=set()
        for edge in network['visual_edges']:
            evidence=edge.get('evidence',{})
            if edge['kind']=='backbone' and edge.get('calculation_included') and evidence.get('item_id') in case['item_ids']:
                ids.update((edge['from'],evidence['from']))
        if target in ids: return case
    return None


def display_network(network,show_reference=False):
    if show_reference: return network
    edges=[e for e in network['visual_edges'] if e.get('calculation_included',True)
           and not e.get('score_excluded',False) and not network['nodes'][e['from']].get('score_excluded',False)]
    return dict(network,visual_edges=edges)


def response_comparison(network,events,days,scopes,case):
    variants=[('재고·대체 없음',False,False),('재고만 적용',True,False),('재고+대체 공급',True,True)]
    rows=[]
    for label,inventory,bypass in variants:
        result=calculate_supply_shock(network,events,days,inventory,bypass,scopes)
        for company in case['recipients']:
            view=result['process_views'][company]
            score=view['scores'].get(case['process'])
            first=view['first_hit'].get(case['process'])
            rows.append({'조건':label,'기업':network['nodes'][company]['name'],'공정':case['process'],
                         '말일 소재 충족도':None if score is None else round(score,1),
                         '첫 소재 부족일':str(first)+'일째' if first is not None else '관측 내 없음'})
    return rows
