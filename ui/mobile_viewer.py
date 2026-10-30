"""Presentation summary and official references for QR visitors."""
import streamlit as st

CASES={
    'fire':dict(title='공장 화재 → 다른 기업의 칩 채택',kind='기업·부품 대체',date='2020년 화재 · 특정 고객 제품의 대응 기록',
        intro='AKM 공장 화재 이후, RME가 다른 제조사의 칩을 채택한 기록을 살펴봅니다.',
        chain=[('사건','AKM 노베오카 공장 화재'),('관련 제품','RME ADI-2 DAC의 AKM 칩'),('대응','ESS ES9028Q2M 채택')],
        takeaway='공장 피해가 고객 제품의 부품 조달 제약으로 연결되고, 설계·부품 전환으로 대응한 사례입니다.',
        process='완성 반도체 부품의 채택·설계 변경',
        limit='특정 RME 제품의 전환 기록입니다. 웨이퍼 제조 공정 중단이나 다른 고객 전체의 피해·즉시 호환성을 뜻하지 않습니다.',
        sources=[('AKM 공식 화재 안내','https://www.akm.com/jp/ja/about-us/news/information/20201030-information/'),('RME 공식 매뉴얼 · 4쪽','https://www.rme-audio.de/download/adi2dacr_e.pdf')]),
    'material':dict(title='금 와이어 → 팔라듐 코팅 구리',kind='소재 대체',date='Freescale PCN 16152 · 2014년 변경 공지',
        intro='말레이시아 조립사업장의 지정 제품에서, 검증을 거쳐 와이어 소재를 바꾼 기록입니다.',
        chain=[('기존 소재','금(Au) 와이어'),('전환 조건','지정 제품의 검증 완료'),('대체 소재','팔라듐 코팅 구리(PdCu)')],
        takeaway='같은 공정에 쓰이는 소재도 제품·공정 검증을 거쳐 전환합니다.',process='패키징 · 와이어 본딩',
        limit='지정 제품의 검증 완료·변경 공지입니다. 전체 제품의 실제 전환 물량·절감률이나 공장 이전을 확인한 자료는 아닙니다.',
        sources=[('NXP 보관 공식 변경 공지','https://www.nxp.com/docs/en/product-change-notice/PCN16152.htm')]),
    'route':dict(title='홍해 통항 차질 → 희망봉 우회',kind='물류 우회',date='Maersk · 2023–2024년 과거 대응 사례',
        intro='홍해의 안전 우려에 대응해 선사가 희망봉 우회를 발표한 사례입니다.',
        chain=[('운송 차질','홍해·수에즈 통항 위험'),('대응','희망봉 우회 발표'),('확인할 조건','운항편·화물·추가 운송 시간')],
        takeaway='물류 차질에는 항로 변경을 검토할 수 있습니다. 생산 공장 중단과는 대응 경로가 다릅니다.',process='물류 · 특정 반도체 공정 직접 연결 미확인',
        limit='과거 선사 발표입니다. 현재 운항·예약 가능 여부나 특정 반도체 기업의 실제 화물을 확인한 것은 아닙니다.',
        sources=[('Maersk 공식 우회 안내','https://www.maersk.com/~/media_sc9/maersk/local-information/files/asia-pacific/cambodia/overview/181223-temporary-vessel-diversion.pdf')])}



def render_mobile_viewer():
    st.markdown('''<style>
    [data-testid="stHeader"],footer,[data-testid="stSidebar"]{display:none}
    .block-container{max-width:740px;padding:1.2rem 1rem 3rem}
    .mobile-brand{font-size:13px;font-weight:750;color:#4de5f4;letter-spacing:2px;margin:8px 0}
    .block-container h1{font-size:32px;line-height:1.3;letter-spacing:-.6px}
    .block-container h2,.block-container h3{line-height:1.45}
    .block-container p,.block-container h1,.block-container h2,.block-container h3{word-break:keep-all;overflow-wrap:break-word}
    .block-container p{line-height:1.8}
    .mobile-lead{font-size:19px;color:#d8edf4;line-height:1.6;margin:6px 0 18px;word-break:keep-all}
    .mobile-demo{padding:18px;border:1px solid #29475a;border-radius:14px;background:#0b1928;margin:12px 0}
    .mobile-demo small{color:#58dcd5;letter-spacing:.06em;font-size:12px}
    .mobile-demo h3{font-size:20px!important;margin:8px 0!important;padding:0!important;color:#edf5fa}
    .mobile-demo p{font-size:15px;color:#b9cddd;margin:0 0 10px}
    .mobile-demo .result{border-top:1px solid #263e50;padding-top:10px;margin-bottom:0;color:#d4e5ef;font-size:14px}
    .stLinkButton a{min-height:48px;width:100%;border-radius:10px}
    [data-testid="stCaptionContainer"]{line-height:1.7}
    @media(max-width:600px){.block-container{padding-top:1rem}h1{font-size:26px!important}h2{font-size:22px!important}}
    </style>''',unsafe_allow_html=True)
    st.markdown('<div class="mobile-brand">SUPPLY NEXUS</div>',unsafe_allow_html=True)
    st.title('반도체 공급망, 연결에서 대응까지')
    st.markdown('<div class="mobile-lead">어디에 차질이 생기면, 어떤 공정과 연결되고 무엇을 더 확인해야 할까요?</div>',unsafe_allow_html=True)
    st.info('휴대폰에서는 소개와 근거를 확인하고, 전체 기능은 현장에서 노트북으로 시연합니다.')
    st.write('SUPPLY NEXUS는 기업·소재·공정·물류의 연결을 지도에서 살펴보고, 공개 제품 자료로 대응 후보의 조건을 비교하는 프로젝트입니다.')
    st.caption('이 화면은 발표 안내입니다. 노트북의 선택 상태나 AI 결과를 실시간으로 공유하지 않습니다.')
    st.subheader('노트북에서 이렇게 보여드립니다')
    demos=[
        ('01 · 영향 연결','공급 차질 → 관련 공정 → 대응 후보',
         'JSR 포토레지스트 공급 차질을 가정하고, 등록된 고객·공정 연결과 대응 후보를 지도에서 확인합니다.',
         '직접 바꿔보기: 적용 전·후 전환, ArF·EUV 제품군 선택. 기간과 감소율은 시연 가정입니다.'),
        ('02 · 제품 조건 비교','ArF / Dry 조건에 맞는 제품 찾기',
         'JSR과 동진쎄미켐의 공개 제품 자료를 나란히 놓고 노광 방식과 제품군의 공통점·차이를 확인합니다.',
         '확인할 결과: 공개 조건 일치, 불일치, 자료 미확인을 구분합니다. 고객 공정에 즉시 투입 가능하다는 판정은 아닙니다.'),
        ('03 · 기준 변경','NF3 가스의 순도·불순물 조건 비교',
         '순도와 수분·CF4 허용 기준을 바꾸며 MATHESON·EFC·Linde 제품의 판정이 어떻게 달라지는지 살펴봅니다.',
         '확인할 결과: 선택 기준에 따른 후보 변화와 그 근거. 전체 공급사의 최적 순위를 매기는 기능은 아닙니다.')]
    import html
    for label,title,body,result in demos:
        st.markdown('<article class="mobile-demo"><small>'+html.escape(label)+'</small><h3>'+html.escape(title)+'</h3><p>'+html.escape(body)+'</p><p class="result">'+html.escape(result)+'</p></article>',unsafe_allow_html=True)
    st.subheader('AI는 무엇을 도와주나요?')
    st.write('선택한 제품의 공개 자료와 비교 결과를 설명하고, 입력한 기사에서 근거 문장을 찾아 사건 내용을 요약합니다. 사건·공정 영향 조사 화면에서도 확인할 근거와 조건을 검토할 수 있습니다.')
    with st.expander('AI 해설과 코드 판정의 역할'):
        st.markdown('**코드**는 등록 정보·제품 조건과 인용 일치 등을 검사합니다. **AI**는 근거를 바탕으로 차이와 추가 확인 사항을 설명합니다.')
        st.write('API 연결 및 일부 실제 응답을 확인했습니다. 모든 입력에 대한 정확성을 검증한 것은 아니며, 해설은 원문과 대조해야 합니다.')
        st.caption('이 페이지는 AI 실시간 분석 결과가 아닙니다. 휴대폰에서 API 키를 입력하거나 AI 요청을 실행하지 않습니다.')
    with st.expander('확인할 수 있는 것과 추가 확인이 필요한 것'):
        st.markdown('**제공하는 것** · 등록된 관계와 위치, 공개 제품 조건 비교, 근거 링크, 대응 후보의 확인 항목')
        st.markdown('**추가 확인할 것** · 현재 계약, 고객 승인, 여유 생산능력, 재고, 실제 출하 공장·운송 경로')
        st.write('지도에는 본사·기술센터 등도 포함됩니다. 지도 위치를 생산공장으로 단정하지 않으며, 뉴스만으로 공급 감소율·차질 기간·고객 손실을 산정하지 않습니다.')
    st.subheader('대표 사례와 공식 출처')
    st.caption('아래 사례는 공식 기록을 요약한 것입니다. 프로젝트가 대체 방법을 발견하거나 직접 검증한 결과는 아닙니다.')
    requested=st.query_params.get('case')
    for key,case in CASES.items():
        with st.expander(case['kind']+' · '+case['title'],expanded=key==requested):
            st.caption(case['date'])
            st.write(case['intro'])
            st.markdown('**핵심 연결** · '+' → '.join(value for _,value in case['chain']))
            st.markdown('**확인 범위**')
            st.write(case['limit'])
            for title,url in case['sources']:st.link_button(title,url,width='stretch')
    st.divider()
    st.caption('자료 확인 기록: 2026-10-29 · 과거 발표와 현재 공급·운항 상황은 구분해야 합니다.')
    st.caption('공개 자료는 기업 관계와 제품 용도의 검토 근거입니다. 실제 피해 규모·현재 계약·고객 인증·추가 공급량은 별도 확인 대상입니다.')
