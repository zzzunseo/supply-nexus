"""Small case loader, explicit evidence, and read-only response comparison."""
import streamlit as st
from core_cases import core_cases,case_for_target,response_comparison


def prepare_core_case():
    key=st.session_state.get('rr_core_preset')
    case=next((c for c in core_cases() if c['id']==key),None)
    if case:
        st.session_state.update(rr_manual_category='소재',rr_manual_target=case['target'],
            rr_manual_country=None,rr_manual_case='공급 중단',rr_manual_days=case['days'],rr_manual_percent=100.,rr_all_targets=False)


def change_target_range():
    st.session_state.rr_show_reference=st.session_state.get('rr_all_targets',False)


def render_core_controls():
    with st.expander('핵심 사례 · 선택 범위',expanded=False):
        cases=core_cases(); labels={c['id']:c['name'] for c in cases}
        st.selectbox('시연 조건 불러오기',[None,*labels],key='rr_core_preset',
                     format_func=lambda key:labels.get(key,'직접 대상 선택'),on_change=prepare_core_case,
                     placeholder='웨이퍼 / 포토레지스트 사례')
        st.caption('60일 공급 중단 조건을 채웁니다. 적용 버튼을 눌러야 계산에 반영됩니다.')
        st.toggle('전체 등록 대상 보기',key='rr_all_targets',value=False,on_change=change_target_range)


def close_comparison(): st.session_state.rr_core_comparison_open=False


@st.dialog('핵심 소재 · 재고와 대체 공급 비교',width='large',on_dismiss=close_comparison)
def comparison_dialog(network,result):
    target=st.session_state.get('rr_core_compare_target')
    case=case_for_target(network,target)
    if not case:
        st.info('웨이퍼 또는 포토레지스트 조건을 먼저 적용하세요.')
        return
    st.write(case['name']+' · 관측 '+str(st.session_state.rr_days)+'일')
    st.caption('현재 활성 이슈 전체를 유지하고 재고·대체 공급 옵션만 바꾼 계산입니다. 현재 설정은 바꾸지 않습니다.')
    rows=response_comparison(network,st.session_state.rr_events,st.session_state.rr_days,result['scopes'],case)
    st.session_state.rr_core_comparison_rows=rows
    st.dataframe(rows,hide_index=True,width='stretch',height=260)
    st.caption('동일한 말일 점수라도 첫 부족일은 달라질 수 있습니다.  \n개선이 없으면 현재 가정에서 효과가 없는 것입니다.  \n실제 생산 회복률·인증된 대체 발주가 아닙니다.')
    st.write('근거: '+case['evidence'])
    st.caption(case['limits'])
    st.markdown('[공급관계 자료]('+case['relationship_source']+') · [제품·용도 자료]('+case['product_source']+')')


def render_core_result(network):
    events=st.session_state.rr_events
    target=next((key for event in reversed(events) if event['kind']=='supply' for key in event['targets']
                 if case_for_target(network,key)),None)
    if not target: return
    case=case_for_target(network,target)
    def open_comparison():
        st.session_state.rr_core_compare_target=target
        st.session_state.rr_core_comparison_open=True
        st.session_state.rr_relationship_open=False
    st.button('재고·대체 공급 비교',key='rr_core_compare',on_click=open_comparison,width='stretch')
    with st.expander('핵심 사례 근거 · 확인 범위',expanded=False):
        st.write(case['evidence']); st.caption(case['limits'])
        st.markdown('[공급관계 자료]('+case['relationship_source']+') · [제품·용도 자료]('+case['product_source']+')')
