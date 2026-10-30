"""Five live API smoke cases. Reference validation is not factual AI accuracy."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from product_comparison import load_comparison_data
from news.alternative_ai import comparison_context,explain_alternatives

CASES=[
    ('pr_immersion_negative','photoresist',dict(exposure='ArF',exposure_mode='Immersion',tone='negative'),['fujifilm_fairs_nti','fujifilm_fairs_pti','dongjin_arf_immersion']),
    ('wafer_200mm','silicon-wafer',dict(wafer_type='PW',diameter_mm=200,thickness_um=725,resistivity_ohm_cm=10),['swt_dsp_200','swt_dsp_150','sumco_pw']),
    ('nf3_impurities','process-gas',dict(chemical='NF3',min_purity_pct=99.995,max_cf4_ppmv=25),['al_nf3_sg','matheson_nf3_4n5','sk_nf3']),
    ('cf4_water','process-gas',dict(chemical='CF4',min_purity_pct=99.999,max_water_ppmv=1),['matheson_cf4_5n','messer_cf4_5n']),
    ('cmp_hybrid','cmp-slurry',dict(target_film='Cu',application='hybrid_bonding'),['fujifilm_cu','fujifilm_hybrid','fujimi_metal']),
]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='Make five paid API requests, no automatic retries')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.live:parser.error('실제 호출은 --live가 필요합니다. 모델 정확도로 오인할 모의 결과는 생성하지 않습니다.')
    key=os.environ.get('SUPPLY_AI_API_KEY') or os.environ.get('OPENAI_API_KEY','')
    if not key:parser.error('API 키 환경변수를 설정하세요. 명령행 인수나 결과 파일에 키를 넣지 마세요.')
    model=os.environ.get('SUPPLY_AI_MODEL','gpt-4.1-mini');data=load_comparison_data();results=[]
    for name,family,req,ids in CASES:
        context=comparison_context(data,family,req,ids,'선택 조건의 차이와 자료 부족·추가 확인 사항을 설명해 주세요.')
        item=dict(case=name,context=context,local_validation_pass=False,human_semantic_review='pending')
        try:
            item['result']=explain_alternatives(context,key,model)
            item['local_validation_pass']=True
        except ValueError as error:item['error']=str(error)
        results.append(item)
    report=dict(method='live_api',model=model,executed_at=datetime.now(timezone.utc).isoformat(),
        limit='5개 시연 조건의 API·참조 검사. 독립 평가 데이터나 해설 사실 정확도 측정이 아님. 모든 의미·수치 해석은 사람이 원문과 대조해야 함.',results=results)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Reference/schema validation passed:',sum(r['local_validation_pass'] for r in results),'/',len(results))
    print('Human semantic review: pending')


if __name__=='__main__':main()
