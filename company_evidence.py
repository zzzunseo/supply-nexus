"""Separate company/response library; never inserts inferred engine edges."""
import json
from pathlib import Path
from product_comparison import load_comparison_data

PATH=Path(__file__).resolve().parent/'data/company_response_evidence.json'


def load_company_evidence():
    return json.loads(PATH.read_text(encoding='utf-8'))


def evidence_bundle():
    products=load_comparison_data();companies=load_company_evidence()
    profiles={}
    for r in products['records']:
        if r['legacy']:continue
        profile=profiles.setdefault(r['supplier'],dict(name=r['supplier'],role='제품 자료가 있는 벤더',
            aliases=[r['supplier']],products=[],source_ids=[]))
        profile['products'].append(dict(id=r['id'],name=r['name'],family=r['family'],fields=r['fields'],
            notes=r['notes'],customer_qualification=r['customer_qualification'],
            additional_capacity=r['additional_capacity'],lead_time_days=r['lead_time_days']))
        profile['source_ids']=sorted(set(profile['source_ids'])|{f['source_id'] for f in r['fields'].values()})
    for profile in companies['profiles']:
        if profile['name'] not in profiles:profiles[profile['name']]=dict(profile,products=[])
    sources={**products['sources'],**companies['sources']}
    used={sid for p in profiles.values() for sid in p['source_ids']}
    for row in companies['relationships']+companies['responses']+companies['routes']:used.update(row['source_ids'])
    sources={key:source for key,source in sources.items() if key in used}
    return dict(checked_at=companies['checked_at'],profiles=list(profiles.values()),sources=sources,
        relationships=companies['relationships'],responses=companies['responses'],routes=companies['routes'])
