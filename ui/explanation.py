"""Grounded material-availability explanation; no production cascade forecast."""
import html
from simulation.reporting import score_view
from .process_comparison import view_label


def current_explanation(network, result, state, compact=False):
    view_key = state.get('rr_score_view', 'worst')
    view = score_view(result, view_key)
    label = view_label(result, view_key)
    scores = view['scores']
    supported = [p for p,v in scores.items() if v is not None]
    affected = sorted(((p, v) for p, v in scores.items() if v is not None and v < 100 - 1e-7), key=lambda row: row[1])
    paragraphs = []
    if affected:
        names = ' · '.join(f'{p} {v:.0f}' for p,v in affected[:3])
        paragraphs.append(f"{result['duration_days']}일째, {label} 기준 소재 부족 공정은 {len(affected)}개입니다. 주요 소재 충족도: {names}.")
        shortages = [row for row in result.get('material_shortages', []) if view_key in ('worst','mean') or row['company']==view_key]
        names = list(dict.fromkeys(row['name'] for row in sorted(shortages,key=lambda row:row['fulfillment'])))
        if names:
            paragraphs.append('부족한 등록 소재: ' + ' · '.join(names[:3]) + '.')
        paragraphs.append('후속 생산에 영향을 줄 가능성은 있지만, 감소율과 발생 시점은 산정하지 않습니다. 다른 공정의 소재 점수로 자동 전파하지 않습니다.')
    elif supported:
        paragraphs.append(f"관측 {result['duration_days']}일째, {label} 기준 산정 가능한 등록 소재에서 공급 부족이 계산되지 않았습니다. 실제 생산 정상 여부와는 별도입니다.")
    else:
        paragraphs.append(f'{label} 보기는 활성 소재 입력이 등록되지 않아 소재 충족도를 산정하지 않습니다.')
    first = min(view['first_hit'].values(), default=None)
    if first is not None:
        paragraphs.append(f'현재 재고·대체 공급 가정에서 첫 소재 부족은 {first}일째입니다. 실제 부족일 예측은 아닙니다.')
    process = state.get('rr_process', '전체')
    if process != '전체':
        value = scores.get(process)
        paragraphs.append(f'선택 공정 {process}의 직접 소재 충족도는 {value:.0f}/100입니다.' if value is not None else f'선택한 {process} 공정은 활성 소재 입력이 미등록이므로 미산정입니다.')
    categories = {row['category'] for row in result.get('context_impacts', [])}
    if 'equipment' in categories:
        paragraphs.append('장비 공급 제한 이슈는 신규 조달·증설·교체 위험으로 별도 해설하며 소재 점수를 낮추지 않습니다. 기존 장비 고장·정비 중단의 가동 영향도 별도 정보 없이는 산정하지 않습니다.')
    if 'cost' in categories:
        paragraphs.append('관세는 비용 이슈로 분리하며 소재 점수를 낮추지 않습니다. 상세 가격지수는 대상 수입재 전액 과세·전액 전가 가정이며 실제 제품 원가 상승률이 아닙니다.')
    if 'facility' in categories:
        paragraphs.append('생산 기업의 설비·가동 차질 자체는 소재 충족도와 구분합니다. 등록된 소재 공급자로서의 공급 감소만 해당 소재 경로에 반영합니다.')
    focus = state.get('rr_focus')
    target = network['entities'].get(focus)
    if target and focus in result['nodes']:
        value = result['nodes'][focus]
        if target.get('score_excluded'):
            paragraphs.append(f"선택 대상 {target['name']}은 소재 점수에서 제외된 장비·참고 품목입니다.")
        elif target['kind'] in ('material','product'):
            paragraphs.append(f"선택 소재 {target['name']}: 기존 공급 {value['primary']*100:.0f}%, 재고 보완 {value['inventory']*100:.0f}%, 우회 보완 {value['backup']*100:.0f}%를 반영한 유효 공급 {value['effective']*100:.0f}%입니다.")
        else:
            paragraphs.append(f"선택 대상 {target['name']}의 시설 가동률은 예측하지 않습니다. 연결된 소재 경로의 충족도를 확인하세요.")
    shown=paragraphs[:2] if compact else paragraphs
    return '<div class="rr-explanation">' + ''.join('<p>'+html.escape(p)+'</p>' for p in shown) + '</div>'
