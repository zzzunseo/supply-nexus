"""Registered target discovery; browsing never creates simulation events."""
import streamlit as st

KINDS={'소재':('resource','product','material'),'기업':('company',),
       '지역·물류':('company','resource','product','material','logistics')}


def target_options(network, category, country=None):
    return sorted((key for key,node in network['entities'].items()
                   if node['kind'] in KINDS[category] and
                   (country is None or node.get('country')==country)),
                  key=lambda key:(network['entities'][key]['name'],key))


def choose_target(state, network, target, use_question=False):
    node=network['entities'].get(target)
    if not node or node['kind'] not in KINDS['지역·물류']:
        raise ValueError('등록된 소재·기업·물류 대상 하나를 선택하세요.')
    state['rr_focus']=target
    state['rr_process']='전체'
    longitude=node.get('lon')
    state['rr_view']='미주' if longitude is not None and longitude<-30 else '유럽' if longitude is not None and longitude<60 else '아시아'
    if use_question:
        # Selection adds a subject only. It never invents duration or severity.
        state['rr_chat_text']=node['name']+' '
        for key in ('rr_function_pending','rr_function_context','rr_function_last','rr_chat_apply_error'):
            state.pop(key,None)
    state['rr_target_finder_open']=False


def close_finder():
    st.session_state.rr_target_finder_open=False


def open_finder():
    st.session_state.rr_target_finder_open=True


def apply_selection(network, use_question):
    target=st.session_state.get('rr_finder_target')
    if target:
        choose_target(st.session_state,network,target,use_question)


@st.dialog('대상 찾기',width='large',on_dismiss=close_finder)
def finder_dialog(network):
    category=st.radio('찾을 대상',list(KINDS),horizontal=True,key='rr_finder_category')
    country=None
    if category=='지역·물류':
        countries=sorted({n.get('country') for n in network['entities'].values()
                          if n['kind'] in KINDS[category] and n.get('country')})
        country=st.selectbox('국가·지역으로 좁히기',[None,*countries],
                             format_func=lambda key:key or '전체 국가·지역',key='rr_finder_country')
        st.caption('국가는 등록 데이터의 소속국 기준입니다. 지역 전체 중단이나 실제 생산지를 뜻하지 않습니다.')
    options=target_options(network,category,country)
    if st.session_state.get('rr_finder_target') not in options:
        st.session_state.rr_finder_target=None
    def label(key):
        if key is None: return '이름을 검색해 선택하세요'
        node=network['entities'][key]
        kind='항만·해협' if node['kind']=='logistics' else '기업' if node['kind']=='company' else '소재'
        return node['name']+' · '+kind+' · '+node.get('country','미확인')
    target=st.selectbox('등록 대상',[None,*options],format_func=label,key='rr_finder_target')
    st.caption(f'등록 대상 {len(options)}개 · 선택창에서 이름 검색 가능')
    if target:
        node=network['entities'][target]
        place=node.get('map_location')
        st.write('선택: '+node['name'])
        if place:
            st.caption('등록 위치: '+place['name']+' · 실제 사건 발생 위치와는 별도입니다.')
        elif node.get('lat') is None or node.get('lon') is None:
            st.caption('검증된 지도 위치 없음 · 연결된 등록 경로에서 확인하세요.')
        st.caption('선택만으로 지도 점수·적용 조건은 바뀌지 않습니다. 질문에 넣으면 대상 이름만 채웁니다.')
    left,right=st.columns(2)
    with left:
        if st.button('지도에서 보기',key='rr_finder_map',disabled=not target,
                     on_click=apply_selection,args=(network,False),width='stretch'):
            st.rerun()
    with right:
        if st.button('질문에 넣기',key='rr_finder_question',disabled=not target,
                     on_click=apply_selection,args=(network,True),type='primary',width='stretch'):
            st.rerun()


def render_target_finder(network):
    st.button('대상 찾기 · 소재 / 기업 / 지역',key='rr_target_find',on_click=open_finder,width='stretch')
    if st.session_state.get('rr_target_finder_open'):
        finder_dialog(network)
