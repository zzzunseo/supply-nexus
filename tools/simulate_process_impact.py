"""Offline illustrative scenarios. Never performs network or model calls."""
import argparse
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from company_evidence import evidence_bundle
from news.external_research import make_research_context,research_external,ResearchError,validate_report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    bundle=evidence_bundle()
    cases=[
        ('포토레지스트 공장 중단', 'ArF 액침 포토레지스트 생산 공장이 중단됐다고 가정하면 어느 공정에 영향이 가나요?', 'fuji_arf',
         '가상 공장의 ArF 액침 포토레지스트 공급과 포토 공정의 연결을 검토합니다.',
         [('포토','ArF 액침 포토레지스트는 노광에 사용하는 제품군입니다. 해당 등급이 피해 공장에서 생산되고 사용 라인의 조달에 연결되는 경우 포토 공정의 소재 조달 영향을 검토할 수 있습니다.')],
         ['피해 공장·중단 제품의 정확한 등급은 가정이며 실제 사건 자료가 없습니다.','고객별 공급 연결·재고·공정 호환성·생산 차질은 미확인입니다.']),
        ('NF3 공급 중단','NF3 공급이 중단됐다고 가정하면 어떤 반도체 공정을 검토해야 하나요?', 'efc_nf3',
         '공개된 NF3 용도를 기준으로 식각과 증착 장비 세정의 조건부 연결을 검토합니다.',
         [('식각','NF3의 공개 용도에는 플라즈마 식각이 포함됩니다. NF3를 실제 사용하는 식각 단계의 조달 영향을 검토하며 모든 식각 공정에 일반화하지 않습니다.'),
          ('증착·이온주입','NF3의 공개 용도에는 증착 챔버 세정이 포함됩니다. 증착 장비 유지·세정 경로의 간접 영향을 검토하며 이온주입 전체의 직접 투입 영향으로 확대하지 않습니다.')],
         ['사용 장비·레시피·대체 세정 방식·재고·실제 공급 중단 범위는 미확인입니다.']),
        ('희토류 관세 · 품목 미지정','희토류 관세가 생긴다고 가정하면 어느 반도체 공정에 영향이 가나요?', 'fuji_hybrid',
         '희토류의 원소·화합물·제품 형태가 지정되지 않아 특정 공정 연결을 보류합니다.',[],
         ['희토류의 원소·화합물·자석·연마재 등 제품 형태와 용도 자료가 필요합니다.','수입국·원산지·품목이 미지정이며 실제 관세 시행·세율을 주장하지 않습니다.','등록 CMP 자료만으로 희토류 포함이나 특정 공정의 영향을 입증할 수 없습니다. 관세는 생산 중단을 자동으로 뜻하지 않습니다.'])]
    output=[]
    for name,query,sid,summary,impacts,unknowns in cases:
        context=make_research_context(bundle,query,'공정 영향')
        source=bundle['sources'][sid]
        # Search protocol is simulated; its citation is a real registered URL,
        # not evidence that this script fetched it or verified the interpretation.
        proposal=dict(summary=summary,source_statements=[],impact_review=[dict(entity=p,statement=s,basis='conditional',source_ids=['D_'+sid]) for p,s in impacts],vendor_options=[],route_options=[],unknowns=unknowns)
        calls=[]
        def transport(request,timeout):
            calls.append(json.loads(request.data))
            if len(calls)==1:
                response=dict(status='completed',output=[dict(type='web_search_call',status='completed'),dict(type='message',content=[dict(type='output_text',text='직접 작성한 모의 검색 응답입니다. 실제 검색은 수행하지 않았습니다.',annotations=[dict(type='url_citation',url=source['url'],title=source['title'])])])])
            else:
                response=dict(status='completed',output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(proposal,ensure_ascii=False))])])
            return io.BytesIO(json.dumps(response).encode())
        report=research_external(context,'synthetic-test-only',model='synthetic-model',transport=transport)
        assert len(calls)==2 and not report['vendor_options'] and not report['route_options']
        assert all('공정 영향' in call['instructions'] for call in calls)
        report['provenance']=dict(method='handwritten_mock_response',real_api_calls=0,real_web_searches=0,mock_requests=len(calls))
        report['warning']='직접 작성한 가상 응답으로 연결·검증을 확인한 결과입니다. 실제 검색·AI 생성·의미 정확도 평가 결과가 아닙니다.'
        report['search']['simulated']=True
        blocked=[]
        for mutation in ('invented_source','invalid_process','vendor_in_process_mode'):
            bad=deepcopy(proposal)
            item=dict(entity='포토',statement='모의 오류 검사 문장입니다.',basis='conditional',source_ids=['D_'+sid])
            bad['impact_review']=[item]
            if mutation=='invented_source':item['source_ids']=['S999']
            elif mutation=='invalid_process':item['entity']='전체 공정 확정 중단'
            else:bad['vendor_options']=[dict(item,entity='가상 회사',basis='candidate')]
            try:validate_report(context,report['search'],bad)
            except ValueError:blocked.append(mutation)
            else:raise AssertionError(mutation+' was not blocked')
        output.append(dict(case=name,input=query,result=report,rejected_invalid_examples=blocked))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(dict(simulation=True,real_api_calls=0,real_web_searches=0,cases=output),ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 공정 영향 모의 시뮬레이션','', '직접 작성한 가상 응답으로 처리 흐름을 실행했습니다. 실제 API·웹 검색 0회. 모델의 정확도 평가는 아닙니다.','']
    for case in output:
        result=case['result']
        lines.extend(['## '+case['case'],'', '**입력:** '+case['input'],'','**출력:** '+result['summary'],''])
        for item in result['impact_review']:lines.extend(['- **'+item['entity']+'**: '+item['statement']])
        for value in result['unknowns']:lines.append('- 확인 필요: '+value)
        lines.extend(['','처리 결과: 모의 2단계 요청 완료. 없는 출처·지원하지 않는 공정·공정 모드의 벤더 추천 응답 차단.',''])
    args.output.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')
    print('PASS: 3 illustrative scenarios; 9 rejected invalid responses; 0 actual API/search calls')


if __name__=='__main__':main()

