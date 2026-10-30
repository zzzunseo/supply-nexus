"""A reviewed product claim never establishes a customer contract or recipe."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path


REVIEW_FILE = Path(__file__).parent / 'data/evidence_review.json'
PRODUCT_LABELS = {'documented': '제품 종류 근거 있음', 'family_only': '제품군 자료만 있음',
                  'unverified': '제품 종류 미확인'}


def attach_review(network, path=None):
    """Attach provenance only; numerical inputs and dependencies stay untouched."""
    review = json.loads(Path(path or REVIEW_FILE).read_text(encoding='utf-8'))
    for key, node in network['nodes'].items():
        if node['kind'] not in ('product', 'material'):
            continue
        record = deepcopy(review['materials'].get(key, {}))
        record.setdefault('product_basis', 'unverified')
        record.setdefault('customer_contract_basis', 'unverified')
        record.setdefault('technical_use_basis', 'unverified')
        record.setdefault('condition', '고객별 필수 사용 미확인')
        record['checked_at'] = review['checked_at'] if key in review['materials'] else None
        node['product_evidence'] = record
        node['previous_source'] = node.get('source')
        node['candidate_source'] = record.get('product_source') or record.get('candidate_source')
        node['source'] = record.get('product_source')
        node['status'] = PRODUCT_LABELS[record['product_basis']]
        node['source_note'] += ' 제품 종류 근거와 현재 고객 납품·필수 레시피·물량은 별개이며 후자는 미확인.'
    network['evidence_review'] = deepcopy(review)
    return network


def material_basis(network, node_id):
    record = network['nodes'][node_id].get('product_evidence', {})
    return deepcopy({
        'product_basis': record.get('product_basis', 'unverified'),
        'product_source': record.get('product_source'),
        'technical_use_basis': record.get('technical_use_basis', 'unverified'),
        'technical_stage': record.get('technical_stage'),
        'condition': record.get('condition', '소재의 고객별 필수 사용·실제 납품은 미확인'),
        'customer_contract_basis': record.get('customer_contract_basis', 'unverified'),
        'checked_at': record.get('checked_at'),
    })


def review_summary(network):
    records = network.get('evidence_review', {}).get('materials', {})
    counts = Counter(record['product_basis'] for record in records.values())
    extended = Counter(record['product_basis'] for key, record in records.items()
                       if key.startswith('extended:'))
    return {
        'material_product_nodes': len(records),
        'product_basis_counts': dict(counts),
        'extended_product_basis_counts': dict(extended),
        'verified_current_item_contracts': sum(record['customer_contract_basis'] == 'documented'
                                               for record in records.values()),
        'actual_share_values': sum(record.get('actual_share_pct') is not None for record in records.values()),
        'actual_inventory_values': sum(record.get('actual_inventory_days') is not None for record in records.values()),
        'actual_alternative_values': sum(record.get('actual_alternative_fraction') is not None for record in records.values()),
        'included_backbone_scenario_links': sum(item['included'] for item in network['relationship_decisions'].values()),
        'excluded_backbone_reference_links': sum(not item['included'] for item in network['relationship_decisions'].values()),
    }
