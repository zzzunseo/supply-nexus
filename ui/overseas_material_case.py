"""Location-backed material conversion, scoped to its published change notice."""
import streamlit as st
import plotly.graph_objects as go

OVERSEAS='소재 대체 · Freescale 말레이시아 금 → PdCu 와이어 (2014)'
SOURCE='https://www.nxp.com/docs/en/product-change-notice/PCN16152.htm'


def render_overseas_material_case():
    st.subheader('말레이시아 조립사업장 · 금 → PdCu 와이어 전환')
    st.caption('Freescale PCN 16152 · NXP 보관 공식 자료 / 발표 2014-06-24 / 효력일 2014-09-22')
    left,right=st.columns([2,1])
    with left:
        from .verified_globe import render_evidence_globe
        render_evidence_globe('material')
        st.caption('공식 문서에 명시된 도시의 개략 대표점입니다. 공장 출입구·정밀 좌표 또는 소재 공급사의 위치를 뜻하지 않습니다.')
    with right:
        st.markdown('**적용 공정 · 패키징의 와이어 본딩**')
        st.write('대상: SPC5676·SPC5642·SPC5644·SPC5645 계열의 문서 지정 제품')
        st.markdown('**기존 소재 → 대체 소재**')
        st.write('금(Au) 23μm → 팔라듐 코팅 구리(PdCu) 20μm')
        st.markdown('**변경 이유**')
        st.write('원재료 비용 상승 부담 완화와 공급 안정성 확보')
        st.markdown('**검증 상태 · 완료**')
        st.write('공식 문서에 Qualification Status: COMPLETED 명시. 검증 자료 공개일은 2014-06-02입니다.')
        st.markdown('[원문 · PCN 16152]('+SOURCE+')')
        st.info('같은 조립사업장의 자재 변경입니다. 공장 이전이나 국가 간 우회 운송 사례가 아닙니다.')
    st.graphviz_chart('''digraph conversion {
        rankdir=LR;bgcolor="transparent";
        node [shape=box,style="rounded,filled",fillcolor="#102638",fontcolor="#E6F0FF",color="#31576D",fontname="Malgun Gothic",fontsize=15];
        edge [color="#4fe4db",penwidth=2];
        a [label="기존 · 금(Au) 23μm"];
        b [label="제품·공정 검증 완료"];
        c [label="대체 · PdCu 20μm"];
        d [label="KLM 조립사업장 · 지정 제품"];
        a -> b -> c -> d;
    }''')
    st.caption('확인 범위는 지정 제품의 자재 변경과 검증 완료·효력일입니다. 실제 출하량·절감률·모든 제품의 전면 전환을 의미하지 않습니다.')
