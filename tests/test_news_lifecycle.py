from copy import deepcopy
import json
import unittest

from news.lifecycle import empty_registry, transition, active_candidates
from resilience_data import build_network
from test_news_contract import example


class NewsLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()

    def event(self, key='article-1', rate=.5, occurred='2026-10-25T09:00:00+09:00'):
        event = example()
        event['event_id'] = key
        event['claims']['targets']['value'] = ['TSMC']
        event['claims']['rate']['value'] = rate
        event['occurred_at'] = occurred
        return event

    def add(self, registry=None, event=None, **options):
        return transition(empty_registry() if registry is None else registry,
                          self.event() if event is None else event, self.network,
                          reviewed=True, **options)

    def initial(self):
        return self.add()['registry']

    def update(self, registry, event, operation, revision=1):
        return self.add(registry, event, operation=operation,
                        incident_id='article-1', expected_revision=revision)

    def recovery(self, key='recovery-1'):
        event = self.event(key, rate=0, occurred='2026-10-26T09:00:00+09:00')
        event['event_type'] = 'recovery'
        return event

    def test_new_incident_has_one_active_candidate(self):
        result = self.add()
        self.assertEqual(result['status'], 'accepted')
        record = result['registry']['incidents']['article-1']
        self.assertEqual(record['revision'], 1)
        self.assertEqual(record['status'], 'active')
        self.assertEqual(len(active_candidates(result['registry'])), 1)

    def test_exact_retry_is_idempotent_even_after_later_revision(self):
        original = self.event()
        registry = self.initial()
        registry = self.update(registry, self.event('article-2', rate=.7), 'correct')['registry']
        retry = self.add(registry, original)
        self.assertEqual(retry['status'], 'duplicate')
        self.assertEqual(retry['registry'], registry)

    def test_same_input_id_changed_content_or_operation_is_held(self):
        registry = self.initial()
        self.assertEqual(self.add(registry, self.event(rate=.9))['status'], 'hold')
        self.assertEqual(self.update(registry, self.event(), 'report')['status'], 'hold')

    def test_possible_duplicate_new_id_is_held_even_with_changed_rate(self):
        for rate in (.5, .9):
            result = self.add(self.initial(), self.event('article-2', rate))
            self.assertEqual(result['status'], 'hold')
            self.assertEqual(len(active_candidates(result['registry'])), 1)

    def test_additional_report_keeps_one_effect_and_all_sources_in_history(self):
        event = self.event('article-2')
        event['sources'][0]['url'] = 'https://example.com/second-fictional-report'
        registry = self.initial()
        result = self.update(registry, event, 'report')
        self.assertEqual(result['status'], 'accepted')
        record = result['registry']['incidents']['article-1']
        self.assertEqual(len(record['history']), 2)
        self.assertEqual(record['history'][1]['event'], event)
        self.assertEqual(record['candidate'], registry['incidents']['article-1']['candidate'])
        self.assertEqual(len(active_candidates(result['registry'])), 1)

    def test_conflicting_report_needs_correction(self):
        result = self.update(self.initial(), self.event('article-2', rate=.9), 'report')
        self.assertEqual(result['status'], 'hold')
        self.assertEqual(result['registry'], self.initial())

    def test_correction_replaces_rate_and_duration_without_adding_effect(self):
        event = self.event('article-2', rate=.8)
        event['claims']['duration_days']['value'] = 10
        result = self.update(self.initial(), event, 'correct')
        self.assertEqual(result['status'], 'accepted')
        candidates = active_candidates(result['registry'])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]['candidate']['rate'], .8)
        self.assertEqual(candidates[0]['candidate']['days'], 10)
        self.assertEqual(candidates[0]['revision'], 2)

    def test_missing_target_id_wrong_revision_and_unknown_incident_hold(self):
        registry = self.initial()
        event = self.event('article-2')
        for revision in (None, 0, True, 2):
            self.assertEqual(self.update(registry, event, 'correct', revision)['status'], 'hold')
        self.assertEqual(self.add(registry, event, operation='correct')['status'], 'hold')
        self.assertEqual(self.add(registry, event, operation='correct',
                         incident_id='missing', expected_revision=1)['status'], 'hold')

    def test_scope_or_target_changes_do_not_replace_unrelated_incident(self):
        event = self.event('article-2')
        event['claims']['targets']['value'] = ['삼성전자']
        self.assertEqual(self.update(self.initial(), event, 'correct')['status'], 'hold')
        event['claims']['targets']['value'] = ['TSMC']
        event['claims']['impact_scope']['value'] = 'registered_route'
        self.assertEqual(self.update(self.initial(), event, 'correct')['status'], 'hold')

    def test_recovery_removes_only_linked_incident(self):
        registry = self.add(self.initial(), self.event('other-incident', .3,
                            '2026-10-24T09:00:00+09:00'))['registry']
        result = self.update(registry, self.recovery(), 'recover')
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(result['registry']['incidents']['article-1']['status'], 'recovered')
        candidates = active_candidates(result['registry'])
        self.assertEqual([item['incident_id'] for item in candidates], ['other-incident'])
        self.assertEqual(candidates[0]['candidate']['rate'], .3)

    def test_partial_recovery_requires_correction_and_does_not_clear(self):
        event = self.recovery()
        event['claims']['rate']['value'] = .2
        self.assertEqual(self.update(self.initial(), event, 'recover')['status'], 'hold')
        event['event_type'] = 'supply_disruption'
        self.assertEqual(self.update(self.initial(), event, 'correct')['status'], 'accepted')

    def test_recovery_requires_review_and_known_claims(self):
        registry = self.initial()
        event = self.recovery()
        result = transition(registry, event, self.network, operation='recover',
                            incident_id='article-1', expected_revision=1)
        self.assertEqual(result['status'], 'hold')
        event['claims']['rate'] = {'value': None, 'basis': 'unknown', 'evidence': []}
        self.assertEqual(self.update(registry, event, 'recover')['status'], 'hold')

    def test_logistics_recovery_uses_original_kind_for_validation(self):
        event = self.event()
        event['event_type'] = 'logistics_disruption'
        event['claims']['targets']['value'] = ['말라카 해협']
        event['claims']['impact_scope']['value'] = 'registered_route'
        registry = self.add(event=event)['registry']
        recovery = deepcopy(event)
        recovery.update(event_id='recovery-1', event_type='recovery')
        recovery['claims']['rate']['value'] = 0
        result = self.update(registry, recovery, 'recover')
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(active_candidates(result['registry']), [])

    def test_recovered_incident_cannot_reopen_or_be_readded_as_same_onset(self):
        registry = self.update(self.initial(), self.recovery(), 'recover')['registry']
        self.assertEqual(self.update(registry, self.event('new-report'), 'correct', 2)['status'], 'hold')
        self.assertEqual(self.add(registry, self.event('new-report'))['status'], 'hold')

    def test_stale_publication_and_recovery_before_onset_hold(self):
        event = self.event('article-2')
        event['published_at'] = '2026-10-25T09:00:00+09:00'
        self.assertEqual(self.update(self.initial(), event, 'correct')['status'], 'hold')
        event = self.recovery()
        event['occurred_at'] = '2026-10-24T09:00:00+09:00'
        self.assertEqual(self.update(self.initial(), event, 'recover')['status'], 'hold')

    def test_timezone_equivalent_onset_detects_possible_duplicate(self):
        event = self.event('article-2', occurred='2026-10-25T00:00:00Z')
        self.assertEqual(self.add(self.initial(), event)['status'], 'hold')

    def test_correction_keeps_previous_identity_for_duplicate_detection(self):
        event = self.event('correction-1', occurred='2026-10-25T10:00:00+09:00')
        registry = self.update(self.initial(), event, 'correct')['registry']
        self.assertEqual(self.add(registry, self.event('late-copy'))['status'], 'hold')

    def test_unreviewed_and_unapproved_assumptions_do_not_enter_registry(self):
        event = self.event()
        registry = empty_registry()
        self.assertEqual(transition(registry, event, self.network)['registry'], registry)
        event['claims']['rate'] = {'value': .5, 'basis': 'assumption', 'evidence': []}
        self.assertEqual(self.add(event=event)['status'], 'hold')
        self.assertEqual(self.add(event=event, approved_assumptions={'rate'})['status'], 'accepted')

    def test_input_and_returned_candidates_do_not_share_data(self):
        registry = self.initial()
        event = self.event('article-2', rate=.9)
        before_registry = deepcopy(registry)
        before_event = deepcopy(event)
        before_network = deepcopy(self.network)
        result = self.update(registry, event, 'correct')
        candidates = active_candidates(result['registry'])
        candidates[0]['candidate']['targets'].clear()
        self.assertEqual(len(active_candidates(result['registry'])[0]['candidate']['targets']), 1)
        self.assertEqual(registry, before_registry)
        self.assertEqual(event, before_event)
        self.assertEqual(self.network, before_network)

    def test_json_roundtrip_preserves_retry_and_identity_checks(self):
        registry = json.loads(json.dumps(self.initial()))
        self.assertEqual(self.add(registry)['status'], 'duplicate')
        self.assertEqual(self.add(registry, self.event('copy'))['status'], 'hold')

    def test_invalid_payload_and_control_arguments_are_rejected(self):
        self.assertEqual(self.add(event={})['status'], 'reject')
        for operation in ('unsupported', []):
            self.assertEqual(self.add(operation=operation)['status'], 'reject')
        self.assertEqual(self.add(approved_assumptions={'arbitrary'})['status'], 'reject')
        self.assertEqual(self.add(incident_id='not-allowed')['status'], 'reject')
