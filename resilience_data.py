"""Editable mineral → vendor → 44 original links → process graph.

Official sources establish products/uses/locations, not undisclosed contracts.
Every added delivery, stock, reserve and recipe is labeled as a model assumption.
The original 44 records, including unconfirmed/collaboration records, stay intact.
"""
from copy import deepcopy
import json
from pathlib import Path
from resilience_locations import apply_locations
from resilience_materials import extend_materials
from resilience_logistics import add_logistics
from simulation.evidence import relationship_decision, attach_coverage
from evidence_review import attach_review

ROOT = Path(__file__).resolve().parent
CHECKED = '2026-10-26'
SOURCES = {
    'quartz': ('https://www.sibelco.com/en/materials/high-purity-quartz', None,
               'Spruce Pine의 HPQ와 반도체 CZ 도가니·석영 부품 용도. 특정 웨이퍼 고객 계약은 미확인.'),
    'poly': ('https://reports.wacker.com/2024/annual-report/combined-management-report/segments/wacker-polysilicon.html', 2024,
             'WACKER의 반도체급 폴리실리콘 사업·Burghausen 생산. Shin-Etsu/SUMCO 계약은 미확인.'),
    'ceria': ('https://www.ipms.fraunhofer.de/en/applications/Green-ICT/Clean-Technologies/green-slurries.html', 2026,
              '세륨 산화물의 일부 STI/산화막 CMP 용도. 모든 CMP의 필수재가 아님.'),
    'agc-cmp': ('https://www.agc.com/en/products/electoric/detail/cmp.html', None,
                'AGC의 CMP 슬러리 제품·용도. 고객 및 광물 원산지는 미공개.'),
    'merck-cmp': ('https://www.merckgroup.com/de/geschaeftsbericht/2023/lagebericht/grundlagen-des-konzerns/forschung-und-entwicklung/electronics.html', 2023,
                  'Merck의 ceria 입자 기반 CMP 개발. 예약 여력·등급 상호대체성은 가정.'),
    'neon': ('https://www.cymer.com/wp-content/uploads/2018/01/Cymer_SPIE_AdvancedLithography_2017v2-1.pdf', 2017,
             '네온은 DUV 엑시머 레이저 소모재. EUV 광원 가스로 일반화하지 않음.'),
    'neon-origin': ('https://newsroom.posco.com/kr/포스코홀딩스-반도체용-희귀가스-국산화로-국내-공/', 2023,
                    '한국의 미국·중국·우크라이나 희귀가스 수입 언급. 현재 물량·특정 TEMC 수입 계약은 미확인.'),
    'posco-temc': ('https://newsroom.posco.com/kr/포스코-반도체용-희귀가스-네온-생산-설비-및-기/', 2022,
                   '광양의 네온 추출과 TEMC의 정제·엑시머 가스 생산. 현재 대체 여력은 미공개.'),
    'hoya': ('https://www.hoya.com/en/business/informationtechnology/', None,
             'HOYA의 반도체 마스크 블랭크·포토마스크 제품. 개별 팹 납품·여유 생산량은 미확인.'),
    'agc-mask': ('https://www.agc.com/en/everyday/semiconductor/semiconductor.html', 2021,
                 'AGC의 EUV 마스크 블랭크 제품. HOYA 제품과의 등급별 즉시 대체는 가정.'),
    'stella': ('https://www.stella-chemifa.co.jp/english/products/cat1/', None,
               'Stella Chemifa의 고순도 HF와 반도체 습식 세정·식각 용도.'),
    'stella-sites': ('https://www.stella-chemifa.co.jp/english/files/corporate%20info%20English20240701.pdf', 2024,
                     '일본·싱가포르 생산 거점. 가용 여력과 고객별 배분율은 미공개.'),
    'jx': ('https://nmmjx-dc.com/en/products/ng-device/semiconductor.html', None,
           'JX Advanced Metals의 Cu·W·Ta·Co 등 반도체 타깃 제품. 원산지와 특정 고객 경로는 미확인.'),
    'sk-wf6': ('https://eng.sk.com/companies/info/sk-ecoplant-materials', None,
               'SK materials 계열의 WF6 제품. 중국 텅스텐 조달·Samsung/TSMC 공급 비중은 가정.'),
    '5n': ('https://www.5nplus.com/en/news/5n-to-expand-st-george-utah-production-facility-by/', 2026,
           'St. George의 Ge·GaAs 특수 반도체 소재·기판 사업. 일반 실리콘 공정 전체에 적용하지 않음.'),
    'ga-ge': ('https://pubs.usgs.gov/publication/ofr20241057/full', 2024,
              '중국의 Ga·Ge 1차 생산 집중과 화합물 반도체 응용. 특정 5N+ 조달 계약은 미확인.'),
    'minerals': ('https://pubs.usgs.gov/periodicals/mcs2025/mcs2025.pdf', 2025,
                 '국가별 광물 생산 자료. 이 모델의 개별 기업 조달 경로·점유율·생산여력으로 쓰지 않음.'),
    'palladium': ('https://pubs.usgs.gov/publication/sir20255021/full', 2025,
                  '러시아 등 Pd 생산국 자료. 러시아→Heraeus 계약은 가정.'),
    'wire': ('https://www.heraeus-electronics.com/en/products-and-solutions/bonding-wires/fine-bonding-wires/', None,
             'Heraeus의 Au·Ag·Cu 및 Pd 코팅 Cu 본딩 와이어 제품. 패키지별 적용·실제 조달 국가는 별도 확인.'),
    'sinter': ('https://www.heraeus-electronics.com/en/products-and-solutions/sinter-materials/non-pressure-sinter-materials/', None,
               '선택한 전력반도체 패키지의 은 소결 접합 소재 용도.'),
    'solder': ('https://www.heraeus-electronics.com/en/products-and-solutions/solder-materials/solder-pastes/advanced-packaging-solder-pastes/', None,
               '첨단 패키징용 주석계 솔더 제품. 특정 ASE/Amkor 납품·원산지는 미확인.'),
    'dongjin': ('https://www.dongjin.com/en/business/semiconductor.php', None,
                '동진쎄미켐의 ArF/KrF/i-line PR·CMP 제품. 일본산 PR과의 등급별 인증·대체 한도는 가정.'),
}

COMPANIES = [
    ('sibelco', 'Sibelco Spruce Pine', '미국', '미국 노스캐롤라이나', 35.92, -82.06, 'quartz', ['시벨코', '스프루스파인', 'spruce pine']),
    ('wacker', 'WACKER Burghausen', '독일', '독일 Burghausen', 48.17, 12.83, 'poly', ['바커', 'wacker']),
    ('agc', 'AGC', '일본', '일본 대표 거점', 35.67, 139.77, 'agc-cmp', ['아사히글라스']),
    ('hoya', 'HOYA', '일본', '일본 대표 거점', 35.69, 139.69, 'hoya', ['호야']),
    ('stella', 'Stella Chemifa', '일본', '일본 오사카 대표 거점', 34.69, 135.50, 'stella', ['스텔라 케미파', '스텔라케미파']),
    ('stella-sg', 'Stella Chemifa Singapore', '싱가포르', '싱가포르 대표 거점', 1.30, 103.78, 'stella-sites', ['스텔라 싱가포르']),
    ('temc', 'TEMC', '한국', '한국 대표 거점', 36.49, 127.73, 'posco-temc', ['티이엠씨']),
    ('posco-neon', 'POSCO 광양 네온', '한국', '한국 광양', 34.94, 127.70, 'posco-temc', ['포스코', '광양 네온']),
    ('jx', 'JX Advanced Metals', '일본', '일본 대표 거점', 35.66, 139.74, 'jx', ['jx금속', 'jx 금속', 'jx']),
    ('sk-materials', 'SK materials 계열', '한국', '한국 대표 거점', 36.82, 128.62, 'sk-wf6', ['sk머티리얼즈', 'sk 머티리얼즈']),
    ('five-n', '5N Plus St. George', '미국', '미국 유타 St. George', 37.10, -113.58, '5n', ['5n plus', '5n+', '파이브엔플러스']),
    ('heraeus', 'Heraeus Electronics', '독일', '독일 대표 거점', 50.13, 8.92, 'wire', ['헤레우스']),
    ('dongjin', 'Dongjin Semichem', '한국', '한국 대표 거점', 37.39, 126.73, 'dongjin', ['동진쎄미켐', '동진']),
]

# Every entry declares a product scope; Ge/Ga and package recipes are opt-in.
# resource ID/name/country/lat/lon, vendor, output, source, selected scope, buffer, alt limit
CHAINS = [
    ('quartz', '미국 고순도 석영', '미국', 35.92, -82.06, 'sibelco', '석영 도가니·부품 투입재', 'quartz', 'core', 7, 0),
    ('poly', '반도체급 실리콘 원료', '독일', 48.17, 12.83, 'wacker', '반도체급 폴리실리콘', 'poly', 'core', 7, 0),
    ('ceria', '중국 세륨·희토류', '중국', 40.66, 109.84, 'agc', '세륨계 CMP 슬러리', 'ceria', 'core', 7, .5),
    ('neon', '우크라이나 네온', '우크라이나', 46.48, 30.72, 'temc', 'DUV 엑시머 네온 혼합가스', 'neon', 'core', 10, .6),
    ('fluorspar', '중국 형석·불소 원료', '중국', 29.0, 119.0, 'stella', '고순도 불산(HF)', 'stella', 'core', 7, .45),
    ('mask', '합성 실리카·마스크 기판', '일본', 35.69, 139.69, 'hoya', '포토마스크 블랭크', 'hoya', 'core', 30, .4),
    ('copper', '칠레 구리', '칠레', -23.65, -70.40, 'jx', '고순도 구리 타깃', 'jx', 'core', 7, .4),
    ('tungsten', '중국 텅스텐', '중국', 25.83, 114.93, 'sk-materials', 'WF6 텅스텐 전구체', 'sk-wf6', 'core', 7, .4),
    ('gallium', '중국 갈륨', '중국', 35.0, 106.0, 'five-n', 'GaAs 계열 특수 기판', '5n', 'gallium', 10, .35),
    ('germanium', '중국 게르마늄', '중국', 26.6, 106.7, 'five-n', '게르마늄계 특수 소재', '5n', 'germanium', 10, .35),
    ('palladium', '러시아 팔라듐', '러시아', 69.35, 88.20, 'heraeus', 'Pd 코팅 Cu 본딩 와이어', 'wire', 'package_palladium', 14, .4),
    ('gold', '호주 금', '호주', -30.75, 121.47, 'heraeus', '금 본딩 와이어', 'wire', 'package_gold', 14, .4),
    ('silver', '멕시코 은', '멕시코', 23.17, -102.87, 'heraeus', '은 소결 접합재', 'sinter', 'package_silver', 14, .4),
    ('tin', '인도네시아 주석', '인도네시아', -2.1, 106.1, 'heraeus', '주석계 솔더', 'solder', 'package_tin', 14, .4),
]

RAW_ALIASES = {
    'quartz': ['고순도 석영', '석영', 'quartz', '노스캐롤라이나'],
    'poly': ['실리콘 원료', '폴리실리콘', 'silicon'],
    'ceria': ['희토류', '세륨', '산화세륨', 'ceria', 'rare earth'],
    'neon': ['네온', 'neon'], 'fluorspar': ['형석', '불소 원료', 'fluorspar'],
    'mask': ['합성 실리카'], 'copper': ['구리', 'copper', 'Cu'],
    'tungsten': ['텅스텐', 'tungsten', 'W'], 'gallium': ['갈륨', 'gallium', 'Ga'],
    'germanium': ['게르마늄', 'germanium', 'Ge'], 'palladium': ['팔라듐', 'palladium', 'Pd'],
    'gold': ['금 공급', '금 수출', '금 관세', '금광', 'gold', 'Au'],
    'silver': ['은 공급', '은 수출', '은 관세', '은광', 'silver', 'Ag'],
    'tin': ['주석', 'tin', 'Sn'],
}
ITEM_ALIASES = {'photoresist': ['포토레지스트', '감광 소재', '감광액', 'photoresist'],
    'developer': ['현상액', 'TMAH'], 'lithography': ['노광 장비', 'EUV 장비'],
    'etch-gas': ['CF4', '사불화탄소'], 'etch-tool': ['식각 장비'],
    'oxygen': ['산소', '고순도 산소'], 'hydrogen': ['수소', '고순도 수소'],
    'polished-wafer': ['폴리시드 웨이퍼'], 'epi-wafer': ['에피 웨이퍼'],
    'wafer-tester': ['검사 장비'], 'processed-wafer': ['가공 웨이퍼']}
COMPANY_ALIASES = {'samsung': ['삼성', '삼성전자'], 'tsmc': ['TSMC'], 'shinetsu': ['신에츠'],
    'sumco': ['섬코'], 'airliquide': ['에어리퀴드'], 'airproducts': ['에어프로덕츠'],
    'tok': ['TOK', '도쿄오카', '도쿄오카공업'], 'fujifilm': ['후지필름'],
    'asml': ['ASML'], 'lam': ['램리서치', '램 리서치'], 'applied': ['어플라이드', 'AMAT'],
    'merck': ['머크'], 'advantest': ['어드반테스트'], 'teradyne': ['테라다인'],
    'ase': ['ASE'], 'amkor': ['앰코']}


def build_network(folder=None):
    folder = Path(folder or ROOT / 'data')
    original = json.loads((folder / 'demo.json').read_text(encoding='utf-8'))
    if len(original['edges']) != 44 or len({e['id'] for e in original['edges']}) != 44:
        raise ValueError('원본 Backbone은 고유한 44개 연결이어야 합니다.')
    network = dict(nodes={}, entities={}, visual_edges=[], backbone=deepcopy(original['edges']),
        processes=original['processes'], process_outputs={}, sources=SOURCES, original=original)
    network['relationship_decisions'] = {
        edge['id']: dict(zip(('included', 'reason'), relationship_decision(edge)))
        for edge in original['edges']
    }
    network['coverage_gaps'] = []
    nodes, entities = network['nodes'], network['entities']

    def add(key, name, kind, country, lat, lon, *, requires=(), visible=True, source_key=None, **extra):
        if key in nodes:
            return key
        source, year, finding = SOURCES.get(source_key, (None, None, '계산·표시용 모델 구성'))
        n = dict(id=key, name=name, kind=kind, country=country, region=country,
            lat=lat, lon=lon, requires=list(requires), alt_vendor=None, alt_capacity=0.,
            inventory_days=0., capacity_units=1., mode='min', scope='core', buffer_direct=True,
            status='가정값', source=source, source_year=year, source_note=finding,
            parameter_status='가정값', parameter_source='재고·대체·생산 단위는 편집 가능한 시연 가정',
            location_scope='국가/본사 인근 대표 표시점; 실제 공장 위치 아님',
            aliases=[], visible=visible)
        n.update(extra)
        nodes[key] = n
        if visible:
            entities[key] = n
        return key

    def line(a, b, *, calc_source=None, calc_target=None, kind='upstream', processes=(), scope='core', **extra):
        edge=dict(id=f'{kind}:{len(network["visual_edges"])}',
            **{'from': a, 'to': b}, calc_source=calc_source or a, calc_target=calc_target or b,
            kind=kind, processes=list(processes), scope=scope, status='가정값',
            source=None, source_year=None, note='제품 용도에 근거한 시나리오 의존성. 실제 계약·비중은 확인 필요.')
        edge.update(extra)
        network['visual_edges'].append(edge)

    # Preserve the original real entities and their source/relationship metadata.
    for n in original['nodes']:
        if n['type'] == 'country_hub':
            continue
        key = add(n['id'], n['name'], 'company', n['country'], n['lat'], n['lon'],
                  aliases=COMPANY_ALIASES.get(n['id'], []), buffer_direct=False)
        nodes[key].update({k: deepcopy(v) for k, v in n.items() if k not in ('type', 'role')})
        nodes[key].update(kind='company', requires=[], inventory_days=0., alt_vendor=None, alt_capacity=0.)
    for key, name, country, region, lat, lon, source, aliases in COMPANIES:
        add(key, name, 'company', country, lat, lon, source_key=source, region=region,
            aliases=aliases, buffer_direct=False)
        if key in ('sibelco','wacker','stella-sg','posco-neon','five-n'):
            nodes[key]['location_scope']='공개 지역 거점; 좌표는 지역 대표점이며 실제 시설 경계가 아님'
    items = {i['id']: i for i in original['items']}
    supplies = {}
    for edge in original['edges']:
        supplier, item_id = edge['from'], edge['item_id']
        sid = f'supply:{supplier}:{item_id}'
        supplies[(supplier, item_id)] = sid
        c = nodes[supplier]
        i = items[item_id]
        add(sid, f'{c["name"]} · {i["name"]}', 'product', c['country'],
            c['lat'], c['lon'],
            requires=[supplier], item_id=item_id, company_id=supplier,
            input_category=i['category'], score_excluded=i['category']=='equipment',
            inventory_days=30. if i['category']=='equipment' else 7. if item_id=='processed-wafer' else 14.,
            aliases=[i['name'], *ITEM_ALIASES.get(item_id, [])], status=i['status'],
            source=i['source'], source_year=i['source_year'])
    # Alternative production is an additional reserved pool; not the supplier's
    # already-counted normal output. Availability/grade/reservation are assumptions.
    def reserve(key, provider, label, capacity=1., requires=None, scope='core'):
        c = nodes[provider]
        add(key, label, 'reserve', c['country'], c['lat'], c['lon'],
            requires=requires or [provider], capacity_units=capacity, scope=scope,
            source=c['source'], source_year=c['source_year'], company_id=provider,
            source_note='기업 제품 존재와 별개로 등급 인증·예약 계약·남는 생산능력은 모두 모델 가정.')
        return key
    pr = reserve('reserve:pr', 'dongjin', '한국 PR 대체 예약풀', capacity=1.2)
    for supplier in ('jsr', 'tok'):
        nodes[supplies[(supplier, 'photoresist')]].update(alt_vendor=pr, alt_capacity=.6)
    for item_id in ('polished-wafer', 'epi-wafer', 'oxygen', 'hydrogen'):
        vendors = ('shinetsu', 'sumco') if 'wafer' in item_id else ('airliquide', 'airproducts')
        for a, b in (vendors, vendors[::-1]):
            alt = reserve(f'reserve:{b}:{item_id}', b, f'{nodes[b]["name"]} {items[item_id]["name"]} 대체풀', .6)
            nodes[supplies[(a, item_id)]].update(alt_vendor=alt, alt_capacity=.6)

    products = {}
    for key, name, country, lat, lon, vendor, output, source, scope, inventory, alt_limit in CHAINS:
        raw = f'raw:{key}'
        raw_source = 'ga-ge' if key in ('gallium', 'germanium') else 'palladium' if key=='palladium' else 'neon-origin' if key=='neon' else 'quartz' if key=='quartz' else 'minerals'
        add(raw, name, 'resource', country, lat, lon, source_key=raw_source,
            scope=scope, aliases=RAW_ALIASES[key], inventory_days=0.)
        if key=='quartz':
            nodes[raw].update(location_scope='Spruce Pine 산지 확인; 좌표는 지역 대표점', status='출처 있음')
        sid = f'upstream:{key}'
        c = nodes[vendor]
        add(sid, output, 'material', c['country'], c['lat'], c['lon'],
            requires=[raw, vendor], source_key=source, scope=scope, inventory_days=float(inventory),
            aliases=[output], company_id=vendor)
        products[key] = sid
        line(raw, vendor, calc_target=sid, scope=scope, label=name)
        line(vendor, sid, calc_target=sid, scope=scope, label=output)
        if alt_limit:
            provider = {'ceria':'merck', 'neon':'posco-neon', 'fluorspar':'stella-sg', 'mask':'agc',
                        'copper':'jx', 'tungsten':'sk-materials', 'gallium':'five-n', 'germanium':'five-n'}.get(key, 'heraeus')
            alt = reserve(f'reserve:upstream:{key}', provider, f'{output} 대체 예약풀', capacity=1., scope=scope)
            nodes[sid].update(alt_vendor=alt, alt_capacity=alt_limit)
            # Reserve pools represent finished feedstock already qualified/secured
            # from independent origins, an explicit scenario assumption (not fact).
            nodes[alt]['source_note'] += ' 원재료 원산지 다변화도 가정.'
    # Both wafer candidates require quartzware feedstock AND semiconductor-grade silicon.
    for (supplier, item_id), sid in supplies.items():
        if item_id in ('polished-wafer', 'epi-wafer'):
            for key in ('quartz', 'poly'):
                nodes[sid]['requires'].append(products[key])
                line(products[key], sid, processes=['웨이퍼 제조'])
            alt = nodes[sid]['alt_vendor']
            nodes[alt]['requires'].extend([products['quartz'], products['poly']])

    operations = {}
    front = ('samsung', 'tsmc')
    recipients = {p: sorted({e['to'] for e in original['edges'] if p in e['processes']}) for p in original['processes']}
    # Every record is displayed, but only eligible supply records enter the DAG.
    routes = {}
    for edge in original['edges']:
        key = 'route:' + edge['id']
        a, b, item_id = edge['from'], edge['to'], edge['item_id']
        sid = supplies[(a, item_id)]
        decision = network['relationship_decisions'][edge['id']]
        if decision['included']:
            add(key, edge['item'], 'route', nodes[b]['country'], nodes[b]['lat'], nodes[b]['lon'],
                requires=[sid], visible=False, backbone_id=edge['id'])
            routes[edge['id']] = key
        line(sid, b, calc_target=key if decision['included'] else b,
            kind='backbone', processes=edge['processes'],
            backbone_id=edge['id'], label=edge['item'], evidence=deepcopy(edge),
            calculation_included=decision['included'] and items[edge['item_id']]['category']!='equipment',
            score_excluded=items[edge['item_id']]['category']=='equipment',
            exclusion_reason='장비 공급은 소재 점수 제외 · 해설 대상' if items[edge['item_id']]['category']=='equipment' else decision['reason'])
    for p in original['processes']:
        for company in recipients[p]:
            own_edges = [e for e in original['edges'] if e['to']==company and p in e['processes']]
            required = []
            gap_ids = []
            for item_id in sorted({e['item_id'] for e in own_edges}):
                if items[item_id]['category']=='equipment':
                    continue
                originals = [e for e in own_edges if e['item_id'] == item_id]
                candidates = [e for e in originals if e['id'] in routes]
                if not candidates:
                    gap_id = f'{company}:{item_id}:{p}'
                    gap_ids.append(gap_id)
                    network['coverage_gaps'].append(dict(
                        id=gap_id, company=company, item_id=item_id, process=p,
                        excluded_edges=[e['id'] for e in originals],
                    ))
                    continue
                mix = f'mix:{company}:{item_id}'
                add(mix, items[item_id]['name']+' 투입 충족', 'mix', nodes[company]['country'],
                    nodes[company]['lat'], nodes[company]['lon'], visible=False, mode='mix',
                    requires=[routes[e['id']] for e in candidates], weights=[1.]*len(candidates))
                required.append(mix)
            op = f'operation:{company}:{p}'
            add(op, f'{nodes[company]["name"]} · {p}', 'operation', nodes[company]['country'],
                nodes[company]['lat'], nodes[company]['lon'], visible=False, requires=required,
                coverage_gap_ids=gap_ids)
            operations[(company,p)] = op
    # Each operation measures its own material inputs. Previous operations and
    # their manufactured output are not used to forecast production propagation.
    # Additional recipes extend the process DAG. Raw Ga/Ge never gate the default
    # silicon recipe, and only one package recipe is enabled at a time by the UI.
    targets = {'ceria':['산화','증착·이온주입','금속배선'], 'neon':['포토'],
        'fluorspar':['식각'], 'mask':['포토'], 'copper':['금속배선'],
        'tungsten':['증착·이온주입','금속배선'], 'gallium':['웨이퍼 제조'],
        'germanium':['증착·이온주입'], 'palladium':['패키징'], 'gold':['패키징'],
        'silver':['패키징'], 'tin':['패키징']}
    for material, ps in targets.items():
        sid = products[material]
        for p in ps:
            for company in recipients[p]:
                nodes[operations[(company,p)]]['requires'].append(sid)
                line(sid, company, calc_target=operations[(company,p)], processes=[p],
                     scope=nodes[sid]['scope'], label=nodes[sid]['name'])
    for p in original['processes']:
        marker = f'process:{p}'
        ids = [operations[(c,p)] for c in recipients[p]]
        # A process is a logical output, never a geographic point in the ocean.
        add(marker, p, 'process', '', None, None, visible=False, requires=ids,
            location_scope='비지리적 공정 지표; 지도 표시 없음')
        network['process_outputs'][p] = ids
    # Products used only by reference relationships must not request reserve pools.
    used_supplies = {(e['from'], e['item_id']) for e in original['edges'] if e['id'] in routes}
    for pair, sid in supplies.items():
        included = pair in used_supplies and not nodes[sid].get('score_excluded',False)
        nodes[sid]['calculation_included'] = included
        if not included:
            nodes[sid].update(alt_vendor=None, alt_capacity=0.)
    # All nodes expose the same editable resilience fields, including hidden nodes.
    for n in nodes.values():
        n['assumption_note'] = '재고·대체율·예약량·레시피·추가 납품경로는 가정값. 관측 생산량이 아님.'
    network['supplies'] = supplies
    network['operations'] = operations
    network['upstream_products'] = products
    extend_materials(network,add,line)
    apply_locations(network)
    network['scoring_policy'] = 'direct-material-fulfillment-v1'
    return attach_review(attach_coverage(add_logistics(network,add)))
