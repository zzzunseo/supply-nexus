from copy import deepcopy
from pathlib import Path
import unittest

from simulation.resilience import calculate_supply_shock
from simulation.logistics import validate_route_settings
from resilience_data import build_network
from resilience_globe import build_globe, COLORS
from ui.logistics import apply_saved_settings


def fixture(count=1, delay=2, capacity=1., sea=1.):
    def node(**extra):
        return dict(requires=[], inventory_days=0., alt_vendor=None,
                    alt_capacity=0., scope='core', **extra)
    nodes = dict(source=node(), cp=node(kind='logistics'), alternate=node(kind='logistics'),
                 cp2=node(kind='logistics'), alternate2=node(kind='logistics'))
    routes, settings = {}, {}
    for i in range(count):
        key = 'delivery' + str(i)
        nodes[key] = node(kind='transport', logistics_via=['cp'], requires_unused=[])
        nodes[key]['requires'] = ['source', 'cp']
        routes[key] = dict(source='source', target=key, via=['cp'], scope='core')
        settings[key] = dict(sea_fraction=sea, inventory_days=0.)
    return dict(nodes=nodes, logistics={'cp': {}, 'cp2': {}}, logistics_routes=routes,
        route_settings=settings, process_outputs={'p': list(routes)},
        port_detours={'cp': dict(enabled=True, via=['alternate'], max_fraction=.6,
                               capacity_units=capacity, extra_days=delay, cost_rate=.2)})


def event(target='cp', days=10, rate=1.):
    return dict(kind='supply', targets=[target], rate=rate, days=days)


def run(n, events=None, days=5, inventory=False):
    return calculate_supply_shock(n, events or [event()], days, use_inventory=inventory, use_bypass=False)


class PortDetourTests(unittest.TestCase):
    def test_extra_transit_days_and_cost(self):
        r = run(fixture(), days=4)
        self.assertEqual([row['p'] for row in r['timeline']], [0, 0, 60, 60])
        self.assertAlmostEqual(r['logistics']['pending'], 1.2)
        self.assertAlmostEqual(r['logistics']['detour_freight_index'], 120)

    def test_zero_delay_and_vendor_switch_independence(self):
        r = run(fixture(delay=0), days=1)
        self.assertEqual(r['overall'], 60)
        self.assertEqual(r['nodes']['delivery0']['backup'], 0)
        self.assertEqual(r['logistics']['pending'], 0)

    def test_shared_capacity_is_not_duplicated(self):
        r = run(fixture(count=2, delay=0, capacity=.6), days=1)
        for value in r['logistics']['routes'].values():
            self.assertAlmostEqual(value['dispatched'], .3)
        self.assertAlmostEqual(r['logistics']['totals']['dispatched'], .6)

    def test_capacity_shared_across_dag_layers(self):
        n = fixture(count=2, delay=0, capacity=.6)
        n['nodes']['middle'] = dict(n['nodes']['source'], requires=['source'])
        n['nodes']['delivery1']['requires'][0] = 'middle'
        n['logistics_routes']['delivery1']['source'] = 'middle'
        r = run(n, days=1)
        self.assertAlmostEqual(r['logistics']['totals']['dispatched'], .6)

    def test_secondary_port_closure_prevents_departure(self):
        r = run(fixture(), [event(), event('alternate')])
        self.assertEqual(r['overall'], 0)
        self.assertEqual(r['logistics']['totals']['dispatched'], 0)
        self.assertIsNone(r['logistics']['detour_freight_index'])

    def test_partial_closure_only_fills_actual_deficit(self):
        n = fixture(delay=0)
        r = run(n, [event(rate=.3)], days=1)
        self.assertEqual(r['overall'], 100)
        self.assertAlmostEqual(r['logistics']['routes']['delivery0']['dispatched'], .3)

    def test_sea_share_leaves_other_transport_unaffected(self):
        r = run(fixture(sea=.5), days=3)
        self.assertEqual([row['p'] for row in r['timeline']], [50, 50, 80])

    def test_no_detour_of_supply_that_does_not_exist(self):
        r = run(fixture(), [event(), event('source')])
        self.assertEqual(r['overall'], 0)
        self.assertEqual(r['logistics']['totals']['dispatched'], 0)

    def test_recovery_caps_deliveries_and_reports_surplus(self):
        r = run(fixture(), [event(days=1)], days=3)
        self.assertEqual([row['p'] for row in r['timeline']], [0, 100, 100])
        self.assertAlmostEqual(r['logistics']['totals']['surplus'], .6)
        self.assertEqual(r['logistics']['totals']['delivered'], 0)

    def test_inventory_consumed_once_and_conservation(self):
        n = fixture()
        n['route_settings']['delivery0']['inventory_days'] = 1.
        n['nodes']['delivery0']['inventory_days'] = 1.
        r = run(n, days=5, inventory=True)
        self.assertEqual([row['p'] for row in r['timeline']], [100, 0, 60, 60, 60])
        self.assertEqual(r['nodes']['delivery0']['stock_remaining'], 0)
        t = r['logistics']['totals']
        self.assertAlmostEqual(t['dispatched'], t['arrived'] + r['logistics']['pending'])
        self.assertAlmostEqual(t['arrived'], t['delivered'] + t['surplus'])

    def test_two_blockages_require_both_detours_add_delay_and_cost(self):
        n = fixture(delay=1)
        n['nodes']['delivery0']['requires'].append('cp2')
        n['nodes']['delivery0']['logistics_via'].append('cp2')
        n['logistics_routes']['delivery0']['via'].append('cp2')
        n['port_detours']['cp2'] = dict(n['port_detours']['cp'], via=['alternate2'], extra_days=2, cost_rate=.3)
        r = run(n, [event(), event('cp2')], days=4)
        self.assertEqual([row['p'] for row in r['timeline']], [0, 0, 0, 60])
        self.assertAlmostEqual(r['logistics']['detour_freight_index'], 150)
        n['port_detours']['cp2']['enabled'] = False
        self.assertEqual(run(n, [event(), event('cp2')])['overall'], 0)

    def test_remaining_partial_chokepoint_limits_detour_without_reusing_capacity(self):
        n = fixture(delay=0)
        n['nodes']['delivery0']['requires'].append('cp2')
        n['nodes']['delivery0']['logistics_via'].append('cp2')
        n['logistics_routes']['delivery0']['via'].append('cp2')
        # Only cp is bypassed. The remaining cp2 limits total transport to 50%.
        r = run(n, [event(), event('cp2', rate=.5)], days=1)
        self.assertEqual(r['overall'], 50)
        r = run(n, [event(rate=.75), event('cp2', rate=.5)], days=1)
        self.assertEqual(r['overall'], 50)

    def test_no_event_no_dispatch_and_no_mutation(self):
        n = fixture()
        before = deepcopy(n)
        r = calculate_supply_shock(n, [], 5)
        self.assertEqual(r['overall'], 100)
        self.assertEqual(r['logistics']['totals']['dispatched'], 0)
        self.assertEqual(n, before)

    def test_invalid_settings_fail(self):
        for field, value in [('extra_days', 1.5), ('extra_days', True), ('max_fraction', 1.1),
                             ('capacity_units', -1), ('cost_rate', float('nan')),
                             ('via', ['cp']), ('via', ['missing'])]:
            with self.subTest(field=field, value=value):
                n = fixture()
                n['port_detours']['cp'][field] = value
                with self.assertRaises(ValueError):
                    run(n)

    def test_actual_network_and_map_detour_waypoint(self):
        n = build_network()
        n['port_detours']['logistics:kaohsiung'].update(enabled=True, extra_days=0, capacity_units=100.)
        r = calculate_supply_shock(n, [event('logistics:kaohsiung')], 2, use_inventory=False, use_bypass=False)
        self.assertGreater(r['logistics']['totals']['delivered'], 0)
        fig = build_globe(n, r)
        p = n['nodes']['logistics:keelung']
        self.assertTrue(any(any(abs(a-p['lat']) < 1e-6 and abs(b-p['lon']) < 1e-6
            for a, b in zip(t.lat, t.lon) if a is not None)
            for t in fig.data if t.mode == 'lines' and t.line.color == COLORS['bypass']))

    def test_saved_settings_validation_is_atomic(self):
        n = build_network()
        before = deepcopy(n['port_detours'])
        with self.assertRaises(ValueError):
            apply_saved_settings(n, {'missing': {}}, {})
        self.assertEqual(n['port_detours'], before)

    def test_inventory_sensitivity_also_scales_destination_route_setting(self):
        from ui.calculation import calculate_sensitivity
        n = fixture()
        n['route_settings']['delivery0']['inventory_days'] = 2.
        n['nodes']['delivery0']['inventory_days'] = 2.
        rows = calculate_sensitivity(n, [event()], 5, True, False, [])
        self.assertLess(rows[1]['average'], rows[0]['average'])
        self.assertEqual(n['route_settings']['delivery0']['inventory_days'], 2.)


class PortSettingsUITests(unittest.TestCase):
    def test_edit_save_reopen_and_vendor_toggle(self):
        from streamlit.testing.v1 import AppTest
        root = Path(__file__).resolve().parents[1]
        app = AppTest.from_file(str(root / 'tests/fixtures/panel_components.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.run(timeout=30)
        app.button[0].click().run(timeout=30)
        next(c for c in app.checkbox if c.label == '이 항만·해협의 우회 사용').check()
        next(v for v in app.number_input if v.label == '우회 추가 운송일 · 가정').set_value(0)
        next(b for b in app.button if b.label == '항만 우회 설정 저장').click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state['rr_network']['port_detours']['logistics:kaohsiung']['enabled'])
        app.text_input(key='rr_issue_text').set_value('가오슝항 폐쇄 30일')
        next(b for b in app.button if b.label == '이슈 적용 → 소재 계산').click().run(timeout=30)
        self.assertGreater(app.session_state['rr_result']['logistics']['totals']['dispatched'], 0)
        app.checkbox(key='rr_bypass').uncheck().run(timeout=30)
        self.assertGreater(app.session_state['rr_result']['logistics']['totals']['dispatched'], 0)
        app.button[0].click().run(timeout=30)
        self.assertTrue(next(c for c in app.checkbox if c.label == '이 항만·해협의 우회 사용').value)
        self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()
