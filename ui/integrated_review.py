"""One-screen evidence review and explicitly bounded inventory sensitivity."""
import html
import json
import streamlit as st
import plotly.graph_objects as go
from .demo_scenarios import connections
from .major_ports import major_ports
from .impact_explanation import USES
from .public_contracts import public_contracts
from relationship_audit import vendor_catalog


def coverage(days,reduction,stock):
    # Constant normalized daily demand; no replenishment, alternatives or ramp.
    missing=max(0.,days*reduction/100-stock)
    return round(100*(1-missing/days),1)


def render_integrated_review(network):
    rows=connections(network);catalog=vendor_catalog(network)
    ports={p['id']:p for p in major_ports()}
    from .presentation_scene import scene_loader,render_scene_review
    scene_loader(rows,ports)
    st.subheader('공급 차질 조건 비교')
    poster=st.toggle('요약 보기',key='integrated_poster')
    with st.expander('사건·연결·가정 설정',expanded=not poster):
        a,b=st.columns(2)
        with a:
            portkey=st.selectbox('경유 가정 항만',list(ports),format_func=lambda k:ports[k]['name'],key='integrated_port')
            options=list(range(len(rows)))
            chosen=st.multiselect('영향 검토 연결',options,default=[0],key='integrated_rows',
                format_func=lambda i:network['entities'][rows[i]['supplier']]['name']+' → '+network['entities'][rows[i]['recipient']]['name']+' / '+rows[i]['material'])
        with b:
            days=st.number_input('차질 기간 가정 · 일',1,365,30,key='integrated_days')
            reduction=st.slider('해당 연결의 도착 공급 감소 가정 · %',0,100,100,key='integrated_reduction')
            stock=st.number_input('시작 재고 · 정상 수요 기준 일',0,365,7,key='integrated_stock')
        st.caption('항만 통항 감소를 공급 감소로 자동 환산하지 않습니다. 아래 감소율은 선택 연결의 도착 공급에 직접 적용하는 별도 가정입니다.')
    port=ports[portkey];selected=[rows[i] for i in chosen]
    if not selected:
        st.info('설정에서 영향 검토 연결을 하나 이상 선택하세요.');return
    left,right=st.columns([2,1])
    with left:
        st.markdown('**'+html.escape(port['name'])+f' · {days}일 / 도착 공급 {reduction}% 감소 가정**')
        fig=go.Figure();seen=set()
        for r in selected:
            a=network['entities'][r['supplier']]['map_location'];b=network['entities'][r['recipient']]['map_location']
            name=network['entities'][r['supplier']]['name']+' → '+network['entities'][r['recipient']]['name']+' / '+r['material']
            fig.add_trace(go.Scattergeo(lat=[a['lat'],port['lat'],b['lat']],lon=[a['lon'],port['lon'],b['lon']],mode='lines',
                line=dict(color='#ffad49' if reduction else '#4fe4db',width=2,dash='dash'),text=[name+' · 경유 가정']*3,hovertemplate='%{text}<extra></extra>',showlegend=False))
            for k in (r['supplier'],r['recipient']):
                if k in seen:continue
                seen.add(k);e=network['entities'][k];p=e['map_location']
                fig.add_trace(go.Scattergeo(lat=[p['lat']],lon=[p['lon']],text=[e['name']],mode='markers+text',textposition='top center',marker=dict(size=9,color='#4fe4db'),showlegend=False))
        fig.add_trace(go.Scattergeo(lat=[port['lat']],lon=[port['lon']],text=[port['name']],mode='markers+text',textposition='bottom center',marker=dict(size=16,color='#ff5264'),showlegend=False))
        fig.update_layout(height=520,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor='#071324',font=dict(color='#dceaf8',size=11),geo=dict(projection_type='natural earth',bgcolor='#071324',showland=True,landcolor='#193245',showcountries=True,countrycolor='#365267'))
        st.plotly_chart(fig,key='integrated_map',width='stretch',theme=None,config=dict(displayModeBar=False,topojsonURL='/app/static/'))
        st.caption('🟢 企業 공급 관계 근거　🟠 점선: 항만 경유 가정　기업 대표 거점 · 선박 항적 아님'.replace('企業','기업'))
        st.markdown(f"[항만 위치 근거]({port['source']}) · {port['precision']}")
    with right:
        if st.session_state.get('integrated_detail') not in chosen:st.session_state.integrated_detail=chosen[0]
        index=st.selectbox('상세 설명 연결',chosen,format_func=lambda i:network['entities'][rows[i]['supplier']]['name']+' → '+network['entities'][rows[i]['recipient']]['name']+' / '+rows[i]['material'],key='integrated_detail')
        row=rows[index]
        st.markdown('**🟢 공급 관계 근거　🟠 경유 가정**')
        st.caption('관계 자료 연도: '+str(row['evidence'].get('relationship_source_year') or '미기재')+' · 품목별 현재 계약·물량 별도 확인')
        st.write('검토 공정: '+' · '.join(row['processes']))
        use,reason=USES.get(row['item'],('소재 투입','등록된 소재 용도와 고객 공정의 투입 조건을 확인합니다.'))
        st.write(use+' · '+reason)
        source=row['evidence'].get('relationship_source') or row['evidence'].get('source')
        if source:st.markdown('[기업 관계 출처]('+source+')')
        candidates=[v for v in catalog if v['product_group']==row['item'] and v['supplier_id']!=row['supplier']]
        st.markdown('**대체 조달 검토 · 제품 자료만 확인**')
        if not candidates:st.write('등록 후보 없음 · 추가 제품 자료 확보 필요')
        for v in candidates:st.markdown('['+v['supplier']+']('+v['source']+') · 고객 승인·등급·여력 미확인')
        material_names={v['material'].split(' · ')[-1] for v in catalog if v['product_group']==row['item']}
        announced=[r for r in public_contracts() if material_names.intersection(r['materials'])]
        for r in announced:st.caption('계약 발표·가동 미확인: '+r['supplier']+' → '+r['customer'])
        st.markdown('**다음 확인**')
        st.write('출하 공장·실제 이용 항만 → 위험물·보관·통관 → 고객 승인 → 공급량·납기 견적')
    cols=st.columns(3)
    cols[0].metric('검토 공급사',len({r['supplier'] for r in selected}))
    cols[1].metric('검토 고객사',len({r['recipient'] for r in selected}))
    cols[2].metric('재고 가정상 기간 수요 충족률',str(coverage(days,reduction,stock))+'%')
    st.caption(f'가정: 매일 정상 수요 1, 시작 재고 {stock}일분, 기간 {days}일, 도착 공급 {100-reduction}%. 재고 소진 후 부족량을 누적합니다. 대체·재입고·증산·공정 병목은 제외하며 기업 생산률을 뜻하지 않습니다.')
    with st.expander('기간·재고 가정 비교',expanded=not poster):
        compare_days=sorted({max(1,days//2),days,min(365,days*2)})
        compare_stock=sorted({0,stock,min(365,stock+7)})
        data=[{'기간 가정 · 일':d,'재고 가정 · 정상 수요 기준 일':s,'기간 수요 충족률 · %':coverage(d,reduction,s)} for d in compare_days for s in compare_stock]
        st.dataframe(data,hide_index=True)
        st.caption('충족률 = 1 − max(0, 기간 × 감소율 − 시작 재고) ÷ 기간.  \n같은 가정을 각 연결에 독립 적용하며 기업별 가중 평균은 산정하지 않습니다.')
    report=dict(port=port,connections=selected,assumptions=dict(days=days,reduction_percent=reduction,stock_days=stock),coverage_percent=coverage(days,reduction,stock),limits='가정 기반 수요 충족률; 생산률·실제 항만 경유 미확인')
    st.download_button('검토 근거·가정 내려받기',json.dumps(report,ensure_ascii=False,indent=2),file_name='presentation-review.json',mime='application/json',key='integrated_download')

    render_scene_review(network,port,selected,row,candidates,days,reduction,stock)
