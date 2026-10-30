"""Factory incident review UI; explicit live/API-free states and reviewed maps."""
import json
import os
import streamlit as st
from .api_credentials import api_key, render_credentials, api_model, render_model
from news.factory_ai import (factory_registry,prepare_factory_article,analyze_factory_article,
    FIELD_LABELS)
from news.factory_examples import EXAMPLES,load_validation_example


def clear_factory_review():
    st.session_state.pop('factory_ai_result',None)
    st.session_state.pop('factory_ai_map',None)
    st.session_state.factory_ai_confirm=False


def load_factory_example(registry,key):
    clear_factory_review()
    st.session_state.factory_ai_body=EXAMPLES[key]['body']
    st.session_state.factory_ai_url=EXAMPLES[key]['url']
    st.session_state.factory_ai_result=load_validation_example(registry,key)


def render_factory_map(registry,result):
    chosen=st.session_state.get('factory_ai_map')
    if not chosen or chosen['article_id']!=result['draft']['id']:
        return
    ids=chosen['routes']
    if not ids:
        st.info('확인한 기업·시설은 있으나 지도에 표시할 검토 연결이 없습니다. 영향 없음 판정은 아닙니다.')
        return
    markers={};routes=[]
    for key in ids:
        route=registry['routes'][key]
        for company_id in (route['supplier'],route['customer']):
            company=registry['companies'][company_id];place=company.get('location')
            if not place:
                continue
            markers[company_id]=dict(id=company_id,name=company['name'],lat=place['lat'],lon=place['lon'],
                site='기업 개략 대표점',role='location',role_label='사건 기업' if company_id==result['company_id'] else '관련 고객 · 피해 미확인',
                impact='normal',score=None)
        if route['supplier'] in markers and route['customer'] in markers:
            routes.append(dict(start=route['supplier'],end=route['customer'],kind='primary',status='normal',material=route['material']))
    if not markers:
        st.info('등록된 위치가 없어 지도 표시를 보류했습니다.');return
    reference=chosen.get('mode')=='reference'
    data=dict(markers=list(markers.values()),routes=routes,review=True,applied=False,response=False,alternative=None,
        status_label='기업 관계 참고 · 피해 시설·품목과 연결 미확인' if reference else '사용자 확인 · 관련 연결 검토 / 고객 피해·물류 경로 미확정',title='AI 기사 검토',
        process='',material='',context='factory-ai-'+result['draft']['id'],camera_context='factory-ai-'+result['draft']['id'],
        camera_focus=dict(lat=45,lon=70,distance=3.5),selected=None)
    if st.session_state.get('demo_basic_map',False):
        import plotly.graph_objects as go
        figure=go.Figure()
        for route in routes:
            a,b=markers[route['start']],markers[route['end']]
            figure.add_trace(go.Scattergeo(lat=[a['lat'],b['lat']],lon=[a['lon'],b['lon']],mode='lines',line=dict(color='#4fe4db',width=2),hoverinfo='skip'))
        for marker in markers.values():
            figure.add_trace(go.Scattergeo(lat=[marker['lat']],lon=[marker['lon']],mode='markers+text',text=[marker['name']],textposition='top center',marker=dict(size=12,color='#4fe4db')))
        figure.update_layout(height=460,showlegend=False,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor='#040c18',font=dict(color='#dceaf8'),geo=dict(projection_type='natural earth',bgcolor='#040c18',showland=True,landcolor='#10283a'))
        st.plotly_chart(figure,key='factory_ai_basic',width='stretch',theme=None,config=dict(displayModeBar=False,topojsonURL='/app/static/'))
    else:
        from .night_globe import component
        component()(data=data,key='factory_ai_globe',width='stretch',height=520)
    st.caption('관련성 검토 지도입니다. 기업 대표점이며 실제 운송 항로·제조 공장 간 연결·고객 피해를 확정하지 않습니다. 기존 시나리오의 감소율·점수는 변경하지 않습니다.')


def render_factory_ai(network,show_header=True):
    registry=factory_registry(network)
    if show_header:st.subheader('AI · 공장 사건과 공급망 연결 검토')
    st.caption('입력 본문의 핵심 근거와 미확인 사항을 요약합니다. 뉴스 요약은 공급 감소율·고객 손실 계산에 자동 반영되지 않습니다.')
    st.caption('화재·실제 가동 중단만 지원합니다. 항만·해협은 물류 검토에서 확인하고, 관세는 AI 자동 연결 대상에서 제외합니다.')
    with st.expander('AI의 역할과 확인 범위'):
        st.write('① 사건·시설·제품과 근거 추출 → ② 등록 연결의 관련성·보류 이유 해석 → ③ 승인·공급 여력 등 추가 확인 조건 설명')
        st.caption('등록 기업·연결과 인용·날짜는 코드로 검사합니다. 인용 일치는 사실·의미의 검증이 아니므로 원문을 직접 확인합니다. AI가 새 공급 관계·대체 성공·피해율을 만들거나 점수를 자동 변경하지 않습니다.')
        st.write(f"등록 기업 {len(registry['companies'])}곳 / 검토 연결 {len(registry['routes'])}개 · 산업 전체 목록이 아닙니다.")
        st.caption('AKM의 노베오카 시설과 2020년 사건은 별도 확인한 사례입니다. 그 외 기업은 시설·제품 연결 근거가 부족하면 고객 영향 연결을 보류합니다.')
    left,right=st.columns([2,1],gap='large')
    with right:
        with st.expander('API 연결 설정',expanded=False):
            server_key=os.environ.get('SUPPLY_AI_API_KEY') or os.environ.get('OPENAI_API_KEY','')
            render_credentials('factory')
            st.caption('공개 기사 본문·등록 근거를 전송합니다. 클릭당 1회 요청하며 자동 재시도하지 않습니다.')
            render_model('factory')
        with st.expander('API 없이 검증 동작 살펴보기'):
            example=st.selectbox('검증 예시',list(EXAMPLES),format_func=lambda k:EXAMPLES[k]['label'],key='factory_ai_example')
            st.caption('직접 작성한 예시 문장과 예상 초안입니다. 실제 AI 응답·저장된 API 결과·AI 정확도 평가가 아닙니다. AKM 문장도 공식 원문의 직접 발췌가 아닙니다.')
            st.button('검증 예시 불러오기 · AI 호출 없음',key='factory_ai_load',on_click=load_factory_example,args=(registry,example),width='stretch')
    with left:
        st.caption('기사 내용을 복사해 붙여넣으세요. URL만 입력하면 분석할 수 없습니다.')
        st.text_area('공개 기사 본문',height=190,max_chars=20000,key='factory_ai_body',on_change=clear_factory_review,
            placeholder='기업·공장·사건의 근거가 있는 본문을 붙여넣으세요. URL만으로 원문을 수집하지 않습니다.')
        st.text_input('출처 URL · 선택',key='factory_ai_url',on_change=clear_factory_review)
        key=api_key()
        import re
        url_only=bool(re.fullmatch(r'https?://\S+',st.session_state.get('factory_ai_body','').strip()))
        if url_only:st.warning('본문 칸에 기사 주소가 들어 있습니다. 기사 텍스트를 붙여넣고 주소는 아래 출처 URL에 넣어주세요. API 요청은 보내지 않습니다.')
        if st.button('AI로 사건·범위·연결 검토',key='factory_ai_run',type='primary',disabled=not bool(key) or url_only,width='stretch'):
            clear_factory_review()
            try:
                draft=prepare_factory_article(st.session_state.get('factory_ai_body',''),st.session_state.get('factory_ai_url',''))
                with st.spinner('사건 범위와 등록 연결의 근거를 검토하고 있습니다…'):
                    result=analyze_factory_article(registry,draft,key,api_model())
                st.session_state.factory_ai_result=result
            except ValueError as error:
                st.error(str(error))
        if not key:
            st.info('API 키를 설정하면 실제 AI 분석을 실행할 수 있습니다. 검증 예시는 API 없이 확인할 수 있습니다.')
    result=st.session_state.get('factory_ai_result')
    if not result:
        return
    try:
        current=prepare_factory_article(st.session_state.get('factory_ai_body',''),st.session_state.get('factory_ai_url',''))
    except ValueError:
        return
    if current['id']!=result['draft']['id']:
        st.info('원문이 변경됐습니다. 다시 분석하세요.');return
    provenance=result['provenance']
    st.divider()
    if provenance['method']=='live_api':
        st.caption('실제 API 분석 · 모델 '+provenance['model']+' · 사용자 검토 대기')
    else:
        st.warning('검증 예시 · AI 호출 0회 · 실제 모델 성능을 검증한 결과가 아닙니다.')
    st.markdown('**'+result['status']+'**')
    st.write('사건 기업: '+(result['company_name'] or '등록 기업 미연결 / 직접 당사자 미확정'))
    st.caption(result['validation'])
    facts,links,checks=st.tabs(['사건·근거 해석','등록 연결·보류 이유','추가 확인 조건'])
    with facts:
        st.write('분류: '+{'factory_fire':'공장 화재','factory_shutdown':'실제 가동 중단','other':'지원 범위 밖','no_event':'직접 사건 미확인'}[result['event_type']])
        st.dataframe([{'항목':label,'추출 값':result['fields'][name]['value'] or '미확인','본문 근거':result['fields'][name]['quote'] or ''} for name,label in FIELD_LABELS.items()],hide_index=True)
        for finding in result['findings']:
            st.write('AI 근거 요약 · '+finding['interpretation']);st.text('본문 근거: '+finding['quote'])
        st.caption('본문에 정보가 없다는 것은 실제 피해가 없거나 회사가 공개하지 않았다는 뜻이 아닙니다. 매출 전망 유지와 생산 차질 여부도 별도로 확인해야 합니다.')
        st.caption('공급 감소율·차질 기간·고객 손실은 산정하지 않았습니다.')
    with links:
        if not result['routes']:
            st.info('표시할 등록 연결을 선택하지 못했습니다. 무관함·영향 없음으로 확정한 것은 아닙니다.')
        for row in result['routes']:
            route=row['route']
            st.markdown('**'+registry['companies'][route['supplier']]['name']+' → '+registry['companies'][route['customer']]['name']+' / '+route['material']+'**')
            st.write(('범위 일치 · 검토 연결' if row['state']=='bounded_review' else '영향 연결 보류')+' · '+row['gate_reason'])
            st.write('AI 검토 이유 · '+row['ai_reason']);st.text('본문 근거: '+row['quote'])
            st.caption(route['scope'])
            if route['source']:st.markdown('[등록 연결의 별도 근거]('+route['source']+')')
    with checks:
        for q in result['review_questions']:
            st.markdown('**'+q['question']+'**');st.write('AI 선정 이유 · '+q['reason']);st.text('본문 근거: '+q['quote'])
        if not result['review_questions']:st.write('추가 검토 조건 제안 없음 · 충분한 자료가 있다는 뜻은 아닙니다.')
    eligible=[r['route_id'] for r in result['routes'] if r['state']=='bounded_review'] if result['supported'] else []
    st.checkbox('원문과 등록 자료를 확인했습니다 · 고객 피해 확정과 구분',key='factory_ai_confirm')
    if st.button('확인한 검토 연결을 지도에 표시',key='factory_ai_apply',disabled=not eligible or not st.session_state.get('factory_ai_confirm'),width='stretch'):
        st.session_state.factory_ai_map=dict(article_id=result['draft']['id'],routes=eligible,mode='bounded')
    reference=[r['route_id'] for r in result['routes']] if result['supported'] else []
    if not eligible and reference:
        st.caption('영향 연결은 보류했습니다. 아래에서는 피해와 구분해 기존 기업 관계만 참고할 수 있습니다.')
        if st.button('기업 관계만 참고 지도에 표시',key='factory_ai_reference',disabled=not st.session_state.get('factory_ai_confirm'),width='stretch'):
            st.session_state.factory_ai_map=dict(article_id=result['draft']['id'],routes=reference,mode='reference')
    render_factory_map(registry,result)
    st.download_button('분석·근거·보류 기록 내려받기',json.dumps(result,ensure_ascii=False,indent=2),file_name='factory-incident-review.json',mime='application/json',key='factory_ai_download')
