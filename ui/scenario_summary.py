"""Compact summaries of the current engine state, separate from extraction drafts."""
import html
import streamlit as st


def render_process_impact(network, result):
    if not st.session_state.rr_events:
        return
    groups=[]
    for company,view in result['process_views'].items():
        if company in ('worst','mean'):
            continue
        affected=[(p,v) for p,v in view['scores'].items() if v is not None and v<100-1e-7]
        if affected:
            groups.append((network['nodes'].get(company,{}).get('name',company),affected))
    st.markdown('<div class="rr-section-label">소재 부족이 계산된 기업·공정</div>',unsafe_allow_html=True)
    if not groups:
        st.caption('현재 등록 범위에서는 소재 부족이 계산되지 않았습니다. 장비·관세와 미산정 공정은 별도입니다.')
        return
    for company,affected in groups:
        names=' · '.join(p for p,_ in affected)
        lowest=min(v for _,v in affected)
        st.markdown('<div class="rr-impact-card"><b>'+html.escape(company)+'</b><p>'+html.escape(names)+
                    f'</p><span>최저 소재 충족도 {lowest:.0f}/100</span></div>',unsafe_allow_html=True)
    st.caption('현재 전체 시나리오의 계산 결과 · 실제 피해·생산 감소율 아님')
