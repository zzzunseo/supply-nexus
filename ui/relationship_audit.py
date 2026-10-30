"""Compact provenance explorer; product vendors never imply customer contracts."""
import csv
import io
import streamlit as st
from relationship_audit import audit_relationships,vendor_catalog,scenario_routes


def csv_text(rows):
    output=io.StringIO()
    if rows:
        writer=csv.DictWriter(output,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    return output.getvalue()


def render_relationship_audit(network):
    audit=audit_relationships(network)
    with st.expander('공급 관계 · 소재별 벤더 · 시연 경로',expanded=False):
        st.caption('저장된 출처의 근거 범위에 따른 분류입니다. 현재 계약 전수 확인이나 산업 전체 목록은 아닙니다. 미등록은 영향 없음이 아닙니다.')
        st.caption('지도 실선은 기업 관계에 제품 용도를 연결한 시나리오입니다.  \n붉은 영역은 사건 위치 강조이며 피해 면적이 아닙니다.  \n점선 후보의 실행 가능성은 별도 확인합니다.')
        relationship,vendor,scenario,reference,public=st.tabs(['공급 관계 근거','소재별 벤더','시연 경로','추가 검토 기록','공개 계약 확장'])
        with relationship:
            rows=audit['supported']
            st.write(f'공급 관계 근거가 있는 품목 연결 {len(rows)}개')
            st.caption('같은 기업 관계가 여러 품목에 반복될 수 있습니다. 품목별 납품·현재 물량·공장·재고는 별도 확인하며, 지도 품목 연결은 시나리오 해석입니다.')
            st.dataframe([{'공급사':r['supplier'],'고객사':r['customer'],'검토 품목':r['material'],
                '자료 연도':str(r['year'] or '미기재'),'확인 기록일':r['checked_at'],
                '근거 범위':r['scope'],'출처':r['source']} for r in rows],hide_index=True)
        with vendor:
            catalog=vendor_catalog(network)
            items=sorted({r['product_group'] for r in catalog})
            labels={r['product_group']:r['material'].split(' · ')[-1] for r in catalog}
            selected=st.selectbox('벤더 품목 필터',['전체',*items],key='audit_vendor_item',format_func=lambda key:labels.get(key,key))
            shown=[r for r in catalog if selected=='전체' or r['product_group']==selected]
            st.write(f"제품 자료가 있는 벤더 {len({r['supplier'] for r in shown})}곳 · 제품 항목 {len(shown)}개")
            st.caption('제품 종류 자료가 있는 벤더입니다. 이 목록에서 고객 납품·등급 호환·여유 공급량을 추정하지 않습니다.')
            if selected!='전체':
                from .vendor_map import render_vendor_map
                render_vendor_map(network,selected,shown)
            else:st.caption('품목을 선택하면 벤더 위치와 등록된 고객 연결을 지도에 표시합니다.')
            st.dataframe([{'벤더':r['supplier'],'소재·제품':r['material'],'확인 기록일':r['checked_at'],
                           '제품 출처':r['source']} for r in shown],hide_index=True)
        with scenario:
            routes=scenario_routes(network)
            ports=sorted({p for r in routes for p in r['via'].split(' → ')})
            selected=st.selectbox('시연 경유지 필터',['전체',*ports],key='audit_route_port')
            shown=[r for r in routes if selected=='전체' or selected in r['via'].split(' → ')]
            st.write(f"시연 경로 {len(shown)}개 · 공급사 {len({r['supplier'] for r in shown})}곳 · 연결 대상 {len({r['customer'] for r in shown})}곳")
            st.caption('국가 기반으로 설정된 시연 경유입니다.  \n실제 화물·선박 항적을 확인한 연결이 아닙니다.  \n항만 발표 지도는 이 중 공급 관계 근거가 있는 품목 연결을 함께 보여줍니다.')
            st.dataframe([{'공급사':r['supplier'],'고객사':r['customer'],'소재':r['material'],
                           '가정 경유지':r['via']} for r in shown],hide_index=True)
        with reference:
            rows=audit['references']
            st.write(f'기본 발표 연결에서 제외한 기록 {len(rows)}개')
            st.dataframe([{'기업':r['supplier'],'상대 기업':r['customer'],'검토 품목':r['material'],
                '관계 종류':r['basis'],'시점 상태':r['temporal'],'분류 이유':r['reason'],
                '자료 연도':str(r['year'] or '미기재'),'출처':r['source']} for r in rows],hide_index=True)
            st.download_button('관계 분류 기록 내려받기',('\ufeff'+csv_text(audit['supported']+rows)).encode('utf-8'),
                               file_name='relationship-audit.csv',mime='text/csv',key='audit_download')

        with public:
            from .public_contracts import render_public_contracts
            render_public_contracts()
