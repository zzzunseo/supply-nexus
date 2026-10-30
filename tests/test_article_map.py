from copy import deepcopy
from pathlib import Path
import json
import unittest

from article_map import article_map_data, build_article_globe, select_article_route
from news.article_review import article_draft, review_article
from resilience_data import build_network


class ArticleMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network=build_network()
        body='JSR의 한 공장에서 발생한 사건에 관한 기능 검증용 가상 사례다.'
        cls.review=review_article(cls.network,article_draft(cls.network,'가상 기사',body),'jsr',body)

    def test_only_reviewed_route_ids_are_shown_with_registered_evidence_categories(self):
        payload=article_map_data(self.network,self.review)
        self.assertEqual({r['id'] for r in payload['routes']},{r['id'] for r in self.review['routes']})
        self.assertEqual({r['kind'] for r in payload['routes']},{'supply','reference'})
        figure=build_article_globe(payload)
        self.assertFalse(figure.layout.meta['simulation_used'])
        self.assertFalse(figure.layout.meta['event_location_verified'])
        lines=[t for t in figure.data if t.mode=='lines']
        self.assertEqual(len(lines),2)
        self.assertEqual({t.line.dash for t in lines},{'solid','dot'})
        self.assertFalse(any(t.line.color=='#FF587B' for t in lines))

    def test_missing_position_is_not_replaced_by_headquarters_guesses_or_old_coordinates(self):
        network=deepcopy(self.network)
        network['nodes']['jsr']['map_location_id']=None
        # The old map_location/lat/lon values remain: the article map must not fall back to them.
        payload=article_map_data(network,self.review)
        self.assertTrue(all(not r['mapped'] for r in payload['routes']))
        self.assertFalse(build_article_globe(payload).data)

    def test_headquarters_never_becomes_the_article_incident_location(self):
        payload=article_map_data(self.network,self.review)
        self.assertFalse(payload['event_location_verified'])
        a=payload['routes'][0]['anchors'][0]
        self.assertEqual(a['location_type'],'hq')
        self.assertIn('사건 발생 장소',payload['routes'][0]['location_note'])

    def test_source_links_come_from_registered_graph_not_replaced_article_snapshot(self):
        review=deepcopy(self.review)
        for row in review['routes']:row['source']='https://example.com/invented'
        payload=article_map_data(self.network,review)
        self.assertTrue(all(r['source']!='https://example.com/invented' for r in payload['routes']))

    def test_unknown_route_is_explicitly_unmapped(self):
        review=deepcopy(self.review)
        review['routes'][0]['id']='missing-route'
        payload=article_map_data(self.network,review)
        self.assertFalse(payload['routes'][0]['mapped'])
        self.assertIn('찾을 수 없음',payload['routes'][0]['reason'])

    def test_selection_whitelist_and_read_only_inputs(self):
        before_network,before_review=deepcopy(self.network),deepcopy(self.review)
        payload=article_map_data(self.network,self.review)
        row=payload['routes'][0]
        figure=build_article_globe(payload,row['id'])
        self.assertEqual(figure.layout.meta['selected_route'],row['id'])
        diamonds=[t for t in figure.data if t.mode=='markers+text' and t.customdata]
        self.assertEqual({t.customdata[0] for t in diamonds},{r['id'] for r in payload['routes']})
        state={'rr_article_route_click':{'picked':'unknown'},'rr_article_route':None}
        select_article_route(state,{row['id']})
        self.assertIsNone(state['rr_article_route'])
        state['rr_article_route_click']['picked']=row['id']
        select_article_route(state,{row['id']})
        self.assertEqual(state['rr_article_route'],row['id'])
        self.assertEqual(self.network,before_network)
        self.assertEqual(self.review,before_review)


class ArticleMapUITests(unittest.TestCase):
    def test_open_and_select_article_map_keeps_calculation_and_main_map_selection_unchanged(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'tests/fixtures/panel_components.py'))
        app.session_state['rr_workspace_mode'] = '상세 모드'
        app.session_state['rr_chat_mode'] = '기사 검토 · 모의 대화'
        app.run(timeout=30)
        body='JSR의 한 공장 사건에 관한 검증용 가상 사례다.'
        review=review_article(app.session_state['rr_network'],article_draft(app.session_state['rr_network'],'가상 기사',body),'jsr',body)
        app.session_state['rr_article_review']=review
        app.run(timeout=30)
        before=deepcopy(app.session_state['rr_result'])
        events=deepcopy(app.session_state['rr_events'])
        scopes=deepcopy(app.session_state['rr_material_scopes'])
        process,focus=app.session_state['rr_process'],app.session_state['rr_focus']
        app.button(key='rr_article_map_button').click().run(timeout=30)
        self.assertFalse(app.exception)
        row=review['routes'][1]
        app.selectbox(key='rr_article_route_picker').select(row['id']).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['rr_article_route'],row['id'])
        figures=[json.loads(item.proto.spec) for item in app.get('plotly_chart')]
        metadata=next(f['layout']['meta'] for f in figures if f['layout'].get('meta',{}).get('article_id'))
        self.assertEqual(metadata['selected_route'],row['id'])
        self.assertFalse(metadata['simulation_used'])
        self.assertEqual(app.session_state['rr_result'],before)
        self.assertEqual(app.session_state['rr_events'],events)
        self.assertEqual(app.session_state['rr_material_scopes'],scopes)
        self.assertEqual((app.session_state['rr_process'],app.session_state['rr_focus']),(process,focus))


if __name__=='__main__':
    unittest.main()
