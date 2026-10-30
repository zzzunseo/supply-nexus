"""Article-first UI. Review never calls the scenario parser or changes scopes."""
import html
import json
import streamlit as st

from news.article_review import article_draft, candidate_ids, review_article, CLAIM_TYPES, SCOPES
from news.article_fields import FIELD_LABELS, SUPPLY_STATUSES
from news.article_briefing import article_briefing, briefing_markdown
from news.article_mock import attach_mock_commentary
from news.article_exposure import process_exposure
from .article_map import open_article_map, article_map_dialog
from .article_llm import render_llm_suggestion, render_mock_loader


def close_article_dialog():
    st.session_state.rr_article_dialog = False


def close_article_details():
    st.session_state.rr_article_details = False


def open_article_dialog():
    st.session_state.rr_article_dialog = True
    st.session_state.rr_article_details = False
    st.session_state.rr_article_map_open = False


def open_article_details():
    st.session_state.rr_article_details = True
    st.session_state.rr_article_dialog = False
    st.session_state.rr_article_map_open = False



@st.dialog('기사 원문 검토', width='large', on_dismiss=close_article_dialog)
def article_input(network):
    st.caption('1. 원문 입력 → 2. 대상·근거 문장 검토. 이름 언급은 피해 확인이 아닙니다. URL을 자동으로 읽거나 사실을 독립 검증하지 않습니다.')
    render_mock_loader(network)
    draft = st.session_state.get('rr_article_draft')
    if not draft:
        with st.form('rr_article_source_form'):
            title = st.text_input('기사 제목 · 선택', key='rr_article_title', max_chars=600)
            url = st.text_input('원문 URL · 선택', key='rr_article_url', placeholder='https://…')
            body = st.text_area('기사 본문', key='rr_article_body', max_chars=20000, height=170,
                                placeholder='검토할 기사 본문을 붙여넣으세요.')
            if st.form_submit_button('원문에서 대상 후보 찾기', width='stretch'):
                try:
                    st.session_state.rr_article_draft = article_draft(network,title,body,url)
                    for key in ('rr_llm_suggestion', 'rr_llm_applied', 'rr_llm_provenance'):
                        st.session_state.pop(key, None)
                    for key in ('rr_article_target','rr_article_quote','rr_article_type','rr_article_scope'):
                        st.session_state.pop(key,None)
                    for key in list(st.session_state):
                        if key.startswith('rr_fact_'):
                            st.session_state.pop(key,None)
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
        return
    st.write(draft['headline'])
    with st.expander('검토 중인 고정 원문 보기'):
        st.text(draft['body'])
    if st.button('새 원문 입력 · 후보 다시 찾기'):
        st.session_state.rr_article_draft = None
        st.rerun()
    st.markdown('**원문에서 찾은 언급 후보**')
    if draft['mentions']:
        st.dataframe([dict(원문표현=hit['mention'], 연결후보=' / '.join(c['name'] for c in hit['candidates']),
                           문맥=hit['excerpt']) for hit in draft['mentions']], hide_index=True, height=140)
    else:
        st.info('등록된 이름과 일치하는 언급을 찾지 못했습니다. 대상 미연결 상태로 보관할 수 있습니다.')
    st.caption('참고·비교 대상으로 등장한 이름일 수도 있습니다. 사건 대상인지는 근거 문장을 읽고 직접 구분하세요.')
    render_llm_suggestion(network, draft)
    if st.session_state.get('rr_llm_applied') == draft['id']:
        mode = '모의 LLM' if st.session_state.get('rr_llm_provenance',{}).get('method') == 'mock_assisted_human_review' else 'LLM'
        st.info(mode+' 초안이 채워졌습니다. 사건 대상·범위와 각 인용의 의미를 확인한 뒤 저장하세요. 점수는 자동 변경되지 않습니다.')
    with st.form('rr_article_review_form'):
        target = st.selectbox('원문을 검토해 연결할 대상', [None,*candidate_ids(draft)], key='rr_article_target',
                              format_func=lambda key: '선택하지 않음 · 연결 보류' if key is None else network['nodes'][key]['name'])
        quote = st.text_area('대상 언급을 포함하는 원문 근거 문장', key='rr_article_quote', height=90,
                            placeholder='위 본문에서 그대로 복사하세요. 원문과 일치하는지 확인합니다.')
        claim_type = st.selectbox('원문을 읽고 분류한 사건', CLAIM_TYPES, key='rr_article_type')
        scope = st.selectbox('원문에서 확인한 영향 범위', SCOPES, key='rr_article_scope')
        fields = {}
        with st.expander('날짜·시설·제품·공급 영향 구조화 · 선택', expanded=False):
            st.caption('모르는 항목은 비워두세요.  \n날짜는 연·월·일이 모두 있는 원문만 YYYY-MM-DD로 입력합니다.  \n기사 제목·발행일 표기도 본문에 포함해 붙여넣어 주세요.  \n인용 일치 검사는 의미나 사실의 검증이 아닙니다.')
            for field, label in FIELD_LABELS.items():
                if field == 'supply_status':
                    value = st.selectbox(label, SUPPLY_STATUSES, key='rr_fact_'+field)
                else:
                    value = st.text_input(label+' · 미기재는 미확인', key='rr_fact_'+field,
                                          max_chars=500, placeholder='YYYY-MM-DD' if field.endswith('_date') else '원문에 명시된 이름·제품·등급')
                evidence = st.text_input(label+' 원문 근거', key='rr_fact_'+field+'_quote',
                                         placeholder='본문의 문장을 그대로 복사하세요.')
                fields[field] = {'value': value, 'quote': evidence}
        st.caption('공급 감소율·기간·고객 피해는 자동으로 확정하지 않습니다.  \n저장해도 기존 시나리오와 점수는 그대로입니다.  \n검토 결과는 현재 세션에 보관되며 파일로 내려받을 수 있습니다.')
        if st.form_submit_button('검토 결과 저장 · 경로 확인', type='primary', width='stretch'):
            try:
                # Review the immutable submitted draft; editing it requires rematching.
                current = st.session_state.rr_article_draft
                if current['id'] != draft['id']:
                    raise ValueError('원문이 변경됐습니다. 먼저 대상 후보를 다시 찾아주세요.')
                st.session_state.rr_article_review = review_article(network,draft,target,quote,claim_type,scope,fields=fields)
                provenance = st.session_state.get('rr_llm_provenance')
                if provenance and provenance['draft_id'] == draft['id']:
                    st.session_state.rr_article_review['extraction'] = dict(provenance)
                    attach_mock_commentary(st.session_state.rr_article_review, st.session_state.get('rr_llm_suggestion'))
                close_article_dialog()
                st.rerun()
            except ValueError as error:
                st.error(str(error))


@st.dialog('기사 검토 결과 · 근거', width='large', on_dismiss=close_article_details)
def article_details():
    review = st.session_state.rr_article_review
    article = review['article']
    st.subheader(article['headline'])
    if review.get('extraction',{}).get('method') == 'mock_conversation_preview':
        st.caption('대화에서 불러온 가상 기사·모의 초안입니다. 사용자 검토·실제 모델 호출·독립 사실 검증을 수행하지 않았습니다.')
    elif review.get('extraction',{}).get('method') == 'mock_assisted_human_review':
        st.caption('Codex가 작성한 모의 LLM 응답을 사용자가 검토한 가상 사례입니다. 실제 모델 호출·기사 사실 검증을 수행하지 않았습니다.')
    elif review.get('extraction'):
        st.caption('LLM 초안을 사용자가 검토·저장한 기록입니다. 모델: '+review['extraction']['model']+' · 독립 사실 검증·기사 자동 수집은 수행하지 않았습니다.')
    else:
        st.caption('붙여넣은 원문에 대한 사용자 검토입니다. 독립 사실 검증·기사 자동 수집·LLM 해석 결과가 아닙니다.')
    source, paths, unknown = st.tabs(['원문·검토 내용','등록 경로·근거','미확인·추가 확인'])
    with source:
        if article['url']:
            st.link_button('입력한 원문 URL 열기',article['url'])
        else:
            st.warning('출처 URL이 없어 원문 출처 확인이 필요합니다.')
        st.write('검토 대상: ' + (review['target_name'] or '미연결'))
        st.write('사용자 분류: ' + review['claim_type'] + ' / 범위: ' + review['scope'])
        st.text(review['excerpt'] or '검토 근거 문장 미지정')
        st.caption(review['warning'])
        st.markdown('**구조화한 기사 내용**')
        for key,label in FIELD_LABELS.items():
            claim=review.get('fields',{}).get(key,{})
            st.write(label+': '+(claim.get('value') or '미확인'))
            if claim.get('quote'):
                st.text(claim['quote'])
        st.caption('사용자가 원문을 대조한 값입니다. 독립 검증 또는 자동 의미 판정 결과가 아닙니다.')
        with st.expander('붙여넣은 본문 보기'):
            st.text(article['body'])
    with paths:
        st.warning('아래는 등록 데이터의 관련 경로입니다. 이 기사로 고객 피해나 현행 품목 계약이 확인됐다는 뜻은 아닙니다.')
        if not review['routes']:
            st.info('등록된 관련 경로를 찾지 못했습니다. 영향 없음으로 해석하지 않습니다.')
        for row in review['routes']:
            with st.expander(row['supplier']+' → '+row['material']+' → '+row['recipient']):
                st.write('관련 공정: ' + (' · '.join(row['processes']) or '미등록'))
                st.write('관계 근거 구분: ' + row['basis'])
                st.write(row['impact_status'])
                st.caption('모델 적용 범위: '+('기본 소재' if row['scope']=='core' else '선택 제품군·확장 소재')+' · 기사 검토로 활성화하지 않음')
                st.caption('소재 점수 대상' if row['scoring_included'] else '소재 점수 제외 · 참고/장비 관계')
                if row['source']:
                    st.link_button('관계·제품 근거 원문',row['source'],key='rr_article_source_'+row['id'])
                else:
                    st.caption('개별 경로의 출처 미등록')
    with unknown:
        for item in review['unknowns']:
            st.write('• ' + item)
        st.info('공장 사건을 기업 전체 중단으로, 이름 언급을 고객 피해로 자동 변환하지 않습니다. 현재 단계는 분석 검토이며 계산 후보를 생성하지 않습니다.')
    st.download_button('검토 기록 저장',json.dumps(review,ensure_ascii=False,indent=2).encode('utf-8'),
                       file_name='article-review.json',mime='application/json')


def render_article_summary(network):
    review = st.session_state.get('rr_article_review')
    if not review:
        st.markdown('<div class="rr-article-empty">기사 한 건을 검토해 보세요.<br>원문 내용 → 관련 등록 경로 → 근거와 미확인 사항을 구분합니다.</div>',unsafe_allow_html=True)
        return
    escape = html.escape
    note = article_briefing(review)
    st.caption(note['method'])
    st.markdown('<div class="rr-section-label">이슈 요약</div>',unsafe_allow_html=True)
    st.markdown('<div class="rr-article-summary"><b>'+escape(note['headline'])+'</b><p>'+escape(note['context'])+'</p></div>',unsafe_allow_html=True)
    st.markdown('<div class="rr-section-label">현재 상태 · 기사 기준</div>',unsafe_allow_html=True)
    st.markdown('<div class="rr-explanation"><p>'+escape(note['status'])+'</p></div>',unsafe_allow_html=True)
    exposure=process_exposure(review)
    st.markdown('<div class="rr-section-label">'+escape(exposure['title'])+'</div>',unsafe_allow_html=True)
    primary=exposure['direct'] or exposure['equipment']
    for row in primary[:2]:
        st.markdown('<div class="rr-article-summary"><b>'+escape(row['path'])+'</b><p>'+escape(row['effect'])+'</p></div>',unsafe_allow_html=True)
    if not primary:
        st.caption('등록 공급관계 기반의 직접 노출 후보 없음 · 아래 참고·가정 관계와 구분해 확인하세요.')
    st.caption(exposure['limit'])
    if exposure['rows']:
        with st.expander('기업·공정별 연결 전체 · 근거 구분',expanded=False):
            for label,group in [('공급관계 기반 소재 경로',exposure['direct']),
                                ('장비·점수 제외 공급관계',exposure['equipment']),
                                ('참고·가정 경로 · 직접 피해로 사용하지 않음',exposure['other'])]:
                if group:
                    st.markdown('**'+label+'**')
                    st.dataframe([{'소재·품목':r['material'],'기업':r['recipient'],
                                   '직접 공정':' · '.join(r['processes']) or '미등록',
                                   '검토 방향':r['effect'],'관계 근거':r['basis']} for r in group],hide_index=True)
            st.caption('개별 출처 링크는 원문·등록 경로·근거 보기에서 확인할 수 있습니다.')
    st.markdown('<div class="rr-section-label">해설</div>',unsafe_allow_html=True)
    st.markdown('<div class="rr-explanation"><p>'+escape(note['interpretation'])+'</p><p>'+escape(note['route_note'])+'</p></div>',unsafe_allow_html=True)
    if note['caution']:
        st.warning(note['caution'])
    with st.expander('원문 근거 · 추가 확인', expanded=False):
        st.markdown('<div class="rr-article-quote">'+escape(review['excerpt'] or '근거 문장 미지정 · 연결 보류')+'</div>',unsafe_allow_html=True)
        st.caption('사건일: '+note['event_date']+' · 시설: '+note['facility']+' · 제품: '+note['product'])
        for item in note['checks']:
            st.write('• '+item)
        st.caption(note['score_note'])
        st.download_button('발표용 검토 메모 저장', briefing_markdown(review).encode('utf-8'),
                           file_name='article-briefing.md', mime='text/markdown')
    st.button('원문·등록 경로·근거 보기',key='rr_article_details_button',on_click=open_article_details,width='stretch')
    st.button('기사 관련 경로 지도 보기',key='rr_article_map_button',on_click=open_article_map,
              disabled=not bool(review['routes']),width='stretch')



def render_article_input_button(network):
    st.button('기사 붙여넣기 · 원문 검토',key='rr_article_open',on_click=open_article_dialog,width='stretch',type='primary')
    if st.session_state.get('rr_article_dialog'):
        article_input(network)
    elif st.session_state.get('rr_article_details'):
        article_details()
    elif st.session_state.get('rr_article_map_open'):
        article_map_dialog(network)
