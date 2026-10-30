"""Optional same-supplier maritime detours with shared capacity and transit queues.

One route's nominal daily demand is one unit. Units across routes are deliberately
equal-weight scenario units, never tonnes, TEU, production or measured port capacity.
Normal transport retains the legacy zero-lag baseline; queues model extra delay only.
"""
from collections import defaultdict
from copy import deepcopy
from math import isfinite


def bounded(value, low, high, label, integer=False):
    if (type(value) not in (int, float) or not isfinite(value)
            or not low <= value <= high or (integer and type(value) is not int)):
        raise ValueError(f'{label}: {low}~{high}' + (' 정수' if integer else ' 숫자') + '가 필요합니다.')


def validate_route_settings(network):
    nodes = network['nodes']
    routes = network.get('logistics_routes', {})
    settings = network.get('route_settings', {})
    if set(settings) - set(routes):
        raise ValueError('미등록 운송 경로 설정입니다.')
    for key, setting in settings.items():
        if set(setting) != {'sea_fraction', 'inventory_days'}:
            raise ValueError('운송 비중 설정 필드가 잘못되었습니다.')
        bounded(setting['sea_fraction'], 0, 1, '해상 비중')
        bounded(setting['inventory_days'], 0, 365, '도착지 재고일')
    for key, setting in network.get('port_detours', {}).items():
        if key not in network.get('logistics', {}) or set(setting) != {
                'enabled', 'via', 'max_fraction', 'capacity_units', 'extra_days', 'cost_rate'}:
            raise ValueError('항만 우회 설정 필드 또는 대상이 잘못되었습니다.')
        if type(setting['enabled']) is not bool:
            raise ValueError('항만 우회 사용 여부는 참/거짓이어야 합니다.')
        via = setting['via']
        if (not isinstance(via, list) or not via or any(not isinstance(c, str) for c in via)
                or len(set(via)) != len(via) or key in via
                or any(c not in nodes or nodes[c].get('kind') != 'logistics' for c in via)):
            raise ValueError('우회 경유점은 등록된 다른 항만·해협이어야 합니다.')
        bounded(setting['max_fraction'], 0, 1, '경로별 우회 한도')
        bounded(setting['capacity_units'], 0, 1000, '공유 우회 처리량')
        bounded(setting['extra_days'], 0, 365, '추가 운송일', integer=True)
        bounded(setting['cost_rate'], 0, 10, '추가 운임률')


class LogisticsRouter:
    def __init__(self, network, scopes):
        validate_route_settings(network)
        self.network, self.scopes = network, scopes
        self.routes = network.get('logistics_routes', {})
        self.settings = network.get('port_detours', {})
        self.queues = defaultdict(lambda: defaultdict(list))
        self.timeline = []
        self.last = {}
        self.totals = defaultdict(float)

    def start_day(self, day):
        self.day = day
        self.left = {key: s['capacity_units'] for key, s in self.settings.items()}
        self.last = {}

    def plan_layer(self, layer, daily):
        plans = {}
        for key in layer:
            if key not in self.routes:
                continue
            route = self.routes[key]
            if route['scope'] not in self.scopes:
                continue
            sea = self.network.get('route_settings', {}).get(key, {}).get('sea_fraction', 1.)
            supply = daily[route['source']]['effective']
            availability = min(daily[c]['effective'] for c in route['via'])
            regular = supply * (1 - sea) + sea * min(supply, availability)
            blocked = [c for c in route['via'] if daily[c]['effective'] < 1 - 1e-10]
            replaced = [c for c in blocked if self.settings.get(c, {}).get('enabled', False)]
            selected = [self.settings[c] for c in replaced]
            via, delay, cost, request = [], 0, 0., 0.
            possible = bool(replaced)
            if possible:
                for c in route['via']:
                    via.extend(self.settings[c]['via'] if c in replaced else [c])
                # Every remaining/new chokepoint constrains the detour too.
                remaining = [max(0., daily[c]['effective'] - availability)
                             for c in route['via'] if c not in replaced]
                alternate_points = [c for s in selected for c in s['via']]
                alternative = min(remaining + [daily[c]['effective'] for c in alternate_points])
                request = min(max(0., supply - regular), sea * alternative,
                              sea * min(s['max_fraction'] for s in selected))
                delay = sum(s['extra_days'] for s in selected)
                cost = sum(s['cost_rate'] for s in selected)
            plans[key] = dict(regular=regular, main_availability=availability,
                              sea_fraction=sea, via=via, pools=replaced,
                              extra_days=delay, cost_rate=cost, requested=request)
        demands = defaultdict(float)
        for plan in plans.values():
            for c in plan['pools']:
                demands[c] += plan['requested']
        factors = {c: min(1., self.left[c] / total) for c, total in demands.items() if total > 0}
        for key, plan in plans.items():
            factor = min([factors.get(c, 1.) for c in plan['pools']] or [1.])
            shipped = plan['requested'] * factor
            for c in plan['pools']:
                self.left[c] = max(0., self.left[c] - shipped)
            if shipped:
                self.queues[key][self.day + plan['extra_days']].append(
                    dict(units=shipped, via=plan['via']))
            arrivals = self.queues[key].pop(self.day, [])
            arrived = sum(p['units'] for p in arrivals)
            delivered = min(max(0., 1 - plan['regular']), arrived)
            # No backlog recovery or destination restocking is implied. Excess
            # after primary recovery is reported, never silently added to demand.
            pending = sum(p['units'] for items in self.queues[key].values() for p in items)
            self.last[key] = dict(**plan, dispatched=shipped, arrived=arrived,
                delivered=delivered, surplus=arrived-delivered, pending=pending,
                arrival_vias=[p['via'] for p in arrivals],
                effective=min(1., plan['regular'] + delivered))
            self.totals['dispatched'] += shipped
            self.totals['arrived'] += arrived
            self.totals['delivered'] += delivered
            self.totals['surplus'] += arrived - delivered
            self.totals['extra_freight'] += shipped * plan['cost_rate']
        return self.last

    def end_day(self):
        self.timeline.append(dict(day=self.day, routes=deepcopy(self.last)))

    def finish(self):
        dispatched = self.totals['dispatched']
        return dict(routes=deepcopy(self.last), timeline=self.timeline,
            totals=dict(self.totals), pending=sum(r['pending'] for r in self.last.values()),
            detour_freight_index=100 * (1 + self.totals['extra_freight'] / dispatched) if dispatched else None,
            settings=deepcopy(self.settings),
            route_settings=deepcopy(self.network.get('route_settings', {})),
            note='각 경로 명목 수요=1/일인 동일 비중 가정. 정상 경로는 기존 즉시 도착 기준이며 우회는 추가 운송일만 반영. '
                 '일반 경로 복구 뒤 초과 도착은 별도 표시하고 재고·미납 수요로 재배정하지 않음. '
                 '우회 운임지수는 발송 우회 물량 가중 운임이며 제품 원가·전체 물류비가 아님.')
