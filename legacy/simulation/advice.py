"""Explain deterministic results and compare explicit mitigation assumptions."""
from copy import deepcopy
from .engine import calculate


def explain_report(data, report):
    nodes = {n['id']: n for n in data['nodes']}
    edges = {e['id']: e for e in data['edges']}
    causes = []
    for process in report['processes']:
        for item in process['inputs']:
            if not item['critical'] or item['supply'] >= 1 - 1e-9:
                continue
            damaged = []
            for supplier in item['suppliers']:
                if supplier['operating_rate'] >= 1 - 1e-9:
                    continue
                edge = edges[supplier['edge_id']]
                a, b = nodes[edge['from']], nodes[edge['to']]
                damaged.append({'edge_id': edge['id'],
                    'from': a.get('company_name', a.get('name', a['id'])),
                    'to': b.get('company_name', b.get('name', b['id'])),
                    'country': a['country'], 'availability': supplier['operating_rate'],
                    'loss_pct': round(supplier['share_pct'] * (1-supplier['operating_rate']), 4)})
            alternatives = []
            for supplier in item['suppliers']:
                if supplier['operating_rate'] < 1 - 1e-9:
                    continue
                edge = edges[supplier['edge_id']]
                node = nodes[edge['from']]
                if not any(a['id'] == node['id'] for a in alternatives):
                    alternatives.append({'id': node['id'], 'name': node.get('company_name', node.get('name', node['id'])),
                        'country': node['country'], 'source': edge.get('source'),
                        'evidence_scope': edge.get('evidence_scope', '확인 필요'),
                        'notice': '기존 모델의 정상 경로 후보. 추가 여력·등급·납기·고객 승인 확인 필요.'})
            causes.append({'process': process['name'], 'item': item['name'], 'item_id': item['item_id'],
                'supply_pct': round(item['supply']*100, 4), 'stock_pct': round(item['inventory']*100, 4),
                'substitute_pct': round(item['substitute']*100, 4), 'available_pct': item['score'],
                'process_score': process['score'], 'limiting': item['name'] in process['limiting_items'],
                'damaged': damaged, 'alternatives': alternatives})
    causes.sort(key=lambda c: (c['process_score'], not c['limiting'], c['available_pct']))
    return causes


def build_advice(data, model, scenario, options, report):
    causes = explain_report(data, report)
    variants = []
    for key, label, stock, substitute in [
            ('current', '현재 조건', False, False), ('stock', '소모성 재고 +7일', True, False),
            ('substitute', '대체 공급 가정 적용', False, True), ('combined', '재고 + 대체', True, True)]:
        variant_model = deepcopy(model)
        variant_options = dict(options)
        if stock:
            variant_options['inventory'] = True
            for process in variant_model['processes']:
                for item in process['required_inputs']:
                    # A zero-buffer equipment input must not become stockable.
                    if item['buffer_days'] > 0:
                        item['buffer_days'] += 7
        if substitute:
            variant_options['substitutes'] = True
        candidate = report if key == 'current' else calculate(data, variant_model, scenario, **variant_options)
        variants.append({'id': key, 'label': label, 'score': candidate['overall_score'],
            'gain': round(candidate['overall_score'] - report['overall_score'], 4),
            'bottlenecks': candidate['bottlenecks'],
            'processes': [{'name': p['name'], 'score': p['score']} for p in candidate['processes']]})
    best = max(variants, key=lambda v: v['score'])
    summary = (f"비교한 가정 중 '{best['label']}'에서 전체 점수가 {best['gain']:g}점 높아집니다."
               if best['gain'] > 0 else '비교한 재고·대체 가정으로는 전체 점수가 개선되지 않습니다. 제한 투입재를 확인하세요.')
    if not causes:
        summary = '현재 필수 투입재의 직접 공급 감소가 없습니다.'
    return {'causes': causes, 'mitigations': variants, 'summary': summary,
        'notice': '가정 비교이며 실제 조달·가동 권고가 아닙니다. 장비에는 재고를 추가하지 않고, 대체 여력·전환 기간은 기존 모델 값을 사용합니다.'}
