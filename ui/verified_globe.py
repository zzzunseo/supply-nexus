"""Use the existing interactive 3D globe for geographically bounded evidence."""
def evidence_globe_data(case,stage=3,after=True):
    def point(key,name,lat,lon,label):
        return dict(id=key,name=name,lat=lat,lon=lon,site='지리적 개략 대표점',role='location',role_label=label,impact='normal',score=None)
    if case=='fire':
        markers=[point('akm','AKM · 노베오카 피해 공장',32.58,131.66,'기존 AK4493 · 공장 도시'),point('rme','RME · 독일',48.32,11.55,'ADI-2 DAC · 고객 제품'),point('ess','ESS · 미국',37.43,-121.9,'대체 ES9028Q2M · 기업 연락 권역')]
        replacement=stage==3 and after
        supplier='ess' if replacement else 'akm'
        markers=[m for m in markers if m['id'] in (supplier,'rme')]
        routes=[dict(start=supplier,end='rme',kind='alternative' if replacement else 'primary',status='blocked' if stage==2 else 'candidate' if replacement else 'normal',material='부품 채택 관계 · 실제 운송 경로 아님',disruption_label='공장 화재 · 공급 제약')]
        if stage==2:markers[0]['impact']='origin'
        camera=dict(lat=48,lon=-45 if replacement else 76,distance=3.5)
        label='공식 공장 피해·부품 전환 · AKM → ESS / 고객 RME'
    elif case=='material':
        markers=[point('klm','Freescale KLM · 쿠알라룸푸르',3.14,101.69,'동일 사업장 · Au → PdCu')]
        routes=[];camera=dict(lat=12,lon=105,distance=2.5)
        label='공식 소재 변경 · 말레이시아 / 도시 대표점'
    else:
        markers=[point('indian','인도양 방향',12,65,'연결도 기준점'),point('redsea','홍해 입구 방향',12,44,'기존 통항 방향'),
            point('suez','수에즈 방향',30,32,'기존 통항 방향'),point('med','지중해 방향',35,20,'연결도 기준점'),
            point('southindian','인도양 남부',-20,58,'개략 우회 방향'),point('cape','희망봉 방향',-35,20,'공식 우회 발표'),
            point('southatlantic','남대서양 방향',-20,0,'개략 우회 방향'),point('atlantic','북대서양 방향',35,-15,'연결도 기준점')]
        routes=[]
        for kind,path in [('primary',['indian','redsea','suez','med']),('detour',['indian','southindian','cape','southatlantic','atlantic'])]:
            for start,end in zip(path,path[1:]):routes.append(dict(start=start,end=end,kind=kind,status='normal' if kind=='primary' else 'candidate',material='선사 우회 발표 · 화물 종류 미확인'))
        camera=dict(lat=1,lon=31,distance=3.4)
        label='홍해 사태 · 희망봉 우회 / 실제 항적이 아닌 개략도'
    if case=='material':
        markers[0]['role_label']='대체 · PdCu 20μm' if stage==3 and after else '기존 · 금(Au) 23μm' if stage!=2 else '비용·조달 조건 검토'
        if stage==2:markers[0]['impact']='cost'
    elif case!='fire':
        routes=[r for r in routes if r['kind']==('detour' if stage==3 and after else 'primary')]
        ids={k for r in routes for k in (r['start'],r['end'])}
        markers=[m for m in markers if m['id'] in ids]
        if stage==2:
            for r in routes:r['status']='restricted'
    label+=f' · {stage}단계'
    return dict(markers=markers,routes=routes,review=True,applied=False,response=False,alternative=None,
        title=label,status_label=label,process='',material='',context='verified-3d-'+case+str(stage)+str(after),camera_context='verified-3d-'+case+str(stage)+str(after),camera_focus=camera,selected=None)


def render_evidence_globe(case,stage=3,after=True):
    import streamlit as st
    data=evidence_globe_data(case,stage,after)
    if st.session_state.get('demo_basic_map',False):
        import plotly.graph_objects as go
        figure=go.Figure()
        lookup={m['id']:m for m in data['markers']}
        for route in data['routes']:
            start,end=lookup[route['start']],lookup[route['end']]
            color='#ff5264' if route.get('status') in ('blocked','restricted') else '#4fe4db' if route['kind'] in ('alternative','detour') else '#ffad49'
            figure.add_trace(go.Scattergeo(lat=[start['lat'],end['lat']],lon=[start['lon'],end['lon']],mode='lines',line=dict(color=color,width=3),hoverinfo='skip'))
        for marker in data['markers']:
            figure.add_trace(go.Scattergeo(lat=[marker['lat']],lon=[marker['lon']],mode='markers+text',text=[marker['name']],textposition='top center',marker=dict(size=13,color='#ff5264' if marker.get('impact')=='origin' else '#4fe4db'),hovertext=[marker['role_label']],hovertemplate='%{hovertext}<extra></extra>'))
        figure.update_layout(height=520,showlegend=False,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor='#040c18',font=dict(color='#dceaf8'),geo=dict(projection_type='natural earth',bgcolor='#040c18',showland=True,landcolor='#10283a',showcountries=True,countrycolor='#34506a'))
        st.plotly_chart(figure,key='verified_basic_'+case,width='stretch',theme=None,config=dict(displayModeBar=False,topojsonURL='/app/static/'))
        return
    from .night_globe import component
    component()(data=data,key='verified_globe_'+case,width='stretch',height=520)
