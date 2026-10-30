"""Explicit registered selections mapped directly to the existing engine contract."""
from .schema import validate_parsed

KINDS={'기업':('company',),'소재':('resource','product','material'),'항만·해협':('logistics',)}
SUPPLY_CASES=('공급 중단','공급 감소','수출 제한','화재·사고에 따른 공급 차질','관세 부과','이 대상 이슈 해제')
PORT_CASES=('완전 봉쇄','부분 통항 제한','이 대상 이슈 해제')


def cases_for(network,target):
    return PORT_CASES if network['nodes'][target]['kind']=='logistics' else SUPPLY_CASES


def build_manual_issue(network,target,case,days,percent):
    node=network['nodes'].get(target)
    if not node or node['kind'] not in sum(KINDS.values(),()):
        raise ValueError('등록된 기업·소재·항만 하나를 선택하세요.')
    if case not in cases_for(network,target):
        raise ValueError('선택 대상에 적용할 수 없는 사건입니다.')
    restore=case=='이 대상 이슈 해제'
    full=case in ('공급 중단','완전 봉쇄')
    if not restore and not full and (type(percent) not in (int,float) or not 0<percent<=(500 if case=='관세 부과' else 100)):
        raise ValueError('감소율은 0 초과~100%, 관세율은 0 초과~500%로 지정하세요.')
    if case=='부분 통항 제한' and percent>=100:
        raise ValueError('부분 통항 제한은 100% 미만으로 지정하세요. 전면 차단은 완전 봉쇄를 선택하세요.')
    rate=0. if restore else 1. if full else percent/100
    label='관세율' if case=='관세 부과' else '통항 감소' if node['kind']=='logistics' else '공급 감소'
    note='사용자가 직접 선택한 시뮬레이션 가정입니다. 소재 충족도는 생산량 감소 예측치가 아닙니다.'
    if node['kind']=='logistics': note+=' 등록 물류 경유·우회 가정에만 적용합니다.'
    if case=='화재·사고에 따른 공급 차질': note+=' 화재 자체에서 피해율을 추정하지 않고 사용자가 지정한 공급 감소율을 적용합니다.'
    if case=='관세 부과': note+=' 관세는 비용 맥락으로만 계산하며 소재 점수를 낮추지 않습니다.'
    if restore: note='선택 대상에 걸린 공급·관세 이슈를 해제했습니다. 다른 대상의 이슈는 유지합니다.'
    return validate_parsed(dict(action='restore' if restore else 'apply',kind='tariff' if case=='관세 부과' else 'supply',
        targets=[target],rate=rate,days=days,
        text=f"{node['name']} · {case}" if restore else f"{node['name']} · {case} · {days}일 · {label} {rate*100:g}%",note=note),network['nodes'])
