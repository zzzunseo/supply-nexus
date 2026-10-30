"""Three-stage company, material and response comparison for published cases."""
import html
import streamlit as st
from .verified_globe import render_evidence_globe
from .overseas_material_case import SOURCE


def reset_verified_steps():
    st.session_state.verified_step=1
    st.session_state.verified_compare='대응 후'


def render_verified_steps(material):
    from .compact_cases import render_compact_case
    render_compact_case('material' if material else 'shipping')
