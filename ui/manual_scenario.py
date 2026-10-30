"""A compact no-LLM scenario editor; one explicit apply action."""
import streamlit as st
from simulation.manual_scenario import KINDS,cases_for,build_manual_issue
from simulation.resilience import apply_issue
from resilience_materials import scopes_for_targets
from company_relationships import target_coverage,variant_scopes,VARIANTS


def apply_manual(network):
    state=st.session_state
    try:
        target=state.get('rr_manual_target')
        case=state.get('rr_manual_case')
        parsed=build_manual_issue(network,target,case,int(state.get('rr_manual_days',30)),state.get('rr_manual_percent',50.))
        events=apply_issue(state.rr_events,parsed)
        scopes=state.rr_material_scopes
        variants=variant_scopes(network,target)
        if parsed['action']=='apply':
            chosen=state.get('rr_manual_variant')
            if variants and chosen not in variants: raise ValueError('적용할 제품군을 선택하세요.')
            scopes=sorted(set(scopes)|set(scopes_for_targets(network,[target])))
            if variants:
                if chosen in ('gallium','germanium'): state.rr_special=VARIANTS[chosen]
                else: state.rr_package=VARIANTS[chosen]
        state.rr_events=events; state.rr_material_scopes=scopes
        if parsed['action']=='apply': state.rr_days=parsed['days']
        state.rr_focus=target; state.rr_process='전체'; state.rr_view='이슈'
        state.rr_last_query=parsed['text']; state.rr_reply=parsed['note']; state.rr_error=False
        state.rr_history=(state.rr_history+[{'query':parsed['text'],'reply':parsed['note']}])[-20:]
        state.rr_manual_last=parsed
        for key in ('rr_function_pending','rr_function_context','rr_function_last','rr_chat_apply_error'):
            state.pop(key,None)
    except (ValueError,TypeError) as error:
        state.rr_reply=str(error); state.rr_error=True


def render_manual_scenario(network):
    state=st.session_state
    st.caption('대상과 사건을 선택한 뒤 적용하세요.')
    category=st.radio('대상 구분',list(KINDS),horizontal=True,key='rr_manual_category',label_visibility='collapsed')
    allowed=[key for key,node in network['entities'].items() if node['kind'] in KINDS[category]]
    with st.expander('국가·지역 필터',expanded=False):
        countries=sorted({network['nodes'][key].get('country') for key in allowed if network['nodes'][key].get('country')})
        if state.get('rr_manual_country') not in [None,*countries]: state.rr_manual_country=None
        country=st.selectbox('등록 소속국',[None,*countries],key='rr_manual_country',format_func=lambda key:key or '전체')
        st.caption('대상을 좁히는 필터입니다. 국가 전체 중단으로 적용하지 않습니다.')
    options=sorted((key for key in allowed if country is None or network['nodes'][key].get('country')==country),
                   key=lambda key:(network['nodes'][key]['name'],key))
    if state.get('rr_manual_target') not in options: state.rr_manual_target=None
    target=st.selectbox('적용 대상',[None,*options],key='rr_manual_target',format_func=lambda key:
        '대상 선택 · 이름 검색' if key is None else network['nodes'][key]['name']+' · '+network['nodes'][key].get('country','미확인'))
    if not target:
        st.caption('대상을 선택하면 적용할 사건과 조건이 나타납니다.')
        return
    coverage=target_coverage(network,target)
    st.caption(coverage['status']+' · '+coverage['reason'])
    if network['nodes'][target]['kind']=='company' and not network['entities'][target].get('map_location'):
        st.caption('지도 위치 미확인 · 아래 공급관계에서 연결을 확인할 수 있습니다.')
    if network['nodes'][target]['kind']=='company':
        from .relationship_view import open_relationships
        st.button('이 기업의 공급사·고객사 보기',key='rr_manual_relationships',on_click=open_relationships,args=(target,),width='stretch')
    options=list(cases_for(network,target))
    if state.get('rr_manual_case') not in options: state.rr_manual_case=options[0]
    case=st.selectbox('사건 유형',options,key='rr_manual_case')
    restore=case=='이 대상 이슈 해제'
    full=case in ('공급 중단','완전 봉쇄')
    variants=variant_scopes(network,target) if not restore else []
    if variants:
        if state.get('rr_manual_variant') not in variants: state.rr_manual_variant=variants[0] if len(variants)==1 else None
        st.selectbox('적용 제품군',[None,*variants],key='rr_manual_variant',format_func=lambda key:VARIANTS[key] if key else '제품군 선택')
    if restore:
        st.caption('선택 대상의 공급·관세 이슈만 해제합니다.')
    else:
        cols=st.columns(2)
        with cols[0]: st.number_input('지속 기간 · 일',1,365,value=30,key='rr_manual_days')
        with cols[1]:
            if full: st.metric('통항 감소' if network['nodes'][target]['kind']=='logistics' else '공급 감소','100%')
            else:
                maximum=500. if case=='관세 부과' else 99.9 if case=='부분 통항 제한' else 100.
                if state.get('rr_manual_percent',50.)>maximum: state.rr_manual_percent=maximum
                st.number_input('관세율 · %' if case=='관세 부과' else '감소율 · %',.1,maximum,value=50.,step=5.,key='rr_manual_percent')
        if case=='관세 부과': st.caption('비용 이슈로 반영 · 소재 충족도는 낮추지 않습니다.')
        elif case=='화재·사고에 따른 공급 차질': st.caption('사건의 공급 영향은 직접 지정한 감소율로 가정합니다.')
        node=network['nodes'][target]
        if node.get('score_excluded') or not node.get('calculation_included',True):
            st.caption('장비·참고 품목은 소재 점수 계산에서 제외됩니다.')
        elif node['kind']=='company':
            st.caption('기업의 등록 공급 경로에 적용합니다. 해당 기업의 생산량 감소율을 뜻하지 않습니다.')
    st.button('선택 조건 적용' if not restore else '선택 대상 이슈 해제',key='rr_manual_apply',
              on_click=apply_manual,args=(network,),type='primary',width='stretch',disabled=bool(variants) and state.get('rr_manual_variant') not in variants)
