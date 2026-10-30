"""Explicit offline tool-call simulator. Not a language model or news verifier."""
from copy import deepcopy
import json
import re
from .article_review import article_draft, candidate_ids
from .scenario_tools import TOOL_NAME, decode_call, catalog


def blank_arguments():
    return dict(intent='simulate',target_ids=[],event_type='unknown',duration_days=None,loss_pct=None,
                closure_level='unknown',quotes={k:None for k in ('target','event','days','loss','closure')},unresolved=[])


def mock_turn(network, context, text):
    if not isinstance(text,str) or not text.strip() or len(text)>600:
        raise ValueError('질문은 1~600자로 입력하세요.')
    text=text.strip()
    state=deepcopy(context or {})
    allowed={r['id'] for r in catalog(network)}
    draft=article_draft(network,'',text)
    ids=[key for key in candidate_ids(draft) if key in allowed]
    companies={key for key in ids if network['nodes'][key]['kind']=='company'}
    owned=[key for key in ids if network['nodes'][key].get('company_id') in companies]
    if owned: ids=owned
    changed=bool(ids)  # An explicitly named target starts a fresh event; no silent numeric carry-over.
    port_names=re.findall(r'(\w+항)(?=\s|은|이|을|봉쇄|\d|$)',text)
    unknown_place=not ids and (bool(re.search(r'해협|항구|운하',text)) or
                               any(name not in ('통항','운항','출입항','항') for name in port_names))
    args=blank_arguments() if changed or unknown_place else deepcopy(state.get('draft') or blank_arguments())
    args['intent']='simulate'
    if len(ids)==1:
        args['target_ids']=ids
        args['quotes']['target']=next(hit['mention'] for hit in draft['mentions'] if any(c['id']==ids[0] for c in hit['candidates']))
        args['unresolved']=[]
    elif len(ids)>1:
        args['target_ids']=[]; args['quotes']['target']=None; args['unresolved']=[text]
    elif unknown_place:
        args['unresolved']=[text]
    if re.search(r'기사|보도|실제|확인해|뉴스',text): args['intent']='report'
    # Negative, recovery and cancellation language is not interpreted as a new outage.
    if re.search(r'아니|않|없|안\s*(?:됐|되|막|봉쇄)|취소|해제|복구',text):
        args['intent']='clarify'; args['unresolved']=[text]
    event=re.search(r'관세|봉쇄|통항|폐쇄|출입항|공급\s*(?:중단|감소|차질)|출하\s*(?:중단|감소|차질)',text)
    if event:
        token=event.group()
        args['event_type']='tariff' if token=='관세' else 'logistics_blockade' if re.search(r'봉쇄|통항|폐쇄|출입항',token) else 'supply_reduction'
        args['quotes']['event']=token
    if re.search(r'\d+\.\d+\s*일|-\s+\d',text): raise ValueError('기간은 정수 일수, 감소율은 음수가 아닌 값으로 지정하세요.')
    days=re.findall(r'-?\d+\s*일',text)
    losses=re.findall(r'-?\d+(?:\.\d+)?\s*%',text)
    if len(set(days))>1 or len(set(losses))>1: raise ValueError('기간과 감소율을 각각 하나만 지정하세요.')
    if days:
        args['duration_days']=int(re.search(r'-?\d+',days[0]).group()); args['quotes']['days']=days[0]
    if losses:
        args['loss_pct']=float(re.search(r'-?\d+(?:\.\d+)?',losses[0]).group()); args['quotes']['loss']=losses[0]
    closure=re.search(r'완전\s*봉쇄|전면\s*봉쇄|완전|전면|통항\s*중단|부분\s*봉쇄|일부\s*봉쇄|부분|일부',text)
    if closure:
        args['closure_level']='partial' if re.search(r'부분|일부',closure.group()) else 'full'
        args['quotes']['closure']=closure.group()
        if args['closure_level']=='full' and not losses:
            args['loss_pct']=None; args['quotes']['loss']=None
    elif args['event_type']=='logistics_blockade' and losses:
        args['closure_level']='full' if args['loss_pct']==100 else 'partial'
        args['quotes']['closure']=losses[0]
    if args['event_type']=='supply_reduction':
        args['closure_level']='not_applicable'; args['quotes']['closure']=None
    if not any((ids,event,days,losses,closure)) and not re.search(r'적용|계산|가정|시뮬',text):
        args['intent']='clarify'  # A question must not replay a previously completed tool call.
    turns=(state.get('turns',[])+[text])[-10:]
    call={'type':'function_call','name':TOOL_NAME,'arguments':json.dumps(args,ensure_ascii=False)}
    result=decode_call(call,network,'\n'.join(turns))
    return {'turns':turns,'draft':args,'call':call,'result':result,'mode':'offline_mock_function_call'}
