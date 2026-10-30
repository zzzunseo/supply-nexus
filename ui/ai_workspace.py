"""One entry point for external research, product comparison and article review."""
import streamlit as st

TASKS={
    '사건·공정 영향 조사':'사건이나 질문을 입력해 외부 자료에서 관련 소재·공정·기업을 조사합니다. 대체 후보와 항로 검토도 여기서 선택할 수 있습니다.',
    '기업·소재 조건 비교':'등록된 제품 자료에서 기업·소재 후보와 공통 조건·차이를 비교합니다. API 없이 후보를 확인할 수 있습니다.',
    '기사 본문 근거 검토':'공장 화재·가동 중단 기사에서 사건과 인용 근거를 추출하고 등록 기업 관계와 대조합니다.'}


def render_ai_workspace(network):
    st.subheader('AI 공급망 분석')
    task=st.radio('어떤 자료로 분석할까요?',list(TASKS),horizontal=True,key='ai_workspace_task')
    if task!='사건·공정 영향 조사':st.caption(TASKS[task])
    if task=='사건·공정 영향 조사':
        from .external_research import render_external_research
        render_external_research(show_header=False,network=network)
    elif task=='기업·소재 조건 비교':
        from .product_comparison import render_product_comparison
        render_product_comparison(enable_ai=True,network=network)
    else:
        from .factory_ai import render_factory_ai
        render_factory_ai(network,show_header=False)
    from .api_credentials import render_request_history
    render_request_history()
