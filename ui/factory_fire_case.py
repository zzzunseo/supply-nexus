"""Factory damage and documented downstream component substitution."""
import streamlit as st
from .verified_globe import render_evidence_globe

FIRE='공장 피해·기업 대체 · AKM 화재 → RME의 ESS 칩 전환'
FIRE_SOURCE='https://www.akm.com/jp/ja/about-us/news/information/20201030-information/'
MANUAL='https://www.rme-audio.de/download/adi2dacr_e.pdf'


def render_factory_fire():
    st.session_state.setdefault('verified_step',1)
    step=st.session_state.verified_step
    st.subheader('AKM 공장 화재 → 고객 제품의 대체 칩 채택')
    st.caption('2020-10-20 · 일본 노베오카 반도체 공장 화재 / 고객 제품: 독일 RME ADI-2 DAC')
    st.markdown('**실제 대응 기록** · 공장 화재 → 고객의 부품 조달 제약 → 다른 제조사의 칩 채택')
    for i,col in enumerate(st.columns(3),1):
        with col:st.button(str(i)+'　'+['기업·부품 연결','공장 피해와 영향','대체 전후 비교'][i-1],key='verified_step_'+str(i),width='stretch',type='primary' if step==i else 'secondary',on_click=lambda n=i:st.session_state.update(verified_step=n))
    after=False
    if step==3:
        after=st.segmented_control('대체 전후',['대응 전','대응 후'],key='verified_compare',default='대응 후',required=True,width='stretch')=='대응 후'
    left,right=st.columns([2,1])
    with left:
        render_evidence_globe('fire',step,after)
        st.caption('연결선은 고객 제품의 부품 채택 관계입니다. 실제 선박 항적·직거래 계약·칩 제조지를 뜻하지 않습니다. AKM은 피해 공장의 도시, RME·ESS는 공식 연락거점 권역의 개략 대표점입니다.')
    with right:
        if step==1:
            st.subheader('기존 기업·부품 연결')
            st.markdown('**AKM AK4493 → RME ADI-2 DAC**')
            st.write('AKM의 D/A 변환 칩을 사용하던 해외 고객 제품입니다. RME 매뉴얼은 초기 AK4490, 이후 AK4493 채택 이력을 설명합니다.')
            st.info('원재료가 아니라 반도체 부품과 공급 기업의 대체 사례입니다.')
        elif step==2:
            st.subheader('실제 공장 화재의 영향')
            st.markdown('**노베오카 공장 화재 → AD/DA 칩 생산설비 피해 → 부품 조달 제약**')
            st.write('화재 발생일은 2020-10-20입니다. RME는 공식 매뉴얼에서 AKM 생산설비 화재 때문에 기존 칩 기반 제품을 중단하거나 다른 칩을 사용해야 했다고 설명합니다.')
            st.caption('공장 전체 붕괴나 RME의 실제 매출·생산 감소율을 확인한 것은 아닙니다. 실제 확인된 표현은 화재에 따른 설비 피해와 공급 제약입니다.')
        else:
            st.subheader('다른 기업의 칩으로 전환')
            st.markdown('**'+('ESS ES9028Q2M 채택' if after else 'AKM AK4493 사용')+'**')
            st.write('RME는 해당 공식 매뉴얼에 기록된 ADI-2 DAC 버전에서 ESS ES9028Q2M을 채택해 제품 제공을 이어갔다고 설명합니다. 주요 기능은 거의 동일하게 유지되지만 필터 등 칩 의존 기능에는 차이가 있습니다.')
            st.caption('자동으로 꽂아 바꾸는 호환 부품이라는 의미는 아닙니다. 특정 RME 제품에서 확인된 설계·부품 전환이며 다른 AKM 고객 전체로 일반화하지 않습니다.')
        st.markdown('[AKM 공식 화재 안내]('+FIRE_SOURCE+')')
        st.markdown('[RME 공식 매뉴얼 · 4쪽]('+MANUAL+')')
        if step<3:st.button('다음 단계 →',key='verified_next',type='primary',width='stretch',on_click=lambda:st.session_state.update(verified_step=step+1))
        if step>1:st.button('← 이전 단계',key='verified_previous',width='stretch',on_click=lambda:st.session_state.update(verified_step=step-1))
    if step==3:
        st.dataframe([{'항목':'부품 제조사','대체 전':'AKM','대체 후':'ESS Technology'},
            {'항목':'DAC 칩','대체 전':'AK4493','대체 후':'ES9028Q2M'},
            {'항목':'고객 제품','대체 전':'RME ADI-2 DAC','대체 후':'같은 제품 계열 유지 · 칩 의존 기능 차이'},
            {'항목':'근거','대체 전':'RME 매뉴얼의 기존 채택 이력','대체 후':'동일 매뉴얼의 화재 대응·변경 설명'}],hide_index=True)
        st.success('공식 자료로 확인되는 연결: 공장 화재 → 고객의 공급 제약 → 다른 기업의 칩 채택')
    with st.expander('사실·추론 구분과 확인 범위'):
        st.caption('원문 재확인: 2026-10-29 · 과거 사건·제품 변경 기록이며 현재 모든 제품의 부품 구성을 뜻하지 않습니다.')
        st.dataframe([
            {'주장':'노베오카 공장 화재','근거':'AKM 공식 안내 · 2020-10-30','확인 범위':'발생 10월 20일 / 진화 10월 24일 · 진화일은 생산 복구일이 아님','출처':FIRE_SOURCE},
            {'주장':'고객 영향과 ESS 칩 전환','근거':'RME 공식 매뉴얼 · 4쪽','확인 범위':'ADI-2 DAC의 기존 칩·공급 제약·대체 칩 채택 기록','출처':MANUAL},
        ],hide_index=True,column_config={'출처':st.column_config.LinkColumn('공식 원문')})
        st.write('**앱이 보여주는 것:** 공식 기록을 기업·부품 연결과 전후 비교로 구성합니다. 앱이 대체 칩을 발견하거나 호환성을 실험한 결과는 아닙니다.')
        st.write('**추가 확인이 필요한 것:** 정확한 전환일·대체 물량·매출 손실·회복률·직거래 계약·실제 운송 경로. 자료가 없으면 수치나 연결을 확정하지 않습니다.')
        st.markdown('[RME 공식 연락거점](https://rme-audio.de/imprint.html)')
        st.markdown('[ESS 공식 발표 · Milpitas 연락 권역](https://www.esstech.com/essnews/ess-introduces-the-worlds-first-codec-with-hardware-mqa-hi-res-rendering/)')
        st.caption('위치는 개략 표시이며 ESS 칩의 실제 제조·선적 공장이나 RME 제품 조립 공장을 확인한 자료는 아닙니다. 시연에서 피해량·회복률을 임의로 계산하지 않습니다.')
