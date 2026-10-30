"""Compact public facility evidence and internal-site review."""
import streamlit as st
from news.facility_scope import facility_scope,facility_map

def render_facility_scope(query,selected_id=''):
    scope=facility_scope(query,selected_id)
    if not scope['facilities']:
        st.info('이번 질문에 연결된 공장별 자료가 없습니다. 기업 제품 자료를 모든 공장에 적용하지 않습니다.');return
    st.caption(scope['scope_status'])
    st.caption('지도는 도시·지역 개략점입니다. 정확한 공장 위치가 아니며 같은 지역의 공장은 한 점에 묶었습니다.')
    left,right=st.columns([1.5,1])
    with left:
        from .night_globe import component
        component()(data=facility_map(scope),key='facility_review_globe',width='stretch',height=410)
    with right:
        selected=scope['selected']
        if selected:
            st.markdown('**'+selected['name']+'**')
            st.write(' → '.join(selected['products']))
            st.caption(selected['operator']+' · '+selected['as_of'])
            st.caption(selected['note'])
            st.markdown('**같은 기업·그룹의 다른 거점**')
            for option in scope['internal_options']:
                st.write(option['name']+' · '+option['status'])
                if option['same_region']:st.caption('같은 지역: 광역 재난·전력·용수 위험이 함께 발생할 수 있습니다.')
        else:st.info('입력칸 아래에서 검토할 공장을 선택하세요. 기업 이름만으로 피해 공장을 정하지 않습니다.')
        st.caption('여유 생산능력 · 고객 인증 · 전환 소요기간 · 피해율: 미확인')
    with st.expander('공장별 제품·공정과 공개 근거'):
        for f in scope['facilities']:
            st.markdown('**'+f['name']+' · '+f['city']+'**')
            st.write(' / '.join(f['products']))
            st.caption(f['as_of']+' · '+f['note'])
            for sid in f['source_ids']:
                source=scope['sources'][sid]
                st.link_button(source['title'],source['url'])
                st.caption(source['as_of']+' · '+source['locator'])
        st.caption('일부 생산거점만 등록되어 있습니다. 목록에 없다는 이유로 공장이나 대체 가능성이 없다고 판단하지 않습니다.')
