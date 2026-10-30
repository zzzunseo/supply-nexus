"""Authored simulated LLM responses; no inference and no network requests."""
import json
from pathlib import Path
from .article_fields import FIELD_LABELS
from .article_review import article_draft
from .article_llm import validate_suggestion

NOTES = {
    'direct_supply': ('소재 출하 중단', '포토레지스트 출하 중단이 기사에 명시돼 있습니다. 고객별 재고와 구매 비중이 없어 고객 생산 감소 규모는 판단할 수 없습니다.'),
    'factory_unknown': ('화재 · 출하 영향 미확인', '공장 화재는 보도됐지만 출하 영향은 확인되지 않았습니다. JSR 전체 공급 중단으로 확대하지 않고 해당 시설·생산 품목의 후속 공지를 먼저 확인합니다.'),
    'tariff': ('관세 · 생산 차질과 구분', '25%는 기사에 등장하는 관세율입니다. 공급 중단 발표가 없으므로 이를 공급 25% 감소로 바꾸지 않습니다. 적용 품목과 비용 부담 조건을 확인합니다.'),
    'logistics_delay': ('물류 지연 · 전면 차단 아님', '말라카 해협 통항과 소재 출하의 지연이 함께 언급됐습니다. 통항 전면 차단이나 모든 고객의 생산 중단은 명시되지 않았습니다. 지도는 등록된 관련 경로를 확인하는 용도입니다.'),
    'planned_regulation': ('수출 제한 검토 · 미시행', '수출 제한은 검토 단계이고 아직 시행되지 않았습니다. 즉시 공급 중단으로 계산하지 않고 시행 여부와 대상 품목을 확인해야 합니다.'),
    'enacted_restriction': ('규제 시행 · 특정 제품 출하 중단', '규제 시행에 따른 특정 제품의 출하 중단이 명시됐습니다. 다른 제품이나 기업 전체로 범위를 넓히지 않습니다. 고객 계약·재고가 없으므로 고객 피해는 미확인입니다.'),
    'partial_recovery': ('일부 설비 재가동', '일부 설비 재가동과 전체 정상화 시점 미정을 구분해야 합니다. 정상 출하가 재개됐다는 확인이 없으므로 전체 공급 복구로 처리하지 않습니다.'),
    'equipment_only': ('장비 인도 지연', 'ASML 장비 인도 지연은 기존 설비의 가동 중단을 의미하지 않습니다. 소재 충족도와 구분하고 장비 도입 일정 및 고객 영향에 대한 추가 확인 항목으로 다룹니다.'),
    'comparison_only': ('비교 기업 오인 방지', 'JSR은 비교 대상으로만 언급됐고 화재 업체는 등록외업체입니다. JSR을 사건 대상으로 연결하지 않고 경로 연결을 보류합니다.'),
    'unknown_company': ('미등록 기업 · 연결 보류', '소재 공급 차질은 언급됐지만 사건 업체가 등록돼 있지 않습니다. 유사한 다른 기업에 임의 연결하지 않습니다. 경로가 없다는 것은 영향이 없다는 뜻이 아닙니다.'),
    'relative_date': ('상대 날짜 · 추정 보류', '사건일은 어제로만 표현돼 있습니다. 기준 발행일이 없으므로 연·월·일을 임의로 채우지 않습니다. 출하 영향도 미확인으로 유지합니다.'),
    'embedded_instruction': ('기사 내 지시문 무시', '기사 내 명령문은 분석 지시로 취급하지 않습니다. 실제 보도 문맥은 화재 원인 조사와 출하 영향 미확인이며, 기업 전체 100% 중단으로 변환하지 않습니다.'),
}


def cases():
    return json.loads(Path(__file__).with_name('article_mock_cases.json').read_text(encoding='utf-8'))


def load_mock(network, identifier):
    case = next((item for item in cases() if item['id'] == identifier), None)
    if case is None:
        raise ValueError('등록된 모의 사례를 선택하세요.')
    title, commentary = NOTES[identifier]
    draft = article_draft(network, '가상 기사 · '+title, case['body'])
    draft['is_fictional'] = True
    fields = {key: {'value': None, 'quote': None} for key in FIELD_LABELS}
    if case['supply_status']:
        fields['supply_status'] = {'value': case['supply_status'], 'quote': case['body']}
    proposal = validate_suggestion(network, draft, dict(target=case['target'], quote=case['body'],
        claim_type=case['claim_type'], scope=case['scope'], fields=fields))
    return draft, {'draft_id': draft['id'], 'provider': 'mock', 'case_id': identifier,
                   'model': '모의 응답 · Codex 작성', 'value': proposal,
                   'commentary': {'text': commentary, 'quote': case['body']}}


def attach_mock_commentary(review, saved):
    """Authored commentary is valid only for the exact original reviewed values."""
    if not saved or saved.get('provider') != 'mock' or saved['draft_id'] != review['article']['id']:
        return
    current = dict(target=review['target_id'], quote=review['excerpt'] or '', claim_type=review['claim_type'],
                   scope=review['scope'], fields={key:{'value':field['value'],'quote':field['quote']}
                                                for key,field in review['fields'].items()})
    if current == saved['value']:
        review['mock_commentary'] = dict(saved['commentary'])
    else:
        review['mock_commentary_omitted'] = '검토 내용을 수정해 원래 모의 해설을 적용하지 않았습니다.'
