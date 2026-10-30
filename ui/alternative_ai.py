"""Optional AI explanation next to deterministic product evidence comparisons."""
import json
import os
import streamlit as st
from .api_credentials import api_key, render_credentials, api_model, render_model
from news.alternative_ai import comparison_context,explain_alternatives
from product_comparison import STATUS,field_text,LABELS

TOPICS={'process_conditions':'공정 조건 대조','qualification':'고객 승인·샘플 평가','capacity':'공급 여력·납기 확인','logistics':'출하·취급 조건','source_freshness':'현행 규격·자료 시점'}


def render_alternative_ai(data,family,requirements,records,results):
    st.divider();st.subheader('AI · 검토 후보의 선정 근거와 차이')
    st.caption('선택 제품의 공개 데이터와 비교 결과를 AI에 전달합니다. 코드 비교 판정과 AI 해석을 나란히 확인합니다.')
    available=[r for r in records if not r['legacy']]
    order={'meets_documented':0,'insufficient':1,'mismatch':2}
    ordered=sorted(available,key=lambda r:order.get(results[r['id']]['status'],3))
    options=[r['id'] for r in ordered];by_id={r['id']:r for r in available}
    selection_signature=json.dumps([family,requirements],sort_keys=True)
    if st.session_state.get('alternative_selection_signature')!=selection_signature or any(k not in options for k in st.session_state.get('alternative_records',[])):
        st.session_state.alternative_selection_signature=selection_signature
        st.session_state.alternative_records=options[:4]
    chosen=st.multiselect('AI 해설 대상 · 최대 6개',options,key='alternative_records',max_selections=6,
        format_func=lambda k:by_id[k]['supplier']+' · '+by_id[k]['name'])
    st.caption('선택 항목만 비교합니다. 산업 전체 후보의 최적 순위가 아닙니다. 조건 변경 시 해설 대상도 다시 확인하세요.')
    goal=st.text_area('검토 목적·우선순위',value='기존 공정 조건의 차이와 추가 확인할 항목을 중심으로 설명해 주세요.',max_chars=2000,height=80,key='alternative_goal')
    if not chosen:
        st.info('해설할 제품을 하나 이상 선택하세요.');return
    context=comparison_context(data,family,requirements,chosen,goal)
    saved=st.session_state.get('alternative_result')
    if saved and saved['context_id']!=context['id']:
        st.session_state.pop('alternative_result',None);saved=None
    server_key=os.environ.get('SUPPLY_AI_API_KEY') or os.environ.get('OPENAI_API_KEY','')
    with st.expander('AI API 설정',expanded=not bool(server_key or st.session_state.get('alternative_key'))):
        render_credentials('alternative')
        render_model('alternative')
        st.caption('클릭당 1회 유료 요청 · 공개 제품 데이터·입력 조건·목적을 전송합니다. 키는 다운로드·파일에 포함하지 않습니다. 자동 재시도하지 않습니다.')
    key=api_key()
    if st.button('AI로 후보 근거·차이 설명',key='alternative_run',type='primary',disabled=not bool(key),width='stretch'):
        st.session_state.pop('alternative_result',None);saved=None
        try:
            with st.spinner('제품별 근거를 대조해 해설하고 있습니다…'):
                saved=explain_alternatives(context,key,api_model())
            st.session_state.alternative_result=saved
        except ValueError as error:st.error(str(error))
    if not key:st.info('현재 비교표는 API 없이 작동합니다. 키를 설정하면 실제 AI 해설을 실행할 수 있습니다.')
    if not saved:return
    st.caption('실제 API 해설 · 모델 '+saved['provenance']['model']+' · 사용자 검토 필요')
    st.write(saved['overview']);st.caption(saved['validation'])
    facts={k:v for r in context['records'] for k,v in r['facts'].items()}
    def references(refs):
        rows=[]
        for ref in refs:
            record_id,field_key=ref.split('::',1)
            fact=facts[ref]
            rows.append({'제품':by_id[record_id]['name'],'항목':LABELS.get(field_key,field_key),'공개 값':field_text(fact),
                '자료 위치':fact['locator'],'공식 원문':fact['url']})
        st.dataframe(rows,hide_index=True,column_config={'공식 원문':st.column_config.LinkColumn('공식 원문')})
    for item in saved['candidates']:
        st.markdown('**'+by_id[item['record_id']]['supplier']+' · '+by_id[item['record_id']]['name']+'**')
        st.caption('코드 판정: '+STATUS[item['status']]);st.write(item['explanation']);references(item['evidence_refs'])
    with st.expander('추가로 확인할 사항',expanded=False):
        for item in saved['next_checks']:
            st.markdown('**'+TOPICS[item['topic']]+'**');st.write(item['reason']);references(item['evidence_refs'])
    st.download_button('AI 해설·입력 조건·근거 내려받기',json.dumps(dict(context=context,result=saved),ensure_ascii=False,indent=2),
        file_name='alternative-comparison-review.json',mime='application/json',key='alternative_download')
