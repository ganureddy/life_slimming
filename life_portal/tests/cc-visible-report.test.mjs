import test from 'node:test';
import assert from 'node:assert/strict';
import {ref,nextTick,effectScope} from 'vue';
import {watchVisibleReport} from '../src/lib/cc-visible-report.js';
const flush=async()=>{await nextTick();await Promise.resolve();await nextTick();};
test('hidden cached tabs do not read changed dates; activation loads once',async()=>{
 const scope=effectScope(),visible=ref(false),date=ref('2026-11-01');let calls=0,loaded=false;
 scope.run(()=>watchVisibleReport(()=>[date.value],()=>visible.value,async()=>{calls++;loaded=true;},()=>loaded));
 await flush();assert.equal(calls,0);date.value='2026-11-02';await flush();assert.equal(calls,0);
 visible.value=true;await flush();assert.equal(calls,1);visible.value=false;await flush();visible.value=true;await flush();assert.equal(calls,1);
 visible.value=false;date.value='2026-11-03';await flush();assert.equal(calls,1);visible.value=true;await flush();assert.equal(calls,2);scope.stop();
});
