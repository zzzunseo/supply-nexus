"""Candidate product to existing material/process taxonomy; no customer edges."""
import json


def candidate_flow(network,bundle,company,product_name):
    profile=next((p for p in bundle['profiles'] if p['name']==company),None)
    product=next((p for p in profile['products'] if p['name']==product_name),None) if profile else None
    if not product:return None
    fields=product['fields'];item_id=None
    if product['family']=='silicon-wafer':
        item_id={'PW':'polished-wafer','EPI':'epi-wafer'}.get(fields.get('wafer_type',{}).get('value'))
    elif product['family']=='photoresist':item_id='photoresist'
    elif product['family']=='process-gas':
        item_id={'NF3':'nf3','CF4':'etch-gas'}.get(fields.get('chemical',{}).get('value'))
    if product['family'] in ('wet-chemical','cmp-abrasive'):
        application=fields.get('application',{}).get('value',[])
        chemical=fields.get('chemical',{}).get('value','')
        processes=[label for token,label in [('wet-etch','습식 식각'),('wet-clean','습식 세정'),('STI','STI CMP'),('ILD','ILD CMP')] if token in application]
        if not processes and 'CMP' in application:processes=['CMP · 대상 막 추가 확인']
        return dict(company=company,product=product_name,material={'HF':'불화수소 약액','BHF':'완충 불화수소 약액','CeO2':'산화세륨 연마재'}.get(chemical,chemical),processes=processes,source_ids=sorted({f['source_id'] for f in fields.values()}))
    items={i['id']:i for i in network['original']['items']}
    items.update(network['extended_materials'])
    material=items.get(item_id)
    return dict(company=company,product=product_name,material=material['name'] if material else '소재 연결 확인 필요',
        processes=material.get('processes',[]) if material else [],
        source_ids=sorted({f['source_id'] for f in fields.values()}))


def render_candidate_flow(network,bundle,company,product_name):
    import streamlit as st
    flow=candidate_flow(network,bundle,company,product_name)
    if not flow:return
    st.markdown('**선택 후보의 소재·공정 흐름**')
    labels=[flow['company'],flow['product'],flow['material'],
            ' · '.join(flow['processes']) or '관련 공정 자료 부족']
    dot=['digraph {rankdir=LR; bgcolor="transparent"; node [shape=box,style="rounded,filled",fillcolor="#102a3d",fontcolor="#e0f3ff",color="#42cbdc"]; edge [color="#42cbdc",fontcolor="#a5bbce"];']
    for index,label in enumerate(labels):dot.append('n'+str(index)+' [label='+json.dumps(label)+'];')
    dot+=['n0 -> n1 [label="제품 자료"];','n1 -> n2 [label="제품 종류 매칭"];','n2 -> n3 [label="제품 용도 연결"];','}']
    st.graphviz_chart('\n'.join(dot))
    st.caption('공개 제품 자료와 소재·공정 용도의 연결입니다. 고객별 납품·실제 공장 사용·대체 승인은 추가 확인 대상입니다.')
