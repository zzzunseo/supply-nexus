import unittest
from copy import deepcopy
from resilience_data import build_network
from ui.research_map import map_matches,mentions


class ResearchMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.network=build_network()

    def test_wafer_impurity_mention_does_not_add_oxygen_supply_chain(self):
        data=map_matches(self.network,'SUMCO 300mm 폴리시드 실리콘 웨이퍼 대안',
            'Siltronic의 비저항과 산소 관리 기준을 확인하세요.')
        self.assertNotIn('고순도 산소',data['materials'])
        self.assertNotIn('산화',data['processes'])
        self.assertIn('Siltronic',{m['name'] for m in data['markers']})

    def test_hf_is_not_hydrogen_and_has_evidence_based_etch_scope(self):
        data=map_matches(self.network,'고순도 불화수소 수용액 49% 대체 공급사')
        self.assertFalse(mentions('불화수소','수소'))
        self.assertNotIn('고순도 수소',data['materials'])
        self.assertIn('불화수소',data['materials'])
        self.assertIn('식각',data['processes'])

    def test_named_factory_uses_factory_region_instead_of_headquarters(self):
        data=map_matches(self.network,'TSMC Fab 14 중단을 가정')
        markers={m['id']:m for m in data['markers']}
        self.assertNotIn('tsmc',markers)
        self.assertEqual(markers['facility:tsmc-14']['site'],'타이난')
        self.assertIn('개략점',markers['facility:tsmc-14']['role_label'])
        self.assertEqual(data['routes'],[])

    def test_company_and_route_use_registered_coordinates(self):
        data=map_matches(self.network,'SUMCO 수에즈','희망봉 우회')
        ids={m['id'] for m in data['markers']}
        self.assertTrue({'sumco','logistics:suez','logistics:cape'}<=ids)
        self.assertEqual(data['routes'],[])
        self.assertTrue(all(m['score'] is None for m in data['markers']))

    def test_material_maps_suppliers_not_losses(self):
        data=map_matches(self.network,'NF3 공급 중단')
        self.assertTrue(data['materials'])
        self.assertTrue(data['markers'])
        self.assertEqual(data['loss'],0)
        self.assertTrue(all('등록 제품 자료' in m['reason'] for m in data['markers']))

    def test_three_questions_and_answer_mentions(self):
        cases=[('SUMCO 공급 중단','SUMCO와 Shin-Etsu Chemical',{'sumco','shinetsu'}),
               ('NF3 대체 공급사','Merck KGaA',{'merck'}),
               ('수에즈 우회','희망봉 우회',{'logistics:suez','logistics:cape'})]
        for question,answer,expected in cases:
            with self.subTest(question=question):
                data=map_matches(self.network,question,answer)
                self.assertTrue(expected<={m['id'] for m in data['markers']})
                self.assertEqual(len(data['markers']),len({m['id'] for m in data['markers']}))
                if question=='수에즈 우회':
                    self.assertEqual(data['routes'][0]['kind'],'detour')
                    self.assertIn('실제 운항 경로 아님',data['routes'][0]['material'])
                else:
                    self.assertTrue(all('등록 위치' in m['role_label'] for m in data['markers']))
                    self.assertEqual(data['routes'],[])

    def test_unknown_and_substrings_do_not_invent_nodes(self):
        before=deepcopy(self.network)
        self.assertFalse(map_matches(self.network,'UnknownFabricator999')['markers'])
        self.assertFalse(mentions('SUMCOLOGY','SUMCO'))
        self.assertTrue(mentions('NF₃ 공급','NF3'))
        self.assertEqual(before,self.network)

    def test_detour_pair_does_not_depend_on_ai_text(self):
        data=map_matches(self.network,'말라카 해협 우회 방법은?')
        markers={m['id']:m for m in data['markers']}
        self.assertEqual(markers['logistics:malacca']['role'],'blocked_port')
        self.assertEqual(markers['logistics:lombok']['role'],'detour_port')
        self.assertEqual(len(data['comparisons']),1)
        self.assertEqual(len(data['routes']),1)
        self.assertFalse(map_matches(self.network,'말라카 위치')['routes'])
