"""Dedicated article map dialog; never reads or changes simulation outputs."""
from pathlib import Path
import streamlit as st

from article_map import article_map_data, build_article_globe, select_article_route


_route_bridge = st.components.v2.component('article_route_click',
    js=Path(__file__).with_name('article_route_click.mjs').read_text(encoding='utf-8'))


def close_article_map():
    st.session_state.rr_article_map_open = False


def open_article_map():
    st.session_state.rr_article_map_open = True
    st.session_state.rr_article_dialog = False
    st.session_state.rr_article_details = False
    st.session_state.rr_article_route = None


def change_article_route():
    st.session_state.rr_article_route=st.session_state.rr_article_route_picker


@st.dialog('기사 관련 등록 경로 지도',width='large',on_dismiss=close_article_map)
def article_map_dialog(network):
    review=st.session_state.get('rr_article_review')
    if not review:
        st.info('먼저 기사 원문을 검토하세요.')
        return
    payload=article_map_data(network,review)
    rows={r['id']:r for r in payload['routes']}
    mapped=[r for r in payload['routes'] if r['mapped']]
    numbers={r['id']:i for i,r in enumerate(mapped,1)}
    selected=st.session_state.get('rr_article_route')
    if selected not in rows:
        selected=None
        st.session_state.rr_article_route=None
    st.caption(review['article']['headline']+' · 기사 관련 등록 관계 탐색 · 시나리오 점수와 별도')
    st.warning('점과 선은 등록된 기업·사업장의 개략 연결입니다. 본사도 포함되며 기사 속 사고 장소·실제 운송 경로·고객 피해를 뜻하지 않습니다.')
    st.session_state.rr_article_route_picker=selected
    st.selectbox('기사 관련 경로 선택', [None,*rows],key='rr_article_route_picker',
        format_func=lambda key: '전체 관련 경로 · ◇ 선택점 또는 목록에서 선택' if key is None else
            str(numbers.get(key,'미표시'))+' · '+rows[key]['label'],
        on_change=change_article_route,placeholder='전체 관련 경로 · 경로를 선택하세요')
    globe,detail=st.columns([2.4,1],gap='medium',wrap=False)
    with globe:
        st.markdown('<div class="rr-article-legend"><span style="color:#67E3F0">━ 공급관계 근거</span>　<span style="color:#96A7BB">┄ 참고 관계</span>　<span style="color:#B7A1EE">┄ 추가 가정</span></div>',unsafe_allow_html=True)
        with st.container(key='rr_article_map_area'):
            st.plotly_chart(build_article_globe(payload,selected),key='rr_article_globe',
                height=340,width='stretch',theme=None,config=dict(displayModeBar=False,scrollZoom=True,topojsonURL='/app/static/'))
            def picked():
                select_article_route(st.session_state,set(numbers))
            _route_bridge(key='rr_article_route_click',height=0,
                data={'ids':list(numbers),'focus':selected},on_picked_change=picked)
        st.caption(f'지도 표시 {len(mapped)}개 / 등록 관련 경로 {len(rows)}개 · ◇ 선택점을 누르면 오른쪽에 연결 근거 표시')
        if len(mapped)<len(rows):
            st.info('좌표가 없거나 동일 위치인 경로는 선으로 표시하지 않습니다. 목록에서 해당 경로와 이유를 확인할 수 있습니다.')
    with detail:
        row=rows.get(selected)
        st.markdown('**선택 경로 · 연결 근거**')
        if not row:
            st.write('지도 선 중앙의 ◇ 선택점 또는 위 목록에서 경로를 선택하세요.')
            st.caption('기사에 기업 이름이 등장했다는 이유로 고객 피해를 확정하지 않습니다.')
        elif 'kind' not in row:
            st.write(row['label'])
            st.warning(row['reason'])
        else:
            st.write(row['label'])
            st.write('근거 구분: '+row['basis'])
            st.caption(row['reason'])
            st.write('관련 공정: '+(' · '.join(row['processes']) or '미등록'))
            st.caption('실제 고객 영향 · 해당 품목의 현행 계약 미확인')
            if row['source']:
                st.link_button('관계·제품 근거 원문',row['source'],key='rr_article_map_source_'+row['id'])
            else:
                st.caption('이 경로의 출처 미등록')
            if row['mapped']:
                with st.expander('등록 위치 근거 · 사고 위치와 구분'):
                    for index,anchor in enumerate(row['anchors']):
                        st.write(anchor['company']+' · '+anchor['name'])
                        st.link_button('위치 출처',anchor['source'],key=f'rr_map_location_{index}')
                        st.link_button('좌표 출처',anchor['coordinate_source'],key=f'rr_map_coordinate_{index}')
            elif row.get('coincident'):
                st.warning('양 끝의 등록 좌표가 같습니다. 별도 운송선을 만들어내지 않습니다.')
            else:
                st.warning('위치 미등록: '+' · '.join(row['missing']))
        with st.expander('기사 원문 근거'):
            st.text(payload['article_quote'] or '인용 미지정')
            st.caption('사용자가 검토한 원문 · 독립 사실 검증 아님')
    if not rows:
        st.info('관련 등록 경로가 없습니다. 실제 영향이 없다는 뜻은 아닙니다.')
