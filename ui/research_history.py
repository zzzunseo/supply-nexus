"""Bounded session-only replay. Never persists API credentials or claims a new search."""
from copy import deepcopy
from datetime import datetime,timezone
from html import escape
import json
from news.external_research import safe_url

def snapshot(report):
    search=report.get('search',{})
    sources=[]
    for source in search.get('sources',[]):
        try:url=safe_url(source.get('url'))
        except ValueError:continue
        sources.append(dict(title=str(source.get('title') or url),url=url))
    return dict(id=str(report.get('context_id','')),question=str(report.get('question','')),answer=str(search.get('text','')),
        sources=sources,reviewed_at=str(report.get('reviewed_at') or datetime.now(timezone.utc).isoformat()),
        kind='저장된 검색 답변 · 새로운 검색 아님 · 정확도 검증 완료 아님')

def remember(history,report):
    record=snapshot(report)
    if not record['answer'] or not record['sources']:return history
    return [record]+[r for r in history if r['id']!=record['id']][:4]

def export_html(record):
    refs=''.join('<li><a href="'+escape(safe_url(s['url']),quote=True)+'">'+escape(s['title'])+'</a></li>' for s in record['sources'])
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>공급망 검토 기록</title><style>body{font:17px/1.7 sans-serif;max-width:900px;margin:40px auto;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere}small{color:#555}</style><h1>'+escape(record['question'])+'</h1><small>'+escape(record['kind']+' · '+record['reviewed_at'])+'</small><pre>'+escape(record['answer'])+'</pre><h2>출처</h2><ul>'+refs+'</ul></html>'

def render_history():
    import streamlit as st
    history=st.session_state.get('research_answer_history',[])
    if not history:return
    with st.expander('최근 답변 다시 보기 · 추가 API 호출 없음'):
        record=st.selectbox('보관된 질문',history,format_func=lambda r:r['question'],key='research_history_choice')
        st.caption(record['kind']+' · '+record['reviewed_at'])
        with st.container(height=240):st.text(record['answer'])
        for source in record['sources']:st.link_button(source['title'],source['url'])
        st.download_button('시연용 답변 파일 저장 · HTML',export_html(record),file_name='supply-review.html',mime='text/html',key='research_replay_html')
        st.caption('최근 5개는 현재 세션에 보관됩니다. 새로고침·서버 재시작에 대비하려면 파일로 저장하세요. 파일 본문은 오프라인에서도 열 수 있으며 출처 링크 접속에는 인터넷이 필요합니다.')
