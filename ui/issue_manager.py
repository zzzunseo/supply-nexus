"""Active issue list and per-issue duration/delete controls."""
import hashlib
import html
import json
import streamlit as st
from .issues import change_issue_duration, delete_issue


def close_manager():
    st.session_state.rr_issue_manager_open = False


@st.dialog('활성 이슈 관리', width='large', on_dismiss=close_manager)
def manage_issues():
    st.caption('이슈는 모두 1일째 시작합니다. 기간 종료 다음 날부터 해당 이슈의 직접 감소가 해제됩니다. 관측 기간은 별도입니다.')
    events = st.session_state.rr_events
    if not events:
        st.info('활성 이슈가 없습니다.')
    for index, event in enumerate(events):
        token = hashlib.sha256(json.dumps(event, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
        st.write(f"{index + 1}. {event['text']}")
        days_col, save_col, delete_col = st.columns([2, 1, 1])
        with days_col:
            days = st.number_input('이슈 지속 기간 · 일', 1, 365, value=int(event['days']), key=f'issue_days_{index}_{token}')
        with save_col:
            if st.button('기간 저장', key=f'issue_save_{index}_{token}'):
                st.session_state.rr_events = change_issue_duration(events, index, days)
                close_manager()
                st.rerun()
        with delete_col:
            if st.button('삭제', key=f'issue_delete_{index}_{token}'):
                st.session_state.rr_events = delete_issue(events, index)
                close_manager()
                st.rerun()


def render_active_issues():
    events = st.session_state.rr_events
    if not events:
        return
    network=st.session_state.rr_network
    for event in events:
        names=' · '.join(network['nodes'].get(key,{}).get('name',key) for key in event['targets'])
        logistics=any(network['nodes'][key]['kind']=='logistics' for key in event['targets'])
        label='관세율' if event['kind']=='tariff' else '통항 감소' if logistics else '공급 감소'
        st.markdown('<div class="rr-condition-card"><div><b>'+html.escape(names)+
                    '</b><span>적용 중</span></div><p>'+f"{event['days']}일 · {label} {event['rate']*100:g}%"+
                    '</p></div>',unsafe_allow_html=True)
    st.button(f'활성 이슈 {len(events)}개 · 기간 수정 / 삭제', width='stretch',
              on_click=lambda: st.session_state.update(rr_issue_manager_open=True))
    if st.session_state.rr_issue_manager_open:
        manage_issues()
