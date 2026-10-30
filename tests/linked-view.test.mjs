import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {selectView,initialState,computeFocus,priorityLabels} from '../legacy/frontend/view-model.mjs';
const data=JSON.parse(readFileSync(new URL('../data/demo.json',import.meta.url)));

test('every process/level/page has valid endpoints, core-only corporate nodes and <=15 arcs',()=>{
  for(const process of data.processes)for(const level of ['country','company','chain']){
    const state={...initialState(data),process,level,context:false},first=selectView(data,state),seen=new Set();
    for(let routePage=0;routePage<first.pages;routePage++){
      const view=selectView(data,{...state,routePage}),ids=new Set(view.nodes.map(n=>n.id));
      assert.ok(view.routes.length<=15);
      for(const e of view.routes){assert.ok(ids.has(e.from)&&ids.has(e.to));seen.add(e.id);}
      for(const n of view.nodes.filter(n=>n.company_name))assert.ok(data.core_companies[process].includes(n.id));
    }
    assert.equal(seen.size,first.totalRoutes);
  }
});
test('country aggregation conserves input weights without fabricating real shares',()=>{
  for(const process of data.processes){
    const view=selectView(data,{...initialState(data),process,context:false});
    for(const item of data.items.filter(i=>i.processes.includes(process))){
      const grouped=view.allRoutes.filter(e=>e.item_id===item.id);
      assert.equal(grouped.reduce((sum,e)=>sum+e.model_share_pct,0),100);
      assert.ok(grouped.every(e=>e.share_pct===null));
      assert.ok(grouped.every(e=>e.evidence_scope&&Array.isArray(e.evidence_ids)));
    }
  }
});
test('same-country cores collapse, explicitly expand or expand on zoom',()=>{
  const state={...initialState(data),level:'company'};
  assert.ok(selectView(data,state).nodes.some(n=>n.cluster&&n.country==='일본'));
  for(const extra of [{expandedCountries:['일본']},{zoomExpanded:true}]){
    const view=selectView(data,{...state,...extra});
    assert.ok(!view.nodes.some(n=>n.cluster&&n.country==='일본'));
    const japan=view.nodes.filter(n=>n.company_name&&n.country==='일본');
    assert.equal(japan.length,3);
    assert.equal(new Set(japan.map(n=>`${n.lat}:${n.lon}`)).size,3);
  }
});
test('material focus contains only that item and dims unrelated routes',()=>{
  const view=selectView(data,{...initialState(data),level:'chain',focus:{type:'material',id:'developer'}});
  assert.ok(view.focus.edgeIds.size>0);
  const focused=view.canonical.routes.filter(e=>view.focus.edgeIds.has(e.id));
  assert.ok(focused.every(e=>e.item_id==='developer'));
  assert.ok(view.allRoutes.some(e=>!e.focused));
});
test('directed route focus follows ancestors and descendants without unrelated siblings',()=>{
  const graph={routes:[{id:'ab',from:'a',to:'b'},{id:'cb',from:'c',to:'b'},{id:'bd',from:'b',to:'d'}]};
  const focus=computeFocus(graph,{type:'route',id:'ab'});
  assert.deepEqual([...focus.edgeIds].sort(),['ab','bd']);
  assert.ok(!focus.nodeIds.has('c'));
});
test('country route focus resolves grouped corporate member IDs',()=>{
  const state={...initialState(data),context:false};
  const route=selectView(data,state).routes.find(e=>e.item_id==='photoresist');
  const view=selectView(data,{...state,focus:{type:'route',id:route.id,member_ids:route.member_ids}});
  assert.ok(view.routes.find(e=>e.id===route.id).focused);
  assert.ok(view.routes.some(e=>!e.focused));
});
test('label budget and collisions prefer stopped, then warning, then selected process',()=>{
  const rows=[{id:'other',x:10,y:10},{id:'active',x:10,y:10,active:true},
    {id:'warning',x:10,y:10,warning:true},{id:'stopped',x:10,y:10,blocked:true},
    {id:'far',x:300,y:200,active:true},{id:'back',x:500,y:20,visible:false}];
  assert.deepEqual(priorityLabels(rows,8).map(n=>n.id),['stopped','far']);
  assert.equal(priorityLabels(rows,1).length,1);
});
test('company capacities aggregate with demo weights, not worst route status',()=>{
  const state={...initialState(data),context:false};
  const reports={[state.scenario]:{node_availability:Object.fromEntries(data.nodes.map(n=>[n.id,n.id==='jsr'?0:1])),
    edge_availability:Object.fromEntries(data.edges.map(e=>[e.id,e.from==='jsr'?0:1]))}};
  const view=selectView({...data,simulation:{options:{duration_days:14,severity:1,inventory:true,substitutes:false},reports}},state);
  const routes=view.routes.filter(e=>e.item_id==='photoresist');
  assert.ok(routes.every(e=>e.availability===.5&&e.warning));
});
test('country aggregation retains collaboration, planned contract and unknown item scope',()=>{
  const state={...initialState(data),process:'패키징',context:false};
  const view=selectView(data,state);
  const planned=view.allRoutes.find(e=>e.member_ids.includes('processed-wafer:tsmc>amkor'));
  assert.equal(planned.evidence_scope,'planned_contract');
  assert.equal(planned.item_status,'확인 필요');
  assert.ok(planned.evidence_ids.includes('amkor-tsmc-2024'));
});

test('chain pagination preserves whole material paths without isolated nodes',()=>{
  for(const process of data.processes){
    const state={...initialState(data),process,level:'chain'},first=selectView(data,state);
    for(let routePage=0;routePage<first.pages;routePage++){
      const view=selectView(data,{...state,routePage});
      for(const item of new Set(view.routes.map(e=>e.item_id)))assert.equal(view.routes.filter(e=>e.item_id===item).length,view.allRoutes.filter(e=>e.item_id===item).length);
      for(const n of view.nodes)assert.ok(view.routes.some(e=>e.from===n.id||e.to===n.id));
    }
  }
});
test('presentation displays every original corporate edge once without synthetic routes',()=>{
  const view=selectView(data,{...initialState(data),poster:true});
  assert.equal(view.routes.length,data.edges.length);
  assert.equal(new Set(view.routes.map(e=>e.id)).size,data.edges.length);
  assert.ok(view.routes.some(e=>!e.active));
  assert.ok(view.routes.every(e=>!e.synthetic));
  assert.equal(view.pages,1);
});
