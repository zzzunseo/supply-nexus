"""Three-stage company, material and response comparison for published cases."""
import html
import streamlit as st
from .verified_globe import render_evidence_globe
from .overseas_material_case import SOURCE


def reset_verified_steps():
    st.session_state.verified_step=1
    st.session_state.verified_compare='대응 후'


def render_verified_steps(material):
    st.session_state.setdefault('verified_step',1)
    step=st.session_state.verified_step
    st.markdown('''<style>
    .verified-hero{padding:14px 18px;border:1px solid #28566b;border-left:4px solid #4fe4db;border-radius:12px;background:linear-gradient(110deg,#102b3e,#081321);margin:8px 0 14px}
    .verified-hero b{display:block;font-size:23px;color:#e4f6ff}.verified-hero span{display:block;margin-top:5px;font-size:14px;color:#b4ccdd;line-height:1.6}
    .verified-focus{padding:14px 16px;border:1px solid #31576d;border-radius:10px;background:#0b2030;margin:10px 0}.verified-focus strong{font-size:24px;color:#4fe4db;display:block}.verified-focus small{font-size:14px;color:#b9cfdf;line-height:1.7}
    </style>''',unsafe_allow_html=True)
    title='Freescale · 말레이시아 조립사업장' if material else 'Maersk · 홍해 사태와 희망봉 우회'
    subtitle='금 가격·조달 부담 → 제품 검증 → 금(Au)에서 PdCu로 전환' if material else '홍해 통항 위험 → 운항 조정 → 아프리카 남단 우회'
    st.markdown('<div class="verified-hero"><b>'+html.escape(title)+'</b><span>'+html.escape(subtitle)+'</span></div>',unsafe_allow_html=True)
    st.caption('공식 발표 기록 비교 · 지정 제품의 변경 통지와 검증 완료를 확인합니다. 앱이 수행한 재료 시험이나 출하 실적 검증은 아닙니다.' if material else '공식 발표 기록 비교 · 선사의 우회 결정을 확인합니다. 특정 반도체 화물의 실제 항적이나 생산 피해를 검증한 결과는 아닙니다.')
    for i,col in enumerate(st.columns(3),1):
        with col:st.button(str(i)+'　'+['기업·소재 연결','영향 범위','대응 비교'][i-1],key='verified_step_'+str(i),width='stretch',type='primary' if step==i else 'secondary',on_click=lambda n=i:st.session_state.update(verified_step=n))
    after=False
    if step==3:
        compare=st.segmented_control('대응 전후',['대응 전','대응 후'],key='verified_compare',default='대응 후',required=True,width='stretch')
        after=compare=='대응 후'
    left,right=st.columns([2,1])
    with left:
        render_evidence_globe('material' if material else 'shipping',step,after)
        st.caption('확인된 조립사업장 도시의 대표점입니다. 같은 사업장 안의 자재 변경이며 공장 이전·운송 경로가 아닙니다.' if material else '선사가 발표한 우회 방향을 연결한 개략도입니다. 실제 항적·화물 종류·반도체 고객은 확인 범위 밖입니다.')
    with right:
        if material:
            if step==1:
                st.subheader('기업과 사용 소재')
                st.write('기업: 당시 Freescale Semiconductor')
                st.write('거점: KLM 조립사업장 · 쿠알라룸푸르')
                st.write('공정: 패키징 · 와이어 본딩')
                focus='금(Au) 23μm';note='지정 제품에서 사용하던 본딩 와이어'
            elif step==2:
                st.subheader('무엇을 바꾸려 했나요?')
                st.write('변경 이유: 원재료 비용 상승 부담 완화와 공급 안정성 확보')
                st.write('범위: SPC5676·SPC5642·SPC5644·SPC5645 계열 중 PCN에 지정된 제품')
                focus='소재·직경 변경';note='같은 조립사업장 유지 · 생산 중단이나 피해율은 발표하지 않음'
            else:
                st.subheader('검증을 거친 소재 전환')
                focus='PdCu 20μm' if after else '금(Au) 23μm'
                note='팔라듐 코팅 구리 · 검증 완료가 명시된 대체 소재' if after else '기존 본딩 소재 · 전환 이전 조건'
                st.write('검증 자료 공개: 2014-06-02')
                st.write('변경 통지: 2014-06-24 / 효력일: 2014-09-22')
            st.markdown('<div class="verified-focus"><strong>'+focus+'</strong><small>'+note+'</small></div>',unsafe_allow_html=True)
            st.caption('공식 변경 통지와 검증 완료를 보여줍니다. 출하량·절감률·모든 제품의 전면 대체를 뜻하지 않습니다.')
            source=SOURCE
        else:
            st.subheader(['기업과 기존 통항 방향','통항 위험과 영향 범위','우회 전후 비교'][step-1])
            st.write('기업: A.P. Moller–Maersk · 해외 해운사')
            st.write('사건: 2023년 12월 홍해·아덴만의 안전 위험')
            if step==1:focus='홍해·수에즈 방향';note='기존 통항 방향을 개략적으로 표시'
            elif step==2:focus='운항 조정 필요';note='공식 안내에 선박별 우회 계획 명시 · 소재 공급 중단률은 미확인'
            else:focus='희망봉 우회' if after else '홍해·수에즈 방향';note='공식 발표된 우회 방향' if after else '우회 전 통항 방향 · 비교용 개략도'
            st.markdown('<div class="verified-focus"><strong>'+focus+'</strong><small>'+note+'</small></div>',unsafe_allow_html=True)
            st.write('공식 안내: 2023-12-18 / 대상 예: Maersk Hanoi·Maersk Athabasca')
            st.caption('물류 우회 사례입니다. 특정 반도체 소재의 선적 여부·고객사 생산 피해와 연결하지 않습니다.')
            source='https://www.maersk.com/~/media_sc9/maersk/local-information/files/asia-pacific/cambodia/overview/181223-temporary-vessel-diversion.pdf'
        st.markdown('[공식 원문 확인]('+source+')')
        if step<3:st.button('다음 단계 →',key='verified_next',type='primary',width='stretch',on_click=lambda:st.session_state.update(verified_step=step+1))
        if step>1:st.button('← 이전 단계',key='verified_previous',width='stretch',on_click=lambda:st.session_state.update(verified_step=step-1))
    if step==3:
        st.dataframe([{'비교 항목':'소재' if material else '통항 방향','대응 전':'금(Au) 23μm' if material else '홍해·수에즈 방향','대응 후':'PdCu 20μm' if material else '희망봉 방향'},
            {'비교 항목':'공식 확인','대응 전':'PCN의 기존 자재' if material else '기존 통항 방향 비교','대응 후':'지정 제품의 소재 검증 완료·변경 통지' if material else '선박별 우회 발표'},
            {'비교 항목':'해석 한계','대응 전':'실제 손실·생산 감소율 미산정','대응 후':'생산 회복률·운송 지연일 임의 계산 없음'}],hide_index=True)
