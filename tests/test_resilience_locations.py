import unittest
from resilience_data import build_network
from resilience_globe import build_globe
from resilience_locations import location_rows, apply_locations
from copy import deepcopy
import json
import tempfile
from pathlib import Path
from simulation.resilience import calculate_supply_shock


class VerifiedLocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph=build_network()
        cls.normal=calculate_supply_shock(cls.graph)

    def test_no_geographic_process_nodes_or_ocean_display_points(self):
        self.assertFalse(any(n['kind']=='process' for n in self.graph['entities'].values()))
        for n in self.graph['nodes'].values():
            if n['kind']=='process':
                self.assertIsNone(n['lat']);self.assertIsNone(n['lon'])
        self.assertFalse(any(e['kind']=='process' for e in self.graph['visual_edges']))

    def test_all_original_44_remain_locatable_without_changing_records(self):
        self.assertEqual(len(self.graph['backbone']),44)
        self.assertEqual(self.graph['mapped_backbone_count'],44)

    def test_no_material_or_reserve_position_offsets(self):
        for n in self.graph['nodes'].values():
            if n['kind']=='logistics':
                self.assertEqual(n['location_status'],'시나리오 경유점')
                continue
            key=n.get('map_location_id')
            if key:
                p=self.graph['locations'][key]
                self.assertEqual((n['lat'],n['lon']),(p['lat'],p['lon']))
            else:
                self.assertIsNone(n['lat']);self.assertIsNone(n['lon'])

    def test_every_plotted_marker_is_on_a_sourced_real_location(self):
        allowed={(p['lat'],p['lon']) for p in self.graph['locations'].values()}
        allowed.update((p['lat'],p['lon']) for p in self.graph['logistics'].values())
        for level in ('국가','기업','소재 연쇄'):
            figure=build_globe(self.graph,self.normal,level=level)
            for trace in figure.data:
                if trace.mode in ('markers','text','markers+text'):
                    self.assertTrue(set(zip(trace.lat,trace.lon))<=allowed)

    def test_wafer_filter_shows_sourced_wafer_plants(self):
        f=build_globe(self.graph,self.normal,process='웨이퍼 제조')
        coordinates={pair for t in f.data if t.mode=='markers' for pair in zip(t.lat,t.lon)}
        for key in ('seh-shirakawa','sumco-imari'):
            p=self.graph['locations'][key]
            self.assertIn((p['lat'],p['lon']),coordinates)
            self.assertEqual(p['process_roles'],['웨이퍼 제조'])

    def test_etch_filter_has_actual_fabs_and_never_etch_as_a_place(self):
        f=build_globe(self.graph,self.normal,process='식각')
        coordinates={pair for t in f.data if t.mode=='markers' for pair in zip(t.lat,t.lon)}
        for key in ('samsung-giheung','samsung-pyeongtaek','tsmc-fab12a','tsmc-fab18'):
            p=self.graph['locations'][key]
            self.assertIn((p['lat'],p['lon']),coordinates)
        self.assertFalse(any(t.mode=='text' and any(s=='식각' for s in t.text) for t in f.data))

    def test_unknown_mines_and_sites_do_not_get_country_coordinate_fallbacks(self):
        for key in ('raw:ceria','raw:gallium','raw:neon','stella-sg','temc'):
            self.assertIsNone(self.graph['nodes'][key]['map_location_id'])
            self.assertIn(key,self.graph['unlocated_entities'])
        for p in self.graph['locations'].values():
            self.assertTrue(p['source']);self.assertTrue(p['coordinate_source'])
            self.assertIsNone(p['site_impact_share']);self.assertIsNone(p['route_allocation'])

    def test_review_covers_every_registered_coordinate_and_corrects_road_anchor(self):
        for p in self.graph['locations'].values():
            audit=p['coordinate_audit']
            self.assertIn(audit['method'],('within_source_bounds','map_resolved','corrected_building'))
            self.assertEqual(audit['evidence']['url'],p['coordinate_source'])
            bounds=audit['evidence'].get('bounds')
            if bounds:
                self.assertTrue(bounds[0]<=p['lat']<=bounds[2])
                self.assertTrue(bounds[1]<=p['lon']<=bounds[3])
        applied=self.graph['locations']['applied-hq']
        self.assertEqual(applied['coordinate_audit']['method'],'corrected_building')
        self.assertEqual(applied['coordinate_audit']['evidence']['tags']['name'],'Applied Materials Building 1')

    def test_headquarters_and_reference_fabs_have_distinct_marker_shapes(self):
        fig=build_globe(self.graph,self.normal)
        symbols={}
        for t in fig.data:
            if t.mode=='markers':
                for lat,lon,symbol in zip(t.lat,t.lon,t.marker.symbol):symbols[lat,lon]=symbol
        for p in self.graph['locations'].values():
            if p['location_type'] in ('hq','hq_campus') and (p['lat'],p['lon']) in symbols:
                self.assertEqual(symbols[p['lat'],p['lon']],'square-open')
        p=self.graph['locations']['samsung-pyeongtaek']
        self.assertEqual(symbols[p['lat'],p['lon']],'circle-open')

    def test_foreign_company_site_binding_fails_instead_of_plotting(self):
        registry=json.loads((Path(__file__).parents[1]/'data/verified_locations.json').read_text(encoding='utf-8'))
        registry['bindings']['samsung']='sumco-imari'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'registry.json';path.write_text(json.dumps(registry),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'소속'):
                apply_locations(deepcopy(self.graph),path)

    def test_export_lists_all_places_and_does_not_claim_facility_deliveries(self):
        rows=location_rows(self.graph)
        self.assertEqual(len(rows),len(self.graph['locations']))
        self.assertTrue(all(r['시설간납품']=='미확인' for r in rows))


if __name__=='__main__':unittest.main()
