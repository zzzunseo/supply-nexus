"""Local WebGL presentation layer using verified location and engine outputs."""
from pathlib import Path
import streamlit as st

ROOT=Path(__file__).resolve().parents[1]


def alternative_supply(network,result,case):
    """Report only allocated end-day reserve output; never infer a contract."""
    product=network['nodes'][case['target']]
    amount=result['nodes'][case['target']].get('backup',0)
    pool_id=product.get('alt_vendor')
    pool=network['nodes'].get(pool_id,{})
    company_id=pool.get('company_id')
    if amount<=1e-7 or company_id not in network['entities']:
        return None
    return dict(company_id=company_id,name=network['entities'][company_id]['name'],
                pool_id=pool_id,material=product.get('item_id'),
                amount=round(amount*100,1),basis='모델상 예약 대체 공급')


def globe_payload(network,result,case,applied=False,response=False):
    if case.get('connections'):
        from .demo_scenarios import custom_payload
        return custom_payload(network,case,applied)
    if case.get('kind')=='logistics':
        from .logistics_demo import logistics_payload
        return logistics_payload(network,result,case,applied,response)
    product=network['nodes'][case['target']]
    supplier=product.get('company_id')
    if not supplier:
        raise ValueError('시연 소재의 공급사 정보가 없습니다.')
    markers=[]
    for key in (supplier,*case['recipients']):
        entity=network['entities'][key]
        place=entity.get('map_location')
        if not place:
            continue
        score=None if key==supplier else result['process_views'][key]['scores'].get(case['process'])
        markers.append(dict(id=key,name=entity['name'],lat=place['lat'],lon=place['lon'],
                            site=place['name'],score=score,role='supplier' if key==supplier else 'recipient'))
    origin=next((m for m in markers if m['id']==supplier),None)
    routes=[]
    if origin:
        for destination in markers:
            if destination['role']=='recipient':
                routes.append(dict(start=origin['id'],end=destination['id'],kind='primary'))
    alternative=alternative_supply(network,result,case) if response else None
    if alternative:
        entity=network['entities'][alternative['company_id']]
        place=entity.get('map_location')
        if place:
            existing=next((m for m in markers if m['id']==entity['id']),None)
            if existing:
                existing['also_alternative']=True
            else:
                markers.append(dict(id=entity['id'],name=entity['name'],lat=place['lat'],lon=place['lon'],
                                    site=place['name'],score=None,role='alternative'))
            for recipient in case['recipients']:
                if any(m['id']==recipient for m in markers):
                    routes.append(dict(start=entity['id'],end=recipient,kind='alternative'))
    return dict(markers=markers,routes=routes,applied=applied,
                alternative=alternative,response=response,
                title=case['name'],process=case['process'],loss=case.get('percent',0) if applied else 0)


@st.cache_resource
def component():
    return st.components.v2.component('night_supply_globe',
        html='<div class="night-root"></div>',
        css=(ROOT/'night_globe/style.css').read_text(encoding='utf-8'),
        js=(ROOT/'night_globe/dist/globe.js').read_text(encoding='utf-8'),
        isolate_styles=True)


def render_night_globe(network,result,case,applied=False,response=False,qualitative=False):
    data=globe_payload(network,result,case,applied,response)
    if qualitative:
        data['review']=True
        for marker in data['markers']:marker['score']=None
    return component()(data=data,key='demo_night_globe',
                       width='stretch',height=520)
