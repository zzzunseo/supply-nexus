import {assistantMarkup, renderAdvice, renderDialogue, bindDialogue} from './dialogue-ui.mjs';
import Globe from 'globe.gl';
import {MeshPhongMaterial, TextureLoader, SRGBColorSpace, AmbientLight, DirectionalLight, Vector3} from 'three';
import earthTexture from './assets/earth-dots.png';
import {selectView, initialState, priorityLabels, LABEL_LIMITS, escapeHtml as esc} from './view-model.mjs';

const VIEWS = {
  '아시아·태평양': {lat:25,lng:116}, '유럽': {lat:38,lng:15},
  '북미': {lat:30,lng:-105}, '전체': {lat:18,lng:105},
};
const ICONS = {
  globe:'<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18M5 6.5h14M5 17.5h14"/>',
  reset:'<path d="M3 10a9 9 0 1 1 2 8M3 4v6h6"/>',
  layers:'<path d="m12 3 10 6-10 6L2 9l10-6Zm-9 11 9 5 9-5M3 18l9 5 9-5"/>',
  arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  pin:'<path d="M19 10c0 6-7 11-7 11S5 16 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2"/>',
  mouse:'<rect x="6" y="2" width="12" height="20" rx="6"/><path d="M12 2v7"/>',
  plus:'<path d="M12 4v16M4 12h16"/>', minus:'<path d="M4 12h16"/>',
  chevron:'<path d="m9 5 7 7-7 7"/>', close:'<path d="m6 6 12 12M6 18 18 6"/>',
};
const icon=(name, cls='')=>`<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]||ICONS.globe}</svg>`;
const toggle=(key,label,desc='')=>`<label class="toggle-row"><span>${label}${desc?`<small>${desc}</small>`:''}</span><input type="checkbox" data-setting="${key}" aria-label="${label}"><span class="switch" aria-hidden="true"></span></label>`;
const fmt=value=>Number(value).toFixed(1).replace(/\.0$/,'');
const percent=value=>`${fmt(value*100)}%`;
const STATE_LABELS={normal:'정상',warning:'주의',stopped:'중단'};
const evidenceState=r=>r.evidence_status||r.relation_status||(['출처 있음','가정값','확인 필요'].includes(r.status)?r.status:'확인 필요');
const SCOPE_LABELS={company:'기업 관계',collaboration:'기술·연구 협력',service:'현장 서비스',qualification:'과거 인증',planned_contract:'예정 계약',aggregate:'합산 경로 근거',item:'품목',historical_item:'과거 품목'};
const badge=r=>`<span class="evidence-badge evidence-${evidenceState(r)==='출처 있음'?'sourced':evidenceState(r)==='가정값'?'assumed':'pending'}">${esc(evidenceState(r)==='출처 있음'&&SCOPE_LABELS[r.evidence_scope]?`${SCOPE_LABELS[r.evidence_scope]} · 출처 있음`:evidenceState(r))}</span>`;
const sourceDetails=r=>`${/^https:\/\//.test(r.source||'')?`<a href="${esc(r.source)}" target="_blank" rel="noopener noreferrer">공식 출처 ↗</a>`:esc(r.source||'관계 근거 미확인')} · ${r.source_year==null?'자료 연도 미표기':`기준연도 ${esc(r.source_year)}`}${r.checked_at?` · 확인 ${esc(r.checked_at)}`:''}`;
const relationDetails=e=>`${badge(e)}<small class="source-detail">${sourceDetails(e)}</small><small class="relation-note">${esc(e.evidence_note||e.relation_note||'원본 기업 경로의 근거 확인 필요')}</small><small class="relation-note">${esc(e.legal_entity_scope||'')}</small>${e.item_status==='출처 있음'?`${badge({status:'출처 있음',evidence_scope:e.temporal_status==='historical'?'historical_item':'item'})}<small class="source-detail">${sourceDetails({source:e.item_source,source_year:e.item_source_year})}</small><small class="relation-note">${esc(e.item_evidence_note)}</small>`:'<span class="evidence-badge evidence-pending">세부 품목 납품 확인 필요</span>'}${e.temporal_status==='planned'?'<small class="relation-note">예정 시설·계약 계획. 현재 가동으로 해석하지 마세요.</small>':e.temporal_status==='expired_certificate'?'<small class="relation-note">인증 유효기간 2022.12~2024.12. 현재 유효성은 미확인입니다.</small>':''}`;
const dim=color=>{const h=color.replace('#','');return `rgb(${[0,2,4].map(i=>Math.round(parseInt(h.slice(i,i+2),16)*.12)).join(',')})`;};

function markup(data) {
  return `<div class="dashboard">
    <header class="topbar"><div class="brand-symbol">${icon('globe')}</div><div class="brand"><div class="eyebrow">반도체 공급망 시뮬레이터</div><h1>공급망 디지털 트윈</h1></div><div class="topbar-end"><button class="outline-button" data-action="open-chat">이슈 대화</button><span class="demo-badge"><i></i> 예시 데이터</span><span class="version">기업 연계 · 03</span></div></header>
    <nav class="pipeline" aria-label="반도체 공정 선택">${["전체",...data.processes].map((p,i)=>`<button class="process-step" data-process="${esc(p)}" aria-pressed="false"><span class="step-number">${p==='전체'?'ALL':String(i).padStart(2,'0')}</span><span class="step-name">${esc(p)}</span><span class="step-score" aria-label="공정 점수">—</span></button>`).join('')}</nav>
    <div class="workspace">
      <aside class="sidebar panel"><div class="section-heading">${icon('layers')}<h2>시뮬레이션 설정</h2></div><p class="subtle">조건을 바꾸고 흐름을 살펴보세요.</p>
        <div class="field"><label for="scenario">시나리오</label><select id="scenario" aria-label="시나리오">${data.scenarios.map(s=>`<option value="${esc(s.name)}">${esc(s.name.replace(' · 예시',''))}</option>`).join('')}</select></div>
        <div class="field"><label for="region">시작 지역</label><select id="region" aria-label="시작 지역">${Object.keys(VIEWS).map(r=>`<option>${r}</option>`).join('')}</select><small>지역을 바꾸면 시점이 이동합니다.</small></div>
        <details class="model-controls" open><summary>계산 조건 · 가정값</summary>
          <div class="field"><label for="duration">이슈 지속 기간</label><select id="duration" aria-label="이슈 지속 기간"><option value="7">7일</option><option value="14" selected>14일</option><option value="30">30일</option><option value="60">60일</option></select></div>
          <div class="field"><label for="severity">공급 중단 강도</label><select id="severity" aria-label="공급 중단 강도"><option value="0">0% · 영향 없음</option><option value="0.25">25% · 일부 감소</option><option value="0.5">50% · 절반 감소</option><option value="1" selected>100% · 완전 중단</option></select></div>
          ${toggle('inventory','재고 완충 적용')}${toggle('substitutes','대체 공급 가정 적용')}
          <p class="model-hint">재고·배분율·대체 여력은 검증용 가정값입니다.</p><span class="calculation-status" role="status" aria-live="polite"></span></details>
        <div class="divider"></div><h3 class="small-heading">지도 표시</h3>
        ${toggle('context','다른 공정 함께 보기','선택 공정 외 경로는 흐리게')}${toggle('routes','공급 경로')}${toggle('labels','거점 이름')}${toggle('rotate','자동 회전')}
        <button class="outline-button reset-button" data-action="reset">${icon('reset')}시점 초기화</button>
        <details class="display-options"><summary>고급 표시 설정</summary>${toggle('atmosphere','외곽 광채')}<p>대륙은 정적 지도 질감으로 표시해 렌더링 부하를 줄였습니다.</p></details>
        <div class="sidebar-note"><span class="tiny-label">데이터 검증</span><p>공식 자료의 기업 관계·품목·과거/예정 범위를 구분합니다.</p><small class="research-summary"></small><small>실제 배분율은 공개 수치 미확보입니다. 계산은 별도 가정값을 사용합니다.</small></div>
      </aside>
      <main class="stage">
        <div class="metrics"><div class="metric overall-metric"><span>전체 점수 · 가정 기반</span><div><strong data-metric="overall">—</strong><small>/ 100</small></div><span class="metric-caption" data-content="score-delta"></span></div><div class="metric bottleneck-metric"><span>병목 공정</span><div><strong data-metric="bottleneck">—</strong></div><span class="metric-caption" data-content="bottleneck-note"></span></div><div class="metric"><span>영향받은 거점</span><div><strong data-metric="affected">—</strong><small>개 거점</small></div><span class="metric-caption">전체 기업 거점 기준</span></div></div>
        <section class="map-panel panel"><div class="map-heading"><div><div class="tiny-label">공정별 공급 네트워크</div><h2 data-content="map-title">포토 공정 공급 흐름</h2></div><div class="view-tabs" role="tablist" aria-label="지도 보기"><button role="tab" data-tab="globe" aria-selected="true">지구본</button><button role="tab" data-tab="compare" aria-selected="false">전후 비교</button><button role="tab" data-tab="data" aria-selected="false">상세 데이터</button></div></div>
          <div class="globe-view" role="tabpanel" aria-label="지구본">
          <div class="presentation-toolbar"><button class="outline-button" data-action="poster" aria-pressed="false">전체 공급망 · 발표 보기</button><button class="text-button" data-action="demo-scene">대표 장면 · 네덜란드 50% 감소</button></div><section class="poster-story" hidden><div class="tiny-label">SEMICONDUCTOR SUPPLY CHAIN DIGITAL TWIN</div><h2>한 곳의 공급 충격,<br>어느 공정의 병목으로 이어질까?</h2><p class="poster-result"></p><div class="poster-chain"></div><small>기업 관계·협력·과거/예정 계약을 포함한 후보 네트워크 · 점수는 가정 기반 · 표시 위치는 실제 공장이 아닙니다.</small></section><div class="level-toolbar"><div class="level-segments" role="group" aria-label="보기 레벨"><button data-level="country" aria-pressed="true">국가</button><button data-level="company" aria-pressed="false">기업</button><button data-level="chain" aria-pressed="false">소재 연쇄</button></div><button class="text-button unlink-button" data-action="unlink">연계 보기 끄기</button></div>
          <p class="level-description" role="status"></p><div class="focus-strip" hidden><span></span><button class="text-button" data-action="clear-focus">포커스 해제 · ESC</button></div>
          <div class="globe-viewport"><div class="globe-canvas"></div><div class="loading-message"><span class="loading-orbit"></span><p>지구본을 준비하고 있습니다</p></div><div class="map-corner"><span class="tiny-label">현재 시점</span><span data-content="region">아시아·태평양</span></div><div class="map-buttons"><button data-action="zoom-in" aria-label="지구본 확대" title="확대">${icon('plus')}</button><button data-action="zoom-out" aria-label="지구본 축소" title="축소">${icon('minus')}</button><button data-action="reset" aria-label="지도 시점 초기화" title="시점 초기화">${icon('reset')}</button></div><div class="map-toast" role="status" aria-live="polite"></div></div>
          <div class="arc-pager"><span class="arc-count" role="status"></span><button class="text-button" data-action="more-routes" aria-pressed="false">더 보기</button></div><div class="map-footer"><div class="legend"><span><i class="dot cyan"></i>정상</span><span><b class="amber-text">△</b>감소</span><span><b class="red">×</b>중단</span><span class="context-key"><i class="line"></i>다른 공정</span></div><span class="interaction-hint">${icon('mouse')}드래그하여 회전 · 스크롤하여 확대</span></div></div>
          <section class="overview-heatmap" hidden></section><div class="data-view" role="tabpanel" aria-label="상세 데이터" hidden><div class="table-toolbar"><span>현재 보기의 공급 관계 후보</span><button class="text-button" data-action="download">${icon('download')}JSON 저장</button></div><div class="table-scroll"><table class="routes-table"><thead><tr><th>출발</th><th>도착</th><th>품목</th><th>상태</th><th>관계 근거</th><th>실제 배분율</th><th>계산 가정</th></tr></thead><tbody></tbody></table></div><p class="table-note">국가 값은 같은 소재·공정의 기업 경로 합계입니다. 실제 배분율 미확인 값은 —, 계산용 배분은 가정값으로 표시합니다.</p></div>
          <div class="comparison-view" role="tabpanel" aria-label="전후 비교" hidden><div class="comparison-summary"></div><div class="table-scroll"><table class="comparison-table"><thead><tr><th>공정</th><th>정상</th><th>이슈 후</th><th>변화</th><th>직렬 상한</th></tr></thead><tbody></tbody></table></div><p class="table-note">공정 점수 = 필수 투입재 가용률의 최솟값 × 100. 직렬 상한은 해당 공정까지의 최솟값이며, 실제 시간별 생산량을 뜻하지 않습니다.</p><details class="assumption-details"><summary>계산식과 가정값 확인</summary><p>가용률 = 공급 배분율 × 경로 가용률의 합 + 대체 공급 보정 + 재고 완충. 합계는 100%를 넘지 않습니다. 공급 배분율은 시연용 수치이며 시장 점유율이 아닙니다.</p><p>대체 공급 보정은 전환에 걸리는 기간을 제외한 추가 여력입니다. 재고는 공정별 공통 풀로 가정하고, 장비에는 재고 완충을 적용하지 않습니다. 경로 중단은 전달 가능량의 감소로 모델링하며 시설별 생산 일정은 계산하지 않습니다.</p><div class="assumption-list"></div></details><button class="outline-button report-download" data-action="report">${icon('download')}계산 결과 JSON 저장</button></div>
        </section>
        ${assistantMarkup}
      </main>
      <aside class="inspector panel"><section class="overview-inspector" hidden></section><div class="tiny-label">선택 공정</div><div class="process-heading"><span class="process-index" data-content="process-index">03</span><h2 data-content="process-name">포토</h2></div><p class="process-description" data-content="description"></p><div class="process-score-summary"></div><div class="divider"></div><h3 class="small-heading">표시 투입재</h3><div class="chips" data-content="items"></div><div class="divider"></div><h3 class="small-heading">시나리오 영향</h3><div class="scenario-status" role="status"></div><p class="scenario-description"></p><div class="input-breakdown"></div><div class="divider"></div><div class="route-heading"><h3 class="small-heading">주요 공급 경로</h3><span data-content="route-count"></span></div><div class="route-list"></div><section class="linked-section"><div class="divider"></div><h3 class="small-heading">연계 기업·소재</h3><p class="link-notice">소재 → 공급 기업 → 본사 국가. 근거 배지의 범위·시점을 확인하세요.</p><div class="linked-list"></div><div class="focus-details" hidden></div></section><div class="node-detail" hidden></div><div class="inspector-foot">거점 또는 경로를 선택하면<br>연결 정보를 확인할 수 있습니다.</div></aside>
    </div><footer class="page-footer"><span><i></i>가정 기반 병목 모델 · 실제 수치 확인 필요</span><span>지구본과 경로를 자유롭게 탐색하세요</span></footer>
  </div>`;
}

class Dashboard {
  constructor(root, data, send) {
    this.root=root; this.data=data; this.send=send; this.state={...initialState(data),...data.ui_selection,...data.simulation?.options};this.appliedRevision=data.assistant?.applied_selection?.revision;
    this.lookup=new Map(data.nodes.map(n=>[n.id,n]));
    this.cleanup=[]; this.timers=[]; this.disposed=false;
    this.colors=data.tokens;
    Object.entries(data.tokens).forEach(([key,value])=>root.style.setProperty(`--${key.replaceAll('_','-')}`,value));
    root.innerHTML=markup(data);
    this.$('.globe-viewport').append(this.$('.poster-story'));
    this.bindControls();bindDialogue(this); this.update(); this.mountGlobe();
  }
  $(s) {return this.root.querySelector(s);}
  $$(s) {return [...this.root.querySelectorAll(s)];}
  listen(el,type,fn) {el.addEventListener(type,fn);this.cleanup.push(()=>el.removeEventListener(type,fn));}
  bindControls() {
    this.$$('.process-step').forEach(el=>this.listen(el,'click',()=>{this.state.process=el.dataset.process;if(this.state.process==='전체'){this.state.level='country';this.state.poster=false;this.state.tab='globe';}this.state.selectedRoute=null;this.state.selectedNode=null;this.state.focus=null;this.state.routePage=0;this.state.expandedCountries=[];this.change();}));
    this.$$('[data-level]').forEach(el=>this.listen(el,'click',()=>this.setLevel(el.dataset.level)));
    this.listen(document,'keydown',e=>{if(e.key==='Escape'&&this.state.focus){e.preventDefault();this.clearFocus();}});
    this.listen(this.$('#scenario'),'change',e=>{this.state.scenario=e.target.value;this.change();});
    this.listen(this.$('#region'),'change',e=>{this.state.region=e.target.value;this.resetCamera();this.change();});
    for(const [id,key] of [['duration','duration_days'],['severity','severity']]){
      this.listen(this.$(`#${id}`),'change',e=>{this.state[key]=Number(e.target.value);this.change();});
    }
    this.$$('[data-setting]').forEach(el=>this.listen(el,'change',()=>{
      this.state[el.dataset.setting]=el.checked;
      if(el.dataset.setting==='rotate') this.userPaused=false;
      this.change();
    }));
    this.$$('[data-tab]').forEach(el=>this.listen(el,'click',()=>{this.state.tab=el.dataset.tab;this.change();}));
    this.$$('[data-action]').forEach(el=>this.listen(el,'click',()=>{
      const action=el.dataset.action;
      if(action==='poster'){this.state.poster=!this.state.poster;this.state.focus=null;this.state.routePage=0;this.state.tab='globe';this.update();this.resetCamera();}
      if(action==='demo-scene'){const scenario=this.data.scenarios.find(s=>s.name.includes('네덜란드'));if(scenario){Object.assign(this.state,{poster:true,process:'포토',scenario:scenario.name,severity:.5,duration_days:14,inventory:true,substitutes:false,focus:null,tab:'globe',routes:true,rotate:false,region:'아시아·태평양'});this.change();this.resetCamera();}}
      if(action==='open-chat'){this.$('.chat-input').focus();this.$('.dialogue-panel').scrollIntoView({behavior:'smooth',block:'center'});}
      if(action==='reset') {this.resetCamera();this.toast('시작 지역으로 시점을 되돌렸습니다.');}
      if(action==='zoom-in'||action==='zoom-out') this.zoom(action==='zoom-in'?.85:1.18);
      if(action==='download') this.download();
      if(action==='report') this.downloadReport();
      if(action==='unlink')this.setLevel('country');
      if(action==='clear-focus')this.clearFocus();
      if(action==='more-routes'){this.state.routePage=(this.view.page+1)%this.view.pages;this.update();}
    }));
  }
  change() {
    this.update();
    // One state object is the stable integration seam for the Python engine.
    this.send?.('selection',{process:this.state.process,scenario:this.state.scenario,region:this.state.region,
      duration_days:this.state.duration_days,severity:this.state.severity,inventory:this.state.inventory,substitutes:this.state.substitutes});
  }
  receiveData(data) {
    this.data=data;
    if(data.assistant?.last_request_id===this.pendingChat)this.pendingChat=null;
    const applied=data.assistant?.applied_selection;
    if(applied&&applied.revision!==this.appliedRevision){Object.assign(this.state,applied,{focus:null,selectedNode:null,selectedRoute:null,routePage:0});this.appliedRevision=applied.revision;}
    this.update();
  }
  sendChat(action){
    if(this.pendingChat)return;
    const text=this.$('.chat-input').value.trim();
    if(action==='analyze'&&!text){this.$('.chat-input').focus();return;}
    const id=crypto.randomUUID();this.pendingChat=id;
    this.send?.('chat_request',{id,action,text,mode:this.$('#chat-mode').value});
    if(action==='analyze')this.$('.chat-input').value='';
    renderDialogue(this);
  }
  setLevel(level){if(this.state.process==='전체')return;this.state.level=level;this.state.routePage=0;this.state.focus=null;this.state.selectedNode=null;this.state.selectedRoute=null;this.update();}
  clearFocus(){this.state.focus=null;this.state.selectedNode=null;this.state.selectedRoute=null;this.state.routePage=0;this.update();}
  update() {
    this.view=selectView(this.data,this.state);
    this.lookup=new Map([...this.data.nodes,...this.view.canonical.nodes,...this.view.nodes].map(n=>[n.id,n]));
    const {view,state}=this;
    const overview=state.process==='전체';
    this.$('.dashboard').classList.toggle('overview-mode',overview);
    this.$$('[data-level]').forEach(el=>el.disabled=overview&&el.dataset.level!=='country');
    this.$('.presentation-toolbar').hidden=overview;
    this.$('[data-tab="data"]').disabled=overview;
    this.$('.overview-heatmap').hidden=!overview;
    this.$('.overview-inspector').hidden=!overview;
    this.$('.dashboard').classList.toggle('poster-mode',state.poster);
    this.$('.poster-story').hidden=!state.poster;
    this.$('.level-toolbar').hidden=state.poster;
    this.$('[data-action="poster"]').setAttribute('aria-pressed',String(state.poster));
    this.$('[data-action="poster"]').textContent=state.poster?'분석 화면으로 돌아가기':'전체 공급망 · 발표 보기';
    this.$('.poster-result').textContent=view.report?`${state.scenario.replace(' · 예시','')} · 공급 능력 ${percent(state.severity)} 감소 · 정상 100 → ${fmt(view.report.overall_score)}점 · 병목 ${view.report.bottlenecks.join(' · ')||'없음'}`:'시나리오를 계산하고 있습니다…';
    this.$('.poster-chain').innerHTML=(this.data.items||[]).filter(i=>i.processes.includes(state.process)).map(item=>{const suppliers=[...new Set(view.selected.filter(e=>e.item_id===item.id).map(e=>this.lookup.get(e.from)?.company_name))];return `<button class="poster-path" data-poster-material="${esc(item.id)}"><b>${esc(item.name)}</b><span>→ ${suppliers.map(esc).join(' / ')} → 고객 기업 → ${esc(state.process)} 공정</span></button>`;}).join('');
    this.$$('[data-poster-material]').forEach(el=>el.onclick=()=>{this.state.poster=false;this.state.level='chain';this.selectMaterial(el.dataset.posterMaterial);});
    this.$$('[data-level]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.level===state.level)));
    this.$('.unlink-button').hidden=state.level==='country';
    this.$('[data-setting="context"]').disabled=overview||state.level!=='country';
    this.$('.level-description').textContent=overview?'국가 크기: 관여 공정 수 · 색/기호: 최악 경로 상태 · 호 굵기: 모델 배분 합계(물동량 아님)':state.poster?'전체 기업 연결은 옅은 파랑, 선택 공정은 시안, 공급 충격은 주황·빨강입니다. 소재 흐름을 누르면 상세 연쇄로 이동합니다.':state.level==='country'?'같은 소재·공정의 기업 흐름을 국가별로 합산합니다. 근거 배지의 범위·연도를 확인하세요.':state.level==='company'?'선택 공정의 core 기업만 표시합니다. 국가 묶음을 클릭하거나 확대하면 기업이 펼쳐집니다.':'◇ 소재 → 기업 → □ 공정의 표시 연쇄입니다. 소재·공정 표시는 실제 위치가 아닙니다.';
    const research=this.data.research_summary;
    this.$('.research-summary').textContent=research?`본사 국가 ${research.company_countries_verified}/17 · 기업 관계·협력·인증 ${research.relationship_evidence_edges}/${research.edges_total} · 품목 근거 ${research.item_evidence_edges}/${research.edges_total}(과거 ${research.historical_item_edges}) · 확인 ${research.checked_at}`:'';
    const focusTitle=state.focus?.name||state.focus?.id;
    this.$('.focus-strip').hidden=!state.focus;
    this.$('.focus-strip span').textContent=state.focus?`${focusTitle} · 상류·하류 연결 강조`:'';
    this.$('.arc-count').textContent=`${view.totalRoutes}개 중 ${view.routes.length}개 호 · ${view.page+1}/${view.pages} · 라벨 최대 ${LABEL_LIMITS[state.level]}개`;
    const more=this.$('[data-action="more-routes"]');more.hidden=view.pages<=1;
    more.textContent=view.page===view.pages-1?'처음 보기':`더 보기 · ${view.page+2}/${view.pages}`;
    more.setAttribute('aria-pressed',String(view.page>0));
    this.$$('.process-step').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.process===state.process)));
    this.$('#scenario').innerHTML=this.data.scenarios.map(s=>`<option value="${esc(s.name)}">${esc(s.name.replace(' · 예시',''))}</option>`).join('');
    this.$('#scenario').value=state.scenario;this.$('#region').value=state.region;
    for(const [id,value,label] of [['duration',state.duration_days,`${state.duration_days}일 · 대화 입력`],['severity',state.severity,`${percent(state.severity)} · 대화 입력`]]){
      const select=this.$(`#${id}`);select.querySelectorAll('[data-custom]').forEach(el=>el.remove());
      if(![...select.options].some(o=>o.value===String(value))){const option=document.createElement('option');option.value=String(value);option.textContent=label;option.dataset.custom='true';select.append(option);}
      select.value=String(value);
    }
    this.$$('[data-setting]').forEach(el=>el.checked=state[el.dataset.setting]);
    this.$$('[data-tab]').forEach(el=>el.setAttribute('aria-selected',String(el.dataset.tab===state.tab)));
    this.$('.globe-view').hidden=state.tab!=='globe';this.$('.data-view').hidden=state.tab!=='data';
    this.$('.comparison-view').hidden=state.tab!=='compare';
    const text={ 'map-title':overview?'8대 공정 · 국가별 의존도':`${state.process} 공정 공급 흐름`,region:state.region,'process-name':state.process,
      'process-index':String(this.data.processes.indexOf(state.process)+1).padStart(2,'0'),
      description:this.data.descriptions[state.process], 'route-count':`${view.selected.length}개`};
    Object.entries(text).forEach(([k,v])=>this.$(`[data-content="${k}"]`).textContent=v);
    this.$('[data-content="items"]').innerHTML=[...new Map(view.selected.map(e=>[e.item_id,e])).values()].map(i=>`<button class="chip material-chip" data-material="${esc(i.item_id)}">${esc(i.item)}</button>`).join('');
    this.$$('[data-material]').forEach(el=>el.onclick=()=>this.selectMaterial(el.dataset.material));
    this.renderScores();renderAdvice(this);renderDialogue(this);
    if(overview)this.renderOverview();
    this.$('.route-list').innerHTML=view.selected.map((e,i)=>{
      const a=this.lookup.get(e.from),b=this.lookup.get(e.to);
      return `<button class="route-card ${e.blocked?'blocked':e.warning?'warning':''} ${state.selectedRoute===e.id?'selected':''}" data-route="${esc(e.id)}"><span class="route-number">${String(i+1).padStart(2,'0')}</span><span class="route-info"><strong>${esc(a.company_name||a.country)} <span>→</span> ${esc(b.company_name||b.country)}</strong><small>${esc(e.item)} ${badge(e)}</small></span><span class="route-state" title="${STATE_LABELS[e.status]}">${e.blocked?'×':e.warning?'△':'●'}</span></button>`;
    }).join('');
    this.$$('.route-card').forEach(el=>el.onclick=()=>this.selectRoute(el.dataset.route));
    this.$('.routes-table tbody').innerHTML=view.allRoutes.map(e=>`<tr class="${e.active?'':'context-row'}"><td>${esc(this.lookup.get(e.from)?.display_name||this.lookup.get(e.from)?.name)}</td><td>${esc(this.lookup.get(e.to)?.display_name||this.lookup.get(e.to)?.name)}</td><td>${esc(e.item)}</td><td><span class="${e.blocked?'red':e.warning?'amber-text':'cyan-text'}">${view.report?(e.blocked?'× 중단':e.warning?'△ 감소':'● 정상'):'계산 중'}</span></td><td>${badge(e)}</td><td>${e.share_pct==null?'— · 확인 필요':`${fmt(e.share_pct)}%`}</td><td>${e.model_share_pct==null?'표시 연결':`${fmt(e.model_share_pct)}% · 가정값`}</td></tr>`).join('');
    this.renderLinked();
    this.updateNodeDetail();
    if(this.globe) {if(view.report)this.updateGlobe();if(state.tab==='globe'){this.globe.resumeAnimation();this.resize();}else this.globe.pauseAnimation();}
  }
  renderScores() {
    const report=this.view.report;
    this.$('.calculation-status').textContent=report?'계산 완료':'조건을 반영하고 있습니다…';
    this.$('.report-download').disabled=!report;
    this.$$('.process-step').forEach(el=>{
      const p=report?.processes.find(p=>p.name===el.dataset.process);
      el.dataset.status=el.dataset.process==='전체'?(report?.status||'pending'):p?.status||'pending';
      el.classList.toggle('is-bottleneck',!!report?.bottlenecks.includes(el.dataset.process));
      const score=el.querySelector('.step-score');score.textContent=el.dataset.process==='전체'&&report?fmt(report.overall_score):p?fmt(p.score):'—';
      score.style.setProperty('--score',p?.score||0);
      el.title=el.dataset.process==='전체'&&report?`전체: ${fmt(report.overall_score)}점 · ${STATE_LABELS[report.status]}`:p?`${p.name}: ${fmt(p.score)}점 · ${STATE_LABELS[p.status]}${report.bottlenecks.includes(p.name)?' · 병목 공정':''}`:'계산 중';
    });
    const metric=this.$('[data-metric="overall"]');metric.textContent=report?fmt(report.overall_score):'—';
    this.$('.overall-metric').dataset.status=report?.status||'pending';
    const bottleneck=this.$('[data-metric="bottleneck"]');
    bottleneck.textContent=!report?'—':report.bottlenecks.length?report.bottlenecks[0]:'없음';
    bottleneck.title=report?.bottlenecks.join(', ')||'';
    this.$('[data-content="bottleneck-note"]').textContent=!report?'계산 중':report.bottlenecks.length>1?`동률 ${report.bottlenecks.length}개 공정 · 전후 비교에서 확인`:report.bottlenecks.length?'필수 투입재 가용률 최저':'모든 필수 투입재 충족';
    this.$('[data-metric="affected"]').textContent=report?String((report.affected_companies||report.affected_nodes).length).padStart(2,'0'):'—';
    this.$('[data-content="score-delta"]').textContent=report?`정상 대비 ${report.delta<0?'−':''}${fmt(Math.abs(report.delta))}점`:'새 조건 계산 중';
    const process=report?.processes.find(p=>p.name===this.state.process);
    this.$('.process-score-summary').innerHTML=process?`<span>공정 점수 <strong class="status-${process.status}">${fmt(process.score)}</strong></span><span>직렬 상한 <b>${fmt(process.serial_score)}</b></span>`:'계산 중…';
    const statusEl=this.$('.scenario-status');statusEl.className=`scenario-status ${process?.status==='stopped'?'interrupted':process?.status||'pending'}`;
    statusEl.textContent=!process?'조건을 반영하고 있습니다…':process.limiting_items.length?`${process.status==='stopped'?'×':'△'} 제한 투입재: ${process.limiting_items.join(' · ')}`:'● 필수 투입재 충족';
    this.$('.scenario-description').textContent=process&&process.serial_score<process.score?`앞 공정의 병목으로 직렬 상한이 ${fmt(process.serial_score)}점까지 낮아집니다.`:report&&this.view.scenario.affected.length?`${this.state.duration_days}일 동안 해당 거점에 연결된 경로의 공급 능력을 ${percent(this.state.severity)} 낮춘 가정입니다.`:this.view.scenario.description;
    this.$('.input-breakdown').innerHTML=process?process.inputs.map(item=>`<details class="input-item"><summary><span>${esc(item.name)}</span><b class="status-${item.status}">${percent(item.availability)}</b></summary><div class="availability-bar"><i style="width:${item.score}%;background:var(--${item.status==='normal'?'cyan':item.status==='warning'?'amber':'red'})"></i></div><dl><dt>공급 가용량</dt><dd>${percent(item.supply)}</dd><dt>대체 공급 보정</dt><dd>+${percent(item.substitute)}</dd><dt>재고 완충</dt><dd>+${percent(item.inventory)}</dd></dl><small>가정값 · 실제 수치 확인 필요</small></details>`).join(''):'';
    this.$('.comparison-summary').innerHTML=report?`<span>정상 상태 <b>100</b></span><span class="comparison-arrow">→</span><span>${esc(this.state.scenario.replace(' · 예시',''))}<b class="status-${report.status}">${fmt(report.overall_score)}</b></span><small>${this.state.duration_days}일 · 중단 강도 ${percent(this.state.severity)}<br>재고 ${this.state.inventory?'적용':'미적용'} · 대체 공급 ${this.state.substitutes?'가정 적용':'미적용'}</small>`:'조건을 반영하고 있습니다…';
    this.$('.comparison-table tbody').innerHTML=report?report.processes.map(p=>`<tr class="${report.bottlenecks.includes(p.name)?'bottleneck-row':''}"><td>${esc(p.name)}${report.bottlenecks.includes(p.name)?'<small class="bottleneck-tag">병목</small>':''}</td><td>100</td><td class="status-${p.status}">${fmt(p.score)} <small>${STATE_LABELS[p.status]}</small></td><td>${p.score<100?'−':''}${fmt(100-p.score)}</td><td class="status-${p.serial_status}">${fmt(p.serial_score)}</td></tr>`).join(''):'';
    this.$('.assumption-list').innerHTML=report?report.processes.map(p=>`<h4>${esc(p.name)}</h4>${p.inputs.map(item=>`<p><strong>${esc(item.name)}</strong> · ${item.suppliers.map(s=>{const edge=this.data.edges.find(e=>e.id===s.edge_id);return `${esc(this.lookup.get(edge.from).country)}→${esc(this.lookup.get(edge.to).country)} ${fmt(s.share_pct)}%`;}).join(' / ')}<br>재고 ${item.buffer_days}일 · 대체 여력 ${percent(item.substitute_fraction)} · 전환 ${item.substitute_lead_days}일<br><small>${esc(item.source)} · 기준연도 ${item.source_year??'확인 필요'}</small></p>`).join('')}`).join(''):'';
  }
  renderOverview(){
    const summary=this.view.summary,host=this.$('.overview-heatmap'),panel=this.$('.overview-inspector');
    if(!summary){host.textContent='새 조건을 집계하고 있습니다…';panel.textContent='계산 중…';return;}
    const symbol={normal:'●',warning:'△',stopped:'×'};
    host.innerHTML=`<h3>국가 × 공정 의존도 <small>계산용 가정 배분율</small></h3><p>밝기 = 의존 비중 · 테두리/△/× = 공급 기여 감소 · 빗금/— = 데이터 없음. 칸을 누르면 공정으로 이동합니다.</p><div class="heatmap-scroll"><table class="dependency-table"><thead><tr><th>공급 국가</th>${this.data.processes.map(p=>`<th>${esc(p)}</th>`).join('')}</tr></thead><tbody>${summary.countries.map(row=>`<tr class="${this.state.focus?.id===row.id?'highlighted':''}"><th>${esc(row.country)}</th>${row.cells.map(cell=>{
      const title=cell.has_data?`${row.country} · ${cell.process}\n필수 투입재 비중 최댓값 ${fmt(cell.value_pct)}% (가정)\n${cell.details.map(d=>`${d.item}: 배분 ${fmt(d.share_pct)}%, 가용 기여 ${fmt(d.available_share_pct)}%, 감소 ${fmt(d.loss_pct)}%p`).join('\n')}\n재고·대체 전의 직접 경로 기여. 공정 점수는 재고·대체를 반영합니다.`:`${row.country} · ${cell.process}: 모델에 공급 기록 없음. 실제 공급 0%를 의미하지 않습니다.`;
      return `<td><button data-heat-process="${esc(cell.process)}" data-heat-country="${esc(row.id)}" class="heat-cell ${cell.has_data?'status-'+cell.status:'no-data'}" style="--intensity:${cell.value_pct==null?0:cell.value_pct/100}" title="${esc(title)}" aria-label="${esc(title)}">${cell.has_data?`${symbol[cell.status]} ${fmt(cell.value_pct)}%`:'—'}<small>${cell.has_data?(cell.loss_pct?`−${fmt(cell.loss_pct)}%p`:'정상'):'데이터 없음'}</small></button></td>`;
    }).join('')}</tr>`).join('')}</tbody></table></div><p>국가는 본사/대표 법인 기준입니다. 실제 조달 비중은 미확보이며 모든 비중은 가정값입니다.</p>`;
    host.querySelectorAll('[data-heat-process]').forEach(el=>el.onclick=()=>{
      const row=summary.countries.find(r=>r.id===el.dataset.heatCountry);
      Object.assign(this.state,{process:el.dataset.heatProcess,level:'country',poster:false,context:true,routePage:0,selectedNode:row.id,selectedRoute:null,
        focus:{type:'node',id:row.id,name:row.country,member_node_ids:this.data.nodes.filter(n=>n.company_name&&n.country===row.country).map(n=>n.id)}});
      this.change();this.globe?.pointOfView({lat:row.lat,lng:row.lon},500);
    });
    panel.innerHTML=`<div class="tiny-label">8대 공정 요약 · 가정 기반</div><h2>전체 공급망</h2><div class="overview-score">${fmt(summary.overall_score)}<small> / 100</small></div><h3>병목 공정</h3><p>${esc(summary.bottlenecks.join(' · ')||'없음')}</p><h3>이슈로 영향받은 공정</h3><p><b>${summary.affected_process_count}</b> / 8개 · 공정 점수 100 미만</p><h3>단일 국가 의존도 상위 3개</h3><small>모델 비중 ${summary.threshold_pct}% 이상인 공정 수 순</small>${summary.top_dependencies.map(r=>`<div class="dependency-card"><b>${esc(r.country)}</b><p>${esc(r.processes.join(' · '))}</p><small>${r.count}개 공정에서 ${summary.threshold_pct}% 이상 · 최대 ${fmt(r.max_pct)}%</small></div>`).join('')}<p class="link-notice">직접 경로 공급 기여 감소와 재고·대체 반영 후 공정 점수는 다를 수 있습니다. 다단계 전파 계산은 포함하지 않습니다.</p>`;
  }
  renderLinked(){
    const items=(this.data.items||[]).filter(i=>i.processes.includes(this.state.process));
    this.$('.linked-list').innerHTML=items.map(item=>{
      const edges=this.view.selected.filter(e=>e.item_id===item.id);
      return `<details class="linked-item" open><summary><button class="chip material-chip" data-focus-material="${esc(item.id)}">${esc(item.name)}</button>${badge(item)}</summary><small class="source-detail">${sourceDetails(item)}</small><small class="relation-note">${esc(item.source_scope||'제품군 소개의 근거. 개별 고객 납품은 별도 확인.')}</small><ul>${[...new Set(edges.map(e=>e.from))].map(id=>{
        const n=this.lookup.get(id),out=edges.filter(e=>e.from===id);
        const metrics=(this.data.public_metrics||[]).filter(m=>m.company_id===id);
        return `<li><button class="link-company" data-focus-company="${esc(id)}">${esc(n.company_name)}</button>${badge(n)}<span class="link-country">→ ${esc(n.country)} · 본사/대표 법인 ${badge({status:n.country_status||'확인 필요'})}</span><small class="source-detail">${sourceDetails({source:n.country_source,source_year:n.country_source_year,checked_at:n.checked_at})}</small><small class="source-detail">제품군: ${sourceDetails(n)}</small>${out.map(e=>`<details class="input-item"><summary><span>→ ${esc(this.lookup.get(e.to).company_name)}</span></summary>${relationDetails(e)}<small class="relation-note">실제 배분율 ${e.share_pct==null?'공개 수치 미확보':fmt(e.share_pct)+'%'} · 계산 배분 ${fmt(e.model_share_pct)}% ${badge({status:'가정값'})}</small></details>`).join('')}${metrics.map(m=>`<details class="input-item"><summary>공시 참고 수치 · 계산 배분과 별개</summary><p class="relation-note">${m.period}년 ${esc(m.metric)} ${m.value}${esc(m.unit)}<br>분모: ${esc(m.denominator)}<br>${esc(m.includes)}<br>${esc(m.note)}</p><small class="source-detail">${sourceDetails(m)}</small></details>`).join('')}</li>`;
      }).join('')}</ul></details>`;
    }).join('');
    this.$$('[data-focus-material]').forEach(el=>el.onclick=e=>{e.preventDefault();this.selectMaterial(el.dataset.focusMaterial);});
    this.$$('[data-focus-company]').forEach(el=>el.onclick=()=>this.selectCompany(el.dataset.focusCompany));
    const panel=this.$('.focus-details');panel.hidden=!this.state.focus;
    if(this.state.focus){
      const links=this.view.canonical.routes.filter(e=>this.view.focus?.edgeIds.has(e.id));
      panel.innerHTML=`<h4>선택 항목의 연계 · ${links.length}개</h4><p class="link-notice">상류·하류 방향의 연결입니다. 관계 후보와 표시 연결의 근거를 함께 확인하세요.</p>${links.map(e=>`<button class="focus-link" data-focus-route="${esc(e.id)}"><span>${esc(this.lookup.get(e.from)?.name)} → ${esc(this.lookup.get(e.to)?.name)}</span><small>${esc(e.item)} · ${e.relation_kind==='product_capability'?'제품군 연결':e.synthetic?'공정 표시 연결':'납품 후보'} ${badge(e)}</small></button>`).join('')||'<p class="link-notice">선택 공정에 연결된 항목이 없습니다.</p>'}`;
      this.$$('[data-focus-route]').forEach(el=>el.onclick=()=>this.selectRoute(el.dataset.focusRoute));
    }
  }
  mountGlobe() {
    try {
      const texture=new TextureLoader().load(earthTexture,()=>{if(!this.disposed&&!this.renderError)this.$('.loading-message').hidden=true;});
      texture.colorSpace=SRGBColorSpace;
      const material=new MeshPhongMaterial({map:texture,emissiveMap:texture,emissive:this.colors.land_emission,emissiveIntensity:.65,shininess:6});
      this.material=material;this.texture=texture;
      const globe=new Globe(this.$('.globe-canvas'),{animateIn:false,waitForGlobeReady:false,rendererConfig:{antialias:true,alpha:true,preserveDrawingBuffer:true}});
      this.globe=globe;
      globe.backgroundColor('rgba(0,0,0,0)').globeMaterial(material)
        .showAtmosphere(true).atmosphereColor(this.colors.atmosphere).atmosphereAltitude(.14)
        .globeCurvatureResolution(2)
        .pointLat('lat').pointLng('lon').pointAltitude(.006).pointRadius(n=>this.state.process==='전체'?.18+.09*n.process_count:n.id===this.state.selectedNode?.48:n.cluster?.4:.28)
        .pointColor(n=>this.nodeColor(n)).pointsTransitionDuration(0).pointResolution(16)
        .pointLabel(n=>this.nodeTooltip(n)).onPointClick(n=>this.selectNode(n.id))
        .arcStartLat(e=>this.lookup.get(e.from).lat).arcStartLng(e=>this.lookup.get(e.from).lon-(e.local?1.4:0))
        .arcEndLat(e=>this.lookup.get(e.to).lat).arcEndLng(e=>this.lookup.get(e.to).lon+(e.local?1.4:0))
        .arcColor(e=>this.routeColor(e)).arcAltitudeAutoScale(.24)
        .arcStroke(e=>this.state.process==='전체'?.1+Math.min(.65,e.flow_weight/1000):e.id===this.state.selectedRoute?.32:e.active?.18:.09)
        .arcDashLength(e=>e.blocked?.22:1).arcDashGap(e=>e.blocked?.12:0).arcDashAnimateTime(0)
        .arcCurveResolution(64).arcCircularResolution(5).arcsTransitionDuration(0)
        .arcLabel(e=>this.state.process==='전체'?`${esc(e.directions.join(' / '))}<br>${e.processes.length}개 공정 · 모델 배분 합 ${fmt(e.flow_weight)}<br>${STATE_LABELS[e.status]} · 물동량 아님`:`${esc(this.lookup.get(e.from).display_name||this.lookup.get(e.from).name)} → ${esc(this.lookup.get(e.to).display_name||this.lookup.get(e.to).name)}<br>${esc(e.item)} · ${STATE_LABELS[e.status]}<br>${badge(e)}<br>${e.synthetic?'표시 연결':e.item_status==='출처 있음'?esc(e.item_evidence_note||'품목 근거 있음'):'세부 품목 납품·실제 배분율 확인 필요'}`)
        .onArcClick(e=>this.selectRoute(e.id))
        .onGlobeClick(()=>this.clearFocus())
        .htmlLat('lat').htmlLng('lon').htmlAltitude(.014).htmlElement(n=>this.nodeLabel(n));
      const ambient=new AmbientLight('#b5d7ff',1.8);const sun=new DirectionalLight('#c7e3ff',2.2);sun.position.set(-100,180,250);
      globe.lights([ambient,sun]);
      globe.renderer().setPixelRatio(Math.min(window.devicePixelRatio||1,1.5));
      const controls=globe.controls();controls.enablePan=false;controls.minDistance=180;controls.maxDistance=620;
      controls.enableDamping=true;controls.dampingFactor=.09;controls.rotateSpeed=.65;controls.zoomSpeed=.7;controls.autoRotateSpeed=.35;
      const pause=()=>{if(this.state.rotate){this.userPaused=true;controls.autoRotate=false;this.toast('직접 조작 중에는 자동 회전을 멈춥니다.');}};
      controls.addEventListener('start',pause);this.cleanup.push(()=>controls.removeEventListener('start',pause));
      const changed=()=>{
        if(this.cameraFrame)return;
        this.cameraFrame=requestAnimationFrame(()=>{
          this.cameraFrame=null;
          const altitude=globe.pointOfView().altitude;
          const expanded=this.state.zoomExpanded?altitude<1.85:altitude<1.55;
          if(expanded!==this.state.zoomExpanded){this.state.zoomExpanded=expanded;if(this.state.level==='company')this.update();}
          this.refreshLabels();
        });
      };
      controls.addEventListener('change',changed);this.cleanup.push(()=>controls.removeEventListener('change',changed));
      const canvas=globe.renderer().domElement;
      this.listen(canvas,'pointerdown',e=>{this.pointerStart={x:e.clientX,y:e.clientY};});
      this.listen(canvas,'click',e=>{
        if(!this.pointerStart||Math.hypot(e.clientX-this.pointerStart.x,e.clientY-this.pointerStart.y)>5)return;
        const time=performance.now();
        // Globe handles surface clicks; this also covers empty space around it.
        this.timers.push(setTimeout(()=>{if((this.hitClickAt||0)<time-40&&this.state.focus)this.clearFocus();},0));
      });
      canvas.setAttribute('aria-label','회전 가능한 3D 공급망 지구본');canvas.setAttribute('tabindex','0');canvas.setAttribute('role','img');
      this.listen(canvas,'keydown',e=>{
        const pov=globe.pointOfView();const delta=10;
        if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','-','Home'].includes(e.key)){
          e.preventDefault();pause();
          if(e.key==='Home')this.resetCamera();
          else if(e.key==='+'||e.key==='-')this.zoom(e.key==='+'?.85:1.18);
          else globe.pointOfView({lat:Math.max(-80,Math.min(80,pov.lat+(e.key==='ArrowUp'?delta:e.key==='ArrowDown'?-delta:0))),lng:pov.lng+(e.key==='ArrowLeft'?-delta:e.key==='ArrowRight'?delta:0)},200);
        }
      });
      this.listen(canvas,'webglcontextlost',e=>{e.preventDefault();this.$('.loading-message').hidden=false;this.$('.loading-message').textContent='그래픽 연결이 중단되었습니다. 페이지를 새로고침해 주세요.';});
      this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(this.$('.globe-viewport'));
      this.updateGlobe();this.resize();this.resetCamera(false);
      this.visibility=()=>{if(document.hidden||this.state.tab!=='globe')globe.pauseAnimation();else globe.resumeAnimation();};
      document.addEventListener('visibilitychange',this.visibility);this.cleanup.push(()=>document.removeEventListener('visibilitychange',this.visibility));
    } catch(error) {
      this.renderError=true;
      this.$('.loading-message').innerHTML='<p>3D 지구본을 불러오지 못했습니다.</p><small>브라우저의 WebGL 지원과 그래픽 가속 설정을 확인해 주세요.<br>상세 데이터 탭은 계속 사용할 수 있습니다.</small>';
      console.error('Globe initialization failed',error);
    }
  }
  nodeColor(n) {
    const color=n.blocked?this.colors.red:n.warning?this.colors.amber:n.type==='material_display'?'#B3AAFF':n.active?this.colors.cyan:this.colors.context_node;
    return this.state.focus&&!n.focused?dim(color):color;
  }
  routeColor(e) {
    if(this.state.poster&&!e.active)return '#234468';
    if(this.state.focus&&!e.focused)return dim(e.blocked?this.colors.red:e.warning?this.colors.amber:this.colors.cyan);
    if(this.state.focus&&e.focused)return e.blocked?this.colors.red:e.warning?this.colors.amber:this.colors.cyan;
    if(e.id===this.state.selectedRoute)return e.blocked?this.colors.red:e.warning?this.colors.amber:this.colors.cyan;
    if(e.blocked)return e.active?this.colors.red:this.colors.context_red;
    if(e.warning)return e.active?this.colors.amber:this.colors.context_amber;
    return e.active?[this.colors.arc_start,this.colors.cyan]:this.colors.context_arc;
  }
  nodeTooltip(n) {if(this.state.process==='전체')return `${esc(n.country)} · ${n.process_count}개 공정 관여<br>${esc(n.processes.join(' · '))}<br>${n.blocked?'× 중단':n.warning?'△ 감소':'● 정상'} · 최악 직접 경로 상태`;return `${esc(n.name)}<br>${esc(n.country)} · ${esc(n.role||n.category)}<br>${n.blocked?'× 중단':n.warning?'△ 감소':'● 정상'} 가정<br>${badge(n)}${n.cluster?'<br>클릭하면 core 기업을 펼칩니다.':''}${n.company_name?'<br>국가 묶음용 표시 좌표 · 실제 공장 위치 아님':''}`;}
  nodeLabel(n) {
    const el=document.createElement('button');el.className=`globe-node-label ${n.active?'active':'dim'} ${n.blocked?'blocked':n.warning?'warning':''} ${this.state.focus&&!n.focused?'unfocused':''}`;
    el.textContent=`${n.blocked?'× ':n.warning?'△ ':''}${n.type==='material_display'?'◇ ':n.type==='process_display'?'□ ':''}${n.display_name||n.name}`;
    el.title=`${n.name} 선택`;el.onclick=e=>{e.stopPropagation();this.selectNode(n.id);};
    return el;
  }
  updateGlobe() {
    this.globe.pointsData(this.view.nodes).arcsData(this.state.routes?this.view.routes:[])
      .showAtmosphere(this.state.atmosphere);
    this.globe.controls().autoRotate=this.state.rotate&&!this.userPaused;
    this.refreshLabels();
  }
  refreshLabels(){
    if(!this.globe)return;
    if(!this.state.labels){this.globe.htmlElementsData([]);this.labelSignature=null;return;}
    const box=this.$('.globe-viewport').getBoundingClientRect(),camera=this.globe.camera();
    const projected=this.view.nodes.map(n=>{
      const p=this.globe.getCoords(n.lat,n.lon,.014),world=new Vector3(p.x,p.y,p.z);
      const visible=world.dot(camera.position.clone().sub(world))>0;
      world.project(camera);
      const name=n.display_name||n.name;
      return {...n,x:(world.x+1)*box.width/2,y:(1-world.y)*box.height/2,
        width:Math.max(55,[...name].reduce((s,c)=>s+(/[^\x00-\x7F]/.test(c)?10:6),20)),
        visible:visible&&world.z<1&&Math.abs(world.x)<.85&&Math.abs(world.y)<.9};
    });
    const labels=priorityLabels(projected,LABEL_LIMITS[this.state.level]);
    const signature=JSON.stringify(labels.map(n=>[n.id,n.lat,n.lon,n.blocked,n.warning,n.focused,n.display_name]));
    if(signature!==this.labelSignature){this.labelSignature=signature;this.globe.htmlElementsData(labels);}
  }
  resize() {
    if(!this.globe||this.state.tab!=='globe')return;
    const box=this.$('.globe-viewport').getBoundingClientRect();
    if(box.width<20||box.height<20)return;
    this.globe.width(box.width).height(box.height);
    this.refreshLabels();
    const aspect=box.width/box.height;
    const previousFit=this.fitAltitude;
    this.fitAltitude=Math.max(1.9,aspect<1?2.15/aspect:2.15);
    if(!this.hasSized){this.hasSized=true;this.resetCamera(false);}
    else if(previousFit&&Math.abs(previousFit-this.fitAltitude)>.05){
      const current=this.globe.pointOfView();
      this.globe.pointOfView({altitude:Math.min(5.2,current.altitude*this.fitAltitude/previousFit)},0);
    }
  }
  resetCamera(animate=true) {
    if(!this.globe)return;
    this.globe.pointOfView({...VIEWS[this.state.region],altitude:this.fitAltitude||2.15},animate?650:0);
  }
  zoom(factor) {if(this.globe)this.globe.pointOfView({altitude:Math.max(.8,Math.min(5.2,this.globe.pointOfView().altitude*factor))},240);}
  selectRoute(id) {
    if(this.state.process==='전체')return;
    this.hitClickAt=performance.now();
    const edge=this.view.allRoutes.find(e=>e.id===id)||this.view.canonical.routes.find(e=>e.id===id)||this.view.selected.find(e=>e.id===id);
    if(!edge)return;
    if(this.state.selectedRoute===id){this.clearFocus();return;}
    if(!edge.active)this.state.process=edge.processes[0];
    this.state.selectedRoute=id;this.state.selectedNode=null;this.state.routePage=0;
    this.state.focus={type:'route',id,member_ids:edge.member_ids||[id],name:edge.item};
    this.update();
    const n=this.lookup.get(edge.to);if(n)this.globe?.pointOfView({lat:n.lat,lng:n.lon},650);
  }
  selectNode(id) {
    this.hitClickAt=performance.now();
    const n=this.lookup.get(id);if(!n)return;
    if(n.cluster){this.state.expandedCountries=[...new Set([...this.state.expandedCountries,n.country])];this.update();return;}
    if(n.type==='material_display'){this.selectMaterial(n.item_id);return;}
    this.state.selectedNode=id;this.state.selectedRoute=null;this.state.routePage=0;
    this.state.focus={type:'node',id,member_node_ids:n.member_node_ids||[id],name:n.display_name||n.name};this.update();
  }
  selectCompany(id){
    const n=this.data.nodes.find(n=>n.id===id);if(!n)return;
    this.state.expandedCountries=[...new Set([...this.state.expandedCountries,n.country])];this.selectNode(id);
    const shown=this.lookup.get(id);this.globe?.pointOfView({lat:shown.lat,lng:shown.lon},500);
  }
  selectMaterial(id){
    const item=this.data.items.find(i=>i.id===id);if(!item)return;
    this.hitClickAt=performance.now();this.state.selectedNode=`material:${id}`;this.state.selectedRoute=null;this.state.routePage=0;
    this.state.focus={type:'material',id,name:item.name};this.update();
    const n=this.lookup.get(`material:${id}`);if(n&&this.state.level==='chain')this.globe?.pointOfView({lat:n.lat,lng:n.lon},500);
  }
  updateNodeDetail() {
    const panel=this.$('.node-detail');const node=this.lookup.get(this.state.selectedNode);
    panel.hidden=!node;
    if(node){panel.innerHTML=`<div class="divider"></div><div class="node-detail-heading"><h3>${icon('pin')}${esc(node.name)}</h3><button class="close-button" aria-label="거점 상세 닫기">${icon('close')}</button></div><p>${esc(node.country)} · ${esc(node.role||node.category)} ${badge(node)}</p><small class="source-detail">${sourceDetails(node)}</small><small>표시 좌표 ${node.lat.toFixed(2)}° / ${node.lon.toFixed(2)}° · 실제 시설/산지 위치 아님</small>`;panel.querySelector('button').onclick=()=>this.clearFocus();}
  }
  toast(message) {const el=this.$('.map-toast');el.textContent=message;el.classList.add('visible');clearTimeout(this.toastTimer);this.toastTimer=setTimeout(()=>el.classList.remove('visible'),2500);}
  download() {
    const rows=this.view.allRoutes.map(e=>({...e,from_name:this.lookup.get(e.from).name,to_name:this.lookup.get(e.to).name}));
    const url=URL.createObjectURL(new Blob([JSON.stringify(rows,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='supply-routes-demo.json';a.click();this.timers.push(setTimeout(()=>URL.revokeObjectURL(url),1000));
  }
  downloadReport() {
    if(!this.view.report)return;
    const payload={notice:this.data.simulation.notice,model_version:this.data.simulation.model_version,
      baseline:this.data.simulation.baseline,scenario:this.view.report,
      data_evidence:{core_selection:this.data.core_selection,nodes:this.data.nodes,items:this.data.items,edges:this.data.edges,
        research_summary:this.data.research_summary,public_metrics:this.data.public_metrics,evidence_catalog:this.data.evidence_catalog}};
    const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download='bottleneck-simulation-demo.json';a.click();
    this.timers.push(setTimeout(()=>URL.revokeObjectURL(url),1000));
  }
  dispose() {
    this.disposed=true;this.observer?.disconnect();this.cleanup.forEach(fn=>fn());this.timers.forEach(clearTimeout);clearTimeout(this.toastTimer);
    cancelAnimationFrame(this.cameraFrame);
    this.globe?._destructor();this.globe?.renderer().dispose();this.texture?.dispose();this.material?.dispose();
  }
}

export default function render({parentElement,data,setStateValue}) {
  const root=parentElement.querySelector('.supply-root');
  // Component reruns update the existing dashboard instead of rebuilding WebGL.
  if(root.__dashboard){clearTimeout(root.__disposeTimer);root.__dashboard.send=setStateValue;root.__dashboard.receiveData(data);}
  else root.__dashboard=new Dashboard(root,data,setStateValue);
  return ()=>{root.__disposeTimer=setTimeout(()=>{if(!root.isConnected){root.__dashboard?.dispose();delete root.__dashboard;}},100);};
}
