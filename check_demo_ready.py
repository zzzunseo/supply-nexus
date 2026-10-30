"""Read-only preflight for a local presentation; never calls an LLM API."""
import argparse
import json
from pathlib import Path
from urllib.request import urlopen


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8517)
    parser.add_argument('--files-only',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parent;failed=[]
    files=['night_globe/dist/globe.js','night_globe/style.css','static/world_110m.json',
           'data/core_cases.json','data/response_evidence.json','data/verified_locations.json']
    for name in files:
        path=root/name
        if not path.is_file() or path.stat().st_size==0:failed.append(name)
    try:
        evidence=json.loads((root/'data/response_evidence.json').read_text(encoding='utf-8'))
        assert {'wafer','photoresist'}<=evidence['cases'].keys()
        bundle=(root/'night_globe/dist/globe.js')
        assert all(bundle.stat().st_mtime_ns>=(root/name).stat().st_mtime_ns for name in ['night_globe/index.js','night_globe/interaction.mjs'])
        assert 'data:image/jpeg;base64,' in bundle.read_text(encoding='utf-8')
    except (OSError,ValueError,KeyError,AssertionError):failed.append('bundle or evidence validation')
    if not args.files_only:
        try:
            with urlopen(f'http://127.0.0.1:{args.port}/_stcore/health',timeout=3) as response:
                assert response.status==200 and response.read().strip()==b'ok'
        except (OSError,AssertionError):failed.append('local server health')
    print('READY: local assets, evidence'+(' and server' if not args.files_only else '') if not failed else 'NOT READY: '+', '.join(failed))
    return 1 if failed else 0


if __name__=='__main__':raise SystemExit(main())
