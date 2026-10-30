"""Conservative calculation eligibility for original relationship records.

This is a local metadata policy, not live verification of contracts. Company
supply evidence with limited item scope remains an explicitly assumed recipe.
Unrecognized or missing metadata never establishes calculation eligibility.
"""
ALLOWED_TIMES = {'documented', 'scope_limited'}


def relationship_decision(edge):
    kind = edge.get('relationship_kind')
    temporal = edge.get('temporal_status')
    if kind != 'supply':
        return False, f'공급 관계가 아님 ({kind or "미분류"})'
    if temporal not in ALLOWED_TIMES:
        return False, f'현재 공급 근거로 사용하지 않는 시점 ({temporal or "미분류"})'
    source = edge.get('relationship_source')
    if (edge.get('relationship_status') != '출처 있음' or not isinstance(source, str)
            or not source.startswith(('https://', 'http://'))):
        return False, '공급 관계 출처 미확인'
    return True, '공급 관계 근거를 사용한 가정 경로 · 현행 품목 계약·물량 확인과 별도'


def attach_coverage(network):
    """Trace missing required input groups through the actual dependency graph."""
    nodes = network['nodes']
    incomplete = {}
    for process, outputs in network['process_outputs'].items():
        todo = list(outputs)
        seen = set()
        gap_ids = set()
        while todo:
            key = todo.pop()
            if key in seen:
                continue
            seen.add(key)
            node = nodes[key]
            gap_ids.update(node.get('coverage_gap_ids', []))
            todo.extend(node.get('requires', []))
            if node.get('alt_vendor'):
                todo.append(node['alt_vendor'])
        if gap_ids:
            incomplete[process] = sorted(gap_ids)
    network['incomplete_processes'] = incomplete
    return network
