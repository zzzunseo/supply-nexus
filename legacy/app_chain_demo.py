"""Single-file demo: streamlit run app_chain_demo.py --server.port 8518.

All companies, supply relations, capacities and facility placements are fictional.
The original, researched dashboard remains in app.py. No API calls in test mode.
"""
import html
import json
import math
import os
import re
from collections import defaultdict
from functools import lru_cache
from urllib.request import Request, urlopen

import plotly.graph_objects as go
import streamlit as st

PROCESSES = ['웨이퍼 제조', '산화', '포토', '식각', '증착·이온주입', '금속배선', 'EDS', '패키징']
REGIONS = {
    '일본 규슈': (32.8, 130.7), '일본 도호쿠': (38.3, 140.9), '일본 간토': (35.7, 139.7),
    '한국 경기': (37.3, 127.0), '대만 신주': (24.8, 121.0), '미국 애리조나': (33.4, -112.1),
    '미국 텍사스': (30.3, -97.7), '네덜란드': (51.4, 5.5), '독일 드레스덴': (51.0, 13.7),
    '프랑스': (45.2, 5.7), '싱가포르': (1.35, 103.8), '말레이시아 페낭': (5.4, 100.3),
}
# process, material, original region, core region, alternative region, reserved fraction
# Add a row to extend the model. Each row generates five named, editable nodes.
SAMPLES = [
    ('포토', '감광 원료 A', '일본 규슈', '한국 경기', '미국 텍사스', .60),
    ('포토', '광학 부품 B', '네덜란드', '대만 신주', '독일 드레스덴', .40),
    ('웨이퍼 제조', '실리콘 원료 A', '일본 도호쿠', '한국 경기', '미국 애리조나', .55),
    ('웨이퍼 제조', '연마 패드 B', '일본 간토', '대만 신주', '싱가포르', .45),
    ('산화', '고순도 산소 A', '프랑스', '한국 경기', '미국 텍사스', .65),
    ('산화', '수소 정제 부품 B', '독일 드레스덴', '대만 신주', '말레이시아 페낭', .50),
    ('식각', '식각 가스 A', '일본 간토', '한국 경기', '싱가포르', .40),
    ('식각', '플라스마 부품 B', '미국 애리조나', '대만 신주', '독일 드레스덴', .60),
    ('증착·이온주입', '박막 전구체 A', '일본 규슈', '한국 경기', '프랑스', .60),
    ('증착·이온주입', '이온원 부품 B', '미국 텍사스', '대만 신주', '싱가포르', .45),
    ('금속배선', '구리 전구체 A', '독일 드레스덴', '한국 경기', '미국 텍사스', .55),
    ('금속배선', '배선 장비 부품 B', '일본 간토', '대만 신주', '네덜란드', .50),
    ('EDS', '프로브 소재 A', '일본 도호쿠', '한국 경기', '미국 애리조나', .60),
    ('EDS', '테스트 보드 B', '미국 텍사스', '대만 신주', '말레이시아 페낭', .50),
    ('패키징', '기판 원료 A', '일본 규슈', '한국 경기', '싱가포르', .60),
    ('패키징', '접합 소재 B', '말레이시아 페낭', '대만 신주', '미국 텍사스', .40),
]


def make_network():
    nodes, cores, processes = {}, {}, {p: [] for p in PROCESSES}
    def add(node_id, name, kind, region, requires, index, **extra):
        lat, lon = REGIONS[region]
        # Small offsets separate symbols. These are representative display positions.
        angle = index * 2.4
        nodes[node_id] = dict(id=node_id, name=name, kind=kind, region=region,
            lat=lat + 2*math.sin(angle), lon=lon + 3*math.cos(angle), requires=requires,
            status='가정값', source='단일 파일 시연용 가상 데이터', source_year=None, **extra)
    for i, (p, material, region, core_region, alt_region, capacity) in enumerate(SAMPLES):
        mid, vid, aid, av, cid = [f'{prefix}{i:02d}' for prefix in ('m', 'v', 'am', 'av', 'c')]
        add(mid, material, 'material', region, [], i)
        add(vid, f'가상 {material} 벤더', 'vendor', region, [mid], i+1)
        add(aid, f'대체용 {material}', 'alt_material', alt_region, [], i+2)
        add(av, f'가상 대체 벤더 {i+1:02d}', 'alt_vendor', alt_region, [aid], i+3, capacity=1.0)
        add(cid, f'가상 {p} 코어 {i+1:02d}', 'core', core_region, [vid], i+4)
        cores[cid] = dict(node_id=cid, processes=[p], alt_vendor=dict(id=av,
            name=nodes[av]['name'], region=alt_region, status='가정값', source='시연용 가상 대체 계약', source_year=None),
            alt_capacity=capacity, status='가정값', source='시연용 예약 대체 비중', source_year=None)
        processes[p].append(cid)
    return dict(nodes=nodes, tier1=cores, processes=processes)


def calculate_supply_shock(network, shocks=None, enable_bypass=True):
    """AND dependencies; alternative throughput is additive and capped at demand.

    primary = min(direct operation, required input operation)
    requested backup = min(1-primary, core.alt_capacity)
    allocated backup shares each vendor's available pool proportionally.
    process score = 100 * min(core effective outputs). No fabricated score floor.
    """
    nodes, cores = network['nodes'], network['tier1']
    shocks = dict(shocks or {})
    for key, value in shocks.items():
        if key not in nodes or type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('타격 대상과 감소율(0~1)을 확인하세요.')
    raw, visiting = {}, set()
    def resolve(node_id):
        if node_id in raw:
            return raw[node_id]
        if node_id not in nodes or node_id in visiting:
            raise ValueError('공급망에 누락된 의존성 또는 순환이 있습니다.')
        visiting.add(node_id)
        raw[node_id] = min([1-shocks.get(node_id, 0)] + [resolve(k) for k in nodes[node_id]['requires']])
        visiting.remove(node_id)
        return raw[node_id]
    for node_id in nodes:
        resolve(node_id)
    requests = defaultdict(dict)
    for cid, core in cores.items():
        cap, alt_id = core['alt_capacity'], core['alt_vendor']['id']
        if type(cap) not in (int,float) or not math.isfinite(cap) or not 0 <= cap <= 1 or alt_id not in nodes:
            raise ValueError('대체 벤더와 alt_capacity를 확인하세요.')
        if alt_id in nodes[cid]['requires']:
            raise ValueError('동일 벤더를 주 공급과 대체 공급으로 중복 지정할 수 없습니다.')
        requests[alt_id][cid] = min(1-raw[cid], cap) if enable_bypass else 0
    result = {cid: dict(primary=raw[cid], backup=0.0, effective=raw[cid]) for cid in cores}
    for alt_id, demands in requests.items():
        capacity = nodes[alt_id].get('capacity', 1.0)
        if type(capacity) not in (int,float) or not math.isfinite(capacity) or capacity < 0:
            raise ValueError('대체 벤더의 공급 풀을 확인하세요.')
        pool, total = capacity * raw[alt_id], sum(demands.values())
        scale = min(1.0, pool/total) if total else 0
        for cid, requested in demands.items():
            backup = requested * scale
            result[cid].update(backup=backup, effective=min(1.0, raw[cid]+backup))
    scores = {p: round(100*min(result[c]['effective'] for c in required), 4)
              for p, required in network['processes'].items()}
    return dict(raw=raw, tier1=result, scores=scores, overall=min(scores.values()),
        affected=[c for c in cores if raw[c] < 1-1e-9],
        bypass=[c for c,r in result.items() if r['backup'] > 1e-9])


def interpret_issue(text, network, mode='테스트'):
    """Local test mode or optional explicitly selected OpenAI interpretation."""
    if text.strip() in ('초기화', '정상 복구', '정상복구'):
        return [], 0, 'reset', '누적 이슈를 해제했습니다.'
    if '관세' in text:
        return [], 0, 'blocked', '관세를 생산 감소율로 바꿀 수 없습니다. 이 시연은 공급·가동 감소 이슈를 계산합니다.'
    nodes = network['nodes']
    if mode == 'OpenAI':
        if not api_ready():
            raise ValueError('발표용 OpenAI 연결이 준비되지 않았습니다.')
        properties = {'target_ids':{'type':'array','items':{'type':'string'}},
            'loss_pct':{'type':['number','null']}, 'unresolved':{'type':'array','items':{'type':'string'}}}
        payload = dict(model=os.environ['OPENAI_MODEL'], store=False, max_output_tokens=1500,
            instructions='가상 공급망의 시연 입력을 해석한다. catalog에 있는 정확한 ID만 선택한다. 지역은 그 지역의 노드를 선택한다. 소재/기업명이 특정되면 그 대상만 선택한다. 새 공장이나 사건 사실을 만들지 않는다. 모르는 대상·관세·모호한 방향은 unresolved에 기록한다. loss_pct는 공급 감소율이다. 가동률은 100에서 빼며, 값이 없으면 null이다.',
            input=json.dumps(dict(message=text,catalog=[{k:n[k] for k in ('id','name','kind','region')} for n in nodes.values()]),ensure_ascii=False),
            text={'format':{'type':'json_schema','name':'demo_shock','strict':True,'schema':dict(type='object',additionalProperties=False,properties=properties,required=list(properties))}})
        request = Request('https://api.openai.com/v1/responses', data=json.dumps(payload).encode(),
            headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ['OPENAI_API_KEY']})
        try:
            with urlopen(request,timeout=35) as response:
                reply=json.load(response)
            if reply.get('status')!='completed':
                raise ValueError('미완성 응답')
            extracted=json.loads(''.join(c['text'] for m in reply.get('output',[]) if m.get('type')=='message'
                for c in m.get('content',[]) if c.get('type')=='output_text'))
        except Exception:
            raise ValueError('OpenAI 해석에 실패했습니다. 테스트 모드로 다시 입력하세요.') from None
        targets, loss = extracted['target_ids'], extracted['loss_pct']
        if extracted['unresolved']:
            return [],0,'blocked','추가 확인 필요: '+', '.join(extracted['unresolved'])
    else:
        if re.search(r'증가|관세|Nokia|노키아',text,re.I):
            return [],0,'blocked','이 입력은 등록된 공급 감소 이슈로 해석하지 못했습니다.'
        # Exact named nodes take priority over a region, so a material does not
        # accidentally become a whole-region outage.
        targets,spans=[],[]
        for key,node in sorted(nodes.items(),key=lambda pair:-len(pair[1]['name'])):
            for match in re.finditer(re.escape(node['name']),text):
                if not any(match.start()<end and match.end()>start for start,end in spans):
                    targets.append(key);spans.append(match.span());break
        targets += [k for k in nodes if re.search(r'\b'+re.escape(k)+r'\b',text)]
        if not targets:
            regions=[r for r in REGIONS if r in text or r.split()[-1] in text or r.split()[0] in text]
            # A specific subregion takes precedence over its country.
            specific=[r for r in regions if len(r.split())>1 and (r in text or r.split()[-1] in text)]
            regions=specific or regions
            targets=[k for k,n in nodes.items() if n['region'] in regions]
            if '소재' in text or '원료' in text:
                targets=[k for k in targets if nodes[k]['kind'] in ('material','alt_material')]
        percentages=re.findall(r'(-?\d+(?:\.\d+)?)\s*(?:%|퍼센트)',text)
        if len(percentages)>1:
            return [],0,'blocked','공급 감소율을 하나만 입력하세요.'
        loss=float(percentages[0]) if percentages else None
        if loss is not None and '가동률' in text and not re.search(r'감소|하락',text):
            loss=100-loss
        if '복구' in text:
            loss=0
    if not isinstance(targets,list) or any(not isinstance(k,str) for k in targets):
        raise ValueError('해석된 대상 형식을 확인하지 못했습니다.')
    if not targets or any(k not in nodes for k in targets):
        return [],0,'blocked','등록된 대상이 없습니다. 예: 규슈 소재 100% 중단 / 감광 원료 A 공급 80% 감소'
    if loss is not None and (type(loss) not in (int,float) or not math.isfinite(loss) or not 0 <= loss <= 100):
        raise ValueError('감소율은 0~100%로 입력하세요.')
    note='감소율 미지정: 시연용 100% 중단을 가정했습니다.' if loss is None else f'공급 능력 {loss:g}% 감소 가정.'
    return list(dict.fromkeys(targets)), (100 if loss is None else loss)/100, 'apply', note


def api_ready():
    return os.environ.get('SUPPLY_OPENAI_ENABLED')=='1' and bool(os.environ.get('OPENAI_API_KEY')) and bool(os.environ.get('OPENAI_MODEL'))


def xyz(lat, lon, radius=1):
    a,b=math.radians(lat),math.radians(lon)
    return (radius*math.cos(a)*math.cos(b),radius*math.cos(a)*math.sin(b),radius*math.sin(a))


def arc(a,b):
    u,v=xyz(a['lat'],a['lon']),xyz(b['lat'],b['lon'])
    omega=math.acos(max(-1,min(1,sum(x*y for x,y in zip(u,v)))))
    points=[]
    for i in range(31):
        t=i/30
        q=[(1-t)*x+t*y for x,y in zip(u,v)] if omega<1e-6 else [
            (math.sin((1-t)*omega)*x+math.sin(t*omega)*y)/math.sin(omega) for x,y in zip(u,v)]
        norm=math.sqrt(sum(x*x for x in q)) or 1
        points.append(tuple(x/norm*(1.025+.22*math.sin(math.pi*t)) for x in q))
    return points


@lru_cache(maxsize=1)
def sphere():
    return tuple([[xyz(-90+i*3, -180+j*3)[axis] for j in range(121)] for i in range(61)] for axis in range(3))


def build_globe(network, result):
    nodes=network['nodes']
    x,y,z=sphere()
    fig=go.Figure(go.Surface(x=x,y=y,z=z,surfacecolor=[[0]*121 for _ in range(61)],
        colorscale=[[0,'#0D3050'],[1,'#0D3050']],showscale=False,hoverinfo='skip',
        lighting=dict(ambient=.85,diffuse=.8,specular=.5),lightposition=dict(x=-150,y=220,z=200)))
    # Simplified continent outlines embedded in this file; no map/texture download.
    outlines=[[(70,-165),(50,-130),(30,-115),(15,-85),(30,-80),(50,-55),(70,-85),(70,-165)],
        [(12,-80),(-5,-80),(-30,-70),(-55,-70),(-35,-45),(0,-50),(12,-80)],
        [(35,-10),(60,0),(70,40),(60,90),(65,150),(45,145),(30,120),(5,105),(20,75),(30,45),(35,-10)],
        [(35,-15),(30,30),(10,50),(-35,20),(-30,10),(0,-15),(35,-15)],
        [(-10,115),(-20,150),(-38,145),(-35,115),(-10,115)]]
    gx,gy,gz=[],[],[]
    for outline in outlines+[[(-85+i*5,lon) for i in range(35)] for lon in range(-180,180,30)]+[[(lat,-180+i*5) for i in range(73)] for lat in range(-60,90,30)]:
        for lat,lon in outline:
            a,b,c=xyz(lat,lon,1.004);gx.append(a);gy.append(b);gz.append(c)
        gx.append(None);gy.append(None);gz.append(None)
    fig.add_trace(go.Scatter3d(x=gx,y=gy,z=gz,mode='lines',line=dict(color='#28536A',width=1),hoverinfo='skip',showlegend=False))
    groups={k:dict(x=[],y=[],z=[],text=[]) for k in ('정상','타격 경로','우회 공급')}
    visible=set(k for k,n in nodes.items() if n['kind'] not in ('alt_vendor','alt_material'))
    def add_route(a,b,rate,bypass=False):
        key='우회 공급' if bypass else '타격 경로' if rate<1-1e-9 else '정상'
        g=groups[key]
        for px,py,pz in arc(a,b):
            g['x'].append(px);g['y'].append(py);g['z'].append(pz)
            g['text'].append(f"{a['name']} → {b['name']}<br>{rate*100:.1f}% · 가상 모델")
        for axis in ('x','y','z'):g[axis].append(None)
        g['text'].append('')
    for key,node in nodes.items():
        if node['kind'] in ('alt_material','alt_vendor'):
            continue
        for upstream in node['requires']:
            add_route(nodes[upstream],node,min(result['raw'][upstream],result['raw'][key]))
    destinations=[]
    for index,(process,required) in enumerate(network['processes'].items()):
        # Process nodes are display destinations, not real factories.
        destination=dict(name=process+' 공정 표시점',lat=7+index*3.8,lon=145+index*.8)
        destinations.append((process,destination))
        for cid in required:
            add_route(nodes[cid],destination,result['tier1'][cid]['primary'])
            if result['tier1'][cid]['backup']>1e-9:
                av=network['tier1'][cid]['alt_vendor']['id']
                visible.add(av)
                for mid in nodes[av]['requires']:
                    visible.add(mid);add_route(nodes[mid],nodes[av],result['raw'][av],True)
                add_route(nodes[av],destination,result['tier1'][cid]['backup'],True)
    for key,color,width,dash in [('정상','#286078',1.5,'solid'),('타격 경로','#FF647E',3,'dash'),('우회 공급','#4DE5F4',5,'solid')]:
        g=groups[key]
        if g['x']:
            fig.add_trace(go.Scatter3d(**g,mode='lines',name='정상 경로' if key=='정상' else key,
                line=dict(color=color,width=width,dash=dash),hovertemplate='%{text}<extra></extra>'))
    pc=[xyz(d['lat'],d['lon'],1.03) for _,d in destinations]
    fig.add_trace(go.Scatter3d(x=[p[0] for p in pc],y=[p[1] for p in pc],z=[p[2] for p in pc],mode='markers',
        marker=dict(size=4,symbol='diamond',color=['#4DE5F4' if result['scores'][p]>=100 else '#FFC66D' for p,_ in destinations]),
        text=[f'{p} · {result["scores"][p]:.0f}점<br>공정 표시점 · 실제 시설 아님' for p,_ in destinations],hovertemplate='%{text}<extra></extra>',showlegend=False))
    shown=[nodes[k] for k in sorted(visible)]
    coords=[xyz(n['lat'],n['lon'],1.026) for n in shown]
    fig.add_trace(go.Scatter3d(x=[p[0] for p in coords],y=[p[1] for p in coords],z=[p[2] for p in coords],
        mode='markers',marker=dict(size=[5 if n['kind']=='core' else 3 for n in shown],
        color=['#FF647E' if result['raw'][n['id']]<1-1e-9 else '#4DE5F4' if n['kind']=='alt_vendor' else '#77A9BE' for n in shown]),
        text=[f"{n['name']}<br>{n['region']} · 기존 가용 {result['raw'][n['id']]*100:.0f}%" for n in shown],
        hovertemplate='%{text}<extra></extra>',showlegend=False))
    labels=sorted(shown,key=lambda n:(result['raw'][n['id']]>=1-1e-9,n['kind']!='core',n['id']))
    selected=[]
    for n in labels:
        if len(selected)>=6:break
        if sum(a*b for a,b in zip(xyz(n['lat'],n['lon']),(-.8,1.1,.55)))<0:continue
        if any(n['region']==m['region'] for m in selected):continue
        if all((n['lat']-m['lat'])**2+((n['lon']-m['lon']+180)%360-180)**2>400 for m in selected):selected.append(n)
    points=[xyz(n['lat'],n['lon'],1.06) for n in selected]
    fig.add_trace(go.Scatter3d(x=[p[0] for p in points],y=[p[1] for p in points],z=[p[2] for p in points],
        mode='text',text=[('× ' if result['raw'][n['id']]<1e-9 else '△ ' if result['raw'][n['id']]<1-1e-9 else '')+n['region'] for n in selected],
        textfont=dict(size=11,color='#CDECF6'),hoverinfo='skip',showlegend=False))
    axis=dict(visible=False,range=[-1.28,1.28],showbackground=False)
    fig.update_layout(template='plotly_dark',margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor='rgba(0,0,0,0)',
        scene=dict(xaxis=axis,yaxis=axis,zaxis=axis,aspectmode='manual',aspectratio=dict(x=2,y=2,z=2),bgcolor='rgba(0,0,0,0)',
            camera=dict(eye=dict(x=-1.3,y=1.8,z=.9),projection=dict(type='orthographic'))),
        legend=dict(orientation='h',x=.5,xanchor='center',y=0,font=dict(size=10)),
        uirevision='chain-demo-camera-v3',showlegend=True)
    return fig


CSS='''<style>
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{height:100dvh!important;overflow:hidden!important;background:#060D17;color:#E1ECF6}
[data-testid="stHeader"],footer{display:none!important}.block-container{height:100dvh!important;max-width:none!important;padding:12px 18px!important;overflow:hidden!important}
.block-container>[data-testid="stVerticalBlock"]{height:100%;gap:10px;min-height:0}.block-container>[data-testid="stVerticalBlock"]>[data-testid="stHorizontalBlock"]{flex:1;min-height:0}
.block-container>[data-testid="stVerticalBlock"]>[data-testid="stLayoutWrapper"]{flex:1!important;min-height:0}
.block-container>[data-testid="stVerticalBlock"]>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]{height:100%!important;overflow:hidden!important}
[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]{height:100%;min-height:0;overflow:hidden}[data-testid="stColumn"]>[data-testid="stVerticalBlock"]{height:100%;min-height:0;gap:8px}
.st-key-left_panel,.st-key-center_panel,.st-key-right_panel{height:100%;min-height:0;border:1px solid #24394C;border-radius:12px;padding:14px;background:#0B1524;overflow:hidden}
.st-key-left_panel>[data-testid="stVerticalBlock"],.st-key-center_panel>[data-testid="stVerticalBlock"],.st-key-right_panel>[data-testid="stVerticalBlock"]{height:100%;min-height:0;gap:10px}
.st-key-center_panel{background:radial-gradient(ellipse,#10283F,#07101C 70%)}.st-key-right_panel{gap:8px!important}.st-key-right_panel [data-testid="stElementContainer"]:has(>[data-testid="stMarkdown"]){height:auto!important;min-height:min-content!important}.st-key-causes_box{flex:0 0 auto;gap:6px!important}.st-key-chat_box{min-height:0;gap:8px!important}
.panel-title{font-size:16px;font-weight:650;line-height:24px;min-height:24px}.st-key-left_panel>[data-testid="stElementContainer"],.st-key-causes_box>[data-testid="stElementContainer"],.st-key-chat_box>[data-testid="stElementContainer"]{flex-shrink:0!important}.st-key-causes_box>[data-testid="stElementContainer"]:first-child,.st-key-chat_box>[data-testid="stElementContainer"]:first-child{height:24px!important;min-height:24px!important;flex:0 0 24px!important}.st-key-chat_box>[data-testid="stElementContainer"]:last-child{height:45px!important;min-height:45px!important;flex:0 0 45px!important}.st-key-chat_box>[data-testid="stLayoutWrapper"]:has(>[data-testid="stForm"]){margin-top:auto}.st-key-left_panel>[data-testid="stElementContainer"]:has([data-testid="stButton"]){margin-top:auto}
.app-title{display:flex;justify-content:space-between;align-items:center;height:42px}.app-title b{font-size:21px}.tag{font-size:10px;color:#9FB6C9;border:1px solid #30465F;padding:4px 8px;border-radius:20px}
h3{font-size:16px!important;padding:0!important;margin:0!important}p{margin:0!important}.score-row{display:flex;justify-content:space-between;align-items:center;border:1px solid #284153;border-radius:7px;margin-bottom:5px;padding:7px 9px;height:clamp(31px,calc((100dvh - 340px)/8),62px);font-size:12px;background:#0D1D2D}.score-row strong{font:22px Consolas,monospace}.hint{font-size:10px;color:#9AB1C5;line-height:1.5}.cause{font-size:11px;line-height:1.6;border-left:3px solid #FF647E;padding:6px 8px;background:#112235;margin:6px 0}.cause b{color:#4DE5F4}.chat-answer{font-size:11px;line-height:1.7;padding:10px;border:1px solid #2C465C;border-radius:7px;background:#0B2032;overflow-wrap:anywhere}.chat-question{font-size:10px;color:#8FA9BE;margin-bottom:5px}
[data-testid="stCaptionContainer"]{font-size:10px!important;line-height:1.5}label p,[data-testid="stCheckbox"] p{font-size:11px!important}[data-testid="stForm"]{padding:10px!important;gap:5px}[data-testid="stPlotlyChart"]{min-height:0!important}
.st-key-chat_box [data-testid="stVerticalBlock"]{gap:7px}.stButton button,[data-testid="stFormSubmitButton"] button{font-size:11px;min-height:30px;padding:4px 10px}.stSelectbox label,.stTextInput label{font-size:11px}
@media(max-height:780px){.block-container{padding:8px!important}.st-key-left_panel,.st-key-center_panel,.st-key-right_panel{padding:10px}.score-row{padding:4px 7px}.cause{font-size:10px;padding:4px 6px}.chat-answer{font-size:10px;padding:7px}.app-title{height:32px}.app-title b{font-size:17px}}
</style>'''


def main():
    st.set_page_config(page_title='연쇄 타격 · 벤더 우회',page_icon='🌐',layout='wide')
    st.markdown(CSS,unsafe_allow_html=True)
    network=make_network()
    for key,value in dict(shocks={},last_query='시연 준비 완료',reply='규슈 소재 100% 중단을 입력하면 연쇄 영향과 우회 공급을 볼 수 있습니다.').items():
        st.session_state.setdefault(key,value)
    st.markdown('<div class="app-title"><b>🌐 공급망 연쇄 타격 · 벤더 우회</b><span class="tag">16개 가상 코어 · 전부 시연 가정 · 지역 대표 좌표</span></div>',unsafe_allow_html=True)
    left,center,right=st.columns([2,5,3],gap='small',wrap=False)
    with left,st.container(key='left_panel',height='stretch'):
        st.markdown('<div class="panel-title">8대 공정 점수</div>',unsafe_allow_html=True)
        bypass=st.checkbox('대체 벤더 우회 적용',value=True,key='bypass')
        result=calculate_supply_shock(network,st.session_state.shocks,bypass)
        for process,score in result['scores'].items():
            color='#4DE5F4' if score>=100-1e-9 else '#FF647E' if score<=1e-9 else '#FFC66D'
            symbol='●' if score>=100-1e-9 else '×' if score<=1e-9 else '△'
            st.markdown(f'<div class="score-row"><span>{symbol} {process}</span><strong style="color:{color}">{score:.0f}</strong></div>',unsafe_allow_html=True)
        st.markdown(f'<div class="hint">전체 병목 <b>{result["overall"]:.0f}점</b> · 타격 코어 {len(result["affected"])}개<br>우회 가동 {len(result["bypass"])}개 · 입력 이슈는 누적 적용</div>',unsafe_allow_html=True)
        if st.button('전체 정상 복구',width='stretch'):
            st.session_state.shocks={};st.session_state.reply='모든 타격을 해제했습니다.';st.rerun()
    with center,st.container(key='center_panel',height='stretch'):
        st.markdown('<div class="panel-title">소재 → 벤더 → 코어 → 공정</div>',unsafe_allow_html=True)
        st.markdown('<div class="hint">붉은 점선: 기존 공급 감소 · 굵은 Cyan: 대체 공급 → 공정 수요<br>드래그로 회전 · 휠로 확대 · 대륙 윤곽은 간략화한 시연 표시</div>',unsafe_allow_html=True)
        st.plotly_chart(build_globe(network,result),width='stretch',height='stretch',theme=None,
            config={'displayModeBar':False,'scrollZoom':True},key='chain_globe',
            alt='소재부터 벤더와 코어를 거쳐 공정으로 이어지는 3D 공급망과 우회 경로')
    with right,st.container(key='right_panel',height='stretch'):
        with st.container(key='causes_box'):
            st.markdown('<div class="panel-title">원인 · 점수 방어</div>',unsafe_allow_html=True)
            damaged=sorted(result['affected'],key=lambda c:result['tier1'][c]['effective'])
            if not damaged:
                st.markdown('<div class="cause">현재 직접·연쇄 타격이 없습니다.<br>정상 공급으로 모든 공정이 100점입니다.</div>',unsafe_allow_html=True)
            for cid in damaged[:2]:
                r=result['tier1'][cid];core=network['tier1'][cid];vendor=core['alt_vendor']
                st.markdown(f'<div class="cause">{html.escape(network["nodes"][cid]["name"])}<br>기존 {r["primary"]*100:.0f}% + 우회 <b>{r["backup"]*100:.0f}%</b> = <b>{r["effective"]*100:.0f}%</b><br>{html.escape(vendor["region"])} · {html.escape(vendor["name"])}<br>예약 대체 한도 {core["alt_capacity"]*100:.0f}%</div>',unsafe_allow_html=True)
            if len(damaged)>2:st.caption(f'외 {len(damaged)-2}개 코어 영향 · 자세한 이름과 상태는 지구본 호버에서 확인')
        with st.container(key='chat_box',height='stretch'):
            st.markdown('<div class="panel-title">이슈 대화</div>',unsafe_allow_html=True)
            mode=st.selectbox('해석 모드',['테스트','OpenAI'] if api_ready() else ['테스트'],label_visibility='collapsed')
            st.markdown(f'<div class="chat-question">{html.escape(st.session_state.last_query)}</div><div class="chat-answer">{html.escape(st.session_state.reply)}</div>',unsafe_allow_html=True)
            with st.form('issue_form',clear_on_submit=False):
                query=st.text_input('지역·소재·벤더 이슈',value='규슈 소재 100% 중단',max_chars=500)
                submitted=st.form_submit_button('이슈 적용',width='stretch')
            st.markdown('<div class="hint">예: 감광 원료 A 공급 80% 감소<br>예: 규슈 복구 / 정상 복구<br>테스트는 API 호출 없음 · 실제 사건·기업 예측 아님</div>',unsafe_allow_html=True)
            if submitted and query.strip():
                try:
                    targets,loss,action,note=interpret_issue(query,network,mode)
                    if action=='reset':st.session_state.shocks={}
                    elif action=='apply':
                        for target in targets:
                            if loss==0:st.session_state.shocks.pop(target,None)
                            else:st.session_state.shocks[target]=loss
                        outcome=calculate_supply_shock(network,st.session_state.shocks,bypass)
                        note+=f' {len(targets)}개 대상 → 타격 코어 {len(outcome["affected"])}개, 우회 {len(outcome["bypass"])}개. 전체 {outcome["overall"]:.0f}점.'
                    st.session_state.last_query=query;st.session_state.reply=note
                except ValueError as error:st.session_state.reply=str(error)
                st.rerun()


if __name__=='__main__':
    main()
