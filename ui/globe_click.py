"""Bridge visible globe marker clicks to the shared Streamlit selection."""
from pathlib import Path
import streamlit as st
from .selection import select_globe_event


_bridge = st.components.v2.component(
    'globe_marker_click',
    js=Path(__file__).with_suffix('.mjs').read_text(encoding='utf-8'),
)


def render_globe_click(network):
    def picked():
        select_globe_event(st.session_state, network['entities'])
    _bridge(
        key='rr_globe_click', height=0,
        data={'ids': list(network['entities']), 'focus': st.session_state.rr_focus},
        on_picked_change=picked,
    )
