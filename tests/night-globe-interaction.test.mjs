import test from 'node:test';
import assert from 'node:assert/strict';
import {focusCenter,validSelection,routeSelected,ease,cameraChanged} from '../night_globe/interaction.mjs';

test('comparison changes the frame while preserving the camera',()=>{
 const after={camera_context:'same-case',context:'after'};
 const before={camera_context:'same-case',context:'before'};
 assert.equal(cameraChanged(after,before),false);
 assert.equal(cameraChanged(after,{camera_context:'new-case',context:'new'}),true);
 assert.equal(cameraChanged(undefined,after),true);
});

test('camera focus uses spherical coordinates across the date line',()=>{
 const center=focusCenter([{lat:30,lon:179},{lat:30,lon:-179}]);
 assert.ok(Math.abs(center.lon)>179);assert.ok(center.lat>=30);
 const asia=focusCenter([{lat:35.6,lon:139.7},{lat:24.7,lon:121}]);
 assert.ok(asia.lon>121&&asia.lon<139.7);assert.ok(asia.lat>24.7&&asia.lat<35.6);
});
test('unknown and stale selections do not survive a new frame',()=>{
 const data={context:'new',markers:[{id:'jsr'}],routes:[{kind:'primary',start:'jsr',end:'tsmc'}]};
 assert.equal(validSelection(data,{context:'old',kind:'marker',id:'jsr'}),null);
 assert.equal(validSelection(data,{context:'new',kind:'marker',id:'hidden'}),null);
 assert.equal(validSelection(data,{context:'new',kind:'route',id:'alternative|dongjin|tsmc'}),null);
 assert.equal(validSelection(data,{context:'new',kind:'route',id:'primary|jsr|tsmc'}).kind,'route');
});
test('selected markers highlight only connected routes',()=>{
 const route={kind:'alternative',start:'dongjin',end:'tsmc'};
 assert.equal(routeSelected(route,{kind:'marker',id:'dongjin'}),true);
 assert.equal(routeSelected(route,{kind:'marker',id:'jsr'}),false);
 assert.equal(routeSelected(route,{kind:'route',id:'alternative|dongjin|tsmc'}),true);
});
test('camera easing remains bounded during interrupted transitions',()=>{
 assert.equal(ease(-1),0);assert.equal(ease(2),1);assert.equal(ease(.5),.5);
 assert.ok(Number.isFinite(focusCenter([]).lon));
});
