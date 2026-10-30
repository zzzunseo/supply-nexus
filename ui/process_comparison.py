"""Company-level comparison, with unsupported processes and evidence gaps visible."""
import json
import streamlit as st
from simulation.reporting import score_view


VIEW_LABELS = {'worst': '최악 기업', 'mean': '기업 평균', 'samsung': '삼성전자',
               'tsmc': 'TSMC', 'ase': 'ASE', 'amkor': 'Amkor'}


def view_label(result, key):
    return VIEW_LABELS.get(key, result['company_names'].get(key, key))


def formatted_score(view, process):
    value = view['scores'][process]
    if value is None:
        return '— 미산정'
    return f'{value:g}' + ('*' if process in view['incomplete_processes'] else '')


def comparison_rows(result):
    rows = []
    for process in result['scores']:
        row = {'공정': process}
        for company in result['company_names']:
            row[view_label(result, company)] = formatted_score(score_view(result, company), process)
        row['최악 기업'] = formatted_score(score_view(result, 'worst'), process)
        row['기업 단순평균'] = formatted_score(score_view(result, 'mean'), process)
        row['등록 기업 수'] = sum(process in processes for processes in result['company_processes'].values())
        rows.append(row)
    return rows


def report_payload(result, events):
    return dict(
        duration_days=result['duration_days'], scopes=result['scopes'], events=events,
        scoring_policy=result.get('scoring_policy'),
        material_shortages=result.get('material_shortages',[]),
        context_impacts=result.get('context_impacts',[]),
        unscored_operations=result.get('unscored_operations',[]),
        company_names=result['company_names'], company_processes=result['company_processes'],
        process_views=result['process_views'], coverage_gaps=result['coverage_gaps'],
        aggregation_note=result['aggregation_note'],
        logistics=result.get('logistics', {}),
        overall_note='각 보기에서 산정 가능한 공정 소재 충족도의 최솟값. 전체 산업 생산량이나 개별 시설 가동률이 아닙니다.',
    )


@st.dialog('기업별 공정 점수와 모델 범위', width='large')
def show_process_comparison(result):
    st.caption('삼성·TSMC는 전공정 7개, ASE·Amkor는 패키징 모델입니다.  \n개별 실제 팹의 가동률이 아닙니다.  \nSK하이닉스·인텔·마이크론 등은 미포함입니다.')
    st.dataframe(comparison_rows(result), hide_index=True, height=340)
    st.caption('각 공정의 최악 기업 = 등록 기업 중 최솟값.  \n기업 단순평균 = 해당 공정 등록 기업의 동일 비중 평균.  \n생산량·시장 점유율 가중평균이 아닙니다.  \n—는 미등록 또는 활성 소재 미등록으로 미산정이며 0이나 100으로 채우지 않습니다.')
    st.caption('\\*는 누락된 필수 투입재 제약이 있는 부분 모델입니다.  \n개별 기업과 집계 모두 누락 범위를 이어받습니다.  \n100\\*도 정상 공급을 보장하지 않습니다.')
    selected = st.selectbox('누락 범위를 확인할 기업', list(result['company_names']), format_func=lambda key: view_label(result, key))
    view = score_view(result, selected)
    suffix = '*' if view['incomplete_processes'] else ''
    display = f"{view['overall']:g}{suffix}/100" if view['overall'] is not None else '미산정'
    st.write(f"최저 소재 충족도 {display} · 해당 공정에 등록된 소재만 계산")
    gaps = {gap['id']: gap for gap in result['coverage_gaps']}
    rows = [dict(영향공정=process, 누락품목=gaps[gap_id]['item_id'], 원래기업=view_label(result, gaps[gap_id]['company']))
            for process, ids in view['incomplete_processes'].items() for gap_id in ids]
    if rows:
        st.dataframe(rows, hide_index=True)
    else:
        st.caption('등록 경로 내 구조적 누락 표시 없음. 실제 계약·물량의 완전한 검증을 의미하지 않습니다.')
    payload = report_payload(result, st.session_state.rr_events)
    st.download_button('기업별·집계·일별 결과 저장', json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'), 'company-process-report.json', 'application/json')
