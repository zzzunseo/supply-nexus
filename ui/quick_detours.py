"""Three directly accessible switches in the settings panel; no settings dialog needed."""
import streamlit as st

from simulation.quick_detours import default_quick_profiles, read_profiles, quick_setting


LABELS = {'logistics:kaohsiung': '가오슝 → 기룽',
          'logistics:malacca': '말라카 → 롬복',
          'logistics:suez': '수에즈 → 희망봉'}


def load_quick_profiles(network):
    try:
        st.session_state.rr_quick_profiles = read_profiles(network)
        st.session_state.rr_quick_profile_error = ''
    except (ValueError, OSError, TypeError, KeyError) as error:
        st.session_state.rr_quick_profiles = default_quick_profiles(network)
        st.session_state.rr_quick_profile_error = str(error)


def switch_key(cp):
    return 'rr_quick_' + cp.replace(':', '_')


def change_quick_detour(cp, current):
    enabled = st.session_state[switch_key(cp)]
    value = quick_setting(current, st.session_state.rr_quick_profiles[cp], enabled)
    st.session_state.setdefault('rr_port_detours', {})[cp] = value


def render_quick_detours(network):
    profiles = st.session_state.rr_quick_profiles
    with st.container(key='rr_quick_detours'):
        st.markdown('<div class="rr-quick-title">항만 우회 <span>저장된 가정 적용</span></div>', unsafe_allow_html=True)
        for cp, label in LABELS.items():
            current = network['port_detours'][cp]
            key = switch_key(cp)
            # Also reflect changes made in the detailed editor or JSON import.
            st.session_state[key] = bool(current['enabled'])
            value = current if current['enabled'] else profiles[cp]
            with st.container(key='rr_detour_' + cp.split(':')[1]):
                summary = f"가정: {value['max_fraction']*100:g}% 우회 · +{value['extra_days']}일 · 운임 +{value['cost_rate']*100:g}%"
                st.toggle(label, key=key, on_change=change_quick_detour, args=(cp, current), help=summary)
        if st.session_state.rr_quick_profile_error:
            st.caption('저장된 보통값을 읽지 못해 기본 가정을 표시합니다. 상세 설정에서 다시 저장해 주세요.')
