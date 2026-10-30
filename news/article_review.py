"""Local article review, distinct from fact verification and simulation dispatch.

Literal mentions are candidates only. Human review retains an exact excerpt;
registered relationships never become evidence that an article's customers
have actually suffered losses. No network fetching or model calls occur here.
"""
from copy import deepcopy
from hashlib import sha256
import re
from urllib.parse import urlsplit

from news.entities import build_alias_index
from news.article_fields import validate_fields, FIELD_LABELS


CLAIM_TYPES = ('미분류 · 검토 필요', '공급 중단·감소 보도', '사건 발생 · 공급 영향 미확인',
               '제한 가능성·계획', '비용·관세', '복구 보도')
SCOPES = ('미확인', '특정 시설·제품', '기업 전체', '등록 운송 경로')


def article_draft(network, headline, body, url=''):
    headline, body, url = headline.strip(), body.strip(), url.strip()
    if not body or len(body) > 20000 or len(headline) > 600:
        raise ValueError('기사 본문은 1~20,000자, 제목은 600자 이하로 입력하세요.')
    if url:
        parts = urlsplit(url)
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            raise ValueError('출처는 계정정보 없는 HTTP(S) 주소로 입력하세요.')
    # Match the original text to retain real offsets. No fuzzy entity expansion.
    hits = []
    for alias, candidates in build_alias_index(network).items():
        if len(alias) < 2 or ':' in alias:
            continue
        pattern = re.escape(alias).replace(r'\ ', r'\s+')
        if alias.isascii():
            pattern = r'(?<![A-Za-z0-9])' + pattern + r'(?![A-Za-z0-9])'
        for match in re.finditer(pattern, body, re.IGNORECASE):
            hits.append((match.start(), match.end(), candidates))
    accepted = []
    for start, end, candidates in sorted(hits, key=lambda row: (-(row[1]-row[0]), row[0])):
        if any(start < prior['end'] and prior['start'] < end for prior in accepted):
            continue
        accepted.append(dict(start=start, end=end, mention=body[start:end],
                             excerpt=body[max(0,start-45):min(len(body),end+75)],
                             candidates=deepcopy(candidates)))
    accepted.sort(key=lambda row: row['start'])
    fingerprint = sha256((headline+'\n'+url+'\n'+body).encode()).hexdigest()
    return dict(id=fingerprint, headline=headline or '제목 미입력', body=body, url=url or None,
                source_verified=False, mentions=accepted)


def candidate_ids(draft):
    return list(dict.fromkeys(c['id'] for hit in draft['mentions'] for c in hit['candidates']))


def related_routes(network, target):
    """Find registered outgoing relationships, stopping at local operations."""
    children = {}
    nodes = network['nodes']
    for key, node in nodes.items():
        for parent in node.get('requires', []):
            children.setdefault(parent, set()).add(key)
    reached, pending = set(), [target]
    while pending:
        key = pending.pop()
        if key in reached:
            continue
        reached.add(key)
        if nodes[key]['kind'] not in ('operation', 'process'):
            pending.extend(children.get(key, ()))
    rows, seen = [], set()
    for edge in network['visual_edges']:
        if edge['kind'] == 'backbone':
            item = edge['evidence']['item_id']
            product = edge['from'] if nodes[edge['from']]['kind'] in ('product','material') else f"supply:{edge['from']}:{item}"
            if product not in reached and edge['from'] != target and edge.get('transport_node') not in reached:
                continue
            evidence = edge['evidence']
            basis = '기업 간 공급관계 근거 · 해당 품목의 현행 계약 미확인' if network['relationship_decisions'][edge['backbone_id']]['included'] else '참고 관계 · 현재 공급 관계로 사용하지 않음'
            source = evidence.get('relationship_source')
            material = evidence['item']
            identifier = edge['backbone_id']
        else:
            if (edge['from'] not in reached and edge.get('transport_node') not in reached) or not edge.get('processes'):
                continue
            if not any(company == edge['to'] for company, _ in network['operations']):
                continue
            material = nodes[edge['from']]['name']
            basis = '소재 용도에 따른 추가 경로 가정 · 실제 납품 미확인'
            source = edge.get('source') or nodes[edge['from']].get('source')
            identifier = edge['id']
        token = (edge['from'], edge['to'], material, tuple(edge.get('processes', [])))
        if token in seen:
            continue
        seen.add(token)
        rows.append(dict(id=identifier, supplier=nodes[edge['evidence']['from']]['name'] if edge['kind']=='backbone' else nodes[edge['from']]['name'], material=material,
                         recipient=nodes[edge['to']]['name'], processes=list(edge.get('processes', [])),
                         basis=basis, source=source, scope=edge.get('scope','core'), scoring_included=edge.get('calculation_included', True),
                         impact_status='실제 고객 영향 미확인'))
    return rows


def review_article(network, draft, target, quote='', claim_type=CLAIM_TYPES[0], scope=SCOPES[0], fields=None):
    if claim_type not in CLAIM_TYPES or scope not in SCOPES:
        raise ValueError('지원하는 사건 종류와 범위를 선택하세요.')
    if target is not None and target not in candidate_ids(draft):
        raise ValueError('원문에서 찾은 후보 중 검토 대상을 선택하세요.')
    quote = quote.strip()
    if target is not None:
        if not quote or quote not in draft['body']:
            raise ValueError('근거 문장은 붙여넣은 본문의 일부를 그대로 입력하세요.')
        if not any(quote.find(hit['mention']) >= 0 and any(c['id']==target for c in hit['candidates'])
                   for hit in draft['mentions']):
            raise ValueError('선택한 대상의 언급을 포함하는 원문 근거를 입력하세요.')
    elif quote and quote not in draft['body']:
        raise ValueError('근거 문장은 본문과 일치해야 합니다.')
    checked_fields = validate_fields(draft['body'], fields)
    unknowns = ['기사 내용의 독립 검증', '실제 고객·품목별 공급 계약과 구매 비중',
                '고객 재고와 대체품 인증·공급 여력', '실제 생산 영향의 크기와 시점']
    unknowns += [label+' 미확인' for key,label in FIELD_LABELS.items() if checked_fields[key]['basis']=='unknown']
    if not draft['url']:
        unknowns.insert(0, '원문 출처 URL')
    if not target:
        unknowns.insert(0, '등록 대상과의 연결')
    if scope == SCOPES[0]:
        unknowns.insert(0, '사건 영향 범위')
    # Missing quantities stay missing, even if a number appears in the prose.
    unknowns += ['계산에 사용할 공급 감소율·적용 기간은 별도 확인 필요']
    return dict(review_version=2, fields=checked_fields, article=deepcopy(draft), target_id=target,
                target_name=network['nodes'][target]['name'] if target else None,
                excerpt=quote or None, claim_type=claim_type, scope=scope,
                status='사용자 원문 검토' if target and quote else '연결 보류',
                routes=related_routes(network,target) if target else [], unknowns=unknowns,
                simulation_candidate=None, reported_rate=None, reported_duration_days=None,
                warning='본문에 이름이 등장했다는 사실만으로 피해·중단 대상이라고 판단하지 않습니다.')
