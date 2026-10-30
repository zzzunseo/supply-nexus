"""Registered product matches, not qualified substitutions or live search results."""
import re
import unicodedata
from product_comparison import compare_record,load_comparison_data


def question_requirements(query):
    text=unicodedata.normalize('NFKC',query)
    requirements={};notes=[]
    diameters=re.findall(r'(?<![\d.])(\d+(?:\.\d+)?)\s*mm\b',text,re.I)
    if len(set(diameters))==1:requirements['diameter_mm']=float(diameters[0])
    elif diameters:notes.append('직경이 여러 개입니다. 한 조건씩 비교하세요.')
    wafer_types=[w for w in ('PW','EPI','DSP') if match(text,w)]
    if len(wafer_types)==1:requirements['wafer_type']=wafer_types[0]
    elif wafer_types:notes.append('웨이퍼 종류가 여러 개입니다. PW·EPI·DSP를 하나씩 비교하세요. 종류 조건의 충족 판정은 보류합니다.')
    hf=any(w in text for w in ('불화수소','불산')) or match(text,'HF') or match(text,'BHF')
    purity=re.search(r'(?:순도\s*)?(\d+(?:\.\d+)?)\s*%\s*이상',text)
    if purity and (not hf or '순도' in purity[0]):requirements['min_purity_pct']=float(purity[1])
    for word,key in [('수분','max_water_ppmv'),('CF4','max_cf4_ppmv')]:
        found=re.search(re.escape(word)+r'\s*(\d+(?:\.\d+)?)\s*ppmv\s*이하',text,re.I)
        if found:requirements[key]=float(found[1])
    exposures=[w for w in ('ArF','KrF','EUV') if match(text,w)]
    if len(exposures)==1:requirements['exposure']=exposures[0]
    elif exposures:notes.append('노광 제품군이 여러 개입니다. 한 제품군씩 비교하세요. 제품군 조건의 충족 판정은 보류합니다.')
    for key,choices in [('exposure_mode',{'Immersion':['immersion','액침'],'Dry':['dry','건식']}),('tone',{'positive':['positive','포지티브','포지형','양성','PTI'],'negative':['negative','네거티브','네거형','음성','NTI']})]:
        values=[value for value,words in choices.items() if any(match(text,w) for w in words)]
        if len(values)==1:requirements[key]=values[0]
        elif values:notes.append('조건이 여러 개입니다: '+key+' · 하나씩 비교하세요.')
    if hf:
        if '고순도' in text:requirements['grade_verified']='qualified-grade'
        forms=[]
        if '무수' in text or match(text,'anhydrous'):forms.append('anhydrous')
        if '수용액' in text or match(text,'aqueous'):forms.append('aqueous')
        if '완충' in text or match(text,'BHF'):forms.append('buffered')
        if len(set(forms))==1:requirements['product_form']=forms[0]
        elif forms:notes.append('제품 형태가 여러 개입니다. 무수 HF·수용액·BHF를 나누어 비교하세요.')
        amounts=re.findall(r'(?:농도\s*)?(\d+(?:\.\d+)?)\s*(?:mass|wt)?\s*%(?!\s*(?:이상|이하))',text,re.I)
        if not re.search(r'순도\s*\d',text) and len(set(amounts))==1:requirements['concentration_pct']=float(amounts[0])
        elif amounts and not re.search(r'순도\s*\d',text):notes.append('농도가 여러 개입니다. 한 농도씩 비교하세요.')
        if not re.search(r'순도\s*\d',text) and re.search(r'%\s*(?:이상|이하)',text):
            requirements['concentration_range_unverified']='requested-range'
            notes.append('농도 범위 조건은 자동 비교하지 않습니다. 개별 규격서를 확인하세요.')
        notes.append('HF의 용액 농도와 불순물 순도는 다른 지표입니다. 고순도 적합성은 금속·입자 규격과 CoA로 별도 확인합니다.')
    for unit in ('ppb','ppt'):
        found=re.search(r'(?:총\s*)?금속(?:\s*불순물)?\s*(\d+(?:\.\d+)?)\s*'+unit+r'\s*이하',text,re.I)
        if found:requirements['max_metal_'+unit]=float(found[1])
    particle=re.search(r'입자(?:\s*크기)?\s*(\d+(?:\.\d+)?)\s*nm\s*이하',text,re.I)
    if particle:requirements['max_particle_nm']=float(particle[1])
    if any(w in text for w in ('산화세륨','세리아')) or match(text,'CeO2'):
        requirements['chemical']='CeO2'
        if '완성 슬러리' in text:requirements['product_form']='finished-slurry'
        elif '연마재' in text:requirements['product_form']='abrasive'
        notes.append('세리아 연마재와 배합된 완성 CMP 슬러리를 구분합니다. 원산지는 공급사 국적만으로 판단하지 않습니다.')
    if any(w in text for w in ('비중국','중국 제외','중국산 아닌','중국산이 아닌')):
        requirements['origin_country_verified']='non-China'
        notes.append('원산지는 제품별 확인 필요. 기업 본사·공장 소재국만으로 비중국산 조건을 충족시키지 않습니다.')
    # Only supported, explicit units/operators become constraints.
    if re.search(r'순도|수분|ppmv|%|mm|저항률|두께|인증|납기|공급량',text,re.I):
        notes.append('자동 비교 범위: 직경(mm), PW·EPI·DSP, 노광 제품군·Dry/액침·톤, HF 질량 농도, 금속·입자 상한, 순도 % 이상, 수분·CF4 ppmv 이하. 그 밖의 조건은 별도 확인.')
    return requirements,notes


def match(text,name):
    text=unicodedata.normalize('NFKC',text).casefold()
    name=unicodedata.normalize('NFKC',name).casefold()
    return len(name)>1 and bool(re.search(r'(?<![a-z0-9])'+re.escape(name)+r'(?![a-z0-9])',text))


def registered_candidates(bundle,query,include_rejected=False):
    if not any(w in query for w in ('중단','차질','대체','대안','공급사','벤더','멈추','끊기')):return []
    profiles=bundle['profiles']
    targets=[p for p in profiles if any(match(query,n) for n in [p['name']]+p.get('aliases',[]))]
    target_names={p['name'] for p in targets}
    products=[v for p in targets for v in p['products']]
    # Chemical questions match the actual product identity, never the whole gas family.
    chemical={v['fields']['chemical']['value'] for p in profiles for v in p['products']
              if 'chemical' in v['fields'] and match(query,str(v['fields']['chemical']['value']))}
    if any(w in query for w in ('불화수소','불산')) or match(query,'HF') or match(query,'BHF'):
        chemical={'BHF' if '완충' in query or match(query,'BHF') else 'HF'}
    if any(w in query for w in ('산화세륨','세리아')):chemical={'CeO2'}
    if chemical:
        products=[v for p in profiles for v in p['products'] if v.get('fields',{}).get('chemical',{}).get('value') in chemical]
    result=[];requirements,notes=question_requirements(query)
    if not products and ('wafer_type' in requirements or '웨이퍼' in query):
        products=[v for p in profiles for v in p['products'] if v['family']=='silicon-wafer']
    if not products and ('exposure' in requirements or '포토레지스트' in query):
        products=[v for p in profiles for v in p['products'] if v['family']=='photoresist']
    catalog={r['id']:r for r in load_comparison_data()['records']}
    for p in profiles:
        if p['name'] in target_names:continue
        matches=[];evaluations=[]
        for v in p['products']:
            for target in products:
                if v['family']!=target['family']:continue
                identity={'silicon-wafer':'wafer_type','process-gas':'chemical','photoresist':'exposure','cmp-slurry':'target_film','wet-chemical':'chemical','cmp-abrasive':'chemical'}.get(v['family'])
                if identity:
                    a=v['fields'].get(identity,{}).get('value');b=target['fields'].get(identity,{}).get('value')
                    if a is None or a!=b:continue
                else:continue
                evaluation=compare_record(catalog.get(v['id'],dict(v,legacy=False)),requirements)
                for note in notes:
                    if '여러 개' in note:
                        evaluation['checks'].append(dict(field='질문 조건',state='unknown',reason=note))
                        if evaluation['status']=='meets_documented':evaluation['status']='insufficient'
                evaluations.append(dict(product=v['name'],**evaluation,
                    evidence=[dict(field=k,value=f['value'],unit=f.get('unit'),locator=f['locator'],source_id=f['source_id']) for k,f in v['fields'].items()]))
                # An explicit physical form requires evidence; generic HF/BOE is not a form match.
                form_ok = not requirements.get('product_form') or v['fields'].get('product_form', {}).get('value') == requirements['product_form']
                if evaluation['status'] not in ('mismatch','reference_only') and form_ok:matches.append(v)
                break
        if matches or include_rejected and evaluations:
            eligible=matches or [v for v in p['products'] if v['name'] in {e['product'] for e in evaluations}]
            ids=sorted({f['source_id'] for v in eligible for f in v['fields'].values() if f.get('source_id') in bundle['sources']})
            if ids:result.append(dict(name=p['name'],aliases=p.get('aliases',[]),products=[v['name'] for v in matches],source_ids=ids,
                requirements=requirements,notes=notes,evaluations=evaluations,excluded=not bool(matches)))
    return result
