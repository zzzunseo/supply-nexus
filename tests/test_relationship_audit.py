from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from resilience_data import build_network
from relationship_audit import audit_relationships,vendor_catalog,scenario_routes
from ui.demo_scenarios import connections,selected_case,custom_profile
from simulation.evidence import relationship_decision


class RelationshipAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.network=build_network()

    def test_all_original_records_accounted_and_reference_not_in_default_map(self):
        audit=audit_relationships(self.network)
        self.assertEqual(len(audit['supported'])+len(audit['references']),44)
        self.assertTrue(audit['references'])
        for row in connections(self.network):
            self.assertTrue(relationship_decision(row['evidence'])[0])
        jsr=selected_case(self.network,'기업','jsr','공급 중단')
        self.assertNotIn('samsung',jsr['recipients'])  # Collaboration is not a supply contract.
        self.assertIn('tsmc',jsr['recipients'])

    def test_product_catalog_does_not_invent_customers(self):
        rows=vendor_catalog(self.network)
        self.assertTrue(rows)
        self.assertTrue(all(r['source'].startswith('http') for r in rows))
        self.assertTrue(all('customer' not in r and 'recipient' not in r for r in rows))
        nitrogen=[r for r in rows if r['product_group']=='고순도 질소(N2)']
        self.assertGreaterEqual(len({r['supplier'] for r in nitrogen}),3)
        pr=[r for r in rows if r['product_group']=='photoresist']
        self.assertIn('Dongjin Semichem',{r['supplier'] for r in pr})
        self.assertTrue(all('가정' in r['basis'] for r in scenario_routes(self.network)))

    def test_vendor_map_keeps_product_only_vendor_without_customer_edge(self):
        from ui.vendor_map import vendor_map_data
        data=vendor_map_data(self.network,'photoresist',vendor_catalog(self.network))
        self.assertEqual(data['vendors'],3)
        dongjin=next(m for m in data['markers'] if m['id']=='dongjin')
        self.assertEqual(dongjin['role'],'product')
        self.assertFalse(any(r['supplier']=='dongjin' for r in data['rows']))
        self.assertTrue(any(r['supplier']=='jsr' and r['recipient']=='tsmc' for r in data['rows']))
        self.assertFalse(any(r['supplier']=='jsr' and r['recipient']=='samsung' for r in data['rows']))

    def test_public_contracts_remain_separate_from_operational_simulation(self):
        from ui.public_contracts import public_contracts
        rows=public_contracts()
        self.assertEqual({r['customer'] for r in rows},{'Micron','VSMC','SK hynix'})
        self.assertTrue(all(not r['simulation_eligible'] and r['source'].startswith('https://') for r in rows))
        self.assertFalse(any(r['recipient'] in {'micron','vsmc','skhynix'} for r in connections(self.network)))

    def test_all_eligible_vendors_included_not_only_first_match(self):
        case=selected_case(self.network,'기업','jsr','공급 중단')
        profile=custom_profile(self.network,case)
        expected={p['company_id'] for p in self.network['nodes'].values()
                  if p.get('kind')=='product' and p.get('item_id')=='photoresist'
                  and p.get('company_id')!='jsr'
                  and p.get('product_evidence',{}).get('product_basis')=='documented'
                  and p.get('source') and self.network['entities'].get(p.get('company_id'),{}).get('map_location')}
        self.assertTrue(expected)
        self.assertEqual({r['company_id'] for r in profile['candidates']},expected)

    def test_audit_panel_and_filters_render_in_guided_flow(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertTrue(any({'벤더','소재·제품','제품 출처'} <= set(frame.value.columns) for frame in app.dataframe))
        app.selectbox(key='audit_vendor_item').select('photoresist').run()
        app.selectbox(key='audit_route_port').select('가오슝항').run()
        vendor_frame=next(frame.value for frame in app.dataframe if '벤더' in frame.value.columns)
        expected={r['supplier'] for r in vendor_catalog(self.network) if r['product_group']=='photoresist'}
        self.assertEqual(set(vendor_frame['벤더']),expected)
        self.assertFalse(app.exception)
        app.button(key='demo_apply').click().run()
        app.button(key='demo_next').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any({'벤더','소재·제품','제품 출처'} <= set(frame.value.columns) for frame in app.dataframe))


if __name__=='__main__':unittest.main()
