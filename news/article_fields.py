"""User-cited article fields; literal provenance checks, no semantic verification."""
from datetime import date
import re


FIELD_LABELS = {
    'published_date': '기사 발행일', 'event_date': '사건 발생일',
    'facility': '시설·사업장', 'product': '제품·등급', 'supply_status': '기사상 공급 영향',
}
SUPPLY_STATUSES = ('미확인', '공급 중단·감소 명시', '공급 영향 미확인 명시',
                   '가능성·계획만 언급', '복구 보도')


def empty_fields():
    return {key: dict(value=None, quote=None, basis='unknown') for key in FIELD_LABELS}


def validate_fields(body, supplied=None):
    result = empty_fields()
    if supplied is None:
        return result
    if not isinstance(supplied, dict) or set(supplied)-set(FIELD_LABELS):
        raise ValueError('지원하지 않는 기사 구조화 항목입니다.')
    for key, claim in supplied.items():
        if not isinstance(claim, dict) or set(claim) != {'value','quote'}:
            raise ValueError('기사 항목에는 값과 원문 근거 문장이 필요합니다.')
        value, quote = claim['value'], claim['quote']
        if value is None or value == '' or key == 'supply_status' and value == '미확인':
            if quote:
                raise ValueError(FIELD_LABELS[key]+': 값을 지정하거나 근거 문장을 비워주세요.')
            continue
        if not isinstance(value,str) or len(value)>500:
            raise ValueError(FIELD_LABELS[key]+': 500자 이하의 값이 필요합니다.')
        if not isinstance(quote,str) or not quote.strip() or quote.strip() not in body:
            raise ValueError(FIELD_LABELS[key]+': 본문에 있는 근거 문장을 그대로 입력하세요.')
        value, quote = value.strip(), quote.strip()
        if not value:
            raise ValueError(FIELD_LABELS[key]+': 값을 입력하거나 미확인으로 남겨주세요.')
        if key.endswith('_date'):
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
                raise ValueError(FIELD_LABELS[key]+': YYYY-MM-DD 형식으로 입력하세요.')
            try:
                parsed = date.fromisoformat(value)
            except ValueError as error:
                raise ValueError(FIELD_LABELS[key]+': 유효한 날짜가 아닙니다.') from error
            dates = re.findall(r'(?<!\d)(\d{4})\s*(?:[-./]|년)\s*(\d{1,2})\s*(?:[-./]|월)\s*(\d{1,2})(?:\s*일)?(?!\d)',quote)
            if (parsed.year,parsed.month,parsed.day) not in [tuple(map(int,d)) for d in dates]:
                raise ValueError(FIELD_LABELS[key]+': 연·월·일이 모두 명시된 원문과 일치해야 합니다. 상대 날짜는 미확인으로 남겨주세요.')
        elif key == 'supply_status':
            if value not in SUPPLY_STATUSES[1:]:
                raise ValueError('지원하는 공급 영향 확인 수준을 선택하세요.')
        elif value.casefold() not in quote.casefold():
            raise ValueError(FIELD_LABELS[key]+': 입력한 이름·등급이 근거 문장에 포함되어야 합니다.')
        result[key] = dict(value=value,quote=quote,basis='user_cited')
    return result
