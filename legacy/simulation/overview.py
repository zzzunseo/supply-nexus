"""Country summaries only; never changes bottleneck engine results."""
from collections import defaultdict
from .engine import status


def aggregate_countries(data, report, threshold_pct=50):
    nodes = {n['id']: n for n in data['nodes']}
    edges = {e['id']: e for e in data['edges']}
    hubs = {}
    for n in data['nodes']:
        if n.get('type', 'country_hub') == 'country_hub':
            hubs.setdefault(n['country'], n)
    involvement = defaultdict(set)
    rates = defaultdict(list)
    pairs = {}
    for e in data['edges']:
        a, b = nodes[e['from']]['country'], nodes[e['to']]['country']
        rate = report['edge_availability'][e['id']]
        for country in {a, b}:
            involvement[country].update(e['processes'])
            rates[country].append(rate)
        if a == b:
            continue  # Domestic relations are represented by the country point.
        key = tuple(sorted((a, b)))
        pair = pairs.setdefault(key, {'from': hubs[key[0]]['id'], 'to': hubs[key[1]]['id'],
            'id': 'overview:' + '|'.join(key), 'flow_weight': 0, 'member_ids': [],
            'processes': set(), 'rates': [], 'directions': set()})
        pair['flow_weight'] += e.get('model_share_pct', 0)
        pair['member_ids'].append(e['id'])
        pair['processes'].update(e['processes'])
        pair['rates'].append(rate)
        pair['directions'].add(a + ' → ' + b)
    rows = []
    for country, hub in hubs.items():
        cells = []
        for process in report['processes']:
            details = []
            for item in process['inputs']:
                if not item['critical']:
                    continue
                suppliers = [s for s in item['suppliers'] if nodes[edges[s['edge_id']]['from']]['country'] == country]
                if not suppliers:
                    continue
                share = sum(s['share_pct'] for s in suppliers)
                available = sum(s['share_pct'] * s['operating_rate'] for s in suppliers)
                details.append({'item': item['name'], 'share_pct': round(share, 4),
                    'available_share_pct': round(available, 4), 'loss_pct': round(share - available, 4),
                    'edge_ids': [s['edge_id'] for s in suppliers]})
            value = max((d['share_pct'] for d in details), default=None)
            loss = max((d['loss_pct'] for d in details), default=0)
            cell_status = status(min((d['available_share_pct'] / d['share_pct'] for d in details if d['share_pct'] > 1e-9), default=1))
            cells.append({'process': process['name'], 'value_pct': value, 'loss_pct': loss,
                'status': cell_status, 'details': details, 'has_data': bool(details)})
        rate = min(rates[country], default=1)
        rows.append({'country': country, 'id': hub['id'], 'lat': hub['lat'], 'lon': hub['lon'],
            'process_count': len(involvement[country]), 'processes': sorted(involvement[country]),
            'status': status(rate), 'availability': rate, 'cells': cells})
    ranked = []
    for row in rows:
        cells = [c for c in row['cells'] if c['value_pct'] is not None and c['value_pct'] >= threshold_pct]
        if cells:
            ranked.append({'country': row['country'], 'processes': [c['process'] for c in cells],
                'count': len(cells), 'max_pct': max(c['value_pct'] for c in cells)})
    ranked.sort(key=lambda r: (-r['count'], -r['max_pct'], r['country']))
    flows = []
    for p in pairs.values():
        rate = min(p.pop('rates'))
        flows.append({**p, 'processes': sorted(p['processes']), 'directions': sorted(p['directions']),
            'availability': rate, 'status': status(rate), 'flow_weight': round(p['flow_weight'], 4)})
    return {'countries': rows, 'flows': flows, 'top_dependencies': ranked[:3],
        'threshold_pct': threshold_pct, 'affected_process_count': sum(p['score'] < 100-1e-7 for p in report['processes']),
        'overall_score': report['overall_score'], 'bottlenecks': report['bottlenecks'],
        'share_basis': 'model_share_pct · 가정값',
        'flow_basis': '국가 쌍의 모델 배분율 합계 · 물동량/시장 점유율 아님'}
