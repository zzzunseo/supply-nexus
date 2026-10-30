"""Paged supply relationship overview with no nested scrollable diagram."""
import html
from urllib.parse import urlsplit
import streamlit as st
from company_relationships import relationship_rows,target_coverage


def open_relationships(target=None):
    state=st.session_state
    state.rr_relationship_open=True
    state.rr_relationship_target=target if target is not None else state.get('rr_focus')
    state.rr_relationship_process='전체'
    state.rr_relationship_direction='전체'
    state.rr_relationship_page=1


def close_relationships():
    st.session_state.rr_relationship_open=False


def reset_page(): st.session_state.rr_relationship_page=1


def select_on_globe(network):
    from .target_finder import choose_target
    target=st.session_state.get('rr_relationship_target')
    if target: choose_target(st.session_state,network,target)
    close_relationships()


def relationship_html(rows,network):
    esc=html.escape
    columns='<div class="rr-rel-head"><span>공급 기업·원료</span><span>소재·물류 경로</span><span>공급받는 기업</span><span>관련 공정·계산 범위</span></div>'
    content=[]
    for row in rows:
        status='계산 제외' if not row['included'] else '제품군 비활성' if not row['active'] else f"경로 최저 공급 {row['fulfillment']:.0f}%" if row['fulfillment'] is not None else '등록 경로'
        via=' → '.join(network['nodes'][k]['name'] for k in row['via'] if k in network['nodes'])
        geography=row['origin']+' → '+(via+' → ' if via else '')+row['destination']
        processes=' · '.join(row['processes']) or '원료·소재 제조'
        link=''
        source=row.get('source')
        if source:
            parsed=urlsplit(source)
            if parsed.scheme in ('https','http') and parsed.netloc and not parsed.username and not parsed.password:
                link=' <a href="'+esc(source,quote=True)+'" target="_blank" rel="noopener noreferrer">근거 ↗</a>'
        def cell(main,sub):
            return '<div><b title="'+esc(main,quote=True)+'">'+esc(main)+'</b><small title="'+esc(sub,quote=True)+'">'+esc(sub)+'</small></div>'
        content.append('<div class="rr-rel-row">'+cell(row['supplier'],row['origin'])+
                       cell(row['material'],geography)+cell(row['recipient'],row['destination'])+
                       '<div><b title="'+esc(processes,quote=True)+'">'+esc(processes)+'</b><small>'+esc(status)+' · '+esc(row['basis'])+link+'</small></div></div>')
    return '<div class="rr-rel-grid">'+columns+''.join(content)+'</div>'


@st.dialog('공급 흐름 · 기업 연결 한눈에 보기',width='large',on_dismiss=close_relationships)
def relationship_dialog(network,result):
    with st.container(key='rr_relationship_view'):
        options=[None,*sorted((k for k,n in network['entities'].items() if n['kind']=='company'),key=lambda k:network['nodes'][k]['name'])]
        current=st.session_state.get('rr_relationship_target')
        if current and current not in options and current in network['entities']: options.append(current)
        if current not in options: st.session_state.rr_relationship_target=None
        cols=st.columns([2,1,1.25])
        with cols[0]: target=st.selectbox('기준 기업·선택 대상',options,key='rr_relationship_target',format_func=lambda k:network['nodes'][k]['name'] if k else '전체 공급망',on_change=reset_page,placeholder='전체 공급망 · 기업 이름 검색')
        with cols[1]: process=st.selectbox('관련 공정',['전체',*network['processes']],key='rr_relationship_process',on_change=reset_page)
        with cols[2]: direction=st.selectbox('연결 방향',['전체','공급받는 경로','공급하는 경로'],key='rr_relationship_direction',on_change=reset_page,disabled=not target)
        rows=relationship_rows(network,result,target,process,direction)
        st.session_state.rr_relationship_rows=rows
        if target:
            coverage=target_coverage(network,target)
            st.caption(coverage['status']+' · '+coverage['reason'])
        pages=max(1,(len(rows)+3)//4)
        if st.session_state.get('rr_relationship_page',1)>pages: st.session_state.rr_relationship_page=1
        page=st.session_state.get('rr_relationship_page',1)
        if rows: st.html(relationship_html(rows[(page-1)*4:page*4],network))
        else: st.info('이 조건에 맞는 등록 공급 경로가 없습니다. 다른 공정·연결 방향을 선택하세요.')
        footer=st.columns([1,2,1.5])
        with footer[0]: st.number_input('페이지',1,pages,key='rr_relationship_page')
        with footer[1]: st.caption(f'전체 {len(rows)}개 경로 · {page}/{pages}페이지 · 한 화면에 4개씩 표시\n\n공급 방향은 왼쪽 → 오른쪽입니다. 지역·경유지는 등록 가정이며 실제 항로와 다를 수 있습니다.')
        with footer[2]:
            if st.button('지구본에서 선택',disabled=not target,on_click=select_on_globe,args=(network,),width='stretch'):
                st.rerun()
        st.caption('공급관계 근거와 용도 기반 가정을 구분합니다. 비활성 제품군·계산 제외 경로도 표시하며 실제 계약·물량 확인을 뜻하지 않습니다.')
