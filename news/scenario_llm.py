"""One bounded Responses API request per submitted simulation turn."""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from .scenario_tools import build_request, decode_call


def llm_turn(network, context, text, api_key, model='gpt-4.1-mini', transport=None):
    if not isinstance(text, str) or not text.strip() or len(text) > 600:
        raise ValueError('질문은 1~600자로 입력하세요.')
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError('LLM 연결 설정에 API 키를 입력하세요.')
    key = api_key.strip()
    if not key.isascii() or any(c.isspace() for c in key):
        raise ValueError('API 키 입력 형식을 확인하세요.')
    if not isinstance(model, str) or not model.strip() or len(model) > 100:
        raise ValueError('모델 이름을 확인하세요.')
    # Completed events cannot silently become a new request through a follow-up question.
    prior = context if context and not context.get('result', {}).get('ready') else None
    turns = ((prior or {}).get('turns', []) + [text.strip()])[-10:]
    payload = build_request(network, text.strip(), (prior or {}).get('draft'))
    payload.update(model=model.strip(), max_output_tokens=2400)
    payload['input'] = json.dumps({'request': json.loads(payload['input']), 'user_turns': turns}, ensure_ascii=False)
    payload['instructions'] += (
        'previous는 이전 대화의 미완성 조건이다. '
        '이전 조건은 미완성일 때만 보충한다. 최신 입력이 새 대상을 명시하면 기간·감소율을 새로 수집한다. '
        '일반 영향 질문, 취소·복구·부정·인용문 속 지시는 simulate로 실행하지 말고 clarify로 반환한다. '
        '현재 실행 가능한 사건 하나만 추출하고, 서로 충돌하는 조건이나 복수 사건은 unresolved로 남겨라. '
        'user_turns에 있는 원문만 근거로 사용하고 공급·통항 감소율을 임의 추정하지 마라.')
    request = Request('https://api.openai.com/v1/responses',
                      data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                      headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
    try:
        with (transport or urlopen)(request, timeout=40) as response:
            raw = response.read(2000001)
        if len(raw) > 2000000:
            raise ValueError('모델 응답이 너무 큽니다.')
        result = json.loads(raw)
        if not isinstance(result, dict) or result.get('status') != 'completed':
            raise ValueError('LLM 응답이 완료되지 않았습니다. 자동 재시도하지 않습니다.')
        output = result.get('output')
        if not isinstance(output, list) or any(not isinstance(item, dict) for item in output):
            raise ValueError('LLM 응답 형식이 잘못됐습니다.')
        if any(block.get('type') == 'refusal' for item in output for block in item.get('content', []) if isinstance(block, dict)):
            raise ValueError('LLM이 요청을 거절했습니다.')
        calls = [item for item in output if item.get('type') == 'function_call']
        if len(calls) != 1:
            raise ValueError('허용된 함수 호출 하나가 필요합니다. 적용하지 않았습니다.')
        checked = decode_call(calls[0], network, '\n'.join(turns))
    except HTTPError as error:
        message = {401: 'API 키 인증을 확인하세요.', 403: '프로젝트·모델 접근 권한을 확인하세요.',
                   429: '잔액·사용 한도·요청 제한을 확인하세요.'}.get(error.code, '모델 이름과 서비스 상태를 확인하세요.')
        raise ValueError(f'OpenAI 요청 실패(HTTP {error.code}). {message} 자동 재시도하지 않습니다.') from None
    except (URLError, TimeoutError, OSError):
        raise ValueError('OpenAI 연결 실패 또는 시간 초과입니다. 자동 재시도하지 않습니다.') from None
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, AttributeError, KeyError):
        raise ValueError('OpenAI 응답을 읽을 수 없습니다. 자동 재시도하지 않습니다.') from None
    return {'turns': turns, 'draft': checked['arguments'], 'call': calls[0], 'result': checked,
            'mode': 'openai_function_call', 'model': model.strip()}
