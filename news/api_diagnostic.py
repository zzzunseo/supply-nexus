"""Small explicit connectivity probes; no user documents or stored credentials."""
import re
from datetime import datetime, timezone
from .external_research import _request


def diagnose(key,model,transport=None):
    if not key or not key.isascii() or any(c.isspace() for c in key):
        raise ValueError('공통 API 키를 확인하세요.')
    if not re.fullmatch(r'[A-Za-z0-9._:-]{1,100}',model):
        raise ValueError('모델 ID를 확인하세요.')
    rows=[]
    for structured in (False,True):
        payload=dict(model=model,store=False,max_output_tokens=128,input='Return a JSON object with ok set to true.',instructions='Connectivity test. Respond briefly.')
        if structured:
            payload['text']={'format':dict(type='json_schema',name='connectivity_probe',strict=True,schema=dict(type='object',properties={'ok':{'type':'boolean'}},required=['ok'],additionalProperties=False))}
        try:
            _request(payload,key,transport,timeout=25)
            rows.append({'요청':'구조화 응답' if structured else '일반 응답','결과':'성공','설명':'작은 요청의 API 응답 완료 확인'})
        except ValueError as error:
            rows.append({'요청':'구조화 응답' if structured else '일반 응답','결과':'실패','설명':str(error)})
            if not structured:
                break
    return dict(time=datetime.now(timezone.utc).isoformat(),model=model,rows=rows)
