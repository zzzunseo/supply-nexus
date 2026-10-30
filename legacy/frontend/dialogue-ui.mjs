import {escapeHtml as esc} from './view-model.mjs';
const fmt=n=>Number(n).toFixed(1).replace(/\.0$/,'');
export const assistantMarkup=`
<details class="advice-panel panel" open><summary>영향 원인 · 대응책 비교 <small>현재 계산 조건 기준</small></summary><div class="advice-content"></div></details>
<section class="dialogue-panel panel" aria-label="이슈 대화"><div class="dialogue-heading"><div><div class="tiny-label">ISSUE → IMPACT → RESPONSE</div><h2>이슈 대화</h2></div><button type="button" class="text-button" data-chat-action="clear">새 대화</button></div>
<p class="chat-mode-notice">테스트 모드 · 외부 API 호출 없음 · 등록 데이터와 입력한 가정으로 계산합니다.</p>
<div class="chat-examples"><button type="button" data-chat-example="ASML 공급 능력 50% 감소, 14일">기업 공급 차질</button><button type="button" data-chat-example="프랑스 산소 공급 30% 감소, 7일">국가·소재 차질</button><button type="button" data-chat-example="트럼프 희토류 관세 20% 부과">관세 가정</button><button type="button" data-chat-example="일본 지진으로 Nokia 공장 차질">지역·공장 확인</button></div>
<div class="chat-log" role="log" aria-live="polite"></div><div class="issue-draft"></div>
<form class="chat-form"><label for="issue-text">이슈 또는 후속 조건</label><textarea id="issue-text" class="chat-input" rows="3" maxlength="2000" placeholder="예: ASML 공급 50% 감소, 14일 → 다음 질문: 그럼 20%로 바꾸고 30일"></textarea><div class="chat-actions"><select id="chat-mode" aria-label="이슈 해석 모드"><option value="test">테스트 · API 사용 안 함</option><option value="openai">OpenAI · 발표용</option></select><button type="submit" class="outline-button chat-submit">이슈 분석</button><button type="button" class="text-button" data-chat-action="research">공식 자료 조사</button></div></form><p class="chat-help">Ctrl+Enter로 분석 · 해석한 조건을 검토한 뒤 지도에 적용합니다. 새 대화는 현재 지도 시나리오를 유지합니다.</p></section>`;

function causeHtml(c){
  const paths=c.damaged.slice(0,3).map(e=>`${esc(e.country)} · ${esc(e.from)} → ${esc(e.to)}`).join('<br>');
  return `<article class="cause-card"><strong>${paths}${c.damaged.length>3?`<small>외 ${c.damaged.length-3}개 경로</small>`:''}</strong><p>→ ${esc(c.item)} 가용 ${fmt(c.available_pct)}% → ${esc(c.process)} ${fmt(c.process_score)}점 ${c.limiting?'<b class="amber-text">· 제한 투입재</b>':'· 다른 투입재도 확인'}</p><small>직접 공급 ${fmt(c.supply_pct)}% + 재고 ${fmt(c.stock_pct)}% + 대체 ${fmt(c.substitute_pct)}%</small>${c.alternatives.length?`<p class="alternative-note">정상 경로의 검토 후보: ${c.alternatives.map(a=>`${esc(a.name)}(${esc(a.country)})`).join(' · ')}<br><small>추가 여력·품목 등급·납기·고객 승인 확인 필요</small></p>`:'<p class="alternative-note">등록 모델 안에서 정상 공급 경로 후보가 없습니다.</p>'}</article>`;
}

export function renderAdvice(dashboard){
  const {view,state}=dashboard,host=dashboard.$('.advice-content'),advice=view.report?.advice;
  if(!advice){host.textContent='조건에 맞는 원인과 대응책을 계산하고 있습니다…';return;}
  const causes=advice.causes.filter(c=>state.process==='전체'||c.process===state.process);
  host.innerHTML=`<div class="cause-list">${causes.length?causes.slice(0,2).map(causeHtml).join(''):`<p>선택 범위의 필수 투입재에 직접 공급 감소가 없습니다.${view.report.bottlenecks.length?` 전체 병목: ${view.report.bottlenecks.map(esc).join(' · ')}`:''}</p>`}${causes.length>2?`<details><summary>나머지 원인 ${causes.length-2}개</summary>${causes.slice(2).map(causeHtml).join('')}</details>`:''}</div><div class="mitigation-grid">${advice.mitigations.map(m=>{const selected=m.processes.find(p=>p.name===state.process);return `<article class="mitigation-card"><span>${esc(m.label)}</span><strong>${fmt(m.score)}<small>점</small></strong><small>현재 대비 +${fmt(m.gain)}점</small><p>병목 ${esc(m.bottlenecks.join(' · ')||'없음')}</p>${selected?`<small>${esc(state.process)} ${fmt(selected.score)}점</small>`:''}</article>`;}).join('')}</div><p class="advice-summary">${esc(advice.summary)}</p><p class="chat-help">${esc(advice.notice)}</p>`;
}

function citedText(block){
  let cursor=0,html='';
  const citations=[...(block.citations||[])].sort((a,b)=>a.start_index-b.start_index);
  for(const c of citations){
    if(!Number.isInteger(c.start_index)||!Number.isInteger(c.end_index)||c.start_index<cursor||c.end_index>block.text.length||c.end_index<c.start_index)continue;
    let url;try{url=new URL(c.url);if(url.protocol!=='https:')continue;}catch{continue;}
    html+=esc(block.text.slice(cursor,c.start_index))+`<a href="${esc(url.href)}" target="_blank" rel="noopener noreferrer">[${esc(c.title||'출처')}]</a>`;
    cursor=c.end_index;
  }
  return (html+esc(block.text.slice(cursor))).replaceAll('\n','<br>');
}

export function renderDialogue(dashboard){
  const info=dashboard.data.assistant||{},busy=!!dashboard.pendingChat;
  dashboard.$('#chat-mode option[value="openai"]').disabled=!info.openai_available;
  if(!info.openai_available)dashboard.$('#chat-mode').value='test';
  const mode=dashboard.$('#chat-mode').value;
  dashboard.$('.chat-mode-notice').textContent=mode==='test'?'테스트 모드 · 외부 API 호출 없음 · 규칙 기반 해석이며 뉴스나 공장 정보를 검색하지 않습니다.':'OpenAI 발표 모드 · 입력 문장과 등록 목록을 OpenAI로 전송해 해석합니다. 점수는 기존 계산 엔진에서 산출합니다.';
  dashboard.$('.chat-log').innerHTML=(info.messages||[]).map(m=>`<article class="chat-message ${m.role==='user'?'user':'assistant'} ${m.error?'error':''}"><b>${m.role==='user'?'입력':m.mode==='test'?'테스트 해석':'분석'}</b><p>${esc(m.text).replaceAll('\n','<br>')}</p>${(m.research||[]).map(b=>`<div class="research-note">${citedText(b)}</div>`).join('')}</article>`).join('')+(busy?'<p role="status">요청을 처리하고 있습니다…</p>':'');
  dashboard.$('.chat-log').scrollTop=dashboard.$('.chat-log').scrollHeight;
  const a=info.analysis,host=dashboard.$('.issue-draft');
  host.innerHTML=a?`<article class="draft-card"><span class="evidence-badge ${a.can_apply?'evidence-assumed':'evidence-pending'}">${esc(a.status)}</span><h3>${esc(a.target_label)}</h3><p>${a.draft.event_type==='tariff'?'관세 · 비용 검토':`공급 능력 감소 ${a.draft.loss_pct==null?'미지정':fmt(a.draft.loss_pct)+'%'} · ${a.draft.duration_days??'미지정'}일`}</p><p>${a.edge_count}개 등록 경로 · ${a.processes.map(esc).join(' · ')||'연계 공정 미확인'}</p>${a.required.length?`<ul>${a.required.map(r=>`<li>${esc(r)}</li>`).join('')}</ul>`:''}${a.preview?`<div class="draft-score">예상 전체 점수 <b>${fmt(a.preview.score)}</b> / 100 · 병목 ${esc(a.preview.bottlenecks.join(' · ')||'없음')}</div><p class="chat-help">미리보기: 재고 ${a.preview.options.inventory?'적용':'미적용'} · 대체 ${a.preview.options.substitutes?'적용':'미적용'}. 적용할 때는 왼쪽의 현재 조건으로 계산합니다.</p><details><summary>예상 영향·대응 근거</summary>${a.preview.advice.causes.slice(0,3).map(causeHtml).join('')}<p>${esc(a.preview.advice.summary)}</p></details>`:''}<button type="button" class="outline-button" data-chat-action="apply" ${busy||!a.can_apply?'disabled':''}>가정 시나리오를 지도에 적용</button></article>`:'';
  dashboard.$$('.dialogue-panel [data-chat-action]').forEach(el=>{el.disabled=busy||(el.dataset.chatAction==='research'&&!info.research_available)||(el.dataset.chatAction==='apply'&&!a?.can_apply);el.onclick=()=>dashboard.sendChat(el.dataset.chatAction);});
  dashboard.$('.chat-submit').disabled=busy;
  dashboard.$('.chat-input').disabled=busy;
  dashboard.$('#chat-mode').disabled=busy;
  dashboard.$('[data-chat-action="research"]').title=info.research_available?'공식 자료를 검색하고 인용된 조사 메모를 표시합니다. 계산에는 자동 반영하지 않습니다.':'발표 시 서버의 OpenAI 웹 검색 설정을 켜면 사용할 수 있습니다.';
}

export function bindDialogue(dashboard){
  dashboard.listen(dashboard.$('.chat-form'),'submit',e=>{e.preventDefault();dashboard.sendChat('analyze');});
  dashboard.listen(dashboard.$('.chat-input'),'keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();dashboard.sendChat('analyze');}});
  dashboard.listen(dashboard.$('#chat-mode'),'change',()=>renderDialogue(dashboard));
  dashboard.$$('[data-chat-example]').forEach(el=>dashboard.listen(el,'click',()=>{dashboard.$('.chat-input').value=el.dataset.chatExample;dashboard.$('.chat-input').focus();}));
}
