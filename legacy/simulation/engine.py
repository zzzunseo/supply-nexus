"""AND input model. All availability arithmetic is performed in Python.

Inputs are fractions of nominal demand. Inventory and substitution are additive
but capped at the remaining shortfall, so no input can exceed 100% availability.
The report distinguishes intrinsic input capacity from a serial-chain ceiling.
"""
from math import isclose, isfinite

EPS = 1e-9


def number(value, name, minimum=0, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f'{name}: 유한한 숫자가 필요합니다.')
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f'{name}: 허용 범위를 벗어났습니다.')
    return float(value)


def validate_model(data, model):
    edges = {e['id']: e for e in data['edges']}
    definitions = model.get('processes', [])
    if [p['name'] for p in definitions] != data['processes']:
        raise ValueError('계산 공정과 지도 공정의 순서가 일치해야 합니다.')
    for process in definitions:
        inputs = process.get('required_inputs', [])
        if not inputs or not any(i.get('critical', True) for i in inputs):
            raise ValueError(f"{process['name']}: 필수 투입재가 없습니다.")
        ids = [i['item_id'] for i in inputs]
        if len(ids) != len(set(ids)):
            raise ValueError('공정 내 투입재 ID가 중복됩니다.')
        for item in inputs:
            suppliers = item.get('suppliers', [])
            if not suppliers:
                raise ValueError('공급 경로가 없습니다.')
            route_ids = [s['edge_id'] for s in suppliers]
            if len(route_ids) != len(set(route_ids)):
                raise ValueError('동일 공급 경로를 중복 계산할 수 없습니다.')
            for supplier in suppliers:
                edge = edges.get(supplier['edge_id'])
                if not edge or process['name'] not in edge['processes'] or item['name'] != edge['item']:
                    raise ValueError('공급 경로와 공정·품목이 일치하지 않습니다.')
                number(supplier['share_pct'], '공급 배분율', 0, 100)
            if not isclose(sum(s['share_pct'] for s in suppliers), 100, abs_tol=1e-6):
                raise ValueError('투입재별 공급 배분율의 합은 100이어야 합니다.')
            number(item['buffer_days'], '재고일수')
            number(item['substitute_fraction'], '대체 여력', 0, 1)
            number(item['substitute_lead_days'], '대체 공급 리드타임')
            if not item.get('source') or 'source_year' not in item:
                raise ValueError('가정값의 출처 및 기준연도 표시가 필요합니다.')


def status(rate):
    return 'stopped' if rate <= EPS else 'normal' if rate >= 1-EPS else 'warning'


def calculate_input(item, edge_availability, duration_days, *, inventory=True, substitutes=False):
    """Compute one item's horizon-average demand coverage and its audit trail."""
    duration = number(duration_days, '지속 기간', 1)
    contributions = []
    for supplier in item['suppliers']:
        share = number(supplier['share_pct'], '공급 배분율', 0, 100) / 100
        available = number(edge_availability[supplier['edge_id']], '경로 가용률', 0, 1)
        contributions.append({'edge_id': supplier['edge_id'], 'share_pct': share*100,
                              'operating_rate': available, 'contribution': share*available})
    supply = min(1.0, sum(s['contribution'] for s in contributions))
    # This is a separate, explicitly assumed emergency capacity. Existing shares
    # are not counted a second time. A lead time beyond the horizon gives zero.
    active_fraction = max(0.0, (duration-item['substitute_lead_days'])/duration)
    substitute = min(1-supply, item['substitute_fraction']*active_fraction) if substitutes else 0.0
    stock = min(max(0.0, 1-supply-substitute), item['buffer_days']/duration) if inventory else 0.0
    availability = min(1.0, max(0.0, supply+substitute+stock))
    return {'item_id': item['item_id'], 'name': item['name'],
            'critical': item.get('critical', True), 'suppliers': contributions,
            'supply': supply, 'substitute': substitute, 'inventory': stock,
            'availability': availability, 'score': round(100*availability, 4),
            'buffer_days': item['buffer_days'], 'substitute_fraction': item['substitute_fraction'],
            'substitute_lead_days': item['substitute_lead_days'],
            'status': status(availability), 'source': item['source'], 'source_year': item['source_year']}


def calculate(data, model, scenario, *, duration_days=14, severity=1.0, inventory=True, substitutes=False):
    """Return an immutable report for a node-disruption demonstration scenario.

    A scenario targets map nodes; every incident route's delivery capacity falls
    by severity. Multiple affected endpoints do not double-count the same event.
    This is an aggregate delivery model, not a facility scheduling simulator.
    """
    validate_model(data, model)
    number(duration_days, '지속 기간', 1)
    severity = number(severity, '중단 강도', 0, 1)
    affected = set(scenario.get('affected', []))
    ids = [n['id'] for n in data['nodes']]
    if not affected <= set(ids):
        raise ValueError('시나리오에 존재하지 않는 거점이 있습니다.')
    node_rates = {node_id: 1-severity if node_id in affected else 1.0 for node_id in ids}
    edge_rates = {e['id']: min(node_rates[e['from']], node_rates[e['to']]) for e in data['edges']}
    # Explicit scoped supply shocks; the existing bottleneck formula is unchanged.
    # A facility factor is its sourced fraction of a corporate supply edge.
    edge_factors = scenario.get('edge_impact_factors', {})
    if not isinstance(edge_factors, dict) or not set(edge_factors) <= set(edge_rates):
        raise ValueError('이슈에 존재하지 않는 공급 경로가 있습니다.')
    for edge_id, factor in edge_factors.items():
        factor = number(factor, '시설/소재 경로 영향 비중', 0, 1)
        edge_rates[edge_id] = min(edge_rates[edge_id], 1-severity*factor)
    processes = []
    serial_rate = 1.0
    intrinsic_rates = []
    for process in model['processes']:
        items = [calculate_input(item, edge_rates, duration_days, inventory=inventory, substitutes=substitutes)
                 for item in process['required_inputs']]
        required = [i for i in items if i['critical']]
        rate = min(i['availability'] for i in required)
        intrinsic_rates.append(rate)
        serial_rate = min(serial_rate, rate)
        limiting = [i['name'] for i in required if isclose(i['availability'], rate, abs_tol=EPS)] if rate < 1-EPS else []
        processes.append({'name': process['name'], 'score': round(100*rate, 4),
                          'serial_score': round(100*serial_rate, 4),
                          'status': status(rate), 'serial_status': status(serial_rate),
                          'limiting_items': limiting, 'inputs': items})
    overall = min(intrinsic_rates)
    bottlenecks = [p['name'] for p, rate in zip(processes, intrinsic_rates)
                   if isclose(rate, overall, abs_tol=EPS)] if overall < 1-EPS else []
    return {'scenario': scenario['name'], 'overall_score': round(overall*100, 4),
            'status': status(overall), 'bottlenecks': bottlenecks, 'processes': processes,
            'affected_nodes': sorted(n for n, rate in node_rates.items() if rate < 1-EPS),
            'node_availability': node_rates, 'edge_availability': edge_rates,
            'edge_status': {key: status(value) for key, value in edge_rates.items()},
            'options': {'duration_days': int(duration_days), 'severity': severity,
                        'inventory': inventory, 'substitutes': substitutes},
            'is_demo': True}
