"""Direct process exposure from registered relationships, not production forecasts."""


def process_exposure(review):
    kind = review['claim_type']
    rows=[]
    for route in review.get('routes',[]):
        basis=route['basis']
        category=('supply' if basis.startswith('기업 간 공급관계 근거') else
                  'reference' if basis.startswith('참고 관계') else 'assumption')
        material_input=bool(route['scoring_included'])
        if category=='reference':
            effect='참고 관계만 등록 · 직접 공급 노출 판단 보류'
        elif category=='assumption':
            effect='소재 용도에 따른 연결 가정 · 실제 납품 여부부터 확인'
        elif not material_input:
            effect='장비·참고 품목 도입 일정 확인 · 기존 생산 타격 미판정'
        elif kind=='비용·관세':
            effect='해당 소재 조달 비용 검토 · 생산·투입 부족으로 환산하지 않음'
        elif kind=='복구 보도':
            effect='해당 공정 투입재의 정상 출하 회복 여부 확인'
        elif kind=='제한 가능성·계획':
            effect='규제 시행·품목 포함 시 해당 공정 투입재 공급 제약 확인'
        elif kind=='공급 중단·감소 보도':
            effect='해당 소재의 공급 부족 시 직접 사용 공정의 투입 제약 가능성 확인'
        else:
            effect='출하 차질이 발생할 경우 해당 공정의 소재 투입 제약 확인'
        rows.append({'id':route['id'],'supplier':route['supplier'],'material':route['material'],
                     'recipient':route['recipient'],'processes':list(route['processes']),
                     'category':category,'material_input':material_input,'basis':basis,
                     'source':route.get('source'),'effect':effect,
                     'path':route['supplier']+' → '+route['material']+' → '+route['recipient']+' → '+
                            (' · '.join(route['processes']) or '직접 공정 미등록')})
    direct=[r for r in rows if r['category']=='supply' and r['material_input']]
    equipment=[r for r in rows if r['category']=='supply' and not r['material_input']]
    other=[r for r in rows if r['category']!='supply']
    title=('비용 영향 검토 공정' if kind=='비용·관세' else
           '공급 회복 확인 공정' if kind=='복구 보도' else '영향을 우선 확인할 기업·공정')
    return {'title':title,'direct':direct,'equipment':equipment,'other':other,'rows':rows,
            'limit':'직접 연결 범위입니다. 현행 품목 계약·실제 부족 여부·타격 크기와 시점은 미확인입니다. 공정 간 연쇄 피해는 예측하지 않습니다.'}


def exposure_summary(review, limit=3):
    data=process_exposure(review)
    primary=data['direct'] or data['equipment']
    if not primary:
        if data['other']:
            paths=' / '.join(row['path'] for row in data['other'][:limit])
            return paths+' — 참고·가정 관계여서 직접 공급 노출은 판단을 보류합니다.'
        return '등록된 직접 연결 공정이 없어 기업·공정별 노출을 특정할 수 없습니다. 영향 없음이라는 뜻은 아닙니다.'
    text=' / '.join(row['path']+' ('+row['effect']+')' for row in primary[:limit])
    if len(primary)>limit:
        text+=f' 외 {len(primary)-limit}개 경로'
    if data['other']:
        text+=f". 참고·가정 경로 {len(data['other'])}개는 별도로 구분합니다."
    return text+'. '+data['limit']
