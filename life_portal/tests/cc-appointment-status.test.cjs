const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../src/components/cc/CCAppointmentStatus.vue'),'utf8').split('<script setup>')[1].split('</script>')[0].replace(/^import .*;\n/gm,'');
function setup(request) {
  let dispose;
  const state=vm.runInNewContext(source+'\n({loadOptions,options,optionsError,optionsLoading,save,status})',{
    request,AbortController,session:{user:'Administrator',roles:[],csrf_token:'fixture'},defineProps:()=>({lead:{name:'LEAD-1',custom_appointment_status:'Not Visited',modified:'fixture'}}),defineEmits:()=>()=>{},
    ref:value=>({value}),computed:fn=>({get value(){return fn();}}),watch(){},onBeforeUnmount:fn=>{dispose=fn;},
  });
  return{...state,dispose:()=>dispose()};
}
test('unexpected status metadata produces a recoverable field error, never a render-time non-array',async()=>{
  let response={message:{}};
  const s=setup(async()=>response);
  await s.loadOptions();assert(Array.isArray(s.options.value));assert.equal(s.options.value.length,0);assert(s.optionsError.value.includes('retry'));assert.equal(s.optionsLoading.value,false);
  response={message:['Not Visited','Visited Booked','Not Visited','']};await s.loadOptions();
  assert.deepEqual(Array.from(s.options.value),['Not Visited','Visited Booked']);assert.equal(s.optionsError.value,'');
});
test('status metadata aborts on navigation and cannot update an unmounted view',async()=>{
  let finish,signal;
  const s=setup((method,args)=>{signal=args.signal;return new Promise(resolve=>{finish=resolve;});});
  const pending=s.loadOptions();s.dispose();assert.equal(signal.aborted,true);finish({message:['Not Visited']});await pending;
  assert.equal(s.options.value.length,0);
});
test('invalid appointment status cannot submit a mutation',async()=>{
  let calls=0;const s=setup(async()=>{calls++;return{message:[]};});s.status.value='Invalid';await s.save();assert.equal(calls,0);
});
