"""Evidence-scoped response candidates; no assumed recovery or readiness scores."""
import html
import streamlit as st
from .demo_session import clear_selection,change_step
from .demo_interaction import prepare_map,accept_pick,selection_description

PRODUCT_EVIDENCE={
    'shinetsu':dict(material='폴리시드 웨이퍼',item_ids=['polished-wafer'],detail='공식 제품 목록에 polished wafer가 포함되어 있습니다.',
                    source='https://www.shinetsu.co.jp/en/products/semiconductor-silicon-business/silicon-wafers/'),
    'dongjin':dict(material='포토레지스트',item_ids=['photoresist'],detail='공식 자료에 ArF·KrF·i-Line 포토레지스트 제품군이 소개되어 있습니다.',
                  source='https://www.dongjin.com/en/business/semiconductor.php'),
}


def _legacy_review_profile(network,case,product_class=None):
    if case.get('connections') or case.get('event')=='관세 부과':
        from .demo_scenarios import custom_profile
        return custom_profile(network,case)
    logistics=case.get('kind')=='logistics'
    if logistics:
        from resilience_logistics import DETOUR_CANDIDATES
        candidate_id=DETOUR_CANDIDATES[case['target']]
        place=network['logistics'].get(candidate_id)
        return dict(kind='logistics',candidate_id=candidate_id,name=place['name'] if place else '후보 위치 미확인',
            material=case['material_label'],source=place.get('source') if place else None,
            rows=[('항만 자료','자료 확인' if place else '미확인',place['precision'] if place else '항만 자료를 확인해야 합니다.'),
                  ('화물 취급 적합성','미확인','해당 소재의 포장·보관·위험물 취급 조건 확인'),
                  ('운송·통관 조건','미확인','선사 운항·입항·통관 및 고객사 반입 절차 확인'),
                  ('추가 처리 여력','미확인','접안·하역·보관 및 내륙 운송 여력 확인'),
                  ('우회 경로 연결','검토 필요','우회 경유점에서 수요기업까지의 실제 운송 연결 확인')],
            summary=(place['name'] if place else '미등록 경유점')+'은 우회 검토 후보입니다. 실제 운항·화물 취급·고객 반입 연결을 확인해야 합니다.')
    product=network['nodes'][case['target']]
    pool=network['nodes'].get(product.get('alt_vendor'),{})
    candidate_id=pool.get('company_id')
    candidate=network['entities'].get(candidate_id,{})
    evidence=PRODUCT_EVIDENCE.get(candidate_id)
    if evidence and product.get('item_id') not in evidence['item_ids']:evidence=None
    material=evidence['material'] if evidence else product.get('item_id','선택 소재')
    profile=dict(kind='material',candidate_id=candidate_id,name=candidate.get('name','등록 후보 없음'),material=material,candidate_eligible=bool(evidence),
        source=evidence['source'] if evidence else None,
        rows=[('소재 제품군','자료 확인' if evidence else '미확인',evidence['detail'] if evidence else '후보 기업의 해당 제품군 자료 확인 필요'),
              ('소재 호환성','미확인','등급·순도·규격·노광 파장 등 해당 공정 조건의 일치 여부 확인'),
              ('고객사 인증','미확인','선정 고객의 품질 승인·공정 검증 및 전환 절차 확인'),
              ('추가 공급 여력','미확인','여유 생산능력·납기·공급 계약 가능 여부 확인'),
              ('물류 접근성','검토 필요','출하 거점·운송수단 및 차질 지역 경유 여부 확인')],
        summary=f"{candidate['name']}은 {material} 대체 검토 후보입니다. 제품군 보유만으로 해당 고객 공정에 즉시 투입할 수 있다고 판단하지 않습니다." if candidate else '등록된 후보가 없습니다. 해당 소재의 제품 자료와 공급사 후보를 먼저 확인해야 합니다.')
    from .response_evidence import enrich_profile
    return enrich_profile(network,case,profile,product_class)


def review_profile(network,case,product_class=None):
    from .catalog_profile import enrich_catalog_profile
    from .process_catalog import enrich_process_profile
    profile=enrich_process_profile(network,case,_legacy_review_profile(network,case,product_class))
    return enrich_catalog_profile(network,case,profile,product_class)


def review_payload(network,result,case,show_candidate=True,product_class=None):
    from .night_globe import globe_payload
    profile=review_profile(network,case,product_class)
    data=globe_payload(network,result,case,True,response=False)
    for marker in data['markers']:marker['score']=None
    data.update(review=True,alternative=None,response=True,case_id=case['id'],product_class=profile.get('product_class'))
    candidate_id=profile['candidate_id']
    if not show_candidate or not candidate_id or not profile.get('candidate_eligible',True):return data
    if profile.get('candidates'):
        ids={m['id'] for m in data['markers']}
        for entry in profile['candidates']:
            key=entry['company_id'];entity=network['entities'].get(key,{})
            marker=entry.get('location');place=entity.get('map_location')
            if not marker and not place:continue
            if marker:place=dict(name=marker['site'],lat=marker['lat'],lon=marker['lon'])
            if key not in ids:
                data['markers'].append(dict(id=key,name=entry.get('name',entity.get('name',key)),site=place['name'],lat=place['lat'],lon=place['lon'],role='alternative',score=None,products=entry.get('products',[]),location_source=(marker or {}).get('location_source') or (entity.get('map_location') or {}).get('source')));ids.add(key)
            shown=next(m for m in data['markers'] if m['id']==key)
            shown['products']=list(dict.fromkeys(shown.get('products',[])+entry.get('products',[])))
            if entry['recipient'] not in ids:continue
            edge=next((r for r in data['routes'] if r['kind']=='alternative' and r['start']==key and r['end']==entry['recipient']),None)
            if edge:
                if entry['material'] not in edge['material'].split(' · '):edge['material']+=' · '+entry['material']
                edge['products']=list(dict.fromkeys(edge.get('products',[])+entry.get('products',[])))
            else:data['routes'].append(dict(start=key,end=entry['recipient'],kind='alternative',material=entry['material'],products=entry.get('products',[]),sources=entry.get('sources',[entry['source']])))
        return data
    if profile['kind']=='logistics':
        place=network['logistics'].get(candidate_id)
        if not place:return data
        candidate=dict(id=candidate_id,name=place['name'],site=place['precision'],lat=place['lat'],lon=place['lon'],role='detour_port',score=None)
        suppliers={r['start'] for r in data['routes'] if r['end']==case['target']}
        customers={r['end'] for r in data['routes'] if r['start']==case['target']}
        possible=[(s,candidate_id) for s in sorted(suppliers)]+[(candidate_id,c) for c in sorted(customers)]
        kind='detour'
    else:
        entity=network['entities'].get(candidate_id,{})
        place=entity.get('map_location')
        if not place:return data
        label='Shin-Etsu · SEH' if candidate_id=='shinetsu' else '동진쎄미켐' if candidate_id=='dongjin' else entity['name']
        candidate=dict(id=candidate_id,name=label,site=place['name'],lat=place['lat'],lon=place['lon'],role='alternative',score=None)
        possible=[(candidate_id,c) for c in case['recipients']]
        kind='alternative'
    ids={m['id'] for m in data['markers']}
    if candidate_id not in ids:data['markers'].append(candidate);ids.add(candidate_id)
    for start,end in possible:
        if start in ids and end in ids:data['routes'].append(dict(start=start,end=end,kind=kind))
    return data


def review_rows_html(profile):
    rows=[]
    for label,status,detail in profile['rows']:
        tone='verified' if status in ('자료 확인','겹침 확인','관계 범위 확인') else 'unknown'
        rows.append(f'<div class="review-row"><div><b>{html.escape(label)}</b><span class="review-badge {tone}">{status}</span></div><p>{html.escape(detail)}</p></div>')
    return '<div class="review-checks">'+''.join(rows)+'</div>'


def render_review_map(data):
    from .demo_comparison import BEFORE,AFTER,change_comparison
    case=st.session_state.get('demo_applied')
    if case and case.get('id')==data.get('case_id'):
        from .impact_explanation import annotate_processes
        data=annotate_processes(st.session_state.rr_network,data,case)
    if st.session_state.get('demo_applied') and st.session_state.get('demo_step',1)>1:
        st.segmented_control('지도 비교',[BEFORE,AFTER],key='demo_compare',selection_mode='single',required=True,label_visibility='collapsed',
            default=AFTER if 'demo_compare' not in st.session_state else None,
            on_change=change_comparison,args=(st.session_state,),width='stretch',
            help='선택 사건은 유지하고 지도 표시만 비교합니다. 적용 전에는 사건 효과와 대응 후보를 숨깁니다.')
    data=prepare_map(data,st.session_state)
    if st.session_state.get('demo_basic_map') and data.get('scenario_summary'):
        st.caption(data['scenario_summary'])
    if not st.session_state.get('demo_basic_map',False):
        from .night_globe import component
        def picked():
            value=st.session_state.get('demo_night_globe')
            event=value.get('picked') if isinstance(value,dict) else getattr(value,'picked',None)
            accept_pick(st.session_state,event,data)
        component()(data=data,key='demo_night_globe',width='stretch',height=520,on_picked_change=picked)
        return
    import plotly.graph_objects as go
    lookup={m['id']:m for m in data['markers']}
    figure=go.Figure()
    for edge in data['routes']:
        a,b=lookup[edge['start']],lookup[edge['end']]
        color='#ffd166' if edge.get('status')=='cost' else '#ff5264' if edge.get('status') in ('blocked','restricted') else '#68adff' if edge['kind']=='detour' else '#4fe4db' if edge['kind']=='alternative' else '#ffad49'
        figure.add_trace(go.Scattergeo(lat=[a['lat'],b['lat']],lon=[a['lon'],b['lon']],mode='lines',
            line=dict(color=color,width=2,dash='dash' if edge.get('status')=='blocked' or edge['kind']!='primary' else 'solid'),hoverinfo='skip'))
    for marker in data['markers']:
        label=marker['name']+(' · 검토 후보' if marker['role'] in ('alternative','detour_port') else '')
        figure.add_trace(go.Scattergeo(lat=[marker['lat']],lon=[marker['lon']],text=[label],mode='markers+text',
            textposition='top right',marker=dict(size=14 if marker.get('impact')=='origin' else 8,color={'origin':'#ff5264','cost':'#ffd166','exposed':'#ffad49'}.get(marker.get('impact'),'#4fe4db')),hovertemplate='%{text}<extra></extra>'))
    figure.update_layout(height=520,showlegend=False,uirevision=data['camera_context'],margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor='#040c18',
        font=dict(color='#dceaf8',size=11),geo=dict(projection=dict(type='orthographic',rotation=dict(lon=120,lat=25)),
        bgcolor='#040c18',showland=True,landcolor='#10283a',showocean=True,oceancolor='#071324',showcountries=True,countrycolor='#34506a'))
    st.plotly_chart(figure,key='demo_review_basic_map',height=520,width='stretch',theme=None,config=dict(displayModeBar=False,topojsonURL='/app/static/'))


def render_review(network,result,case):
    from .catalog_profile import has_photoresist
    selected=st.session_state.get('demo_review_product','전체 제품군') if has_photoresist(network,case) else None
    profile=review_profile(network,case,selected)
    st.session_state.demo_review=profile
    show=st.session_state.get('demo_show_candidate',True)
    from .impact_explanation import annotate_processes
    data=prepare_map(annotate_processes(network,review_payload(network,result,case,show,selected),case),st.session_state)
    inspection=selection_description(data,case,profile)
    st.markdown('''<style>
    .review-intro{padding:9px 14px;border:1px solid #2a5966;border-radius:10px;background:#0c2533;color:#dcebf5;font-size:17px;line-height:1.4}
    .review-intro small{display:block;font-size:14px;color:#a0bdca;margin-top:3px}
    .review-checks{border:1px solid #294253;border-radius:10px;overflow:hidden;background:#0a1928}
    .review-row{padding:6px 14px;border-bottom:1px solid #233c4d}.review-row:last-child{border:0}
    .review-row>div{display:flex;justify-content:space-between;align-items:center;font-size:14px}
    .review-row p{font-size:14px;color:#9eb8cc;line-height:1.5;margin:4px 0 0}
    .review-badge{font-size:13px;border-radius:12px;padding:3px 8px;background:#243440}
    .review-badge.verified{color:#70ded2}.review-badge.unknown{color:#ffce86}
    .review-actions{border-left:2px solid #ffce86;padding:5px 10px;color:#adc4d6;font-size:14px;line-height:1.5}
    .review-actions b{color:#ead5aa}
    .review-intro.is-selected{border-color:#4fe4db;box-shadow:0 0 15px #4fe4db12}
    .review-flow{display:flex;gap:8px;color:#b6cbdc;font-size:13px;margin-top:8px}
    .review-flow span{flex:1;border:1px solid #2b465b;border-radius:8px;background:#0c1c2c;padding:12px 8px;text-align:center}
    </style>''',unsafe_allow_html=True)
    left,right=st.columns([2,1],gap='large')
    with right:
        st.subheader('선택 연결의 대응 조건' if inspection else '영향 공정과 대응 후보')
        if case.get('kind')=='logistics':
            st.caption('지도는 복수 소재의 경유·우회 검토 범위입니다. 아래 상세는 '+case['material_label']+' 대표 연결이며 경유·우회 적합성은 가정입니다.')
        if has_photoresist(network,case):
            st.selectbox('검토 제품군',['전체 제품군','ArF','KrF','i-line','EUV'],key='demo_review_product',
                         format_func=lambda s:'검토 제품군: '+s,label_visibility='collapsed',
                         on_change=clear_selection,args=(st.session_state,),
                         help='공개 제품 목록의 비교 조건입니다. 고객이 실제 사용하는 등급을 지정하거나 공급 회복을 계산하지 않습니다.')
        level='관세·비용 검토' if case.get('event')=='관세 부과' else '근거 부족 · 후보 보류' if not profile.get('candidate_eligible',True) else profile.get('level','우회 검토 후보' if profile['kind']=='logistics' else '대체 검토 후보')
        title=inspection['title'] if inspection else profile['name']
        subtitle=inspection['subtitle'] if inspection else profile['material']+' · '+level
        if inspection:st.markdown('<div class="review-intro is-selected">'+html.escape(title)+'<small>'+html.escape(subtitle)+'</small></div>',unsafe_allow_html=True)
        from .impact_cards import render_impact_cards
        render_impact_cards(network,case,profile,inspection)
        st.button('← 영향 연결 확인',key='demo_back_impact',on_click=change_step,args=(st.session_state,2))
    with left:
        render_review_map(data)
        before=st.session_state.get('demo_compare')=='적용 전'
        st.toggle('검토 후보 경로 표시',key='demo_show_candidate',on_change=clear_selection,args=(st.session_state,),disabled=before,help='점선 표시만 변경합니다. 대체 가능성이나 공급 회복을 확정하지 않습니다.')
        if before:st.caption('사건 적용으로 전환하면 대체·우회 후보 경로를 다시 볼 수 있습니다.')
        elif show and not profile.get('candidate_eligible',True):
            st.caption('선택 제품군의 근거가 부족해 후보 점선을 보류했습니다. 제품 자료를 추가 확보해야 합니다.')
        elif show and not any(m['id']==profile['candidate_id'] for m in data['markers']):
            st.caption('후보 위치를 확인하지 못해 지도에 표시하지 않았습니다. 오른쪽 자료에서 확인하세요.')
        color='#68adff' if profile['kind']=='logistics' else '#4fe4db'
        from .demo_scenarios import legend
        st.caption(legend(data))
        st.markdown('<div class="demo-result-explanation">'+html.escape(inspection['text'] if inspection else profile['summary'])+'</div>',unsafe_allow_html=True)
        if profile.get('evidence'):
            with st.expander('제품 비교·출처·확인 항목',expanded=False):
                st.toggle('기본 지도 사용 · 3D 호환성',key='demo_basic_map')
                record=profile['evidence']
                st.caption('원문 확인: '+profile['reviewed_at']+' · 제품군 겹침은 등급 호환성 판정이 아닙니다.')
                st.write(case['evidence'])
                st.write(case['limits'])
                st.table([{'제품군':c,record['source_name']:'제품 자료 있음',profile['name']:'제품 자료 있음' if c in record['candidate_classes'] else '이번 자료로 확인 못함'} for c in record['source_classes']])
                st.write(record['legal_scope'])
                for check in record['checks']:st.write('확인할 항목: '+check)
                for source in profile['sources'].values():
                    st.markdown(f"[{source['title']}]({source['url']})")
                    st.caption(source['scope']+' / 한계: '+source['limit'])

    from .simulation_candidates import render_catalog_candidates
    render_catalog_candidates(network,case,selected)
