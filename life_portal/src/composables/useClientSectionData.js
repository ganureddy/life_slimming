import {onBeforeUnmount,ref,watch} from 'vue';
import {createClientInfoReader} from '../api/client-info';

// Read state is scoped to this client/tab; failed or partial responses never
// become a cached empty history. Each tab exposes a retry control.
export function useClientSectionData(bundle,key,read,{immediate=true}={}){
 const data=ref(null),loading=ref(false),error=ref(''),warnings=ref([]);let controller,generation=0,active=true;
 async function load(force=false){
  const b=bundle();if(!b)return;const token=++generation;controller?.abort();controller=new AbortController();error.value='';warnings.value=[];
  if(!force&&b.lazy[key]){data.value=b.lazy[key];loading.value=false;return;}
  loading.value=true;
  try{const result=await read(createClientInfoReader(controller.signal),b);if(!active||token!==generation)return;data.value=result;warnings.value=result?.warnings||[];if(!warnings.value.length)b.lazy[key]=result;}
  catch(e){if(active&&token===generation&&e.name!=='AbortError'){data.value=null;error.value=e.message;}}
  finally{if(active&&token===generation)loading.value=false;}
 }
 if(immediate)watch(()=>bundle()?.pid,()=>{data.value=null;load();},{immediate:true});
 onBeforeUnmount(()=>{active=false;generation++;controller?.abort();});
 return {data,loading,error,warnings,load};
}
