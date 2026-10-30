"""Read-only directional selection for the flow and globe."""


def related_paths(edges, seeds):
    """Return ancestors and descendants separately, without sibling branches."""
    nodes = set(seeds)
    chosen = set()
    for reverse in (False, True):
        reached = set(seeds)
        pending = list(seeds)
        adjacency = {}
        for index, edge in enumerate(edges):
            source, target = (edge['to'], edge['from']) if reverse else (edge['from'], edge['to'])
            adjacency.setdefault(source, []).append((target, index))
        while pending:
            source = pending.pop()
            for target, index in adjacency.get(source, []):
                chosen.add(index)
                if target not in reached:
                    reached.add(target)
                    pending.append(target)
        nodes.update(reached)
    return nodes, chosen


def flow_emphasis(flow):
    cards = [card for column in flow['columns'] for card in column['cards']]
    seeds = {card['id'] for card in cards if card['node_id'] == flow.get('selected')}
    if not seeds:
        return {card['id'] for card in cards}, {edge['id'] for edge in flow['connections']}
    nodes, edges = related_paths(flow['connections'], seeds)
    return nodes, {flow['connections'][index]['id'] for index in edges}
