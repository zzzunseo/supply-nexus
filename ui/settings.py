"""Settings dialog orchestration."""
import streamlit as st
from .settings_tabs import (
    render_assumptions_tab,
    render_backbone_tab,
    render_upstream_tab,
    render_locations_tab,
    render_materials_tab,
    render_logistics_tab,
    render_comparison_tab,
)


def close_settings():
    st.session_state.rr_settings_open = False


@st.dialog('소재·경로·모델 설정', width='large', on_dismiss=close_settings)
def settings(network):
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(['제품군·가정', '44개 원본 경로', '추가 소재·출처', '실제 위치·근거', '확장 소재·우회', '물류 병목', '계산 비교'])
    with tab1:
        render_assumptions_tab(network)
    with tab2:
        render_backbone_tab(network)
    with tab3:
        render_upstream_tab(network)
    with tab4:
        render_locations_tab(network)
    with tab5:
        render_materials_tab(network)
    with tab6:
        render_logistics_tab(network)
    with tab7:
        render_comparison_tab(network)
    if st.button('닫고 화면 반영', type='primary', width='stretch'):
        close_settings()
        st.rerun()
