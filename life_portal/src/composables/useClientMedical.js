import { onBeforeUnmount,ref } from 'vue';
import { createClientInfoReader } from '../api/client-info';

// Mounted only while the Medical tab is visible. Completed results are cached
// on this profile, so returning to the tab needs no further reads.
export function useClientMedical(bundle) {
  const data=ref(bundle.lazy.medical||null),loading=ref(false),error=ref('');
  let controller,active=true;
  async function load(){
    controller?.abort();controller=new AbortController();const current=controller;
    const reader=createClientInfoReader(current.signal);loading.value=true;error.value='';
    try{
      const [vitals,enc]=await Promise.all([
        reader.list('Vital Signs',[['patient','=',bundle.pid],['docstatus','!=',2]],['name','signs_date','height','weight','bmi','bp','pulse','temperature','nutrition_note'],100,'signs_date desc'),
        reader.list('Patient Encounter',[['patient','=',bundle.pid],['docstatus','!=',2]],['name','encounter_date','practitioner_name','medical_department','encounter_comment'],100,'encounter_date desc'),
      ]);
      if(active&&controller===current&&!current.signal.aborted){data.value={vitals,enc};bundle.lazy.medical=data.value;}
    }catch(cause){if(active&&controller===current&&!current.signal.aborted){error.value=cause.message;current.abort();}}
    finally{if(active&&controller===current)loading.value=false;}
  }
  if(!data.value)load();
  onBeforeUnmount(()=>{active=false;controller?.abort();});
  return{data,loading,error,load};
}
