from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from evidence_review import attach_review, material_basis, review_summary
from flow_data import build_flow
from resilience_data import build_network
from simulation.resilience import calculate_supply_shock
from ui.flow_svg import material_details, render_flow_svg


ROOT = Path(__file__).resolve().parents[1]


class EvidenceReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()
        cls.result = calculate_supply_shock(cls.network)

    def test_every_product_is_classified_without_default_verification(self):
        expected = {key for key, node in self.network['nodes'].items()
                    if node['kind'] in ('product', 'material')}
        records = self.network['evidence_review']['materials']
        self.assertEqual(set(records), expected)
        self.assertEqual(len(expected), 140)
        self.assertEqual(len([key for key in records if key.startswith('extended:')]), 104)
        self.assertEqual(sum(review_summary(self.network)['product_basis_counts'].values()), 140)
        self.assertEqual(records['extended:cmp-tungsten:fujifilm']['product_basis'], 'family_only')
        self.assertEqual(records['extended:teos:entegris']['product_basis'], 'family_only')

    def test_product_documents_never_create_contract_stock_share_or_backup_facts(self):
        for record in self.network['evidence_review']['materials'].values():
            self.assertEqual(record['customer_contract_basis'], 'unverified')
            self.assertEqual(record['alternative_qualification_basis'], 'unverified')
            for field in ('actual_share_pct', 'actual_inventory_days', 'actual_alternative_fraction'):
                self.assertIsNone(record[field])
        summary = review_summary(self.network)
        self.assertEqual(summary['verified_current_item_contracts'], 0)
        self.assertEqual(summary['actual_share_values'], 0)

    def test_cross_vendor_product_sources_are_repaired_without_inventing_evidence(self):
        nodes = self.network['nodes']
        self.assertIn('sumcosi.com', nodes['supply:sumco:polished-wafer']['source'])
        self.assertIn('sumcosi.com', nodes['supply:sumco:epi-wafer']['source'])
        self.assertIn('tok.co.jp', nodes['supply:tok:photoresist']['source'])
        self.assertIn('teradyne.com', nodes['supply:teradyne:wafer-tester']['source'])
        self.assertIn('samsung.com', nodes['supply:samsung:processed-wafer']['source'])
        for item in ('oxygen', 'hydrogen'):
            node = nodes['supply:airproducts:' + item]
            self.assertIsNone(node['source'])
            self.assertEqual(node['product_evidence']['product_basis'], 'unverified')
            self.assertIn('airproducts.com', node['candidate_source'])

    def test_market_supplier_list_and_research_collaboration_do_not_establish_item_supply(self):
        expected = {'oxygen:airliquide>tsmc', 'oxygen:airproducts>tsmc',
                    'hydrogen:airliquide>tsmc', 'hydrogen:airproducts>tsmc',
                    'etch-gas:airliquide>tsmc', 'interconnect-tool:applied>samsung'}
        for key in expected:
            self.assertFalse(self.network['relationship_decisions'][key]['included'])
            self.assertNotIn('route:' + key, self.network['nodes'])
        self.assertEqual(review_summary(self.network)['included_backbone_scenario_links'], 24)
        self.assertEqual(len(self.network['backbone']), 44)
        self.assertTrue(all(edge['share_pct'] is None for edge in self.network['backbone']))

    def test_neon_cmp_and_cleaning_are_not_claimed_as_universal_required_inputs(self):
        records = self.network['evidence_review']['materials']
        self.assertIn('DUV', records['upstream:neon']['technical_stage'])
        self.assertIn('EUV', records['upstream:neon']['condition'])
        self.assertEqual(records['upstream:neon']['product_basis'], 'unverified')
        self.assertIn('일반화 금지', records['extended:cmp-pad:entegris']['condition'])
        self.assertIn('챔버', records['extended:nf3:linde']['condition'])
        self.assertTrue(all(r['process_grouping'] == 'model' for r in records.values()))

    def test_flow_retains_detached_evidence_and_excluded_relationships(self):
        flow = build_flow(self.network, self.result, '포토')
        card = next(card for column in flow['columns'] for card in column['cards']
                    if card['node_id'] == 'supply:tok:photoresist')
        self.assertEqual(card['evidence']['basis']['product_basis'], 'documented')
        self.assertEqual(card['evidence']['basis']['customer_contract_basis'], 'unverified')
        details = ' '.join(material_details(card))
        self.assertIn('미확인', details)
        self.assertIn('제품 종류 근거', details)
        self.assertNotIn('소진', render_flow_svg(flow))
        card['evidence']['basis']['product_basis'] = 'changed'
        self.assertEqual(material_basis(self.network, card['node_id'])['product_basis'], 'documented')

    def test_provenance_decoration_does_not_change_any_calculation_values(self):
        network = deepcopy(self.network)
        before = deepcopy(network)
        attach_review(network)
        for key in before['nodes']:
            for field in ('requires', 'weights', 'inventory_days', 'alt_vendor', 'alt_capacity',
                          'capacity_units', 'alt_qualification_days', 'alt_ramp_days'):
                self.assertEqual(network['nodes'][key].get(field), before['nodes'][key].get(field))
        after = calculate_supply_shock(network)
        self.assertEqual(after['timeline'], self.result['timeline'])
        self.assertEqual(after['nodes'], self.result['nodes'])

    def test_missing_review_defaults_to_unknown_not_confirmed(self):
        network = deepcopy(self.network)
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'empty.json'
            path.write_text(json.dumps({'checked_at': '2026-10-26', 'materials': {}}), encoding='utf-8')
            attach_review(network, path)
        record = material_basis(network, 'supply:jsr:photoresist')
        self.assertEqual(record['product_basis'], 'unverified')
        self.assertIsNone(record['checked_at'])
        self.assertIsNone(record['product_source'])

    def test_source_access_failure_is_not_claimed_as_product_absence(self):
        checks = json.loads((ROOT / 'data/evidence_source_checks.json').read_text(encoding='utf-8'))
        self.assertTrue(any(row['status'] == 'unavailable_in_tool' for row in checks['checks']))
        self.assertEqual(self.network['nodes']['supply:airproducts:oxygen']['product_evidence']['product_basis'], 'unverified')
        self.assertIn('supply:airproducts:oxygen', self.network['nodes'])
