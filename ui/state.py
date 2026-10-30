"""Session state and validated issue submission with independent durations."""
from copy import deepcopy
import streamlit as st
from resilience_materials import scopes_for_targets
from simulation.resilience import interpret_issue, apply_issue
from simulation.schema import validate_parsed


def initialize():
    defaults = dict(
        rr_events=[],
        rr_issue_manager_open=False,
        rr_days=30,
        rr_inventory=True,
        rr_bypass=True,
        rr_process='전체',
        rr_flow_process='포토',
        rr_score_view='worst',
        rr_level='소재 연쇄',
        rr_view='아시아',
        rr_focus=None,
        rr_last_chart_selection=(),
        rr_special='실리콘 기준',
        rr_package='주석 솔더',
        rr_history=[],
        rr_reply='지역·소재·기업과 중단 기간을 입력하세요. 예시는 단일 이슈를 적용합니다.',
        rr_issue_text='',
        rr_last_query='입력 대기',
        rr_error=False,
    )
    defaults['rr_material_scopes'] = []
    for k, v in defaults.items():
        st.session_state.setdefault(k, deepcopy(v))


def reset():
    for key in ('rr_function_pending','rr_function_last','rr_function_context','rr_chat_apply_error','rr_manual_last'):
        st.session_state.pop(key,None)
    st.session_state.update(
        rr_events=[],
        rr_issue_manager_open=False,
        rr_focus=None,
        rr_reply='모든 이슈를 해제했습니다.',
        rr_last_query='전체 정상 복구',
        rr_error=False,
    )


def submit(network, example=None):
    state = st.session_state
    text = example or state.rr_issue_text
    try:
        parsed = validate_parsed(interpret_issue(text, network, default_days=30), network['nodes'])
        if parsed.get('action') == 'apply':
            reference_only = [k for k in parsed['targets'] if not network['nodes'][k].get('calculation_included', True)]
            if reference_only:
                parsed['note'] += f' 참고 관계에만 연결된 {len(reference_only)}개 품목은 공정 공급 계산에서 제외됩니다.'
            if any((network['nodes'][k]['kind'] == 'logistics' for k in parsed['targets'])):
                state.rr_view = '이슈'
            extra_scopes = scopes_for_targets(network, parsed['targets'])
            state.rr_material_scopes = sorted(set(state.rr_material_scopes) | set(extra_scopes))
            if extra_scopes:
                parsed['note'] += f' 확장 소재 {len(extra_scopes)}종의 선택 레시피를 활성화했습니다. 기업 소속국 기준이며 실제 생산국은 미확인입니다.'
            scopes = {network['nodes'][k]['scope'] for k in parsed['targets']}
            specialty = scopes & {'gallium', 'germanium'}
            packages = scopes & {'package_gold', 'package_palladium', 'package_silver', 'package_tin'}
            if len(specialty) > 1 or len(packages) > 1:
                parsed['note'] += ' 여러 제품군이 포함되어 현재 선택 레시피만 계산합니다.'
            if len(specialty) == 1:
                state.rr_special = {'gallium': '갈륨 화합물 확장', 'germanium': '게르마늄계 확장'}[next(iter(specialty))]
                parsed['note'] += ' 해당 특수 제품군을 선택했습니다.'
            if len(packages) == 1:
                state.rr_package = {'package_gold': '금 본딩 와이어', 'package_palladium': 'Pd 코팅 와이어', 'package_silver': '은 소결 접합', 'package_tin': '주석 솔더'}[next(iter(packages))]
                parsed['note'] += ' 해당 패키지 레시피를 선택했습니다.'
        state.rr_events = apply_issue([] if example else state.rr_events, parsed)
        state.rr_reply = parsed['note']
        state.rr_error = False
        state.rr_last_query = text
        state.rr_history = (state.rr_history + [dict(query=text, reply=parsed['note'])])[-20:]
    except ValueError as error:
        state.rr_reply = str(error)
        state.rr_error = True
        state.rr_last_query = text


def scopes_from_state():
    special = {'실리콘 기준': None, '갈륨 화합물 확장': 'gallium', '게르마늄계 확장': 'germanium'}[st.session_state.rr_special]
    package = {'기본 패키지': None, '금 본딩 와이어': 'package_gold', 'Pd 코팅 와이어': 'package_palladium', '은 소결 접합': 'package_silver', '주석 솔더': 'package_tin'}[st.session_state.rr_package]
    return [s for s in (special, package) if s] + st.session_state.rr_material_scopes
