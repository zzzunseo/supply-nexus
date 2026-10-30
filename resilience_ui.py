"""Main Plotly dashboard orchestration. Run with app.py."""
import streamlit as st
from ui.resources import ROOT, load_css, cached_network
from ui.state import initialize
from ui.logistics import apply_saved_settings
from ui.quick_detours import load_quick_profiles


def main():
    st.set_page_config(page_title='SUPPLY NEXUS · 반도체 공급망 분석', page_icon='🌐', layout='wide', initial_sidebar_state='collapsed')
    if st.query_params.get('view')=='mobile':
        from ui.mobile_viewer import render_mobile_viewer
        render_mobile_viewer()
        return
    st.markdown('<style>' + load_css() + '</style>', unsafe_allow_html=True)
    initialize()
    data_sources = (
        ROOT / 'data/demo.json',
        ROOT / 'data/verified_locations.json',
        ROOT / 'data/materials_extension.json',
        ROOT / 'resilience_materials.py',
        ROOT / 'resilience_logistics.py',
        ROOT / 'resilience_data.py',
        ROOT / 'resilience_locations.py',
        ROOT / 'simulation/evidence.py',
        ROOT / 'evidence_review.py',
        ROOT / 'data/evidence_review.json',
    )
    network = cached_network(tuple(p.stat().st_mtime_ns for p in data_sources))
    for k, values in st.session_state.get('rr_overrides', {}).items():
        if k in network['nodes']:
            network['nodes'][k].update(values)
    apply_saved_settings(network, st.session_state.get('rr_port_detours', {}),
                         st.session_state.get('rr_route_settings', {}))
    load_quick_profiles(network)
    st.session_state.rr_network = network
    mode = st.session_state.get('rr_workspace_mode', '시연 모드')
    if mode == '시연 모드':
        # Keep hidden detailed-mode widget values through Streamlit cleanup.
        for key in list(st.session_state):
            if key.startswith('rr_'):
                st.session_state[key] = st.session_state[key]
        from ui.demo import render_demo
        render_demo(network)
        return
    from ui.detail_workspace import render_detail_workspace
    render_detail_workspace(network)


if __name__ == "__main__":
    main()
