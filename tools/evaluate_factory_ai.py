"""Run actual model evaluation only when explicitly requested with --live.

Authored examples are smoke tests, not an independent production benchmark.
Never writes the API key or full request/response to disk.
"""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from resilience_data import build_network
from news.factory_ai import factory_registry,prepare_factory_article,analyze_factory_article
from news.factory_examples import EXAMPLES


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='Make four paid API requests, one per authored example')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.live:
        parser.error('실제 모델 평가는 --live가 필요합니다. 예시 규칙 검사와 AI 정확도를 혼동하지 마세요.')
    key=os.environ.get('SUPPLY_AI_API_KEY') or os.environ.get('OPENAI_API_KEY','')
    if not key:
        parser.error('서버 환경변수에 API 키를 설정하세요. 명령행 인수로 키를 전달하지 마세요.')
    registry=factory_registry(build_network())
    expected={'akm':('factory_fire','akm'),'unknown':('factory_fire','jsr'),'tariff':('other',None),'comparison':('no_event',None)}
    rows=[]
    for name,example in EXAMPLES.items():
        row=dict(example=name,completed=False)
        try:
            result=analyze_factory_article(registry,prepare_factory_article(example['body'],example['url']),key,os.environ.get('SUPPLY_AI_MODEL','gpt-4.1-mini'))
            event,company=expected[name]
            row.update(completed=True,event_correct=result['event_type']==event,company_correct=result['company_id']==company,
                returned_event=result['event_type'],returned_company=result['company_id'],
                bounded_routes=sum(r['state']=='bounded_review' for r in result['routes']),
                inappropriate_bounded_route=any(r['state']=='bounded_review' for r in result['routes']) if name!='akm' else False,
                expected_case_route_found=any(r['route_id']=='case:akm-rme-dac' and r['state']=='bounded_review' for r in result['routes']) if name=='akm' else None)
        except ValueError as error:
            row['error']=str(error)
        rows.append(row)
    report=dict(method='live_api',model=os.environ.get('SUPPLY_AI_MODEL','gpt-4.1-mini'),
        limit='직접 작성한 4개 예시의 소규모 점검. 독립 검증 데이터·실제 피해 예측 정확도가 아님. 오류도 결과에 포함하며 의미·근거 해석은 사람이 별도 검토해야 함.',results=rows)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Completed model review:',sum(r['completed'] for r in rows),'/',len(rows))
    print('Report:',args.output.resolve())


if __name__=='__main__':main()
