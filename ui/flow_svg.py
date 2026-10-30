"""One server-rendered SVG with fixed columns and non-interactive cards."""
from html import escape
import unicodedata
from flow_selection import flow_emphasis


WIDTH = 720
CARD_WIDTH = 142
COLUMN_X = (16, 198, 380, 562)
KIND_LABELS = {'company': '기업', 'material': '소재', 'process': '공정'}
STATE_COLORS = {'normal': '#58DCD1', 'reduced': '#FFC46C', 'stopped': '#FF7894',
                'excluded': '#9AAFC3', 'unknown': '#B5C5D5'}


def wrap_name(name, budget=9):
    """Wrap full names conservatively, including long unspaced Korean/Latin text."""
    lines = []
    current = ''
    used = 0.0
    for character in str(name):
        units = 1.0 if unicodedata.east_asian_width(character) in ('W', 'F') else .6
        if character != '\n' and current and used + units > budget and ' ' in current.rstrip():
            split = current.rstrip().rfind(' ') + 1
            lines.append(current[:split])
            current = current[split:]
            used = sum(1.0 if unicodedata.east_asian_width(c) in ('W', 'F') else .6 for c in current)
        if character == '\n' or (current and used + units > budget):
            lines.append(current)
            current = ''
            used = 0.0
        if character != '\n':
            current += character
            used += units
    if current:
        lines.append(current)
    return lines or ['']


def state_text(card):
    status = card['status']
    reduction = card['reduction_pct']
    if status == 'excluded':
        return '— 계산 제외'
    if status == 'unknown' or reduction is None:
        return '？ 미확인'
    if status == 'stopped':
        return '× 중단 · 감소 100%'
    symbol = '△' if status == 'reduced' else '●'
    return f'{symbol} 감소 {reduction:g}%'


def material_details(card):
    if card['kind'] != 'material':
        return []
    if card['status'] == 'excluded':
        return ['재고·우회 계산 제외']
    evidence = card.get('evidence', {})
    stock = evidence.get('stock_remaining_days')
    backup = evidence.get('backup_active_pct')
    basis = evidence.get('basis', {})
    product = {'documented': '제품 종류 근거 있음', 'family_only': '제품군 자료만 있음'}
    provenance = [product.get(basis.get('product_basis'), '제품 종류 미확인'),
                  '용도 근거·조건부' if basis.get('technical_use_basis') == 'documented' else '공정 용도 미확인',
                  '실제 납품·필수 사용 미확인']
    condition = basis.get('condition')
    if condition and ('DUV' in condition or 'CMP' in condition or '챔버' in condition):
        provenance.extend(wrap_name(condition, budget=11))
    provenance = [line for detail in provenance for line in wrap_name(detail, budget=11)]
    return provenance + [
        '가정 재고 잔여 미확인' if stock is None else f'가정 재고 잔여 {stock:g}일',
        '모델 우회 미확인' if backup is None else f'모델 우회 활성 {backup:g}%',
    ]


def render_flow_svg(flow, company_numbers=None, compact=False):
    """Return a standalone SVG, using only the supplied read-only flow data."""
    company_numbers = company_numbers or {}
    active_cards, active_edges = flow_emphasis(flow)
    focused = flow.get("selected") is not None
    outgoing = {}
    for edge in flow['connections']:
        outgoing.setdefault(edge['from'], []).append(edge)
    positions = {}
    drawings = []
    bottom = 148
    supplier_order = {card['id']: index for index, card in enumerate(flow['columns'][0]['cards'])}
    material_order = {
        edge['to']: supplier_order[edge['from']]
        for edge in flow['connections'] if edge['from'] in supplier_order
    }
    for column_index, column in enumerate(flow['columns']):
        x = COLUMN_X[column_index]
        y = 48
        ordered = column['cards']
        if column['id'] == 'materials':
            ordered = sorted(ordered, key=lambda card: (material_order.get(card['id'], len(supplier_order)), card['id']))
        for card in ordered:
            lines = wrap_name(card['name'])
            details = [] if compact else material_details(card)
            height = max(84, 50 + len(lines) * 17 + len(details) * 14,
                         36 * (len(outgoing.get(card['id'], [])) + 1))
            positions[card['id']] = (x, y, CARD_WIDTH, height)
            drawings.append((card, lines, x, y, height))
            y += height + 14
        bottom = max(bottom, y + 8)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" class="rr-flow-svg" '
        f'viewBox="0 0 {WIDTH} {bottom}" width="{WIDTH}" height="{bottom}" '
        f'role="img" font-family="Malgun Gothic,Apple SD Gothic Neo,Arial,sans-serif" '
        f'aria-label="{escape(flow["process"], quote=True)} 공급 흐름">',
        '<defs>',
    ]
    for status, color in STATE_COLORS.items():
        parts.append(f'<marker id="flow-arrow-{status}" viewBox="0 0 8 8" refX="7" refY="4" '
                     f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
                     f'<path d="M0 0 L8 4 L0 8 Z" fill="{color}"/></marker>')
    parts.append('</defs>')
    parts.append(f'<rect width="{WIDTH}" height="{bottom}" fill="#081524"/>')
    for index, column in enumerate(flow['columns']):
        x = COLUMN_X[index]
        parts.append(f'<text x="{x + CARD_WIDTH / 2}" y="25" text-anchor="middle" '
                     f'fill="#DCEAF8" font-size="13" font-weight="700">{escape(column["name"])}</text>')
        if index < 3:
            parts.append(f'<text x="{x + CARD_WIDTH + 20}" y="25" text-anchor="middle" '
                         'fill="#8EAEC6" font-size="16">→</text>')

    for edge in flow['connections']:
        if edge['from'] not in positions or edge['to'] not in positions:
            raise ValueError('흐름 연결의 카드가 없습니다.')
        sx, sy, sw, sh = positions[edge['from']]
        tx, ty, tw, th = positions[edge['to']]
        branches = outgoing[edge['from']]
        branch = next(index for index, item in enumerate(branches) if item['id'] == edge['id'])
        start_y = sy + sh * (branch + 1) / (len(branches) + 1)
        end_y = ty + th / 2
        if sx == tx:
            lane = sx + sw + 18
            path = f'M {sx + sw} {start_y} C {lane} {start_y}, {lane} {end_y}, {tx + tw} {end_y}'
        else:
            middle = (sx + sw + tx) / 2
            path = f'M {sx + sw} {start_y} C {middle} {start_y}, {middle} {end_y}, {tx} {end_y}'
        status = edge['status'] if edge['status'] in STATE_COLORS else 'unknown'
        color = STATE_COLORS[status]
        dash = ' stroke-dasharray="5 4"' if edge['excluded'] else ''
        emphasized = edge['id'] in active_edges
        opacity = '.95' if emphasized else '.18'
        width = '3.2' if focused and emphasized else '1.8'
        parts.append(f'<path data-emphasis="{str(emphasized).lower()}" data-connection-id="{escape(edge["id"], quote=True)}" d="{path}" '
                     f'fill="none" stroke="{color}" stroke-width="{width}" opacity="{opacity}"{dash} '
                     f'marker-end="url(#flow-arrow-{status})"/>')

        badges = []
        if edge['excluded']:
            badges.append('제외')
        if edge['assumption']:
            badges.append('가정')
        for index, badge in enumerate(badges):
            bx = sx + sw + 3
            by = start_y - 15 + index * 16
            parts.append(f'<rect data-edge-badge="{escape(edge["id"], quote=True)}" '
                         f'data-badge="{badge}" opacity="{opacity}" '
                         f'x="{bx}" y="{by}" width="30" height="14" rx="3" '
                         'fill="#10263A" stroke="#9AAFC3"/>')
            parts.append(f'<text x="{bx+15}" y="{by+10.5}" text-anchor="middle" '
                         f'opacity="{opacity}" fill="#E3EDF7" font-size="10">{badge}</text>')


    for card, lines, x, y, height in drawings:
        color = STATE_COLORS.get(card['status'], STATE_COLORS['unknown'])
        emphasized = card['id'] in active_cards
        opacity = '1' if emphasized else '.35'
        parts.append(f'<g opacity="{opacity}" data-emphasis="{str(emphasized).lower()}" data-card-id="{escape(card["id"], quote=True)}" '
                     f'data-kind="{card["kind"]}" data-status="{card["status"]}" '
                     f'data-x="{x}" data-y="{y}" data-width="{CARD_WIDTH}" data-height="{height}">')
        border = '3' if focused and emphasized else '1.5'
        attributes = f'fill="#10263A" stroke="{color}" stroke-width="{border}"'
        if card['kind'] == 'process':
            points = f'{x+10},{y} {x+CARD_WIDTH-10},{y} {x+CARD_WIDTH},{y+height/2} '
            points += f'{x+CARD_WIDTH-10},{y+height} {x+10},{y+height} {x},{y+height/2}'
            parts.append(f'<polygon points="{points}" {attributes}/>')
        else:
            radius = 14 if card['kind'] == 'material' else 0
            parts.append(f'<rect x="{x}" y="{y}" width="{CARD_WIDTH}" height="{height}" rx="{radius}" {attributes}/>')
        number = company_numbers.get(card['node_id']) if card['kind'] == 'company' else None
        label = KIND_LABELS[card['kind']] + (f' · {number}' if number else '')
        parts.append(f'<text x="{x+12}" y="{y+18}" fill="#9FBAD0" font-size="10">{escape(label)}</text>')
        for index, line in enumerate(lines):
            parts.append(f'<text class="flow-name" x="{x+12}" y="{y+39+index*17}" '
                         f'fill="#F0F6FC" font-size="12.5" font-weight="600">{escape(line)}</text>')
        for index, detail in enumerate([] if compact else material_details(card)):
            parts.append(f'<text class="flow-evidence" x="{x+12}" '
                         f'y="{y+39+len(lines)*17+index*14}" fill="#CFDEEC" font-size="10">'
                         f'{escape(detail)}</text>')
        parts.append(f'<text x="{x+12}" y="{y+height-10}" fill="{color}" font-size="11">'
                     f'{escape(state_text(card))}</text>')
        parts.append('</g>')

    if not drawings:
        parts.append('<text x="360" y="90" text-anchor="middle" fill="#B5C5D5" font-size="14">'
                     '해당 공정에 표시할 공급 관계가 없습니다.</text>')
    parts.append('</svg>')
    return ''.join(parts)
