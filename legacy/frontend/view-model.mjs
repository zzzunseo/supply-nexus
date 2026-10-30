/** Presentation graph only. All capacity scores come from the Python engine. */
export const LABEL_LIMITS={country:8,company:10,chain:12};
export const MAX_ARCS=15;
export function currentReport(data, state) {
  const simulation=data.simulation;
  if(!simulation)return null;
  if(['duration_days','severity','inventory','substitutes'].some(k=>simulation.options[k]!==state[k]))return null;
  return simulation.reports[state.scenario] || null;
}

function legacyView(data, state) {
  const scenario = data.scenarios.find(s => s.name === state.scenario) || data.scenarios[0];
  const affected = new Set(scenario.affected);
  const report = currentReport(data, state);
  const routeStatus = e => report?.edge_status[e.id] ?? (data.simulation?'normal':affected.has(e.from)||affected.has(e.to)?'stopped':'normal');
  const selected = data.edges.filter(e => e.processes.includes(state.process));
  const candidates = state.context ? [...selected, ...data.edges.filter(e => !e.processes.includes(state.process))] : selected;
  const routes = candidates.slice(0, 15).map(e => ({
    ...e, active: e.processes.includes(state.process),
    status: routeStatus(e), blocked: routeStatus(e)==='stopped', warning: routeStatus(e)==='warning',
  }));
  const ids = new Set(routes.flatMap(e => [e.from, e.to]));
  const activeIds = new Set(selected.flatMap(e => [e.from, e.to]));
  const nodes = data.nodes.filter(n => ids.has(n.id)).map(n => ({
    ...n, active: activeIds.has(n.id),
    blocked: report ? report.node_availability[n.id]===0 : !data.simulation&&affected.has(n.id),
    warning: report ? report.node_availability[n.id]>0&&report.node_availability[n.id]<1 : false,
  }));
  return {scenario, report, routes, nodes, selected: routes.filter(e => e.active),
    blocked: routes.filter(e => e.blocked), affectedNodes: nodes.filter(n => n.blocked)};
}

export function initialState(data) {
  return {process: '포토', scenario: data.scenarios[0].name, region: '아시아·태평양',
    context: true, routes: true, labels: true, atmosphere: true, rotate: false,
    poster:false, tab: 'globe', selectedNode: null, selectedRoute: null, level:'country',focus:null,
    expandedCountries:[],zoomExpanded:false,routePage:0,
    duration_days:14,severity:1,inventory:true,substitutes:false,...data.simulation?.options};
}

const flags=rate=>({availability:rate,status:rate===0?'stopped':rate<1?'warning':'normal',blocked:rate===0,warning:rate>0&&rate<1});
const members=e=>e.member_ids||[e.id];
const evidence=rows=>rows.some(e=>e.relation_status==='확인 필요')?'확인 필요':rows.some(e=>e.relation_status==='가정값')?'가정값':'출처 있음';
export function aggregateFlows(edges,nodeMap,endpoint,prefix='country') {
  const groups=new Map();
  for(const e of edges){
    const key=JSON.stringify([endpoint(nodeMap.get(e.from)),endpoint(nodeMap.get(e.to)),e.item_id||e.item,[...e.processes].sort()]);
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push(e);
  }
  return [...groups.entries()].map(([key,rows])=>{
    const [from,to]=JSON.parse(key),total=rows.reduce((s,e)=>s+(e.model_share_pct??1),0);
    const rate=total?rows.reduce((s,e)=>s+e.availability*(e.model_share_pct??1),0)/total:Math.min(...rows.map(e=>e.availability));
    return {...rows[0],id:`${prefix}:${key}`,from,to,member_ids:rows.flatMap(members),
      share_pct:rows.every(e=>e.share_pct!=null)?rows.reduce((s,e)=>s+e.share_pct,0):null,
      model_share_pct:total,source:'국가/기업 묶음의 원본 경로 근거는 우측 목록에서 확인',source_year:null,relation_status:evidence(rows),
      evidence_scope:new Set(rows.map(e=>e.evidence_scope)).size===1?rows[0].evidence_scope:'aggregate',
      evidence_ids:[...new Set(rows.flatMap(e=>e.evidence_ids||[]))],
      item_status:rows.every(e=>e.item_status==='출처 있음')?'출처 있음':'확인 필요',
      relationship_count:rows.length,local:from===to,...flags(rate)};
  });
}

export function buildChainGraph(data,edges,process) {
  const lookup=new Map(data.nodes.map(n=>[n.id,n]));
  const ids=new Set(edges.flatMap(e=>[e.from,e.to]));
  const nodes=data.nodes.filter(n=>ids.has(n.id)).map(n=>({...n}));
  const routes=edges.map(e=>({...e,member_ids:[e.id]}));
  const processNode={id:`process:${process}`,name:`${process} 공정`,display_name:`${process} 공정`,
    type:'process_display',country:'공정 표시',role:'공정 표시점 · 실제 시설 아님',lat:8,lon:138,
    active:true,source:'UI 연계도용 표시점',source_year:null,status:'가정값'};
  if(edges.length)nodes.push(processNode);
  for(const [index,item] of (data.items||[]).filter(i=>i.processes.includes(process)).entries()){
    const itemEdges=edges.filter(e=>e.item_id===item.id);
    if(!itemEdges.length)continue;
    const suppliers=[...new Set(itemEdges.map(e=>e.from))],anchor=lookup.get(suppliers[0]);
    const materialId=`material:${item.id}`;
    nodes.push({...item,id:materialId,item_id:item.id,type:'material_display',country:'소재 표시',
      role:'소재 표시점 · 실제 산지 아님',lat:Math.max(-75,anchor.lat+8+index*5),
      lon:((anchor.lon-14-index*9+540)%360)-180,active:true,display_name:item.name});
    for(const supplier of suppliers){
      const supporting=itemEdges.filter(e=>e.from===supplier),source=item.product_sources?.find(s=>s.company_id===supplier);
      const id=`capability:${item.id}:${supplier}`;
      routes.push({id,from:materialId,to:supplier,item:item.name,item_id:item.id,processes:[process],
        active:true,synthetic:true,relation_kind:'product_capability',relation_status:source?.status||'확인 필요',
        source:source?.source??null,source_year:source?.source_year??null,member_ids:[id],
        ...flags(Math.min(...supporting.map(e=>e.availability)))});
    }
    for(const receiver of new Set(itemEdges.map(e=>e.to))){
      const id=`usage:${item.id}:${receiver}`;
      routes.push({id,from:receiver,to:processNode.id,item:item.name,item_id:item.id,processes:[process],
        active:true,synthetic:true,relation_kind:'process_usage',relation_status:'가정값',
        source:'선택 공정 투입을 표현하는 시연용 연결. 실제 레시피·시설 적합성 확인 필요.',
        source_year:null,member_ids:[id],...flags(Math.min(...itemEdges.filter(e=>e.to===receiver).map(e=>e.availability)))});
    }
  }
  return {nodes,routes};
}

/** Directed search: siblings that merely share a customer remain dim. */
export function computeFocus(graph,focus) {
  if(!focus)return null;
  const focusEdges=focus.type==='route'?graph.routes.filter(e=>members(e).some(id=>(focus.member_ids||[focus.id]).includes(id))):[];
  const item=focus.type==='material'?focus.id.replace(/^material:/,''):null;
  const routes=item?graph.routes.filter(e=>e.item_id===item):graph.routes;
  const seeds=focus.type==='route'?new Set(focusEdges.flatMap(e=>[e.from,e.to])):
    new Set(focus.member_node_ids||[focus.type==='material'?`material:${item}`:focus.id]);
  const nodeIds=new Set(seeds),edgeIds=new Set(focusEdges.flatMap(members));
  function walk(initial,direction){
    const seen=new Set(initial),queue=[...initial];
    while(queue.length){
      const id=queue.shift();
      for(const e of routes){
        if((direction==='up'?e.to:e.from)!==id)continue;
        const next=direction==='up'?e.from:e.to;
        members(e).forEach(eid=>edgeIds.add(eid));nodeIds.add(next);
        if(!seen.has(next)){seen.add(next);queue.push(next);}
      }
    }
  }
  walk(focus.type==='route'?focusEdges.map(e=>e.from):seeds,'up');
  walk(focus.type==='route'?focusEdges.map(e=>e.to):seeds,'down');
  return {nodeIds,edgeIds};
}

/** Screen-space collisions are resolved before applying the level label budget. */
export function priorityLabels(projected,limit) {
  const score=n=>(n.blocked?300:n.warning?200:n.active?100:0)+(n.focused?10:0);
  const ordered=[...projected].sort((a,b)=>score(b)-score(a)||a.id.localeCompare(b.id));
  const accepted=[];
  for(const n of ordered){
    if(n.visible===false||accepted.length>=limit)continue;
    const box={left:n.x+8,right:n.x+8+(n.width??100),top:n.y-20,bottom:n.y-20+(n.height??23)};
    if(accepted.some(a=>box.left<a.box.right+6&&box.right>a.box.left-6&&box.top<a.box.bottom+5&&box.bottom>a.box.top-5))continue;
    accepted.push({...n,box});
  }
  return accepted;
}

export function selectView(data,state) {
  if(!data.items){const v=legacyView(data,state);return {...v,allRoutes:v.routes,canonical:{nodes:v.nodes,routes:v.routes},pages:1,page:0,totalRoutes:v.routes.length};}
  if(state.process==='전체'){
    const report=currentReport(data,state),summary=report?.overview;
    const scenario=data.scenarios.find(s=>s.name===state.scenario)||data.scenarios[0];
    const nodes=(summary?.countries||[]).filter(n=>n.process_count).map(n=>({...n,name:n.country,display_name:n.country,type:'country_hub',active:true,
      blocked:n.status==='stopped',warning:n.status==='warning',focused:!state.focus||state.focus.id===n.id}));
    const routes=(summary?.flows||[]).map(e=>({...e,active:true,blocked:e.status==='stopped',warning:e.status==='warning',item:'국가 간 합산 흐름 · 가정값',
      focused:!state.focus||e.from===state.focus.id||e.to===state.focus.id}));
    return {scenario,report,summary,nodes,routes,allRoutes:routes,selected:[],blocked:routes.filter(e=>e.blocked),affectedNodes:nodes.filter(n=>n.blocked),
      canonical:{nodes,routes},pages:1,page:0,totalRoutes:routes.length};
  }
  const scenario=data.scenarios.find(s=>s.name===state.scenario)||data.scenarios[0];
  const report=currentReport(data,state),lookup=new Map(data.nodes.map(n=>[n.id,n]));
  const affected=new Set(scenario.affected);
  const countries=new Set(data.nodes.filter(n=>affected.has(n.id)&&n.type==='country_hub').map(n=>n.country));
  const nodeRate=n=>report?.node_display_availability?.[n.id]??report?.node_availability?.[n.id]??(!data.simulation&&(affected.has(n.id)||countries.has(n.country))?1-state.severity:1);
  const decorated=data.edges.map(e=>{
    const rate=report?.edge_availability?.[e.id]??Math.min(nodeRate(lookup.get(e.from)),nodeRate(lookup.get(e.to)));
    return {...e,active:e.processes.includes(state.process),relation_status:e.status||'확인 필요',member_ids:[e.id],...flags(rate)};
  });
  const core=new Set(data.core_companies[state.process]);
  const selectedEdges=decorated.filter(e=>e.active&&core.has(e.from)&&core.has(e.to));
  const canonical=buildChainGraph(data,selectedEdges,state.process),focused=computeFocus(canonical,state.focus);
  let graph;
  if(state.poster){
    graph={nodes:spreadCompanies(data.nodes.filter(n=>n.company_name),lookup),routes:decorated};
  }else if(state.level==='chain'){
    graph=canonical;
    // Keep companies separated in the chain view as well as in expanded company view.
    graph.nodes=spreadCompanies(graph.nodes,lookup);
  }else if(state.level==='company'){
    const selectedNodes=data.nodes.filter(n=>core.has(n.id)),endpoints=new Map(),nodes=[];
    for(const country of new Set(selectedNodes.map(n=>n.country))){
      const group=selectedNodes.filter(n=>n.country===country).sort((a,b)=>a.id.localeCompare(b.id));
      const hub=lookup.get(group[0].country_hub_id);
      if(!state.zoomExpanded&&!(state.expandedCountries||[]).includes(country)&&group.length>1){
        nodes.push({...hub,id:`cluster:${country}`,name:`${country} · ${group.length}개 core 기업`,
          display_name:`${country} · ${group.length}`,cluster:true,member_node_ids:group.map(n=>n.id)});
        group.forEach(n=>endpoints.set(n.id,`cluster:${country}`));
      }else{
        nodes.push(...spreadCompanies(group,lookup));group.forEach(n=>endpoints.set(n.id,n.id));
      }
    }
    graph={nodes,routes:aggregateFlows(selectedEdges,lookup,n=>endpoints.get(n.id),'company')};
  }else{
    const hub=new Map();data.nodes.filter(n=>n.type==='country_hub').forEach(n=>{if(!hub.has(n.country))hub.set(n.country,n.id);});
    const candidates=state.context?[...selectedEdges,...decorated.filter(e=>!e.active)]:selectedEdges;
    graph={routes:aggregateFlows(candidates,lookup,n=>hub.get(n.country)),
      nodes:data.nodes.filter(n=>n.type==='country_hub'&&hub.get(n.country)===n.id).map(n=>({...n,
        member_node_ids:data.nodes.filter(c=>c.type!=='country_hub'&&c.country===n.country).map(c=>c.id),display_name:n.country}))};
  }
  const activeIds=new Set(selectedEdges.flatMap(e=>[e.from,e.to]));
  const nodes=graph.nodes.map(n=>{
    const ids=n.member_node_ids||[n.id],rates=ids.filter(id=>lookup.has(id)&&lookup.get(id).type!=='country_hub').map(id=>nodeRate(lookup.get(id)));
    const incident=canonical.routes.filter(e=>e.from===n.id||e.to===n.id);
    const rate=rates.length?Math.min(...rates):incident.length?Math.min(...incident.map(e=>e.availability)):1;
    return {...n,evidence_status:n.status,active:n.active||ids.some(id=>activeIds.has(id)),focused:!focused||ids.some(id=>focused.nodeIds.has(id)),...flags(rate)};
  });
  const routes=graph.routes.map(e=>({...e,focused:!focused||members(e).some(id=>focused.edgeIds.has(id))}));
  routes.sort((a,b)=>Number(b.focused)-Number(a.focused)||Number(b.active)-Number(a.active));
  const cap=Math.min(MAX_ARCS,data.ui_limits?.max_arcs||MAX_ARCS);
  // A material's complete path stays together. Never display orphaned active nodes.
  const batches=[[]];
  const groups=state.level==='chain'&&!state.poster?[...new Set(routes.map(e=>e.item_id))].map(id=>routes.filter(e=>e.item_id===id)):routes.map(e=>[e]);
  for(const group of groups){
    if(batches.at(-1).length && batches.at(-1).length+group.length>cap)batches.push([]);
    batches.at(-1).push(...group);
  }
  const pages=state.poster?1:batches.length,page=Math.min(state.routePage||0,pages-1);
  const visible=state.poster?routes:batches[page];
  const visibleIds=new Set(visible.flatMap(e=>[e.from,e.to]));
  return {scenario,report,routes:visible,allRoutes:routes,nodes:nodes.filter(n=>visibleIds.has(n.id)),
    selected:selectedEdges,blocked:visible.filter(e=>e.blocked),affectedNodes:nodes.filter(n=>n.blocked),canonical,focus:focused,pages,page,totalRoutes:routes.length};
}

function spreadCompanies(nodes,lookup){
  return nodes.map(n=>{
    if(!n.company_name)return n;
    const group=nodes.filter(c=>c.company_name&&c.country===n.country).sort((a,b)=>a.id.localeCompare(b.id));
    const hub=lookup.get(n.country_hub_id),angle=2*Math.PI*group.findIndex(c=>c.id===n.id)/group.length,radius=group.length>1?2.4:0;
    return {...n,lat:hub.lat+Math.sin(angle)*radius,lon:hub.lon+Math.cos(angle)*radius/Math.max(.4,Math.cos(hub.lat*Math.PI/180)),
      display_name:n.company_name,member_node_ids:[n.id]};
  });
}

export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
