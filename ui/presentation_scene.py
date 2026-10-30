"""Portable review scenes and conditional propagation, without inferred readiness."""
import io
import json
from pathlib import Path
import streamlit as st


def depletion(days,reduction,stock):
    threshold=stock/(reduction/100) if reduction else None
    return threshold if threshold is not None and threshold<days else None


def restore_scene(payload,rows,ports):
    if not isinstance(payload,dict):raise ValueError('장면은 JSON 객체여야 합니다.')
    if not isinstance(payload.get('port'),str):raise ValueError('항만 형식을 확인하세요.')
    if type(payload.get('schema')) is not int or payload.get('schema')!=1 or payload.get('port') not in ports:raise ValueError('지원하지 않는 장면 또는 항만입니다.')
    settings=payload['assumptions']
    if not isinstance(settings,dict):raise ValueError('가정값 형식을 확인하세요.')
    for key,low,high in [('days',1,365),('reduction_percent',0,100),('stock_days',0,365)]:
        value=settings[key]
        if type(value) is not int or not low<=value<=high:raise ValueError('가정값의 범위를 확인하세요.')
    keys=[(r['supplier'],r['recipient'],r['target']) for r in rows]
    raw=payload['connections']
    if not isinstance(raw,list) or not 1<=len(raw)<=len(keys):raise ValueError('연결 개수를 확인하세요.')
    if any(not isinstance(k,list) or len(k)!=3 or any(not isinstance(v,str) for v in k) for k in raw):raise ValueError('연결 형식을 확인하세요.')
    requested=[tuple(k) for k in raw]
    if len(set(requested))!=len(requested):raise ValueError('중복 연결은 허용하지 않습니다.')
    if not requested or any(k not in keys for k in requested):raise ValueError('현재 자료에 없는 공급 연결이 포함되어 있습니다.')
    return dict(integrated_port=payload['port'],integrated_rows=[keys.index(k) for k in requested],
        integrated_days=settings['days'],integrated_reduction=settings['reduction_percent'],integrated_stock=settings['stock_days'])


def scene_loader(rows,ports):
    with st.expander('저장한 검토 조건 열기'):
        uploaded=st.file_uploader('검토 조건 파일 · JSON',type=['json'],key='scene_upload')
        if st.button('검토 조건 불러오기',disabled=uploaded is None,key='scene_restore'):
            try:
                if uploaded.size>262144:raise ValueError('장면 파일은 256KB 이하여야 합니다.')
                values=restore_scene(json.loads(uploaded.getvalue()),rows,ports)
            except (ValueError,KeyError,TypeError,RecursionError):
                st.error('유효한 장면 파일이 아닙니다. 항만·연결·가정값을 확인하세요.')
            else:
                st.session_state.update(values)
                st.session_state.pop('integrated_detail',None)
                st.success('저장된 항만·연결·가정을 불러왔습니다.')


def poster_png(lines):
    from PIL import Image,ImageDraw,ImageFont
    font_path=Path('C:/Windows/Fonts/malgun.ttf')
    font=ImageFont.truetype(str(font_path),26)
    title=ImageFont.truetype(str(font_path),40)
    wrapped=[]
    for line in lines:
        current=''
        for char in line:
            if font.getlength(current+char)>1450:
                wrapped.append(current);current=''
            current+=char
        wrapped.append(current)
    img=Image.new('RGB',(1600,max(900,170+len(wrapped)*44)), '#071324')
    draw=ImageDraw.Draw(img)
    draw.text((60,40),'SUPPLY NEXUS · 사건에서 대응까지',font=title,fill='#4fe4db')
    for i,line in enumerate(wrapped):draw.text((65,125+i*44),line,font=font,fill='#e1eaf3')
    output=io.BytesIO();img.save(output,format='PNG');return output.getvalue()


def render_scene_review(network,port,selected,row,candidates,days,reduction,stock):
    threshold=depletion(days,reduction,stock)
    inventory='기간 내 재고 부족 없음 · 입력 가정 기준' if threshold is None else f'{threshold:.1f}일 경과 후 재고 부족 가능 · 입력 가정 기준'
    st.markdown('### 연쇄 영향 · 조건부 경로')
    stages=[('항만 차질','선택 화물이 실제 이 항만을 경유할 때'),('소재 반입 감소',f'도착 공급 {reduction}% 감소를 별도 가정'),('재고 소진',inventory),('공정 투입 지연','해당 소재가 필요하고 승인된 대체 공급이 없을 때')]
    for col,(name,condition) in zip(st.columns(4),stages):
        with col:st.markdown('**'+name+'**');st.caption(condition)
    st.caption('이 경로는 조건부 설명입니다. 항만 폐쇄만으로 모든 소재·고객 공정의 중단을 확정하지 않습니다.')
    comparison=[{'대응':'기존 공급 유지','근거':'기업 관계 근거','확인 과제':'현장 재고·차기 입고·고객별 사용량','판정':'추가 확인'},
        *[{'대응':'대체 벤더 · '+v['supplier'],'근거':'제품 자료','확인 과제':'등급·고객 승인·추가 공급량·납기','판정':'검토 후보'} for v in candidates],
        {'대응':'대체 항만 검토','근거':'항만 위치 자료','확인 과제':'선사 운항·화물 취급·통관·내륙 운송','판정':'적합성 미확인'}]
    with st.expander('대응 후보 비교',expanded=not st.session_state.get('integrated_poster',False)):
        st.dataframe(comparison,hide_index=True)
        st.caption('근거·확인 과제를 비교하며 미확인 납기나 공급량으로 순위를 산정하지 않습니다.')
    payload=dict(schema=1,port=port['id'],connections=[[r['supplier'],r['recipient'],r['target']] for r in selected],
        assumptions=dict(days=days,reduction_percent=reduction,stock_days=stock))
    st.download_button('검토 조건 저장 · JSON',json.dumps(payload,ensure_ascii=False,indent=2),file_name='supply-scene.json',mime='application/json',key='scene_save')
    names=lambda r:network['entities'][r['supplier']]['name']+' → '+network['entities'][r['recipient']]['name']+' / '+r['material']
    lines=[port['name']+' · 항만 경유 가정',f'기간 {days}일 · 도착 공급 감소 {reduction}% · 시작 재고 {stock}일분',
        '선택 연결: '+names(row),'검토 공정: '+' · '.join(row['processes']),
        '항만 차질 → 소재 반입 감소 → 재고 소진 → 공정 투입 지연',inventory,
        '발생 조건: 실제 경유 + 해당 소재 필요 + 승인된 대체 공급 부족',
        '검토 후보: '+(' · '.join(v['supplier'] for v in candidates) or '추가 제품 자료 필요'),
        '다음 확인: 고객 승인 / 등급 / 공급 여력 / 운송·통관 / 납기',
        '근거: 기업 관계·제품 자료 / 항만 경유·기간·감소율·재고는 가정',
        '실제 생산률·화물 경유를 확정하지 않습니다. 상세 출처는 함께 저장한 근거 기록 참조.']
    st.download_button('선택 연결 요약 이미지 · PNG',poster_png(lines),file_name='supply-presentation.png',mime='image/png',key='scene_png')
