"""Compact claim-to-source navigation for the three representative cases."""
import streamlit as st

SOURCES = {
    'fire': [
        ('화재 발생 근거', 'AKM 공식 안내 · 2020-10-30',
         '노베오카 공장 화재 및 진화 경과', '안내 본문',
         'https://www.akm.com/jp/ja/about-us/news/information/20201030-information/'),
        ('대체 칩 채택 근거', 'RME ADI-2 DAC 공식 매뉴얼',
         '해당 제품의 AKM → ESS 칩 변경 기록', '매뉴얼 4쪽 · 개정판은 내용 검색',
         'https://www.rme-audio.de/download/adi2dacr_e.pdf#page=4'),
    ],
    'material': [
        ('소재 전환 근거', 'Freescale PCN 16152 · NXP 보관',
         '지정 제품의 금 23μm → PdCu 20μm 변경과 검증',
         '문서 내 Au / PdCu / Qualification 검색',
         'https://www.nxp.com/docs/en/product-change-notice/PCN16152.htm'),
    ],
    'shipping': [
        ('우회 결정 근거', 'Maersk 공식 운항 안내 · 2023-12-18',
         '홍해 위험에 따른 희망봉 우회 발표',
         'PDF 내 Cape of Good Hope 검색',
         'https://www.maersk.com/~/media_sc9/maersk/local-information/files/asia-pacific/cambodia/overview/181223-temporary-vessel-diversion.pdf'),
    ],
}


def render_case_sources(case):
    with st.container(border=True):
        st.markdown('**핵심 근거 · 이 자료부터 확인하세요**')
        for col, (claim, title, supports, locator, url) in zip(st.columns(len(SOURCES[case])), SOURCES[case]):
            with col:
                st.markdown('**'+claim+'**')
                st.caption(title)
                st.write(supports)
                st.caption('찾을 위치: '+locator)
                st.link_button(claim+' 원문 열기 ↗', url, width='stretch')
