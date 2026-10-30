from copy import deepcopy
import unittest
from news.article_chat import preview_review, respond
from news.article_exposure import process_exposure, exposure_summary
from news.article_briefing import briefing_markdown
from resilience_data import build_network


class ProcessExposureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network=build_network()

    def test_jsr_direct_photo_candidate_and_samsung_reference_are_separate(self):
        review,_=preview_review(self.network,'factory_unknown')
        before=deepcopy(review)
        data=process_exposure(review)
        self.assertEqual([r['recipient'] for r in data['direct']],['TSMC'])
        self.assertEqual(data['direct'][0]['processes'],['포토'])
        self.assertIn('포토레지스트',data['direct'][0]['path'])
        self.assertEqual([r['recipient'] for r in data['other']],['Samsung Electronics'])
        self.assertEqual(data['other'][0]['category'],'reference')
        self.assertIn('출하 차질이 발생할 경우',data['direct'][0]['effect'])
        self.assertEqual(review,before)

    def test_equipment_supply_evidence_is_not_mislabeled_reference_or_material_shortage(self):
        review,_=preview_review(self.network,'equipment_only')
        data=process_exposure(review)
        self.assertFalse(data['direct'])
        self.assertEqual(len(data['equipment']),2)
        self.assertTrue(all(r['category']=='supply' for r in data['equipment']))
        self.assertTrue(all('기존 생산 타격 미판정' in r['effect'] for r in data['equipment']))

    def test_cost_recovery_and_no_routes_keep_their_different_meanings(self):
        for case,phrase in [('tariff','조달 비용'),('partial_recovery','정상 출하 회복')]:
            with self.subTest(case=case):
                review,_=preview_review(self.network,case)
                self.assertIn(phrase,process_exposure(review)['direct'][0]['effect'])
                self.assertIn('포토',briefing_markdown(review))
        review,_=preview_review(self.network,'unknown_company')
        self.assertFalse(process_exposure(review)['rows'])
        self.assertIn('영향 없음이라는 뜻은 아닙니다',exposure_summary(review))

    def test_conversation_answers_where_and_which_process_using_same_context(self):
        context,first=respond(self.network,{},'JSR 화재 예시')
        self.assertIn('TSMC → 포토',first)
        context,reply=respond(self.network,context,'어느 공정에 타격이 예상돼?')
        self.assertIn('JSR → 포토레지스트 → TSMC → 포토',reply)
        self.assertIn('미확인',reply)
        context,reply=respond(self.network,context,'삼성만')
        self.assertIn('Samsung Electronics → 포토',reply)
        self.assertIn('직접 공급 노출은 판단을 보류',reply)
        self.assertIsNone(context['review']['simulation_candidate'])


if __name__=='__main__':
    unittest.main()
