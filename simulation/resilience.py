"""Daily, acyclic material-flow simulation; no Streamlit or plotting dependencies.

Scores are direct material fulfillment on the last simulated day, not production forecasts.
All stock and reserved alternative capacities are explicit scenario assumptions.
"""
from collections import defaultdict
from copy import deepcopy
import math
import re
from .reporting import ProcessReporter
from .logistics import LogisticsRouter


def number(value, low, high, label):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{label}: {low}~{high} 범위의 숫자가 필요합니다.')
    return float(value)


def generations(nodes, route_dependencies=None):
    """Include alternative pools in the DAG; reject missing IDs and cycles."""
    parents = {k: set(n.get('requires', [])) | set(n.get('route_dependencies', [])) | set(n.get('alt_logistics_via',[])) | ({n['alt_vendor']} if n.get('alt_vendor') else set())
               for k, n in nodes.items()}
    for key, dependencies in (route_dependencies or {}).items():
        parents[key].update(dependencies)
    for k, deps in parents.items():
        if not deps <= nodes.keys():
            raise ValueError(f'누락된 의존성: {k} → {deps - nodes.keys()}')
    done, layers = set(), []
    while len(done) < len(nodes):
        layer = sorted(k for k, deps in parents.items() if k not in done and deps <= done)
        if not layer:
            raise ValueError('공급망 의존성에 순환이 있습니다.')
        layers.append(layer)
        done.update(layer)
    return layers


def calculate_supply_shock(network, events=None, duration_days=30, use_inventory=True,
                           use_bypass=True, scopes=None):
    """Stock covers deficits first; reserved alternative output covers remaining loss.

    AND inputs use min; parallel suppliers use normalized weighted sums. Stocks
    are physical units of nominal daily demand and are consumed once per day.
    An alternative pool has a shared daily budget, allocated proportionally within
    each DAG generation (upstream reservations precede downstream reservations).
    Tariffs create a separate imported-input price index and never reduce supply.
    """
    horizon = int(number(duration_days, 1, 365, '기간'))
    if horizon != duration_days:
        raise ValueError('기간은 정수 일수여야 합니다.')
    nodes = network['nodes']
    scopes = {'core'} | set(scopes or [])
    active = lambda n: n.get('scope', 'core') in scopes
    for key, n in nodes.items():
        number(n['inventory_days'], 0, 365, f'{key} 재고')
        number(n['alt_capacity'], 0, 1, f'{key} 우회 한도')
        number(n.get('capacity_units', 1), 0, 100, f'{key} 예약 생산량')
        number(n.get('alt_qualification_days', 0), 0, 365, f'{key} 대체 인증일')
        number(n.get('alt_ramp_days', 0), 0, 365, f'{key} 우회 확대일')
        if n.get('mode') == 'mix':
            weights = n.get('weights', [])
            if len(weights) != len(n['requires']) or not weights or sum(weights) <= 0:
                raise ValueError(f'병렬 공급 비중 오류: {key}')
            for w in weights:
                number(w, 0, 1e6, '공급 비중')
    events = deepcopy(events or [])
    for e in events:
        if e.get('kind') not in ('supply', 'tariff') or not e.get('targets'):
            raise ValueError('이슈 종류 또는 대상이 비어 있습니다.')
        if any(k not in nodes for k in e['targets']):
            raise ValueError('등록되지 않은 이슈 대상입니다.')
        number(e['rate'], 0, 1 if e['kind'] == 'supply' else 5, '감소율/관세율')
        number(e.get('days', horizon), 1, 365, '이슈 지속일')
    router = LogisticsRouter(network, scopes)
    route_dependencies = {key: {c for via in route['via']
        for c in network.get('port_detours', {}).get(via, {}).get('via', [])}
        for key, route in network.get('logistics_routes', {}).items()}
    layers = generations(nodes, route_dependencies)
    reporter = ProcessReporter(network, scopes)
    stock = {k: float(n['inventory_days']) if use_inventory else 0.0 for k, n in nodes.items()}
    timeline, first_hit, accumulated = [], {}, defaultdict(float)
    qualification_started = {}
    last = {}
    for day in range(1, horizon + 1):
        router.start_day(day)
        loss = defaultdict(float)
        for event in events:
            if event['kind'] == 'supply' and day <= event.get('days', horizon):
                for k in event['targets']:
                    if active(nodes[k]):
                        loss[k] = max(loss[k], event['rate'])
        daily, pool_left = {}, {}
        for layer in layers:
            route_plans = router.plan_layer(layer, daily)
            requests = defaultdict(list)
            for key in layer:
                node = nodes[key]
                deps = [k for k in node.get('requires', []) if active(nodes[k])]
                if node.get('mode') == 'mix' and deps:
                    pairs = [(d, w) for d, w in zip(node['requires'], node['weights']) if d in deps]
                    inbound = sum(daily[d]['effective'] * w for d, w in pairs) / sum(w for _, w in pairs)
                else:
                    inbound = min([daily[d]['effective'] for d in deps] or [1.0])
                if key in route_plans:
                    inbound = route_plans[key]['effective']
                direct = 1.0 - loss[key] if active(node) else 1.0
                primary = min(direct, inbound) if active(node) else 1.0
                # A company's own shutdown cannot be repaired with raw-material stock.
                deficit = max(0.0, (1 - primary) if node.get('buffer_direct', True) else (direct - primary))
                if node.get('kind')=='transport' and all(daily[c]['effective']>=1-1e-10 for c in node['logistics_via']):
                    deficit=0.0  # logistics-only destination buffer; no extra material buffer in normal routing
                inventory = min(stock[key], deficit) if active(node) else 0.0
                stock[key] -= inventory
                pre_backup = min(1.0, primary + inventory)
                daily[key] = dict(primary=primary, inventory=inventory, backup=0.0,
                                  effective=pre_backup, stock_remaining=stock[key], direct=direct)
                alt = node.get('alt_vendor')
                if use_bypass and alt and active(node):
                    # Start qualification at the first upstream/direct supply loss,
                    # including days when inventory still covers the shortfall.
                    if primary < 1 - 1e-10:
                        qualification_started.setdefault(key, day)
                    elapsed = day - qualification_started.get(key, day) + 1
                    ready = elapsed - node.get('alt_qualification_days', 0)
                    ramp = node.get('alt_ramp_days', 0)
                    readiness = 0.0 if ready <= 0 else min(1.0, ready / ramp) if ramp else 1.0
                    alternative_route=min([daily[c]['effective'] for c in node.get('alt_logistics_via',[])] or [1.0])
                    requested = min(1 - pre_backup, node['alt_capacity'] * readiness * alternative_route)
                    if requested > 1e-10:
                        requests[alt].append((key, requested))
            for alt, demands in requests.items():
                if alt not in pool_left:
                    pool_left[alt] = nodes[alt].get('capacity_units', 1) * daily[alt]['effective']
                total = sum(v for _, v in demands)
                factor = min(1.0, pool_left[alt] / total)
                for key, request in demands:
                    allocated = request * factor
                    daily[key]['backup'] = allocated
                    daily[key]['effective'] = min(1.0, daily[key]['effective'] + allocated)
                    pool_left[alt] = max(0.0, pool_left[alt] - allocated)
        scores = {}
        for p, ids in network['process_outputs'].items():
            values = [daily[k]['effective']*100 for k in ids if k not in reporter.unscored_operations]
            scores[p] = min(values) if values else None
        for p, score in scores.items():
            if score is None:
                continue
            accumulated[p] += score
            if score < 100 - 1e-7:
                first_hit.setdefault(p, day)
        reporter.observe(day, daily, scores)
        router.end_day()
        timeline.append(dict(day=day, **scores))
        last = daily
    tariffs = []
    for e in events:
        if e['kind'] == 'tariff':
            tariffs.append(dict(label=e.get('text', ''), targets=e['targets'],
                # Conditional index: 100% of the identified input import subject to duty,
                # full pass-through. Not a fab's unit manufacturing cost estimate.
                index=100 * (1 + e['rate']), assumption='대상 수입재 전액 과세·전액 전가 가정'))
    buffered = {k for k, r in last.items() if r['inventory'] > 1e-7}
    protected_processes = []
    for process, outputs in network['process_outputs'].items():
        todo, seen = list(outputs), set()
        while todo:
            key = todo.pop()
            if key in seen:continue
            seen.add(key)
            todo.extend(k for k in nodes[key]['requires'] if active(nodes[k]))
        if scores[process] is not None and scores[process]>=100-1e-7 and seen & buffered:
            protected_processes.append(process)
    return dict(nodes=last, scores=scores, overall=min((v for v in scores.values() if v is not None), default=None), timeline=timeline,
        average_scores={p: accumulated[p] / horizon if scores[p] is not None else None for p in scores}, first_hit=first_hit,
        affected=[k for k, r in last.items() if r['effective'] < 1 - 1e-7],
        bypass=[k for k, r in last.items() if r['backup'] > 1e-7],
        buffered=sorted(buffered), protected_processes=protected_processes,
        tariffs=tariffs, duration_days=horizon, scopes=sorted(scopes),
        scoring_policy=network.get('scoring_policy'),
        context_impacts=context_impacts(network, events),
        material_shortages=material_shortages(network, last, scopes),
        unscored_processes=[p for p,v in scores.items() if v is None],
        coverage_gaps=deepcopy(network.get('coverage_gaps', [])),
        incomplete_processes=deepcopy(network.get('incomplete_processes', {})),
        logistics=router.finish(), **reporter.finish())


COUNTRIES = {
    '중국': ['중국', 'china', '중국산'], '일본': ['일본', 'japan', '일본산'],
    '미국': ['미국', 'usa', '미국산'], '한국': ['한국', 'korea', '한국산'],
    '대만': ['대만', 'taiwan', '대만산'], '독일': ['독일', 'germany'],
    '프랑스': ['프랑스', 'france'], '우크라이나': ['우크라이나', 'ukraine'],
    '러시아': ['러시아', 'russia'], '칠레': ['칠레', 'chile'],
    '인도네시아': ['인도네시아', 'indonesia'], '싱가포르': ['싱가포르', 'singapore'],
    '캐나다': ['캐나다', 'canada'], '네덜란드': ['네덜란드', 'netherlands'],
    '멕시코': ['멕시코', 'mexico'], '호주': ['호주', 'australia'],
}


def material_shortages(network, daily, scopes):
    rows = []
    for (company, process), operation in network.get('operations', {}).items():
        for key in network['nodes'][operation]['requires']:
            node = network['nodes'][key]
            if node.get('scope','core') in scopes and daily[key]['effective'] < 1-1e-7:
                rows.append(dict(process=process, company=company, node_id=key,
                    name=node['name'].replace(' 투입 충족','').replace(' · 병렬 공급',''),
                    fulfillment=daily[key]['effective']*100))
    return rows


def context_impacts(network, events):
    """Keep non-material events available for explanation, without inventing losses."""
    rows = []
    equipment_owners = {n.get('company_id') for n in network['nodes'].values() if n.get('input_category')=='equipment'}
    producers = {company for company,_ in network.get('operations',{})}
    for event in events:
        categories = set()
        if event['kind']=='tariff':
            categories.add('cost')
        else:
            for key in event['targets']:
                if network['nodes'][key].get('input_category')=='equipment' or key in equipment_owners:
                    categories.add('equipment')
                if key in producers:
                    categories.add('facility')
        for category in sorted(categories):
            rows.append(dict(category=category, text=event.get('text',''), days=event.get('days'), rate=event['rate']))
    return rows


def interpret_issue(text, network, default_days=30, default_loss=1.0):
    """Offline entity matching; no invented factories, percentages or vendor IDs."""
    q = text.strip().lower()
    generic_strait=bool(re.match(r'^해협(?:\s|봉쇄|폐쇄|통항)',q)) and not any(w in q for w in ('말라카','수에즈','가오슝'))
    if generic_strait:q=q.replace('해협','말라카 해협')
    if not q or len(q) > 600:
        raise ValueError('1~600자의 이슈를 입력하세요.')
    if q in ('초기화', '정상 복구', '정상복구', '전체 복구', '전체 정상 복구', 'reset'):
        return dict(action='reset', note='모든 이슈를 해제했습니다.')
    if any(w in q for w in ('nokia', '노키아')):
        raise ValueError('Nokia의 지역별 공장·공급 경로는 등록되지 않았습니다. 등록된 기업·소재를 지정해 주세요.')
    if not any(w in q for w in ('중단','차질','감소','통제','규제','제한','부족','금지','손실','관세','tariff','복구','해제','정상화','가동률','공급률','화재','지진','홍수','파업','폐쇄','봉쇄')):
        raise ValueError('공급 중단·감소·관세·복구 중 적용할 이슈를 함께 입력하세요.')
    if re.search(r'-\s*\d+(?:\.\d+)?\s*%', q):
        raise ValueError('감소율·관세율은 음수가 될 수 없습니다.')
    days = re.findall(r'(\d+)\s*일', q)
    if len(set(days)) > 1:
        raise ValueError('한 이슈의 지속일을 하나만 입력하세요.')
    duration = int(days[0]) if days else default_days
    number(duration, 1, 365, '기간')
    matches = []
    for entity in network['entities'].values():
        for alias in [entity['name'], *entity.get('aliases', [])]:
            for m in re.finditer(re.escape(alias.lower()), q):
                # Latin abbreviations such as W, Cu and Au must be standalone.
                if alias.isascii() and ((m.start() and q[m.start()-1].isalnum()) or
                                         (m.end() < len(q) and q[m.end()].isalnum())):
                    continue
                matches.append((m.start(), m.end(), entity['id']))
    accepted = []
    for hit in sorted(matches, key=lambda x: (-(x[1]-x[0]), x[0])):
        if any(hit[:2] == prior[:2] for prior in accepted) or not any(hit[0] < b and a < hit[1] for a, b, _ in accepted):
            accepted.append(hit)
    targets = sorted({k for _, _, k in accepted})
    companies = {k for k in targets if network['entities'][k]['kind']=='company'}
    materials = [k for k in targets if network['entities'][k]['kind'] in ('resource','product','material')]
    if companies and materials:
        narrowed = [k for k in materials if network['nodes'][k].get('company_id') in companies or
                    any(k in n['requires'] and n.get('company_id') in companies for n in network['nodes'].values())]
        if not narrowed:
            raise ValueError('지정한 기업과 소재의 연결이 등록되지 않았습니다.')
        targets = narrowed
    countries = [c for c, aliases in COUNTRIES.items() if any(a in q for a in aliases)]
    if not targets:
        if countries and not any(w in q for w in ('전체','국가')):
            raise ValueError('소재·기업을 함께 지정하세요. 국가 전체 가정은 “일본 전체 공급 중단”처럼 입력하세요.')
        for c in countries:
            targets.extend(k for k, e in network['entities'].items() if e['country'] == c
                           and e['kind'] not in ('process', 'reserve'))
        targets = sorted(set(targets))
    elif countries:
        narrowed = [k for k in targets if network['entities'][k]['country'] in countries]
        if not narrowed:
            raise ValueError('지정한 국가에 해당 소재/기업 거점이 등록되지 않았습니다. 다른 국가로 임의 연결하지 않습니다.')
        targets = narrowed
    if not targets:
        raise ValueError('등록된 대상과 연결되지 않았습니다. 예: 중국 희토류, 일본 포토레지스트, 미국 석영, 우크라이나 네온.')
    if any(w in q for w in ('지진', '홍수', '공장', '화재')) and not accepted:
        raise ValueError('지역 전체를 실제 공장 피해로 간주할 수 없습니다. 소재 또는 등록 기업을 함께 지정하세요.')
    percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', q)
    if len(percentages) > 1:
        raise ValueError('한 번에 한 감소율 또는 관세율을 입력하세요.')
    tariff = '관세' in q or 'tariff' in q
    if tariff and not percentages:
        raise ValueError('관세율을 입력하세요. 예: 중국 갈륨 관세 20%. 공급 점수와 별도로 계산합니다.')
    rate = float(percentages[0]) / 100 if percentages else default_loss
    if '가동률' in q or '공급률' in q:
        if tariff:
            raise ValueError('관세율과 가동률을 한 이슈에 함께 입력하지 마세요.')
        rate = 1 - rate
    if not tariff and any(w in q for w in ('증가', '상승', '인상')):
        raise ValueError('가격 증가를 공급 중단으로 변환하지 않습니다. 관세율 또는 공급 감소율을 지정하세요.')
    number(rate, 0, 5 if tariff else 1, '관세율/감소율')
    restore = any(w in q for w in ('복구', '해제', '정상화'))
    note = f"{len(targets)}개 대상 · {'관세' if tariff else '공급 감소'} {rate*100:g}% · {duration}일."
    if any(network['nodes'][k]['kind']=='logistics' for k in targets):
        note+=' 물류 경유 가정에 연결된 해상 공급만 타격합니다. 기업 전체 생산 중단을 뜻하지 않습니다.'
        if generic_strait:note+=' 해협 이름이 없어 등록된 말라카 해협을 적용했습니다.'
    if not percentages and not restore:
        note += f' 감소율 미기재로 설정값 {default_loss*100:g}%를 가정했습니다.'
    if '희토류' in q:
        note += ' 현재 희토류 경로는 세륨계 CMP만 포함합니다.'
    if any(w in q for w in ('지진','공장','화재','홍수')):
        note += ' 시설별 피해 비중은 미확인이며 지정한 기업·소재 수준의 타격 가정입니다.'
    if tariff:
        note += ' 대상 수입재 가격지수이며 실제 제품 원가가 아닙니다.'
    return dict(action='restore' if restore else 'apply', kind='tariff' if tariff else 'supply',
        targets=targets, rate=rate, days=duration, text=text.strip(), note=note)


def apply_issue(events, parsed):
    if parsed['action'] == 'reset':
        return []
    out = deepcopy(events)
    targets = set(parsed['targets'])
    # Applying a new rate to the same target replaces that target's old event.
    for e in out:
        if parsed['action'] == 'restore' or e['kind'] == parsed['kind']:
            e['targets'] = [k for k in e['targets'] if k not in targets]
    out = [e for e in out if e['targets']]
    if parsed['action'] == 'apply':
        out.append({k: parsed[k] for k in ('kind', 'targets', 'rate', 'days', 'text')})
    return out
