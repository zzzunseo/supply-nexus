import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legacy.data_loader import load_demo


class DemoDataTests(unittest.TestCase):
    def test_all_processes_have_display_metadata(self):
        data = load_demo(ROOT / 'data' / 'demo.json')
        self.assertEqual(len(data['processes']), 8)
        self.assertTrue(all(p in data['descriptions'] for p in data['processes']))

    def test_unknown_endpoint_fails_before_rendering(self):
        data = json.loads((ROOT / 'data' / 'demo.json').read_text(encoding='utf-8'))
        data['edges'][0]['to'] = 'missing-node'
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bad.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '연결 거점'):
                load_demo(path)

    def test_invalid_coordinate_is_rejected(self):
        data = json.loads((ROOT / 'data' / 'demo.json').read_text(encoding='utf-8'))
        data['nodes'][0]['lat'] = 999
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bad.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '좌표'):
                load_demo(path)


if __name__ == '__main__':
    unittest.main()
