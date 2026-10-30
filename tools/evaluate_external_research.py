"""Explicit live scenario evaluation; never substitutes mocks for API results."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from company_evidence import evidence_bundle
from news.external_research import make_research_context,research_external,ResearchError,suggest_mode

QUESTIONS={
    'tariff':'희토류 관세가 반도체 공정에 미치는 영향은? 미지정 국가·품목·시점은 가정으로 구분하고 소재 용도의 공식 근거를 찾아 주세요.',
    'factory':'TSMC Fab 14가 중단된다고 가정하면 해당 공장의 공정 범위와 다른 공장 전환 전 확인할 조건은?',
    'material':'불산 공급이 끊기면 식각 공정 영향과 대체 공급사를 제품 형태·규격 근거와 함께 검토해 주세요.',
    'company':'SUMCO 공급 차질을 가정하고 고객 영향 확인 대상과 대체 웨이퍼 벤더를 조사해 주세요. 실제 고객 피해와 기업 관계를 구분해 주세요.',
    'vendor':'ArF Immersion 포토레지스트의 대체 벤더를 등록 목록 밖에서도 찾아 제품 근거와 승인·공급 여력 확인 조건을 구분해 주세요.',
    'route':'홍해 통항 차질을 가정하고 부산에서 로테르담까지 일반 컨테이너 화물의 우회 항로와 선사 검토 후보를 조사해 주세요. 과거 발표와 현재 운항을 구분해 주세요.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--case',choices=list(QUESTIONS),default='company')
    parser.add_argument('--simple',action='store_true',help='검색 답변만 평가: 요청 1회, 후보 구조화 제외')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.live:parser.error('유료 API·검색 실행에는 --live가 필요합니다.')
    key=os.environ.get('SUPPLY_AI_API_KEY') or os.environ.get('OPENAI_API_KEY','')
    if not key:parser.error('API 키 환경변수를 설정하세요. 키를 명령행 인수나 채팅으로 전달하지 마세요.')
    context=make_research_context(evidence_bundle(),QUESTIONS[args.case],suggest_mode(QUESTIONS[args.case]))
    report=dict(case=args.case,context_id=context['id'],human_semantic_review='pending')
    try:
        report['result']=research_external(context,key,os.environ.get('SUPPLY_AI_MODEL','gpt-6.1-sol'),simple=args.simple)
        report['state']='completed'
    except ResearchError as error:report.update(state='search_only',error=str(error),search=error.search)
    except ValueError as error:report.update(state='failed',error=str(error))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('State:',report['state'],'/ human semantic review: pending')


if __name__=='__main__':main()
