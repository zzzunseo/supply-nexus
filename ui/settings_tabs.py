"""Individual settings-tab views; widget labels, keys, order, and behavior are preserved."""
import json
import streamlit as st
from resilience_locations import LOCATION_TYPES, location_rows
from evidence_review import review_summary
from resilience_materials import material_rows
from resilience_logistics import logistics_rows
from simulation.resilience import calculate_supply_shock
from .state import scopes_from_state
from .logistics import render_logistics_settings


def source_rows(network):
    rows = []
    for e in network['backbone']:
        decision = dict(network['relationship_decisions'][e['id']])
        if next(i for i in network['original']['items'] if i['id']==e['item_id'])['category']=='equipment':
            decision.update(included=False, reason='장비 공급은 소재 점수 제외 · 해설 대상')
        rows.append(dict(계산포함=decision['included'], 계산판정=decision['reason'], ID=e['id'], 소재=e['item'], 공급사=network['nodes'][e['from']]['name'], 수요기업=network['nodes'][e['to']]['name'], 공정=' / '.join(e['processes']), 관계=e.get('relationship_kind'), 관계근거=e.get('relationship_status'), 품목근거=e.get('item_status'), 시점=e.get('temporal_status'), 실제비중=e.get('share_pct'), 출처=e.get('relationship_source'), 소재출처=e.get('item_source'), 비고=e.get('evidence_note')))
    return rows


def render_assumptions_tab(network):
    st.caption('추가 연결·조달 비중·재고·예약 대체량은 가정입니다. 점수는 마지막 날의 직접 소재 충족도입니다.')
    st.selectbox('반도체 제품군', ['실리콘 기준', '갈륨 화합물 확장', '게르마늄계 확장'], key='rr_special')
    st.selectbox('추가 패키지 소재', ['기본 패키지', '금 본딩 와이어', 'Pd 코팅 와이어', '은 소결 접합', '주석 솔더'], key='rr_package')
    st.caption('갈륨·게르마늄은 선택 시에만 적용됩니다. 패키지는 선택한 레시피 1개만 추가합니다. 세륨은 일부 CMP, 네온은 DUV 경로입니다.')
    ids = [k for k, n in network['entities'].items() if n['kind'] in ('material', 'product') and not n.get('score_excluded',False)]
    selected = st.selectbox('가정 편집 대상', ids, format_func=lambda k: network['nodes'][k]['name'], key='rr_edit_node')
    overrides = st.session_state.setdefault('rr_overrides', {})
    current = overrides.get(selected, network['nodes'][selected])
    with st.form('rr_assumption_form'):
        inv = st.number_input('재고(일 · 명목 수요 단위)', 0.0, 365.0, float(current['inventory_days']), step=1.0)
        cap = st.slider('대체 공급 방어 한도', 0.0, 1.0, float(current['alt_capacity']), 0.05, disabled=not network['nodes'][selected]['alt_vendor'])
        qualification = st.number_input('대체 인증 대기일 · 가정', 0, 365, int(current.get('alt_qualification_days', 0)), disabled=not network['nodes'][selected]['alt_vendor'])
        ramp = st.number_input('인증 후 공급 확대 기간 · 일 · 가정', 0, 365, int(current.get('alt_ramp_days', 0)), disabled=not network['nodes'][selected]['alt_vendor'])
        st.caption('대체 공급사가 없는 노드는 한도가 0입니다. 예약풀은 여러 요청이 공유하며 중복 배정하지 않습니다.')
        if st.form_submit_button('가정 저장 후 반영', width='stretch'):
            overrides[selected] = dict(inventory_days=inv, alt_capacity=cap, alt_qualification_days=qualification, alt_ramp_days=ramp)
            st.rerun()
    if st.button('가정 기본값 복원', width='stretch'):
        st.session_state.rr_overrides = {}
        st.rerun()


def render_backbone_tab(network):
    included = sum(row['계산포함'] for row in source_rows(network))
    st.caption(f'원본 44개 보존 · 계산 {included}개 / 참고 {44 - included}개. 공급 관계와 허용 시점의 출처가 있는 관계만 계산하며, 연구·서비스·미확인·인증·과거·예정 관계는 참고 표시만 합니다. 포함도 개별 품목의 현행 계약·배분율 확인을 뜻하지 않습니다.')
    rows = source_rows(network)
    page = st.number_input('페이지(페이지당 8개)', 1, 6, step=1, key='rr_records_page')
    st.dataframe(rows[(page - 1) * 8:page * 8], height=315, hide_index=True, column_config={'출처': st.column_config.LinkColumn('기업 관계 원문'), '소재출처': st.column_config.LinkColumn('품목 원문')})
    st.download_button('원본 44개 연결 JSON 저장', json.dumps(rows, ensure_ascii=False, indent=2).encode('utf-8'), 'backbone-44.json', 'application/json')
    gaps = [dict(기업=network['nodes'][gap['company']]['name'], 공정=gap['process'], 누락품목=gap['item_id'], 제외된관계=' / '.join(gap['excluded_edges'])) for gap in network['coverage_gaps']]
    st.caption('모델이 필수로 설정한 품목 중 공급 근거를 걸러낸 뒤 계산 경로가 없는 항목입니다.  \n해당 소재를 직접 사용하는 공정만 범위 불완전(*)으로 표시하며 하위 공정으로 전파하지 않습니다.  \n숫자는 남은 부분 모델의 조건부 값입니다.')
    st.dataframe(gaps, hide_index=True)


def render_upstream_tab(network):
    st.caption('원산지→가공 기업→고객 추가 경로는 가정입니다. 출처는 제품·산업 용도·일부 거점을 뒷받침합니다.')
    material = st.selectbox('추가 소재', list(network['upstream_products']), format_func=lambda k: network['nodes'][network['upstream_products'][k]]['name'])
    node = network['nodes'][network['upstream_products'][material]]
    raw = network['nodes']['raw:' + material]
    st.write(f"{raw['name']} → {network['nodes'][node['company_id']]['name']} → {node['name']}")
    st.write(node['source_note'])
    if node['source']:
        st.markdown(f"[제품·용도 출처]({node['source']})")
    if raw['source']:
        st.markdown(f"[원료·지역 참고 자료]({raw['source']})")
    st.write(f"재고 {node['inventory_days']:g}일 / 우회 한도 {node['alt_capacity'] * 100:g}% — 가정값")
    st.caption('대표 좌표와 실제 시설 위치는 구분합니다. 미확인 계약·물량·가용 여력은 출처 있음으로 승격하지 않습니다.')


def render_locations_tab(network):
    st.caption('주소와 지도의 사업장/건물 위치를 대조했습니다. 본사는 생산 공장과 구분하며, 소재 원산지 국가를 임의 광산 좌표로 바꾸지 않습니다.')
    rows = location_rows(network)
    st.dataframe(rows, height=230, hide_index=True, column_config={'주소근거': st.column_config.LinkColumn('주소·시설 원문'), '좌표근거': st.column_config.LinkColumn('좌표 지도')})
    st.download_button('전체 위치 점검표 저장', json.dumps(rows, ensure_ascii=False, indent=2).encode('utf-8'), 'location-review.json', 'application/json')
    ids = list(network['locations'])
    selected_location = st.selectbox('위치 원문 확인', ids, format_func=lambda k: network['locations'][k]['name'])
    place = network['locations'][selected_location]
    st.write(place['name'] + ' · ' + LOCATION_TYPES[place['location_type']])
    st.write(place['address'])
    st.write(f"위도 {place['lat']:.6f} / 경도 {place['lon']:.6f}")
    st.caption(place['coordinate_precision'] + ' · ' + place['role_note'])
    st.caption('좌표 재점검: ' + place.get('coordinate_audit', {}).get('summary', '재검토 필요'))
    st.markdown(f"[주소·시설 역할 원문]({place['source']}) · [좌표 지도]({place['coordinate_source']})")
    missing = [n['name'] for n in network['entities'].values() if n['kind'] == 'company' and (not n.get('map_location_id'))]
    st.caption('좌표 확인 전 지도에서 제외한 기업/거점: ' + ', '.join(missing))
    st.caption('이 항목과 국가 수준 원료는 계산·소재 목록에 남아 있습니다.  \n시설별 공급 비중은 미확인이므로 지도상 거점 피해를 기업 전체 중단으로 자동 환산하지 않습니다.')


def render_materials_tab(network):
    specs = network['extended_materials']
    rows = material_rows(network)
    counts = review_summary(network)['extended_product_basis_counts']
    st.caption(f'소재 {len(specs)}종 · 후보 {len(rows)}개 · 제품 종류 근거 {counts.get("documented", 0)}개. 현재 고객별 품목 계약·필수 사용·실제 비중은 미확인입니다.')
    st.multiselect('계산에 포함할 확장 소재 레시피', [s['scope'] for s in specs.values()], format_func=lambda scope: specs[scope.split(':', 1)[1]]['name'], key='rr_material_scopes')
    st.caption('초기에는 기존 레시피를 유지합니다.  \n이슈에서 소재·공급사를 지정하면 관련 확장 레시피가 자동 활성화됩니다.  \n모든 소재가 모든 칩에 필요한 것은 아닙니다.')
    group = st.selectbox('소재 분류', ['전체'] + sorted({s['group'] for s in specs.values()}))
    query = st.text_input('소재·공급사 검색', key='rr_material_search')
    filtered = [r for r in rows if (group == '전체' or r['분류'] == group) and (not query or query.lower() in ' '.join((str(v) for v in r.values())).lower())]
    st.dataframe(filtered, height=290, hide_index=True, column_config={'제품근거': st.column_config.LinkColumn('제품 원문')})
    st.download_button('확장 소재·연결·우회 목록 저장', json.dumps(rows, ensure_ascii=False, indent=2).encode('utf-8'), 'extended-materials.json', 'application/json')
    key = st.selectbox('소재별 우회 확인', list(specs), format_func=lambda k: specs[k]['name'])
    spec = specs[key]
    st.write('공급 후보: ' + ' / '.join((network['nodes'][s['company']]['name'] for s in spec['suppliers'])))
    quote = lambda s: json.dumps(s, ensure_ascii=False)
    dot = ['digraph supply { rankdir=LR; bgcolor="transparent";', 'node [shape=box, style="rounded,filled", fillcolor="#142C40", fontcolor="#DCEAF8", color="#31576D"];', 'edge [color="#4FE4DB", fontcolor="#A5CEDD"];', 'material [label=' + quote(spec['name']) + '];']
    for index, supplier in enumerate(spec['suppliers']):
        vendor = network['nodes'][supplier['company']]
        dot += [f'vendor{index} [label=' + quote(vendor['name']) + '];', f'vendor{index} -> material [style=dashed,label="' + ('공급·추가예약 후보·가정' if spec['reserve_node'] and index == len(spec['suppliers']) - 1 else '공급 후보·가정') + '"];']
    for index, process in enumerate(spec['processes']):
        dot += [f'process{index} [label=' + quote(process) + '];', f'material -> process{index} [label="선택 레시피"];']
    dot.append('}')
    st.graphviz_chart('\n'.join(dot))
    st.caption('관계도는 비지리적 모델입니다. 고객 경로는 기존 삼성·TSMC 또는 ASE·Amkor 공정에 연결되며 실제 계약은 미확인입니다.')
    if spec['reserve_node']:
        provider = network['nodes'][spec['reserve_node']]['company_id']
        st.write(f"추가 예약 후보: {network['nodes'][provider]['name']} · 인증 {spec['qualification_days']}일 + 확대 {spec['ramp_days']}일 · 추가 여력 40% 가정")
        st.caption('상류 원료가 같으면 우회도 함께 타격받습니다.  \n예약량은 같은 품목의 요청들이 공유하고 중복 계산하지 않습니다.  \n공급사 전환만으로 공통 원료 부족이 해결되지는 않습니다.')
    else:
        st.caption('검토한 자료에서 별도 대체 후보를 등록하지 못했습니다. 우회율은 0이며 임의 공급사를 만들지 않습니다.')
    st.caption(spec['recipe_note'])
    st.caption('사건 적용은 8대 공정 탭의 ‘분석 조건 · 수동 사건 적용’에서 소재와 감소율을 선택하세요.')


def render_logistics_tab(network):
    st.caption('가상 물류 시나리오.  \n유럽–동아시아는 수에즈·말라카, 대만 수출입은 가오슝항을 경유한다고 가정합니다.  \n원래 경로는 붉은 점선, 우회 발송·도착 경로는 파란 선입니다.')
    render_logistics_settings(network)


def render_comparison_tab(network):
    st.caption('같은 이슈·기간·소재·가정에서 재고와 추가 예약 우회만 켜고 끈 비교입니다.  \n점수는 마지막 날의 부분 모델 공급 충족도이며 실제 생산량이 아닙니다.  \n누락 제약은 원본 경로 탭에서 확인합니다.')
    events = [dict(e) for e in st.session_state.rr_events]
    comparisons = []
    for inventory, bypass in ((True, True), (True, False), (False, True), (False, False)):
        r = calculate_supply_shock(network, events, st.session_state.rr_days, inventory, bypass, scopes_from_state())
        comparisons.append(dict(계산범위='부분 모델' if r['incomplete_processes'] else '등록 모델', 누락제약공정=' / '.join(r['incomplete_processes']), 재고='켬' if inventory else '끔', 추가예약우회='켬' if bypass else '끔', 최악기업병목=r['overall'], 기업평균병목=r['process_views']['mean']['overall'], **r['scores'], **{'평균·' + p: value for p, value in r['process_views']['mean']['scores'].items()}, 최초부족일=min(r['first_hit'].values(), default=None)))
    st.dataframe(comparisons, hide_index=True)
    st.caption('필수 투입재는 최솟값, 병렬 공급사는 가중합입니다.  \n최악 기업은 공정별 등록 기업 최솟값, 기업 평균은 해당 공정의 동일 기업 비중 단순평균입니다.  \n각각의 병목 지수는 8개 산정 가능한 공정 소재 충족도 중 최솟값입니다.  \n산업 생산량/점유율 평균이 아닙니다.  \n최저값은 생산량이 아닙니다.  \n장비·관세·공정 간 생산 연쇄 영향은 점수에서 제외합니다.')
    st.caption('우회 끄기는 추가 예약 공급만 끕니다.  \n원래 등록된 정상 병렬 공급사까지 제거하지 않습니다.  \n기존 경로의 우회 인증일 기본값은 0일인 경우가 있어 즉시 방어될 수 있으며 제품군·가정 탭에서 바꿀 수 있습니다.')
    st.caption('이 입력창은 등록된 소재·기업·물류명의 규칙 해석기입니다.  \n사건별 감소율·재고·대체 여력은 실측 추정치가 아니며, 서로 다른 감소율/기간의 이슈는 나눠 입력해야 합니다.  \n관측 기간은 마지막 관측일만 변경합니다.  \n각 이슈의 지속 기간은 활성 이슈 관리에서 별도로 수정합니다.  \n기간 미기재 시 이슈는 30일로 가정합니다.')
    st.download_button('현재 계산 비교 저장', json.dumps(comparisons, ensure_ascii=False, indent=2).encode('utf-8'), 'simulation-comparison.json', 'application/json')
