"""Editable, session-scoped port detours and portable settings/results."""
from copy import deepcopy
import json
import streamlit as st
from simulation.logistics import validate_route_settings
from resilience_logistics import logistics_rows
from simulation.quick_detours import save_profile


def apply_saved_settings(network, detours, routes):
    # Validate a complete candidate before changing anything, including on import.
    candidate = dict(network, port_detours={**network['port_detours'], **deepcopy(detours)},
                     route_settings={**network['route_settings'], **deepcopy(routes)})
    validate_route_settings(candidate)
    network['port_detours'] = candidate['port_detours']
    network['route_settings'] = candidate['route_settings']
    for key, value in network['route_settings'].items():
        network['nodes'][key]['inventory_days'] = value['inventory_days']


def settings_payload(network):
    return dict(schema_version=1, port_detours=network['port_detours'],
                route_settings=network['route_settings'])


def render_logistics_settings(network):
    st.caption('항만 우회는 같은 공급사의 운송 경로 변경입니다.  \n대체 벤더 우회 스위치와 별도로 적용됩니다.  \n모두 시나리오 가정이며 실제 예약·운송 적합성은 미확인입니다.')
    cp = st.selectbox('우회를 설정할 항만·해협', list(network['port_detours']),
                      format_func=lambda k: network['nodes'][k]['name'], key='rr_detour_cp')
    setting = network['port_detours'][cp]
    alternate = ' → '.join(network['nodes'][c]['name'] for c in setting['via'])
    st.write(network['nodes'][cp]['name'] + ' → ' + alternate)
    st.caption('메인 화면 스위치는 저장된 보통값을 사용합니다.  \n아래 값을 평소 사용할 값으로 남기려면 ‘이 값을 보통값으로 저장’을 누르세요.  \n실측 평균이 아닌 시뮬레이션 가정입니다.')
    with st.form('rr_port_detour_' + cp):
        enabled = st.checkbox('이 항만·해협의 우회 사용', value=setting['enabled'])
        fraction = st.slider('경로별 해상 물량의 우회 한도 · %', 0, 100, round(setting['max_fraction']*100))
        delay = st.number_input('우회 추가 운송일 · 가정', 0, 365, int(setting['extra_days']))
        capacity = st.number_input('공유 우회 처리량 · 경로 수요 단위/일', 0., 1000., float(setting['capacity_units']), step=.1)
        cost = st.number_input('우회 운임 증가 · % · 가정', 0., 1000., float(setting['cost_rate']*100), step=5.)
        st.caption('경로 하나의 명목 하루 수요=1입니다.  \n공유 처리량은 활성 경로들이 나눠 쓰는 동일 비중 가정이며 톤·TEU가 아닙니다.  \n여러 병목을 우회하면 추가 일수·운임률은 합산합니다.')
        apply_now = st.form_submit_button('항만 우회 설정 저장', width='stretch')
        save_usual = st.form_submit_button('이 값을 보통값으로 저장', width='stretch')
        if apply_now or save_usual:
            values = dict(setting, enabled=enabled, max_fraction=fraction/100,
                          extra_days=delay, capacity_units=capacity, cost_rate=cost/100)
            try:
                if save_usual:
                    st.session_state.rr_quick_profiles = save_profile(network, cp, values)
                st.session_state.setdefault('rr_port_detours', {})[cp] = values
                st.session_state.rr_settings_open = False
                st.rerun()
            except (ValueError, OSError, TypeError, KeyError) as error:
                st.error('보통값을 저장하지 못했습니다: ' + str(error))
    for c in setting['via']:
        p = network['logistics'][c]
        st.markdown(f"[대체 지점·항로 참고]({p['source']}) · {p['precision']}")
    st.caption('기룽항 전환은 대만 내 육상 운송·터미널 사용을 포함한 가정입니다.  \n롬복·희망봉 자료는 일반 항로 참고이며 반도체 화물의 계약·시간·처리량 근거가 아닙니다.')
    route_id = st.selectbox('운송 비중·도착 재고를 설정할 경로', list(network['logistics_routes']),
        format_func=lambda k: network['nodes'][network['logistics_routes'][k]['source']]['name'] + ' → ' +
            network['nodes'][network['logistics_routes'][k]['target']]['name'], key='rr_route_edit')
    route_setting = network['route_settings'][route_id]
    with st.form('rr_shipping_' + route_id):
        sea = st.slider('해상 운송 비중 · % · 가정', 0, 100, round(route_setting['sea_fraction']*100))
        inventory = st.number_input('도착지 재고 · 일 · 가정', 0., 365., float(route_setting['inventory_days']))
        st.caption('나머지 비중은 이 해상 병목에 영향을 받지 않는 별도 운송 경로 가정입니다. 항공 전환 계약이나 실제 해상·항공 비중을 뜻하지 않습니다.')
        if st.form_submit_button('운송 비중·재고 저장', width='stretch'):
            st.session_state.setdefault('rr_route_settings', {})[route_id] = dict(sea_fraction=sea/100, inventory_days=inventory)
            st.session_state.rr_settings_open = False
            st.rerun()
    st.caption('정상 경로는 기존 모델처럼 즉시 도착 기준입니다.  \n우회 발송분만 추가 일수 뒤 도착하며, 원래 경로가 먼저 회복되면 초과 도착은 별도 기록합니다.  \n전체 운송 리드타임·미납 주문·재고 재충전은 계산하지 않습니다.')
    st.dataframe(logistics_rows(network), height=230, hide_index=True)
    payload = settings_payload(network)
    st.download_button('항만 우회·운송 설정 JSON 저장', json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'),
                       'port-detour-settings.json', 'application/json')
    upload = st.file_uploader('저장한 항만 우회 설정 불러오기', type=['json'], key='rr_route_upload')
    if st.button('설정 파일 적용', disabled=upload is None):
        try:
            if upload.size > 100_000:
                raise ValueError('설정 파일은 100KB 이하여야 합니다.')
            imported = json.loads(upload.getvalue())
            if not isinstance(imported, dict) or set(imported) != {'schema_version', 'port_detours', 'route_settings'} or type(imported['schema_version']) is not int or imported['schema_version'] != 1:
                raise ValueError('지원하지 않는 설정 파일 형식입니다.')
            if not isinstance(imported['port_detours'], dict) or not isinstance(imported['route_settings'], dict):
                raise ValueError('설정 목록 형식이 잘못되었습니다.')
            candidate = deepcopy(network)
            apply_saved_settings(candidate, imported['port_detours'], imported['route_settings'])
            st.session_state.rr_port_detours = candidate['port_detours']
            st.session_state.rr_route_settings = candidate['route_settings']
            st.session_state.rr_settings_open = False
            st.rerun()
        except (ValueError, TypeError, KeyError) as error:
            st.error('설정을 적용하지 않았습니다: ' + str(error))
    if st.button('항만 우회·운송 설정 기본값 복원'):
        st.session_state.rr_port_detours = {}
        st.session_state.rr_route_settings = {}
        st.session_state.rr_settings_open = False
        st.rerun()
    result = st.session_state.get('rr_result', {}).get('logistics')
    if result:
        st.write('현재 관측 결과 · 우회 운송')
        st.dataframe(result_rows(network, result), hide_index=True)
        st.caption(result['note'])
        st.download_button('항만 우회 일별 결과 JSON 저장', json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8'),
                           'port-detour-results.json', 'application/json')
        if st.session_state.rr_events and any(s['enabled'] for s in network['port_detours'].values()):
            from simulation.resilience import calculate_supply_shock
            variant = deepcopy(network)
            for value in variant['port_detours'].values():
                value['enabled'] = False
            off = calculate_supply_shock(variant, st.session_state.rr_events, st.session_state.rr_days,
                st.session_state.rr_inventory, st.session_state.rr_bypass, st.session_state.rr_result['scopes'])
            st.caption('같은 사건·기간·재고·대체 벤더·운송 비중에서 항만 우회만 끈 비교입니다.')
            st.dataframe([dict(조건=label, 최악기업병목=r['overall'],
                기업평균병목=r['process_views']['mean']['overall'],
                기간평균병목=sum(min(row[p] for p in r['scores'] if row[p] is not None) for row in r['timeline']) / r['duration_days'])
                for label, r in [('현재 항만 우회 설정', st.session_state.rr_result), ('항만 우회 끔', off)]], hide_index=True)


def result_rows(network, result):
    return [dict(경로=key, 우회발송=round(r['dispatched'], 4), 우회도착=round(r['arrived'], 4),
                 공급반영=round(r['delivered'], 4), 초과도착=round(r['surplus'], 4), 운송중=round(r['pending'], 4),
                 해상경유가용률=round(r['main_availability'], 4),
                 우회경유=' → '.join(network['nodes'][c]['name'] for c in r['via']))
            for key, r in result['routes'].items()]
