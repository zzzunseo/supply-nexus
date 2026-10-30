"""Small presentation cards with an expandable, downloadable explanation."""
import html
import re
import streamlit as st
from .impact_explanation import build_explanation,explanation_markdown

def short(values,limit=2):
    values=list(dict.fromkeys(values))
    return ' · '.join(values[:limit])+(' 외 '+str(len(values)-limit)+'개' if len(values)>limit else '')


def render_impact_cards(network,case,profile,inspection=None):
    analysis=build_explanation(network,case,profile)
    st.session_state.demo_explanation=analysis
    esc=html.escape
    processes=''.join('<span>'+esc(p)+'</span>' for p in analysis['processes']) or '<span>등록 공정 없음</span>'
    process_detail=short(analysis['companies'])+' · '+short(row['use'] for row in analysis['impacts'])
    candidate=short(c['name'] for c in analysis['candidates'])
    procurement='관세 조건 비교' if analysis['tariff'] else candidate or '선택 제품군 후보 보류'
    if analysis['logistics']:
        port=short(p['original']+' → '+p['alternate'] for p in analysis['ports']) or '등록 우회 후보 없음'
        port_note='동일 공급사 유지 · 화물 취급·운항 확인'
    else:
        port='항만 변경은 별도 검토' if analysis['tariff'] else '항만 변경만으로 해결 불가'
        port_note='원산지·거래 조건별 비용 비교' if analysis['tariff'] else '생산·출하 차질과 운송 차질을 구분'
    st.markdown('''<style>
    .impact-grid{border:1px solid #294a60;border-radius:10px;background:#0b1b2a;overflow:hidden}
    .impact-line{padding:9px 13px;border-bottom:1px solid #21394a;display:grid;grid-template-columns:76px 1fr;gap:9px;align-items:start;font-size:13px;line-height:1.7}
    .impact-line>b{color:#8faec3;font-size:14px;padding-top:1px}.impact-line strong{font-size:15px;color:#e3eef7;font-weight:650}
    .impact-line small{display:block;font-size:13px;color:#8eabbf;margin-top:2px}.impact-chips{display:flex;gap:5px;flex-wrap:wrap}.impact-chips span{padding:2px 8px;border-radius:5px;background:#452b1d;color:#ffd096;border:1px solid #765033;font-size:13px;font-weight:650}
    .impact-line.procurement strong{color:#67e0d4}.impact-line.port strong{color:#8ebeff}
    .impact-budget{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:#21394a}.impact-budget>div{background:#0b1b2a;padding:9px 13px;font-size:13px;color:#d0e0eb}.impact-budget b{font-size:13px;color:#8faec3;display:block;margin-bottom:3px}
    .impact-next{font-size:14px;color:#a9c5d8;padding:7px 2px;border-left:2px solid #ffcf8b;padding-left:9px;line-height:1.7}.impact-next b{color:#ffcf8b}
    </style>''',unsafe_allow_html=True)
    content=(f'<div class="impact-grid"><div class="impact-line"><b>{"비용 연관 공정" if analysis["tariff"] else "우선 검토 공정"}</b><div><div class="impact-chips">{processes}</div><small>{esc(process_detail)}</small></div></div>'
        f'<div class="impact-line procurement"><b>대체 조달</b><div><strong>{esc(procurement)}</strong><small>{"품목·원산지별 비교" if analysis["tariff"] else "제품군 후보 · 고객 승인·공급 여력 별도" if candidate else "추가 제품·적합성 자료 확보"}</small></div></div>'
        f'<div class="impact-line port"><b>물류 대응</b><div><strong>{esc(port)}</strong><small>{esc(port_note)}</small></div></div>'
        f'<div class="impact-budget"><div><b>시간 비교 항목</b>{esc(analysis["time_short"])}</div><div><b>비용 비교 항목</b>{esc(analysis["cost_short"])}</div></div></div>')
    st.markdown(content,unsafe_allow_html=True)
    st.caption('실제 일수·금액은 동일 조건의 일정·견적 확인 후 산정합니다.')
    st.markdown('<div class="impact-next"><b>먼저 확인</b>　'+esc(analysis['first_action'])+'</div>',unsafe_allow_html=True)
    report=explanation_markdown(case,analysis,profile)
    with st.expander('상세 해석 · 시간·비용 · 근거',expanded=False):
        process_tab,response_tab,cost_tab,source_tab=st.tabs(['영향 공정','대응 후보','시간·비용','근거·기록'])
        with process_tab:
            st.caption(analysis['boundary'])
            for row in analysis['impacts']:
                st.markdown(f"**{row['company']} · {row['process']} / {row['material']}**")
                st.write(row['use']+' — '+row['reason'])
            if analysis['equipment']:st.info('장비 도입·증설 일정과 기존 설치 장비의 운전 영향을 구분합니다.')
        with response_tab:
            for row in analysis['candidates']:
                st.markdown(f"**{row['name']} → {row['recipient']}** · {row['material']}")
                st.write(row['condition'])
            if not analysis['candidates']:st.write('현재 선택 범위에서 표시할 제품 근거가 있는 후보가 없습니다. 대체 불가능 판정은 아닙니다.')
            for row in analysis['ports']:
                st.markdown(f"**{row['original']} → {row['alternate']}** · {row['purpose']}")
                st.caption('등록된 경유 가정입니다. 실제 선박 항적·화물 취급·통관·내륙운송 연결은 별도로 확인합니다.')
            if not analysis['logistics'] and analysis['ports']:st.caption('이 항만 정보는 물류 참고입니다. 소재 생산·출하 중단을 우회 운송만으로 해결하지 못합니다.')
        with cost_tab:
            st.markdown('**소요 시간**')
            st.table([{'구간':a,'비교 항목':b,'확인 조건':c} for a,b,c in analysis['time_rows']])
            st.markdown('**추가 비용**')
            st.table([{'비용':a,'비교 항목':b,'확인 조건':c} for a,b,c in analysis['cost_rows']])
            st.caption('시간은 동일 시작·종료 시점의 차이로 비교합니다.  \n병행 작업은 중복 합산하지 않습니다.  \n비용은 같은 화물량·통화·인도 조건으로 비교하며 감소할 수도 있습니다.')
            if analysis['ports']:
                with st.expander('기존 모델의 시연 가정값 · 실측 아님'):
                    for port in analysis['ports']:
                        if port['model_days'] is not None and port['model_cost_rate'] is not None:
                            st.write(f"{port['original']} → {port['alternate']}: 추가 {port['model_days']}일 / 운임 가산율 {port['model_cost_rate']*100:g}%")
                    st.caption('기존 상세 모드의 입력 가정입니다. 실제 일수·견적이나 제품가격 인상률로 사용하지 않습니다.')
        with source_tab:
            from .response_review import review_rows_html
            st.markdown(review_rows_html(profile),unsafe_allow_html=True)
            links=[]
            for row in analysis['impacts']:
                links.extend([(row['material']+' 제품',row['source']),('공급 관계',row['relationship_source'])])
            links.extend((c['name']+' 제품',c['source']) for c in analysis['candidates'])
            links.extend((p['alternate']+' 항만 자료',p['source']) for p in analysis['ports'])
            links.extend((s['title'],s['url']) for s in profile.get('sources',{}).values())
            for title,url in dict.fromkeys(links):
                if url:st.markdown(f'[{title}]({url})')
            st.write(case['evidence']);st.caption(case['limits'])
            st.download_button('해석 기록 내려받기',report,file_name=re.sub(r'[^A-Za-z0-9_-]','_',case['id'])+'-analysis.md',mime='text/markdown',key='demo_analysis_download')
    return analysis
