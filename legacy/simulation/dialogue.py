"""Session-local requests; drafts are reviewed before they become scenarios."""
from copy import deepcopy
import re
import json
from .issues import offline_extract, assess_issue, scenario_from_assessment
from .engine import calculate
from .advice import build_advice
from .llm_provider import extract_issue, research_issue, configuration


def handle_request(request, data, model, state, current_options):
    state = deepcopy(state or {'messages': [], 'processed_ids': []})
    request_id = str(request.get('id', ''))[:100]
    if not request_id or request_id in state.get('processed_ids', []):
        return state
    state['processed_ids'] = (state.get('processed_ids', []) + [request_id])[-30:]
    state['last_request_id'] = request_id
    action = request.get('action')
    text = str(request.get('text', '')).strip()[:2000]
    try:
        if action == 'clear':
            state['messages'] = []
            state['analysis'] = None
            return state
        if action == 'research':
            query = text or state.get('last_query', '')
            if not query:
                raise ValueError('먼저 조사할 이슈를 입력하세요.')
            query += '\n사용자 입력에서 해석한 초안(검증 전): ' + json.dumps((state.get('analysis') or {}).get('draft'), ensure_ascii=False)
            state['messages'].append({'role':'assistant','text':'외부 자료 조사 메모 · 계산에 자동 반영되지 않습니다.',
                                      'research':research_issue(query)})
        elif action == 'analyze':
            if not text:
                raise ValueError('이슈를 입력하세요.')
            previous_analysis = state.get('analysis') or {}
            previous = previous_analysis.get('draft')
            if (previous_analysis.get('preview') and re.search(r'원인|대응|대안|추천|왜', text)
                    and not re.search(r'\d|%|관세|지진|공장', text)
                    and not any(offline_extract(text,data)[k] for k in ['companies','countries','items','regions','unresolved'])):
                advice = previous_analysis['preview']['advice']
                rows = [f"{c['item']} 가용 {c['available_pct']:g}% → {c['process']} {c['process_score']:g}점"
                        for c in advice['causes'][:3]]
                comparisons = [f"{m['label']}: {m['score']:g}점" for m in advice['mitigations']]
                state['messages'] += [{'role':'user','text':text}, {'role':'assistant','mode':'calculation',
                    'text':'현재 분석 초안 기준입니다.\n' + '\n'.join(rows + comparisons + [advice['summary']])}]
                state['messages'] = state['messages'][-12:]
                return state
            state['analysis'] = None  # A failed request cannot leave a stale apply button.
            state['last_query'] = text
            state['messages'].append({'role':'user','text':text})
            mode = request.get('mode', 'test')
            if mode not in ('test','openai'):
                raise ValueError('지원하지 않는 해석 모드입니다.')
            draft = extract_issue(text,data,previous) if mode=='openai' else offline_extract(text,data,previous)
            assessment = assess_issue(draft,data)
            assessment['mode'] = mode
            if assessment['can_apply']:
                scenario = scenario_from_assessment(assessment)
                options = {**current_options, 'severity':draft['loss_pct']/100, 'duration_days':draft['duration_days']}
                report = calculate(data, model, scenario, **options)
                assessment['preview'] = {'score':report['overall_score'], 'bottlenecks':report['bottlenecks'],
                    'advice':build_advice(data,model,scenario,options,report), 'options':options}
            state['analysis'] = assessment
            state['messages'].append({'role':'assistant','text':assessment['answer'], 'mode':mode})
        elif action == 'apply':
            if not state.get('analysis'):
                raise ValueError('적용할 분석이 없습니다.')
            assessment = assess_issue(state['analysis']['draft'],data)
            scenario = scenario_from_assessment(assessment)
            state['custom_scenario'] = scenario
            state['applied_selection'] = {**current_options, 'revision':request_id, 'scenario':scenario['name'],
                'severity':assessment['draft']['loss_pct']/100, 'duration_days':assessment['draft']['duration_days'],
                'process':'전체', 'level':'country', 'poster':False, 'tab':'globe'}
            state['messages'].append({'role':'assistant','text':f"{assessment['target_label']} 가정 시나리오를 지도에 적용했습니다. 왼쪽 조건을 바꾸면 원인·대응 비교도 갱신됩니다."})
        else:
            raise ValueError('지원하지 않는 대화 동작입니다.')
    except (ValueError, KeyError, TypeError) as error:
        state['messages'].append({'role':'assistant', 'text':str(error) if isinstance(error,ValueError) else '이슈 형식을 확인하지 못했습니다. 대상을 명확히 다시 입력하세요.', 'error':True})
    state['messages'] = state['messages'][-12:]
    return state


def public_state(state):
    state = state or {}
    return {k: state.get(k) for k in ['messages','analysis','last_request_id','applied_selection']} | configuration()
