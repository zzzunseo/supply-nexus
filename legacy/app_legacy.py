"""Streamlit host for the supply-chain globe UI. Run: streamlit run app.py."""
from pathlib import Path
import json
import streamlit as st
from legacy.data_loader import load_demo
from legacy.globe_component import render_dashboard
from legacy.theme import TOKENS, shell_stylesheet
from legacy.simulation import load_model, build_simulation_payload, normalize_options
from legacy.simulation.dialogue import handle_request, public_state
from legacy.simulation.issues import validate_facilities

st.set_page_config(page_title='공급망 디지털 트윈', page_icon='🌐', layout='wide')
st.markdown(shell_stylesheet(), unsafe_allow_html=True)

@st.cache_data
def get_data(source_stamp):
    return load_demo(Path(__file__).resolve().parents[1] / 'data' / 'demo.json')

data_folder = Path(__file__).resolve().parents[1] / 'data'
evidence_file = data_folder / 'evidence.json'
data = get_data(((data_folder / 'demo.json').stat().st_mtime_ns,
                 evidence_file.stat().st_mtime_ns if evidence_file.exists() else 0))
model = load_model(Path(__file__).resolve().parents[1] / 'data' / 'simulation_demo.json', data)
data['scenarios'] += model.get('additional_scenarios', [])
facilities_file = data_folder / 'facilities.json'
data['facilities'] = validate_facilities(json.loads(facilities_file.read_text(encoding='utf-8'))['facilities'], data) if facilities_file.exists() else []
request = st.session_state.get('supply_chat_request')
dialogue = st.session_state.get('supply_dialogue', {})
if request:
    previous_revision = (dialogue.get('applied_selection') or {}).get('revision')
    dialogue = handle_request(request, data, model, dialogue,
                              normalize_options(st.session_state.get('supply_selection')))
    st.session_state['supply_dialogue'] = dialogue
    applied = dialogue.get('applied_selection')
    if applied and applied['revision'] != previous_revision:
        st.session_state['supply_selection'] = {**st.session_state.get('supply_selection', {}), **applied}
if dialogue.get('custom_scenario'):
    data['scenarios'].append(dialogue['custom_scenario'])
options = normalize_options(st.session_state.get('supply_selection'))
data['simulation'] = build_simulation_payload(data, model, options)
data['assistant'] = public_state(dialogue)
data['ui_selection'] = st.session_state.get('supply_selection', {})
data['tokens'] = TOKENS
result = render_dashboard(data)
