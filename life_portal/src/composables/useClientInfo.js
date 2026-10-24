import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { createClientInfoReader } from '../api/client-info';
import { CFG, analyze, buildClientList, clientListTotals, clientNetworkSummary, addDays, billingMonth, TODAY, cleanMobile, d10, isExcluded, lc, lookupRule, qRange } from '../lib/client-info';

const planFields = ['name','patient','patient_name','start_date','due_date','branch','custom_health_status','status','total_sessions','total_sessions_completed'];
const invoiceFields = ['name','patient','posting_date','due_date','base_grand_total','outstanding_amount','status','is_return','branch'];
const sessionFields = ['name','patient','start_date','creation','branch','therapy_plan','therapy_type','docstatus','start_time','duration','before_weight','after_weight','weight_loss','practitioner','custom_practitioner_name'];
const patientFields = ['name','patient_name','customer','mobile','sex','branch_name','custom_branch'];

export function useClientInfo() {
  const root=ref(null), from=ref(''),to=ref(''),quick=ref('today'),query=ref(''),branch=ref(''),status=ref(''),mode=ref(''),unpaid=ref(false),page=ref(1);
  const rows=ref([]),collections=ref([]),modes=ref([]),loading=ref(false),error=ref(''),collectionError=ref(''),modeError=ref(''),notice=ref('');
  const lookupRows=ref([]),lookupOpen=ref(false),lookupLoading=ref(false),lookupError=ref('');
  const profileId=ref(''),paymentsLoaded=ref(false);
  const drawer=ref(null),drawerFilter=ref('all'),modalOpen=ref(false),profile=ref(null),profileLoading=ref(false),profileError=ref(''),profileWarnings=ref([]),tab=ref('overview');
  const dashboard=ref(null),dashLoading=ref(false),dashError=ref(''),dashCollapsed=ref(false),dashUpdated=ref('');
  const payments=ref([]),paymentLoading=ref(false),paymentError=ref(''),photo=ref('');
  const controllers=new Map();let active=true,lookupTimer,previousOverflow,returnFocus,observer,dashVisible=false,dashRange='';let mainGeneration=0;
  const newScope=key=>{controllers.get(key)?.abort();const controller=new AbortController();controllers.set(key,controller);return{controller,reader:createClientInfoReader(controller.signal)};};
  const valid=(key,controller)=>active&&controllers.get(key)===controller&&!controller.signal.aborted;
  const branches=computed(()=>[...new Set(rows.value.flatMap(row=>row.branches))].sort());
  const modeNames=computed(()=>[...new Set([...modes.value,...collections.value.map(row=>row.mode_of_payment)].filter(Boolean))].sort());
  const filtered=computed(()=>{
    const term=lc(query.value),digits=term.replace(/\D/g,''),parties=new Set(collections.value.filter(row=>lc(row.mode_of_payment)===lc(mode.value)).flatMap(row=>[lc(row.party),lc(row.party_name)]));
    return rows.value.filter(row=>(!branch.value||row.branches.some(value=>lc(value)===lc(branch.value)))&&(!status.value||row.status===status.value)&&(!unpaid.value||row.pending>0)
      &&(!mode.value||[row.customer,row.id,row.name].some(value=>parties.has(lc(value))))&&(!term||(digits.length>=3&&digits===term)||lc(row.name).includes(term)));
  });
  const pages=computed(()=>Math.max(1,Math.ceil(filtered.value.length/CFG.PAGE_SIZE)));
  const visible=computed(()=>filtered.value.slice((page.value-1)*CFG.PAGE_SIZE,page.value*CFG.PAGE_SIZE));
  const totals=computed(()=>clientListTotals(filtered.value,collections.value,branch.value,mode.value));
  const metrics=computed(()=>profile.value?analyze(profile.value):null);
  watch([query,branch,status,mode,unpaid],()=>{page.value=1;});
  watch(pages,count=>{page.value=Math.min(page.value,count);});
  async function loadModes(){const {controller,reader}=newScope('modes');modeError.value='';try{const records=await reader.list('Mode of Payment',[],['name','enabled'],500,'name asc');if(valid('modes',controller))modes.value=records.filter(row=>row.enabled==null||Number(row.enabled)!==0).map(row=>row.name);}catch(cause){if(valid('modes',controller))modeError.value=cause.message;}}
  async function loadMain(){
    if(from.value&&to.value&&from.value>to.value){error.value='From date cannot be after To date.';return;}
    const generation=++mainGeneration;controllers.get('selected')?.abort();
    const {controller,reader}=newScope('list'),start=from.value,end=to.value;loading.value=true;error.value='';collectionError.value='';notice.value='';unpaid.value=false;
    const planFilters=[];if(start)planFilters.push(['start_date','>=',start]);if(end)planFilters.push(['start_date','<=',end]);
    const paymentFilters=[['docstatus','=',1],['payment_type','=','Receive']];if(start)paymentFilters.push(['posting_date','>=',start]);if(end)paymentFilters.push(['posting_date','<=',end]);
    try{
      const plans=await reader.list('Therapy Plan',planFilters,planFields,20000,'start_date desc');
      if(!valid('list',controller))return;
      const ids=[...new Set(plans.filter(plan=>plan.patient&&!isExcluded(plan.branch)).map(plan=>plan.patient))];
      const [invoices,sessions,patients,received]=await Promise.all([
        reader.chunks(ids,chunk=>reader.list('Sales Invoice',[['patient','in',chunk],['docstatus','=',1]],invoiceFields,10000)),
        reader.chunks(ids,chunk=>reader.list('Therapy Session',[['patient','in',chunk],['docstatus','!=',2]],sessionFields,20000)),
        reader.chunks(ids,chunk=>reader.list('Patient',[['name','in',chunk]],patientFields,1000)),
        reader.list('Payment Entry',paymentFilters,['name','posting_date','mode_of_payment','party','party_name','branch','base_received_amount','received_amount','paid_amount'],50000)
          .catch(cause=>{if(valid('list',controller))collectionError.value=cause.message;return[];}),
      ]);
      if(!valid('list',controller))return;
      rows.value=buildClientList(plans,invoices,sessions,patients,start,end);collections.value=received.filter(row=>!isExcluded(row.branch));page.value=1;
      if(dashVisible&&!dashCollapsed.value)loadDashboard();
    }catch(cause){if(valid('list',controller)){error.value=cause.message;rows.value=[];collections.value=[];controller.abort();}}
    finally{if(active&&generation===mainGeneration)loading.value=false;}
  }
  async function loadDashboard(force=false){
    const range=from.value+'|'+to.value;if(!force&&dashRange===range&&(dashLoading.value||dashboard.value))return;
    dashRange=range;const {controller,reader}=newScope('dashboard');dashLoading.value=true;dashError.value='';
    const now=new Date(),year=(now.getMonth()>=3?now.getFullYear():now.getFullYear()-1)+'-04-01',start=[year,from.value||billingMonth(0)[0],addDays(TODAY(),-90)].sort()[0];
    const dates={from:from.value,to:to.value};
    try{const[plans,sessions]=await Promise.all([reader.list('Therapy Plan',[],['patient','status','branch'],60000),reader.list('Therapy Session',[['start_date','>=',start],['start_date','<=',TODAY()],['docstatus','!=',2]],['patient','start_date','branch'],80000)]);
      if(valid('dashboard',controller)){dashboard.value=clientNetworkSummary(plans,sessions,dates.from,dates.to);dashUpdated.value='Updated '+new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});}
    }catch(cause){if(valid('dashboard',controller)){dashError.value=cause.message;dashRange='';controller.abort();}}
    finally{if(active&&controllers.get('dashboard')===controller)dashLoading.value=false;}
  }
  function toggleDashboard(){dashCollapsed.value=!dashCollapsed.value;if(!dashCollapsed.value){dashVisible=true;loadDashboard();}}
  function preset(key){quick.value=key;[from.value,to.value]=qRange(key).map(value=>value||'');loadMain();}
  function clear(){query.value=branch.value=status.value=mode.value='';unpaid.value=false;lookupOpen.value=false;preset('today');}
  function searchChanged(){
    clearTimeout(lookupTimer);controllers.get('lookup')?.abort();lookupRows.value=[];lookupError.value='';
    const rule=lookupRule(query.value);lookupOpen.value=rule.ok;lookupLoading.value=rule.ok;
    if(!rule.ok)return;
    lookupTimer=setTimeout(async()=>{const {controller,reader}=newScope('lookup');try{
      const result=await reader.lookup({action:'search',q:rule.q});
      if(!valid('lookup',controller))return;
      if(!Array.isArray(result.rows))throw new Error('Client search returned an invalid response.');
      lookupRows.value=result.rows;
    }catch(cause){if(valid('lookup',controller))lookupError.value=cause.message;}
    finally{if(valid('lookup',controller))lookupLoading.value=false;}},250);
  }
  async function selectLookup(patient){
    lookupOpen.value=false;controllers.get('lookup')?.abort();clearTimeout(lookupTimer);
    const generation=++mainGeneration;controllers.get('list')?.abort();
    const {controller,reader}=newScope('selected');loading.value=true;error.value='';
    try{
      const result=await reader.lookup({action:'row',patient:patient.name});
      if(!valid('selected',controller))return;
      if(!result.patient)throw new Error('The selected client history is unavailable.');
      const [row]=buildClientList(result.plans||[],result.invoices||[],result.sessions||[],[result.patient],'','',true);
      if(!row)throw new Error('The selected client history is unavailable.');
      rows.value=[...rows.value.filter(value=>value.id!==row.id),row];query.value=row.name;page.value=1;
      notice.value=`Full history for ${row.name} — search can show this client outside the selected plan-start date range.`;
    }catch(cause){if(valid('selected',controller))error.value=cause.message;}
    finally{if(active&&generation===mainGeneration)loading.value=false;}
  }
  function openDrawer(row,event){returnFocus=event?.currentTarget;drawer.value=row;drawerFilter.value='all';lookupOpen.value=false;}
  function closeDrawer(){drawer.value=null;returnFocus?.focus();}
  async function openProfile(id,event){
    closeDrawer();returnFocus=event?.currentTarget||returnFocus;lookupOpen.value=false;modalOpen.value=true;profileId.value=id;paymentsLoaded.value=false;tab.value='overview';profile.value=null;photo.value='';profileWarnings.value=[];
    profileError.value='';profileLoading.value=true;payments.value=[];paymentError.value='';paymentLoading.value=false;
    controllers.get('profile-extra')?.abort();controllers.get('payments')?.abort();
    const {controller,reader}=newScope('profile');
    try{
      const [patient,plans,sessions,invoices,appts,followups]=await Promise.all([
        reader.doc('Patient',id),reader.list('Therapy Plan',[['patient','=',id]],[...planFields,'owner','creation','consultant_name','custom_employee_name','category'],500,'start_date desc'),
        reader.list('Therapy Session',[['patient','=',id],['docstatus','!=',2]],sessionFields,5000,'start_date desc'),
        reader.list('Sales Invoice',[['patient','=',id],['docstatus','=',1]],[...invoiceFields,'owner','remarks','custom_therapy_plan','custom_referring_name','ref_practitioner'],2000,'posting_date desc'),
        reader.list('Patient Appointment',[['patient','=',id]],['name','appointment_date','appointment_time','appointment_type','call_back_status','status','practitioner','practitioner_name','department','branch','concern','service_room','service_unit','therapy_type1','therapy_type','therapy_plan_1','therapy_plan'],2000,'appointment_date desc'),
        reader.list('Client Followup',[['client','=',id]],['*'],2000,'creation desc'),
      ]);
      if(!valid('profile',controller)||!modalOpen.value)return;
      if(!patient?.name)throw new Error('The Patient record could not be read.');
      profile.value={pid:id,patient,plans:plans.filter(row=>!isExcluded(row.branch)),sessions:sessions.filter(row=>!isExcluded(row.branch)),invoices:invoices.filter(row=>!isExcluded(row.branch)),appts:appts.filter(row=>!isExcluded(row.branch)),followups:followups.filter(row=>!isExcluded(row.branch)),users:{},transfers:[],lazy:{}};
      photo.value=patient.image||patient.custom_client_photo||'';
      enrichProfile(id);
    }catch(cause){if(valid('profile',controller)){profileError.value=cause.message;controller.abort();}}
    finally{if(active&&controllers.get('profile')===controller)profileLoading.value=false;}
  }
  async function enrichProfile(id){
    const {controller,reader}=newScope('profile-extra'),bundle=profile.value;
    const warn=cause=>{if(valid('profile-extra',controller))profileWarnings.value.push(cause.message);};
    const owners=[...new Set([...bundle.plans,...bundle.invoices].map(row=>row.owner).filter(Boolean))];
    const tasks=[reader.pool(bundle.plans,plan=>reader.doc('Therapy Plan',plan.name)).then(docs=>{if(valid('profile-extra',controller)&&profile.value?.pid===id)profile.value={...profile.value,plans:bundle.plans.map((plan,index)=>({...plan,...docs[index]}))};}).catch(warn),
      owners.length?reader.list('User',[['name','in',owners]],['name','full_name'],200).then(users=>{if(valid('profile-extra',controller)&&profile.value?.pid===id)profile.value={...profile.value,users:Object.fromEntries(users.map(row=>[row.name,row.full_name]))};}).catch(warn):Promise.resolve(),
      reader.list('Zero Session',[['patient','=',id],['status','=','Completed']],['name','patient','status','session_date','creation','modified'],25,'modified desc').then(async rows=>{for(const row of rows){const doc=await reader.doc('Zero Session',row.name);if(!valid('profile-extra',controller))return;if(doc?.client_photo){photo.value=doc.client_photo;return;}}}).catch(warn),
    ];
    await Promise.all(tasks);
  }
  async function loadPayments(force=false){
    if(!profile.value||(!force&&(paymentsLoaded.value||paymentLoading.value)))return;const bundle=profile.value,{controller,reader}=newScope('payments');paymentLoading.value=true;paymentError.value='';
    const fields=['name','posting_date','mode_of_payment','party','party_name','branch','base_received_amount','received_amount','paid_amount'];
    try{
      let received=bundle.patient.customer?await reader.list('Payment Entry',[['party','=',bundle.patient.customer],['docstatus','=',1],['payment_type','=','Receive']],fields,2000,'posting_date desc'):[];
      if(!received.length&&bundle.patient.patient_name)received=await reader.list('Payment Entry',[['party_name','=',bundle.patient.patient_name],['docstatus','=',1],['payment_type','=','Receive']],fields,2000,'posting_date desc');
      if(valid('payments',controller)&&profile.value?.pid===bundle.pid){payments.value=received.filter(row=>!isExcluded(row.branch));paymentsLoaded.value=true;}
    }catch(cause){if(valid('payments',controller))paymentError.value=cause.message;}
    finally{if(active&&controllers.get('payments')===controller)paymentLoading.value=false;}
  }
  watch(tab,value=>{if(value==='billing')loadPayments();});
  function closeProfile(){controllers.get('profile')?.abort();controllers.get('profile-extra')?.abort();controllers.get('payments')?.abort();modalOpen.value=false;profile.value=null;returnFocus?.focus();}
  watch(modalOpen,async open=>{if(open){previousOverflow=document.body.style.overflow;document.body.style.overflow='hidden';await nextTick();root.value?.querySelector('#c3ModalClose')?.focus();}else document.body.style.overflow=previousOverflow??'';});
  function onKey(event){if(event.key==='Escape'){if(modalOpen.value)closeProfile();else if(drawer.value)closeDrawer();else lookupOpen.value=false;}}
  function exportCsv(){
    const headers=['Client','Mobile','Status','Growth','Joined','Last session','Visits','Paid','Pending','Medical','Branches'];
    const records=filtered.value.map(row=>[row.name,row.mobile?`${row.mobile.slice(0,3)}****${row.mobile.slice(-3)}`:'',row.status,row.growth.l,row.joined,row.last,row.visits,row.paid,row.pending,row.medical,row.branches.join(', ')]);
    const cell=value=>'"'+String(value??'').replaceAll('"','""')+'"';
    const blob=new Blob(['\ufeff'+[headers,...records].map(row=>row.map(cell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='LIFE_Clients.csv';link.click();URL.revokeObjectURL(url);
  }
  onMounted(()=>{loadModes();preset('today');window.addEventListener('keydown',onKey);
    if(typeof IntersectionObserver!=='undefined'){observer=new IntersectionObserver(entries=>{if(entries.some(entry=>entry.isIntersecting)){dashVisible=true;if(!dashCollapsed.value)loadDashboard();}},{rootMargin:'100px'});const element=root.value?.querySelector('#c3Dash');if(element)observer.observe(element);}
  });
  onBeforeUnmount(()=>{active=false;observer?.disconnect();controllers.forEach(controller=>controller.abort());clearTimeout(lookupTimer);window.removeEventListener('keydown',onKey);if(modalOpen.value)document.body.style.overflow=previousOverflow??'';});
  return{root,from,to,quick,query,branch,status,mode,unpaid,page,branches,modeNames,filtered,visible,pages,totals,loading,error,collectionError,modeError,notice,
    lookupRows,lookupOpen,lookupLoading,lookupError,drawer,drawerFilter,modalOpen,profileId,profile,metrics,profileLoading,profileError,profileWarnings,tab,payments,paymentLoading,paymentError,photo,
    dashboard,dashLoading,dashError,dashCollapsed,dashUpdated,loadDashboard,toggleDashboard,loadModes,loadMain,preset,clear,searchChanged,selectLookup,openDrawer,closeDrawer,openProfile,closeProfile,loadPayments,exportCsv};
}
