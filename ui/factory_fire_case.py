"""Factory damage and documented downstream component substitution."""
import streamlit as st
from .verified_globe import render_evidence_globe

FIRE='공장 피해·기업 대체 · AKM 화재 → RME의 ESS 칩 전환'
FIRE_SOURCE='https://www.akm.com/jp/ja/about-us/news/information/20201030-information/'
MANUAL='https://www.rme-audio.de/download/adi2dacr_e.pdf'


def render_factory_fire():
    from .compact_cases import render_compact_case
    render_compact_case('fire')
