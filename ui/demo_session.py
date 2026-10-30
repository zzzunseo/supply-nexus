"""Atomic, idempotent presentation transitions; detailed-mode state stays separate."""
from copy import deepcopy
from simulation.manual_scenario import build_manual_issue

TRANSIENT=('demo_review','demo_timing','demo_comparison','demo_inspection','demo_current_map','demo_map_context','demo_error','demo_explanation')
CONTROLS=('demo_case','demo_days','demo_percent','demo_review_product','demo_show_candidate','demo_basic_map','demo_input_mode','demo_category','demo_target','demo_event','demo_compare')


def clear_selection(state):
    state['demo_revision']=state.get('demo_revision',0)+1
    for key in ('demo_inspection','demo_current_map','demo_map_context'):state.pop(key,None)


def clear_case(state):
    clear_selection(state)
    for key in TRANSIENT:state.pop(key,None)
    state.update(demo_review_product='전체 제품군',demo_show_candidate=True,demo_transitioning=False,demo_compare='사건 적용')


def choose_case(state,cases,index):
    if type(index) is not int or not 0<=index<len(cases):raise ValueError('등록된 시연 사례를 선택하세요.')
    clear_case(state)
    state.update(demo_case=index,demo_applied=None,demo_step=1,demo_days=cases[index]['days'],demo_percent=cases[index].get('default_percent',100),
                 demo_active_case_id=cases[index]['id'],demo_input_mode='빠른 사례')


def reset_presentation(state,cases):
    choose_case(state,cases,1)


def commit_case(state,network,case,days,percent):
    # A queued double-click must not apply twice or restart the camera animation.
    old=state.get('demo_applied')
    if state.get('demo_transitioning') or (old and state.get('demo_step',1)>=2 and
        (old['id'],old['days'],old['percent'],old.get('event'))==(case['id'],days,percent,case.get('event'))):
        return False
    logistics=case.get('kind')=='logistics'
    event=case.get('event') or ('완전 봉쇄' if logistics and percent==100 else '부분 통항 제한' if logistics else '공급 감소')
    try:build_manual_issue(network,case.get('issue_target',case['target']),event,days,percent)
    except (ValueError,TypeError) as error:
        state['demo_error']=str(error)
        return False
    clear_case(state)
    state.update(demo_applied=dict(deepcopy(case),days=days,percent=percent),demo_step=2,
                 demo_active_case_id=case['id'],demo_transitioning=True)
    return True


def initialize_presentation(state,cases):
    for key,value in state.pop('demo_saved_controls',{}).items():state.setdefault(key,value)
    state.setdefault('demo_step',1);state.setdefault('demo_applied',None);state.setdefault('demo_revision',0)
    state.setdefault('demo_case',1)
    state.setdefault('demo_input_mode','빠른 사례')
    state.setdefault('demo_show_candidate',True)
    state.setdefault('demo_compare','사건 적용')
    if type(state['demo_case']) is not int or not 0<=state['demo_case']<len(cases):choose_case(state,cases,1)
    # Streamlit normally removes hidden widgets. Retain these across the steps.
    for key in CONTROLS:
        if key in state:state[key]=state[key]
    state['demo_active_case_id']=(state['demo_applied']['id'] if state['demo_applied'] and state['demo_step']>1 else cases[state['demo_case']]['id'])


def change_step(state,step):
    if step not in (1,2,3) or step>1 and not state.get('demo_applied'):return
    if step==1:state['demo_compare']='사건 적용'
    clear_selection(state);state['demo_step']=step
