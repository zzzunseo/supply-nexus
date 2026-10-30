"""Validation and display metadata for the explicitly fictional UI dataset."""
import json
from pathlib import Path

DESCRIPTIONS = {
    '웨이퍼 제조': '반도체 공정의 바탕이 되는 웨이퍼 소재의 공급 흐름을 살펴봅니다.',
    '산화': '웨이퍼 표면의 산화막 형성에 연결된 예시 공급 흐름을 살펴봅니다.',
    '포토': '미세한 회로 패턴을 만드는 감광 소재와 노광 장비의 공급 흐름입니다.',
    '식각': '회로 패턴에 맞춰 재료를 제거하는 장비와 공정 가스의 공급 흐름입니다.',
    '증착·이온주입': '박막 형성과 전기적 특성 조절에 연결된 예시 공급 흐름입니다.',
    '금속배선': '소자 사이를 연결하는 배선 소재의 공급 흐름을 살펴봅니다.',
    'EDS': '웨이퍼 상태에서 전기적 특성을 검사하는 장비의 공급 흐름입니다.',
    '패키징': '가공된 웨이퍼에서 패키징 거점으로 이어지는 예시 공급 흐름입니다.',
}

NODE_TYPES = {'country_hub', 'company', 'fab', 'material_maker', 'mine'}
EVIDENCE_STATES = {'출처 있음', '가정값', '확인 필요'}


def validate_evidence(record):
    if record.get('status') not in EVIDENCE_STATES:
        raise ValueError('출처 상태는 출처 있음 / 가정값 / 확인 필요여야 합니다.')
    if 'source' not in record or 'source_year' not in record:
        raise ValueError('출처 및 기준연도 필드가 필요합니다.')
    if record['status'] == '출처 있음' and not record['source']:
        raise ValueError('출처 있음 상태에는 실제 출처가 필요합니다.')


def load_demo(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    ids = [n['id'] for n in data['nodes']]
    if len(ids) != len(set(ids)):
        raise ValueError('중복된 거점 ID가 있습니다.')
    edge_ids = [e['id'] for e in data['edges']]
    if len(edge_ids) != len(set(edge_ids)):
        raise ValueError('중복된 경로 ID가 있습니다.')
    for node in data['nodes']:
        node.setdefault('type', 'country_hub')  # Original country-only datasets remain valid.
        if node['type'] not in NODE_TYPES:
            raise ValueError(f"알 수 없는 노드 유형: {node['type']}")
        if node['type'] != 'country_hub' and (not node.get('country') or not node.get('company_name')):
            raise ValueError('기업 계열 거점에는 country와 company_name이 필요합니다.')
        if not -90 <= node['lat'] <= 90 or not -180 <= node['lon'] <= 180:
            raise ValueError(f"잘못된 좌표: {node['id']}")
    for edge in data['edges']:
        if edge['from'] not in ids or edge['to'] not in ids:
            raise ValueError(f"연결 거점이 없습니다: {edge['id']}")
        if not edge['processes'] or any(p not in data['processes'] for p in edge['processes']):
            raise ValueError(f"알 수 없는 공정: {edge['id']}")
    for scenario in data['scenarios']:
        if any(n not in ids for n in scenario['affected']):
            raise ValueError(f"시나리오 대상 거점이 없습니다: {scenario['name']}")
    if data.get('schema_version') == 'linked-demo-1':
        lookup = {n['id']: n for n in data['nodes']}
        items = {i['id']: i for i in data['items']}
        if len(items) != len(data['items']):
            raise ValueError('중복된 소재 ID가 있습니다.')
        for record in [*data['nodes'], *data['items'], *data['edges']]:
            validate_evidence(record)
        for node in data['nodes']:
            if node['type'] != 'country_hub':
                hub = lookup.get(node.get('country_hub_id'))
                if not hub or hub['type'] != 'country_hub' or hub['country'] != node['country']:
                    raise ValueError('기업의 소속 국가 거점이 일치하지 않습니다.')
        for process in data['processes']:
            core = data['core_companies'].get(process, [])
            if not 3 <= len(set(core)) <= 6 or len(core) != len(set(core)):
                raise ValueError('공정별 core 기업은 중복 없이 3~6개여야 합니다.')
            if any(cid not in lookup or lookup[cid]['type'] == 'country_hub' for cid in core):
                raise ValueError('core 목록에 유효하지 않은 기업이 있습니다.')
        for edge in data['edges']:
            item = items.get(edge.get('item_id'))
            if not item or item['name'] != edge['item']:
                raise ValueError('경로의 세부 소재 참조가 일치하지 않습니다.')
            if any(edge['from'] not in data['core_companies'][p] or
                   edge['to'] not in data['core_companies'][p] for p in edge['processes']):
                raise ValueError('선택 공정의 core 밖으로 연결된 경로가 있습니다.')
            if any(lookup[edge[k]]['type'] == 'country_hub' for k in ('from', 'to')):
                raise ValueError('계산 경로는 기업 계열 거점끼리 연결해야 합니다.')
            share = edge.get('share_pct')
            if share is not None and (isinstance(share, bool) or not isinstance(share, (int, float)) or not 0 <= share <= 100):
                raise ValueError('실제 배분율은 null 또는 0~100 숫자여야 합니다.')
            if edge.get('share_status') == '확인 필요' and share is not None:
                raise ValueError('확인되지 않은 배분율에 숫자를 넣을 수 없습니다.')
            if edge.get('relationship_status') == '출처 있음' and not edge.get('relationship_source'):
                raise ValueError('기업 관계 확인에는 별도 출처가 필요합니다.')
            if edge.get('item_status') == '출처 있음' and not edge.get('item_source'):
                raise ValueError('품목 확인에는 품목별 출처가 필요합니다.')
        evidence_path = path.with_name('evidence.json')
        if evidence_path.exists():
            evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
            catalog = {s['id']: s for s in evidence['sources']}
            for record in [*data['nodes'], *data['edges']]:
                for eid in record.get('evidence_ids', []) + record.get('country_evidence_ids', []):
                    if eid not in catalog:
                        raise ValueError(f'출처 원장에 없는 근거 ID: {eid}')
            data['evidence_catalog'] = evidence
    data['descriptions'] = DESCRIPTIONS
    return data
