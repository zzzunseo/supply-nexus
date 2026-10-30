"""Guided presentation; isolated inputs, same validated simulation engine."""
import html
from copy import deepcopy
import streamlit as st
from simulation.manual_scenario import build_manual_issue
from simulation.resilience import apply_issue, calculate_supply_shock
from .demo_session import choose_case,commit_case,reset_presentation,initialize_presentation,change_step,clear_selection,CONTROLS


def demo_results(network, applied, inventory=True, bypass=True,detour=False):
    events=[]
    days=60
    if applied:
        days=applied['days']
        logistics=applied.get('kind')=='logistics'
        event='완전 봉쇄' if logistics and applied['percent']==100 else '부분 통항 제한' if logistics else '공급 감소'
        issue=build_manual_issue(network, applied['target'], event, days, applied['percent'])
        events=apply_issue([],issue)
        if logistics:
            from simulation.quick_detours import default_quick_profiles
            network=deepcopy(network)
            network['port_detours']=default_quick_profiles(network)
            network['port_detours'][applied['target']]['enabled']=detour
            bypass=False  # Same-supplier shipping comparison; reserve vendors stay off.
    return calculate_supply_shock(network,deepcopy(events),days,inventory,bypass,[])


def apply_demo(case, days, percent):
    commit_case(st.session_state,st.session_state.rr_network,case,days,percent)


def apply_current(case):
    # Read live widget state: a fast submit can arrive before the selector rerun.
    if st.session_state.get('demo_input_mode')=='직접 선택':
        from .demo_scenarios import selected_case
        case=selected_case(st.session_state.rr_network,st.session_state.demo_category,
                           st.session_state.demo_target,st.session_state.demo_event)
    else:
        from .logistics_demo import demo_cases
        case=demo_cases()[st.session_state.demo_case]
    apply_demo(case,st.session_state.demo_days,st.session_state.demo_percent)


def reset_demo():
    from .logistics_demo import demo_cases
    reset_presentation(st.session_state,demo_cases())
    st.session_state.demo_review_view='단계별 시연'
    st.session_state.verified_case='기존 시나리오 보기'
    st.session_state.process_map_scope='등록 공급관계'
    st.session_state.demo_company_direct=None


def goto(step):
    change_step(st.session_state,step)


def select_demo_case(cases):
    choose_case(st.session_state,cases,st.session_state.demo_case)


def open_details():
    st.session_state.demo_saved_controls={key:st.session_state[key] for key in CONTROLS if key in st.session_state}
    st.session_state.rr_workspace_mode='상세 모드'


def toggle_basic_map():
    st.session_state.demo_basic_map=not st.session_state.get('demo_basic_map',False)
    clear_selection(st.session_state)


@st.cache_data(show_spinner=False,max_entries=4)
def main_company_choices(network):
    from .process_catalog import company_groups
    return company_groups(network)


@st.cache_data(show_spinner=False,max_entries=4)
def presentation_result(network):
    # Qualitative presentation only needs the registered graph, not repeated shocks.
    return demo_results(network,None,False,False)


def card(title, text, accent=False):
    st.markdown('<div class="demo-card'+(' demo-accent' if accent else '')+'"><h3>'+html.escape(title)+'</h3><p>'+html.escape(text)+'</p></div>',unsafe_allow_html=True)


def chain(case, network):
    if case.get('connections'):
        suppliers=' · '.join(dict.fromkeys(network['entities'][r['supplier']]['name'] for r in case['connections']))
        recipients=' · '.join(network['nodes'][c]['name'] for c in case['recipients'])
        st.markdown('<div class="demo-chain">'+html.escape(suppliers+' → '+case['material_label']+' → '+recipients)+'</div>',unsafe_allow_html=True)
        return
    if case.get('kind')=='logistics':
        from .logistics_demo import port_scope
        scope=port_scope(network,case['target'])
        st.markdown(f'<div class="demo-chain"><b>공급사 {scope["suppliers"]}곳</b> → <b>{html.escape(network["logistics"][case["target"]]["name"])} · 경유 가정</b> → <b>고객사 {scope["customers"]}곳 · 소재 {scope["materials"]}종</b></div>',unsafe_allow_html=True)
        st.caption('등록 경로상 영향 검토 범위입니다. 실제 피해 기업 수·물량이 아닙니다.')
        return
    supplier='SUMCO' if case['id']=='wafer' else 'JSR'
    material='폴리시드 웨이퍼' if case['id']=='wafer' else '포토레지스트'
    recipients=' · '.join(network['nodes'][c]['name'] for c in case['recipients'])
    st.markdown('<div class="demo-chain">'+'<span class="demo-arrow">→</span>'.join('<b>'+html.escape(s)+'</b>' for s in (supplier,material,recipients,case['process']+' 공정'))+'</div>',unsafe_allow_html=True)


def render_summary(network, case):
    from .response_review import review_profile
    from .impact_explanation import build_explanation
    from .catalog_profile import has_photoresist
    selected=st.session_state.get('demo_review_product','전체 제품군') if has_photoresist(network,case) else None
    profile=review_profile(network,case,selected)
    analysis=build_explanation(network,case,profile)
    names=list(dict.fromkeys(c['name'] for c in analysis['candidates']))
    if analysis['logistics']:
        names=list(dict.fromkeys(p['alternate'] for p in analysis['ports']))
    candidate_title='비용 조건 검토' if analysis['tariff'] else f'{len(names)}곳 · 검토 후보' if names else '후보 보류'
    candidate_note='원산지·거래 조건별 비교' if analysis['tariff'] else ' · '.join(names) if names else '현재 선택 범위의 근거 부족'
    rate='관세율' if analysis['tariff'] else '통항 감소' if analysis['logistics'] else '공급 감소'
    items=[('선택 사례',case['name'],f"시나리오 가정 · {case['days']}일 / {rate} {case['percent']}%"),
           ('관련 공정',' · '.join(analysis['processes']) or '추가 확인',' · '.join(analysis['companies'])),
           ('대응 검토',candidate_title,candidate_note)]
    st.markdown('<div class="demo-summary">'+''.join(
        '<div class="demo-summary-card"><span>'+html.escape(label)+'</span><strong>'+html.escape(value)+'</strong><small>'+html.escape(note)+'</small></div>'
        for label,value,note in items)+'</div>',unsafe_allow_html=True)
    st.caption('등록 연결 기준 · 후보 수는 선택 범위 내 검토 대상이며 대체 가능 확정이 아닙니다.')


def render_demo(network):
    st.markdown('''<style>
    .block-container{overflow-y:auto!important;padding:12px 24px!important}
    .block-container>[data-testid="stVerticalBlock"]{gap:8px!important;height:auto!important;min-height:100%}
    .block-container [data-testid="stElementContainer"]{flex-shrink:0!important}
    .block-container [data-testid="stVerticalBlock"]>[data-testid="stLayoutWrapper"]{flex-shrink:0!important}
    .demo-brand{font-size:12px;font-weight:700;letter-spacing:.16em;color:#60d9d4;margin-bottom:4px}
    .demo-title{font-size:28px;font-weight:750;letter-spacing:-.6px;line-height:1.3;margin:0 0 6px;word-break:keep-all;overflow-wrap:break-word}
    h1.demo-title{padding:0!important;font-size:28px!important;line-height:1.3!important}
    .demo-sub{color:#a6bdcf;font-size:14px;line-height:1.6;max-width:58ch;word-break:keep-all;overflow-wrap:break-word}
    .demo-steps{display:flex;gap:14px;border-block:1px solid #203b53;padding:10px 0;margin:0 0 4px}
    .demo-steps span{flex:1;min-width:0;box-sizing:border-box;border:1px solid transparent;padding:12px 16px;border-radius:8px;background:#0b1827;color:#9bb1c3;font-size:17px;line-height:1.5;font-weight:650;word-break:keep-all;overflow-wrap:break-word}
    .demo-steps .done{color:#b8d3dc;border:1px solid #294a58}
    .demo-summary{display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:12px;margin:6px 0 2px}
    .demo-summary-card{min-width:0;padding:14px 18px;border:1px solid #29475a;border-radius:12px;background:linear-gradient(125deg,#102638,#091520)}
    .demo-summary-card>span{display:block;color:#8eafc4;font-size:12px;letter-spacing:.04em;margin-bottom:8px}
    .demo-summary-card strong{display:block;color:#e3f1fa;font-size:21px;line-height:1.45;word-break:keep-all;overflow-wrap:break-word}
    .demo-summary-card small{display:block;color:#adc3d2;font-size:13px;line-height:1.65;margin-top:8px;word-break:keep-all;overflow-wrap:break-word}
    .demo-summary-card:last-child{border-top:2px solid #4fe4db}
    @media(max-width:700px){.demo-summary{grid-template-columns:1fr}.demo-summary-card strong{font-size:18px}}
    .demo-steps .active{color:#4fe4db;border:1px solid #267787;background:#0b2938}
    .demo-card{border:1px solid #25445d;background:linear-gradient(120deg,#102539,#091421);border-radius:12px;padding:14px 18px;margin:0}
    [data-testid="stVerticalBlock"]{gap:10px}
    [data-testid="stHeadingWithActionElements"] h3{padding:0!important;margin:0 0 8px!important;font-size:21px!important;line-height:1.45!important;word-break:keep-all;overflow-wrap:break-word}
    .demo-card h3{font-size:19px;color:#dceaf8;margin:0 0 8px;padding:0}
    .demo-card p{font-size:15px;line-height:1.7;color:#b4c9d9;margin:0;word-break:keep-all;overflow-wrap:break-word}
    .demo-accent{border-left:4px solid #ffbe60}
    .demo-chain{display:flex;align-items:center;justify-content:space-around;gap:12px;padding:18px;border:1px solid #294b63;background:#0b1b2b;border-radius:10px;font-size:17px}
    @media(max-width:900px){.demo-steps{gap:6px}.demo-steps span{font-size:14px;padding:10px 8px}h1.demo-title{font-size:23px!important}.demo-chain{flex-wrap:wrap;font-size:14px;padding:12px}}
    .demo-chain b{text-align:center}.demo-arrow{color:#4fe4db;font-size:24px}
    .demo-legend{display:flex;gap:18px;font-size:12px;color:#b9ccde;padding:4px 0}
    .demo-legend .primary{color:#ffad49}.demo-legend .alt{color:#4fe4db}
    .demo-result-explanation{font-size:14px;line-height:1.75;color:#b1c8da;border-left:2px solid #4fe4db;padding-left:9px}
    .stButton button{min-height:42px;font-size:15px!important;border-radius:9px}
    .stButton button[kind="primary"]{background:#17cce3!important;color:#031522!important;border-color:#17cce3!important;font-weight:750}
    label p,[data-testid="stCheckbox"] p{font-size:14px!important}
    [data-baseweb="select"],[data-testid="stNumberInput"] input{font-size:15px!important}
    [data-testid="stMetricValue"]{font-size:32px!important}
    [data-testid="stCaptionContainer"]{font-size:14px!important;line-height:1.75!important;color:#b5cadd!important;margin-bottom:0!important}
    </style>''',unsafe_allow_html=True)
    from .logistics_demo import demo_cases
    cases=demo_cases()
    initialize_presentation(st.session_state,cases)
    top=st.columns([4.8,1.2,1.2,1.4,1.4],vertical_alignment='center')
    with top[0]:
        st.markdown('<div class="demo-brand">SUPPLY NEXUS</div><h1 class="demo-title">반도체 공급망 분석</h1><div class="demo-sub">공급 차질의 영향 연결과 대응 조건을 근거에 따라 살펴봅니다.</div>',unsafe_allow_html=True)
    with top[1]: st.button('처음으로',key='demo_reset',on_click=reset_demo,width='stretch')
    with top[2]: st.button('3D 지도' if st.session_state.get('demo_basic_map') else '기본 지도',key='demo_map_mode',on_click=toggle_basic_map,width='stretch')
    with top[3]: st.button('상세 모드 ↗',key='demo_advanced',on_click=open_details,width='stretch')
    with top[4]: st.link_button('요약·출처 ↗','/?view=mobile',width='stretch')
    old_ai={'AI 외부 검토':'사건·공정 영향 조사','AI 대안 비교':'기업·소재 조건 비교','AI 사건 검토':'기사 본문 근거 검토'}
    previous=st.session_state.get('demo_review_view')
    if previous in old_ai:
        st.session_state.ai_workspace_task=old_ai[previous]
        st.session_state.demo_review_view='AI 분석'
    view=st.radio('화면 선택',['단계별 시연','AI 분석','항만 검토','통합 검토 · 발표'],format_func=lambda v:{'단계별 시연':'영향 검토','AI 분석':'AI 분석','항만 검토':'항만·해협 검토','통합 검토 · 발표':'조건 비교'}[v],horizontal=True,key='demo_review_view')
    if view=='AI 분석':
        from .ai_workspace import render_ai_workspace
        render_ai_workspace(network)
        return
    if view=='항만 검토':
        from .major_ports import render_major_ports
        render_major_ports(network,standalone=True)
        return
    if view=='통합 검토 · 발표':
        from .integrated_review import render_integrated_review
        render_integrated_review(network)
        return
    companies=main_company_choices(network)
    direct=st.selectbox('기업 바로 선택 · 공급 중단 시뮬레이션',[None,*companies],
        format_func=lambda name:name or '기존 공급관계 시나리오',key='demo_company_direct')
    if direct:
        from .process_vendor_map import render_process_vendor_map
        render_process_vendor_map(network,company=direct,groups=companies[direct])
        st.caption('지도 대체 기업·경로를 클릭하면 오른쪽에 대체 품목·선정 근거·전환 조건이 표시됩니다. 중단 대상은 상단 기업 선택에서 변경하세요.')
        return
    scope=st.radio('지도 검토 범위',['등록 공급관계','공정별 기업·소재'],horizontal=True,key='process_map_scope')
    if scope=='공정별 기업·소재':
        from .process_vendor_map import render_process_vendor_map
        render_process_vendor_map(network)
        return
    from .verified_cases import render_representative_picker,render_verified_cases
    if st.session_state.get('verified_case','기존 시나리오 보기')!='기존 시나리오 보기':
        render_representative_picker(cases)
        if render_verified_cases(st.session_state.verified_case):return
        st.rerun()
    step=st.session_state.demo_step
    applied=st.session_state.demo_applied
    if step>1 and not applied:
        step=1
        st.session_state.demo_step=1
    st.markdown('<div class="demo-steps">'+''.join(f'<span class="{"active" if i==step else "done" if i<step else ""}">{i}　{label}</span>' for i,label in enumerate(('공급 차질 설정','영향 확인','대응 후보 비교'),1))+'</div>',unsafe_allow_html=True)
    case=applied or cases[1]
    if applied and step>1:render_summary(network,case)
    with st.spinner('공급 연결 자료를 준비하고 있습니다…'):
        result=presentation_result(network)
    st.session_state.demo_result=result
    if step in (1,2):
        left,right=st.columns([2,1],gap='large')
        with right:
            if step==1:
                st.subheader('어떤 공급 차질을 살펴볼까요?')
                render_representative_picker(cases)
                if st.session_state.get('verified_case','기존 시나리오 보기')!='기존 시나리오 보기':
                    st.rerun()
                st.session_state.setdefault('demo_case',next((i for i,c in enumerate(cases) if applied and c['id']==applied['id']),1))
                st.session_state.setdefault('demo_days',applied['days'] if applied else 60)
                st.session_state.setdefault('demo_percent',applied['percent'] if applied else 100)
                st.radio('선택 모드',['빠른 사례','직접 선택'],format_func=lambda v:'사례 선택' if v=='빠른 사례' else v,key='demo_input_mode',horizontal=True)
                if st.session_state.demo_input_mode=='빠른 사례':
                    chosen=st.selectbox('검토 사례',range(len(cases)),format_func=lambda i:cases[i]['name'],key='demo_case',on_change=select_demo_case,args=(cases,))
                    case=cases[chosen]
                else:
                    from .demo_scenarios import choices,selected_case
                    category=st.selectbox('대상 종류',['소재','기업','항만·해협'],format_func=lambda v:'항만·해협·운하' if v=='항만·해협' else v,key='demo_category')
                    options=dict(choices(network,category))
                    if st.session_state.get('demo_target') not in options:st.session_state.demo_target=next(iter(options))
                    target=st.selectbox('대상',list(options),format_func=options.get,key='demo_target')
                    events=['완전 봉쇄','부분 통항 제한'] if category=='항만·해협' else ['공급 중단','공급 감소','수출 제한','화재·사고에 따른 공급 차질','관세 부과']
                    if st.session_state.get('demo_event') not in events:st.session_state.demo_event=events[0]
                    event=st.selectbox('사건',events,key='demo_event')
                    case=selected_case(network,category,target,event)
                if case.get('historical'):
                    st.caption('역사 사례 재현 · 실제 사건과 영향 가정을 구분합니다.')
                    with st.expander('실제 사건·재현 범위'):
                        st.write(case['history'])
                        st.caption(case['limits'])
                        st.markdown('[재고·타 거점 대응 발표]('+case['incident_source']+') · [복구 발표]('+case['recovery_source']+')')
                tariff=case.get('event')=='관세 부과'
                full=case.get('event') in ('공급 중단','완전 봉쇄')
                cap=500 if tariff else 99 if case.get('event')=='부분 통항 제한' else 100
                st.session_state.demo_percent=100 if full else min(st.session_state.demo_percent,cap)
                with st.form('demo_condition_form'):
                    a,b=st.columns(2)
                    with a: st.number_input('적용 기간 · 일',1,365,key='demo_days')
                    with b: st.number_input('관세율 · %' if tariff else '통항 감소 · %' if case.get('kind')=='logistics' else '공급 감소 · %',1,cap,key='demo_percent',disabled=full)
                    st.form_submit_button('시나리오 적용 →',key='demo_apply',type='primary',width='stretch',on_click=apply_current,args=(case,),disabled=st.session_state.get('demo_transitioning',False))
                st.caption('시나리오 가정 · 기간과 감소율은 실제 피해 수치가 아닙니다.')
                with st.expander('입력 안내 · 지원 범위',expanded=False):
                    st.write('조건을 적용하면 관련 기업·공정과 대응 후보를 확인할 수 있습니다.')
                    st.caption('기간·감소율은 입력 가정입니다. 사건 발생일·복구일 또는 실제 공급·생산 감소율을 확인한 값이 아닙니다.')
                    st.caption('등록된 공급 연결을 사용합니다. 가오슝·말라카·수에즈 경유 사례를 지원하며, 대체 후보는 확보된 제품 근거 범위에서 표시합니다.')
                if st.session_state.get('demo_error'):st.error(st.session_state.demo_error)
                if applied: st.caption('지도는 직전 적용 결과입니다. 새 조건은 적용 버튼을 눌러 반영하세요.')
            else:
                st.subheader('어디에 영향이 연결되나요?')
                if case.get('kind')=='logistics':
                    from .logistics_demo import port_scope
                    scope=port_scope(network,case['target'])
                    card('항만 경유 가정 · 영향 검토 범위',f"공급사 {scope['suppliers']}곳 · 고객사 {scope['customers']}곳 · 소재 {scope['materials']}종")
                    st.caption('공정 설명: '+case['material_label']+' 대표 연결입니다.')
                tariff=case.get('event')=='관세 부과'
                change='관세율' if tariff else '통항' if case.get('kind')=='logistics' else '공급'
                detail=f"관세율 {case['percent']}% 가정 · 공급 단절 아님" if tariff else '전면 중단 가정' if case.get('event') in ('공급 중단','완전 봉쇄') else f"{change} {case['percent']}% 감소 가정"
                if case.get('historical'):
                    st.caption('역사 사건 기반 재현 · 고객 연결·기간·감소율은 별도 가정입니다.')
                card('적용 조건',f"{case['name']} · {case['days']}일 · {detail}",True)
                recipients=' · '.join(network['nodes'][company]['name'] for company in case['recipients'])
                card('관련 기업·공정',recipients+' / '+case['process'])
                from .catalog_profile import has_photoresist
                if has_photoresist(network,case):
                    st.selectbox('검토 제품군',['전체 제품군','ArF','KrF','i-line','EUV'],key='demo_review_product')
                st.toggle('검토 후보 경로 표시',key='demo_show_candidate')
                from .impact_explanation import build_explanation
                from .response_review import review_profile
                analysis=build_explanation(network,case,review_profile(network,case,st.session_state.get('demo_review_product')))
                st.session_state.demo_explanation=analysis
                card('가정에 따른 영향 검토',analysis['impacts'][0]['reason'] if analysis['impacts'] else '등록된 품목·공정 연결을 추가 확인해야 합니다.')
                st.button('다음: 대응 후보 검토 →',key='demo_next',type='primary',width='stretch',on_click=goto,args=(3,))
                st.button('← 조건 수정',key='demo_previous',on_click=goto,args=(1,))
        with left:
            mapcase=applied or case
            from .night_globe import globe_payload
            from .response_review import render_review_map
            if applied and step>1:
                from .response_review import review_payload
                mapdata=review_payload(network,result,mapcase,st.session_state.get('demo_show_candidate',True),st.session_state.get('demo_review_product'))
            else:
                mapdata=globe_payload(network,result,mapcase,applied is not None)
            mapdata.update(review=True,case_id=mapcase['id'])
            for marker in mapdata['markers']:marker['score']=None
            render_review_map(mapdata)
            from .demo_scenarios import legend
            st.caption(legend(st.session_state.demo_current_map))
            from .demo_interaction import selection_description
            inspection=selection_description(st.session_state.demo_current_map,mapcase)
            if inspection:card(inspection['title'],inspection['subtitle']+' / '+inspection['text'])
            else:chain(mapcase,network)
    else:
        from .response_review import render_review
        render_review(network,result,case)
    st.caption('공개 자료 기반 · 미등록은 영향 없음을 뜻하지 않습니다.')
    from .relationship_audit import render_relationship_audit
    render_relationship_audit(network)
    if step!=3 or not st.session_state.get('demo_review',{}).get('evidence'):
        with st.expander('근거 · 가정과 한계',expanded=False):
            st.toggle('기본 지도 사용 · 3D 호환성',key='demo_basic_map')
            st.write(case['evidence'])
            st.write(case['limits'])
            st.markdown(f"[공급관계 자료]({case['relationship_source']}) · [제품 자료]({case['product_source']})")
            st.caption('제품군·항만 자료와 고객별 호환·인증·공급 계약은 확인 범위가 다릅니다. 가정 기반 점수·재고 계산은 상세 모드에서 검토할 수 있습니다.')
    st.session_state.demo_transitioning=False
