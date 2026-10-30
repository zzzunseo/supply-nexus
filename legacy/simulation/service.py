"""File loading and presentation payloads; engine formulas remain separate."""
import json
from math import isfinite
from pathlib import Path
from .engine import calculate, validate_model
from .overview import aggregate_countries
from .advice import build_advice

DEFAULT_OPTIONS = {'duration_days': 14, 'severity': 1.0, 'inventory': True, 'substitutes': False}
DURATIONS = (7, 14, 30, 60)
SEVERITIES = (0.0, 0.25, 0.5, 1.0)


def normalize_options(selection=None):
    selection = selection or {}
    days = selection.get('duration_days', 14)
    severity = selection.get('severity', 1.0)
    return {'duration_days': days if type(days) is int and 1 <= days <= 365 else 14,
            'severity': severity if type(severity) in (int, float) and isfinite(severity) and 0 <= severity <= 1 else 1.0,
            'inventory': selection.get('inventory', True) is True,
            'substitutes': selection.get('substitutes', False) is True}


def load_model(path: Path, data: dict):
    model = json.loads(path.read_text(encoding='utf-8'))
    validate_model(data, model)
    if data.get('schema_version') == 'linked-demo-1':
        edges = {e['id']: e for e in data['edges']}
        for process in model['processes']:
            for item in process['required_inputs']:
                for supplier in item['suppliers']:
                    edge = edges[supplier['edge_id']]
                    if item['item_id'] != edge['item_id'] or abs(supplier['share_pct'] - edge['model_share_pct']) > 1e-6:
                        raise ValueError('기업 경로와 계산용 소재·가정 배분율이 일치하지 않습니다.')
    return model


def expand_country_scenario(data, scenario):
    """Resolve legacy hub events to company IDs; no dependency propagation."""
    lookup = {n['id']: n for n in data['nodes']}
    affected = set(scenario.get('affected', []))
    countries = {lookup[n]['country'] for n in affected
                 if n in lookup and lookup[n].get('type', 'country_hub') == 'country_hub'}
    affected.update(n['id'] for n in data['nodes']
                    if n.get('type', 'country_hub') != 'country_hub' and n['country'] in countries)
    return {**scenario, 'affected': sorted(affected)}


def attach_share_evidence(data, report):
    """Tag calculation weights in exports without altering engine arithmetic."""
    edges = {e['id']: e for e in data['edges']}
    for process in report['processes']:
        for item in process['inputs']:
            for supplier in item['suppliers']:
                edge = edges[supplier['edge_id']]
                supplier.update(source=edge.get('model_source', item['source']),
                    source_year=edge.get('model_source_year', item['source_year']),
                    status='가정값', share_basis='model_share_pct',
                    actual_share_pct=edge.get('share_pct'))
    return report


def build_simulation_payload(data, model, options=None):
    options = normalize_options(options)
    baseline_scenario = {'name': '정상 상태', 'affected': []}
    baseline = attach_share_evidence(data, calculate(data, model, baseline_scenario, **options))
    reports = {}
    for scenario in data['scenarios']:
        resolved_scenario = expand_country_scenario(data, scenario)
        report = attach_share_evidence(data, calculate(data, model, resolved_scenario, **options))
        report['delta'] = round(report['overall_score']-baseline['overall_score'], 4)
        report['affected_companies'] = [n['id'] for n in data['nodes']
            if n.get('type', 'country_hub') != 'country_hub' and n['id'] in report['affected_nodes']]
        report['overview'] = aggregate_countries(data, report)
        report['advice'] = build_advice(data, model, resolved_scenario, options, report)
        if scenario.get('custom_issue'):
            report['node_display_availability'] = {n['id']: min(
                (report['edge_availability'][e['id']] for e in data['edges'] if n['id'] in (e['from'], e['to'])), default=1)
                for n in data['nodes']}
            report['affected_companies'] = [n['id'] for n in data['nodes'] if n.get('company_name')
                and report['node_display_availability'][n['id']] < 1-1e-9]
        reports[scenario['name']] = report
    return {'options': options, 'baseline': baseline, 'reports': reports,
            'notice': model['notice'], 'model_version': 'bottleneck-linked-demo-1'}
