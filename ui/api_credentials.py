"""Shared session-only credentials; independent of widget lifecycle."""
import os
import streamlit as st

LEGACY=('research_secret','research_key_input','alternative_key','factory_ai_key')

def session_key(state):
    if 'ai_api_secret' not in state:
        state['ai_api_secret']=next((state.get(k,'').strip() for k in LEGACY if state.get(k,'').strip()),'')
    return state['ai_api_secret']

def api_key():
    return os.environ.get('SUPPLY_AI_API_KEY') or os.environ.get('OPENAI_API_KEY') or session_key(st.session_state)

def update_key(widget):
    st.session_state.pop('ai_connection_diagnostic',None)
    st.session_state.ai_api_secret=st.session_state.get(widget,'').strip()
    for name in LEGACY:
        st.session_state.pop(name,None)

def clear_key():
    st.session_state.pop('ai_connection_diagnostic',None)
    st.session_state.ai_api_secret=''
    for name in LEGACY:
        st.session_state.pop(name,None)

def render_credentials(panel):
    session_key(st.session_state)
    if os.environ.get('SUPPLY_AI_API_KEY') or os.environ.get('OPENAI_API_KEY'):
        st.caption('세 AI 기능 모두 서버 환경변수의 API 키를 사용합니다.')
        return
    widget='shared_api_input_'+panel
    st.session_state[widget]=st.session_state.ai_api_secret
    st.text_input('공통 API 키 · 현재 세션에만 보관',type='password',key=widget,on_change=update_key,args=(widget,))
    st.caption('사건·공정 조사, 기업·소재 비교, 기사 검토에 같은 키를 사용합니다.')
    st.button('공통 API 키 지우기',key='clear_shared_'+panel,on_click=clear_key)


def api_model():
    if 'ai_api_model' not in st.session_state:
        st.session_state.ai_api_model=st.session_state.get('research_model') or os.environ.get('SUPPLY_AI_MODEL','gpt-4.1-mini')
    return st.session_state.ai_api_model

def update_model(widget):
    st.session_state.pop('ai_connection_diagnostic',None)
    st.session_state.ai_api_model=st.session_state.get(widget,'').strip()

def render_model(panel):
    widget='shared_model_'+panel
    st.session_state[widget]=api_model()
    st.text_input('공통 모델 ID',key=widget,on_change=update_model,args=(widget,))
    st.caption('세 AI 기능에 동일한 키·모델 적용 · 연결 설정 v4')

    with st.expander('연결 진단 · 같은 키로 요청 방식 비교'):
        st.caption('최대 2회 소량의 유료 API 요청을 보냅니다. 문서·제품 데이터는 전송하지 않으며 첫 요청 실패 시 중단합니다.')
        if st.button('연결 진단 실행',key='diagnose_'+panel,disabled=not bool(api_key())):
            from news.api_diagnostic import diagnose
            try:
                with st.spinner('동일한 키·모델로 연결을 확인합니다…'):
                    result=diagnose(api_key(),api_model())
                st.session_state.ai_connection_diagnostic=result
            except ValueError as error:
                st.error(str(error))
        result=st.session_state.get('ai_connection_diagnostic')
        if result:
            st.caption('아래는 세 화면에서 공유하는 별도 연결 진단 기록입니다. 현재 부문의 분석 실행 결과가 아닙니다.')
            st.caption('진단 시각(UTC): '+result['time']+' · 당시 모델: '+result['model'])
            st.dataframe(result['rows'],hide_index=True)
            if result['rows'][0]['결과']=='실패':
                st.info('제품 비교 데이터가 없는 작은 일반 요청도 실패했습니다. 제품 데이터나 구조화 형식만의 문제로 볼 수 없습니다. 아래 기록을 지원 문의에 첨부할 수 있습니다.')
            elif len(result['rows'])==2 and result['rows'][1]['결과']=='실패':
                st.info('동일한 키·모델로 일반 응답은 성공하고 구조화 응답은 실패했습니다. 시점별 서버 상태 차이도 가능하므로 구조화 형식이 원인이라고 단정하지 않습니다.')
            else:
                st.info('작은 일반·구조화 요청은 모두 성공했습니다. 실제 분석 요청의 크기·내용·실행 시점 차이를 추가 확인해야 합니다.')
            import json
            st.download_button('진단 기록 내려받기',json.dumps(result,ensure_ascii=False,indent=2),file_name='api-diagnostic.json',mime='application/json',key='diagnostic_download_'+panel)


def render_request_history():
    with st.expander('실제 API 호출 기록 · 부문별 성공/실패 비교',expanded=True):
        st.caption('이번 수정 이후의 실제 요청만 최근 30건 기록합니다. 같은 세션에서 연결 식별값이 같으면 같은 키입니다. 키·본문·응답 내용은 저장하지 않습니다. API 응답 완료는 이후 분석 검증의 성공까지 뜻하지 않습니다.')
        rows=st.session_state.get('ai_request_history',[])
        if not rows:
            st.info('아직 기록된 호출이 없습니다. 기존 표시 결과나 API 없는 비교표는 새 호출로 기록되지 않습니다.')
            return
        st.dataframe(list(reversed(rows)),hide_index=True)
        import json
        st.download_button('부문별 호출 기록 내려받기',json.dumps(rows,ensure_ascii=False,indent=2),
                           file_name='api-request-history.json',mime='application/json',key='ai_request_history_download')
