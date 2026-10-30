"""HTML fragments for cause and resilience cards."""
import html
from resilience_globe import COLORS


def advice_cards(network, result):
    candidates = []
    for k, n in network['entities'].items():
        r = result['nodes'][k]
        if n.get('calculation_included', True) and n['kind'] in ('product', 'material') and n['scope'] in result['scopes'] and (r['primary'] < 1 - 1e-07):
            candidates.append((k, n, r))
    candidates.sort(key=lambda row: (-row[2]['backup'], -row[2]['inventory'], row[2]['effective']))
    cards = []
    for k, n, r in candidates[:2]:
        alternative = network['nodes'].get(n['alt_vendor'], {})
        reserve = html.escape(alternative.get('name', '등록된 우회 없음'))
        color = COLORS['buffer'] if r['effective'] >= 1 - 1e-07 else COLORS['stopped'] if r['effective'] < 1e-07 else COLORS['reduced']
        cards.append(f"""<div class="rr-cause" style="--accent:{color}"><b>{html.escape(n['name'])}</b><div>기존 {r['primary'] * 100:.0f} + 재고 {r['inventory'] * 100:.0f} + 우회 {r['backup'] * 100:.0f} = <strong>{r['effective'] * 100:.0f}%</strong></div><small>{reserve}<br>재고 {n['inventory_days']:g}일 · 우회 한도 {n['alt_capacity'] * 100:g}% (가정)</small></div>""")
    if not cards:
        active = [n for n in network['nodes'].values() if n['kind'] in ('material', 'product') and n.get('scope', 'core') in result['scopes'] and not n.get('score_excluded', False)]
        inventory = [n['inventory_days'] for n in active]
        bypass = [n['alt_capacity'] * 100 for n in active]
        assumptions = f'활성 소재 재고 {min(inventory):g}~{max(inventory):g}일 · 우회 한도 {min(bypass):g}~{max(bypass):g}% (가정)' if active else '활성 소재 가정 없음'
        overall = result['overall']
        color = COLORS['normal'] if overall >= 100 - 1e-7 else COLORS['stopped'] if overall < 1e-7 else COLORS['reduced']
        description = '계산 경로 내 부족 없음 · 누락 제약의 정상 판정은 아닙니다.' if overall >= 100 - 1e-7 else '등록 소재 공급 부족 · 공정별 직접 투입재를 확인하세요.'
        cards = [f'<div class="rr-cause" style="--accent:{color}"><b>최저 소재 충족도 {overall:g}/100 <small>· 최악 기업</small></b><div>{description}</div><small>{assumptions}</small></div>']
    closed = [(k, p) for k, p in network.get('logistics', {}).items() if result['nodes'][k]['effective'] < 1 - 1e-07]
    if closed:
        affected = sum((any((result['nodes'][c]['effective'] < 1 - 1e-07 for c in r['via'])) and r['scope'] in result['scopes'] for r in network['logistics_routes'].values()))
        cards.insert(0, '<div class="rr-cause" style="--accent:#FF587B"><b>물류 병목 · ' + html.escape(' / '.join((p['name'] for _, p in closed))) + '</b><div>활성 경유 ' + str(affected) + '개 차질</div><small>해상 경유 가정 · 재고가 남으면 공정 점수는 방어됩니다.</small></div>')
    if result['tariffs']:
        t = result['tariffs'][-1]
        cards.insert(0, f"""<div class="rr-cause" style="--accent:#FFBE60"><b>관세 · 수입재 비용 위험</b><div>대상 수입재 지수 100 → <strong>{t['index']:.0f}</strong></div><small>전액 과세·전액 전가 가정 · 제품 원가와 별도</small></div>""")
    logistics = result.get('logistics', {})
    if logistics.get('totals', {}).get('dispatched', 0) > 1e-9:
        routes = logistics['routes'].values()
        today = sum(r['delivered'] for r in routes)
        cards.insert(0, f'<div class="rr-cause" style="--accent:#409CFF"><b>항만·항로 우회</b><div>오늘 공급 반영 {today:.2f} · 운송 중 {logistics["pending"]:.2f}</div><small>동일 비중 경로 수요 단위 · 실제 물량 아님<br>우회 발송분 운임지수 {logistics["detour_freight_index"]:.1f} (기준 100)<br>추가 비용이며 관세·제품 원가와 별도</small></div>')
    return ''.join(cards[:2])
