"""Upper main-map exploration for all eight process stages."""
import streamlit as st
from .process_catalog import load_process_catalog,group_offerings,process_map_payload
from .candidate_explanation import explain_candidate,candidate_from_pick


def render_process_vendor_map(network,company=None,groups=None):
    st.session_state.pop('process_candidate_explanation',None)
    catalog=load_process_catalog()
    st.subheader('기업 공급 중단 시뮬레이션' if company else '공정·소재별 기업 단절과 대체 후보')
    st.caption('공식 제품군으로 후보를 비교합니다. 수요처 연결은 시뮬레이션 가정이며 실제 거래 관계가 아닙니다.')
    a,b=st.columns([1,2])
    if company:
        with a:st.write('선택 기업: **'+company+'**')
        choices={k:catalog['groups'][k] for k in groups}
    else:
        with a:stage=st.selectbox('공정',catalog['stages'],key='process_stage')
        choices={k:g for k,g in catalog['groups'].items() if g['stage']==stage}
    if st.session_state.get('process_group') not in choices:st.session_state.process_group=next(iter(choices))
    with b:gid=st.selectbox('비교할 소재·장비·서비스',list(choices),format_func=lambda k:choices[k]['name'],key='process_group')
    product_class=st.selectbox('노광 제품군',['전체 제품군','ArF','KrF','i-line','EUV'],key='process_exposure') if gid=='photoresist' else None
    entries=group_offerings(network,gid,product_class)
    if company and company not in {e['name'] for e in entries}:
        st.info('선택 기업은 이 노광 제품군에 등록된 제품 근거가 없습니다. 다른 제품군을 선택하세요.')
        return
    if not entries:st.info('현재 제품 근거가 등록되지 않은 범위입니다.');return
    byname={e['name']:e for e in entries}
    if st.session_state.get('process_origin') not in byname:st.session_state.process_origin=entries[0]['name']
    left,right=st.columns([2.1,1])
    with right:
        origin=company or st.selectbox('중단할 기업',list(byname),key='process_origin')
        recipient=st.selectbox('가정 수요처',[None,'tsmc','samsung'],index=1,
            format_func=lambda k:network['entities'][k]['name']+' · 거래 미확인' if k else '미지정 · 공급자끼리 비교',key='process_recipient')
        cut=st.toggle('기업 공급 중단 가정',value=True,key='process_cut')
        data,entries,group=process_map_payload(network,gid,origin,recipient,cut,product_class)
        candidates=[e for e in entries if e['name']!=origin]
        st.metric('동일 품목군의 다른 기업 후보',len(candidates))
        if not candidates:
            st.info('이 품목에 등록된 다른 기업 근거가 없습니다. 관련 공정의 다른 품목을 대체재로 연결하지 않습니다.')
        else:
            names=[e['name'] for e in candidates]
            if st.session_state.get('process_candidate') not in names:st.session_state.process_candidate=names[0]
            selected=st.selectbox('후보 설명',names,key='process_candidate')
            entry=byname[selected]
            # Keep server rerenders and dropdown changes aligned with WebGL picking.
            if entry['location']:
                data['selected']=dict(kind='marker',id=entry['map_id'],context=data['context'])
            explanation=explain_candidate(gid,group,origin,entry,product_class)
            st.session_state.process_candidate_explanation=explanation
            st.markdown('**'+explanation['title']+'**')
            st.markdown('**대신 공급할 품목**')
            st.write(explanation['supply'])
            st.write(' / '.join(explanation['products']))
            st.markdown('**왜 대체 후보인가요?**')
            st.write(explanation['reason'])
            st.markdown('**실제 전환에 필요한 조건**')
            for i,condition in enumerate(explanation['conditions'],1):st.write(f'{i}. {condition}')
            st.caption(explanation['limit'])
            with st.expander('제품 근거 · 출처'):
                for i,source in enumerate(entry['sources']):st.markdown(f'[제품 근거 {i+1}]({source})')
            location=entry['location']
            if location:
                st.caption(location['site']+' · '+location['precision'])
                if location.get('location_source'):st.markdown('[사업장 주소 근거]('+location['location_source']+')')
            else:st.caption('위치 미확인 · 목록에는 유지하고 지도와 연결선은 보류합니다.')
    with left:
        if st.session_state.get('demo_basic_map'):
            import plotly.graph_objects as go
            fig=go.Figure();lookup={m['id']:m for m in data['markers']}
            for r in data['routes']:
                x,y=lookup[r['start']],lookup[r['end']]
                focus=data.get('selected',{}).get('id')
                active=not focus or focus in (r['start'],r['end'])
                fig.add_trace(go.Scattergeo(lat=[x['lat'],y['lat']],lon=[x['lon'],y['lon']],mode='lines',
                    opacity=1 if active else .18,
                    line=dict(color='#ff5264' if r['status']=='blocked' else '#4fe4db',width=4 if focus and active else 2,dash='dash'),
                    text=[r['material']]*2,hovertemplate='%{text}<extra></extra>',showlegend=False))
            for m in data['markers']:
                focus=data.get('selected',{}).get('id')
                fig.add_trace(go.Scattergeo(lat=[m['lat']],lon=[m['lon']],text=[m['name']],mode='markers+text',
                    marker=dict(size=16 if m['id']==focus else 10,color='#ff5264' if m['impact']=='origin' else '#4fe4db'),showlegend=False))
            fig.update_layout(height=540,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor='#071324',font=dict(color='#dceaf8'),
                geo=dict(projection_type='natural earth',showland=True,landcolor='#193245',bgcolor='#071324'))
            st.plotly_chart(fig,key='process_basic_map',width='stretch',theme=None,config=dict(displayModeBar=False,topojsonURL='/app/static/'))
        else:
            from .night_globe import component
            def picked():
                value=st.session_state.get('process_vendor_globe')
                event=value.get('picked') if isinstance(value,dict) else getattr(value,'picked',None)
                name=candidate_from_pick(data,entries,origin,event)
                if name:st.session_state.process_candidate=name
            component()(data=data,key='process_vendor_globe',width='stretch',height=540,on_picked_change=picked)
        st.caption('빨강: 선택 기업 중단 가정 · 청록 점선: 대체 조달 검토 · 본사/소재 도시 참고 위치 · 실제 운송 항적 아님')
        if data.get('selected'):st.caption('강조: '+st.session_state.process_candidate+' 및 연결 경로 · 나머지 경로는 흐리게 표시')
        if data['missing_locations']:st.info('위치 확인 대기: '+' · '.join(data['missing_locations']))
    st.session_state.process_current_map=data
    if company:st.session_state.demo_current_map=data
    with st.expander('전체 기업·제품·위치 근거'):
        st.dataframe([{'기업':e['name'],'제품':' / '.join(e['products']),
            '표시 위치':e['location']['site'] if e['location'] else '위치 미확인',
            '좌표 범위':e['location']['precision'] if e['location'] else '미확인',
            '제품 출처':e['sources'][0],
            '주소 출처':(e['location'] or {}).get('location_source'),
            '좌표 출처':(e['location'] or {}).get('coordinate_source')} for e in entries],hide_index=True,width='stretch',
            column_config={k:st.column_config.LinkColumn(k) for k in ('제품 출처','주소 출처','좌표 출처')})
        st.caption(catalog['limits'])
