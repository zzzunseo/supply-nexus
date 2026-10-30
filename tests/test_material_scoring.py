from copy import deepcopy
import unittest
from resilience_data import build_network
from simulation.resilience import calculate_supply_shock, interpret_issue
from ui.explanation import current_explanation


class MaterialScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network=build_network()

    def run_issue(self,text,days=60,**kwargs):
        return calculate_supply_shock(self.network,[interpret_issue(text,self.network)],days,**kwargs)

    def test_photoresist_only_reduces_photo_and_does_not_predict_downstream_dates(self):
        result=self.run_issue('일본 포토레지스트 공급 중단 60일')
        self.assertEqual(result['scores']['포토'],60)
        for process in ('식각','증착·이온주입','금속배선'):
            self.assertEqual(result['scores'][process],100)
            self.assertNotIn(process,result['first_hit'])
        self.assertEqual(set(result['first_hit']),{'포토'})
        self.assertTrue(all(row['process']=='포토' for row in result['material_shortages']))
        text=current_explanation(self.network,result,{})
        self.assertIn('감소율과 발생 시점은 산정하지 않습니다',text)

    def test_equipment_supply_does_not_reduce_material_scores_even_without_stock(self):
        baseline=calculate_supply_shock(self.network,duration_days=60,use_inventory=False,use_bypass=False)
        for text in ('ASML 공급 중단 60일','램리서치 공급 중단 60일','검사 장비 공급 중단 60일'):
            with self.subTest(text=text):
                result=self.run_issue(text,use_inventory=False,use_bypass=False)
                self.assertEqual(result['scores'],baseline['scores'])
                self.assertEqual(result['first_hit'],{})
                self.assertIn('equipment',[r['category'] for r in result['context_impacts']])
                self.assertIn('장비 공급 제한',current_explanation(self.network,result,{}))

    def test_tariff_is_cost_context_and_supply_loss_remains_independent(self):
        baseline=calculate_supply_shock(self.network)
        result=self.run_issue('중국 갈륨 관세 20%',days=30)
        self.assertEqual(result['scores'],baseline['scores'])
        self.assertEqual(result['tariffs'][0]['index'],120)
        self.assertIn('비용 이슈',current_explanation(self.network,result,{}))

    def test_no_material_input_is_unscored_not_a_fabricated_hundred(self):
        result=calculate_supply_shock(self.network)
        self.assertIsNone(result['scores']['EDS'])
        self.assertIsNone(result['scores']['패키징'])
        self.assertTrue(all(row['EDS'] is None for row in result['timeline']))
        self.assertEqual(result['unscored_processes'],['EDS','패키징'])
        recipe=calculate_supply_shock(self.network,scopes=['package_tin'])
        self.assertEqual(recipe['scores']['패키징'],100)

    def test_upstream_material_losses_still_reach_their_material_product_but_not_other_operations(self):
        result=self.run_issue('미국 고순도 석영 공급 중단 60일')
        self.assertEqual(result['scores']['웨이퍼 제조'],0)
        self.assertEqual(result['scores']['포토'],100)
        self.assertEqual(result['scores']['식각'],100)

    def test_material_stock_and_backups_still_change_direct_fulfillment(self):
        event=interpret_issue('일본 포토레지스트 공급 중단 30일',self.network)
        with_stock=calculate_supply_shock(self.network,[event],14,use_bypass=False)
        after=calculate_supply_shock(self.network,[event],15,use_bypass=False)
        self.assertEqual(with_stock['scores']['포토'],100)
        self.assertEqual(after['scores']['포토'],0)
        self.assertEqual(after['scores']['식각'],100)

    def test_shared_material_can_affect_multiple_direct_users_without_operation_dependencies(self):
        result=self.run_issue('중국 희토류 공급 중단 60일',use_inventory=False,use_bypass=False)
        for process in ('산화','증착·이온주입','금속배선'):
            self.assertEqual(result['scores'][process],0)
        self.assertEqual(result['scores']['포토'],100)
        for node in self.network['nodes'].values():
            if node['kind']=='operation':
                self.assertFalse(any(self.network['nodes'][p]['kind']=='operation' for p in node['requires']))

    def test_calculation_preserves_original_sources_and_does_not_mutate_network(self):
        before=deepcopy(self.network)
        self.run_issue('일본 포토레지스트 중단 60일')
        self.assertEqual(self.network,before)
        self.assertEqual(len(self.network['backbone']),44)
