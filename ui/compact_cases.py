"""One clear takeaway per stage; evidence remains directly accessible."""
import streamlit as st
from .verified_globe import render_evidence_globe
from .case_sources import render_case_sources

CASES={
 'fire': dict(title='공장 화재 → 다른 기업의 칩 채택',
   subtitle='AKM → RME ADI-2 DAC → ESS',
   stages=[('기존 부품','AKM AK4493','RME ADI-2 DAC에 사용하던 칩'),('공급 차질','AKM 공장 화재','2020년 화재로 기존 칩 조달에 제약 발생'),('대응','ESS ES9028Q2M','RME가 해당 제품의 칩을 변경')],
   before='AKM AK4493',limit='특정 제품의 변경 사례 · 즉시 호환이나 전체 고객의 대체를 뜻하지 않음',
   detail='RME 매뉴얼은 초기 AK4490, 이후 AK4493 및 ESS ES9028Q2M의 채택 이력을 설명합니다. 주요 기능은 거의 유지되지만 칩 의존 기능에는 차이가 있습니다. 지도는 부품 채택 관계이며 실제 운송 경로가 아닙니다. 피해량·매출 손실·전환 물량은 미확인입니다.'),
 'material':dict(title='원재료 비용 부담 → 검증 후 소재 전환',
   subtitle='Freescale · 말레이시아 조립사업장 · 2014',
   stages=[('기존 소재','금(Au) 23μm','패키징 · 와이어 본딩'),('전환 이유','비용·조달 부담','원재료 비용 부담 완화와 공급 안정성 확보'),('대응','PdCu 20μm','제품 검증 후 팔라듐 코팅 구리로 변경')],
   before='금(Au) 23μm',limit='PCN 지정 제품의 변경 · 모든 금 와이어를 바로 대체하는 것은 아님',
   detail='Freescale PCN 16152의 SPC5676·SPC5642·SPC5644·SPC5645 계열 중 지정 제품입니다. 검증 자료 공개 2014-06-02, 변경 통지 2014-06-24, 효력일 2014-09-22. 같은 조립사업장 안의 자재 변경이며 공장 이전이나 운송 경로가 아닙니다. 절감률·출하량·생산 회복률은 산정하지 않습니다.'),
 'shipping':dict(title='홍해 통항 위험 → 희망봉 우회',
   subtitle='Maersk · 공식 운항 안내 · 2023-12-18',
   stages=[('기존 방향','홍해·수에즈','기존 통항 방향'),('위험','홍해 안전 위험','선박 운항 조정 필요'),('대응','희망봉 우회','아프리카 남단으로 통항 방향 변경')],
   before='홍해·수에즈',limit='선사의 우회 발표 · 특정 반도체 화물이나 생산 피해는 미확인',
   detail='공식 안내의 대상 예는 Maersk Hanoi·Maersk Athabasca입니다. 지도는 우회 방향의 개략도이며 실제 선박 항적이 아닙니다. 반도체 고객, 화물 종류, 공급 중단률과 운송 지연일을 임의로 연결하지 않습니다.')}


def render_compact_case(case):
    d=CASES[case]
    st.session_state.setdefault('verified_step',1)
    step=st.session_state.verified_step
    st.subheader(d['title'])
    st.caption(d['subtitle'])
    for i,col in enumerate(st.columns(3),1):
        with col:st.button(str(i)+' · '+['기존 상태','변화 원인','대응 결과'][i-1],key='verified_step_'+str(i),width='stretch',type='primary' if step==i else 'secondary',on_click=lambda n=i:st.session_state.update(verified_step=n))
    after=False
    if step==3:
        after=st.segmented_control('대응 전후',['대응 전','대응 후'],key='verified_compare',default='대응 후',required=True,width='stretch')=='대응 후'
    left,right=st.columns([2,1])
    with left:render_evidence_globe(case,step,after)
    with right:
        label,focus,note=d['stages'][step-1]
        if step==3 and not after:focus=d['before'];note='대응 이전 상태'
        st.caption(label)
        st.subheader(focus)
        st.write(note)
        st.caption(d['limit'])
        render_case_sources(case)
        if step<3:st.button('다음 단계 →',key='verified_next',type='primary',width='stretch',on_click=lambda:st.session_state.update(verified_step=step+1))
        if step>1:st.button('← 이전 단계',key='verified_previous',width='stretch',on_click=lambda:st.session_state.update(verified_step=step-1))
    with st.expander('자세히 보기 · 적용 범위와 한계',expanded=False):
        st.write(d['detail'])
