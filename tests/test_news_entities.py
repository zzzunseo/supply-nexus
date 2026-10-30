from copy import deepcopy
import unittest

from news.entities import build_alias_index, normalize_name, resolve_name, assess_named_event
from resilience_data import build_network
from test_news_contract import example


class NewsEntityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()
        cls.index = build_alias_index(cls.network)

    def event(self, names, logistics=False):
        event = example()
        event['claims']['targets']['value'] = names
        if logistics:
            event['event_type'] = 'logistics_disruption'
            event['claims']['impact_scope']['value'] = 'registered_route'
        return event

    def test_company_names_aliases_and_registered_ids(self):
        for name, target in [('삼성전자', 'samsung'), ('TSMC', 'tsmc'),
                             ('동진쎄미켐', 'dongjin'), ('TOK', 'tok'), ('shinetsu', 'shinetsu')]:
            with self.subTest(name=name):
                self.assertEqual(resolve_name(name, self.index)['target_id'], target)

    def test_unicode_case_and_whitespace_normalization(self):
        self.assertEqual(normalize_name('  Ａｉｒ   Ｌｉｑｕｉｄｅ  '), 'air liquide')
        self.assertEqual(resolve_name('  ＴＳＭＣ ', self.index)['target_id'], 'tsmc')
        self.assertEqual(resolve_name('AIR  LIQUIDE', self.index)['target_id'], 'airliquide')

    def test_ports_straits_and_detours_use_their_own_ids(self):
        for name, target in [('말라카해협', 'logistics:malacca'), ('kaohsiung', 'logistics:kaohsiung'),
                             ('수에즈 운하', 'logistics:suez'), ('기룽항', 'logistics:keelung')]:
            self.assertEqual(resolve_name(name, self.index)['target_id'], target)

    def test_all_supported_registered_ids_resolve_to_themselves(self):
        for key, entity in self.network['entities'].items():
            if entity['kind'] in {'company', 'material', 'product', 'resource', 'logistics'}:
                self.assertEqual(resolve_name(key, self.index)['target_id'], key)

    def test_shared_material_is_ambiguous_and_never_expands(self):
        result = resolve_name('포토레지스트', self.index)
        self.assertEqual(result['status'], 'ambiguous')
        self.assertIsNone(result['target_id'])
        self.assertGreater(len(result['candidates']), 1)
        assessed = assess_named_event(self.event(['포토레지스트']), self.network, reviewed=True)
        self.assertEqual(assessed['status'], 'hold')
        self.assertIsNone(assessed['candidate'])

    def test_unknown_country_facility_and_sentence_do_not_become_company(self):
        for name in ('미등록기업', '일본', 'TSMC 가오슝 공장', 'TSMC 공급이 중단됐다', '', 'TSM'):
            self.assertEqual(resolve_name(name, self.index)['status'], 'unknown')

    def test_mixed_known_unknown_targets_are_held_as_a_whole(self):
        result = assess_named_event(self.event(['TSMC', '미등록기업']), self.network, reviewed=True)
        self.assertEqual(result['status'], 'hold')
        self.assertIsNone(result['candidate'])
        self.assertEqual(len(result['mapping']), 2)

    def test_company_aliases_produce_candidate_but_keep_original_evidence(self):
        event = self.event(['삼성전자', 'Samsung Electronics'])
        before = deepcopy(event)
        result = assess_named_event(event, self.network, reviewed=True)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['candidate']['targets'], ['samsung'])
        self.assertEqual(result['original_event'], before)
        self.assertEqual(result['event']['claims']['targets']['evidence'],
                         before['claims']['targets']['evidence'])
        self.assertEqual(event, before)

    def test_logistics_candidate_and_mismatched_event_types(self):
        result = assess_named_event(self.event(['말라카 해협'], True), self.network, reviewed=True)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['candidate']['targets'], ['logistics:malacca'])
        for event in (self.event(['TSMC'], True), self.event(['말라카 해협'])):
            self.assertEqual(assess_named_event(event, self.network, reviewed=True)['status'], 'hold')

    def test_review_assumption_and_scope_gates_still_apply(self):
        event = self.event(['TSMC'])
        self.assertEqual(assess_named_event(event, self.network)['status'], 'hold')
        event['claims']['rate'] = {'value': .5, 'basis': 'assumption', 'evidence': []}
        self.assertEqual(assess_named_event(event, self.network, reviewed=True)['status'], 'hold')
        self.assertEqual(assess_named_event(event, self.network, reviewed=True,
                         approved_assumptions={'rate'})['status'], 'ready')
        event['claims']['impact_scope']['value'] = 'facility'
        self.assertEqual(assess_named_event(event, self.network, reviewed=True,
                         approved_assumptions={'rate'})['status'], 'hold')

    def test_unknown_targets_and_bad_contract_still_hold_or_reject(self):
        event = self.event(['TSMC'])
        event['claims']['targets'] = {'value': None, 'basis': 'unknown', 'evidence': []}
        self.assertEqual(assess_named_event(event, self.network, reviewed=True)['status'], 'hold')
        self.assertEqual(assess_named_event({}, self.network)['status'], 'reject')

    def test_network_index_and_outputs_do_not_share_mutable_data(self):
        before = deepcopy(self.network)
        index = build_alias_index(self.network)
        result = resolve_name('TSMC', index)
        result['candidates'][0]['name'] = 'changed'
        self.assertEqual(resolve_name('TSMC', index)['candidates'][0]['name'], 'TSMC')
        self.assertEqual(self.network, before)
        self.assertFalse(any(target['kind'] == 'reserve' for targets in index.values() for target in targets))

    def test_sorting_determinism_and_alias_collisions(self):
        reversed_network = {'entities': dict(reversed(list(self.network['entities'].items())))}
        self.assertEqual(build_alias_index(reversed_network), self.index)
        network = {'entities': {'a': {'name': 'A', 'kind': 'company', 'aliases': ['Ｘ']},
                                'b': {'name': 'B', 'kind': 'company', 'aliases': ['x']}}}
        result = resolve_name('X', build_alias_index(network))
        self.assertEqual(result['status'], 'ambiguous')
        self.assertEqual([item['id'] for item in result['candidates']], ['a', 'b'])
