from copy import deepcopy
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from product_comparison import load_comparison_data,compare_record,validate_catalog


class ProductComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_comparison_data()
        cls.records={r['id']:r for r in cls.data['records']}

    def status(self,key,requirements):
        return compare_record(self.records[key],requirements)['status']

    def test_pr_conditions_change_candidates_without_implying_qualification(self):
        required={'exposure':'ArF','exposure_mode':'Dry'}
        self.assertEqual(self.status('jsr_ar2772',required),'meets_documented')
        self.assertEqual(self.status('dongjin_arf_dry',required),'meets_documented')
        self.assertEqual(self.status('dongjin_arf_immersion',required),'mismatch')
        self.assertEqual(self.status('tok_tarf_p6111',required),'insufficient')
        self.assertEqual(self.status('tok_euv',{'exposure':'EUV'}),'meets_documented')
        self.assertTrue(all(r['customer_qualification']=='unverified' for r in self.records.values()))

    def test_gas_thresholds_distinguish_missing_and_listed_without_upper_operator(self):
        required={'chemical':'NF3','min_purity_pct':99.995,'max_cf4_ppmv':25}
        self.assertEqual(self.status('matheson_nf3_4n5',required),'meets_documented')
        self.assertEqual(self.status('matheson_nf3_4n',required),'mismatch')
        self.assertEqual(self.status('al_nf3_sg',required),'insufficient')
        self.assertEqual(self.status('sk_nf3',required),'insufficient')
        self.assertEqual(self.status('matheson_nf3_2n7',{'oxygen_ppmv':1}),'insufficient')

    def test_external_nf3_specs_change_candidates(self):
        required={'chemical':'NF3','min_purity_pct':99.995,'max_water_ppmv':1,'max_cf4_ppmv':25}
        self.assertEqual(self.status('efc_nf3_4n5',required),'meets_documented')
        self.assertEqual(self.status('linde_nf3_4n5',required),'mismatch')
        required.update(max_water_ppmv=5,max_cf4_ppmv=20)
        self.assertEqual(self.status('linde_nf3_4n5',required),'meets_documented')
        self.assertEqual(self.status('efc_nf3_4n5',required),'mismatch')
        self.assertIn('용기',self.records['efc_nf3_4n5']['notes'])

    def test_wafer_raw_material_purity_and_ingot_dimensions_not_reused(self):
        required={'wafer_type':'PW','diameter_mm':300}
        self.assertEqual(self.status('siltronic_pw',required),'meets_documented')
        self.assertEqual(self.status('sumco_pw',required),'meets_documented')
        self.assertEqual(self.status('sk_siltron_pw',required),'meets_documented')
        self.assertEqual(self.status('sk_siltron_epi',required),'mismatch')
        self.assertEqual(self.status('sumco_pw',dict(required,diameter_mm=250)),'mismatch')
        self.assertEqual(self.status('sumco_pw',dict(required,thickness_um=775)),'insufficient')
        self.assertEqual(self.status('shinetsu_pw',required),'insufficient')
        self.assertEqual(self.status('siltronic_epi',required),'mismatch')
        self.assertNotIn('purity_pct',self.records['shinetsu_pw']['fields'])

    def test_example_condition_and_old_catalog_never_become_approval(self):
        self.assertEqual(self.status('tok_tarf_p6111',{'example_film_nm':250}),'insufficient')
        self.assertEqual(self.status('fujimi_7000',{'target_film':'Cu'}),'reference_only')
        self.assertEqual(self.status('fujifilm_cu',{'target_film':'Cu'}),'meets_documented')
        self.assertEqual(self.status('fujifilm_barrier',{'target_film':'Cu'}),'mismatch')

    def test_field_provenance_and_no_customer_edges(self):
        validate_catalog(self.data)
        self.assertEqual({r['family'] for r in self.records.values()},{'photoresist','silicon-wafer','process-gas','cmp-slurry','wet-chemical','cmp-abrasive'})
        self.assertTrue(all(not r['customer_edges'] for r in self.records.values()))
        broken=deepcopy(self.data)
        broken['records'][0]['fields']['exposure']['source_id']='missing'
        with self.assertRaises(ValueError):validate_catalog(broken)
        broken=deepcopy(self.data)
        broken['records'][0]['customer_edges']=['invented-customer']
        with self.assertRaises(ValueError):validate_catalog(broken)

    def test_ui_switch_families_threshold_and_sources(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        app.button(key='demo_advanced').click().run()
        self.assertFalse(app.exception)
        app.selectbox(key='comparison_family').select('process-gas').run()
        app.checkbox(key='comparison_check_cf4').check().run()
        app.selectbox(key='comparison_record').select('matheson_nf3_4n5').run()
        self.assertFalse(app.exception)
        for family in ['silicon-wafer','cmp-slurry','photoresist']:
            app.selectbox(key='comparison_family').select(family).run()
            self.assertFalse(app.exception)
        app.selectbox(key='comparison_exposure').select('EUV').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.tabs),8)

