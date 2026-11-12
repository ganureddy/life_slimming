import test from 'node:test';
import assert from 'node:assert/strict';
import { createReportLoader } from '../src/lib/cc-report-loader.js';
test('identical report requests share a network call and cached result', async () => {
 let calls=0, finish; const loader=createReportLoader(()=>{calls++;return new Promise(resolve=>finish=resolve);},()=>['a']);
 const a=loader({from:'2026-11-01',view:'calendar'}),b=loader({view:'calendar',from:'2026-11-01'});
 await Promise.resolve(); assert.equal(calls,1);finish({rows:[1]});assert.deepEqual(await a,await b);
 await loader({from:'2026-11-01',view:'calendar'});assert.equal(calls,1);
});
test('explicit refresh goes to server, failures can retry, login changes invalidate cache',async()=>{
 let calls=0,user='a'; const loader=createReportLoader(async()=>{calls++;if(calls===2)throw Error('offline');return {calls};},()=>[user]);
 await loader({});await assert.rejects(loader({},undefined,true),/offline/);await loader({},undefined,true);assert.equal(calls,3);
 user='b';await loader({});assert.equal(calls,4);
});
test('aborting one consumer does not cancel another consumer',async()=>{
 let finish; const loader=createReportLoader(()=>new Promise(resolve=>finish=resolve),()=>['a']);const controller=new AbortController();
 const first=loader({},controller.signal),second=loader({});await Promise.resolve();controller.abort();await assert.rejects(first,{name:'AbortError'});
 finish({ok:true});assert.deepEqual(await second,{ok:true});
});
test('expired cache fetches fresh data',async()=>{
 let calls=0;const loader=createReportLoader(async()=>++calls,()=>['a'],-1);await loader({});await loader({});assert.equal(calls,2);
});
