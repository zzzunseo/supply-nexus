"""Separate source-backed company relationships, product vendors and model routes.

This audits stored provenance, not present-day contracts or freshly fetched sources.
Product evidence alone must never create a customer relationship.
"""
from simulation.evidence import relationship_decision
import json
from pathlib import Path


def audit_relationships(network):
    supported=[]; references=[]
    for edge in network['backbone']:
        accepted,reason=relationship_decision(edge)
        row=dict(id=edge['id'],supplier=network['entities'][edge['from']]['name'],
                 customer=network['entities'][edge['to']]['name'],material=edge['item'],
                 year=edge.get('relationship_source_year'),checked_at=edge.get('checked_at'),
                 temporal=edge.get('temporal_status'),source=edge.get('relationship_source'),
                 scope=edge.get('evidence_note') or edge.get('relation_note'),
                 reason=reason)
        # Keep the original provenance vocabulary; no inferred current contract.
        row['basis']='공급 관계 근거' if accepted else {
            'collaboration':'협력 관계','service':'서비스 관계','qualification':'인증 기록',
            'planned_contract':'예정 계약','unconfirmed':'관계 미확인',
            'supply':'과거 공급 관계'}.get(edge.get('relationship_kind'),'추가 검토')
        row['item_confirmed']=edge.get('item_status')=='출처 있음'
        (supported if accepted else references).append(row)
    return dict(supported=supported,references=references)


def vendor_catalog(network):
    grouped={}
    for node in network['nodes'].values():
        proof=node.get('product_evidence',{})
        company=node.get('company_id')
        if node['kind'] not in ('product','material') or not company:continue
        if proof.get('product_basis')!='documented' or not node.get('source'):continue
        key=(company,node.get('item_id') or node['name'])
        if key in grouped:continue
        grouped[key]=dict(supplier_id=company,supplier=network['entities'][company]['name'],material=node['name'],
                          item_id=node.get('item_id'),source=node['source'],
                          product_group=node.get('item_id') or node['name'].split(' · ',1)[-1],
                          checked_at=proof.get('checked_at'),basis='제품 자료 확인 · 고객 연결 없음')
    # Curated candidates can be reserve nodes, which have no product_evidence.
    # Read their explicit product review rather than inferring from reserve capacity.
    review=json.loads((Path(__file__).parent/'data/response_evidence.json').read_text(encoding='utf-8'))
    for record in review['cases'].values():
        company=record['candidate_id'];item=record['item_id']
        source=review['sources'].get(company+'_products',{})
        if (company,item) in grouped or not source.get('url') or not record.get('candidate_classes'):continue
        if company not in network['entities']:continue
        grouped[(company,item)]=dict(supplier_id=company,supplier=network['entities'][company]['name'],material=record['material'],
            item_id=item,product_group=item,source=source['url'],checked_at=review['reviewed_at'],
            basis='제품 자료 확인 · 고객 연결 없음')
    return sorted(grouped.values(),key=lambda r:(r['supplier'],r['material']))


def scenario_routes(network):
    rows=[]
    for key,route in network.get('logistics_routes',{}).items():
        for edge_id in route['edges']:
            edge=next(e for e in network['visual_edges'] if e['id']==edge_id)
            product=network['nodes'][edge['from']]
            supplier=product.get('company_id') or edge.get('evidence',{}).get('from')
            rows.append(dict(id=edge_id,supplier=network['nodes'].get(supplier,product)['name'],
                customer=network['nodes'][edge['to']]['name'],material=product['name'],
                via=' → '.join(network['logistics'][p]['name'] for p in route['via']),
                basis='시연 경유 가정 · 실제 화물 경로 미확인'))
    return rows
