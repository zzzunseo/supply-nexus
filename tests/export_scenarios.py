"""Regenerate the reviewable scenario matrix and complete JSON audit trail."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legacy.data_loader import load_demo
from legacy.simulation import load_model, build_simulation_payload

data = load_demo(ROOT / 'data' / 'demo.json')
model = load_model(ROOT / 'data' / 'simulation_demo.json', data)
data['scenarios'] += model['additional_scenarios']
payload = build_simulation_payload(data, model)
(ROOT / 'simulation_examples.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
lines = ['# 시나리오별 공정 점수 검증', '',
         '조건: 14일, 중단 강도 100%, 재고 적용, 대체 공급 미적용. 모든 배분율과 완충값은 검증용 가정입니다.', '',
         '| 시나리오 | ' + ' | '.join(data['processes']) + ' | 전체 | 병목 |',
         '|' + '---|'*(len(data['processes'])+3)]
for name, report in payload['reports'].items():
    values = ' | '.join(f"{p['score']:.1f}" for p in report['processes'])
    bottleneck = ', '.join(report['bottlenecks']) or '없음'
    lines.append(f"| {name} | {values} | {report['overall_score']:.1f} | {bottleneck} |")
lines += ['', '## 손계산 예제', '', '10일 동안 공급처 X는 50%, Y는 100% 가동합니다.', '',
          '- 투입재 A: 60% × 50% + 40% × 100% = 70%',
          '- 투입재 B: 100% × 50% + 대체 10% + 재고 1일 ÷ 10일 = 70%',
          '- 투입재 C: 100% × 100% = 100%',
          '- AND 공정 점수: 100 × min(0.7, 0.7, 1.0) = **70점**', '',
          '`test_three_inputs_hand_calculation`에서 같은 조건을 검증합니다.', '',
          '## 해석', '',
          '각 공정 점수는 해당 공정 자체의 필수 투입재 가용률입니다. 직렬 상한은 공정 순서대로 누적 최솟값을 취합니다.',
          '가용률이 100%일 때 정상, 0% 초과 100% 미만일 때 주의, 0%일 때 중단으로 표시합니다.',
          '동률인 병목은 모두 반환합니다. 정상 상태에서는 병목을 표시하지 않습니다.']
(ROOT / 'docs' / 'SIMULATION_RESULTS.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print('Exported SIMULATION_RESULTS.md and simulation_examples.json for 5 scenarios.')
