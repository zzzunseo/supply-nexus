"""News claims remain distinct from reviewed simulation assumptions."""
from copy import deepcopy
from datetime import datetime
from math import isfinite
from urllib.parse import urlsplit

from simulation.schema import validate_parsed


FIELDS = {'schema_version', 'event_id', 'headline', 'published_at', 'occurred_at',
          'event_type', 'sources', 'claims'}
CLAIMS = {'targets', 'rate', 'duration_days', 'impact_scope'}
EVENT_TYPES = {'supply_disruption', 'logistics_disruption', 'tariff', 'recovery', 'other'}


def _text(value, label, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'{label}: 비어 있지 않은 문자열이 필요합니다.')


def _date(value, label):
    _text(value, label, 64)
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError(f'{label}: ISO 날짜·시간이 필요합니다.') from error
    if parsed.tzinfo is None:
        raise ValueError(f'{label}: 시간대가 필요합니다.')


def validate_event(event):
    """Validate structure/provenance, not the truth of the cited news."""
    if not isinstance(event, dict) or set(event) != FIELDS:
        raise ValueError('뉴스 사건 필드가 누락되었거나 알 수 없는 필드가 있습니다.')
    if type(event['schema_version']) is not int or event['schema_version'] != 1:
        raise ValueError('뉴스 형식 버전은 1이어야 합니다.')
    _text(event['event_id'], '사건 ID', 128)
    _text(event['headline'], '제목', 600)
    _date(event['published_at'], '기사 발행 시점')
    if event['occurred_at'] is not None:
        _date(event['occurred_at'], '사건 발생 시점')
    if not isinstance(event['event_type'], str) or event['event_type'] not in EVENT_TYPES:
        raise ValueError('지원하지 않는 사건 종류입니다.')
    sources = event['sources']
    if not isinstance(sources, list) or not 1 <= len(sources) <= 30:
        raise ValueError('출처는 1~30개가 필요합니다.')
    ids = set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != {'id', 'url', 'title', 'published_at'}:
            raise ValueError('출처 필드가 올바르지 않습니다.')
        for key in ('id', 'url', 'title'):
            _text(source[key], f'출처 {key}')
        parts = urlsplit(source['url'])
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            raise ValueError('출처 URL은 계정정보 없는 HTTP(S) 주소여야 합니다.')
        _date(source['published_at'], '출처 발행 시점')
        if source['id'] in ids:
            raise ValueError('출처 ID가 중복되었습니다.')
        ids.add(source['id'])
    claims = event['claims']
    if not isinstance(claims, dict) or set(claims) != CLAIMS:
        raise ValueError('대상·영향률·기간·영향 범위 주장이 필요합니다.')
    for name, claim in claims.items():
        if not isinstance(claim, dict) or set(claim) != {'value', 'basis', 'evidence'}:
            raise ValueError('주장에는 값·근거 종류·근거 문장이 필요합니다.')
        basis, value, evidence = claim['basis'], claim['value'], claim['evidence']
        if basis not in ('reported', 'assumption', 'unknown'):
            raise ValueError('근거 종류는 reported, assumption, unknown 중 하나입니다.')
        if not isinstance(evidence, list) or len(evidence) > 30:
            raise ValueError('근거 문장 목록이 올바르지 않습니다.')
        for item in evidence:
            if not isinstance(item, dict) or set(item) != {'source_id', 'quote'}:
                raise ValueError('근거에는 출처 ID와 원문 문장이 필요합니다.')
            if not isinstance(item['source_id'], str) or item['source_id'] not in ids:
                raise ValueError('근거가 등록된 출처를 참조하지 않습니다.')
            _text(item['quote'], '근거 문장')
        if basis == 'unknown':
            if value is not None or evidence:
                raise ValueError('미확인 주장은 값과 근거를 비워야 합니다.')
            continue
        if value is None or (basis == 'reported' and not evidence):
            raise ValueError('기사 주장에는 값과 출처 문장이 필요합니다.')
        if name == 'targets':
            if not isinstance(value, list) or not 1 <= len(value) <= 100:
                raise ValueError('대상은 1~100개 ID 목록이어야 합니다.')
            for key in value:
                _text(key, '대상 ID', 256)
            if len(set(value)) != len(value):
                raise ValueError('대상 ID가 중복되었습니다.')
        elif name == 'rate':
            maximum = 5 if event['event_type'] == 'tariff' else 1
            if type(value) not in (int, float) or not isfinite(value) or not 0 <= value <= maximum:
                raise ValueError('영향률 범위가 올바르지 않습니다.')
        elif name == 'duration_days':
            if type(value) is not int or not 1 <= value <= 365:
                raise ValueError('기간은 1~365일 정수여야 합니다.')
        elif value not in ('whole_entity', 'registered_route', 'facility', 'country', 'unknown'):
            raise ValueError('영향 범위가 올바르지 않습니다.')
    return deepcopy(event)


def assess_event(event, known_targets, *, reviewed=False, approved_assumptions=()):
    """Return a candidate only after external review; never apply it to the engine.

    Review/assumption approval are caller-controlled arguments, never news fields.
    reported means cited in a report, not independently verified or factual truth.
    """
    if type(reviewed) is not bool:
        raise ValueError('검토 여부는 bool이어야 합니다.')
    approved = set(approved_assumptions)
    if not approved <= CLAIMS:
        raise ValueError('승인할 가정 필드가 올바르지 않습니다.')
    try:
        checked = validate_event(event)
    except (ValueError, TypeError) as error:
        return {'status': 'reject', 'reasons': [str(error)], 'candidate': None}
    reasons = []
    claims = checked['claims']
    if not reviewed:
        reasons.append('사람의 사건·출처·범위 검토 필요')
    for name in sorted(CLAIMS):
        if claims[name]['basis'] == 'unknown':
            reasons.append(f'{name}: 미확인')
        elif claims[name]['basis'] == 'assumption' and name not in approved:
            reasons.append(f'{name}: 가정 승인 필요')
    targets = claims['targets']['value'] or []
    if any(target not in known_targets for target in targets):
        reasons.append('등록되지 않은 대상: 이름 연결 검토 필요')
    scope = claims['impact_scope']['value']
    if scope not in ('whole_entity', 'registered_route'):
        reasons.append('시설·국가 범위를 기업 전체 영향으로 자동 변환할 수 없음')
    if checked['occurred_at'] is None:
        reasons.append('사건 발생 시점 미확인')
    if checked['event_type'] in ('recovery', 'other'):
        reasons.append('사건 갱신/복구 또는 미지원 유형 검토 필요')
    if checked['event_type'] == 'logistics_disruption' and scope != 'registered_route':
        reasons.append('물류 사건은 등록된 경로 범위 확인 필요')
    if reasons:
        return {'status': 'hold', 'reasons': reasons, 'candidate': None, 'event': checked}
    assumed = sorted(name for name in CLAIMS if claims[name]['basis'] == 'assumption')
    note = '뉴스 검토 후보 · 실제 공급량 확정값 아님'
    if assumed:
        note += ' · 승인된 가정: ' + ', '.join(assumed)
    candidate = validate_parsed({
        'action': 'apply',
        'kind': 'tariff' if checked['event_type'] == 'tariff' else 'supply',
        'targets': deepcopy(targets),
        'rate': claims['rate']['value'],
        'days': claims['duration_days']['value'],
        'text': checked['headline'],
        'note': note,
    }, known_targets)
    return {'status': 'ready', 'reasons': [], 'candidate': candidate, 'event': checked}
