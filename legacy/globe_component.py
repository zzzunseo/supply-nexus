"""Stable Streamlit v2 boundary; bundled local JS contains all rendering assets."""
from pathlib import Path
import streamlit.components.v2 as components
import streamlit as st

FRONTEND = Path(__file__).parent / 'frontend'
_dashboard = components.component(
    'semiconductor_globe',
    html='<div class="supply-root"></div>',
    css=(FRONTEND / 'style.css').read_text(encoding='utf-8'),
    js=(FRONTEND / 'dist' / 'globe-ui.js').read_text(encoding='utf-8'),
    isolate_styles=True,
)


def _selection_changed():
    # Callbacks run before the rerun, so the engine sees the new controls without
    # a one-interaction delay. Component state is owned by this browser session.
    value = st.session_state.get('supply_globe_dashboard')
    selection = getattr(value, 'selection', None)
    if selection is None and isinstance(value, dict):
        selection = value.get('selection')
    if selection:
        st.session_state['supply_selection'] = selection


def render_dashboard(data: dict):
    return _dashboard(
        data=data,
        key='supply_globe_dashboard',
        default={'selection': None, 'chat_request': None},
        on_selection_change=_selection_changed,
        on_chat_request_change=_chat_request_changed,
        width='stretch',
        height='content',
    )


def _chat_request_changed():
    value = st.session_state.get('supply_globe_dashboard')
    request = getattr(value, 'chat_request', None)
    if request is None and isinstance(value, dict):
        request = value.get('chat_request')
    if isinstance(request, dict):
        st.session_state['supply_chat_request'] = request
