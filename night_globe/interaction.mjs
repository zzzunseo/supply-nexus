export const routeKey=r=>r.id||`${r.kind}|${r.start}|${r.end}`;
export const cameraChanged=(previous,next)=>!previous||(previous.camera_context||previous.context)!==(next.camera_context||next.context);
export function validSelection(data,pick){
 if(!pick||pick.context!==data.context)return null;
 if(pick.kind==='clear')return {kind:'clear',id:null,context:data.context};
 const ids=pick.kind==='marker'?data.markers.map(m=>m.id):pick.kind==='route'?data.routes.map(routeKey):[];
 return ids.includes(pick.id)?{kind:pick.kind,id:pick.id,context:data.context}:null;
}
export function routeSelected(route,selected){
 return !!selected&&(selected.kind==='route'?routeKey(route)===selected.id:
  selected.kind==='marker'&&(route.start===selected.id||route.end===selected.id));
}
export function focusCenter(markers){
 const valid=markers.filter(m=>Number.isFinite(m.lat)&&Number.isFinite(m.lon));
 if(!valid.length)return {lat:29,lon:120,distance:2.18};
 const xyz=valid.reduce((s,m)=>{const lat=m.lat*Math.PI/180,lon=m.lon*Math.PI/180;return [s[0]+Math.cos(lat)*Math.cos(lon),s[1]+Math.sin(lat),s[2]+Math.cos(lat)*Math.sin(lon)];},[0,0,0]);
 const length=Math.hypot(...xyz);if(length<1e-7)return {lat:29,lon:120,distance:3.5};
 return {lat:Math.asin(xyz[1]/length)*180/Math.PI,lon:Math.atan2(xyz[2],xyz[0])*180/Math.PI,distance:2.18};
}
export const ease=t=>{const p=Math.min(1,Math.max(0,t));return p*p*(3-2*p);};
