"""Grounded external research cards and a separately labeled local library."""
import json
import os
from urllib.parse import urlsplit
import streamlit as st
from .api_credentials import api_key, render_credentials, api_model, render_model
from company_evidence import evidence_bundle
from news.external_research import MODES,SECTIONS,PROCESSES,make_research_context,research_external,format_research,ResearchError,suggest_mode

EXAMPLES={
    '관세 → 공정':'희토류 관세가 반도체 공정에 미치는 영향은?',
    '공장 중단 → 공정':'포토레지스트 공장이 멈추면 어떤 공정에 영향이 있어?',
    '기업·벤더':'SUMCO 공급이 중단되면 영향과 대체 기업은?',
    '소재 벤더':'NF3 공급이 끊기면 대체 공급사는?',
    '희토류 · CMP':'산화세륨에 관세가 붙는다고 가정하면 CMP 공정 영향과 검토 조건은?',
    'ArF · 액침':'ArF 액침 Positive 포토레지스트 공급 중단 시 대체 공급사는?',
    'HF · 농도':'고순도 불화수소 수용액 농도 49%, 총 금속 1 ppb 이하 대체 공급사를 검토해줘.',
    '항로 우회':'수에즈가 막히면 부산에서 로테르담까지 우회는?'}



def clear_research():
    for key in ('research_report','research_partial'):st.session_state.pop(key,None)


def load_question():
    clear_research();st.session_state.research_query=EXAMPLES[st.session_state.research_example]
    if '→ 공정' in st.session_state.research_example:st.session_state.research_mode='공정 영향'
    else:st.session_state.research_mode='통합 검토'


def update_secret():
    st.session_state.research_secret=st.session_state.get('research_key_input','').strip()


def clear_secret():
    st.session_state.research_secret=''
    st.session_state.research_key_input=''


def source_link(source):
    label=source['title'].replace('\\','\\\\').replace('[','\\[').replace(']','\\]')
    url=source['url'].replace('(','%28').replace(')','%29')
    st.markdown('['+label+']('+url+')')
    st.caption(urlsplit(source['url']).hostname)
    if source.get('origin')=='web_search_consulted':st.caption('검색 참조 자료 · 본문 인용 여부 미확인')


def render_registered_query(bundle,query):
    matched=[p for p in bundle['profiles'] if any(len(name)>2 and name.casefold() in query.casefold() for name in [p['name']]+p.get('aliases',[]))]
    if not matched:return
    with st.expander('현재 질문에 연결된 등록 근거 · API 없이 확인',expanded=True):
        st.caption('기존에 확보한 공식 자료의 정리입니다. 방금 외부 검색으로 확인한 결과나 AI 추천은 아닙니다.')
        names={p['name'] for p in matched}
        rows=[r for r in bundle['relationships'] if r['supplier'] in names or r['customer'] in names]
        if rows:
            st.markdown('**공개된 기업 관계**')
            st.dataframe([{'공급사':r['supplier'],'관련 기업':r['customer'],'확인 내용':r['statement'],'확인 범위':r['limit']} for r in rows],hide_index=True,width='stretch')
        families={p['family'] for profile in matched for p in profile['products']}
        products=[dict(기업=profile['name'],제품=p['name'],범위='같은 소재군 · 세부 조건·인증 미검증')
            for profile in bundle['profiles'] if profile['name'] not in names for p in profile['products'] if p['family'] in families]
        if products:
            st.markdown('**같은 소재군의 기업·제품 · 세부 조건 비교 전**')
            st.dataframe(products,hide_index=True,width='stretch',height=230)
        sids={s for profile in matched for s in profile['source_ids']}
        for r in rows:sids.update(r['source_ids'])
        with st.expander('등록 관계·제품의 공식 자료'):
            for sid in sorted(sids):source_link(bundle['sources'][sid])


def render_library(bundle):
    with st.expander('기업·벤더·우회 발표 자료 · API 없이 확인'):
        st.caption('저장된 공식 자료를 직접 확인하는 라이브러리입니다. AI 검색 결과·현행 계약·실제 고객 피해 목록이 아닙니다.')
        profiles={p['name']:p for p in bundle['profiles']}
        selected=st.selectbox('기업 프로필',sorted(profiles),key='research_library_company')
        profile=profiles[selected];st.write(profile['role'])
        if profile['products']:
            st.write('제품 자료: '+' · '.join(p['name'] for p in profile['products']))
            for product in profile['products']:
                if product.get('notes'):st.caption(product['name']+' · '+product['notes'])
        rows=[r for r in bundle['relationships'] if selected in (r['supplier'],r['customer'])]
        if rows:
            st.dataframe([{'공급사':r['supplier'],'상대 기업':r['customer'],'자료 연도':r['year'],'자료상 관계':r['statement'],'한계':r['limit']} for r in rows],hide_index=True)
            if st.checkbox('등록 기업 관계 개략도 보기',key='research_library_graph'):
                dot=['digraph relationships {rankdir=LR;bgcolor="transparent";node[shape=box,style="rounded,filled",fillcolor="#102a3d",color="#4fe4db",fontcolor="#deedf7"];edge[color="#4fe4db"];']
                for r in rows:dot.append(json.dumps(r['supplier'])+' -> '+json.dumps(r['customer'])+';')
                st.graphviz_chart('\n'.join(dot+['}']))
                st.caption('공개 발표에 기록된 기업 관계 개략도 · 사건 피해·품목별 현행 계약·실제 운송 경로 아님')
        related=[r for r in bundle['routes'] if r['carrier']==selected]
        for route in related:
            st.write(route['scope']+' · '+route['original']+' → '+route['alternative']);st.caption(route['limit'])
        sids=set(profile['source_ids'])
        for r in rows+related:sids.update(r['source_ids'])
        for sid in sorted(sids):
            source=bundle['sources'][sid]
            st.markdown('['+source['title']+']('+source['url']+')');st.caption((source.get('edition') or '발행 시점 미표기')+' · '+source['scope'])
        st.download_button('기업·벤더·우회 근거 라이브러리',json.dumps(bundle,ensure_ascii=False,indent=2),file_name='company-response-library.json',mime='application/json',key='research_library_download')


def render_process_visual(report):
    affected={item['entity'] for item in report['impact_review']}
    st.subheader('사건에서 공정까지')
    if report.get('question'):
        with st.expander('입력한 사건·질문'):st.write(report['question'])
    cols=st.columns([1,0.1,1,0.1,1])
    with cols[0]:
        with st.container(border=True):
            st.markdown('**① 사건·소재 근거**')
            st.write('관세·공장 중단·공급 차질')
            st.caption('실제 발표와 입력 가정을 구분')
    with cols[1]:st.write('→')
    with cols[2]:
        with st.container(border=True):
            st.markdown('**② 소재·제품의 용도**')
            st.write('공정에 쓰이는 경로 확인')
            st.caption('연결 소재와 조건은 아래 결과에서 확인')
    with cols[3]:st.write('→')
    with cols[4]:
        with st.container(border=True):
            st.markdown('**③ 영향 검토 공정**')
            st.write(' · '.join(p for p in PROCESSES if p in affected) or '공정 연결 근거 부족')
            st.caption('실제 가동 중단 여부는 별도 확인')
    for start in (0,4):
        for col,process in zip(st.columns(4),PROCESSES[start:start+4]):
            with col:
                with st.container(border=True):
                    st.markdown(('**:cyan[● '+process+']**') if process in affected else '**'+process+'**')
                    st.caption('조건부 영향 검토' if process in affected else '이번 결과에 연결 근거 미표시')
    st.caption('강조 표시는 공정 연결 검토 대상입니다. 다른 공정의 영향 없음이나 피해 규모를 뜻하지 않습니다.')


def render_report(report):
    if report.get('answer_only'):
        st.divider()
        st.subheader('분석 결과')
        st.caption('웹 검색 1회 기반 · AI 해설 · 원문 확인 필요')
        if not report['search'].get('citation_count'):
            st.warning('참조 자료는 있으나 문장별 인용이 없습니다. 아래 내용은 검토 초안입니다.')
        # Plain text prevents model-generated links/images from bypassing native source validation.
        answer=report['search']['text'].strip()
        preview=answer.split('\n\n')[0]
        if len(preview)>400:preview=preview[:400]+'…'
        st.text(preview)
        if preview!=answer:
            with st.expander('전체 답변 보기',expanded=False):st.text(answer)
        for source in report['search']['sources'][:3]:source_link(source)
        with st.expander('출처 · 전체 답변 보관'):
            st.caption('아래 문장은 검색 답변의 인용 범위입니다. 원문 발췌·독립 사실 검증과는 구분합니다.')
            by_id={s['id']:s for s in report['search']['sources']}
            for block in report['search'].get('blocks',[]):
                for citation in block.get('citations',[]):
                    end=citation.get('end');start=citation.get('start')
                    if isinstance(start,int) and isinstance(end,int) and 0<=start<end<=len(block['text']):
                        st.text(block['text'][max(0,start-240):end])
                        source=by_id.get(citation['source_id'])
                        if source:source_link(source)
            for source in report['search']['sources']:source_link(source)
            st.download_button('답변·출처 보관',json.dumps(report,ensure_ascii=False,indent=2),file_name='supply-answer.json',mime='application/json',key='research_download')
        return
    st.divider();st.caption('실제 웹 검색 + AI 정리 · 모델 '+report['provenance']['model']+' · 사용자 검토 대기')
    st.write(report['summary']);st.caption(report['warning'])
    if report['search'].get('citation_count')==0:
        st.warning('검색 참조 URL로 구성한 검토 초안입니다. 본문 인용이 없어 주장과 원문의 연결을 직접 확인해야 합니다.')
    process=report.get('mode')=='공정 영향'
    if process:
        render_process_visual(report)
        st.caption('관세는 조달 비용·거래 조건, 공장 중단은 중단 품목의 공급 경로를 검토합니다. 실제 생산 차질 여부·크기는 별도 확인 대상입니다.')
    labels=['impact_review','source_statements'] if process else ['source_statements','impact_review','vendor_options','route_options']
    tabs=st.tabs(['영향 검토 공정','사건·소재 근거','추가 확인'] if process else ['발표·관계 근거','기업 영향','대체 벤더','항로 우회','미확인'])
    for tab,section in zip(tabs,labels):
        with tab:
            if not report[section]:st.info('이번 조사에서 표시할 항목이 없습니다. 영향 없음·대체 불가라는 판정은 아닙니다.')
            for item in report[section]:
                with st.container(border=True):
                    st.markdown('**'+item['entity']+'**')
                    st.caption(item['origin']+' · '+{'source_statement':'자료상 발표·관계','conditional':'조건부 영향 검토','candidate':'실행 가능성 추가 확인할 후보'}[item['basis']])
                    st.write(item['statement'])
                    for sid in item['source_ids']:
                        source=report['sources'][sid]
                        source_link(source)
                        if source.get('edition'):st.caption('등록 자료 시점: '+source['edition'])
    with tabs[-1]:
        for value in report['unknowns']:st.write('• '+value)
        if not report['unknowns']:st.caption('미확인 항목 제안 없음 · 실행 가능성 보증이 아닙니다.')
    with st.expander('검색 인용 출처·검색 답변 확인'):
        st.caption('외부 검색은 조회 시점의 초안입니다. 인용 URL이 존재한다는 것과 해당 주장·공식성·현재성을 확인한 것은 다릅니다.')
        st.text(report['search']['text'])
        for source in report['search']['sources']:source_link(source)
    st.download_button('외부 검토 결과·출처 내려받기',json.dumps(report,ensure_ascii=False,indent=2),file_name='external-supply-review.json',mime='application/json',key='research_download')


def render_external_research(show_header=True,network=None):
    bundle=evidence_bundle()
    if show_header:st.subheader('AI · 사건과 소재의 공정 영향 검토')
    left,right=st.columns([2,1],gap='large')
    with right:
        with st.expander('질문 예시',expanded=False):
            example=st.selectbox('질문 예시',list(EXAMPLES),key='research_example')
            st.button('질문만 불러오기',key='research_load',on_click=load_question,width='stretch')
        server_key=os.environ.get('SUPPLY_AI_API_KEY') or os.environ.get('OPENAI_API_KEY','')
        with st.expander('API 연결 설정',expanded=False):
            render_credentials('research')
            render_model('research')
            st.caption('간단 답변은 API 요청 1회, 상세 카드는 2회이며 웹 검색 도구 사용료가 발생할 수 있습니다. 검색 도구 호출은 최대 3회로 제한하며 자동 재시도하지 않습니다. 공개 질문·등록 자료를 전송합니다.')

    with left:
        if 'research_query' not in st.session_state:st.session_state.research_query=EXAMPLES['공장 중단 → 공정']
        st.text_area('무엇이 궁금한가요?',height=100,max_chars=3000,key='research_query',on_change=clear_research,placeholder='예: SUMCO가 멈추면 대체 기업은?')
        with st.expander('분석 조건 · 선택',expanded=False):
            st.selectbox('검토 범위',['자동']+list(MODES),key='research_mode',on_change=clear_research)
            from news.external_research import INTENTS,question_intent
            intent=st.selectbox('질문의 목적',INTENTS,key='research_intent',on_change=clear_research)
            st.caption('질문 해석: '+question_intent(st.session_state.research_query,intent)+' · 목적이 다르면 위에서 변경하세요.')
            from news.facility_scope import facility_scope
            scope=facility_scope(st.session_state.research_query)
            facility_id=''
            if scope['facilities']:
                from hashlib import sha256
                options={'':'질문에서 확인 · 미지정이면 전체 거점'}
                options.update({f['id']:f['name'] for f in scope['facilities']})
                facility_id=st.selectbox('검토할 공장 · 피해 사실을 확정하는 선택이 아닙니다',list(options),format_func=options.get,
                    key='research_facility_'+sha256(st.session_state.research_query.encode()).hexdigest()[:10],on_change=clear_research)
                active=facility_scope(st.session_state.research_query,facility_id)
                st.caption('공장 범위: '+(active['selected']['name'] if active['selected'] else '미지정 · 기업 전체 피해로 확대하지 않음'))
            enrich=st.checkbox('외부 대체 기업도 근거·조건 비교',value=True,key='research_enrich',on_change=clear_research)
            if enrich:st.caption('후보 정리 API 요청 1회 추가 · 공개 출처 원문 최대 6개 확인 · 위치 근거가 없으면 카드만 표시')
            simple=st.checkbox('간단 답변 · 핵심 설명과 출처 보기',value=True,key='research_simple',on_change=clear_research)

            mode=suggest_mode(st.session_state.research_query) if st.session_state.research_mode=='자동' else st.session_state.research_mode
            st.caption('이번 질문의 검토 범위: '+mode)
            with st.expander('추가 조건 · 소재·출발지·도착지'):
                route=mode in ('항로 우회','통합 검토')
                origin=destination=''
                if route:
                    with st.expander('항로 조건 · 항로 검토 시 입력',expanded=st.session_state.research_mode=='항로 우회'):
                        a,b=st.columns(2)
                        with a:origin=st.text_input('출발지',key='research_origin',on_change=clear_research)
                        with b:destination=st.text_input('도착지',key='research_destination',on_change=clear_research)
                st.text_input('화물·취급 조건 · 선택' if route else '소재·제품 정보 · 선택',key='research_cargo',max_chars=200,on_change=clear_research,
                    placeholder='예: 일반 컨테이너 / 위험물·특수가스' if route else '예: ArF 액침 포토레지스트 / NF3 / 피해 공장·중단 품목')
        try:context=make_research_context(bundle,st.session_state.research_query,mode,origin,destination,st.session_state.research_cargo,intent=intent,external_candidates=enrich,facility_id=facility_id)
        except ValueError as error:
            st.info(str(error));return
        saved=st.session_state.get('research_report')
        if saved and saved['context_id']!=context['id']:clear_research();saved=None
        partial=st.session_state.get('research_partial')
        if partial and partial['context_id']!=context['id']:clear_research();partial=None
        key=api_key()
        if st.button('분석하기',key='research_run',type='primary',disabled=not bool(key),width='stretch'):
            clear_research();saved=None;partial=None;progress=st.empty()
            try:
                saved=research_external(context,key,api_model(),on_progress=progress.info,simple=simple)
                st.session_state.research_report=saved
                from .research_history import remember
                st.session_state.research_answer_history=remember(st.session_state.get('research_answer_history',[]),saved)
            except ResearchError as error:
                st.error(str(error))
                partial=dict(context_id=context['id'],search=error.search)
                st.session_state.research_partial=partial
            except ValueError as error:st.error(str(error))
            finally:progress.empty()
        if not key:st.info('AI 분석을 실행하려면 오른쪽 ‘API 연결 설정’에 키를 입력하세요.')
    from .research_history import render_history
    render_history()
    if saved:
        render_report(saved)
        if saved.get('candidate_error'):st.warning(saved['candidate_error'])
        elif context.get('external_candidates') and not saved.get('external_candidates'):st.caption('이번 검색에서 원문 근거까지 연결된 외부 후보가 없습니다. 등록 후보는 아래에서 비교할 수 있습니다.')
    elif partial:
        st.warning('출처가 있는 검색 초안은 보관했습니다. 상세 카드 정리는 완료되지 않았습니다.' if partial['search']['sources'] else '검색 도구는 실행됐지만 출처를 확보하지 못했습니다. 검증 가능한 답변이 아직 없습니다.')
        st.download_button('검색 초안·출처 보관',json.dumps(partial,ensure_ascii=False,indent=2),file_name='unreviewed-search-draft.json',mime='application/json',key='research_partial_download')
        if partial['search']['sources']:
            st.caption('검색을 다시 하지 않고 정리 요청만 1회 실행할 수 있습니다. 별도 사용료가 발생할 수 있으며 자동 재시도하지 않습니다.')
            if st.button('저장된 검색으로 보고서 정리만 재시도',key='research_format_retry',disabled=not bool(key),width='stretch'):
                try:
                    with st.spinner('기존 검색 초안을 정리하고 있습니다…'):
                        result=format_research(context,partial['search'],key,api_model(),reuse=True)
                    st.session_state.research_report=result
                    st.session_state.pop('research_partial',None)
                    st.rerun()
                except ValueError as error:st.error(str(error))
        with st.expander('미검증 검색 초안·참조 자료'):
            st.caption('검색 답변의 사건·수치·용도는 원문 확인 전입니다. 인용 링크가 있다고 주장이 검증된 것은 아닙니다.')
            st.text(partial['search']['text'])
            for source in partial['search']['sources']:source_link(source)
        if not partial['search']['sources']:
            st.info('출처 누락은 질문의 구체성만으로 설명할 수 없습니다. 반복 실행 전에 검색 진단을 확인하세요. 원인을 확인할 때까지 추가 결제는 필요하지 않습니다.')
            with st.expander('검색 응답 형식 진단 · 키 제외'):
                st.json(partial['search'].get('diagnostics',{'안내':'이전 버전의 초안에는 형식 진단이 없습니다. 현재 보관 파일과 검색 초안을 먼저 확인하세요.'}))
            render_registered_query(bundle,context['query'])
    from news.material_scope import render_material_scope
    with st.expander('소재별 검토 기준',expanded=False):
        render_material_scope(context['query']+' '+context.get('cargo',''))
    from news.vendor_candidates import registered_candidates
    from news.vendor_candidates import question_requirements
    from product_comparison import LABELS,STATUS
    comparison_query=context['query']+' '+context.get('cargo','')
    candidates=[] if context.get('intent')=='실제 사건 확인' else registered_candidates(bundle,comparison_query)
    bundle=dict(bundle,sources=dict(bundle['sources']))
    for external in (saved or {}).get('external_candidates',[]):
        if not any(external['name'].casefold() in [c['name'].casefold()]+[a.casefold() for a in c.get('aliases',[])] for c in candidates):
            candidates.append(external)
            bundle['sources'].update(external['sources'])
    requirements,requirement_notes=question_requirements(comparison_query)
    with st.expander('후보·지도 비교',expanded=bool(saved)):
        candidate=None
        if candidates:
            labels=['전체 보기']+[c['name'] for c in candidates]
            if st.session_state.get('research_candidate_source') not in labels:st.session_state.research_candidate_source='전체 보기'
            chosen=st.selectbox('후보 선택 · 지도와 조건 함께 보기',labels,key='research_candidate_source')
            candidate=next((c for c in candidates if c['name']==chosen),None)
        if context.get('facility_scope',{}).get('facilities'):
            factories,overview,details=st.tabs(['공장 · 내부 거점','지도 · 조건 비교','대체 기업 · 제품 근거'])
        else:
            overview,details,factories=st.tabs(['지도 · 조건 비교','대체 기업 · 제품 근거','공장 · 내부 거점'])
        with factories:
            from .facility_scope import render_facility_scope
            render_facility_scope(context['query'],facility_id)
        with overview:
            if network is not None:
                from .research_map import render_research_map
                answer=saved['search']['text'] if saved else ''
                if candidate:
                    map_col,condition_col=st.columns([1.8,1],gap='medium')
                    with map_col:render_research_map(network,context['query'],answer,candidates,selected_candidate=candidate['name'])
                    with condition_col:
                        with st.container(border=True):
                            st.markdown('**'+candidate['name']+' · 조건 비교**')
                            st.caption(candidate.get('origin','등록 자료 후보'))
                            if candidate.get('origin'):
                                st.write(candidate['reason'])
                                st.caption(candidate['location_note'])
                                st.caption('원문 발췌 일치 확인 · AI의 제품 연결·규격 해석은 검토 필요')
                            evaluations=[e for e in candidate['evaluations'] if e['product'] in candidate['products']]
                            product=st.selectbox('비교 제품',[e['product'] for e in evaluations],key='research_compare_product')
                            evaluation=next(e for e in evaluations if e['product']==product)
                            st.caption(STATUS[evaluation['status']])
                            if not evaluation['checks']:st.info('질문에 구체적인 규격 조건이 없습니다. 같은 제품 종류를 기준으로 찾은 후보입니다.')
                            for check in evaluation['checks']:
                                label={'match':'✓ 일치','mismatch':'× 불일치','unknown':'? 자료 부족'}[check['state']]
                                st.write(label+' · '+check['field'])
                                st.caption(check['reason'])
                            st.caption('고객 인증 · 추가 공급 여력 · 납기: 미확인')
                            with st.expander('제품 근거 확인'):
                                if candidate.get('product_quote'):st.text(candidate['product_quote'])
                                for sid in candidate['source_ids']:source_link(bundle['sources'][sid])
                    from .candidate_flow import render_candidate_flow
                    if not candidate.get('origin'):render_candidate_flow(network,bundle,candidate['name'],product)
                else:render_research_map(network,context['query'],answer,candidates)
            else:st.info('현재 화면에는 지도 데이터가 연결되지 않았습니다.')
        with details:
            if candidates:
                st.caption('등록 자료 후보와 외부 검색 후보 · 고객 인증·세부 규격·공급 여력은 추가 확인')
                if requirements:st.write('인식한 조건: '+' · '.join(LABELS.get(k,k)+' = '+str(v) for k,v in requirements.items()))
                for note in requirement_notes:st.caption(note)
                st.dataframe([{'검토 기업':c['name'],'근거 구분':c.get('origin','등록 자료'),'제품 종류':' / '.join(c['products']),
                    '조건 비교':' / '.join(dict.fromkeys(STATUS[e['status']] for e in c['evaluations'] if e['product'] in c['products']))} for c in candidates],hide_index=True,width='stretch',height=min(250,36*(len(candidates)+1)))
                inspected=candidate or candidates[0]
                with st.expander(inspected['name']+' · 선정 이유와 근거',expanded=bool(candidate)):
                    for evaluation in inspected['evaluations']:
                        st.markdown('**'+evaluation['product']+' · '+STATUS[evaluation['status']]+'**')
                        for check in evaluation['checks']:st.write({'match':'✓ 일치','mismatch':'× 불일치','unknown':'? 자료 부족'}[check['state']]+' · '+check['field']+' · '+check['reason'])
                        for evidence in evaluation['evidence']:
                            st.caption(LABELS.get(evidence['field'],evidence['field'])+': '+str(evidence['value'])+' '+str(evidence.get('unit') or '')+' · 자료 위치: '+evidence['locator'])
                    for sid in inspected['source_ids']:source_link(bundle['sources'][sid])
                st.caption('등록 위치 또는 인용 원문에서 주소·좌표를 확인한 후보만 지도에 표시됩니다. 실제 거래·대체 승인 관계를 의미하지 않습니다.')
            else:st.info('현재 질문과 연결된 등록 대체 후보가 없습니다. 외부 검색 답변을 함께 확인하세요.')
            rejected=[c for c in registered_candidates(bundle,comparison_query,include_rejected=True) if c['excluded']]
            if rejected:
                with st.expander('제외된 기업 · 불일치 또는 과거 자료'):
                    for c in rejected:
                        st.write(c['name'])
                        for e in c['evaluations']:
                            st.caption(e['product']+' · '+STATUS[e['status']])
                            for check in e['checks']:
                                if check['state']!='match':st.write(check['field']+' · '+check['reason'])
    from .research_evaluation import render_evaluation
    with st.expander('추가 자료 · 평가 도구',expanded=False):
        render_evaluation(bundle,key,api_model())
        render_library(bundle)
