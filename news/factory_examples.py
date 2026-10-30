"""Authored validation examples, explicitly not live or recorded model outputs."""
from .article_fields import FIELD_LABELS
from .factory_ai import AKM_SOURCE, prepare_factory_article, validate_factory_result

EXAMPLES = {
    'akm': dict(label='AKM · 과거 화재 사례의 범위 일치', url=AKM_SOURCE,
        body='2020년 10월 20일 AKM의 노베오카 공장에서 화재가 발생했다. AD/DA 변환 칩의 공급에 영향이 발생했다. 조기 복구는 어렵고 외부 협력을 통한 대체 생산을 준비한다고 밝혔다.'),
    'unknown': dict(label='JSR · 공장·제품·출하 영향 미확인 (가상)', url='',
        body='JSR의 한 공장에서 화재가 발생했다. 피해 공장의 이름과 생산 품목은 공개되지 않았다. 출하 영향은 아직 확인되지 않았다.'),
    'tariff': dict(label='JSR · 관세 기사 제외 (가상)', url='',
        body='JSR의 소재에 대한 관세 인상 가능성이 논의됐다. 공장 화재나 가동 중단은 발생하지 않았다.'),
    'comparison': dict(label='JSR · 비교 언급을 사건으로 오인하지 않기 (가상)', url='',
        body='다른 기업의 공장 화재를 계기로 JSR의 안전 관리 체계가 비교 소개됐다. JSR 공장에서 발생한 사고는 아니다.'),
}


def example_proposal(key, registry):
    body = EXAMPLES[key]['body']
    proposal = dict(event_type='factory_fire',event_quote=body,company_id='akm' if key=='akm' else 'jsr',
        company_quote=body,fields={k:dict(value=None,quote=None) for k in FIELD_LABELS},
        route_reviews=[],findings=[],review_questions=[])
    if key=='akm':
        proposal['fields'].update(event_date=dict(value='2020-10-20',quote=body),
            facility=dict(value='노베오카 공장',quote=body),product=dict(value='AD/DA 변환 칩',quote=body),
            supply_status=dict(value='공급 중단·감소 명시',quote=body))
        proposal['route_reviews']=[dict(route_id='case:akm-rme-dac',decision='examine',quote=body,
            reason='피해 시설·제품·발생일이 등록된 과거 사례와 일치하므로 고객 기록을 함께 검토합니다.')]
        proposal['findings']=[dict(quote=body,interpretation='대체 생산 준비는 완료·출하 재개를 뜻하지 않습니다.')]
        topics=['qualification','capacity','inventory']
    elif key=='unknown':
        proposal['fields']['supply_status']=dict(value='공급 영향 미확인 명시',quote='출하 영향은 아직 확인되지 않았다.')
        proposal['route_reviews']=[dict(route_id=r['id'],decision='hold',quote=body,
            reason='피해 공장·제품이 불명확하므로 기업 관계만으로 고객 타격을 적용하지 않습니다.')
            for r in registry['routes'].values() if r['supplier']=='jsr']
        topics=['facility','product','customer_contract']
    else:
        proposal.update(event_type='other' if key=='tariff' else 'no_event',company_id=None,company_quote='')
        topics=[]
    proposal['review_questions']=[dict(topic=t,quote=body,reason='예시 본문에는 해당 조건을 확인할 자료가 없습니다.') for t in topics]
    return proposal


def load_validation_example(registry,key):
    example=EXAMPLES[key]
    draft=prepare_factory_article(example['body'],example['url'])
    checked=validate_factory_result(registry,draft,example_proposal(key,registry))
    checked['provenance']=dict(method='validation_example',model=None,article_id=draft['id'])
    return checked
