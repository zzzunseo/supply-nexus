"""Read-only supply-flow data, independent of Streamlit and rendering.

The four columns contain suppliers, materials, company-specific operations and
recipients. Process-tagged deliveries determine the scope. Material dependencies
are expanded upstream, but preceding operations are not unfolded into this view.
Rates are presentation conversions of existing engine results, not a simulation.
"""
import math

from simulation.evidence import relationship_decision
from evidence_review import material_basis


MATERIAL_KINDS = {'product', 'material', 'resource'}
COLUMNS = (
    ('suppliers', '공급 기업'),
    ('materials', '소재'),
    ('processes', '공정'),
    ('recipients', '영향 기업'),
)


def _state(result, node_id, excluded=False):
    if excluded:
        return {'status': 'excluded', 'reduction_pct': None}
    if node_id in result.get('unscored_operations', []):
        return {'status':'unknown', 'reduction_pct':None}
    value = result.get('nodes', {}).get(node_id, {}).get('effective')
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return {'status': 'unknown', 'reduction_pct': None}
    if not 0 <= value <= 1:
        return {'status': 'unknown', 'reduction_pct': None}
    if value <= 1e-7:
        status = 'stopped'
    elif value < 1 - 1e-7:
        status = 'reduced'
    else:
        status = 'normal'
    return {'status': status, 'reduction_pct': round((1 - value) * 100, 6)}


def _material_evidence(result, node_id, excluded):
    """Copy reported model metrics without forecasting stock depletion."""
    data = result.get('nodes', {}).get(node_id, {})
    def value(key, upper=None):
        number = data.get(key)
        if excluded or type(number) not in (int, float) or not math.isfinite(number):
            return None
        if number < 0 or (upper is not None and number > upper):
            return None
        return number
    backup = value('backup', 1)
    return {
        'stock_remaining_days': value('stock_remaining'),
        'backup_active_pct': None if backup is None else round(backup * 100, 6),
        'metric_node_id': node_id,
    }


def _exclusion(network, edge):
    decision = network.get('relationship_decisions', {}).get(edge.get('backbone_id'))
    if decision is not None and not decision['included']:
        return True, decision['reason']
    if edge.get('calculation_included') is False:
        return True, edge.get('exclusion_reason', '계산 제외 관계')
    if edge.get('kind') == 'backbone' and 'calculation_included' not in edge:
        included, reason = relationship_decision(edge.get('evidence', {}))
        if not included:
            return True, reason
    return False, None


def _assumed_share(network, edge, operation):
    evidence = edge.get('evidence', {})
    if evidence.get('model_share_pct') is not None:
        # model_share_pct is explicitly the model's assumption, not share_pct.
        return True
    nodes = network['nodes']
    candidates = {edge['from'], edge.get('calc_target'), edge.get('transport_node')}
    for key in [edge.get('calc_target'), *nodes[operation].get('requires', [])]:
        node = nodes.get(key, {})
        if node.get('mode') != 'mix' or not node.get('weights'):
            continue
        if key == edge.get('calc_target') or candidates.intersection(node['requires']):
            if node.get('parameter_status') != '출처 있음':
                return True
    return False


def build_flow(network, result, process='포토', selected=None):
    """Build a detached, deterministic flow for one registered process.

    Each column has ``id``, ``name`` and ``cards``. Cards expose ``id``, ``kind``
    (company/material/process), ``name``, ``status`` and ``reduction_pct``.
    ``node_id`` links selection back to the network. ``result_node_id`` states
    which existing result supplies the status; recipient cards use their own
    selected operation rather than an unrelated company-wide bottleneck.

    Connections expose from/to IDs, status, reduction_pct, excluded, assumption
    and provenance. No excluded connection receives a calculated reduction.
    Selection accepts a displayed network/card ID. Missing or invalid selection
    becomes None and leaves the full process flow intact. No highlighting is
    performed here. No input object is modified or returned by reference.
    """
    process = '포토' if process is None else process
    if process not in network['process_outputs']:
        raise ValueError(f'등록되지 않은 공정: {process}')

    nodes = network['nodes']
    scopes = set(result.get('scopes', ['core']))
    cards = {key: {} for key, _ in COLUMNS}
    connections = {}
    items = {item['id']: item['name'] for item in network.get('original', {}).get('items', [])}

    def active(node):
        return node.get('scope', 'core') in scopes

    def add_card(column, node_id, kind, name=None, result_node_id=None):
        card_id = f'{column}:{node_id}'
        excluded = nodes[node_id].get('calculation_included') is False
        metric = result_node_id or node_id
        cards[column][card_id] = {
            'id': card_id,
            'kind': kind,
            'name': name or nodes[node_id]['name'],
            'node_id': node_id,
            'result_node_id': metric,
            **_state(result, metric, excluded),
        }
        if kind == 'material':
            cards[column][card_id]['evidence'] = _material_evidence(result, metric, excluded)
            cards[column][card_id]['evidence']['basis'] = material_basis(network, node_id)
        return card_id

    def connect(source, target, metric, source_edge_id, excluded=False,
                assumption=False, exclusion_reason=None):
        edge_id = f'{source_edge_id}|{source}|{target}'
        connections[edge_id] = {
            'id': edge_id,
            'from': source,
            'to': target,
            'result_node_id': metric,
            'source_edge_id': source_edge_id,
            'excluded': excluded,
            'assumption': assumption,
            'exclusion_reason': exclusion_reason,
            **_state(result, metric, excluded),
        }

    def material_parents(node_id):
        # Transport wrappers carry stock/arrival state but are not a fifth kind
        # of flow card. Keep their result ID on the collapsed connection.
        pending = [(key, key) for key in nodes[node_id].get('requires', [])]
        seen = set()
        while pending:
            key, metric = pending.pop()
            if key in seen or key not in nodes or not active(nodes[key]):
                continue
            seen.add(key)
            node = nodes[key]
            if node['kind'] in MATERIAL_KINDS:
                yield key, metric
            elif node['kind'] == 'transport':
                pending.extend((parent, metric) for parent in node.get('requires', []))

    def add_material(node_id):
        card_id = f'materials:{node_id}'
        if card_id in cards['materials']:
            return card_id
        node = nodes[node_id]
        name = items.get(node.get('item_id'))
        if node.get('material_id') in network.get('extended_materials', {}):
            name = network['extended_materials'][node['material_id']]['name']
        add_card('materials', node_id, 'material', name)
        owner = node.get('company_id')
        if owner in nodes and nodes[owner]['kind'] == 'company' and active(nodes[owner]):
            supplier_id = add_card('suppliers', owner, 'company')
            excluded = node.get('calculation_included') is False
            connect(supplier_id, card_id, owner, f'product:{node_id}', excluded,
                    exclusion_reason='계산 제외 품목' if excluded else None)
        for parent, metric in material_parents(node_id):
            parent_card = add_material(parent)
            excluded = node.get('calculation_included') is False or nodes[parent].get('calculation_included') is False
            connect(parent_card, card_id, metric, f'dependency:{parent}>{node_id}', excluded,
                    exclusion_reason='계산 제외 품목' if excluded else None)
        return card_id

    for edge in network.get('visual_edges', []):
        if process not in edge.get('processes', []) or edge.get('scope', 'core') not in scopes:
            continue
        material = edge['from']
        recipient = edge['to']
        if material not in nodes or recipient not in nodes:
            continue
        if nodes[material]['kind'] not in MATERIAL_KINDS or nodes[recipient]['kind'] != 'company':
            continue
        operation = network.get('operations', {}).get((recipient, process))
        if operation not in nodes or operation not in network['process_outputs'][process]:
            continue
        if not all(active(nodes[key]) for key in (material, recipient, operation)):
            continue

        material_id = add_material(material)
        process_id = add_card('processes', operation, 'process')
        recipient_id = add_card('recipients', recipient, 'company', result_node_id=operation)
        excluded, reason = _exclusion(network, edge)
        metric = edge.get('transport_node') or material
        if nodes.get(edge.get('calc_target'), {}).get('kind') == 'route':
            metric = edge['calc_target']
        connect(material_id, process_id, metric, edge.get('backbone_id', edge['id']),
                excluded, _assumed_share(network, edge, operation), reason)
        connect(process_id, recipient_id, operation, f'operation:{operation}')

    columns = [
        {'id': key, 'name': name, 'cards': sorted(cards[key].values(), key=lambda card: (card['name'], card['id']))}
        for key, name in COLUMNS
    ]
    all_cards = [card for column in columns for card in column['cards']]
    selected_node = next(
        (card['node_id'] for card in all_cards if selected in (card['id'], card['node_id'])),
        None,
    )
    return {
        'process': process,
        'selected': selected_node,
        'columns': columns,
        'connections': sorted(connections.values(), key=lambda edge: edge['id']),
    }
