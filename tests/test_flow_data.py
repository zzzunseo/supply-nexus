from copy import deepcopy
import json
import unittest

from flow_data import build_flow
from resilience_data import build_network
from simulation.resilience import calculate_supply_shock, interpret_issue


def cards_by_node(flow, column):
    return {
        card['node_id']: card
        for item in flow['columns'] if item['id'] == column
        for card in item['cards']
    }


class FlowDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = build_network()
        cls.normal = calculate_supply_shock(cls.network)

    def test_default_is_photo_with_only_its_materials_and_suppliers(self):
        flow = build_flow(self.network, self.normal)
        self.assertEqual(flow['process'], '포토')
        self.assertEqual(
            [column['name'] for column in flow['columns']],
            ['공급 기업', '소재', '공정', '영향 기업'],
        )
        self.assertEqual(
            set(cards_by_node(flow, 'suppliers')),
            {'jsr', 'tok', 'fujifilm', 'asml', 'temc', 'hoya'},
        )
        self.assertEqual(
            set(cards_by_node(flow, 'materials')),
            {'supply:jsr:photoresist', 'supply:tok:photoresist',
             'supply:fujifilm:developer', 'supply:asml:lithography',
             'upstream:neon', 'raw:neon', 'upstream:mask', 'raw:mask'},
        )
        self.assertEqual(set(cards_by_node(flow, 'recipients')), {'samsung', 'tsmc'})

    def test_each_process_includes_exactly_its_scoped_delivery_sources(self):
        for process in self.network['processes']:
            with self.subTest(process=process):
                flow = build_flow(self.network, self.normal, process)
                material_ids = set(cards_by_node(flow, 'materials'))
                displayed = {edge['source_edge_id'] for edge in flow['connections']}
                expected = set()
                for edge in self.network['visual_edges']:
                    if process not in edge['processes'] or edge['scope'] != 'core':
                        continue
                    source = self.network['nodes'][edge['from']]
                    target = self.network['nodes'][edge['to']]
                    if source['kind'] not in {'product', 'material', 'resource'} or target['kind'] != 'company':
                        continue
                    expected.add(edge.get('backbone_id', edge['id']))
                    self.assertIn(source['id'], material_ids)
                actual = {
                    edge['source_edge_id'] for edge in flow['connections']
                    if edge['to'].startswith('processes:')
                }
                self.assertEqual(actual, expected)
                self.assertTrue(expected <= displayed)
                self.assertTrue(all(
                    card['node_id'].endswith(':' + process)
                    for card in cards_by_node(flow, 'processes').values()
                ))

    def test_photo_and_etch_do_not_leak_materials_into_each_other(self):
        photo = cards_by_node(build_flow(self.network, self.normal, '포토'), 'materials')
        etch = cards_by_node(build_flow(self.network, self.normal, '식각'), 'materials')
        self.assertNotIn('supply:lam:etch-tool', photo)
        self.assertNotIn('upstream:fluorspar', photo)
        self.assertIn('supply:lam:etch-tool', etch)
        self.assertIn('upstream:fluorspar', etch)
        self.assertNotIn('supply:jsr:photoresist', etch)
        self.assertNotIn('upstream:neon', etch)

    def test_all_edges_resolve_and_every_card_reaches_an_affected_company(self):
        for process in self.network['processes']:
            with self.subTest(process=process):
                flow = build_flow(self.network, self.normal, process)
                cards = [card for column in flow['columns'] for card in column['cards']]
                ids = {card['id'] for card in cards}
                self.assertEqual(len(ids), len(cards))
                adjacency = {key: set() for key in ids}
                for edge in flow['connections']:
                    self.assertIn(edge['from'], ids)
                    self.assertIn(edge['to'], ids)
                    adjacency[edge['from']].add(edge['to'])
                sinks = {card['id'] for card in cards_by_node(flow, 'recipients').values()}
                for key in ids:
                    pending = [key]
                    seen = set()
                    while pending:
                        node = pending.pop()
                        if node in seen:
                            continue
                        seen.add(node)
                        pending.extend(adjacency[node] - seen)
                    self.assertTrue(seen & sinks, key)

    def test_unconfirmed_and_collaboration_stay_excluded_but_supply_stays_active(self):
        flow = build_flow(self.network, self.normal)
        edges = {edge['source_edge_id']: edge for edge in flow['connections']}
        for key in ('photoresist:tok>samsung', 'photoresist:jsr>samsung'):
            with self.subTest(relationship=key):
                self.assertTrue(edges[key]['excluded'])
                self.assertEqual(edges[key]['status'], 'excluded')
                self.assertIsNone(edges[key]['reduction_pct'])
                self.assertTrue(edges[key]['exclusion_reason'])
                self.assertTrue(edges[key]['assumption'])
        included = edges['photoresist:tok>tsmc']
        self.assertFalse(included['excluded'])
        self.assertEqual(included['status'], 'normal')
        self.assertEqual(included['reduction_pct'], 0)

    def test_all_original_exclusions_are_preserved_in_every_process(self):
        for process in self.network['processes']:
            flow = build_flow(self.network, self.normal, process)
            edges = {edge['source_edge_id']: edge for edge in flow['connections']}
            for original in self.network['backbone']:
                if process not in original['processes']:
                    continue
                decision = self.network['relationship_decisions'][original['id']]
                self.assertEqual(edges[original['id']]['excluded'], not decision['included'] or next(i for i in self.network['original']['items'] if i['id']==original['item_id'])['category']=='equipment')

    def test_assumed_shares_are_not_assigned_to_non_share_links(self):
        flow = build_flow(self.network, self.normal)
        edges = {edge['source_edge_id']: edge for edge in flow['connections']}
        self.assertTrue(edges['developer:fujifilm>tsmc']['assumption'])
        self.assertFalse(edges['product:supply:fujifilm:developer']['assumption'])
        self.assertFalse(edges['upstream:86']['assumption'])
        self.assertTrue(all(not edge['assumption'] for edge in flow['connections']
                            if edge['to'].startswith('recipients:')))

    def test_optional_material_scope_is_included_only_when_calculated(self):
        scope = 'material:pgmea'
        result = calculate_supply_shock(self.network, scopes=[scope])
        flow = build_flow(self.network, result)
        self.assertIn('extended:pgmea:kanto', cards_by_node(flow, 'materials'))
        self.assertNotIn('extended:ipa:kanto', cards_by_node(flow, 'materials'))
        self.assertNotIn('extended:pgmea:kanto', cards_by_node(
            build_flow(self.network, self.normal), 'materials'))
        links = [edge for edge in flow['connections']
                 if edge['from'] == 'materials:extended:pgmea:kanto'
                 and edge['to'].startswith('processes:')]
        self.assertEqual(len(links), 2)
        self.assertTrue(all(edge['assumption'] for edge in links))

    def test_upstream_materials_keep_the_wafer_dependency_chain_connected(self):
        flow = build_flow(self.network, self.normal, '웨이퍼 제조')
        suppliers = cards_by_node(flow, 'suppliers')
        materials = cards_by_node(flow, 'materials')
        self.assertIn('sibelco', suppliers)
        self.assertIn('wacker', suppliers)
        self.assertIn('raw:quartz', materials)
        self.assertIn('upstream:quartz', materials)
        self.assertTrue(any(
            edge['from'] == 'materials:upstream:quartz'
            and edge['to'] == 'materials:supply:shinetsu:polished-wafer'
            for edge in flow['connections']
        ))

    def test_no_selection_or_missing_selection_preserves_the_entire_flow(self):
        base = build_flow(self.network, self.normal)
        self.assertIsNone(base['selected'])
        self.assertEqual(base, build_flow(self.network, self.normal, selected='not-registered'))
        self.assertEqual(base, build_flow(self.network, self.normal, selected='lam'))
        company = build_flow(self.network, self.normal, selected='tsmc')
        card = build_flow(self.network, self.normal, selected='recipients:tsmc')
        self.assertEqual(company, card)
        self.assertEqual(company['selected'], 'tsmc')
        self.assertEqual(company['columns'], base['columns'])
        self.assertEqual(company['connections'], base['connections'])
        material = build_flow(self.network, self.normal, selected='supply:jsr:photoresist')
        self.assertEqual(material['selected'], 'supply:jsr:photoresist')

    def test_missing_result_is_unknown_instead_of_imputed_normal(self):
        result = deepcopy(self.normal)
        del result['nodes']['supply:jsr:photoresist']
        card = cards_by_node(build_flow(self.network, result), 'materials')['supply:jsr:photoresist']
        self.assertEqual(card['status'], 'unknown')
        self.assertIsNone(card['reduction_pct'])

    def test_recipient_status_uses_selected_operation_not_global_bottleneck(self):
        result = deepcopy(self.normal)
        operation = self.network['operations']['tsmc', '포토']
        result['nodes'][operation]['effective'] = .35
        result['nodes']['tsmc']['effective'] = 1
        flow = build_flow(self.network, result)
        recipient = cards_by_node(flow, 'recipients')['tsmc']
        self.assertEqual(recipient['result_node_id'], operation)
        self.assertEqual(recipient['reduction_pct'], 65)
        self.assertEqual(recipient['status'], 'reduced')
        self.assertEqual(cards_by_node(flow, 'recipients')['samsung']['reduction_pct'], 0)

    def test_route_status_reads_delivery_result_not_unrelated_mix_average(self):
        result = deepcopy(self.normal)
        target = 'route:developer:fujifilm>tsmc'
        result['nodes'][target]['effective'] = .2
        result['nodes']['supply:fujifilm:developer']['effective'] = 1
        flow = build_flow(self.network, result)
        edge = next(edge for edge in flow['connections']
                    if edge['source_edge_id'] == 'developer:fujifilm>tsmc')
        self.assertEqual(edge['result_node_id'], target)
        self.assertEqual(edge['reduction_pct'], 80)

    def test_inputs_are_unchanged_and_output_is_detached_and_json_serializable(self):
        network = deepcopy(self.network)
        result = deepcopy(self.normal)
        before_network = deepcopy(network)
        before_result = deepcopy(result)
        flow = build_flow(network, result)
        self.assertEqual(network, before_network)
        self.assertEqual(result, before_result)
        self.assertEqual(flow, build_flow(network, result))
        json.dumps(flow, ensure_ascii=False, allow_nan=False)
        flow['columns'][0]['cards'][0]['name'] = 'changed'
        flow['connections'][0]['status'] = 'changed'
        self.assertEqual(network, before_network)
        self.assertEqual(result, before_result)

    def test_requested_scenarios_build_data_with_existing_calculation_values(self):
        cases = (
            ('일본 포토레지스트 공급 100% 중단 30일', ('포토',)),
            ('말라카 해협 봉쇄 30일', ('포토', '식각')),
        )
        for text, processes in cases:
            event = interpret_issue(text, self.network)
            result = calculate_supply_shock(self.network, [event], 30)
            for process in processes:
                with self.subTest(issue=text, process=process):
                    flow = build_flow(self.network, result, process)
                    self.assertTrue(flow['connections'])
                    for card in cards_by_node(flow, 'processes').values():
                        effective = result['nodes'][card['result_node_id']]['effective']
                        self.assertAlmostEqual(card['reduction_pct'], (1 - effective) * 100)
                    if '포토레지스트' in text:
                        pr = cards_by_node(flow, 'materials')['supply:jsr:photoresist']
                        self.assertEqual(pr['status'], 'reduced')
                        self.assertEqual(result['first_hit']['포토'], 15)
                        self.assertEqual(result['scores']['포토'], 60)

    def test_invalid_process_is_explicit_and_none_uses_default(self):
        with self.assertRaisesRegex(ValueError, '등록되지 않은 공정'):
            build_flow(self.network, self.normal, '없는 공정')
        self.assertEqual(build_flow(self.network, self.normal, None),
                         build_flow(self.network, self.normal))


if __name__ == '__main__':
    unittest.main()
