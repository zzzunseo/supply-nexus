"""Map only sourced buildings/campuses. Keep geography independent of scoring."""
import json
from pathlib import Path

LOCATION_TYPES = {
    'chip_fab':'칩 가공 팹', 'chip_fab_hq':'팹·본사', 'wafer_plant':'실리콘 웨이퍼 공장',
    'hq':'본사', 'hq_campus':'본사 사업장', 'assembly_test':'패키징·검사 사업장',
    'mine_processing':'광산·분리 사업장', 'materials_campus':'소재 사업장',
}


def location_rows(network):
    return [dict(시설=p['name'],구분=LOCATION_TYPES[p['location_type']],국가=p['country'],
        주소=p['address'],위도=p['lat'],경도=p['lon'],
        좌표검토=p.get('coordinate_audit',{}).get('summary','재검토 필요'),
        주소근거=p['source'],좌표근거=p['coordinate_source'],
        공정=' / '.join(p['process_roles']) or '생산 공정 위치 미확인',
        시설간납품='미확인') for p in network['locations'].values()]


def apply_locations(network, path=None):
    path=Path(path or Path(__file__).parent/'data/verified_locations.json')
    registry=json.loads(path.read_text(encoding='utf-8'))
    locations=registry['locations'];bindings=registry['bindings']
    for key,place in locations.items():
        if place['id']!=key or place['location_type'] not in LOCATION_TYPES:
            raise ValueError(f'위치 ID·유형 오류: {key}')
        if not place.get('source') or not place.get('coordinate_source'):
            raise ValueError(f'위치·좌표 출처가 없습니다: {key}')
        if not -90<=place['lat']<=90 or not -180<=place['lon']<=180:
            raise ValueError(f'위도·경도 오류: {key}')
    for key,n in network['nodes'].items():
        location_id=registry.get('raw_bindings',{}).get(key)
        if n['kind']=='company':location_id=bindings.get(key)
        elif n['kind'] in ('product','material','reserve'):
            location_id=bindings.get(n.get('company_id'))
        # Unverified coordinates must never silently fall back to old UI offsets.
        n.update(lat=None,lon=None,map_location_id=None,location_status='확인 필요',
                 location_scope='소재·기업의 위치 좌표 미확인; 지도에는 표시하지 않음')
        if location_id:
            place=locations[location_id]
            company_id=n['id'] if n['kind']=='company' else n.get('company_id')
            if company_id and company_id!=place['company_id']:
                raise ValueError(f'기업과 사업장의 소속이 다릅니다: {key}')
            n.update(lat=place['lat'],lon=place['lon'],map_location_id=location_id,
                location_status='출처 있음',map_location=place,
                location_scope=f"{place['name']} · {place['location_type']} · {place['coordinate_precision']}")
    network['locations']=locations
    network['location_bindings']=bindings
    network['unlocated_entities']=[k for k,n in network['entities'].items() if not n.get('map_location_id')]
    network['mapped_backbone_count']=sum(bool(network['nodes']['supply:'+e['from']+':'+e['item_id']].get('map_location_id'))
        and bool(network['nodes'][e['to']].get('map_location_id')) for e in network['backbone'])
    return network
