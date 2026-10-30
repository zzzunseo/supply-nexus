import * as THREE from '../legacy/frontend/node_modules/three/build/three.module.js';
import {OrbitControls} from '../legacy/frontend/node_modules/three/examples/jsm/controls/OrbitControls.js';
import nightUrl from './assets/earth-night.jpg';
import dayUrl from './assets/earth-day.jpg';
import topologyUrl from './assets/earth-topology.png';
import boundaries from './assets/boundaries.json';
import {routeKey,validSelection,routeSelected,focusCenter,ease,cameraChanged} from './interaction.mjs';

const vector=(lat,lon,r=1)=>new THREE.Vector3(Math.cos(lat*Math.PI/180)*Math.cos(lon*Math.PI/180)*r,Math.sin(lat*Math.PI/180)*r,-Math.cos(lat*Math.PI/180)*Math.sin(lon*Math.PI/180)*r);
const shaderVertex=`varying vec3 n;varying vec3 v;void main(){vec4 p=modelViewMatrix*vec4(position,1.);n=normalize(normalMatrix*normal);v=normalize(-p.xyz);gl_Position=projectionMatrix*p;}`;

class NightGlobe {
 constructor(root,data,send){
  this.send=send;
  this.root=root;this.disposed=false;this.resources=[];this.labels=[];this.frame=0;this.last=0;this.reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  root.innerHTML='<div class="night-labels"></div><div class="night-status">MATERIAL SUPPLY NETWORK</div><div class="night-toolbar"><button aria-label="지구본 확대" title="확대">＋</button><button aria-label="지구본 축소" title="축소">−</button><button aria-label="지구본 시점 복귀" title="시점 복귀">↺</button><button aria-label="지도 선택 해제" title="선택 해제">×</button></div><select class="night-route-choice" aria-label="지구본 경로 선택"></select><div class="night-hint">드래그 회전 · 기업/경로 클릭 → 설명 연동</div>';
  try{this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'low-power'});}catch(error){this.error('이 환경에서는 3D 그래픽을 시작할 수 없습니다. 아래 기본 지도 옵션을 사용하세요.');return;}
  this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.75));this.renderer.outputColorSpace=THREE.SRGBColorSpace;this.renderer.setClearColor(0x020812,0);root.prepend(this.renderer.domElement);
  this.scene=new THREE.Scene();this.camera=new THREE.PerspectiveCamera(40,1,.1,30);this.home();
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;this.controls.enablePan=false;this.controls.minDistance=1.65;this.controls.maxDistance=4.6;this.controls.enableZoom=false;this.controls.rotateSpeed=.5;
  this.buttons=[...root.querySelectorAll('button')];this.actions=[()=>this.zoom(.86),()=>this.zoom(1.16),()=>this.home(true),()=>this.pick('clear',null)];this.buttons.forEach((b,i)=>b.addEventListener('click',this.actions[i]));
  this.routeChoice=root.querySelector('.night-route-choice');this.routeChange=()=>this.pick(this.routeChoice.value?'route':'clear',this.routeChoice.value||null);this.routeChoice.addEventListener('change',this.routeChange);
  this.stopFlight=()=>{this.flight=null;};this.controls.addEventListener('start',this.stopFlight);
  this.pointerDown=e=>{if(e.button===0)this.press={x:e.clientX,y:e.clientY};};
  this.pointerUp=e=>{const press=this.press;this.press=null;if(!press||Math.hypot(e.clientX-press.x,e.clientY-press.y)>6)return;
    const rect=this.renderer.domElement.getBoundingClientRect();const mouse=new THREE.Vector2((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);const ray=new THREE.Raycaster();ray.setFromCamera(mouse,this.camera);
    const eye=this.camera.position.clone().normalize();const hits=ray.intersectObjects(this.pickables||[],false).filter(h=>h.point.clone().normalize().dot(eye)>.35);
    const hit=hits.find(h=>h.object.userData.pick.kind==='marker')||hits[0];if(hit)this.pick(hit.object.userData.pick.kind,hit.object.userData.pick.id);
  };
  this.renderer.domElement.addEventListener('pointerdown',this.pointerDown);this.renderer.domElement.addEventListener('pointerup',this.pointerUp);
  this.scene.add(new THREE.AmbientLight(0x9cbdec,2));const sun=new THREE.DirectionalLight(0xa7caff,2);sun.position.set(-3,4,4);this.scene.add(sun);
  const loader=new THREE.TextureLoader();this.textures=[nightUrl,dayUrl,topologyUrl].map(url=>{const t=loader.load(url,()=>{},undefined,()=>this.error('지구 텍스처를 불러오지 못했습니다. 기본 지도를 사용할 수 있습니다.'));t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=Math.min(8,this.renderer.capabilities.getMaxAnisotropy());return t;});
  const material=new THREE.MeshPhongMaterial({map:this.textures[0],color:0x526b8c,emissive:0xffffff,emissiveMap:this.textures[0],emissiveIntensity:3.2,bumpMap:this.textures[2],bumpScale:.006,shininess:8,specular:0x12385e});
  this.scene.add(this.mesh(new THREE.SphereGeometry(1,128,96),material));
  // Outer atmosphere: Fresnel shell, modest opacity keeps coastlines readable.
  const atmosphere=new THREE.ShaderMaterial({vertexShader:shaderVertex,fragmentShader:`varying vec3 n;varying vec3 v;void main(){float f=pow(1.-abs(dot(normalize(n),normalize(v))),3.5);gl_FragColor=vec4(.17,.48,1.,f*.64);}`,transparent:true,depthWrite:false,side:THREE.FrontSide,blending:THREE.AdditiveBlending});
  const shell=this.mesh(new THREE.SphereGeometry(1.025,96,64),atmosphere);this.scene.add(shell);
  const positions=[];for(const line of boundaries){for(let i=1;i<line.length;i++){for(const p of [line[i-1],line[i]]){const v=vector(p[1],p[0],1.0017);positions.push(v.x,v.y,v.z);}}}
  const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));this.scene.add(new THREE.LineSegments(geo,new THREE.LineBasicMaterial({color:0x5b8aaf,transparent:true,opacity:.28})));this.resources.push(geo);
  this.group=new THREE.Group();this.scene.add(this.group);this.update(data);
  this.resize=()=>{const w=root.clientWidth,h=root.clientHeight;this.camera.aspect=w/h;this.camera.updateProjectionMatrix();this.renderer.setSize(w,h);};this.observer=new ResizeObserver(this.resize);this.observer.observe(root);this.resize();
  this.contextLost=e=>{e.preventDefault();this.error('3D 그래픽 연결이 끊겼습니다. 새로고침하거나 기본 지도를 사용하세요.');};this.renderer.domElement.addEventListener('webglcontextlost',this.contextLost);
  this.visibility=()=>{if(!document.hidden&&!this.frame)this.frame=requestAnimationFrame(t=>this.animate(t));};document.addEventListener('visibilitychange',this.visibility);this.frame=requestAnimationFrame(t=>this.animate(t));
 }
 mesh(geo,mat){this.resources.push(geo,mat);return new THREE.Mesh(geo,mat);}
 error(text){if(!this.root.querySelector('.night-error')){const el=document.createElement('div');el.className='night-error';el.textContent=text;this.root.append(el);}}
 home(animate=false){const target=this.data?(this.data.camera_focus||focusCenter(this.data.markers)):{lat:29,lon:120,distance:2.18};if(animate)this.flyTo(target);else{this.flight=null;this.camera?.position.copy(vector(target.lat,target.lon,target.distance));this.camera?.lookAt(0,0,0);this.controls?.update();}}
 flyTo(target){const destination=vector(target.lat,target.lon,target.distance);if(this.reduced){this.camera.position.copy(destination);this.controls.update();return;}this.flight={start:performance.now(),from:this.camera.position.clone(),to:destination};}
 zoom(f){this.flight=null;const length=THREE.MathUtils.clamp(this.camera.position.length()*f,1.65,4.6);this.camera.position.setLength(length);this.controls.update();}
 pick(kind,id){const event=validSelection(this.data,{kind,id,context:this.data.context});if(!event)return;const prior=this.data.selected;if(kind!=='clear'&&prior?.kind===kind&&prior?.id===id)return;this.data.selected=kind==='clear'?null:event;this.highlight();this.send?.('picked',event);}
 highlight(){const selected=this.data.selected;for(const item of this.routeMeshes||[]){const active=routeSelected(item.route,selected);item.mesh.material.opacity=item.opacity*(!selected||active?1:.18);}for(const item of this.markerGroups||[]){let active=!selected||selected.kind==='marker'&&selected.id===item.id;if(selected?.kind==='route'){const route=this.data.routes.find(r=>routeKey(r)===selected.id);active=!!route&&(route.start===item.id||route.end===item.id);}item.group.scale.setScalar(active&&selected?1.25:1);item.label.classList.toggle('night-selected',!!selected&&active);}this.routeChoice.value=selected?.kind==='route'?selected.id:'';}
 clear(){if(!this.group)return;this.group.traverse(o=>{o.geometry?.dispose();if(o.material){o.material.map?.dispose();o.material.dispose();}});this.group.clear();this.root.querySelector('.night-labels').replaceChildren();this.labels=[];this.pulses=[];this.particles=[];this.pickables=[];this.routeMeshes=[];this.markerGroups=[];}
 label(name,position,country=false){const container=this.root.querySelector('.night-labels');const el=document.createElement('div');el.className='night-label'+(country?' night-country':'');el.textContent=name;container.append(el);let leader=null;if(!country){let svg=container.querySelector('svg');if(!svg){svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('width','100%');svg.setAttribute('height','100%');svg.style.cssText='position:absolute;inset:0;pointer-events:none';container.prepend(svg);}leader=document.createElementNS('http://www.w3.org/2000/svg','line');leader.setAttribute('stroke-width','1');leader.setAttribute('stroke-opacity','.65');svg.append(leader);}this.labels.push({el,position,country,leader});return el;}
 update(data){const changed=cameraChanged(this.data,data);this.data=data;if(!this.group)return;this.clear();const lookup=new Map(data.markers.map(m=>[m.id,m]));const color=data.applied?0xffad49:0x4bdce9;
  this.root.querySelector('.night-status').textContent=data.status_label|| (data.comparison==='적용 전'?'적용 전 비교 · 등록 공급 연결':data.comparison?'사건 적용 · 공급 연결과 검토 후보':data.review?'REVIEW · 공급 연결과 검토 후보':'PREVIEW · 공급 연결');
  let summary=this.root.querySelector('.night-scenario');if(!summary){summary=document.createElement('div');summary.className='night-scenario';summary.setAttribute('role','status');this.root.append(summary);}summary.textContent=data.scenario_summary||'';summary.hidden=!data.scenario_summary;summary.classList.toggle('is-before',data.comparison==='적용 전');summary.classList.toggle('is-cost',!!data.tariff);summary.title=data.scenario_summary||'';
  this.routeChoice.replaceChildren();const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent='경로 선택 · 연결 설명 보기';this.routeChoice.append(placeholder);
  for(const route of data.routes){const option=document.createElement('option');option.value=routeKey(route);option.textContent=(route.status==='cost'?'관세·비용':route.status==='blocked'?'중단 가정':route.status==='restricted'?'공급 제한':route.kind==='primary'?'기존':route.kind==='detour'?'우회 후보':'대체 후보')+' · '+lookup.get(route.start)?.name+' → '+lookup.get(route.end)?.name;option.title=route.material||data.material||'';this.routeChoice.append(option);}
  for(const marker of data.markers){const port=marker.role==='blocked_port'||marker.role==='detour_port';const pos=vector(marker.lat,marker.lon,1.01);const color=marker.impact==='origin'?0xff4057:marker.impact==='cost'?0xffd166:marker.impact==='exposed'?0xffad49:marker.role==='detour_port'?0x68adff:marker.role==='alternative'?0x4fe4db:0x4bdce9;const group=new THREE.Group();group.position.copy(pos);group.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),pos.clone().normalize());
   if(marker.impact==='origin'){
    for(const [radius,opacity] of [[.13,.035],[.09,.07],[.05,.13]]){const area=new THREE.Mesh(new THREE.SphereGeometry(1.004,48,12,0,Math.PI*2,0,radius),new THREE.MeshBasicMaterial({color:0xff294b,transparent:true,opacity,depthWrite:false,blending:THREE.AdditiveBlending}));area.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),pos.clone().normalize());this.group.add(area);}
   }
   const halo=new THREE.Mesh(new THREE.RingGeometry(.018,.027,48),new THREE.MeshBasicMaterial({color,transparent:true,opacity:.95,side:THREE.DoubleSide,depthWrite:false}));group.add(halo);
   const core=new THREE.Mesh(marker.role==='alternative'||port?new THREE.CircleGeometry(.018,4):new THREE.CircleGeometry(.012,32),new THREE.MeshBasicMaterial({color:0xffffff,side:THREE.DoubleSide}));core.position.z=.001;if(port)core.rotation.z=Math.PI/4;group.add(core);
   core.userData.pick={kind:'marker',id:marker.id};this.pickables.push(core);
   const pulse=new THREE.Mesh(new THREE.RingGeometry(.022,.027,48),new THREE.MeshBasicMaterial({color,transparent:true,opacity:.5,side:THREE.DoubleSide,depthWrite:false}));group.add(pulse);this.pulses.push(pulse);
   // Wide soft halo is built from concentric transparent rings, no heavy bloom pass.
   for(let j=1;j<=5;j++)group.add(new THREE.Mesh(new THREE.RingGeometry(.024+j*.004,.03+j*.004,48),new THREE.MeshBasicMaterial({color,transparent:true,opacity:.05,side:THREE.DoubleSide,depthWrite:false,blending:THREE.AdditiveBlending})));
   this.group.add(group);const prefix=port?'□ ':marker.role==='alternative'?'◇ ':marker.role==='recipient'?'○ ':'● ';const label=this.label(prefix+marker.name,pos.clone().multiplyScalar(1.005));label.style.color='#'+new THREE.Color(color).getHexString();
   const badge=document.createElement('small');badge.textContent=marker.role_label|| (marker.impact==='origin'?'사건 발생 · 가정':marker.impact==='cost'?'관세·비용 영향':marker.impact==='exposed'?'영향 검토'+(marker.process_label?' · '+marker.process_label:''):marker.role==='blocked_port'?'기존 경유 · 가정':marker.role==='detour_port'?'우회 검토 후보':marker.role==='alternative'?'대체 검토 후보':marker.role==='recipient'?'수요기업'+(marker.process_label?' · '+marker.process_label:''):'원래 공급');label.append(badge);label.title=marker.site+' · '+(data.material||'')+(marker.processes?.length?' · '+marker.processes.join(' · '):'')+(marker.score==null?'':` · 소재 충족도 ${marker.score.toFixed(1)}%`);
   label.setAttribute('role','button');label.setAttribute('tabindex','0');label.setAttribute('aria-label',marker.name+' 선택');label.onclick=e=>{e.stopPropagation();this.pick('marker',marker.id);};label.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();this.pick('marker',marker.id);}};this.markerGroups.push({id:marker.id,group,label});
  }
  for(const route of data.routes){const a=lookup.get(route.start),b=lookup.get(route.end);if(!a||!b)continue;const start=vector(a.lat,a.lon),end=vector(b.lat,b.lon);const points=[];for(let i=0;i<=64;i++){const t=i/64;const p=start.clone().lerp(end,t).normalize().multiplyScalar(1.012+.055*Math.sin(Math.PI*t));points.push(p);}
   const curve=new THREE.CatmullRomCurve3(points);const alternative=route.kind==='alternative'||route.kind==='detour';const routeColor=route.status==='cost'?0xffd166:route.status==='blocked'||route.status==='restricted'?0xff4057:route.kind==='detour'?0x68adff:alternative?0x4fe4db:color;
   const dashed=alternative||route.status==='blocked';const curves=dashed?Array.from({length:12},(_,j)=>new THREE.CatmullRomCurve3(Array.from({length:6},(_,i)=>curve.getPoint((j+i*.65/5)/12)))):[curve];
   if(route.status==='blocked'){const badge=this.label(route.disruption_label||'× 중단 가정',curve.getPoint(.5));badge.classList.add('night-disruption');}
   for(const part of curves)for(const [radius,opacity] of (alternative?[[.006,.13],[.0024,1]]:[[.010,.055],[.005,.13],[.0017,1]])){const mesh=new THREE.Mesh(new THREE.TubeGeometry(part,alternative?8:100,radius,5,false),new THREE.MeshBasicMaterial({color:routeColor,transparent:true,opacity,depthWrite:false,blending:THREE.AdditiveBlending}));mesh.userData.pick={kind:'route',id:routeKey(route)};this.group.add(mesh);this.pickables.push(mesh);this.routeMeshes.push({route,mesh,opacity});}
   if(!data.review){const particle=new THREE.Mesh(new THREE.SphereGeometry(.006,10,8),new THREE.MeshBasicMaterial({color:0xfff7d9}));this.group.add(particle);this.particles.push({particle,curve});}
  }
  for(const [name,lat,lon] of [['중국',33,107],['한국',36,127],['대만',23.5,120],['일본',39,141]])this.label(name,vector(lat,lon,1.008),true);
  if(changed){this.revealStart=performance.now();if(data.applied)this.flyTo(data.camera_focus||focusCenter(data.markers));else this.home();}this.highlight();
 }
 animate(time){this.frame=0;if(this.disposed||document.hidden)return;this.frame=requestAnimationFrame(t=>this.animate(t));if(time-this.last<32)return;this.last=time;if(this.flight){const p=ease((time-this.flight.start)/900);this.camera.position.lerpVectors(this.flight.from,this.flight.to,p);if(p>=1)this.flight=null;}this.controls.update();
  for(const item of this.routeMeshes){const p=this.reduced?1:Math.min(1,Math.max(0,(time-this.revealStart)/700));const total=item.mesh.geometry.index.count;item.mesh.geometry.setDrawRange(0,Math.floor(total*p/6)*6);}
  if(!this.reduced){this.pulses.forEach((p,i)=>{const phase=(time/2200+i*.3)%1;p.scale.setScalar(1+phase*1.8);p.material.opacity=(1-phase)*.4;});this.particles.forEach((p,i)=>p.particle.position.copy(p.curve.getPoint((time/4500+i*.3)%1)));}else this.particles.forEach(p=>p.particle.position.copy(p.curve.getPoint(.5)));
  const eye=this.camera.position.clone().normalize();const occupied=[];const width=this.root.clientWidth,height=this.root.clientHeight;
  for(const {el,position,country,leader} of this.labels){const projected=position.clone().project(this.camera);const visible=position.clone().normalize().dot(eye)>.35&&Math.abs(projected.x)<1&&Math.abs(projected.y)<1;el.style.display=visible?'block':'none';if(leader)leader.style.display='none';if(!visible)continue;
   const x=(projected.x*.5+.5)*width,y=(-projected.y*.5+.5)*height;el.style.left=x+'px';el.style.top=y+'px';el.style.marginTop='0';
   const w=el.offsetWidth,h=el.offsetHeight;const overlap=r=>occupied.some(o=>r.x<o.x+o.w+4&&r.x+r.w+4>o.x&&r.y<o.y+o.h+4&&r.y+r.h+4>o.y);
   if(country){const r={x:x-w/2,y:y-h/2,w,h};if(overlap(r))el.style.display='none';}
   else {let offset=0;for(const candidate of [0,-(h+8),h+8,-2*(h+8),2*(h+8)]){const r={x:x+14,y:y-h/2+candidate,w,h};if(r.y>6&&r.y+h<height-24&&!overlap(r)){offset=candidate;break;}}el.style.marginTop=offset+'px';occupied.push({x:x+14,y:y-h/2+offset,w,h});if(leader&&offset){leader.style.display='block';for(const [k,v] of Object.entries({x1:x,y1:y,x2:x+14,y2:y+offset,stroke:el.style.color||'#a5bcd2'}))leader.setAttribute(k,v);}}
  }
  this.renderer.render(this.scene,this.camera);
 }
 dispose(){this.disposed=true;cancelAnimationFrame(this.frame);this.observer?.disconnect();document.removeEventListener('visibilitychange',this.visibility);this.controls?.removeEventListener('start',this.stopFlight);this.controls?.dispose();this.clear();this.scene?.traverse(o=>{o.geometry?.dispose();o.material?.dispose();});this.textures?.forEach(t=>t.dispose());this.renderer?.domElement.removeEventListener('webglcontextlost',this.contextLost);this.renderer?.domElement.removeEventListener('pointerdown',this.pointerDown);this.renderer?.domElement.removeEventListener('pointerup',this.pointerUp);this.routeChoice?.removeEventListener('change',this.routeChange);this.renderer?.dispose();this.renderer?.forceContextLoss();this.buttons?.forEach((b,i)=>b.removeEventListener('click',this.actions[i]));}
}

export default function render({parentElement,data,setTriggerValue}){const root=parentElement.querySelector('.night-root');if(root.__globe){clearTimeout(root.__timer);root.__globe.send=setTriggerValue;root.__globe.update(data);}else root.__globe=new NightGlobe(root,data,setTriggerValue);return()=>{root.__timer=setTimeout(()=>{if(!root.isConnected){root.__globe?.dispose();delete root.__globe;}},150);};}
