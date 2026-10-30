"""Presenter-controlled QR for the read-only mobile introduction."""
from io import BytesIO
from urllib.parse import urlsplit, urlunsplit, urlencode
import streamlit as st


def mobile_url(value):
    try:
        parts=urlsplit(value.strip())
        if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password:
            return None
        if parts.hostname.lower() in ('localhost','127.0.0.1','::1','0.0.0.0'):
            return None
        return urlunsplit((parts.scheme,parts.netloc,parts.path or '/',urlencode({'view':'mobile'}),''))
    except ValueError:
        return None


def render_presentation_qr():
    with st.expander('휴대폰 안내 · QR 표시',expanded=False):
        st.caption('관람객에게 프로젝트 소개·노트북 시연 내용·공식 출처를 제공합니다.')
        value=st.text_input('휴대폰에서 접속 가능한 앱 주소',placeholder='https://배포주소 또는 http://노트북IP:포트',key='presentation_public_url')
        st.caption('같은 Wi-Fi 주소 또는 배포 주소를 사용하세요. 주소 입력만으로 서버가 공개되지는 않습니다.')
        if not value:return
        url=mobile_url(value)
        if not url:
            st.warning('휴대폰에서 열 수 있는 http/https 주소를 입력하세요. localhost·127.0.0.1은 사용할 수 없습니다.')
            return
        import qrcode
        output=BytesIO()
        qrcode.make(url,border=4,box_size=10).save(output,format='PNG')
        st.image(output.getvalue(),width=240,caption='SUPPLY NEXUS · 프로젝트 소개와 시연 안내')
        st.link_button('휴대폰 안내 페이지 열기',url)
        st.download_button('QR 이미지 내려받기',output.getvalue(),file_name='supply-nexus-mobile-qr.png',mime='image/png')
        st.caption('배포 전 휴대폰 카메라로 접속을 확인하세요. 노트북의 시연 선택·API 키는 이 페이지에 공유되지 않습니다.')
