"""Header and left, globe, and analysis panels."""
import html
import streamlit as st
from resilience_globe import build_network_globe, process_edges, COLORS
from .cards import advice_cards
from .calculation import calculate_current, calculate_sensitivity
from .resources import EXAMPLES
from .settings import settings
from .state import reset, submit, scopes_from_state
from .issue_manager import render_active_issues
from .timeline import build_timeline
from simulation.reporting import score_view
from .process_comparison import show_process_comparison, view_label
from .quick_detours import render_quick_detours
from .flow_panel import render_flow_panel
from flow_data import build_flow
from .globe_click import render_globe_click
from .selection import select_globe_process


def render_header():
    st.markdown('<div class="rr-header"><div><span class="rr-logo">◈</span> <b>공급망 디지털 트윈</b><span class="rr-subtitle">반도체 공급망</span></div><span class="rr-badge">시뮬레이션 가정</span></div>', unsafe_allow_html=True)


def render_left_panel(network):
    st.markdown('<div class="rr-panel-heading">설정 · 소재 충족도 <span>관측 기간 · 일</span></div>', unsafe_allow_html=True)
    st.number_input('관측 기간 · 일', 1, 365, key='rr_days', label_visibility='collapsed')
    st.checkbox('재고 완충 적용', key='rr_inventory')
    st.checkbox('대체 벤더 우회 적용', key='rr_bypass')
    result = calculate_current(network)
    st.session_state.rr_result = result
    color = COLORS['normal'] if result['overall'] >= 100 - 1e-07 else COLORS['stopped'] if result['overall'] < 1e-07 else COLORS['reduced']
    incomplete = result.get('incomplete_processes', {})
    index_label = '최저 소재 충족도 · 등록 범위'
    suffix = '*' if incomplete else ''
    mean = score_view(result, 'mean')
    mean_color = COLORS['normal'] if mean['overall'] >= 100 - 1e-7 else COLORS['stopped'] if mean['overall'] < 1e-7 else COLORS['reduced']
    st.markdown(f'<div class="rr-overall-dual"><span>{index_label}</span><div><span>최악 기업 <b style="color:{color}">{result["overall"]:.0f}{suffix}</b></span><span>기업 평균 <b style="color:{mean_color}">{mean["overall"]:.0f}{suffix}</b></span></div></div><div class="rr-score-heading">공정 <span>최악 / 기업 단순평균</span></div>', unsafe_allow_html=True)
    rows = []
    for p, v in result['scores'].items():
        if v is None:
            rows.append(f'<div class="rr-score rr-score-unscored"><span>{html.escape(p)}</span><b>— <small>미산정</small></b></div>')
            continue
        color = COLORS['buffer'] if p in result['protected_processes'] else COLORS['normal'] if v >= 100 - 1e-07 else COLORS['stopped'] if v < 1e-07 else COLORS['reduced']
        partial = p in incomplete
        score_label = f'{v:.0f}' + ('*' if partial else '')
        mean_value = mean['scores'][p]
        mean_label = f'{mean_value:.0f}' + ('*' if p in mean['incomplete_processes'] else '') if mean_value is not None else '—'
        mean_color = COLORS['normal'] if mean_value >= 100 - 1e-7 else COLORS['stopped'] if mean_value < 1e-7 else COLORS['reduced']
        number_color = '#ACC0D2' if v >= 100 - 1e-7 else color
        mean_color = '#8FAABD' if mean_value >= 100 - 1e-7 else mean_color
        row_class = 'rr-score rr-score-selected' if p == st.session_state.rr_process else 'rr-score'
        symbol = '?' if partial else '●' if v >= 100 - 1e-07 else '×' if v < 1e-07 else '△'
        rows.append(f'<div class="{row_class}"><span><i style="color:{color}">{symbol}</i> {p}</span><b style="color:{number_color}">{score_label}<small> / </small><span style="color:{mean_color}">{mean_label}</span></b><div class="rr-scorebar" style="width:{max(1, v):g}%;background:{color}"></div></div>')
    st.markdown('<div class="rr-scores">' + ''.join(rows) + '</div>', unsafe_allow_html=True)
    shortage_count = sum(v is not None and v < 100-1e-7 for v in result['scores'].values())
    st.markdown(f'<div class="rr-material-summary">소재 부족 {shortage_count}개 공정 · 미산정 {len(result.get("unscored_processes", []))}개</div>', unsafe_allow_html=True)
    with st.expander('점수 해석 · 모델 범위', expanded=False):
        st.markdown(f"""<div class="rr-hint">{result['duration_days']}일째 소재 충족도 · 생산량 예측 아님<br>* 누락 투입재 제약 제외 · 범위 불완전 {len(incomplete)}/8<br>감소 공정 {sum((v is not None and v < 100 - 1e-07 for v in result['scores'].values()))} / 8 · 우회 {len(result['bypass'])}개</div>""", unsafe_allow_html=True)
        front = ' · '.join(f'{view_label(result, company)} {result["process_views"][company]["overall"]:.0f}' + ('*' if result['process_views'][company]['incomplete_processes'] else '') for company in ('samsung', 'tsmc'))
        st.markdown('<div class="rr-hint">전공정 7개: ' + html.escape(front) + '<br>패키징: ASE·Amkor · 산업 전체 아님<br>평균은 산정 가능한 기업 동일 비중 · 막대는 최저 소재</div>', unsafe_allow_html=True)
    render_quick_detours(network)
    st.button('소재·44개 경로·가정 설정', width='stretch',
              on_click=lambda: st.session_state.update(rr_settings_open=True))
    if st.session_state.get('rr_settings_open', False):
        settings(network)
    st.button('전체 정상 복구', width='stretch', on_click=reset)
    return result


def render_center_panel(network, result):
    process = st.session_state.rr_process
    title = '전체 공정 공급망' if process == '전체' else process + ' 공정 공급망'
    st.markdown(f"""<div class="rr-panel-heading">{html.escape(title)} <span>위치 {len(network['locations'])} · 확장 소재 {len(network['extended_materials'])}종</span></div>""", unsafe_allow_html=True)
    filters = st.columns([1, 1, 1.8], gap='small')
    with filters[0]:
        st.selectbox('관측', ['아시아', '유럽', '미주', '이슈'], key='rr_view', label_visibility='collapsed')
    with filters[1]:
        st.selectbox('타임라인 점수 보기', list(result['process_views']), key='rr_score_view', format_func=lambda key: view_label(result, key), label_visibility='collapsed')
    current_flow = build_flow(network, result, st.session_state.rr_flow_process)
    materials = {card['node_id']: card['name'] for column in current_flow['columns']
                 for card in column['cards'] if card['kind'] == 'material'}
    current_focus = st.session_state.rr_focus
    process_nodes = None
    if process != '전체':
        process_nodes, _ = process_edges(network, result, process)
        if current_focus not in process_nodes:
            current_focus = None
            st.session_state.rr_focus = None
    selectable = {key for key, entity in network['entities'].items()
                  if entity['kind'] == 'company' and entity.get('map_location')}
    selectable.update(materials)
    if process_nodes is not None:
        selectable.intersection_update(process_nodes)
    if current_focus in network['entities']:
        selectable.add(current_focus)
    company_options = [None] + sorted(selectable, key=lambda key: (network['entities'][key]['kind'], network['entities'][key]['name'], key))
    st.session_state.rr_name_company = current_focus if current_focus in company_options else None
    def selection_label(key):
        if key is None:
            return '기업·소재 찾기 · 전체 보기'
        entity = network['entities'][key]
        if entity['kind'] == 'company':
            place=entity.get('map_location')
            return '기업 · ' + entity['name'] + ' · ' + (place['name'] if place else '지도 위치 미확인')
        if entity['kind'] == 'logistics':
            return '항만·해협 · ' + entity['name']
        return '소재 · ' + materials.get(key, entity['name']) + ' · ' + entity['name']
    def select_named_company():
        st.session_state.rr_focus = st.session_state.rr_name_company
    with filters[2]:
        st.selectbox(
            '기업·소재 찾기', company_options, key='rr_name_company',
            format_func=selection_label, on_change=select_named_company, label_visibility='collapsed',
            placeholder='기업·소재 찾기',
        )
    with st.container(key='rr_process_selector'):
        st.pills('지구본 공정', ['전체', *network['processes']], key='rr_process',
                 selection_mode='single', required=True, label_visibility='collapsed',
                 width='stretch', on_change=select_globe_process, args=(st.session_state,))
    selected_view = score_view(result, st.session_state.rr_score_view)
    st.markdown('<div class="rr-legend"><span style="color:#4FE4DB">● 정상</span><span style="color:#71F5B2">● 가정 재고 방어</span><span style="color:#FFBE60">● 공급 감소</span><span style="color:#FF587B">●/┄ 차질</span><span style="color:#409CFF">┄ 활성 우회</span><span style="color:#839EB5">┄ 참고·계산 제외</span></div>', unsafe_allow_html=True)
    with st.container(key='rr_visual_area', height='stretch'):
        with st.container(key='rr_globe_area', height='stretch'):
            fig = build_network_globe(network, result, st.session_state.rr_view,
                                      st.session_state.rr_focus, process=process)
            selection = st.plotly_chart(fig, width='stretch', height='stretch', theme=None, key='rr_globe', config=dict(displayModeBar=False, scrollZoom=True, topojsonURL='/app/static/'), on_select='ignore')
            render_globe_click(network)
            target = network['entities'].get(st.session_state.rr_focus)
            if target and target['kind'] == 'company' and target.get('map_location'):
                caption = '선택 기업: ' + target['name'] + ' · 시설: ' + target['map_location']['name']
            elif target and target['kind']=='company':
                caption='선택 기업: '+target['name']+' · 지도 위치 미확인 · 공급 흐름에서 등록 연결 확인'
            elif target and target['kind'] == 'logistics':
                caption = '선택 물류: ' + target['name'] + ' · 등록 항만·해협 대표점 · 경유·통항 제약은 시뮬레이션 가정'
            elif target:
                caption = '선택 소재: ' + target['name'] + ' · 공급 이전·이후 경로 강조'
                if not target.get('map_location_id'):
                    caption += ' · 위치 미확인 구간은 상세 흐름에서 확인'
            else:
                caption = '기업·소재를 선택하면 연결 경로가 강조됩니다 · 시뮬레이션 가정'
            if process != '전체':
                missing = sum(not network['nodes'][card['node_id']].get('map_location_id')
                              for column in current_flow['columns'] if column['id'] == 'suppliers'
                              for card in column['cards'])
                if missing and not (target and not target.get('map_location_id')):
                    caption += f' · 위치 미확인 {missing}곳: 상세 흐름 참조'
            caption_class = 'rr-location-caption rr-location-selected' if target else 'rr-location-caption'
            st.markdown('<div class="' + caption_class + '">' + html.escape(caption) + '</div>', unsafe_allow_html=True)
        flow_scope = '전체 보기 / ' if process == '전체' else ''
        flow_title = '공급 흐름 · ' + flow_scope + st.session_state.rr_flow_process + ' 상세 펼쳐보기'
    from .relationship_view import open_relationships,relationship_dialog
    st.button('공급 흐름 · 기업 연결 한눈에 보기',key='rr_supply_overview',on_click=open_relationships,width='stretch')
    if st.session_state.get('rr_relationship_open'):
        relationship_dialog(network,result)
    with st.expander('공정 상세 흐름 · 추가 정보', expanded=False):
        with st.container(key='rr_flow_area', height=220):
            render_flow_panel(network, result)
    with st.expander('일별 소재 충족도 · 타임라인', expanded=False):
        hits = ' · '.join(f'{p} {day}일' for p, day in selected_view['first_hit'].items()) or '등록 공정의 관측 기간 내 없음'
        label = view_label(result, st.session_state.rr_score_view)
        st.markdown('<div class="rr-timeline-title">일별 ' + html.escape(label) + ' · * 누락 제약 제외 · 미등록 공정은 공백</div>', unsafe_allow_html=True)
        st.plotly_chart(build_timeline(selected_view), key='rr_timeline', width='stretch', height=150, theme=None, config=dict(displayModeBar=False))
        st.markdown('<div class="rr-first-hits">가정상 첫 소재 부족: ' + html.escape(hits) + '</div>', unsafe_allow_html=True)



def render_right_panel(network, result):
    from .explanation import current_explanation
    from .article_review import render_article_summary, render_article_input_button
    from .article_chat import render_chat_answer, render_chat_input, render_function_result, render_function_review
    from .scenario_summary import render_process_impact

    with st.container(key='rr_analysis'):
        st.markdown('<div class="rr-panel-heading">이슈 · 영향 분석</div>', unsafe_allow_html=True)
        with st.container(key='rr_chat'):
            render_chat_input(network)
        st.markdown('<div class="rr-section-label">현재 이슈</div>', unsafe_allow_html=True)
        if st.session_state.rr_events:
            render_active_issues()
        else:
            st.markdown('<div class="rr-issue-empty">적용 중인 시나리오가 없습니다.</div>', unsafe_allow_html=True)
        if st.session_state.rr_error:
            st.error(st.session_state.rr_reply)
        if st.session_state.get('rr_chat_mode')=='직접 조건 선택':
            if st.session_state.get('rr_manual_last') and not st.session_state.rr_error:
                st.caption('최근 작업: '+st.session_state.rr_manual_last['text'])
        else:
            render_chat_answer()
        if st.session_state.get('rr_function_mode'):
            render_function_review(network)
        if st.session_state.get('rr_article_review') and st.session_state.get('rr_chat_mode')=='기사 검토 · 모의 대화':
            render_article_summary(network)
        st.markdown('<div class="rr-section-label">현재 상태 · 해설</div>', unsafe_allow_html=True)
        st.markdown(current_explanation(network, result, st.session_state, compact=True), unsafe_allow_html=True)
        render_process_impact(network,result)
        st.caption('모델상 소재 충족도 · 실제 생산량 예측 아님')
        with st.expander('상세 보기 · 근거와 기록', expanded=False):
            with st.expander('해설 전체 · 가정과 한계',expanded=False):
                st.markdown(current_explanation(network,result,st.session_state),unsafe_allow_html=True)
            if st.session_state.get('rr_function_mode'):
                render_function_result(network,result)
            messages=st.session_state.get('rr_chat_messages',[])
            if messages:
                with st.expander('대화 기록',expanded=False):
                    for message in messages:
                        st.caption('질문' if message['role']=='user' else '답변')
                        st.text(message['text'])
            with st.expander('공정·기업별 상세 점수', expanded=False):
                if st.button('기업별 공정 점수·모델 범위', key='rr_company_details', width='stretch'):
                    show_process_comparison(result)
                st.markdown(advice_cards(network, result), unsafe_allow_html=True)
            with st.expander('가정 비교 · 계산 근거', expanded=False):
                included = sum(edge.get('calculation_included',True) for edge in network['visual_edges'] if edge['kind']=='backbone')
                st.markdown(f'<div class="rr-hint">원본 44개: 소재 경로 {included} · 참고 {44 - included}<br>누락 제약이 있어 100도 정상 보장이 아닙니다.<br>납품·필수 투입재·비중은 시뮬레이션 가정입니다.<br>최저 소재 충족도 = 산정 가능한 공정 중 최솟값<br>장비·관세·공정 간 생산 전파는 점수 제외</div>', unsafe_allow_html=True)
                first = min(result['first_hit'].values(), default=None)
                st.markdown(f"""<div class="rr-hint">가정상 첫 소재 부족: {(str(first) + '일째' if first else '없음')} · 활성 이슈 {len(st.session_state.rr_events)}개<br>제품군: {html.escape(st.session_state.rr_special)} / {html.escape(st.session_state.rr_package)}</div>""", unsafe_allow_html=True)
                rows = calculate_sensitivity(
                    network, st.session_state.rr_events, st.session_state.rr_days,
                    st.session_state.rr_inventory, st.session_state.rr_bypass, scopes_from_state()
                )
                table_rows = ''.join(
                    f"<tr><td>{row['label']}</td><td>{row['overall']:.1f} ({row['delta']:+.1f})</td><td>{row['average']:.1f} ({row['average_delta']:+.1f})</td><td>{row['mean_overall']:.1f} ({row['mean_delta']:+.1f})</td><td>{row['mean_average']:.1f} ({row['mean_average_delta']:+.1f})</td></tr>"
                    for row in rows
                )
                st.markdown('<div class="rr-hint">가정 민감도 · 최악/기업평균 (기준 대비 변화)</div><table class="rr-sensitivity"><thead><tr><th>변경</th><th>최악<br>말일</th><th>최악<br>기간평균</th><th>기업평균<br>말일</th><th>기업평균<br>기간평균</th></tr></thead><tbody>' + table_rows + '</tbody></table><div class="rr-hint">활성 소재군의 재고/우회 한도만 각각 변경 · 365일/100% 상한<br>예약 풀·인증일 고정. 해당 옵션을 끄면 민감도 변화도 없습니다.</div>', unsafe_allow_html=True)
                if st.session_state.rr_focus:
                    target = network['entities'].get(st.session_state.rr_focus)
                    if target:
                        place = target.get('map_location')
                        st.caption('포커스: ' + (place['name'] if place else target['name']))
                        if place:
                            st.markdown(f"[시설·주소 원문]({place['source']}) · [좌표 지도]({place['coordinate_source']})")
                    st.button('포커스 해제', on_click=lambda: st.session_state.update(rr_focus=None), width='stretch')
            with st.expander('입력·적용 기록', expanded=False):
                st.markdown('<div class="rr-query">' + html.escape(st.session_state.rr_last_query) + '</div><div class="rr-reply">' + html.escape(st.session_state.rr_reply) + '</div>', unsafe_allow_html=True)
        with st.expander('기사 검토 · 시연 도구',expanded=False):
            render_article_input_button(network)
            with st.expander('시연 예시 선택', expanded=False):
                st.selectbox('단일 시연 예시', ['선택 안 함'] + list(EXAMPLES), key='rr_example', label_visibility='collapsed')
                if st.session_state.rr_example in EXAMPLES:
                    st.button('선택 예시 단일 적용', on_click=submit, args=(network, EXAMPLES[st.session_state.rr_example]), width='stretch')
            with st.expander('가정 입력 · 시나리오 계산', expanded=False):
                with st.form('rr_issue_form', clear_on_submit=False):
                    st.text_input('지역·소재·기업 이슈', key='rr_issue_text', max_chars=600, placeholder='일본 포토레지스트 중단 30일', label_visibility='collapsed')
                    st.form_submit_button('이슈 적용 → 소재 계산', on_click=submit, args=(network,), type='primary', width='stretch')
                st.caption('이 수동 입력에 한해 미기재 값은 100% 중단·30일로 적용됩니다.')
