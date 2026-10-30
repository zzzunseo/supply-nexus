"""Live response evaluation records, separate from mocked software tests."""
import json
import streamlit as st
from news.external_research import make_research_context,research_external,suggest_mode

QUESTIONS={
    '희토류·관세':'희토류 관세가 생기면 반도체 공정에 어떤 영향이 있어?',
    '세리아·원산지':'중국산이 아닌 산화세륨 CMP 연마재 대체 공급사를 찾아줘.',
    'ArF·복합조건':'ArF 액침 Positive 포토레지스트 대체 공급사를 비교해줘.',
    'HF·농도와순도':'고순도 불화수소 수용액 농도 49%, 총 금속 1 ppb 이하 대체 공급사를 검토해줘.',
    '기업·직경':'SUMCO의 300mm PW 웨이퍼 공급 중단을 가정하면 대체 검토 기업은?',
    '가스·순도':'NF3 순도 99.999% 이상을 공급할 대체 기업은?',
    '가스·불순물':'NF3 수분 1 ppmv 이하인 대체 공급사는?',
    '범위 불명':'희토류 공급이 중단되면 어느 공정에 영향이 있어?',
    '미등록 기업':'Soitec의 SOI 웨이퍼 공급 중단을 가정하면 영향과 대체 후보는?',
    '항로':'말라카 해협이 막히면 우회 후보는?',
    '잘못된 전제':'SUMCO가 오늘 모든 공장을 폐쇄했다는 가정으로 실제 고객 피해율을 알려줘.'}


def render_evaluation(bundle,key,model):
    with st.expander('실제 AI 평가 · 질문별 실행 및 기록'):
        st.caption('실제 호출 결과와 사용자 원문 검토를 저장합니다. 자동 검사는 응답 형식·출처 유무만 확인하며 답변 정확도 점수가 아닙니다. 질문당 검색 요청 1회와 사용료가 발생할 수 있습니다.')
        case=st.selectbox('평가 질문',list(QUESTIONS),key='eval_case')
        query=QUESTIONS[case];st.write(query)
        records=st.session_state.setdefault('research_evaluations',{})
        if st.button('이 질문 실제 평가 실행',disabled=not bool(key),key='eval_run'):
            try:
                with st.spinner('실제 API 평가 중…'):
                    context=make_research_context(bundle,query,suggest_mode(query))
                    result=research_external(context,key,model,simple=True)
                records[case]=dict(question=query,result=result,review={},status='원문 검토 대기')
            except ValueError as error:records[case]=dict(question=query,error=str(error),status='실행 실패')
        record=records.get(case)
        if record:
            if 'error' in record:st.error(record['error'])
            else:
                with st.container(height=220):st.text(record['result']['search']['text'])
                for s in record['result']['search']['sources']:st.link_button(s['title'],s['url'])
                st.caption('각 항목은 원문을 직접 확인한 뒤 판정하세요.')
                for criterion in ('질문 요구 충족','주장과 원문 일치','규격·대체 후보 적절','가정·사실·미확인 구분'):
                    record['review'][criterion]=st.selectbox(criterion,['미검토','통과','실패','해당 없음'],key='eval_'+case+'_'+criterion)
                record['status']='원문 검토 대기' if '미검토' in record['review'].values() else '검토 완료'
        if records:
            st.dataframe([{'질문':name,'상태':r['status']} for name,r in records.items()],hide_index=True)
            st.download_button('실제 평가 기록 내려받기',json.dumps(records,ensure_ascii=False,indent=2),file_name='live-ai-evaluation.json',mime='application/json')
