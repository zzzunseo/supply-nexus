"""Offline issue interpretation and validated scenarios. No network in this module."""
import re
from copy import deepcopy
from math import isfinite

COMPANY_ALIASES = {
    'samsung': ['삼성', '삼성전자'], 'tsmc': ['티에스엠씨'], 'shinetsu': ['신에츠'],
    'sumco': ['섬코'], 'airliquide': ['에어리퀴드', '에어 리퀴드'],
    'airproducts': ['에어프로덕츠', '에어 프로덕츠'], 'jsr': ['제이에스알'],
    'tok': ['도쿄오카', '도쿄 오카'], 'fujifilm': ['후지필름'], 'asml': ['에이에스엠엘'],
    'lam': ['램리서치', '램 리서치'], 'applied': ['어플라이드'], 'merck': ['머크'],
    'advantest': ['어드반테스트'], 'teradyne': ['테라다인'], 'ase': ['에이에스이'], 'amkor': ['앰코']}
ITEM_ALIASES = {'photoresist':['감광재', '포토레지스트'], 'developer':['현상액', 'TMAH'],
    'oxygen':['산소'], 'hydrogen':['수소'], 'lithography':['노광 장비'], 'etch-gas':['CF4', '사불화탄소'],
    'wafer-tester':['웨이퍼 검사 장비'], 'polished-wafer':['폴리시드 웨이퍼'], 'epi-wafer':['에피 웨이퍼']}
COUNTRY_ALIASES = {'한국':['대한민국', 'korea'], '일본':['japan'], '대만':['taiwan'],
    '미국':['미국', 'usa'], '네덜란드':['netherlands'], '프랑스':['france'], '독일':['germany'],
    '중국':['china'], '말레이시아':['malaysia']}
FIELDS = ['countries', 'companies', 'items', 'regions', 'facilities', 'unresolved']


def contains(text, name):
    if re.fullmatch(r'[A-Za-z0-9 .-]+', name):
        return bool(re.search(r'(?<![a-z0-9])' + re.escape(name.lower()) + r'(?![a-z0-9])', text.lower()))
    return name.lower() in text.lower()


def catalog(data):
    return {'countries': sorted({n['country'] for n in data['nodes']}),
        'companies': [{'id': n['id'], 'name': n['company_name'], 'country': n['country']}
                      for n in data['nodes'] if n.get('company_name')],
        'items': [{'id': i['id'], 'name': i['name']} for i in data.get('items', [])],
        'facilities': [{'id': f['id'], 'name': f['name'], 'region': f['region']} for f in data.get('facilities', [])]}


def offline_extract(text, data, previous=None):
    """Conservative, documented test syntax; this is not an LLM or news verification."""
    draft = {k: [] for k in FIELDS}
    draft.update(event_type='unknown', loss_pct=None, tariff_pct=None, duration_days=None, facility_requested=False)
    known_aliases = []
    for n in data['nodes']:
        if not n.get('company_name'):
            continue
        aliases = [n['company_name'], n['id']] + COMPANY_ALIASES.get(n['id'], [])
        known_aliases += aliases
        if any(contains(text, a) for a in aliases):
            draft['companies'].append(n['id'])
    for item in data.get('items', []):
        aliases = [item['name'], item['id']] + ITEM_ALIASES.get(item['id'], [])
        known_aliases += aliases
        if any(contains(text, a) for a in aliases):
            draft['items'].append(item['id'])
    for country in sorted({n['country'] for n in data['nodes']}):
        aliases = [country] + COUNTRY_ALIASES.get(country, [])
        known_aliases += aliases
        if any(contains(text, a) for a in aliases):
            draft['countries'].append(country)
    for f in data.get('facilities', []):
        if contains(text, f['name']):
            draft['facilities'].append(f['id'])
        elif contains(text, f['region']):
            draft['regions'].append(f['region'])
    for region in ['구마모토', '규슈', '도호쿠', '오사카', '도쿄', '후쿠시마', '홋카이도', '이시카와', '노토', '히로시마', '후쿠오카']:
        if region in text and region not in draft['regions']:
            draft['regions'].append(region)
    draft['facility_requested'] = bool(re.search(r'공장|시설|fab|factory|지진|홍수|화재', text, re.I) or draft['regions'] or draft['facilities'])
    # Never silently convert an unknown named factory into a whole-country event.
    residue = text
    for alias in sorted(known_aliases, key=len, reverse=True):
        residue = re.sub(re.escape(alias), ' ', residue, flags=re.I)
    for word in re.findall(r'[A-Za-z][A-Za-z0-9_-]{2,}', residue):
        if word.lower() not in {'supply','loss','days','day','tariff','factory','fab','earthquake','percent'}:
            draft['unresolved'].append(word)
    for word in ['희토류', '노키아', '키옥시아', '도시바']:
        if word in text:
            draft['unresolved'].append(word)
    prefix = re.split(r'공급|생산|가동|지진|관세|공장|시설|전면|완전', residue, maxsplit=1)[0]
    prefix = re.sub(r'그럼|그러면|가정|만약|에서|으로|로 인해|이슈|기업|지역|소재|능력|국가|전체', ' ', prefix)
    # Unknown Korean suppliers/materials must not broaden a known country's scope.
    if draft['countries'] and draft['event_type'] != 'tariff':
        draft['unresolved'] += [w for w in re.findall(r'[가-힣]{2,}', prefix) if w not in ('트럼프','대통령','일본산','미국산')]
    if re.search(r'증가|확대|늘려', text) and not re.search(r'기간|일수', text):
        draft['unresolved'].append('증가 이슈는 감소율로 자동 변환하지 않습니다. 공급 감소 가정을 명시하세요.')
    if re.search(r'→|->|에서.+(?:으로|까지)|수출|수입', text) and '관세' not in text:
        draft['unresolved'].append('방향이 지정된 거래 이슈는 테스트 모드에서 자동 적용하지 않습니다. 대상 기업과 소재로 범위를 명시하세요.')
    is_followup = bool(previous and re.search(r'그럼|그러면|대신|바꿔|수정|변경|기간|강도|으로 해|로 해|퍼센트|%|일', text))
    has_target = any(draft[k] for k in FIELDS)
    if not has_target and is_followup:
        for key in FIELDS + ['facility_requested', 'event_type', 'loss_pct', 'tariff_pct', 'duration_days']:
            draft[key] = deepcopy(previous.get(key, draft[key]))
    if '관세' in text or 'tariff' in text.lower():
        draft['event_type'] = 'tariff'
    elif re.search(r'공급|가동|중단|감소|차질|지진|화재|홍수|supply|loss', text, re.I):
        draft['event_type'] = 'supply'
    # Multiple percentages have ambiguous roles in test mode.
    percentages = re.findall(r'(-?\d+(?:\.\d+)?)\s*(?:%|퍼센트)', text)
    if len(percentages) == 1:
        key = 'tariff_pct' if draft['event_type'] == 'tariff' else 'loss_pct'
        draft[key] = float(percentages[0])
        if key == 'loss_pct' and re.search(r'가동률|가용률', text) and not re.search(r'감소|하락|중단', text):
            draft[key] = 100 - float(percentages[0])
    elif len(percentages) > 1:
        draft['unresolved'].append('복수 비율의 역할: 한 번에 하나의 감소율 또는 관세율을 입력하세요')
    if draft['event_type'] == 'supply' and re.search(r'완전\s*중단|전면\s*중단', text):
        draft['loss_pct'] = 100
    duration = re.search(r'(-?\d+)\s*(?:일|days?)', text, re.I)
    if duration:
        draft['duration_days'] = int(duration.group(1))
    # A new entity never inherits an old event's numeric assumptions implicitly.
    return draft


def validate_facilities(records, data):
    """A facility must have sourced capacity-to-edge mappings before it can calculate."""
    nodes = {n['id']: n for n in data['nodes']}
    edges = {e['id']: e for e in data['edges']}
    seen = set()
    if not isinstance(records, list):
        raise ValueError('facilities는 목록이어야 합니다.')
    for f in records:
        if not isinstance(f, dict):
            raise ValueError('시설 정보는 객체여야 합니다.')
        if f.get('id') in seen or not f.get('id'):
            raise ValueError('시설 ID가 없거나 중복됩니다.')
        seen.add(f['id'])
        if f.get('company_id') not in nodes or not nodes[f['company_id']].get('company_name') or not f.get('name') or not f.get('region') or not f.get('country'):
            raise ValueError('시설의 기업·국가·지역·이름이 필요합니다.')
        for key, lo, hi in [('lat', -90, 90), ('lon', -180, 180)]:
            v = f.get(key)
            if type(v) not in (int, float) or not isfinite(v) or not lo <= v <= hi:
                raise ValueError('시설 좌표를 확인하세요.')
        if f.get('status') != '출처 있음' or not str(f.get('source', '')).startswith('https://') or not f.get('source_year'):
            raise ValueError('시설 위치의 출처·기준연도가 필요합니다.')
        if not isinstance(f.get('edge_capacity_shares'), dict) or not f['edge_capacity_shares']:
            raise ValueError('시설별 경로 공급 비중이 필요합니다.')
        for edge_id, mapping in f['edge_capacity_shares'].items():
            if not isinstance(mapping, dict):
                raise ValueError('시설 공급 비중의 값·출처·연도가 필요합니다.')
            fraction = mapping.get('fraction')
            if edge_id not in edges or edges[edge_id]['from'] != f['company_id']:
                raise ValueError('시설과 공급 경로의 기업이 일치하지 않습니다.')
            if type(fraction) not in (int, float) or not isfinite(fraction) or not 0 < fraction <= 1:
                raise ValueError('시설 공급 비중은 0 초과 1 이하입니다.')
            if not str(mapping.get('source', '')).startswith('https://') or not mapping.get('source_year'):
                raise ValueError('시설 공급 비중의 출처·연도가 필요합니다.')
    return records


def assess_issue(draft, data):
    """Only this deterministic gate may choose calculation edges."""
    d = deepcopy(draft)
    required = []
    for k in FIELDS:
        if not isinstance(d.get(k), list) or any(not isinstance(x, str) for x in d[k]):
            raise ValueError('이슈 해석 형식을 확인하세요.')
        d[k] = list(dict.fromkeys(d[k]))[:20]
    companies = {n['id']: n for n in data['nodes'] if n.get('company_name')}
    items = {i['id']: i for i in data.get('items', [])}
    countries = {n['country'] for n in data['nodes']}
    for field, allowed in [('companies', companies), ('items', items), ('countries', countries),
                           ('facilities', {f['id'] for f in data.get('facilities', [])}),
                           ('regions', {f['region'] for f in data.get('facilities', [])})]:
        invalid = [v for v in d[field] if v not in allowed]
        d['unresolved'] += invalid
        d[field] = [v for v in d[field] if v in allowed]
    if d['unresolved']:
        required.append('현재 모델에서 식별·연결하지 못한 대상: ' + ', '.join(d['unresolved']))
    for key, hi in [('loss_pct',100), ('tariff_pct',1000), ('duration_days',365)]:
        v = d.get(key)
        if v is not None and (type(v) not in (int, float) or not isfinite(v) or not 0 <= v <= hi or key == 'duration_days' and (v < 1 or int(v) != v)):
            required.append(f'{key}: 허용 범위를 벗어났습니다.')
    factors = {}
    selected_facilities = []
    facilities_needed = bool(d.get('facility_requested') or d['facilities'] or d['regions'])
    if facilities_needed:
        if not d['regions'] and not d['facilities']:
            required.append('피해 지역 또는 시설명을 지정해야 합니다. 국가·기업 전체 공장을 피해 범위로 자동 간주하지 않습니다.')
        for f in data.get('facilities', []):
            if d['facilities'] and f['id'] not in d['facilities']:
                continue
            if d['regions'] and f['region'] not in d['regions']:
                continue
            if d['companies'] and f['company_id'] not in d['companies']:
                continue
            if d['countries'] and f['country'] not in d['countries']:
                continue
            if not any(d[k] for k in ['facilities','regions','companies','countries']):
                continue
            selected_facilities.append(f)
            for eid, mapping in f['edge_capacity_shares'].items():
                if d['items'] and next(e for e in data['edges'] if e['id']==eid)['item_id'] not in d['items']:
                    continue
                factors[eid] = factors.get(eid, 0) + mapping['fraction']
        if not selected_facilities:
            required.append('해당 지역·기업의 검증된 공장 위치와 품목별 공급 비중이 없습니다. 본사 좌표를 공장 좌표로 대신 사용하지 않습니다.')
        if any(v > 1 + 1e-9 for v in factors.values()):
            required.append('선택 시설들의 같은 공급 경로 비중 합계가 100%를 넘습니다.')
    else:
        target_companies = set(d['companies'])
        if d['countries']:
            country_ids = {k for k,n in companies.items() if n['country'] in d['countries']}
            target_companies = target_companies & country_ids if target_companies else country_ids
        for e in data['edges']:
            if (d['countries'] or d['companies']) and e['from'] not in target_companies and e['to'] not in target_companies:
                continue
            # With a material qualifier, a country/company denotes its supplier.
            if d['items'] and (d['countries'] or d['companies']) and e['from'] not in target_companies:
                continue
            if d['items'] and e['item_id'] not in d['items']:
                continue
            if any(d[k] for k in ['countries','companies','items']):
                factors[e['id']] = 1.0
    if d.get('event_type') == 'tariff':
        if d.get('tariff_pct') is None:
            required.append('관세율을 입력하세요.')
        required += ['실제 적용 여부·시행일·수입국·원산지·HS 코드 확인 필요',
            '생산 차질 계산에는 별도의 납기 지연·공급 감소율·대체 가능성 정보가 필요합니다.']
        answer = '관세는 비용 이슈로 분류했습니다. 관세율을 생산 감소율로 바꾸지 않습니다.'
        if type(d.get('tariff_pct')) in (int,float) and isfinite(d['tariff_pct']) and 0 <= d['tariff_pct'] <= 1000:
            answer += f" 과세 기준 가격을 100으로 놓고 관세만 단순 가산하면 {100+d['tariff_pct']:g}입니다(설명용 가정)."
        answer += ' 대체 원산지의 공급처·품목 등급·인증·추가 여력을 확인한 뒤 비교해야 합니다. 단순 경유를 관세 절감 경로로 추천하지 않습니다.'
    elif d.get('event_type') == 'supply':
        if d.get('loss_pct') is None:
            required.append('공급 능력 감소율(0~100%)을 가정으로 입력하세요. 예: 공급 50% 감소')
        if d.get('duration_days') is None:
            required.append('이슈 기간(1~365일)을 입력하세요. 예: 14일')
        if not factors:
            required.append('계산에 연결할 등록된 공급 경로가 없습니다.')
        answer = '입력 내용을 가정 시나리오로 해석했습니다. 아래 대상과 조건을 확인하면 지구본에 적용할 수 있습니다.'
    else:
        required.append('공급 감소 또는 관세 이슈인지 명시하세요.')
        answer = '테스트 모드에서는 등록된 대상과 공급 감소율·기간을 구체적으로 입력해 주세요.'
    can_apply = d.get('event_type') == 'supply' and not required
    affected_edges = [e for e in data['edges'] if e['id'] in factors]
    names = d['countries'] + [companies[k]['company_name'] for k in d['companies']] + [items[k]['name'] for k in d['items']] + [f['name'] for f in selected_facilities]
    return {'draft': d, 'can_apply': can_apply, 'answer': answer, 'required': required,
        'target_label': ' · '.join(names) or '대상 확인 필요', 'edge_count': len(factors),
        'processes': [p for p in data['processes'] if any(p in e['processes'] for e in affected_edges)],
        'edge_factors': factors, 'facilities': [{'name': f['name'], 'source': f['source'], 'source_year': f['source_year']} for f in selected_facilities],
        'status': '가정 · 적용 가능' if can_apply else '추가 확인 필요'}


def scenario_from_assessment(assessment):
    if not assessment['can_apply']:
        raise ValueError('확인되지 않은 이슈는 계산에 적용할 수 없습니다.')
    return {'name': '대화 시나리오 · ' + assessment['target_label'], 'affected': [],
        'edge_impact_factors': assessment['edge_factors'], 'custom_issue': True,
        'description': '사용자가 입력한 가정입니다. 실제 사건 발생이나 시설 피해를 검증한 결과가 아닙니다.'}
