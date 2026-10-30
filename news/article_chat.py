"""Bounded offline dialogue using authored examples; never calls a model."""
from copy import deepcopy
import re

from .article_mock import load_mock, attach_mock_commentary
from .article_review import article_draft, review_article
from .article_briefing import article_briefing
from .article_exposure import exposure_summary
from simulation.schema import validate_parsed


def preview_review(network, case_id):
    draft, saved = load_mock(network, case_id)
    value = saved['value']
    review = review_article(network, draft, value['target'], value['quote'], value['claim_type'],
                            value['scope'], fields=value['fields'])
    attach_mock_commentary(review, saved)
    review['status'] = '대화용 모의 초안 · 미검토'
    review['extraction'] = {'method':'mock_conversation_preview', 'model':saved['model'],
                            'case_id':case_id, 'independently_verified':False}
    return review, saved


def respond(network, context, text):
    """Return a new context and reply. Simulation state is outside this module."""
    state = deepcopy(context or {})
    state.pop('action',None)
    q = text.strip()
    if not q or len(q) > 600:
        raise ValueError('질문은 1~600자로 입력하세요.')
    lower = q.casefold()
    review = state.get('review')
    if any(word in lower for word in ('최신','검색','뉴스 찾아','기사 찾아','실시간')):
        return state, '현재는 모의 대화입니다. 실제 뉴스 검색은 연결되지 않았습니다. 기사를 붙여넣어 검토하거나 “JSR 화재 예시”로 가상 사례를 시작하세요.'

    scenario = any(word in lower for word in ('만약','가정','시뮬','계산'))
    pending = state.get('pending')
    numeric_followup = bool(pending and re.fullmatch(r'[\s\d.%일동안감소율공급중단은는로가정해줘,\-]+',q))
    if scenario or numeric_followup:
        state.pop('proposal',None)
        if not review or not review.get('target_id'):
            return state, '계산 대상을 먼저 정해야 합니다. 기사나 모의 사례를 선택하세요. 감소율·기간을 임의로 채우지 않습니다.'
        if review['claim_type'] == '비용·관세' or '관세' in q:
            state.pop('pending',None)
            return state, '관세율을 공급 감소율로 계산하지 않습니다. 비용은 해설로 구분합니다. 소재 공급 차질 가정은 해당 소재 사건을 먼저 선택하세요.'
        if state.get('base_review',review)['routes'] != review['routes']:
            return state, '현재는 고객별 경로를 좁혀 보고 있습니다. 이 필터를 고객 생산 감소로 계산하지 않습니다. “전체 경로”로 돌아온 뒤 공급사에 대한 가정을 지정하세요.'
        if not any(row['scoring_included'] for row in review['routes']):
            return state, '현재 대상의 경로는 소재 점수에 연결되지 않았습니다. 장비 지연·미등록 관계를 고객 생산 중단으로 계산하지 않습니다.'
        p = deepcopy(pending or {'article_id':review['article']['id'],'target':review['target_id'],
                                 'name':review['target_name'],'rate':None,'days':None})
        if p['article_id'] != review['article']['id'] or p['target'] != review['target_id']:
            return state, '검토 대상이 바뀌었습니다. 새 대상의 가정을 다시 입력하세요.'
        if re.search(r'\d+\.\d+\s*일|-\s+\d',q):
            return state, '기간은 정수 일수로, 감소율은 음수가 아닌 값으로 지정하세요.'
        rates = re.findall(r'(-?\d+(?:\.\d+)?)\s*%',q)
        days = re.findall(r'(-?\d+)\s*일',q)
        if len(set(rates)) > 1 or len(set(days)) > 1:
            return state, '감소율과 기간을 각각 하나만 지정하세요. 여러 가정을 한 번에 혼합하지 않습니다.'
        if rates:
            rate = float(rates[0])
            if not 0 <= rate <= 100:
                return state, '공급 감소율은 0~100%로 지정하세요.'
            p['rate'] = rate/100
        if days:
            duration = int(days[0])
            if not 1 <= duration <= 365:
                return state, '기간은 1~365일로 지정하세요.'
            p['days'] = duration
        state['pending'] = p
        missing = []
        if p['rate'] is None: missing.append('공급 감소율(예: 40%)')
        if p['days'] is None: missing.append('기간(예: 20일)')
        if missing:
            return state, '가정 대상은 '+p['name']+'입니다. '+', '.join(missing)+'을 알려주세요. 기사에서 확인된 수치로 취급하지 않습니다.'
        parsed = dict(action='apply',kind='supply',targets=[p['target']],rate=p['rate'],days=p['days'],
                      text=f"대화 가정: {p['name']} 공급 {p['rate']*100:g}% 감소 {p['days']}일",
                      note='대화에서 지정한 등록 대상 전체에 대한 가정입니다. 기사 속 시설·고객 피해 확인이 아닙니다.')
        validate_parsed(parsed,network['nodes'])
        state['proposal'] = {'article_id':p['article_id'],'parsed':parsed}
        return state, f"가정 준비: {p['name']} 공급 {p['rate']*100:g}% 감소, {p['days']}일. 등록 대상 전체에 적용하는 계산 가정입니다. 아직 점수는 바꾸지 않았습니다. 아래 ‘검토한 가정 적용’을 누르면 반영합니다."

    # A new topic clears pending assumptions; explicitly named unsupported companies do not become JSR.
    topic = any(word in lower for word in ('화재','관세','재가동','복구','장비','규제','물류','출하 중단'))
    if topic:
        state.pop('proposal',None)
        state.pop('pending',None)
        mentions = article_draft(network,'',q)['mentions']
        companies = {candidate['id'] for hit in mentions for candidate in hit['candidates']
                     if network['nodes'][candidate['id']]['kind']=='company'}
        if companies - {'jsr','asml'}:
            return state, '그 기업에 대한 모의 기사 응답은 아직 준비되지 않았습니다. 다른 기업의 사례로 대체하지 않습니다. 실제 기사 본문을 붙여넣어 직접 검토할 수 있습니다.'
        if 'asml' in companies and '장비' not in lower and not any(w in lower for w in ('인도','지연')):
            return state, 'ASML 모의 응답은 장비 인도 지연 사례만 준비돼 있습니다. 다른 사건으로 대체하지 않습니다.'
        case = ('equipment_only' if 'asml' in lower or '장비' in lower else
                'tariff' if '관세' in lower else 'partial_recovery' if any(w in lower for w in ('재가동','복구')) else
                'planned_regulation' if '규제' in lower else 'logistics_delay' if any(w in lower for w in ('말라카','물류')) else
                'direct_supply' if '출하 중단' in lower else 'factory_unknown' if '화재' in lower else None)
        if case:
            review,saved = preview_review(network,case)
            state = {'review':review,'base_review':deepcopy(review),'suggestion':saved}
            return state, '가상 기사·모의 응답입니다. '+exposure_summary(review)+' 실제 뉴스 검색·모델 호출 결과가 아닙니다.'
    if not review:
        return state, '“JSR 화재 예시”, “관세 예시”, “ASML 장비 지연 예시”로 시작하거나 기사 본문을 붙여넣으세요. 현재 대화는 지원 질문을 규칙으로 연결하는 모의 테스트입니다.'
    if any(word in lower for word in ('지도 보여','지도보기','지도로 보여','경로 지도')):
        if not review['routes']:
            return state, '현재 조건에서 표시할 등록 경로가 없습니다. 경로나 위치를 만들어내지 않습니다.'
        state['action']='open_map'
        return state, '현재 기사·필터의 등록 경로 지도를 엽니다. 사고 장소나 실제 고객 피해 지도와는 구분합니다.'
    if any(word in lower for word in ('삼성','samsung','tsmc','전체 경로','전체경로')):
        state.pop('proposal',None)
        state.pop('pending',None)
        base=deepcopy(state.get('base_review') or review)
        if '삼성' in lower or 'samsung' in lower:
            base['routes']=[row for row in base['routes'] if 'samsung' in row['recipient'].casefold()]
        elif 'tsmc' in lower:
            base['routes']=[row for row in base['routes'] if 'tsmc' in row['recipient'].casefold()]
        state['review']=base
        return state, f"선택 조건의 등록 경로 {len(base['routes'])}개를 오른쪽에 표시했습니다. "+exposure_summary(base)
    if any(word in lower for word in ('공정','어디','타격','취약','노출','영향받')):
        return state, exposure_summary(review)
    if any(word in lower for word in ('확인','실제','근거','출처','영향','요약','설명')):
        return state, '현재 기사 기준 상태: '+article_briefing(review)['status']+'. 근거: “'+(review['excerpt'] or '미지정')+'” 독립 사실 검증은 수행하지 않았습니다. 등록 관계만으로 고객 생산 피해를 확정할 수 없습니다.'
    return state, '현재 이슈를 유지했습니다. “공급 영향은 확인됐어?”, “삼성과 연결된 경로만”, “전체 경로”, “만약 공급이 40% 감소하면 20일”처럼 질문해 주세요. 지원하지 않는 질문에 답을 만들어내지 않습니다.'
