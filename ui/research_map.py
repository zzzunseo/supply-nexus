"""Deterministic mention lookup; never turns model prose into supply edges."""
import re
import unicodedata
from hashlib import sha256
import json
from pathlib import Path


def mentions(text, name):
    text=unicodedata.normalize('NFKC',text).casefold()
    name=unicodedata.normalize('NFKC',name).casefold().strip()
    if len(name)<2 or name not in text:return False
    pattern=re.escape(name)
    if name.isascii():pattern=r'(?<![a-z0-9])'+pattern+r'(?![a-z0-9])'
    else:pattern=r'(?<![가-힣a-z0-9])'+pattern
    return bool(re.search(pattern,text))


def map_matches(network,question,answer='',candidates=None,facility_id=''):
    # Research-only anchors include explicitly labeled address approximations.
    # They do not add nodes, capacities or contracts to the simulation engine.
    registry=json.loads((Path(__file__).resolve().parents[1]/'data/research_vendor_locations.json').read_text(encoding='utf-8'))
    entities=dict(network['entities'])
    for place in registry['locations']:
        entities[place['id']]=dict(id=place['id'],name=place['name'],aliases=place['aliases'],kind='company',
            map_location=dict(place,name=place['site']))
    network=dict(network,entities=entities)
    rows={};materials=[];processes=[];comparisons=[];routes=[]
    from news.material_scope import material_scope
    scope=material_scope(question)
    if scope.get('processes'):
        materials.append(scope['kind'])
        processes.extend(scope['processes'])
    def add(key,reason,origin):
        entity=network['entities'].get(key) or network['logistics'].get(key)
        if not entity:return
        # Product nodes can share a company's coordinates; draw the company once.
        if entity.get('company_id') in network['entities'] and entity['company_id']!=key:
            key=entity['company_id'];entity=network['entities'][key]
        place=entity.get('map_location') or (entity if key in network['logistics'] else {})
        if place.get('lat') is None or place.get('lon') is None:return
        if key not in rows:
            rows[key]=dict(id=key,name=entity['name'],lat=place['lat'],lon=place['lon'],
                site=place['name'],score=None,role='supplier',role_label='등록 위치 · '+origin,reason=reason,origin=origin,
                facility_kind=place.get('kind',place.get('location_type','등록 지점')),precision=place.get('precision',place.get('coordinate_precision','')),
                location_source=place.get('source'),coordinate_source=place.get('coordinate_source'),scope=place.get('scope',place.get('role_note','')))
    for origin,text in [('질문 언급',question),('답변 언급',answer)]:
        for key,entity in {**network['entities'],**network['logistics']}.items():
            if entity.get('company_id') and entity['company_id']!=key:continue
            if any(mentions(text,n) for n in [entity['name']]+entity.get('aliases',[])):
                add(key,'이름·등록 별칭 일치',origin)
        items=list(network['original']['items'])+list(network['extended_materials'].values())
        for item in items:
            aliases=item.get('aliases',[])+[item['name']]
            for node in network['nodes'].values():
                if node.get('item_id')==item['id']:aliases+=node.get('aliases',[])
            # An answer can discuss impurities (e.g. wafer oxygen) without
            # asking for that material's supply chain. Only canonical product
            # names expand material suppliers from prose; question aliases and
            # explicitly named companies/candidates remain supported.
            if origin=='답변 언급':aliases=[item['name']]
            if not any(mentions(text,n) for n in aliases):continue
            if item['name'] not in materials:materials.append(item['name'])
            for process in item.get('processes',[]):
                if process not in processes:processes.append(process)
            suppliers=[s['company_id'] for s in item.get('product_sources',[])]+[s['company'] for s in item.get('suppliers',[])]
            for key in suppliers:add(key,item['name']+' · 등록 제품 자료',origin)
    for candidate in candidates or []:
        place=candidate.get('external_location')
        if place:
            key='external:'+sha256(candidate['name'].encode()).hexdigest()[:12]
            rows[key]=dict(id=key,name=candidate['name'],lat=place['lat'],lon=place['lon'],site=place['site'],score=None,
                role='alternative',role_label='외부 검토 후보 · '+place['kind'],reason=candidate.get('reason',''),origin='외부 검색 후보',
                facility_kind=place['kind'],precision=place['precision'],location_source=place['source'],coordinate_source=place['source'],
                scope='원문 주소·좌표 확인 · 실제 거래·공급 가능성 미확인',candidate_name=candidate['name'])
            continue
        names=[candidate['name']]+candidate.get('aliases',[])
        if candidate['name']=='Shin-Etsu 그룹 · SEH':names.append('Shin-Etsu Chemical')
        for key,entity in network['entities'].items():
            if entity.get('kind')!='company':continue
            if any(n.casefold()==entity['name'].casefold() or n.casefold() in [a.casefold() for a in entity.get('aliases',[])] for n in names):
                add(key,' / '.join(candidate['products'])+' · 등록 제품 비교','등록 후보')
                if key in rows:rows[key].update(role='alternative',role_label='대체 검토 후보 · '+rows[key]['facility_kind'],origin='등록 후보',reason=' / '.join(candidate['products']),candidate_name=candidate['name'])
    from news.facility_scope import facility_scope
    facilities=facility_scope(question,facility_id)
    selected=facilities.get('selected')
    if selected:
        rows.pop(selected['group'],None)
        source=next(iter(facilities['sources'].values()),{})
        rows[selected['id']]=dict(id=selected['id'],name=selected['name'],lat=selected['lat'],lon=selected['lon'],
            site=selected['city'],score=None,role='supplier',role_label='선택 공장 지역 · 개략점',
            reason='질문 또는 공장 선택으로 지정한 시설 · 피해 사실 미확정',origin='선택 공장',
            facility_kind='공장 지역',precision=selected['coordinate_precision'],location_source=source.get('url'),
            coordinate_source=None,scope=selected['note'])
    # Fixed, registered comparison pairs. These arcs connect comparison points,
    # not vessel tracks or inferred customer/supplier relationships.
    if any(word in question for word in ('우회','봉쇄','통항','막히','통과하지')):
        for original,alternative in [('logistics:malacca','logistics:lombok'),('logistics:suez','logistics:cape')]:
            point=network['logistics'].get(original,{})
            if not any(mentions(question,n) for n in [point.get('name','')]+point.get('aliases',[])):continue
            if alternative not in network['logistics']:continue
            add(original,'우회 검토의 기존 경유 지점','질문 언급')
            add(alternative,'등록된 우회 비교 지점 · 운항 적합성 미확인','등록 우회 후보')
            rows[original].update(role='blocked_port',role_label='① 기존 경유 · 검토 대상',impact='origin')
            rows[alternative].update(role='detour_port',role_label='② 우회 검토 후보')
            routes.append(dict(start=original,end=alternative,kind='detour',material='우회 지점 비교선 · 실제 운항 경로 아님'))
            comparisons.append(dict(original=point['name'],alternative=network['logistics'][alternative]['name'],
                source=network['logistics'][alternative].get('source')))
    return dict(markers=list(rows.values()),routes=routes,comparisons=comparisons,review=True,applied=False,response=False,
                context=sha256((question+'\n'+answer+'\n'+facility_id).encode()).hexdigest()[:20],
                status_label='질문·답변의 등록 위치 · 피해 판정 아님',
                title='질문·답변과 일치하는 등록 위치',process=' · '.join(processes),loss=0,
                materials=materials,processes=processes)


def focus_candidate(data,name):
    data=dict(data)
    data.pop('camera_focus',None)
    data.pop('selected',None)
    data['camera_context']=data['context']+':'+(name or 'overview')
    marker=next((m for m in data['markers'] if name and m.get('candidate_name')==name),None)
    if marker:
        data['camera_focus']=dict(lat=marker['lat'],lon=marker['lon'],distance=2.4)
        data['selected']=dict(kind='marker',id=marker['id'],context=data['context'])
        data['status_label']='선택 후보 · '+name
    return data,marker


def render_research_map(network,question,answer='',candidates=None,selected_candidate=None,facility_id=''):
    import streamlit as st
    data,focused=focus_candidate(map_matches(network,question,answer,candidates,facility_id),selected_candidate)
    if selected_candidate:
        if focused:st.caption('선택 위치: '+focused['site']+' · '+focused['facility_kind'])
        else:st.info(selected_candidate+'의 확인된 위치가 없습니다. 전체 지도를 유지하며 조건 비교는 오른쪽에서 확인할 수 있습니다.')
    if data['comparisons']:
        for comparison in data['comparisons']:
            a,b,c=st.columns([1,.15,1])
            with a:
                with st.container(border=True):
                    st.markdown('**:red[① 기존 경유]**')
                    st.write(comparison['original'])
            with b:st.markdown('### →')
            with c:
                with st.container(border=True):
                    st.markdown('**:blue[② 우회 검토]**')
                    st.write(comparison['alternative'])
        st.caption('빨강: 질문의 경유 지점　·　파랑: 등록 우회 후보　·　점선: 두 지점의 비교 연결')
    else:st.caption('질문·답변의 등록 위치 · 대체 후보는 제품 근거로 구분합니다.')
    if data['materials']:st.write('소재: '+' · '.join(data['materials']))
    if data['processes']:st.write('등록 소재의 관련 공정: '+' · '.join(data['processes']))
    if not data['markers']:
        st.info('확인된 위치가 없습니다. 후보의 근거·조건 비교는 오른쪽에서 확인하세요.')
        return
    from .night_globe import component
    component()(data=data,key='research_globe',width='stretch',height=440)
    st.caption('우회 비교선은 실제 항적이 아닙니다. 운항 경로는 출발·도착·선박·화물 조건 확인이 필요합니다.' if data['comparisons'] else '기업은 등록 위치 또는 출처에서 주소·좌표를 확인한 지점에 표시합니다. 실제 피해·대체 승인은 별도 확인 대상입니다.')
    with st.expander('지도 표시 이유 · 위치 목록'):
        for marker in data['markers']:
            st.markdown('**'+marker['name']+' · '+marker['site']+'**')
            st.caption(marker['precision']+' · '+marker['scope'])
            if marker['location_source']:st.link_button('사업장 주소 근거',marker['location_source'])
            if marker['coordinate_source']:st.link_button('좌표 근거',marker['coordinate_source'])
        for comparison in data['comparisons']:
            if comparison['source']:st.link_button('등록 우회 지점의 참고 자료',comparison['source'])
        st.dataframe([{'기업·지점':m['name'],'지도 위치':m['site'],'연결 이유':m['reason'],'언급 위치':m['origin']} for m in data['markers']],hide_index=True,width='stretch')
