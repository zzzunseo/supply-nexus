"""Resolve complete mentions against registered names without fuzzy expansion."""
from copy import deepcopy
import unicodedata

from news.schema import assess_event, validate_event


TARGET_KINDS = frozenset({'company', 'material', 'product', 'resource', 'logistics'})


def normalize_name(value):
    """Normalize case, Unicode width and whitespace, retaining punctuation."""
    if not isinstance(value, str):
        raise ValueError('대상 이름은 문자열이어야 합니다.')
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def build_alias_index(network):
    """Index only public targets, preserving every collision in sorted order."""
    index = {}
    for key, entity in sorted(network['entities'].items()):
        if entity['kind'] not in TARGET_KINDS:
            continue
        target = {'id': key, 'name': entity['name'], 'kind': entity['kind']}
        for name in (key, entity['name'], *entity.get('aliases', [])):
            alias = normalize_name(name)
            if alias:
                index.setdefault(alias, {})[key] = target
    return {alias: [deepcopy(targets[key]) for key in sorted(targets)]
            for alias, targets in sorted(index.items())}


def resolve_name(name, index):
    """Resolve a full name only; ambiguous mentions never expand to all IDs."""
    candidates = deepcopy(index.get(normalize_name(name), []))
    status = 'resolved' if len(candidates) == 1 else 'ambiguous' if candidates else 'unknown'
    return {'mention': name, 'status': status, 'candidates': candidates,
            'target_id': candidates[0]['id'] if status == 'resolved' else None}


def assess_named_event(event, network, *, reviewed=False, approved_assumptions=()):
    """Preserve source mentions and resolve them before the existing review gate.

    No engine dispatch, sentence extraction or company/facility scope inference.
    """
    try:
        checked = validate_event(event)
    except (ValueError, TypeError) as error:
        return {'status': 'reject', 'reasons': [str(error)], 'candidate': None, 'mapping': []}
    index = build_alias_index(network)
    claim = checked['claims']['targets']
    mapping = [resolve_name(name, index) for name in claim['value'] or []]
    unresolved = [item for item in mapping if item['status'] != 'resolved']
    if unresolved:
        reasons = [f"{item['mention']}: " + ('여러 대상에 해당함' if item['status'] == 'ambiguous'
                   else '등록된 이름 없음') for item in unresolved]
        return {'status': 'hold', 'reasons': reasons, 'candidate': None,
                'event': checked, 'original_event': deepcopy(checked), 'mapping': mapping}
    ids = list(dict.fromkeys(item['target_id'] for item in mapping))
    if claim['value'] is not None:
        claim['value'] = ids
    logistics = {key for key, entity in network['entities'].items()
                 if entity['kind'] == 'logistics'}
    is_logistics = checked['event_type'] == 'logistics_disruption'
    wrong_kind = any((key not in logistics) if is_logistics else (key in logistics)
                     for key in ids)
    if wrong_kind:
        return {'status': 'hold', 'reasons': ['사건 종류와 대상 종류가 맞지 않음'],
                'candidate': None, 'event': checked,
                'original_event': deepcopy(event), 'mapping': mapping}
    result = assess_event(checked, network['nodes'], reviewed=reviewed,
                          approved_assumptions=approved_assumptions)
    result['mapping'] = mapping
    result['original_event'] = deepcopy(event)
    return result
