"""Curated official-source comparisons; product overlap is not qualification."""
import json
from pathlib import Path


def evidence_catalog():
    return json.loads((Path(__file__).resolve().parents[1]/'data/response_evidence.json').read_text(encoding='utf-8'))


def enrich_profile(network,case,profile,product_class=None):
    catalog=evidence_catalog()
    record=catalog['cases'].get(case['id'])
    if not record or record['candidate_id']!=profile['candidate_id']:return profile
    product=network['nodes'][case['target']]
    if product.get('item_id')!=record['item_id']:return profile
    selected=product_class or record['default_class']
    if case['id']=='wafer':selected='PW'
    common=[c for c in record['source_classes'] if c in record['candidate_classes']]
    eligible=selected=='전체 제품군' and bool(common) or selected in common
    selected_text=' · '.join(common) if selected=='전체 제품군' else selected
    if eligible:
        overlap=f'공통 {selected_text} 제품군 확인. 고객별 등급 호환은 별도입니다.'
        verdict='제품군 기준의 검토 후보입니다. 규격·승인 대조 후 증량 조건을 확인합니다.'
        summary=f"{selected_text} 제품군 근거로 {record['display_name']}을 검토합니다. {'TSMC 공급사 수준의 기존 관계 자료가 있지만 현재 PW 등급 승인은 별도입니다.' if case['id']=='wafer' else '노광 방식·레지스트 타입·막두께와 고객 승인 조건을 먼저 대조해야 합니다.'}"
    else:
        overlap=f'{selected_text}는 원공급 자료에 있으나, 대조한 후보 제품 목록에서 확인하지 못했습니다.' if selected in record['source_classes'] else f'{selected_text}의 제품 근거가 이번 비교 범위에 없습니다.'
        verdict='추가 공식 제품 근거를 확보할 때까지 후보 경로를 보류합니다. 미생산 판정은 아닙니다.'
        summary=f'{selected_text}에 대해서는 현재 자료로 동진 후보를 뒷받침하지 못해 점선 경로를 보류합니다. 다른 공식 제품·고객 적용 자료를 먼저 확보해야 합니다.'
    relationship='TSMC: 2025 SEH 공급사 자료 / 삼성: 2023 모회사 소재 관계. 현재 PW 계약 확정 아님.' if case['id']=='wafer' else 'JSR → TSMC: 2025 공급사 자료. 동진 → TSMC의 해당 PR 관계는 이번 자료에 없음.'
    technical='직경·저항률·결정 방향·결함 기준 및 고객별 승인 규격' if case['id']=='wafer' else '노광 방식·타입·막두께·현상 조건 및 고객별 승인 규격'
    rows=[('세부 제품 대조','겹침 확인' if eligible else '근거 부족',overlap),
          ('공급 관계 근거','관계 범위 확인' if case['id']=='wafer' else '원공급만 확인',relationship),
          ('이번 대응 판단','조건부 검토' if eligible else '후보 보류',verdict),
          ('전환 전 비교 항목','규격·승인 대조',technical),
          ('증량·출하 확인','기업 확인 필요','샘플·CoA·여유 능력·납기 견적·출하 공장과 운송 경로')]
    return dict(profile,name=record['display_name'],material=record['material'],rows=rows,summary=summary,
                evidence=record,sources={key:catalog['sources'][key] for key in record['source_ids']},
                reviewed_at=catalog['reviewed_at'],product_class=selected,candidate_eligible=bool(eligible),
                common_classes=common,level='기존 공급사 관계 자료' if case['id']=='wafer' else '동일 제품군 후보')
