"""Bounded session-only API metadata. Never retain request/response contents."""
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timezone, timedelta


def record_request(state, payload, key, outcome, error=None):
    salt = state.setdefault('ai_request_salt', secrets.token_bytes(32))
    connection = hmac.new(salt, key.encode(), hashlib.sha256).hexdigest()[:12]
    schema = payload.get('text', {}).get('format', {}).get('name', '')
    probe = payload.get('instructions') == 'Connectivity test. Respond briefly.'
    feature = '연결 진단' if probe else {
        'product_comparison': '기업·소재 비교',
        'factory_review': '기사 검토',
    }.get(schema, '사건·공정 조사/정리')
    model = payload.get('model', '')
    if not isinstance(model, str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,100}', model) or model == key:
        model = 'unknown'
    message = str(error) if error else ''
    code = next((c for c in ('credit_balance_exhausted', 'insufficient_quota', 'rate_limit_exceeded',
                            'organization_usage_limit_exceeded', 'billing_hard_limit_reached') if c in message), '')
    request_id = re.search(r'요청 ID: (req_[A-Za-z0-9-]{8,80})', message)
    row = {'시각(KST)': datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds'),
           '기능': feature, '연결 식별값': connection, '모델': model,
           'API 경로': '/v1/responses', '결과': outcome, '오류 코드': code,
           '요청 ID': request_id.group(1) if request_id and key not in request_id.group(1) else ''}
    state['ai_request_history'] = (state.get('ai_request_history', []) + [row])[-30:]


def session_record(payload, key, outcome, error=None):
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    if get_script_run_ctx(suppress_warning=True) is None:
        return
    import streamlit as st
    record_request(st.session_state, payload, key, outcome, error)
