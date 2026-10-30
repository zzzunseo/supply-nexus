"""Regression harness for retained panel components, NOT the current application entrypoint.

The production detail workspace no longer embeds these panels. Keep their engine,
state and article contracts exercised without pretending they are current UI journeys.
Current application journeys are tested by test_detail_workspace/test_demo and AI tests.
"""
import streamlit as st
from ui.state import initialize
from ui.resources import load_css
from resilience_data import build_network
from ui.logistics import apply_saved_settings
from ui.quick_detours import load_quick_profiles
from ui.panels import render_header, render_left_panel, render_center_panel, render_right_panel
st.set_page_config(layout='wide')
st.markdown('<style>'+load_css()+'</style>',unsafe_allow_html=True)
initialize()
network=build_network()
for key,values in st.session_state.get('rr_overrides',{}).items():
    if key in network['nodes']:network['nodes'][key].update(values)
apply_saved_settings(network,st.session_state.get('rr_port_detours',{}),st.session_state.get('rr_route_settings',{}))
load_quick_profiles(network)
st.session_state.rr_network=network
render_header()
left,center,right=st.columns([1,2.4,1.4])
with left:result=render_left_panel(network)
with center:render_center_panel(network,result)
with right:render_right_panel(network,result)
