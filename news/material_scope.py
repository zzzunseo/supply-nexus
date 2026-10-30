"""Material-specific evidence scope; tariffs never become automatic production losses."""
from .vendor_candidates import match
from product_comparison import load_comparison_data

def material_scope(query):
    d=load_comparison_data();scope=None
    if any(w in query for w in ('희토류','산화세륨','세리아')) or match(query,'CeO2'):
        specific=any(w in query for w in ('산화세륨','세리아')) or match(query,'CeO2')
        scope=dict(kind='희토류·산화세륨',flow='산화세륨 연마재 → CMP 슬러리 배합 → STI·ILD CMP' if specific else '희토류 원소·제품 형태 확인 → 소재 직접 투입 / 장비 경유 영향 구분',
            needs=['대상 원소·산화물·자석 등 제품 형태','수입국·원산지·대상 품목·시점','CMP 대상 막·선택비·입자·결함 조건'],
            limits=['산화세륨 CMP 사례를 희토류 전체에 적용하지 않습니다.','관세는 조달 비용·거래 조건의 검토이며 공급 중단·고객 피해율을 뜻하지 않습니다.','제품 원산지·관세 적용은 기업 국적으로 추정하지 않습니다. 실제 세율·시행 여부는 별도 공식 자료 필요.','연마재는 완성 슬러리의 즉시 대체품이 아닙니다.'],source_ids=['solvay_ceria','nyacol_ceria'],specific=specific)
    elif any(w in query for w in ('불화수소','불산')) or match(query,'HF') or match(query,'BHF'):
        scope=dict(kind='불화수소',flow='HF 약액 → 습식 식각·세정 → 제품·공정별 적합성 검토',
            needs=['무수 HF / HF 수용액 / BHF 구분','질량 농도와 금속 불순물·입자 규격','등급별 CoA·고객 승인·공급 여력'],
            limits=['49%·50% 용액 농도는 49%·50% 순도 등급을 뜻하지 않습니다.','일반 HF, 무수 HF, 완충 HF를 자동 대체하지 않습니다.','SDS나 기업 고순도 홍보만으로 모든 금속의 ppt 보증치를 만들지 않습니다.'],source_ids=['daikin_hf','stella_hf','kanto_hf50'],specific=True)
    elif match(query,'ArF') or '포토레지스트' in query:
        scope=dict(kind='ArF 포토레지스트',flow='레지스트 제품군 → Dry/액침·이미징 톤 → 포토 공정 검토',
            needs=['ArF/KrF/EUV 제품군','Dry/액침 및 Positive/Negative 이미징','현상 방식·막두께·공정창·고객 승인'],
            limits=['ArF 제품군이 같아도 Dry와 액침, PTI와 NTI는 같은 제품이 아닙니다.','카탈로그의 예시 막두께·베이크 조건은 보증 허용범위가 아닙니다.'],source_ids=['fuji_arf','tok_arf'],specific=match(query,'ArF'))
    if not scope:return {}
    scope['sources']={sid:d['sources'][sid] for sid in scope['source_ids']}
    return scope

def render_material_scope(query):
    import streamlit as st
    scope=material_scope(query)
    if not scope:return
    st.info(scope['flow'])
    with st.expander('소재 범위·추가 확인 조건'):
        for item in scope['needs']:st.write('확인: '+item)
        for item in scope['limits']:st.caption(item)
        for source in scope['sources'].values():st.link_button(source['title'],source['url'])
