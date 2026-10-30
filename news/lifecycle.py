"""Immutable, reviewed incident revisions; never dispatch engine actions."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json

from news.entities import assess_named_event
from news.schema import validate_event


OPERATIONS = frozenset({'new', 'report', 'correct', 'recover'})


def empty_registry():
    return {'incidents': {}, 'receipts': {}}


def _time(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def _scope(event):
    claims = event['claims']
    return (event['event_type'], tuple(sorted(claims['targets']['value'])),
            claims['impact_scope']['value'])


def _identity(event):
    kind, targets, scope = _scope(event)
    return {'kind': kind, 'targets': list(targets), 'scope': scope,
            'occurred_at': _time(event['occurred_at']).astimezone(timezone.utc).isoformat()}


def _fingerprint(event, operation, incident_id):
    encoded = json.dumps([event, operation, incident_id], sort_keys=True,
                         ensure_ascii=False, separators=(',', ':'))
    return sha256(encoded.encode('utf-8')).hexdigest()


def transition(registry, event, network, *, operation='new', incident_id=None,
               expected_revision=None, reviewed=False, approved_assumptions=()):
    """Return a detached registry with new/report/correct/recover applied once.

    Only accepted changes get receipts. Rejected/held inputs can be reviewed again.
    Registry and control arguments belong to the caller, never the news payload.
    """
    def outcome(status, reasons=(), current_id=incident_id):
        return {'status': status, 'reasons': list(reasons),
                'incident_id': current_id, 'registry': deepcopy(registry)}

    if not isinstance(operation, str) or operation not in OPERATIONS:
        return outcome('reject', ['지원하지 않는 사건 작업'])
    if type(reviewed) is not bool:
        return outcome('reject', ['검토 여부는 bool이어야 함'])
    try:
        checked = validate_event(event)
        approved = tuple(approved_assumptions)
        if not set(approved) <= {'targets', 'rate', 'duration_days', 'impact_scope'}:
            raise ValueError('승인할 가정 필드가 올바르지 않음')
    except (ValueError, TypeError) as error:
        return outcome('reject', [str(error)])
    if operation == 'new':
        if incident_id is not None or expected_revision is not None:
            return outcome('reject', ['새 사건에는 기존 사건 ID·버전을 지정할 수 없음'])
    elif not isinstance(incident_id, str) or not incident_id.strip():
        return outcome('hold', ['갱신할 기존 사건 ID 필요'])
    fingerprint = _fingerprint(checked, operation, incident_id)
    receipt = registry['receipts'].get(checked['event_id'])
    if receipt:
        if receipt['fingerprint'] == fingerprint:
            return outcome('duplicate', ['이미 처리한 기사 입력'], receipt['incident_id'])
        return outcome('hold', ['같은 기사 입력 ID의 내용 또는 작업이 달라짐'])
    current = None
    if operation != 'new':
        current = registry['incidents'].get(incident_id)
        if current is None:
            return outcome('hold', ['갱신할 사건을 찾을 수 없음'])
        if type(expected_revision) is not int or expected_revision != current['revision']:
            return outcome('hold', ['현재 사건 버전과 일치하는 expected_revision 필요'])
        if current['status'] != 'active':
            return outcome('hold', ['이미 복구된 사건은 자동 재개할 수 없음'])
        if _time(checked['published_at']) < _time(current['latest_published_at']):
            return outcome('hold', ['현재 기록보다 오래된 기사 갱신'])
    assessable = deepcopy(checked)
    if operation == 'recover':
        if checked['event_type'] != 'recovery':
            return outcome('hold', ['복구 작업에는 recovery 사건 필요'])
        if checked['claims']['rate']['value'] != 0:
            return outcome('hold', ['완전 복구는 잔여 감소율 0 확인 필요. 부분 복구는 정정으로 처리'])
        assessable['event_type'] = current['event']['event_type']
    try:
        assessment = assess_named_event(assessable, network, reviewed=reviewed,
                                        approved_assumptions=approved)
    except (ValueError, TypeError) as error:
        return outcome('reject', [str(error)])
    if assessment['status'] != 'ready':
        return outcome(assessment['status'], assessment['reasons'])
    resolved = assessment['event']
    if current:
        if _scope(resolved) != _scope(current['event']):
            return outcome('hold', ['기존 사건과 대상·종류·범위가 다름'])
        if operation == 'report':
            same_start = _time(resolved['occurred_at']) == _time(current['event']['occurred_at'])
            same_values = all(resolved['claims'][key]['value'] == current['event']['claims'][key]['value']
                              and resolved['claims'][key]['basis'] == current['event']['claims'][key]['basis']
                              for key in ('rate', 'duration_days'))
            if not same_start or not same_values:
                return outcome('hold', ['기존 영향과 다른 추가 기사. 정정 여부 검토 필요'])
        if operation == 'recover' and _time(resolved['occurred_at']) < _time(current['event']['occurred_at']):
            return outcome('hold', ['복구 시점이 기존 사건 발생보다 빠름'])
    else:
        for existing_id, existing in sorted(registry['incidents'].items()):
            if _identity(resolved) in existing['identities']:
                return outcome('hold', ['같은 대상·범위·발생 시점의 사건 존재. 추가 기사 또는 정정 검토 필요'],
                               existing_id)
    updated = deepcopy(registry)
    key = incident_id if current else checked['event_id']
    revision = current['revision'] + 1 if current else 1
    history = deepcopy(current['history']) if current else []
    history.append({'operation': operation, 'revision': revision,
                    'event': deepcopy(checked), 'mapping': deepcopy(assessment['mapping']),
                    'approved_assumptions': sorted(set(approved))})
    record = deepcopy(current) if current else {}
    record.update(revision=revision, latest_published_at=checked['published_at'], history=history)
    if operation in ('new', 'correct'):
        identities = deepcopy(current['identities']) if current else []
        if _identity(resolved) not in identities:
            identities.append(_identity(resolved))
        record['identities'] = identities
        record.update(status='active', event=deepcopy(resolved),
                      candidate=deepcopy(assessment['candidate']))
    elif operation == 'recover':
        record.update(status='recovered', candidate=None)
    updated['incidents'][key] = record
    updated['receipts'][checked['event_id']] = {'fingerprint': fingerprint, 'incident_id': key}
    return {'status': 'accepted', 'reasons': [], 'incident_id': key, 'registry': updated}


def active_candidates(registry):
    """One candidate per active incident, ready for future whole-set replacement.

    Do not append these on rerun or translate recovery to target-wide restore.
    """
    return [{'incident_id': key, 'revision': record['revision'],
             'candidate': deepcopy(record['candidate'])}
            for key, record in sorted(registry['incidents'].items())
            if record['status'] == 'active']
