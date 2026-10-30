"""Read-only presentation of observed daily values and actual detour arrivals."""
import html


def timeline_data(network,case,baseline,response,inventory_only=None):
    company=case['recipients'][0]
    process=case['process']
    before=baseline['process_views'][company]
    after=response['process_views'][company]
    days=response['duration_days']
    first=after['first_hit'].get(process)
    events=[dict(label='조건 적용',day=1,kind='start')]
    arrival=None
    if case.get('kind')=='logistics':
        from .logistics_demo import representative_route
        key,_=representative_route(network,case)
        arrival=next((row['day'] for row in response['logistics']['timeline']
                      if row['routes'].get(key,{}).get('delivered',0)>1e-7),None)
        if arrival is not None:events.append(dict(label='우회 첫 도착',day=arrival,kind='arrival'))
    if first is not None:events.append(dict(label='첫 소재 부족',day=first,kind='shortage'))
    events.append(dict(label='관측 종료',day=days,kind='end'))
    events.sort(key=lambda e:e['day'])
    score=after['scores'].get(process)
    summary=[]
    if case.get('kind')=='logistics':
        if arrival is not None: summary.append(f'우회 물량은 {arrival}일째부터 도착했습니다.')
        else: summary.append('관측 기간 내 우회 도착이 없습니다.')
    stock_first=None
    if inventory_only is not None:
        stock_first=inventory_only['process_views'][company]['first_hit'].get(process)
        summary.append(f'재고만 적용하면 {stock_first}일째 첫 부족입니다.' if stock_first is not None else '재고만 적용해도 관측 기간 동안 소재 부족이 없습니다.')
    if score is None:
        summary.append('해당 기업·공정은 미산정으로 부족 여부를 판단할 수 없습니다.')
    elif first is None:
        summary.append('현재 대응에서는 관측 기간 내 소재 부족이 없습니다.')
    elif score is not None and score<100-1e-7:
        summary.append(f'현재 대응은 {first}일째부터 부족이 발생하며, 말일 충족도는 {score:.1f}%입니다.')
    else:
        summary.append(f'{first}일째 부족이 발생했지만 말일에는 등록 수요를 충족합니다.')
    return dict(company=company,name=network['nodes'][company]['name'],process=process,days=days,
                before=[dict(day=r['day'],value=r.get(process)) for r in before['timeline']],
                after=[dict(day=r['day'],value=r.get(process)) for r in after['timeline']],
                first_arrival=arrival,first_shortage=first,inventory_only_first=stock_first,
                events=events,summary=' '.join(summary))


def timeline_html(data):
    days=data['days']
    x=lambda day:48+min(1,max(0,(day-1)/max(1,days-1)))*620
    y=lambda value:43-(value/100)*24
    paths=[]
    for key,color in [('before','#ffbe60'),('after','#4fe4db')]:
        # Step segments show daily observed values without interpolating recovery.
        parts=[]; previous=None
        for row in data[key]:
            if row['value'] is None:previous=None;continue
            point=(x(row['day']),y(row['value']))
            parts.append((f'M{point[0]:.1f},{point[1]:.1f}' if previous is None else f'H{point[0]:.1f}V{point[1]:.1f}'))
            previous=point
        paths.append(f'<path d="{" ".join(parts)}" fill="none" stroke="{color}" stroke-width="2"/>')
        if len(data[key])==1 and data[key][0]['value'] is not None:
            paths.append(f'<circle cx="48" cy="{y(data[key][0]["value"]):.1f}" r="2.5" fill="{color}"/>')
    marks=[]
    for event in data['events']:
        if event['kind'] not in ('arrival','shortage'):continue
        color='#68adff' if event['kind']=='arrival' else '#ff9388'
        title=html.escape(f"{event['label']}: {event['day']}일째")
        marks.append(f'<line x1="{x(event["day"]):.1f}" x2="{x(event["day"]):.1f}" y1="16" y2="46" stroke="{color}" stroke-dasharray="2 3"><title>{title}</title></line>')
    tags=''.join(f'<span class="demo-time-{e["kind"]}">{html.escape(e["label"])} <b>{e["day"]}일</b></span>' for e in data['events'])
    title=html.escape(data['name']+' · '+data['process']+' · 일별 소재 충족도')
    return f'''<div class="demo-mini-timeline"><svg viewBox="0 0 700 58" role="img" aria-label="{title}">
    <text x="4" y="10" fill="#a8bfd3" font-size="10">{title}</text>
    <text x="470" y="10" fill="#ffbe60" font-size="10">━ 미적용</text><text x="560" y="10" fill="#4fe4db" font-size="10">━ 현재 대응</text>
    <text x="2" y="22" fill="#8ba4ba" font-size="9">100%</text><text x="20" y="46" fill="#8ba4ba" font-size="9">0</text>
    <path d="M48 19H668M48 43H668" stroke="#294052" stroke-width=".7"/>
    {''.join(marks)}{''.join(paths)}
    <text x="48" y="56" fill="#8ba4ba" font-size="9">1일</text><text x="668" y="56" text-anchor="end" fill="#8ba4ba" font-size="9">{days}일</text></svg>
    <div class="demo-time-events">{tags}</div></div>'''
