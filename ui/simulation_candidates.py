"""Product-catalog procurement candidates, independent of recovery assumptions."""
from product_comparison import load_comparison_data, compare_record

ITEM_RULES = {
    'photoresist': ('photoresist', {}),
    'polished-wafer': ('silicon-wafer', {'wafer_type': 'PW'}),
    'epi-wafer': ('silicon-wafer', {'wafer_type': 'EPI'}),
    'hf': ('wet-chemical', {'chemical': 'HF'}),
    'bhf': ('wet-chemical', {'chemical': 'BHF'}),
    'cmp-copper': ('cmp-slurry', {'target_film': 'Cu'}),
    'cmp-tungsten': ('cmp-slurry', {'target_film': 'W'}),
    'cmp-barrier': ('cmp-slurry', {'target_film': 'barrier'}),
    'cmp-cobalt': ('cmp-slurry', {'target_film': 'Co'}),
    'ceria-abrasive': ('cmp-abrasive', {'chemical': 'CeO2'}),
    'silane': ('process-gas', {'chemical': 'SiH4'}),
    'sf6': ('process-gas', {'chemical': 'SF6'}),
    'c4f8': ('process-gas', {'chemical': 'C4F8'}),
    'cmp-molybdenum': ('cmp-slurry', {'target_film': 'Mo'}),
    'cmp-oxide': ('cmp-slurry', {'target_film': 'oxide'}),
    'nf3': ('process-gas', {'chemical': 'NF3'}),
    'etch-gas': ('process-gas', {'chemical': 'CF4'}),
}


def catalog_candidates(network, case, product_class=None, catalog=None):
    if case.get('kind') == 'logistics' or case.get('event') == '관세 부과':
        return []
    catalog = catalog if catalog is not None else load_comparison_data()
    node = network['nodes'].get(case['target'], {})
    rows = case.get('connections') or [dict(item=node.get('item_id') or node.get('material_id'), supplier=node.get('company_id'), material=node.get('name',''), recipients=case.get('recipients',[]))]
    blocked = {row['supplier'] for row in rows if row.get('supplier') is not None}
    found = {}
    for row in rows:
        rule = ITEM_RULES.get(row['item'])
        if not rule:
            continue
        family, requirements = rule
        requirements = dict(requirements)
        if family == 'photoresist' and product_class in ('ArF','KrF','i-line','EUV'):
            requirements['exposure'] = product_class
        for record in catalog['records']:
            if record['family'] != family or record['legacy']:
                continue
            if record.get('supplier_network_id') in blocked:
                continue
            result = compare_record(record, requirements)
            if requirements and result['status'] != 'meets_documented':
                continue
            sources = [catalog['sources'][key] for key in sorted({f['source_id'] for f in record['fields'].values()})]
            if not sources:
                continue
            entry = found.setdefault(record['id'], dict(record=record, materials=[], sources=sources, recipients=[], links=[]))
            for recipient in ([row['recipient']] if row.get('recipient') else row.get('recipients', [])):
                if recipient not in entry['recipients']:
                    entry['recipients'].append(recipient)
                link = (recipient, row['material'])
                if link not in entry['links']:
                    entry['links'].append(link)
            if row['material'] not in entry['materials']:
                entry['materials'].append(row['material'])
    return sorted(found.values(), key=lambda entry: (entry['record']['supplier'], entry['record']['name']))


def render_catalog_candidates(network, case, product_class=None):
    import streamlit as st
    if case.get('kind') == 'logistics' or case.get('event') == '관세 부과':
        return
    st.subheader('추가 조달 후보 비교')
    scope_labels = {'scenario':'현재 사건의 등록 품목', 'photoresist':'포토레지스트',
                    'polished-wafer':'폴리시드 웨이퍼', 'epi-wafer':'에피 웨이퍼',
                    'silane':'실란 SiH4', 'sf6':'SF6 가스', 'c4f8':'C4F8 가스', 'cmp-molybdenum':'몰리브덴 CMP', 'cmp-oxide':'산화막 CMP', 'nf3':'NF3 가스', 'etch-gas':'CF4 가스', 'hf':'불산 HF', 'bhf':'완충 불산 BHF',
                    'cmp-copper':'구리 CMP', 'cmp-tungsten':'텅스텐 CMP',
                    'cmp-barrier':'배리어 CMP', 'cmp-cobalt':'코발트 CMP', 'ceria-abrasive':'산화세륨 연마재'}
    scope = st.selectbox('검토할 소재', list(scope_labels), format_func=scope_labels.get, key='simulation_catalog_scope')
    lookup_case = case
    if scope != 'scenario':
        node = network['nodes'].get(case['target'], {})
        blocked = {row['supplier'] for row in case.get('connections', [])} or {node.get('company_id')}
        lookup_case = dict(case, connections=[dict(item=scope,supplier=supplier,material=scope_labels[scope]) for supplier in blocked])
        st.caption('별도 소재 탐색입니다. 선택 소재가 현재 사건의 실제 공급 품목이라는 뜻은 아니며, 현재 중단 기업은 후보에서 제외합니다.')
    is_pr = scope == 'photoresist' or (scope == 'scenario' and any(row.get('item')=='photoresist' for row in case.get('connections', [])))
    if is_pr:
        product_class = st.selectbox('후보 노광 제품군', ['전체 제품군','ArF','KrF','i-line','EUV'], key='simulation_catalog_exposure')
    elif scope not in ('scenario','photoresist'):
        product_class = None
    entries = catalog_candidates(network, lookup_case, product_class)
    if not entries:
        st.caption('현재 제품 자료에서 해당 품목의 추가 후보를 찾지 못했습니다. 대체 기업이 없다는 의미는 아닙니다.')
        return
    suppliers = {e['record']['supplier_network_id'] or e['record']['supplier'] for e in entries}
    st.caption(f'제품 자료 기준 {len(suppliers)}개 공급사 · {len(entries)}개 제품 항목. 지도에 위치가 없는 기업도 포함합니다. 고객 승인·공급 여력·납기는 별도 확인 대상이며 공급 회복 계산에는 자동 반영하지 않습니다.')
    st.dataframe([{'기업': e['record']['supplier'], '제품': e['record']['name'],
                   '품목': ' / '.join(e['materials']),
                   '공개 조건': ' / '.join(str(e['record']['fields'][k]['value']) for k in ('exposure','exposure_mode','wafer_type','chemical','target_film') if k in e['record']['fields']),
                   '판정': '동일 제품군 검토 후보', '공식 자료': e['sources'][0]['url']}
                  for e in entries], hide_index=True, width='stretch',
                 column_config={'공식 자료': st.column_config.LinkColumn('공식 자료', display_text='출처 열기')})
    options = [e['record']['id'] for e in entries]
    labels = {e['record']['id']: e['record']['supplier']+' / '+e['record']['name'] for e in entries}
    key = 'simulation_catalog_record'
    if st.session_state.get(key) not in options:
        st.session_state[key] = options[0]
    chosen = st.selectbox('후보별 근거 확인', options, format_func=labels.get, key=key)
    entry = next(e for e in entries if e['record']['id'] == chosen)
    record = entry['record']
    from .candidate_visuals import render_candidate_visuals
    render_candidate_visuals(network, case, entries, chosen, scope == 'scenario')
    if record.get('notes'):
        st.write(record['notes'])
    for source in entry['sources']:
        st.markdown(f"[{source['title']}]({source['url']})")
        st.caption(source.get('scope','') + ' · 자료 확인일 ' + source['checked_at'])
    st.caption('전환 전 확인: 세부 규격과 공정 적합성 → 고객 품질 승인 → 추가 생산 여력과 납기 → 운송 경로. 제품군 보유만으로 즉시 우회할 수 있다는 뜻은 아닙니다.')
