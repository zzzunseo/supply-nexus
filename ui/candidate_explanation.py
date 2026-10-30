"""Explain documented product overlap without asserting interchangeability."""


def candidate_from_pick(data, entries, origin, event):
    if not isinstance(event, dict) or event.get('context') != data['context']:
        return None
    marker = event.get('id')
    if event.get('kind') == 'route':
        route = next((r for r in data['routes'] if r.get('id') == marker), None)
        marker = route['start'] if route else None
    return next((e['name'] for e in entries if e['map_id'] == marker and e['name'] != origin), None)


def explain_candidate(group_id, group, origin, entry, product_class=None):
    if group_id in ('polished-wafer', 'epi-wafer'):
        technical = '직경·결정 방향·도핑/저항률·결함 기준을 대조하고 샘플 웨이퍼를 평가합니다.'
        if group_id == 'epi-wafer':
            technical += ' 에피층 두께·균일도·저항률도 검증합니다.'
    elif group_id == 'photoresist':
        technical = '노광 방식(ArF/KrF/i-line/EUV)과 장비·레지스트 등급을 맞추고 감도·해상도·결함·현상 조건을 평가합니다.'
    elif group_id in ('hf', 'bhf'):
        technical = '농도·혼합비·금속 불순물·입자 기준과 대상 막의 식각률·선택비를 확인합니다.'
    elif group_id in ('nf3', 'etch-gas', 'sf6', 'c4f8', 'silane'):
        technical = '가스 조성·순도·불순물, 용기·밸브와 가스 공급 설비의 호환성, 공정 레시피를 검증합니다.'
    elif (group_id.startswith('cmp-') and group_id != 'cmp-tool') or group_id == 'ceria-abrasive':
        technical = '대상 막·연마 입자·첨가제 조합과 제거율·선택비·스크래치·세정 조건을 평가합니다.'
    else:
        technical = group['condition']
    return dict(
        title=entry['name']+' · 대체 후보 해설',
        supply=origin+'의 '+group['name']+' 공급을 대신할 수 있는지 검토하는 후보입니다.',
        products=entry['products'],
        reason='등록된 공식 제품 자료에서 '+entry['name']+'의 '+group['name']+' 관련 제품·서비스가 확인되어 동일 품목군 후보로 연결했습니다.'
            + (' 현재 노광 필터: '+product_class+'.' if product_class and product_class != '전체 제품군' else ''),
        conditions=[technical,
            '샘플·시험 공정 평가 후 고객의 품질·신뢰성·수율 기준과 변경 승인을 확인합니다.',
            '필요 물량·추가 공급 여력·납기·견적·운송 및 규제 요건을 공급사와 확인합니다.'],
        limit='품목군 근거만 확인된 상태입니다. 동일 등급 호환, 고객 승인, 실제 거래 및 공급 여력은 미확인입니다.',
        sources=entry['sources'])
