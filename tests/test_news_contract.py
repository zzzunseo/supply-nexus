from copy import deepcopy
import unittest
from news.schema import validate_event, assess_event


def example():
    def reported(value):
        return {'value': value, 'basis': 'reported',
                'evidence': [{'source_id': 's1', 'quote': '테스트용 가상 기사 근거 문장'}]}
    return {
        'schema_version': 1, 'event_id': 'fictional-001', 'headline': '가상 공급 중단 테스트',
        'published_at': '2026-10-26T09:00:00+09:00',
        'occurred_at': '2026-10-25T09:00:00+09:00', 'event_type': 'supply_disruption',
        'sources': [{'id': 's1', 'url': 'https://example.com/fictional', 'title': '가상 기사',
                     'published_at': '2026-10-26T09:00:00+09:00'}],
        'claims': {'targets': reported(['registered']), 'rate': reported(.5),
                   'duration_days': reported(30), 'impact_scope': reported('whole_entity')},
    }


class NewsContractTests(unittest.TestCase):
    def test_validated_record_is_detached_and_keeps_provenance(self):
        record = example()
        before = deepcopy(record)
        copied = validate_event(record)
        self.assertEqual(record, before)
        copied['claims']['targets']['value'].append('other')
        self.assertEqual(record, before)
        result = assess_event(record, {'registered'}, reviewed=True)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['candidate']['rate'], .5)
        self.assertEqual(result['event']['sources'], record['sources'])

    def test_unreviewed_input_never_produces_a_candidate(self):
        result = assess_event(example(), {'registered'})
        self.assertEqual(result['status'], 'hold')
        self.assertIsNone(result['candidate'])

    def test_unknown_values_never_get_default_loss_or_duration(self):
        for field in ('targets', 'rate', 'duration_days', 'impact_scope'):
            record = example()
            record['claims'][field] = {'value': None, 'basis': 'unknown', 'evidence': []}
            before = deepcopy(record)
            result = assess_event(record, {'registered'}, reviewed=True)
            self.assertEqual(result['status'], 'hold')
            self.assertIsNone(result['candidate'])
            self.assertEqual(record, before)

    def test_each_assumption_needs_explicit_external_approval(self):
        record = example()
        record['claims']['rate'] = {'value': .5, 'basis': 'assumption', 'evidence': []}
        record['claims']['duration_days'] = {'value': 30, 'basis': 'assumption', 'evidence': []}
        self.assertEqual(assess_event(record, {'registered'}, reviewed=True)['status'], 'hold')
        self.assertEqual(assess_event(record, {'registered'}, reviewed=True,
                                    approved_assumptions={'rate'})['status'], 'hold')
        result = assess_event(record, {'registered'}, reviewed=True,
                              approved_assumptions={'rate', 'duration_days'})
        self.assertEqual(result['status'], 'ready')
        self.assertIn('승인된 가정', result['candidate']['note'])

    def test_payload_cannot_approve_itself(self):
        record = example()
        record['reviewed'] = True
        self.assertEqual(assess_event(record, {'registered'})['status'], 'reject')

    def test_missing_quotes_and_unknown_source_references_are_rejected(self):
        for evidence in ([], [{'source_id': 'missing', 'quote': '문장'}],
                         [{'source_id': 's1', 'quote': ''}]):
            record = example()
            record['claims']['rate']['evidence'] = evidence
            self.assertEqual(assess_event(record, {'registered'}, reviewed=True)['status'], 'reject')

    def test_unregistered_targets_and_facility_or_country_scope_are_held(self):
        self.assertEqual(assess_event(example(), set(), reviewed=True)['status'], 'hold')
        for scope in ('facility', 'country', 'unknown'):
            record = example()
            record['claims']['impact_scope']['value'] = scope
            self.assertEqual(assess_event(record, {'registered'}, reviewed=True)['status'], 'hold')

    def test_logistics_scope_and_recovery_cannot_become_whole_company_shutdown(self):
        record = example()
        record['event_type'] = 'logistics_disruption'
        self.assertEqual(assess_event(record, {'registered'}, reviewed=True)['status'], 'hold')
        record['claims']['impact_scope']['value'] = 'registered_route'
        self.assertEqual(assess_event(record, {'registered'}, reviewed=True)['status'], 'ready')
        for kind in ('recovery', 'other'):
            record['event_type'] = kind
            self.assertEqual(assess_event(record, {'registered'}, reviewed=True)['status'], 'hold')

    def test_publication_time_does_not_replace_missing_event_time(self):
        record = example()
        record['occurred_at'] = None
        self.assertEqual(assess_event(record, {'registered'}, reviewed=True)['status'], 'hold')
        self.assertIsNone(record['occurred_at'])

    def test_numeric_values_are_strict_and_finite(self):
        for field, values in {'rate': [True, -.1, 1.01, float('nan'), float('inf'), '0.5'],
                              'duration_days': [True, 0, 366, 30.0, '30']}.items():
            for value in values:
                record = example()
                record['claims'][field]['value'] = value
                self.assertEqual(assess_event(record, {'registered'}, reviewed=True)['status'], 'reject')

    def test_tariff_uses_separate_rate_limit_and_engine_kind(self):
        record = example()
        record['event_type'] = 'tariff'
        record['claims']['rate']['value'] = 2
        result = assess_event(record, {'registered'}, reviewed=True)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['candidate']['kind'], 'tariff')
        record['claims']['rate']['value'] = 5.01
        self.assertEqual(assess_event(record, {'registered'}, reviewed=True)['status'], 'reject')

    def test_bad_source_url_timezone_and_duplicate_ids_are_rejected(self):
        mutations = [lambda r: r['sources'][0].update(url='javascript:alert(1)'),
                     lambda r: r.update(published_at='2026-10-26T09:00:00'),
                     lambda r: r['sources'].append(deepcopy(r['sources'][0])),
                     lambda r: r.update(event_type=['supply_disruption'])]
        for mutate in mutations:
            record = example()
            mutate(record)
            self.assertEqual(assess_event(record, {'registered'}, reviewed=True)['status'], 'reject')
