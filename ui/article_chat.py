"""Conversation shell for offline authored responses and explicit scenario review."""
from copy import deepcopy
import streamlit as st
from news.article_chat import respond
from simulation.schema import validate_parsed
from simulation.resilience import apply_issue
from resilience_materials import scopes_for_targets
from news.scenario_mock import mock_turn
from news.scenario_tools import validate_arguments, catalog
from news.scenario_llm import llm_turn


def update_chat_key():
    st.session_state.rr_openai_key=st.session_state.get('rr_chat_api_key','').strip()


def clear_chat_key():
    st.session_state.rr_openai_key=''
    st.session_state.rr_chat_api_key=''
    st.session_state.pop('rr_openai_key_input',None)


def reset_function_context():
    st.session_state.pop('rr_function_context',None)
    st.session_state.pop('rr_function_last',None)
    st.session_state.pop('rr_function_pending',None)
    st.session_state.pop('rr_review_open',None)


def change_chat_mode():
    mode=st.session_state.rr_chat_mode
    st.session_state.rr_function_mode=mode in ('모의 시뮬레이션','실제 LLM 시뮬레이션')
    st.session_state.rr_function_provider='OpenAI API' if mode=='실제 LLM 시뮬레이션' else '모의 · API 미사용'
    reset_function_context()


def apply_function_review(network):
    state=st.session_state
    pending=state.get('rr_function_pending')
    if not pending or not state.get('rr_function_mode'):
        state.rr_chat_apply_error='적용할 조건이 없습니다. 새 질문을 입력하세요.'
        return
    try:
        original=validate_arguments(pending['draft'],network,'\n'.join(pending['turns']))['engine_issue']
        if not original:
            raise ValueError('추출 조건을 먼저 완성하세요.')
        target=state.get('rr_review_target',original['targets'][0])
        days=state.get('rr_review_days',original['days'])
        rate=state.get('rr_review_loss',original['rate']*100)/100
        allowed={row['id'] for row in catalog(network)}
        if target not in allowed:
            raise ValueError('등록된 대상만 적용할 수 있습니다.')
        name=network['nodes'][target]['name']
        label='통항' if network['nodes'][target]['kind']=='logistics' else '공급'
        parsed=validate_parsed(dict(action='apply',kind='supply',targets=[target],days=days,rate=rate,
            text=f'{name} {label} {rate*100:g}% 감소 {days}일 가정',
            note='사용자가 확인·수정한 시뮬레이션 조건입니다. 실제 피해·생산량 예측이 아닙니다.'),network['nodes'])
        replacing=pending.get('replaces')
        events=[e for e in state.rr_events if not replacing or not all(e.get(k)==replacing[k] for k in ('kind','targets','rate','days'))]
        next_events=apply_issue(events,parsed)
        next_scopes=sorted(set(state.rr_material_scopes)|set(scopes_for_targets(network,parsed['targets'])))
        state.rr_events=next_events
        state.rr_material_scopes=next_scopes
        state.rr_days=parsed['days']; state.rr_focus=target; state.rr_view='이슈'; state.rr_process='전체'
        state.rr_reply=parsed['note']; state.rr_last_query=parsed['text']; state.rr_error=False
        state.rr_history=(state.rr_history+[{'query':parsed['text'],'reply':parsed['note']}])[-20:]
        state.rr_function_last={**pending['result'],'engine_issue':parsed,'confirmed':True,
                               'edited':any(parsed[k]!=original[k] for k in ('targets','rate','days'))}
        state.rr_review_open=False
        state.pop('rr_function_pending',None)
        state.pop('rr_chat_apply_error',None)
        state.rr_chat_messages=(state.get('rr_chat_messages',[])+[
            {'role':'assistant','text':'확인한 조건을 지도와 소재 충족도에 적용했습니다.'}])[-20:]
    except (ValueError,TypeError) as error:
        state.rr_chat_apply_error=str(error)


def reopen_function_review():
    state=st.session_state
    context=deepcopy(state.get('rr_function_context'))
    last=state.get('rr_function_last',{})
    if not context or not last.get('confirmed'):
        return
    parsed=last['engine_issue']
    context['replaces']=deepcopy(parsed)
    state.rr_function_pending=context
    state.rr_review_target=parsed['targets'][0]
    state.rr_review_days=parsed['days']
    state.rr_review_loss=float(parsed['rate']*100)
    state.rr_review_open=True


def render_function_review(network):
    state=st.session_state
    pending=state.get('rr_function_pending')
    if not pending:
        if state.get('rr_function_last',{}).get('confirmed'):
            st.button('추출 조건 다시 수정',on_click=reopen_function_review,width='stretch')
        return
    st.markdown('**적용 전 조건 확인**')
    st.caption('수정한 값은 기사 사실이 아닌 사용자 가정으로 적용합니다.')
    ids=[r['id'] for r in catalog(network)]
    with st.form('rr_function_review_form'):
        st.selectbox('적용 대상',ids,key='rr_review_target',format_func=lambda key:network['nodes'][key]['name']+' · '+key)
        cols=st.columns(2)
        with cols[0]: st.number_input('기간 · 일',1,365,key='rr_review_days')
        with cols[1]: st.number_input('감소율 · %',0.,100.,step=5.,key='rr_review_loss')
        st.form_submit_button('확인한 조건 적용',on_click=apply_function_review,args=(network,),type='primary',width='stretch')
    if state.get('rr_chat_apply_error'): st.error(state.rr_chat_apply_error)


def send_function_question(network):
    state=st.session_state
    text=state.get('rr_chat_text','')
    state.pop('rr_function_pending',None)
    state.pop('rr_chat_apply_error',None)
    try:
        live=state.get('rr_function_provider')=='OpenAI API'
        if live:
            context=llm_turn(network,state.get('rr_function_context'),text,
                             state.get('rr_openai_key',''),state.get('rr_function_model','gpt-4.1-mini'))
        else:
            context=mock_turn(network,state.get('rr_function_context'),text)
        state.rr_function_context=context
        result=context['result']
        state.rr_function_last=result
        parsed=result['engine_issue']
        if parsed:
            parsed=validate_arguments(context['draft'],network,'\n'.join(context['turns']))['engine_issue']
            state.rr_function_pending=deepcopy(context)
            state.rr_review_target=parsed['targets'][0]
            state.rr_review_days=parsed['days']
            state.rr_review_loss=float(parsed['rate']*100)
            state.rr_review_open=True
            reply='조건을 추출했습니다: '+parsed['text']+'. 아래에서 확인·수정한 뒤 적용하세요. 아직 지도·점수에는 반영하지 않았습니다.'
        else:
            reply='아직 적용하지 않았습니다. 확인할 항목: '+', '.join(result['missing'])+'. 예: “완전 봉쇄로 가정해” 또는 “부분 봉쇄, 통항 40% 감소”.'
    except ValueError as error:
        state.rr_function_context={}
        state.rr_function_last={'ready':False,'engine_issue':None,'error':str(error)}
        reply='새 입력을 적용하지 않았습니다: '+str(error)+' 기존 시나리오는 유지됩니다.'
    state.rr_chat_messages=(state.get('rr_chat_messages',[])+[{'role':'user','text':text},{'role':'assistant','text':reply}])[-20:]


def send_question(network):
    state=st.session_state
    if state.get('rr_function_mode'):
        send_function_question(network)
        return
    text=state.get('rr_chat_text','')
    context=state.get('rr_chat_context',{})
    current=state.get('rr_article_review')
    if current and current != context.get('review'):
        context={'review':deepcopy(current),'base_review':deepcopy(current)}
    try:
        context,reply=respond(network,context,text)
    except ValueError as error:
        reply=str(error)
    state.rr_chat_context=context
    state.rr_chat_messages=(state.get('rr_chat_messages',[])+[
        {'role':'user','text':text},{'role':'assistant','text':reply}])[-20:]
    if context.get('review'):
        state.rr_article_review=deepcopy(context['review'])
        state.rr_article_map_open=False
        state.rr_article_details=False
        state.rr_article_route=None
        if context.pop('action',None) == 'open_map':
            state.rr_article_map_open=True
            state.rr_article_dialog=False
    if context.get('suggestion'):
        if (state.get('rr_article_draft') or {}).get('id') != context['review']['article']['id']:
            for key in list(state):
                if key.startswith('rr_fact_') or key in ('rr_article_target','rr_article_quote','rr_article_type',
                        'rr_article_scope','rr_llm_applied','rr_llm_provenance'):
                    state.pop(key,None)
        state.rr_article_draft=deepcopy(context['review']['article'])
        state.rr_llm_suggestion=deepcopy(context['suggestion'])


def apply_chat_assumption(network):
    state=st.session_state
    context=state.get('rr_chat_context',{})
    proposal=context.get('proposal')
    current=state.get('rr_article_review')
    if not proposal or not current or current != context.get('review') or current['article']['id'] != proposal['article_id'] or current['target_id'] not in proposal['parsed']['targets']:
        state.rr_chat_apply_error='검토 대상이 바뀌었습니다. 가정을 다시 지정하세요.'
        return
    parsed=validate_parsed(proposal['parsed'],network['nodes'])
    state.rr_events=apply_issue(state.rr_events,parsed)
    state.rr_material_scopes=sorted(set(state.rr_material_scopes)|set(scopes_for_targets(network,parsed['targets'])))
    state.rr_reply=parsed['note']
    state.rr_last_query=parsed['text']
    state.rr_error=False
    state.rr_history=(state.rr_history+[{'query':parsed['text'],'reply':parsed['note']}])[-20:]
    state.rr_chat_messages=(state.rr_chat_messages+[{'role':'assistant','text':parsed['text']+' 가정을 적용했습니다. 기사 사실이 아니라 사용자가 지정한 모델 조건입니다.'}])[-20:]
    context.pop('proposal',None)
    context.pop('pending',None)
    state.pop('rr_chat_apply_error',None)


def render_chat_answer():
    messages=st.session_state.get('rr_chat_messages',[])
    live=st.session_state.get('rr_function_mode') and st.session_state.get('rr_function_provider')=='OpenAI API'
    if messages:
        st.markdown('**최근 답변**')
        st.write(messages[-1]['text'])
    else:
        st.caption('예: 가오슝항 30일 완전 봉쇄' if st.session_state.get('rr_function_mode') else '예: JSR 화재 예시를 설명해줘')
    proposal=st.session_state.get('rr_chat_context',{}).get('proposal')
    if proposal and not st.session_state.get('rr_function_mode'):
        parsed=proposal['parsed']
        st.warning(parsed['text']+' · 등록 대상 전체에 대한 가정입니다. 기사 속 특정 공장·고객 피해와 구분하세요.')


def render_chat_input(network):
    from .target_finder import render_target_finder
    modes=['직접 조건 선택','기사 검토 · 모의 대화','모의 시뮬레이션','실제 LLM 시뮬레이션']
    if 'rr_chat_mode' not in st.session_state:
        st.session_state.rr_chat_mode=modes[3] if st.session_state.get('rr_function_mode') and st.session_state.get('rr_function_provider')=='OpenAI API' else modes[2] if st.session_state.get('rr_function_mode') else modes[0]
    st.selectbox('분석 모드',modes,key='rr_chat_mode',on_change=change_chat_mode,label_visibility='collapsed')
    st.session_state.rr_function_mode=st.session_state.rr_chat_mode in modes[2:]
    st.session_state.rr_function_provider='OpenAI API' if st.session_state.rr_chat_mode==modes[3] else '모의 · API 미사용'
    if st.session_state.rr_chat_mode==modes[0]:
        from .manual_scenario import render_manual_scenario
        render_manual_scenario(network)
        return
    live=st.session_state.get('rr_function_mode') and st.session_state.get('rr_function_provider')=='OpenAI API'
    if live:
        with st.expander('LLM 연결 설정 · API 키',expanded=False):
            st.caption('질문·등록 ID·미완성 대화를 OpenAI로 전송합니다.  \n전송당 1회 유료 요청 가능 · 자동 재시도 없음.  \n키는 현재 세션 메모리에만 보관합니다.')
            if 'rr_chat_api_key' not in st.session_state:
                st.session_state.rr_chat_api_key=st.session_state.get('rr_openai_key','')
            st.text_input('OpenAI API 키',type='password',key='rr_chat_api_key',on_change=update_chat_key)
            st.text_input('함수 호출 모델',value='gpt-4.1-mini',key='rr_function_model')
            st.button('API 키 지우기',on_click=clear_chat_key)
    st.caption(('실제 LLM · 키 입력 완료' if st.session_state.get('rr_openai_key') else '실제 LLM · 설정에서 키 입력 필요') if live else '모의 시뮬레이션 · API 미사용' if st.session_state.get('rr_function_mode') else '기사 대화 · 모의 응답')
    render_target_finder(network)
    with st.form('rr_conversation_form',clear_on_submit=True):
        st.text_input('공급망 질문',key='rr_chat_text',max_chars=600,placeholder='가오슝항 30일 완전 봉쇄' if st.session_state.get('rr_function_mode') else 'JSR 화재 예시를 설명해줘',label_visibility='collapsed')
        live=st.session_state.get('rr_function_mode') and st.session_state.get('rr_function_provider')=='OpenAI API'
        st.form_submit_button('질문 보내기 · 실제 LLM' if live else '질문 보내기 · 모의 대화',on_click=send_question,args=(network,),width='stretch',type='primary',disabled=live and not bool(st.session_state.get('rr_openai_key')))
    if not st.session_state.get('rr_function_mode') and st.session_state.get('rr_chat_context',{}).get('proposal'):
        st.button('검토한 가정 적용',on_click=apply_chat_assumption,args=(network,),width='stretch')
    if st.session_state.get('rr_chat_apply_error'):
        st.error(st.session_state.rr_chat_apply_error)


def render_function_result(network,result):
    last=st.session_state.get('rr_function_last')
    if not last: return
    if last.get('error'):
        st.warning(last['error'])
        return
    with st.expander('함수 호출 JSON · 검증 결과',expanded=False):
        st.json(last['arguments'])
        if last.get('edited'):
            st.caption('위 JSON은 사용자 수정 전 추출값입니다. 현재 계산에는 확인한 수정 조건을 사용합니다.')
        context=st.session_state.get('rr_function_context',{})
        st.caption(('OpenAI '+context.get('model','')+' 응답' if context.get('mode')=='openai_function_call' else '모의 응답 · 실제 LLM 응답 아님')+' · 원문 근거와 등록 ID 검증 완료')
    if not last['ready']:
        st.write('추가 확인: '+', '.join(last['missing']))
        return
    parsed=last['engine_issue']
    if not last.get('confirmed'):
        st.write('추출 조건 · 적용 대기')
        st.write(parsed['text'])
        return
    active=any(all(event.get(key)==parsed[key] for key in ('kind','targets','rate','days')) for event in st.session_state.rr_events)
    st.markdown('**적용된 계산 가정**' if active else '**최근 함수 호출 · 현재 가정은 해제·변경됨**')
    st.write(parsed['text'])
    if network['nodes'][parsed['targets'][0]]['kind']=='logistics':
        availability=result['nodes'][parsed['targets'][0]]['effective']*100
        st.write(f'해당 물류 노드 가용률: {availability:g}% · 소재·생산 감소율과 구분')
    rows=[]
    for company,view in result['process_views'].items():
        if company in ('worst','mean'): continue
        for process,score in view['scores'].items():
            if score is not None and score<100-1e-7:
                rows.append({'기업':network['nodes'].get(company,{}).get('name',company),
                             '직접 공정':process,'소재 충족도':round(score,1)})
    if rows:
        st.markdown('**현재 전체 시나리오에서 부족이 계산된 기업·공정**')
        st.dataframe(rows,hide_index=True)
    else:
        st.write('현재 등록 범위에서 소재 부족이 계산된 공정은 없습니다. 실제 정상 생산 보장은 아닙니다.')
    st.caption('가상 물류 경유·재고·우회·등록 투입재 가정에 따른 결과입니다.  \n미산정 공정과 실제 생산 피해는 별도입니다.  \n기존 이슈가 있으면 함께 반영됩니다.')
