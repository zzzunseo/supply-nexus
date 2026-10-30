import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {selectView,initialState,escapeHtml,currentReport} from '../legacy/frontend/view-model.mjs';
const data=JSON.parse(readFileSync(new URL('./fixtures/legacy_demo.json',import.meta.url)));

test('all eight process filters retain their own routes and valid endpoints',()=>{
  for(const process of data.processes){
    const view=selectView(data,{...initialState(data),process,context:false});
    assert.ok(view.routes.length>0);
    assert.ok(view.routes.every(e=>e.processes.includes(process)));
    const ids=new Set(view.nodes.map(n=>n.id));
    assert.ok(view.routes.every(e=>ids.has(e.from)&&ids.has(e.to)));
  }
});
test('outage affects only directly connected routes; recovery clears statuses',()=>{
  const state=initialState(data);
  for(const scenario of data.scenarios){
    const view=selectView(data,{...state,scenario:scenario.name});
    assert.deepEqual(view.blocked.map(e=>e.id),view.routes.filter(e=>scenario.affected.includes(e.from)||scenario.affected.includes(e.to)).map(e=>e.id));
  }
  assert.equal(selectView(data,state).blocked.length,0);
});
test('context is dimmed, selected routes are prioritised, limit is 15',()=>{
  const view=selectView(data,initialState(data));
  assert.equal(view.routes.length,15);
  assert.equal(view.selected.length,3);
  assert.ok(view.routes.slice(0,3).every(e=>e.active));
  assert.ok(view.routes.slice(3).every(e=>!e.active));
});
test('display strings escape markup before insertion',()=>{
  assert.equal(escapeHtml('<img src=x onerror="x">'), '&lt;img src=x onerror=&quot;x&quot;&gt;');
});
test('changing model conditions hides outdated scores until Python responds',()=>{
  const state=initialState(data);
  const enriched={...data,simulation:{options:{duration_days:14,severity:1,inventory:true,substitutes:false},reports:{[state.scenario]:{overall_score:100}}}};
  assert.equal(currentReport(enriched,state).overall_score,100);
  assert.equal(currentReport(enriched,{...state,duration_days:30}),null);
  assert.equal(currentReport(enriched,{...state,inventory:false}),null);
});
test('map states use Python capacities including partial disruption',()=>{
  const state=initialState(data);
  const enriched={...data,simulation:{options:{duration_days:14,severity:1,inventory:true,substitutes:false},reports:{[state.scenario]:{
    edge_status:Object.fromEntries(data.edges.map(e=>[e.id,e.id==='r05'?'warning':'normal'])),
    node_availability:Object.fromEntries(data.nodes.map(n=>[n.id,n.id==='eindhoven'?.5:1]))
  }}}};
  const view=selectView(enriched,state);
  assert.equal(view.routes.find(e=>e.id==='r05').warning,true);
  assert.equal(view.routes.find(e=>e.id==='r05').blocked,false);
  assert.equal(view.nodes.find(n=>n.id==='eindhoven').warning,true);
});
