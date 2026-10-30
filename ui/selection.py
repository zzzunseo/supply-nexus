"""Single selection state shared by the globe and selection box."""


def select_globe_event(state, entities):
    selected = state.get('rr_globe_click', {}).get('picked')
    if isinstance(selected, str) and selected in entities:
        state['rr_focus'] = selected


def select_globe_process(state):
    """Keep a concrete globe process and the detailed flow in one selection."""
    if state['rr_process'] != '전체':
        state['rr_flow_process'] = state['rr_process']
        state['rr_flow_picker'] = state['rr_process']
    else:
        state['rr_flow_picker'] = None


def select_flow_process(state, picker_key='rr_flow_process'):
    process = state[picker_key]
    if process is None:
        state[picker_key] = state['rr_flow_process']
        return
    state['rr_flow_process'] = process
    state['rr_process'] = process
