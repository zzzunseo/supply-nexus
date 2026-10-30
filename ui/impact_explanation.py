"""Inspectable qualitative explanations; no invented lead times or freight quotes."""
from .demo_scenarios import connections

USES={
    'polished-wafer':('기판 투입','웨이퍼 기판 입고가 부족하면 새 투입 로트의 시작 일정을 검토합니다. 이미 공정 중인 웨이퍼까지 즉시 중단되는 것은 아닙니다.'),
    'epi-wafer':('에피 기판 투입','선택 에피 웨이퍼 규격을 사용하는 로트의 기판 투입 일정을 검토합니다. 일반 PW로 즉시 바꿀 수 있다고 보지 않습니다.'),
    'photoresist':('감광막 도포·노광·현상','레지스트를 사용하는 포토 단계의 투입을 우선 검토합니다. 노광 방식·타입·막두께가 맞아야 하며, 식각 등 후속 일정의 지연은 해당 로트 진행 상황에 따라 달라집니다.'),
    'developer':('포토 현상','현상액이 필요한 포토 단계의 투입을 검토합니다. 농도·금속 오염·레지스트 조합과 고객 승인 조건을 대조해야 합니다.'),
    'oxygen':('등록 산화·공정가스 투입','등록된 산소 사용 공정의 가스 공급을 검토합니다. 현장 저장·배관 공급 방식과 재고에 따라 실제 제약이 달라집니다.'),
    'hydrogen':('등록 공정가스 투입','등록된 수소 사용 공정의 공급을 검토합니다. 고순도 규격과 현장 공급 방식이 대응 조건입니다.'),
    'etch-gas':('식각 가스 투입','등록된 식각 단계의 가스 투입을 검토합니다. 다른 가스나 공급사로 바꾸려면 레시피·순도·취급 조건을 확인해야 합니다.'),
    'film-precursor':('박막 형성 재료 투입','등록된 증착 단계의 전구체 공급을 검토합니다. 막 종류·공정 조건·용기와 공급 장치 호환을 확인해야 합니다.'),
    'metal-precursor':('금속막 형성 재료 투입','등록된 금속막 형성 단계의 재료 투입을 검토합니다. 다른 전구체를 동일 레시피에 바로 사용할 수 있다고 보지 않습니다.'),
    'lithography':('노광 장비 도입·유지보수','장비 출하 차질은 신규 도입·증설·교체 일정의 문제로 먼저 봅니다. 기존 설치 장비의 즉시 정지나 생산 감소로 변환하지 않습니다.'),
    'etch-tool':('식각 장비 도입·유지보수','신규 식각 장비 반입·증설·교체 일정을 우선 검토합니다. 설치 장비 운전 영향은 부품·서비스 차질 여부가 추가로 필요합니다.'),
    'deposition-tool':('증착 장비 도입·유지보수','증착 장비 도입·증설·교체 일정을 검토합니다. 기존 장비 운전은 부품·서비스 의존 조건을 별도로 확인합니다.'),
    'interconnect-tool':('금속배선 장비 도입','등록된 금속배선 공정의 장비 도입·교체 일정을 검토합니다. 납품 지연을 기존 공정의 즉시 중단으로 해석하지 않습니다.'),
    'wafer-tester':('웨이퍼 전기 검사','검사 장비의 신규 반입·교체 일정과 기존 검사 여력을 대조합니다. 장비 출하 중단만으로 검사 라인 정지를 확정하지 않습니다.'),
    'processed-wafer':('후공정용 웨이퍼 입고','등록된 수요기업의 후속 검사·조립 등 연결 단계에 필요한 웨이퍼 입고를 검토합니다. 실제 고객별 공정·로트·재고를 확인해야 합니다.'),
}


def build_explanation(network,case,profile):
    target=case.get('material_target',case['target'])
    rows=case.get('connections') or [r for r in connections(network) if r['target']==target and r['recipient'] in case['recipients']]
    tariff=case.get('event')=='관세 부과';logistics=case.get('kind')=='logistics'
    impacts=[]
    for row in rows:
        product=network['nodes'][row['target']]
        use,reason=USES.get(row['item'],('등록 소재 투입','등록된 소재 용도와 관련 공정의 투입 일정을 검토합니다.'))
        for process in row['processes']:
            impacts.append(dict(company=network['entities'][row['recipient']]['name'],company_id=row['recipient'],supplier_id=row['supplier'],target=row['target'],material=row['material'],
                process=process,use=use,category=product.get('input_category','material'),
                reason=('관세는 해당 품목의 구매·도착 비용 검토입니다. 공정 중단이나 생산 감소를 산정하지 않습니다.' if tariff else
                        '등록된 경유 항만의 차질로 이 소재의 반입 일정이 달라질 수 있습니다. '+reason if logistics else reason),
                source=product.get('source'),relationship_source=row['evidence'].get('relationship_source') or row['evidence'].get('source'),
                scope=row['evidence'].get('evidence_note') or '등록 관계·용도의 시나리오 연결. 품목별 계약·비중은 별도 확인.'))
    processes=list(dict.fromkeys(row['process'] for row in impacts))
    companies=list(dict.fromkeys(row['company'] for row in impacts))
    candidates=[]
    if not tariff:
        if profile.get('candidates'):
            for entry in profile['candidates']:
                candidates.append(dict(name=entry.get('name') or network['entities'].get(entry['company_id'],{}).get('name',entry['company_id']),material=entry['material'],
                    recipient=network['entities'][entry['recipient']]['name'],source=entry['source'],condition='품목 근거 → 규격·고객 승인·추가 공급량 확인'))
        elif profile['kind']!='logistics' and profile.get('candidate_eligible',True) and profile.get('candidate_id'):
            candidates.append(dict(name=profile['name'],material=profile['material'],recipient=' · '.join(companies),source=profile.get('source'),condition='제품군 일치 → 고객별 규격·승인·출하 확인'))
        elif logistics:
            # Procurement is a separate strategy; it does not establish a port bypass.
            from .response_review import review_profile
            from .logistics_demo import demo_cases
            material_case=next((c for c in demo_cases()[:2] if c['target']==target),None)
            if material_case:
                p=review_profile(network,material_case)
                if p.get('candidate_eligible',True):candidates.append(dict(name=p['name'],material=p['material'],recipient=' · '.join(companies),source=p.get('source'),condition='조달 후보. 고객 승인과 봉쇄 항만을 피하는 운송 경로는 별도 확인'))
    unique=[]
    for candidate in candidates:
        if candidate not in unique:unique.append(candidate)
    ports=[]
    # Registered model routing only; never infer real shipments from company country.
    relevant={r['target'] for r in rows}
    for edge in network['visual_edges']:
        if edge['from'] not in relevant or edge['to'] not in case['recipients']:continue
        for port in edge.get('logistics_via',[]):
            if logistics and port!=case['target']:continue
            setting=network['port_detours'].get(port,{})
            for alternate in setting.get('via',[]):
                if alternate not in network['logistics']:continue
                entry=dict(original=network['logistics'][port]['name'],alternate=network['logistics'][alternate]['name'],
                    original_id=port,alternate_id=alternate,source=network['logistics'][alternate]['source'],
                    purpose='반입 경로 변경 후보' if logistics else '물류 참고 · 생산·출하 중단 자체는 해결하지 못함',
                    model_days=setting.get('extra_days'),model_cost_rate=setting.get('cost_rate'))
                if entry not in ports:ports.append(entry)
    equipment=bool(impacts) and all(i['category']=='equipment' for i in impacts)
    if tariff:
        time_short='운송 일정은 별도';cost_short='품목·원산지·과세기준'
        time_rows=[('반입 일정','관세율만으로 지연일을 계산하지 않음','운항·통관 일정이 실제로 달라지는지 확인')]
        cost_rows=[('관세','선택 관세율은 가정','거래 국가·원산지·품목분류·과세가격 확인'),('조달 전환','세금 감소 확정 아님','대체 공급자의 원산지·거래 조건도 별도 비교')]
    elif logistics:
        time_short='선적·통관·반입';cost_short='운임·하역·내륙운송'
        time_rows=[('선적·해상운송','기존/후보 항로의 출항→입항 일정 차이','선복 예약·환적·정박 대기 포함'),('항만·통관','입항→반출 가능 시점 차이','화물 서류·검사·보관 조건'),('내륙 반입','항만 반출→고객 수령 일정 차이','육상 배차·반입 시간대·화물 취급 조건')]
        cost_rows=[('해상운임','기존 견적과 후보 견적의 차액','같은 화물량·통화·견적일·포함 조건으로 비교'),('항만·보관','하역·보관·서류·대기 비용 차액','이미 견적에 포함된 항목을 중복 계산하지 않음'),('내륙운송·취급','항만→고객 육상운송과 포장·취급 비용 차액','항만 변경이 항상 더 멀거나 더 비싼 것은 아님')]
    else:
        time_short='반입·설치·검증' if equipment else '샘플·승인·납기';cost_short='장비·설치·검증' if equipment else '단가·검증·물류'
        time_rows=[('후보 확보','공급 가능 시점·견적 회신·샘플 일정','기존 승인 공급사와 신규 후보를 구분'),('적합성 검증','설치·인수·공정 검증 일정' if equipment else '샘플 평가·규격 대조·고객 승인 일정','이미 승인된 등급이면 필요한 절차 범위가 달라질 수 있음'),('출하·반입','발주→출하→고객 반입 가능 시점','검증과 생산이 병행되면 단순 합산하지 않음')]
        cost_rows=[('조달 단가','기존/대체 견적의 동일 수량 기준 차액','단가·최소주문량·계약 통화·인도 조건'),('전환 비용','장비 설치·시험·공정 재검증' if equipment else '샘플·품질 평가·레시피 검증·전환 작업','일회성 비용과 반복 구매비 분리'),('물류·취급','운임·보관·포장·고객 반입 비용 차액','화물별 SDS·취급 조건과 운송수단 확인')]
    return dict(title=case['name'],material=profile['material'],processes=processes,companies=companies,impacts=impacts,
        candidates=unique,ports=ports,tariff=tariff,logistics=logistics,equipment=equipment,
        time_short=time_short,cost_short=cost_short,time_rows=time_rows,cost_rows=cost_rows,
        time_value=None,cost_value=None,
        first_action='거래 품목·원산지·과세 기준 확인' if tariff else '선적 상태·기룽 취급·운항 확인' if logistics else '설치 장비·부품·도입 일정 구분' if equipment else '고객 승인 등급·가용재고 확인',
        boundary='후속 공정은 해당 로트의 투입 지연이 이어질 때만 영향 가능성을 검토합니다. 모든 공정에 같은 피해율을 전파하지 않습니다.')


def explanation_markdown(case,analysis,profile):
    lines=['# 공급망 영향·대응 검토 기록','',f"사건: {case['name']}",f"기간: {case.get('days','미지정')}일 / 비율: {case.get('percent','미지정')}% (선택 시나리오)",
        '','## 영향 공정과 해석','',analysis['boundary']]
    for row in analysis['impacts']:
        lines.extend(['',f"### {row['company']} / {row['process']} / {row['material']}",row['use'],row['reason'],'관계 근거 범위: '+row['scope']])
        if row['source']:lines.append(f"[제품 용도 자료]({row['source']})")
        if row['relationship_source']:lines.append(f"[공급 관계 자료]({row['relationship_source']})")
    lines.extend(['','## 대체 조달 후보',''])
    if not analysis['candidates']:lines.append('현재 선택 범위에서 표시할 제품 근거가 있는 후보가 없습니다. 미생산 또는 대체 불가능 판정은 아닙니다.')
    for row in analysis['candidates']:
        lines.extend([f"- {row['name']} / {row['material']} / {row['recipient']}",'  '+row['condition'],f"  [제품 근거]({row['source']})"])
    lines.extend(['','## 항만·경유 변경 후보',''])
    if not analysis['ports']:lines.append('현재 연결에서 등록된 경유 변경 후보가 없습니다.')
    for row in analysis['ports']:
        lines.extend([f"- {row['original']} → {row['alternate']}: {row['purpose']}",f"  [위치·항만 자료]({row['source']})",'  화물 취급·선사 운항·통관·내륙 운송·고객 반입을 확인해야 합니다.'])
    for title,rows in [('소요 시간 비교',analysis['time_rows']),('추가 비용 비교',analysis['cost_rows'])]:
        lines.extend(['','## '+title,''])
        for name,definition,check in rows:lines.append(f'- {name}: {definition}. 확인: {check}.')
    lines.extend(['','실제 일수·금액: 미산정. 기존/후보의 운항 일정·동일 조건 견적이 필요합니다.',
        '전체 시간 차이는 동일한 시작·종료 시점(예: 발주 확정→고객 반입 완료)으로 비교합니다. 병행 단계는 중복 합산하지 않습니다.',
        '추가 비용은 동일 화물량·통화·세금/인도 조건의 후보 총비용 − 기존 총비용입니다. 차액은 감소할 수도 있으며, 자료가 없다고 0으로 표시하지 않습니다.',
        '','## 후보 적합성·근거 경계','',profile['summary']])
    for label,status,detail in profile['rows']:lines.append(f'- {label} / {status}: {detail}')
    for source in profile.get('sources',{}).values():
        lines.append(f"- [{source['title']}]({source['url']}): {source['scope']} / 한계: {source['limit']}")
    lines.extend(['',case['evidence'],case['limits'],'','## 상세 모드의 시연 입력값 (실측·견적 아님)',''])
    for port in analysis['ports']:
        if port['model_days'] is not None and port['model_cost_rate'] is not None:
            lines.append(f"- {port['original']} → {port['alternate']}: 추가 {port['model_days']}일, 운임 가산율 {port['model_cost_rate']*100:g}%. 기존 모델 입력 가정이며 실제 운송시간·운임 견적 또는 제품가격 인상률이 아닙니다. 기본 화면의 실제 시간·비용으로 사용하지 않습니다.")
    return '\n'.join(lines)+'\n'


def annotate_processes(network,data,case):
    """Map badges follow only registered recipient/product process edges."""
    from copy import deepcopy
    data=deepcopy(data)
    target=case.get('material_target',case['target'])
    rows=case.get('connections') or [r for r in connections(network) if r['target']==target and r['recipient'] in case['recipients']]
    if data.get('logistics') and data.get('exposure') and not data.get('response'):
        rows=data['exposure']['rows']
    for marker in data['markers']:
        if marker['role']!='recipient':continue
        processes=list(dict.fromkeys(p for row in rows if row['recipient']==marker['id'] for p in row['processes']))
        marker['processes']=processes
        marker['process_label']=' · '.join(processes[:2])+(' 외' if len(processes)>2 else '')
    for route in data['routes']:
        processes=list(dict.fromkeys(p for row in rows if row['recipient']==route['end'] and (route['kind']!='primary' or row['supplier']==route['start'] or data.get('logistics')) for p in row['processes']))
        route['process_label']=' · '.join(processes)
    return data
