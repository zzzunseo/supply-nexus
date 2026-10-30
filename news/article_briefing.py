"""Offline presentation notes derived only from a saved human review."""
from .article_exposure import process_exposure

INTERPRETATIONS = {
    '공급 중단·감소 보도': '공급 차질로 분류한 기사입니다. 등록 경로는 우선 확인할 범위이며, 고객의 실제 생산 감소를 뜻하지 않습니다.',
    '사건 발생 · 공급 영향 미확인': '시설 사건과 출하 차질은 별개입니다. 사고 발생만으로 기업 전체 중단이나 고객 피해를 확정할 수 없습니다.',
    '제한 가능성·계획': '계획·검토 단계와 시행을 구분해야 합니다. 적용 시점과 대상 품목을 확인하기 전에는 실제 공급 중단으로 취급하지 않습니다.',
    '비용·관세': '비용 변화로 검토하는 기사입니다. 관세율·가격 상승률을 소재 부족률이나 생산 감소율로 환산하지 않습니다.',
    '복구 보도': '재가동과 정상 출하는 구분해야 합니다. 일부 설비의 복구만으로 전 품목·전체 고객 공급이 정상화됐다고 판단하지 않습니다.',
}
CHECKS = {
    '공급 중단·감소 보도': '중단 품목·사업장, 출하 감소 규모와 지속 기간을 확인하세요.',
    '사건 발생 · 공급 영향 미확인': '해당 사업장 생산 품목과 출하 영향에 대한 후속 공지를 확인하세요.',
    '제한 가능성·계획': '시행 여부·시행일·품목 범위와 예외 조항을 확인하세요.',
    '비용·관세': '적용 국가·품목·세율·시행일과 계약상 비용 부담 주체를 확인하세요.',
    '복구 보도': '부분·전체 복구 여부와 품목별 정상 출하 재개 시점을 확인하세요.',
}


def article_briefing(review):
    fields = review.get('fields', {})
    value = lambda key: fields.get(key, {}).get('value')
    kind = review['claim_type']
    routes = review.get('routes', [])
    linked = bool(review.get('target_id') and review.get('excerpt'))
    status = value('supply_status') or '공급 영향 미확인 · 구조화 항목 미지정'
    context = [review.get('target_name') or '등록 대상 미연결', kind, review['scope']]
    interpretation = INTERPRETATIONS.get(kind, '사건 분류가 미완료입니다. 원문 근거와 사건 대상을 먼저 검토하세요.')
    preview = review.get('extraction', {}).get('method') == 'mock_conversation_preview'
    mock = preview or review.get('extraction', {}).get('method') == 'mock_assisted_human_review'
    authored = review.get('mock_commentary')
    if mock and authored and authored.get('quote') in review['article']['body']:
        interpretation = authored['text']
    if not linked:
        interpretation = '등록 대상과의 연결을 보류했습니다. 관련 경로가 없다는 이유로 영향이 없다고 판단하지 않습니다. ' + interpretation
    if routes and all(not row['scoring_included'] for row in routes):
        interpretation += ' 현재 연결된 경로는 모두 소재 점수 제외 관계입니다. 관계 근거를 별도로 검토하세요.'
    checks = [CHECKS.get(kind, '사건 종류와 영향 범위를 원문에서 확인하세요.'),
              '고객별 계약·구매 비중·재고와 대체품 인증 여부는 별도 확인이 필요합니다.']
    if not review['article'].get('url'):
        checks.insert(0, '기사 출처 URL이 없어 원문 출처 확인이 필요합니다.')
    caution = None
    if kind in ('사건 발생 · 공급 영향 미확인', '제한 가능성·계획', '미분류 · 검토 필요') and value('supply_status') == '공급 중단·감소 명시':
        caution = '사건 분류와 공급 중단 표기가 함께 저장돼 있습니다. 서로 같은 사건·범위를 가리키는지 원문을 다시 확인하세요.'
    return {'headline': review['article']['headline'], 'context': ' · '.join(context),
            'status': status, 'event_date': value('event_date') or '미확인',
            'facility': value('facility') or '미확인', 'product': value('product') or '미확인',
            'interpretation': interpretation, 'route_count': len(routes),
            'route_note': f'관련 등록 경로 {len(routes)}개 · 실제 고객 영향 미확인',
            'checks': checks, 'caution': caution,
            'method': ('대화용 모의 초안 · 미검토 · API 미사용' if preview else
                       '모의 LLM 응답 · Codex 작성 · 실제 API 미사용' if mock and authored else
                       '모의 초안 수정 후 규칙 해설 · API 미사용' if mock else '사용자 검토 기반 규칙 해설 · API 미사용'),
            'score_note': '기사 검토는 시나리오·점수를 자동 변경하지 않습니다.'}


def briefing_markdown(review):
    note = article_briefing(review)
    lines = ['# '+note['headline'], '', note['method'], '',
             '## 이슈 요약', '', note['context'], '', '## 현재 상태 · 기사 기준', '',
             note['status'], f"사건일: {note['event_date']} · 시설: {note['facility']} · 제품: {note['product']}", '',
             '## 해설', '', note['interpretation'], '', note['route_note'], '', note['score_note'], '',
             '## 검토한 원문 근거', '', review.get('excerpt') or '미지정', '',
             '출처: '+(review['article'].get('url') or '미등록'), '', '## 추가 확인', '']
    lines.extend('- '+item for item in note['checks'])
    exposure=process_exposure(review)
    lines.extend(['', '## '+exposure['title'], ''])
    for row in exposure['rows']:
        lines.extend(['- '+row['path']+' — '+row['effect'], '  관계 근거: '+row['basis']])
    if not exposure['rows']:
        lines.append('직접 연결 공정 미등록 · 영향 없음으로 해석하지 않음')
    lines.extend(['',exposure['limit']])
    if note['caution']:
        lines.extend(['', note['caution']])
    lines.extend(['', '독립 사실 검증·실시간 상태 확인·생산 피해 예측을 수행하지 않았습니다.', ''])
    return '\n'.join(lines)
