"""Optional, session-only API setup and human-reviewed extraction."""
import os
import streamlit as st
from news.article_llm import extract_article
from news.article_fields import FIELD_LABELS
from news.article_mock import cases, load_mock, NOTES


def clear_key():
    st.session_state.rr_openai_key = ''
    st.session_state.rr_openai_key_input = ''


def update_key():
    # Unbound state survives Streamlit's cleanup when the dialog is hidden.
    st.session_state.rr_openai_key = st.session_state.get('rr_openai_key_input', '').strip()


def render_mock_loader(network):
    with st.expander('모의 LLM 테스트 · API 호출 없음', expanded=not bool(st.session_state.get('rr_article_draft'))):
        st.caption('Codex가 미리 작성한 가상 기사와 예상 응답입니다. 새 기사를 자동 분석하거나 실제 모델의 정확도를 검증하는 기능은 아닙니다.')
        selected = st.selectbox('모의 기사 사례', [item['id'] for item in cases()],
                                format_func=lambda key: NOTES[key][0], key='rr_mock_case')
        if st.button('가상 기사와 모의 응답 불러오기'):
            draft, saved = load_mock(network, selected)
            for key in list(st.session_state):
                if key.startswith('rr_fact_') or key in ('rr_article_target','rr_article_quote','rr_article_type',
                        'rr_article_scope','rr_llm_applied','rr_llm_provenance'):
                    st.session_state.pop(key, None)
            st.session_state.rr_article_draft = draft
            st.session_state.rr_llm_suggestion = saved
            st.rerun()


def render_llm_suggestion(network, draft):
    with st.expander('실제 API 설정 · 추후 연결', expanded=False):
        enabled = os.environ.get('SUPPLY_ARTICLE_LLM_UI') == '1'
        if not enabled:
            st.caption('API 연결 기능은 유지돼 있습니다. 현재는 실제 호출을 비활성화하고 모의 응답으로 테스트합니다.')
        st.caption('키는 현재 브라우저 세션의 서버 메모리에만 보관합니다.  \n파일·검토 기록에 저장하지 않습니다.  \n호출 시 본문과 등록 후보를 OpenAI로 전송하며 API 사용료가 발생할 수 있습니다.')
        if 'rr_openai_key_input' not in st.session_state:
            st.session_state.rr_openai_key_input = st.session_state.get('rr_openai_key', '')
        st.text_input('OpenAI API 키 · 채팅 대신 여기에 입력', type='password',
                      key='rr_openai_key_input', on_change=update_key)
        st.text_input('추출 모델', value='gpt-4.1-mini', key='rr_openai_model')
        st.button('세션에서 API 키 지우기', on_click=clear_key)
        st.caption('버튼당 1회 요청 · 자동 재시도 없음. 인용 일치는 검사하지만 사건 의미·사실의 정확성은 직접 검토해야 합니다.')
        if st.button('LLM으로 검토 초안 추출', disabled=not enabled or not bool(st.session_state.get('rr_openai_key'))):
            # Remove stale suggestions even when this new request fails.
            st.session_state.pop('rr_llm_suggestion', None)
            try:
                with st.spinner('원문 근거를 추출하는 중…'):
                    result = extract_article(network, draft, st.session_state.rr_openai_key,
                                             st.session_state.rr_openai_model)
                st.session_state.rr_llm_suggestion = {'draft_id': draft['id'], 'value': result,
                                                     'model': st.session_state.rr_openai_model.strip(), 'provider': 'openai'}
            except ValueError as error:
                st.error(str(error))
    render_saved_suggestion(network, draft)


def render_saved_suggestion(network, draft):
    saved = st.session_state.get('rr_llm_suggestion')
    if saved and saved['draft_id'] == draft['id']:
        mock = saved.get('provider') == 'mock'
        with st.expander('모의 LLM 응답 · 검토 대기' if mock else 'LLM 제안 · 검토 대기', expanded=True):
            proposal = saved['value']
            st.caption('Codex 작성 모의 응답 · 실제 API 호출 0회' if mock else '실제 API 추출 초안 · 사용자 검토 필요')
            st.write('대상: '+(network['nodes'][proposal['target']]['name'] if proposal['target'] else '연결 보류'))
            st.write(proposal['claim_type']+' / '+proposal['scope'])
            st.text(proposal['quote'] or '대상 근거 미확인')
            for key, label in FIELD_LABELS.items():
                field = proposal['fields'][key]
                st.write(label+': '+(field['value'] or '미확인'))
                if field['quote']:
                    st.text(field['quote'])
            if mock:
                st.markdown('**모의 해설**')
                st.write(saved['commentary']['text'])
            if st.button('제안을 아래 검토 양식에 채우기'):
                for key, source in [('target','target'), ('quote','quote'), ('type','claim_type'), ('scope','scope')]:
                    st.session_state['rr_article_'+key] = proposal[source]
                for key, field in proposal['fields'].items():
                    st.session_state['rr_fact_'+key] = field['value'] or ('미확인' if key == 'supply_status' else '')
                    st.session_state['rr_fact_'+key+'_quote'] = field['quote'] or ''
                st.session_state.rr_llm_applied = draft['id']
                st.session_state.rr_llm_provenance = {'draft_id': draft['id'], 'model': saved['model'],
                    'method': 'mock_assisted_human_review' if mock else 'llm_assisted_human_review',
                    'independently_verified': False}
                if mock:
                    st.session_state.rr_llm_provenance['case_id'] = saved['case_id']
                st.rerun()
