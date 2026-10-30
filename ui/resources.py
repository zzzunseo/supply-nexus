"""Project resources and cached network loading."""
from pathlib import Path
import streamlit as st
from resilience_data import build_network

ROOT = Path(__file__).resolve().parents[1]
def load_css():
    """Read the stylesheet on each rerun so an imported module cannot retain old CSS."""
    return (ROOT / "resilience.css").read_text(encoding="utf-8")


EXAMPLES = {
    '일본 PR 중단': '일본 포토레지스트 공급 100% 중단 30일',
    '중국 희토류 통제': '중국 희토류 수출 통제 30일',
    '미국 석영 중단': '미국 고순도 석영 공급 100% 중단 60일',
    '우크라이나 네온': '우크라이나 네온 공급 100% 중단 30일',
    '갈륨 관세 20%': '중국 갈륨 관세 20% 30일',
    '독일 NF3 중단': '독일 NF3 공급 중단 60일',
    '일본 세정액 차질': '일본 과산화수소 공급 감소 50% 60일',
    'CMP 공급사 차질': '인테그리스 구리 CMP 공급 중단 60일',
    'DAF 우회 비교': '레조낙 DAF 공급 중단 90일',
    'PGMEA 중단': '간토화학 PGMEA 공급 중단 60일',
    '헬륨 부족': '헬륨 공급 감소 50% 30일',
    '말라카 해협 봉쇄': '말라카 해협 봉쇄 30일',
    '수에즈 운하 봉쇄': '수에즈 운하 봉쇄 30일',
    '가오슝항 폐쇄': '가오슝항 폐쇄 30일',
}


@st.cache_data
def cached_network(stamp):
    return build_network()
