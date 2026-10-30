"""Public facility scope, not live outages, capacity estimates or substitution approvals."""
import json
import re
import unicodedata
from pathlib import Path
from hashlib import sha256

PATH=Path(__file__).resolve().parents[1]/'data/facility_evidence.json'

def load_facilities():return json.loads(PATH.read_text(encoding='utf-8'))

def mentioned(text,alias):
    text=unicodedata.normalize('NFKC',text).casefold();alias=unicodedata.normalize('NFKC',alias).casefold()
    pattern=re.escape(alias)
    if alias.isascii():pattern=r'(?<![a-z0-9])'+pattern+r'(?![a-z0-9])'
    return bool(re.search(pattern,text))

def facility_scope(query,selected_id=''):
    data=load_facilities()
    groups={k for k,g in data['groups'].items() if any(mentioned(query,a) for a in g['aliases'])}
    explicit=[f for f in data['facilities'] if any(mentioned(query,a) for a in [f['name']]+f['aliases']) and (not groups or f['group'] in groups)]
    if not groups:groups={f['group'] for f in explicit}
    if not groups and mentioned(query,'NF3') and not any(mentioned(query,n) for n in ('SK','SK스페셜티','SK specialty','SKspecialty','에스케이','Air Liquide','MATHESON','Linde','EFC')):groups={'hyosung'}
    facilities=[f for f in data['facilities'] if f['group'] in groups]
    selected=next((f for f in facilities if f['id']==selected_id),None)
    if not selected and len(explicit)==1:selected=explicit[0]
    internal=[]
    if selected:
        for f in facilities:
            if f['group']!=selected['group'] or f['id']==selected['id']:continue
            shared=set(selected['product_tags'])&set(f['product_tags'])
            if 'foundry' in shared:
                shared={x for x in shared if x.startswith('node:')}
                status='표기 공정 겹침 · 전환 미확인' if shared else '공정 호환 미확인'
            elif shared:status='생산 품목 겹침 · 전환 미확인'
            elif not selected['product_tags'] or not f['product_tags']:status='공장별 제품 근거 부족'
            else:status='공개 생산 단계 다름'
            internal.append(dict(facility_id=f['id'],name=f['name'],status=status,shared_products=sorted(shared),
                same_region=selected['city']==f['city'],transfer_confirmed=False))
    ids={sid for f in facilities for sid in f['source_ids']}
    return dict(selected=selected,facilities=facilities,internal_options=internal,sources={k:data['sources'][k] for k in ids},
        scope_status='공장 선택됨 · 피해 사실 미확정' if selected else '대상 공장 미지정 · 기업 전체 피해로 확대하지 않음',
        limits=data['limits'],checked_at=data['checked_at'])

def facility_map(scope):
    groups={};selected=scope['selected'];byid={x['facility_id']:x for x in scope['internal_options']}
    for f in scope['facilities']:
        key=(f['lat'],f['lon']);groups.setdefault(key,[]).append(f)
    markers=[]
    for (lat,lon),items in groups.items():
        chosen=next((f for f in items if selected and f['id']==selected['id']),None)
        internal=any(byid.get(f['id'],{}).get('shared_products') for f in items)
        markers.append(dict(id='facility-region:'+items[0]['id'],name=' / '.join(f['name'] for f in items),lat=lat,lon=lon,
            role='alternative' if internal and not chosen else 'supplier',score=None,
            role_label=('선택 공장 지역' if chosen else '내부 검토 지역' if internal else '생산거점 지역')+' · 개략점',
            candidate_name=chosen['name'] if chosen else '',site=items[0]['city'],facility_ids=[f['id'] for f in items]))
    context=sha256(json.dumps([f['id'] for f in scope['facilities']]).encode()).hexdigest()[:16]
    data=dict(markers=markers,routes=[],comparisons=[],review=True,applied=False,response=False,context=context,
        camera_context=context+(':'+selected['id'] if selected else ':all'),title='공장별 생산 범위',status_label='지역 개략점 · 피해·전환 확정 아님',process='',loss=0)
    if selected:
        marker=next(m for m in markers if selected['id'] in m['facility_ids'])
        data['camera_focus']=dict(lat=marker['lat'],lon=marker['lon'],distance=2.4)
        data['selected']=dict(kind='marker',id=marker['id'],context=context)
    return data
