"""Run with: python -m streamlit run app.py"""
import json
from pathlib import Path
import streamlit as st
from legacy.globe import build_globe, VIEWS
from legacy.theme import stylesheet

st.set_page_config(page_title='반도체 공급망 | 지구본', page_icon='🌐', layout='wide')
st.markdown(stylesheet(), unsafe_allow_html=True)


@st.cache_data
def load_data():
    return json.loads((Path(__file__).resolve().parents[1] / 'data' / 'demo.json').read_text(encoding='utf-8'))


data = load_data()
with st.sidebar:
    st.markdown('### 공급망 제어 패널')
    st.caption('조건을 바꾸고 연결의 변화를 살펴보세요.')
    scenario_name = st.selectbox('시나리오 선택', [s['name'] for s in data['scenarios']])
    region = st.selectbox('지역 선택 · 시작 시점', list(VIEWS))
    st.caption('지역 선택은 카메라 시작 위치를 바꿉니다. 경로는 공정 선택으로 필터링합니다.')
    st.divider()
    all_processes = st.toggle('전체 공정 경로 보기', value=False)
    with st.expander('지도 표시 설정'):
        labels = st.toggle('거점 이름 표시', value=True)
        grid = st.toggle('위도·경도 격자', value=True)
    if st.button('시점 초기화', use_container_width=True):
        st.session_state['camera_revision'] = st.session_state.get('camera_revision', 0) + 1
    st.divider()
    st.caption('데이터 모드: UI 검증용 예시')
    st.caption('실제 거래·점유율·공정 가용률은 연결되지 않았습니다.')

st.markdown('<div class="eyebrow">반도체 공급망 · 디지털 트윈</div>', unsafe_allow_html=True)
st.title('공급망을, 하나의 지구 위에.')
st.caption('공정별 공급 흐름과 거점 중단을 살펴보는 인터랙티브 지구본')
process = st.radio('공정 선택', data['processes'], index=2, horizontal=True)
scenario = next(s for s in data['scenarios'] if s['name'] == scenario_name)
affected = set(scenario['affected'])
edges = [e for e in data['edges'] if all_processes or process in e['processes']][:15]
visible_ids = {e[k] for e in edges for k in ('from', 'to')}
nodes = [n for n in data['nodes'] if n['id'] in visible_ids]
blocked = [e for e in edges if e['from'] in affected or e['to'] in affected]
lookup = {n['id']: n for n in data['nodes']}

a, b, c = st.columns(3)
a.metric('표시 거점', f'{len(nodes):02d}', help='현재 공정 필터에 포함된 예시 거점 수')
b.metric('표시 경로', f'{len(edges):02d}', help='최대 15개 경로를 표시합니다.')
c.metric('중단 경로 · 예시', f'{len(blocked):02d}', help='중단 예시 거점에 직접 연결된 경로 수. 공정 점수가 아닙니다.')

globe_tab, detail_tab = st.tabs(['지구본', '상세 데이터'])
with globe_tab:
    left, right = st.columns([3.6, 1.2], gap='large')
    with left:
        st.markdown(f'#### {"전체 공정" if all_processes else process} 공급 흐름')
        st.markdown('<div class="legend"><span class="normal">● 정상 · 실선</span>　'
                    '<span class="alert">× 중단 · 점선</span>　｜　드래그하여 회전 · 스크롤하여 확대</div>', unsafe_allow_html=True)
        fig = build_globe(nodes, edges, affected, region, labels, grid, st.session_state.get('camera_revision', 0))
        st.plotly_chart(fig, use_container_width=True, theme=None, key='supply_globe',
                        config={'scrollZoom': True, 'displaylogo': False, 'displayModeBar': False})
        st.caption('구면 위 대권 경로를 표시합니다. 반대편 경로는 지구 뒤로 가려지며 회전하면 나타납니다.')
    with right:
        st.markdown('#### 현재 시나리오')
        with st.container(border=True):
            st.write(f'**{scenario_name}**')
            st.caption(scenario['description'])
            st.write('**선택 공정**')
            st.write(process if not all_processes else '전체 8개 공정')
            st.write('**표시 품목**')
            for item in dict.fromkeys(e['item'] for e in edges):
                st.caption(f'• {item}')
        st.markdown('#### 주요 경로')
        for e in edges[:5]:
            is_blocked = e in blocked
            with st.container(border=True):
                st.caption('× 중단 예시' if is_blocked else '● 정상 예시')
                st.write(f"{lookup[e['from']]['name']} → {lookup[e['to']]['name']}")
                st.caption(e['item'])
        if len(edges) > 5:
            st.caption('나머지 경로는 상세 데이터 탭에서 확인할 수 있습니다.')

with detail_tab:
    st.subheader('현재 표시 중인 공급 경로')
    rows = [{'출발 거점': lookup[e['from']]['name'], '도착 거점': lookup[e['to']]['name'],
             '품목': e['item'], '공정': ', '.join(e['processes']),
             '상태': '중단 예시' if e in blocked else '정상 예시', '출처': '가상 예시 · 확인 필요'} for e in edges]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.download_button('현재 경로 JSON 다운로드', json.dumps(rows, ensure_ascii=False, indent=2),
                       file_name='supply_routes.json', mime='application/json')
    st.subheader('표시 거점')
    st.dataframe([{'거점': n['name'], '국가': n['country'], '위도': n['lat'], '경도': n['lon'],
                   '역할': n['role']} for n in nodes], use_container_width=True, hide_index=True)

st.caption(data['notice'])
