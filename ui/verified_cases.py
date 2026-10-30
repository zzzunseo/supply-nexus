"""Published response cases, isolated from hypothetical impact calculations."""
import streamlit as st
import plotly.graph_objects as go
from .overseas_material_case import OVERSEAS,render_overseas_material_case
from .factory_fire_case import FIRE,render_factory_fire

NEON='네온 국산화 · 포스코 → TEMC → SK하이닉스 (2022)'
REDSEA='홍해 사태 · Maersk 희망봉 우회 (2023–2024)'
COPPER='소재 대체 · TI 금(Au) → 구리(Cu) 본딩 와이어'


def render_copper_case():
    st.subheader('TI · 금 와이어에서 구리 와이어로 전환')
    st.caption('소재 자체의 대체 · 반도체 패키징 / 공식 발표일 2012-05-23')
    left,right=st.columns([2,1])
    with left:
        st.graphviz_chart('''digraph substitution {
          rankdir=LR; bgcolor="transparent"; nodesep=0.4; ranksep=0.45;
          node [shape=box,style="rounded,filled",fontname="Malgun Gothic",fontsize=16,
                fontcolor="#E6F0FF",color="#34566A",fillcolor="#102638",margin="0.20,0.18"];
          edge [color="#4fe4db",penwidth=2];
          gold [label="기존 소재\\n금(Au) 와이어",color="#E7BE67"];
          qualification [label="전환 조건\\n공정·신뢰성 검증"];
          copper [label="대체 소재\\n구리(Cu) 와이어",color="#4fe4db"];
          packaging [label="적용 공정\\n패키징·와이어 본딩"];
          gold -> qualification -> copper -> packaging;
        }''')
        st.markdown('**전환 이유**')
        st.write('금 가격의 상승과 변동이 전환의 초기 동인이었습니다. TI는 연구·개발과 제품 검증을 거쳐 구리 와이어를 양산에 적용했다고 발표했습니다.')
        st.info('이 그림은 소재·공정 전환도입니다. 특정 공급사·공장·운송 경로를 확인한 지도는 아닙니다.')
    with right:
        st.metric('구리 와이어 적용 제품 누적 출하 · 당시 발표','약 65억 개')
        st.caption('2012년 5월 발표 기준의 제품 수입니다. 대체 비율·절감률·현재 출하량을 뜻하지 않습니다.')
        st.markdown('**공식 자료에서 확인되는 내용**')
        st.write('금의 대체재로 구리 채택 / 여러 제품의 검증 / 실제 양산·출하')
        st.markdown('[TI 공식 발표 · 2012-05-23](https://www.ti.com/about-ti/newsroom/news-releases/2012/2012-05-23-texas-instruments-drives-adoption-of-copper-wire-bonding-technology--delivering-nearly-6-5-billion-units-to-customers.html)')
        st.markdown('[후속 양산 확대 발표 · 2014-10-14](https://www.ti.com/about-ti/newsroom/news-releases/2014/2014-10-14-ti-demonstrates-leadership-in-copper-wire-bonding-technology-with-more-than-22b-units-shipped.html)')
    st.markdown('**사례의 의미** · 소재 대체는 구매처 변경만으로 끝나지 않으며, 공정 적합성과 제품 신뢰성 검증을 거쳐야 합니다.')
    st.caption('모든 금 와이어 제품에 구리를 즉시 적용할 수 있다는 의미는 아닙니다. 현재 앱의 다른 소재에 이 대체 관계를 자동 적용하거나 생산 회복률로 환산하지 않습니다.')


def render_representative_picker(cases):
    with st.expander('대표 사례',expanded=True):
        if st.session_state.get('verified_case') in (COPPER,NEON):st.session_state.verified_case=OVERSEAS
        from .verified_steps import reset_verified_steps
        st.selectbox('확인할 사례',['기존 시나리오 보기',FIRE,OVERSEAS,REDSEA],key='verified_case',on_change=reset_verified_steps,
            format_func=lambda v:'가정 시나리오 · 기업·소재 영향 검토' if v=='기존 시나리오 보기' else '물류 우회 · '+v if v==REDSEA else v)



def render_verified_cases(selected):
    if selected=='기존 시나리오 보기':return False
    if selected==FIRE:
        render_factory_fire()
        return True
    from .verified_steps import render_verified_steps
    render_verified_steps(selected in (OVERSEAS,COPPER,NEON))
    return True
