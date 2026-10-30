"""Sourced candidate locations and schematic material alternatives, without recovery scores."""
import json
from hashlib import sha256
from .research_map import map_matches, focus_candidate


def candidate_visual_data(network, case, entries, chosen, scenario=True):
    selected = next(e for e in entries if e['record']['id'] == chosen)
    candidates = {}
    for entry in entries:
        record = entry['record']
        candidate = candidates.setdefault(record['supplier'], dict(name=record['supplier'], products=[]))
        candidate['products'].append(record['name'])
    data = map_matches(network, '', candidates=list(candidates.values()))
    data['context'] = sha256(json.dumps([case['target'], scenario, [e['record']['id'] for e in entries]],sort_keys=True).encode()).hexdigest()[:20]
    mapped = {m.get('candidate_name'): m['id'] for m in data['markers']}
    missing = [name for name in candidates if name not in mapped]
    ids = {m['id'] for m in data['markers']}
    def add_entity(key, role):
        entity = network['entities'].get(key, {})
        place = entity.get('map_location')
        if not place or key in ids:
            return
        data['markers'].append(dict(id=key,name=entity['name'],lat=place['lat'],lon=place['lon'],
            site=place['name'],role=role,score=None,impact='origin' if role=='supplier' else 'normal',
            location_source=place.get('source')))
        ids.add(key)
    if scenario:
        node = network['nodes'].get(case['target'], {})
        rows = case.get('connections') or [dict(supplier=node.get('company_id'),recipients=case.get('recipients',[]),material=node.get('name',''))]
        for row in rows:
            origin = row['supplier']
            add_entity(origin,'supplier')
            for recipient in ([row['recipient']] if row.get('recipient') else row.get('recipients',[])):
                add_entity(recipient,'recipient')
                if origin in ids and recipient in ids:
                    data['routes'].append(dict(start=origin,end=recipient,kind='primary',status='blocked' if case.get('event')=='공급 중단' or case.get('percent')==100 else 'restricted',material=row['material']))
        # Draw only the selected product's review destinations, not a cartesian product of customers.
        start = mapped.get(selected['record']['supplier'])
        for recipient in selected['recipients']:
            if start and recipient in ids:
                data['routes'].append(dict(start=start,end=recipient,kind='alternative',status='candidate',
                    material=' / '.join(selected['materials'])+' · 조달 검토 연결'))
    data['title']='소재별 대체 기업 비교'
    data['status_label']='대체 조달 검토 · 실제 운송 경로 아님'
    data, focused = focus_candidate(data,selected['record']['supplier'])
    return data, missing, focused


def candidate_diagram(network, entries, chosen, scenario=True):
    selected = next(e for e in entries if e['record']['id']==chosen)
    suppliers = list(dict.fromkeys(e['record']['supplier'] for e in entries if set(e['materials']) & set(selected['materials'])))
    quote = json.dumps
    dot = ['digraph {rankdir=LR; bgcolor="transparent"; node [shape=box,style="rounded,filled",fillcolor="#102a3d",fontcolor="#e0f3ff",color="#426176"]; edge [color="#53d5c8",fontcolor="#bdd0dd",fontsize=11];']
    for i,name in enumerate(suppliers):
        active=name==selected['record']['supplier']
        dot.append(f's{i} [label={quote(name)},color="'+('#53d5c8' if active else '#426176')+'"];')
    dot.append('product [label='+quote(selected['record']['name'])+'];')
    dot.append('material [label='+quote(' / '.join(selected['materials']))+'];')
    index=suppliers.index(selected['record']['supplier'])
    dot.append(f's{index} -> product [label="公開製品" ];'.replace('公開製品','공개 제품'))
    dot.append('product -> material [label="제품군 확인"];')
    for i,name in enumerate(suppliers):
        if i != index:
            dot.append(f's{i} -> material [style=dashed,label="다른 검토 후보"];')
    if scenario:
        for i,key in enumerate(selected['recipients']):
            name=network['entities'].get(key,{}).get('name',key)
            dot.append(f'c{i} [label='+quote(name)+'];')
            dot.append(f'material -> c{i} [style=dashed,label="규격·승인·여력 확인"];')
    dot.append('}')
    return '\n'.join(dot)


def render_candidate_visuals(network, case, entries, chosen, scenario=True):
    import streamlit as st
    selected = next(e for e in entries if e['record']['id']==chosen)
    record=selected['record']
    st.markdown('**소재와 대체 기업 연결도**')
    st.graphviz_chart(candidate_diagram(network,entries,chosen,scenario))
    st.caption('실선: 공개 제품 자료에 따른 연결 · 점선: 대체 조달 검토. 다른 소재를 탐색할 때는 현재 사건의 수요기업에 연결하지 않습니다.')
    fields=record['fields']
    details=' / '.join(str(fields[k]['value']) for k in ('exposure','exposure_mode','wafer_type','chemical','target_film') if k in fields)
    st.markdown('**선택 후보 해설**')
    st.write(f"{record['supplier']}의 {record['name']}은 공개 자료에 {details or record['family']} 제품으로 등록되어 있어 검토 후보로 표시했습니다.")
    checks={'photoresist':'노광 파장, Dry·Immersion, 현상 방식, 톤, 막두께와 고객 레시피',
            'silicon-wafer':'PW·EPI 구분, 직경, 저항률, 결정 방향과 결함 규격',
            'process-gas':'화학종, 순도, 불순물 상한, 용기와 가스 공급 설비',
            'wet-chemical':'HF·BHF 구분, 농도, 금속·입자 불순물과 포장 조건',
            'cmp-slurry':'연마 대상 막, 제거율, 선택비, 결함과 패드 조합',
            'cmp-abrasive':'연마재 입자 크기, 분산 상태와 슬러리 배합 조건'}
    st.write('전환 검토 조건: '+checks[record['family']]+'. 고객 승인, 공급 여력과 납기는 별도 확인합니다.')
    if record['family']=='cmp-abrasive':
        st.caption('연마재는 슬러리의 구성 소재입니다. 완성된 CMP 슬러리를 그대로 대체하는 제품으로 표시하지 않습니다.')
    data, missing, focused = candidate_visual_data(network,case,entries,chosen,scenario)
    st.markdown('**대체 기업 위치와 조달 검토 연결**')
    if data['markers']:
        from .night_globe import component
        component()(data=data,key='simulation_candidate_globe',width='stretch',height=420)
        st.caption('빨강: 사건의 기존 연결 · 청록 점선: 선택 후보의 조달 검토. 기업 지점은 본사 등 등록 위치이며 실제 출하 공장·운송 항적이 아닙니다.')
    if focused:
        st.caption('선택 위치: '+focused['site'])
    else:
        st.caption('선택 기업의 확인된 위치가 없어 지도 표시는 보류했습니다. 위 연결도와 제품 해설은 확인할 수 있습니다.')
    if missing:
        st.caption('위치 자료 추가 필요: '+' · '.join(missing))
    with st.expander('지도 위치 근거'):
        for marker in data['markers']:
            st.write(marker['name']+' · '+marker['site'])
            if marker.get('location_source'):
                st.markdown('[위치 출처]('+marker['location_source']+')')
