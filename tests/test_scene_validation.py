import unittest
from copy import deepcopy
from ui.presentation_scene import restore_scene


class SceneValidationTests(unittest.TestCase):
    def test_rejects_malformed_and_duplicate_connections(self):
        rows=[dict(supplier='a',recipient='b',target='p')]
        good=dict(schema=1,port='port',connections=[['a','b','p']],assumptions=dict(days=30,reduction_percent=100,stock_days=7))
        self.assertEqual(restore_scene(good,rows,{'port':{}})['integrated_rows'],[0])
        bad=[dict(good,schema=True),[],None,42,dict(good,port=[]),dict(good,assumptions=[]),dict(good,connections='abc'),dict(good,connections=[['a','b','p']]*2),dict(good,connections=[[{},'b','p']])]
        for field,value in [('days',0),('days',True),('reduction_percent',101),('stock_days',-1)]:
            item=deepcopy(good);item['assumptions'][field]=value;bad.append(item)
        for item in bad:
            with self.subTest(payload=item),self.assertRaises(ValueError):restore_scene(item,rows,{'port':{}})
