<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import { dataApi } from '../api';
import { request } from '../api/http';
import { session } from '../lib/session';

import RecoveryCalendar from '../components/pending-balances/RecoveryCalendar.vue';
import RecoverySourceTable from '../components/pending-balances/RecoverySourceTable.vue';
import RecoveryClientCell from '../components/pending-balances/RecoveryClientCell.vue';
import { useRecoveryClients } from '../composables/useRecoveryClients';
import { useRecoveryLayout } from '../composables/useRecoveryLayout';
import { recoveryTotals, recoveryNumber, maskRecoveryMobile, recoveryCsvCell, sortRecoveryRows, recoveryManagerSortKeys } from '../lib/recovery-domain';

const clientInfo=useRecoveryClients();
const {details:clientDetails,status:enrichmentStatus}=clientInfo;
const {root,order:panelOrder,collapsed,hidden,announcement,printTarget,active:activeSection,click:layoutClick}=useRecoveryLayout();
const clientSearch=ref(''),toastMessage=ref('');let toastTimer;
const pageSize=15;
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;};
const rows=ref([]),branches=ref([]),loading=ref(false),error=ref(''),notice=ref(''),page=ref(1),sortKey=ref('due'),sortDir=ref('desc'),mode=ref('HO');
const branch=ref(''),employee=ref(''),status=ref(''),age=ref(''),from=ref(''),to=ref(''),minDue=ref(''),search=ref(''),saving=ref({});
const statuses=[['PENDING','- Not yet updated -'],['COLLECTED','Already collected (full)'],['COMMITTED','Yes, this can be collected'],['NOTCOLL','This will not be collectable'],['DISPUTE','Client dispute / on hold']];
const reasons=['Client not reachable / number invalid','Client refused to pay','Service discontinued by client','Duplicate or wrong billing entry','Discount agreed but not adjusted','Refund / package cancelled case','Client shifted city / not traceable','Legal or medical complaint case','Other (explain in remark)'];
const modes=['Cash','UPI','Card','Bank transfer','Cheque'];
let controller,alive=true,saveTimers=new Map();
const activeWrites=new Set(),resave=new Set();
watch([error,notice],()=>{clearTimeout(toastTimer);toastMessage.value=error.value||notice.value;toastTimer=setTimeout(()=>toastMessage.value='',4500);});
const hasUnsaved=()=>Object.values(saving.value).some(value=>value!=='saved');
function beforeUnload(event){if(activeWrites.size||hasUnsaved()){event.preventDefault();event.returnValue='';}}
onBeforeRouteLeave(()=>{if(activeWrites.size){notice.value='Wait for the current manager updates to finish saving.';return false;}if(hasUnsaved())return window.confirm('Some manager updates are unsaved or invalid. Leave this page and discard those changes?');return true;});
const money=v=>Number(v||0).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2});
const dateText=v=>v?String(v).slice(0,10).split('-').reverse().join('-'):'—';
const words=v=>String(v||'').trim().split(/\s+/).filter(Boolean);
const filtered=computed(()=>{let list=rows.value.filter(r=>!employee.value||r.emp===employee.value).filter(r=>!status.value||r.st===status.value).filter(r=>{if(age.value==='')return true;const bucket=Number(r.age)<=30?0:Number(r.age)<=90?1:2;return String(bucket)===age.value;});if(sortKey.value)list=sortRecoveryRows(list,sortKey.value,sortDir.value);return list;});
const pageCount=computed(()=>Math.max(1,Math.ceil(filtered.value.length/pageSize)));
const pagerNumbers=computed(()=>Array.from({length:Math.min(pageCount.value,page.value+2)-Math.max(1,page.value-2)+1},(_,index)=>Math.max(1,page.value-2)+index));
function goPage(value){page.value=Math.max(1,Math.min(pageCount.value,parseInt(value,10)||1));}
const pageRows=computed(()=>filtered.value.slice((page.value-1)*pageSize,page.value*pageSize));
const totals=computed(()=>recoveryTotals(filtered.value));
const employees=computed(()=>[...new Set(rows.value.map(r=>r.emp).filter(Boolean))].sort((a,b)=>a.localeCompare(b)));
function validDate(value){if(!/^\d{4}-\d{2}-\d{2}$/.test(value||''))return false;const date=new Date(value+'T00:00:00');return !isNaN(date)&&`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`===value;}
function validate(r){if(!['PENDING','COLLECTED','PARTIAL','COMMITTED','NOTCOLL','DISPUTE'].includes(r.st))return 'Select a valid status.';const c=Number(r.colAmt)||0,m=Number(r.cmtAmt)||0;if(c<0||m<0||c>r.due||m>r.due||c+m>r.due+.01)return'Collection and promise amounts cannot exceed the ERP balance.';if(['COLLECTED','PARTIAL'].includes(r.st)&&(!(c>0)||!modes.includes(r.mode)))return'Collected amount and payment mode are required.';if(['COLLECTED','PARTIAL'].includes(r.st)&&r.colDate!==today())return'Collected date must be today.';if(['COMMITTED','PARTIAL'].includes(r.st)&&(!(m>0)||!validDate(r.cmtDate)||r.cmtDate<today()))return'Enter a positive promise amount and today or a future date.';if(r.st==='COLLECTED'&&Math.abs(c-r.due)>.01)return'Full collection must equal the ERP balance.';if(r.st==='NOTCOLL'&&(!reasons.includes(r.reason)||words(r.remark).length<3))return'Choose a reason and enter at least three remark words.';if(r.st==='DISPUTE'&&words(r.remark).length<3)return'Enter at least three words describing the dispute.';if(words(r.remark).length>25)return'Remarks are limited to 25 words.';return'';}
async function reload(){if(activeWrites.size||hasUnsaved()){notice.value='Save or correct pending manager updates before refreshing the invoice list.';return;}controller?.abort();const current=new AbortController();controller=current;loading.value=true;error.value='';notice.value='';page.value=1;try{const args={branch:branch.value,from:from.value,to:to.value,min_due:minDue.value,q:search.value.trim(),sort_by:recoveryManagerSortKeys.includes(sortKey.value)?'due':sortKey.value,sort_dir:sortDir.value,limit:1500};const response=await dataApi('dues_recovery_data',args,{signal:current.signal});if(!alive||controller!==current)return;const data=response.message||{};rows.value=(data.rows||[]).map(r=>({...r,invAmt:recoveryNumber(r.invAmt),paid:recoveryNumber(r.paid),due:recoveryNumber(r.due),colAmt:r.colAmt===''?'':String(recoveryNumber(r.colAmt)),cmtAmt:r.cmtAmt===''?'':String(recoveryNumber(r.cmtAmt))}));clientInfo.enrich(rows.value);branches.value=data.branches||[];if(mode.value==='BR'&&!branch.value&&branches.value.length===1)branch.value=branches.value[0].branch;notice.value=`${rows.value.length.toLocaleString('en-IN')} invoices loaded. Backend returns up to 1,500 rows per request.`;}catch(e){if(alive&&controller===current&&e.name!=='AbortError'){error.value=e.message;rows.value=[];}}finally{if(alive&&controller===current)loading.value=false;}}
function setField(r,key,value){if(key==='st'){r.st=value;if(!['COLLECTED','PARTIAL'].includes(value)){r.colAmt='';r.colDate='';r.mode='';}if(!['PARTIAL','COMMITTED'].includes(value)){r.cmtAmt='';r.cmtDate='';}if(value!=='NOTCOLL')r.reason='';if(value==='COLLECTED'){r.colAmt=String(r.due);}if(value==='COMMITTED'&&!r.cmtAmt)r.cmtAmt=String(r.due);}else if(['colAmt','cmtAmt'].includes(key)){const text=String(value).replace(/,/g,'').trim();if(text&&!/^\d+(?:\.\d{0,2})?$/.test(text)){saving.value={...saving.value,[r.inv]:'Enter a valid amount with up to two decimal places.'};return false;}r[key]=text;}else r[key]=value;return true;}
async function persistRow(r){
  saveTimers.delete(r.inv);
  if(activeWrites.has(r.inv)){resave.add(r.inv);return;}
  const snapshot={...r},problem=validate(snapshot);
  if(problem){saving.value={...saving.value,[r.inv]:problem};return;}
  activeWrites.add(r.inv);
  saving.value={...saving.value,[r.inv]:'pending'};
  try{
    const args={invoice_no:snapshot.inv,branch:snapshot.branch,manager_status:snapshot.st,collected_amount:snapshot.colAmt||0,collected_on:snapshot.colDate||'',mode_of_payment:snapshot.mode||'',committed_amount:snapshot.cmtAmt||0,committed_by:snapshot.cmtDate||'',reason:snapshot.reason||'',remark:snapshot.remark||''};
    const result=await request('dues_recovery_save',{args,csrfToken:session.csrf_token});
    if(!result.message?.ok)throw Error(result.message?.error||'Save failed.');
    if(alive)saving.value={...saving.value,[r.inv]:resave.has(r.inv)||saveTimers.has(r.inv)?'pending':'saved'};
  }catch(e){if(alive)saving.value={...saving.value,[r.inv]:e.message};}
  finally{
    activeWrites.delete(r.inv);
    if(alive&&resave.delete(r.inv)){clearTimeout(saveTimers.get(r.inv));saveTimers.delete(r.inv);persistRow(r);}
  }
}
function saveRow(r){
  clearTimeout(saveTimers.get(r.inv));saving.value={...saving.value,[r.inv]:'pending'};
  if(activeWrites.has(r.inv))resave.add(r.inv);
  saveTimers.set(r.inv,setTimeout(()=>persistRow(r),400));
}

function update(r,key,value){if(setField(r,key,value)!==false)saveRow(r);}
function sort(key){if(sortKey.value===key)sortDir.value=sortDir.value==='asc'?'desc':'asc';else{sortKey.value=key;sortDir.value=['due','invAmt','paid','age','nextDue','inv',...recoveryManagerSortKeys].includes(key)?'desc':'asc';}page.value=1;}
function reset(){if(activeWrites.size||hasUnsaved()){notice.value='Save or correct pending manager updates before clearing filters.';return;}branch.value=employee.value=status.value=age.value=from.value=to.value=minDue.value=search.value='';reload();}
function checkPending(){const count=filtered.value.filter(r=>r.st==='PENDING'||validate(r)).length;notice.value=count?`${count} rows still need complete updates.`:`All ${filtered.value.length} rows are complete.`;}
function printReport(){window.print();}
const csvCell=recoveryCsvCell;
function exportCsv(){const heads=['S.No','Branch','Client Name','Mobile','Booked By','Practitioner','Invoice No','Invoice Date','Service','Invoice Amount','Paid Amount','Due Amount','Next Due Date','Days Overdue','Manager Status','Collected Now','Collected On','Mode','Will Collect','By Date','Reason','Manager Remark'];const data=filtered.value.map((r,index)=>[index+1,r.branch,r.client,maskRecoveryMobile(r.mobile),r.emp,r.practitioner,r.inv,r.invDate,r.service,r.invAmt,r.paid,r.due,r.nextDue,r.age,statuses.find(([key])=>key===r.st)?.[1]||r.st,r.colAmt,r.colDate,r.mode,r.cmtAmt,r.cmtDate,r.reason,r.remark]);const blob=new Blob(['\ufeff'+[heads,...data].map(row=>row.map(csvCell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`LIFE_Pending_Dues_${branch.value||'ALL'}_${today()}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
onMounted(()=>{window.addEventListener('beforeunload',beforeUnload);reload();});
onBeforeUnmount(()=>{clearTimeout(toastTimer);window.removeEventListener('beforeunload',beforeUnload);alive=false;controller?.abort();for(const timer of saveTimers.values())clearTimeout(timer);});

const collectionRows=computed(()=>{const query=clientSearch.value.trim().toLowerCase();return filtered.value.filter(row=>{if(['COLLECTED','NOTCOLL','DISPUTE'].includes(row.st)||Math.max(0,row.due-recoveryNumber(row.colAmt))<=0)return false;return query.length<4||String(row.client||'').toLowerCase().includes(query)||(clientDetails.value[row.inv]?.phones||[row.mobile]).some(phone=>String(phone||'').replace(/\D/g,'').includes(query.replace(/\s/g,'')));});});
const collectionTotal=computed(()=>collectionRows.value.reduce((sum,row)=>sum+Math.max(0,row.due-recoveryNumber(row.colAmt)),0));
const invoiceTotals=computed(()=>filtered.value.reduce((sum,row)=>({invoice:sum.invoice+row.invAmt,paid:sum.paid+row.paid,due:sum.due+row.due}),{invoice:0,paid:0,due:0}));
const kpiCards=computed(()=>[
{label:'Gross pending due',value:money(totals.value.gross),note:filtered.value.length+' invoices in view',cls:'kpi-gross'},
{label:'Update completed',value:(filtered.value.length?Math.round(totals.value.done/filtered.value.length*100):0)+'%',note:totals.value.done+' of '+filtered.value.length+' rows updated',cls:'blue'},
{label:'Collected now',value:money(totals.value.collected),note:'receipted against these invoices',cls:'kpi-collected'},
{label:'Committed by client',value:money(totals.value.committed),note:'promised with a date',cls:'amber'},
{label:'Proposed for removal',value:money(totals.value.writeoff),note:'needs HO approval',cls:'red'},
{label:'Real balance left',value:money(totals.value.real),note:'after collection & clean-up',cls:'kpi-real'}]);
</script>
<template>
<main class="recovery-source-page">


<div id="pdr-app" ref="root" @click="layoutClick" :class="{'pdr-print-one':printTarget}">

<header class="pdr-hd">
  <div class="hd-row">
    <div>
      <div class="pdr-brand">LIFE · COLLECTIONS & RECOVERY</div><h1 class="hd-title" style="margin:0">Pending Balances · Recovery Desk</h1>
      <div class="hd-sub">Live balances, collection commitments and branch follow-up</div>
    </div>
    <div class="hd-mode">
      <a class="pdr-billing" href="/billing-v2?view=billing" target="_blank" rel="noopener">🧾 Billing</a><span class="badge-live" id="liveBadge">● LIVE — ERP DATA</span>
      <label for="modeSel">View as</label>
      <select id="modeSel" v-model="mode" @change="reload">
        <option value="HO">Head Office (all branches)</option>
        <option value="BR">Branch Manager (own branch)</option>
      </select>
      <select id="brLock" v-if="mode==='BR'" v-model="branch" @change="reload"><option v-for="b in branches" :key="b.branch" :value="b.branch">{{b.branch}}</option></select>
    </div>
  </div>
<nav class="pdr-nav" aria-label="Recovery sections"><button type="button" data-pdr-jump="pSchedule" :aria-current="activeSection==='pSchedule'?'location':undefined">Collection Calendar</button><button type="button" data-pdr-jump="pCollection" :aria-current="activeSection==='pCollection'?'location':undefined">Pending collections</button><button type="button" data-pdr-jump="pOverview" :aria-current="activeSection==='pOverview'?'location':undefined">Overview</button><button type="button" data-pdr-jump="pFilter" :aria-current="activeSection==='pFilter'?'location':undefined">Filters</button><button type="button" data-pdr-jump="pMain" :aria-current="activeSection==='pMain'?'location':undefined">Invoices</button><button type="button" data-pdr-jump="pClean" :aria-current="activeSection==='pClean'?'location':undefined">Reconciliation</button><button type="button" data-pdr-jump="pBr" :aria-current="activeSection==='pBr'?'location':undefined">Branches</button><button type="button" data-pdr-jump="pEmp" :aria-current="activeSection==='pEmp'?'location':undefined">Employees</button><button type="button" data-pdr-jump="pFlow" :aria-current="activeSection==='pFlow'?'location':undefined">Process</button><button type="button" class="pdr-reset" data-pdr-reset>Reset layout</button></nav></header>

<div class="wrap" style="display:flex;flex-direction:column">


  <section class="panel" id="pSchedule" tabindex="-1" aria-labelledby="pdr-title-pSchedule" :class="{collapsed:collapsed.includes('pSchedule'), 'pdr-print-target':printTarget==='pSchedule'}" :hidden="hidden.includes('pSchedule')" :style="{order:panelOrder.indexOf('pSchedule')}"><div class="panel-hd"><div class="pdr-section-caption"><h2 class="pdr-section-title" id="pdr-title-pSchedule">Collection Calendar</h2><span class="pdr-section-sub">Scheduled balances and dated commitments for the current filtered invoices</span></div><div class="pdr-panel-tools"><button type="button" data-pdr-move="up" :disabled="panelOrder[0]==='pSchedule'" aria-label="Move section up">↑</button><button type="button" data-pdr-move="down" :disabled="panelOrder[panelOrder.length-1]==='pSchedule'" aria-label="Move section down">↓</button><button type="button" data-pdr-collapse :aria-expanded="!collapsed.includes('pSchedule')">{{collapsed.includes('pSchedule')?'Expand':'Collapse'}}</button><button type="button" data-pdr-extra="close" aria-label="Close section">✕</button><button type="button" data-pdr-extra="print" aria-label="Print section">🖨</button></div></div><div class="panel-bd"><RecoveryCalendar :rows="filtered"/><p class="pdr-due-explain"><b>Two separate views:</b> ERP scheduled dues use the Next Due Date and ERP due balance. Confirmed collectable uses manager commitments and their promised dates; collected, not collectable and disputed rows are excluded. Cards follow the active filters. Next 7 Days starts tomorrow; This Month covers the sales cycle from the 6th to the 5th. These periods overlap and should not be added together.</p></div></section>
  <div class="panel" id="pEmp" tabindex="-1" aria-labelledby="pdr-title-pEmp" :class="{collapsed:collapsed.includes('pEmp'), 'pdr-print-target':printTarget==='pEmp'}" :hidden="hidden.includes('pEmp')" :style="{order:panelOrder.indexOf('pEmp')}">
    <div class="panel-hd"><div class="pdr-section-caption"><h2 class="pdr-section-title" id="pdr-title-pEmp">Employee Pending Balances</h2><span class="pdr-section-sub">Pending balances, collections and commitments by employee and branch</span></div><span class="tog">▾</span><div class="pdr-panel-tools"><button type="button" data-pdr-move="up" :disabled="panelOrder[0]==='pEmp'" aria-label="Move section up">↑</button><button type="button" data-pdr-move="down" :disabled="panelOrder[panelOrder.length-1]==='pEmp'" aria-label="Move section down">↓</button><button type="button" data-pdr-collapse :aria-expanded="!collapsed.includes('pEmp')">{{collapsed.includes('pEmp')?'Expand':'Collapse'}}</button><button type="button" data-pdr-extra="close" aria-label="Close section">✕</button><button type="button" data-pdr-extra="print" aria-label="Print section">🖨</button></div></div>
    <div class="panel-bd"><div class="tbl-scroll" style="max-height:400px"><RecoverySourceTable :rows="filtered" kind="employees"/></div></div>
  </div>

<section class="panel" id="pCollection" tabindex="-1" aria-labelledby="pdr-title-pCollection" :class="{collapsed:collapsed.includes('pCollection'), 'pdr-print-target':printTarget==='pCollection'}" :hidden="hidden.includes('pCollection')" :style="{order:panelOrder.indexOf('pCollection')}"><div class="panel-hd"><div class="pdr-section-caption"><h2 class="pdr-section-title" id="pdr-title-pCollection">Pending Collection List</h2><span class="pdr-section-sub">Exact ERP balance, next appointment and confirmed commitment — amounts never inferred from remarks</span></div><input type="search" id="pdrClientSearch" v-model="clientSearch" placeholder="Search name / phone · 4+ characters" aria-label="Search pending clients"><div class="pdr-panel-tools"><button type="button" data-pdr-move="up" :disabled="panelOrder[0]==='pCollection'" aria-label="Move section up">↑</button><button type="button" data-pdr-move="down" :disabled="panelOrder[panelOrder.length-1]==='pCollection'" aria-label="Move section down">↓</button><button type="button" data-pdr-collapse :aria-expanded="!collapsed.includes('pCollection')">{{collapsed.includes('pCollection')?'Expand':'Collapse'}}</button><button type="button" data-pdr-extra="close" aria-label="Close section">✕</button><button type="button" data-pdr-extra="print" aria-label="Print section">🖨</button></div></div><div class="panel-bd"><div class="tbl-scroll"><table id="pdrCollectionTbl"><thead><tr><th>Client · next appointment · phones</th><th>Branch</th><th>Booked by</th><th>Invoice</th><th>ERP pending</th><th>Confirmed amount</th><th>Promise date</th><th>Manager remark</th></tr></thead><tbody><tr v-for="r in collectionRows" :key="r.inv"><td><RecoveryClientCell :row="r" :detail="clientDetails[r.inv]"/></td><td>{{r.branch}}</td><td>{{r.emp||'Unassigned'}}</td><td>{{r.inv}}</td><td class="num">{{money(Math.max(0,r.due-recoveryNumber(r.colAmt)))}}</td><td class="num">{{['COMMITTED','PARTIAL'].includes(r.st)?money(r.cmtAmt):'—'}}</td><td>{{dateText(r.cmtDate)}}</td><td>{{r.remark||'—'}}</td></tr><tr v-if="!collectionRows.length"><td colspan="8">No matching pending collections.</td></tr></tbody><tfoot><tr><td colspan="4">{{collectionRows.length}} invoices · current filters</td><td class="num">{{money(collectionTotal)}}</td><td colspan="3"></td></tr></tfoot></table></div><p id="pdrEnrichmentStatus" class="hint" role="status">{{enrichmentStatus}}</p></div></section><section class="panel" id="pOverview" tabindex="-1" aria-labelledby="pdr-title-pOverview" :class="{collapsed:collapsed.includes('pOverview'), 'pdr-print-target':printTarget==='pOverview'}" :hidden="hidden.includes('pOverview')" :style="{order:panelOrder.indexOf('pOverview')}"><div class="panel-hd"><div class="pdr-section-caption"><h2 class="pdr-section-title" id="pdr-title-pOverview">Recovery Overview</h2><span class="pdr-section-sub">ERP balances, manager updates and the remaining balance</span></div><div class="pdr-panel-tools"><button type="button" data-pdr-move="up" :disabled="panelOrder[0]==='pOverview'" aria-label="Move section up">↑</button><button type="button" data-pdr-move="down" :disabled="panelOrder[panelOrder.length-1]==='pOverview'" aria-label="Move section down">↓</button><button type="button" data-pdr-collapse :aria-expanded="!collapsed.includes('pOverview')">{{collapsed.includes('pOverview')?'Expand':'Collapse'}}</button><button type="button" data-pdr-extra="close" aria-label="Close section">✕</button><button type="button" data-pdr-extra="print" aria-label="Print section">🖨</button></div></div><div class="panel-bd"><div class="kpis" id="kpis"><div v-for="card in kpiCards" :key="card.label" class="kpi" :class="card.cls"><div class="k-lbl">{{card.label}}</div><div class="k-val">{{card.value}}</div><div class="k-note">{{card.note}}</div></div></div></div></section>


  <div class="panel" id="pFilter" tabindex="-1" aria-labelledby="pdr-title-pFilter" :class="{collapsed:collapsed.includes('pFilter'), 'pdr-print-target':printTarget==='pFilter'}" :hidden="hidden.includes('pFilter')" :style="{order:panelOrder.indexOf('pFilter')}">
    <div class="panel-hd"><div class="pdr-section-caption"><h2 class="pdr-section-title" id="pdr-title-pFilter">Filters & Actions</h2><span class="pdr-section-sub">Choose the branch, employee, status and due-date range</span></div><span class="tog">▾</span><div class="pdr-panel-tools"><button type="button" data-pdr-move="up" :disabled="panelOrder[0]==='pFilter'" aria-label="Move section up">↑</button><button type="button" data-pdr-move="down" :disabled="panelOrder[panelOrder.length-1]==='pFilter'" aria-label="Move section down">↓</button><button type="button" data-pdr-collapse :aria-expanded="!collapsed.includes('pFilter')">{{collapsed.includes('pFilter')?'Expand':'Collapse'}}</button><button type="button" data-pdr-extra="close" aria-label="Close section">✕</button><button type="button" data-pdr-extra="print" aria-label="Print section">🖨</button></div></div>
    <div class="panel-bd">
      <div class="filters">
        <div class="fld"><label for="fBranch">Branch</label><select id="fBranch" v-model="branch" @change="reload"><option value="">All branches</option><option v-for="b in branches" :key="b.branch" :value="b.branch">{{b.branch}}  ({{b.n}})</option></select></div>
        <div class="fld"><label for="fEmp">Booked by (employee)</label><select id="fEmp" v-model="employee" @change="page=1"><option value="">All employees</option><option v-for="e in employees" :key="e" :value="e">{{e}}</option></select></div>
        <div class="fld"><label for="fStatus">Manager status</label><select id="fStatus" v-model="status" @change="page=1"><option value="">All statuses</option><option v-for="[key,label] in statuses" :key="key" :value="key">{{label.replace(/-/g,'').trim()}}</option></select></div>
        <div class="fld"><label for="fAge">Ageing bucket</label><select id="fAge" v-model="age" @change="page=1">
          <option value="">All</option><option value="0">0–30 days</option><option value="1">31–90 days</option><option value="2">90+ days</option></select></div>
        <div class="fld"><label for="fFrom">Due date from</label><input type="date" id="fFrom" v-model="from" @change="reload"></div>
        <div class="fld"><label for="fTo">Due date to</label><input type="date" id="fTo" v-model="to" @change="reload"></div>
        <div class="fld"><label for="fMin">Min due amount</label><input type="number" id="fMin" v-model="minDue" placeholder="0" @change="reload"></div>
        <div class="fld"><label for="fSearch">Search name / mobile / invoice</label><input type="text" id="fSearch" v-model="search" placeholder="Type &amp; Enter…" @keydown.enter="reload"></div>
      </div>
      <div class="btnbar">
        <button class="b" @click="reload">Fetch / Refresh live data</button>
        <button class="b ghost" @click="reset">Clear filters</button>
        <button class="b" @click="checkPending">Check pending updates</button>
        <button class="b ghost" @click="exportCsv">Download Excel (CSV)</button>
        <button class="b ghost" @click="printReport">Print</button>
      </div>
      <div class="hint">
        ERP columns are read only. Enter confirmations in the blue <b>Manager Update</b> columns. Changes save automatically when you leave a field. Use filters to focus the invoice list.
      </div>
    </div>
  </div>


  <div class="panel" id="pMain" tabindex="-1" aria-labelledby="pdr-title-pMain" :class="{collapsed:collapsed.includes('pMain'), 'pdr-print-target':printTarget==='pMain'}" :hidden="hidden.includes('pMain')" :style="{order:panelOrder.indexOf('pMain')}">
    <div class="panel-hd"><div class="pdr-section-caption"><h2 class="pdr-section-title" id="pdr-title-pMain">Invoice Recovery Register</h2><span class="pdr-section-sub">Read ERP details on the left; enter manager updates in the blue columns</span></div><span class="tog" id="cntTag">▾</span><div class="pdr-panel-tools"><button type="button" data-pdr-move="up" :disabled="panelOrder[0]==='pMain'" aria-label="Move section up">↑</button><button type="button" data-pdr-move="down" :disabled="panelOrder[panelOrder.length-1]==='pMain'" aria-label="Move section down">↓</button><button type="button" data-pdr-collapse :aria-expanded="!collapsed.includes('pMain')">{{collapsed.includes('pMain')?'Expand':'Collapse'}}</button><button type="button" data-pdr-extra="close" aria-label="Close section">✕</button><button type="button" data-pdr-extra="print" aria-label="Print section">🖨</button></div></div>
    <div class="panel-bd">
      <div class="tbl-scroll">
        <table id="mainTbl">
          <thead>
            <tr>
              <th class="grp" colspan="9">ERP DATA (read only)</th>
              <th class="grp" colspan="7">MANAGER UPDATE (saved to ERP)</th>
            </tr>
           <tr class="r2">

  <th>#</th>

  <th data-sort-key="branch" tabindex="0" role="button" @click="sort('branch')" @keydown.enter="sort('branch')" @keydown.space.prevent="sort('branch')" :aria-sort="sortKey==='branch'?(sortDir==='asc'?'ascending':'descending'):'none'">
    <div class="pdr-th-sort">
      <span>Branch</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='branch'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
    <span class="sub">Code</span>
  </th>

  <th data-sort-key="client" tabindex="0" role="button" @click="sort('client')" @keydown.enter="sort('client')" @keydown.space.prevent="sort('client')" :aria-sort="sortKey==='client'?(sortDir==='asc'?'ascending':'descending'):'none'">
    <div class="pdr-th-sort">
      <span>Client name</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='client'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
    <span class="sub">Mobile</span>
  </th>

  <th data-sort-key="emp" tabindex="0" role="button" @click="sort('emp')" @keydown.enter="sort('emp')" @keydown.space.prevent="sort('emp')" :aria-sort="sortKey==='emp'?(sortDir==='asc'?'ascending':'descending'):'none'">
    <div class="pdr-th-sort">
      <span>Booked by</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='emp'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
    <span class="sub">Practitioner</span>
  </th>

  <th data-sort-key="inv" tabindex="0" role="button" @click="sort('inv')" @keydown.enter="sort('inv')" @keydown.space.prevent="sort('inv')" :aria-sort="sortKey==='inv'?(sortDir==='asc'?'ascending':'descending'):'none'">
    <div class="pdr-th-sort">
      <span>Invoice no.</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='inv'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
    <span class="sub">Invoice date</span>
  </th>

  <th data-sort-key="invAmt" tabindex="0" role="button" @click="sort('invAmt')" @keydown.enter="sort('invAmt')" @keydown.space.prevent="sort('invAmt')" :aria-sort="sortKey==='invAmt'?(sortDir==='asc'?'ascending':'descending'):'none'">
    <div class="pdr-th-sort">
      <span>Invoice amt</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='invAmt'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
  </th>

  <th data-sort-key="paid" tabindex="0" role="button" @click="sort('paid')" @keydown.enter="sort('paid')" @keydown.space.prevent="sort('paid')" :aria-sort="sortKey==='paid'?(sortDir==='asc'?'ascending':'descending'):'none'">
    <div class="pdr-th-sort">
      <span>Paid amt</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='paid'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
  </th>

  <th data-sort-key="due" tabindex="0" role="button" @click="sort('due')" @keydown.enter="sort('due')" @keydown.space.prevent="sort('due')" :aria-sort="sortKey==='due'?(sortDir==='asc'?'ascending':'descending'):'none'">
    <div class="pdr-th-sort">
      <span>Due amt</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='due'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
  </th>

  <th data-sort-key="nextDue" tabindex="0" role="button" @click="sort('nextDue')" @keydown.enter="sort('nextDue')" @keydown.space.prevent="sort('nextDue')" :aria-sort="sortKey==='nextDue'?(sortDir==='asc'?'ascending':'descending'):'none'">
    <div class="pdr-th-sort">
      <span>Next due date</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='nextDue'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
    <span class="sub">Ageing</span>
  </th>

  <th data-sort-key="st" tabindex="0" role="button" @click="sort('st')" @keydown.enter="sort('st')" @keydown.space.prevent="sort('st')" :aria-sort="sortKey==='st'?(sortDir==='asc'?'ascending':'descending'):'none'" style="min-width:150px">
    <div class="pdr-th-sort">
      <span>Status</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='st'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
    <span class="sub">select first</span>
  </th>

  <th data-sort-key="colAmt" tabindex="0" role="button" @click="sort('colAmt')" @keydown.enter="sort('colAmt')" @keydown.space.prevent="sort('colAmt')" :aria-sort="sortKey==='colAmt'?(sortDir==='asc'?'ascending':'descending'):'none'" style="min-width:100px">
    <div class="pdr-th-sort">
      <span>Collected now ₹</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='colAmt'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
  </th>

  <th data-sort-key="colDate" tabindex="0" role="button" @click="sort('colDate')" @keydown.enter="sort('colDate')" @keydown.space.prevent="sort('colDate')" :aria-sort="sortKey==='colDate'?(sortDir==='asc'?'ascending':'descending'):'none'" style="min-width:112px">
    <div class="pdr-th-sort">
      <span>Collected on</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='colDate'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
  </th>

  <th data-sort-key="mode" tabindex="0" role="button" @click="sort('mode')" @keydown.enter="sort('mode')" @keydown.space.prevent="sort('mode')" :aria-sort="sortKey==='mode'?(sortDir==='asc'?'ascending':'descending'):'none'" style="min-width:95px">
    <div class="pdr-th-sort">
      <span>Mode</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='mode'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
  </th>

  <th data-sort-key="cmtAmt" tabindex="0" role="button" @click="sort('cmtAmt')" @keydown.enter="sort('cmtAmt')" @keydown.space.prevent="sort('cmtAmt')" :aria-sort="sortKey==='cmtAmt'?(sortDir==='asc'?'ascending':'descending'):'none'" style="min-width:110px">
    <div class="pdr-th-sort">
      <span>Will collect ₹</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='cmtAmt'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
  </th>

  <th data-sort-key="cmtDate" tabindex="0" role="button" @click="sort('cmtDate')" @keydown.enter="sort('cmtDate')" @keydown.space.prevent="sort('cmtDate')" :aria-sort="sortKey==='cmtDate'?(sortDir==='asc'?'ascending':'descending'):'none'" style="min-width:112px">
    <div class="pdr-th-sort">
      <span>By date</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='cmtDate'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
  </th>

  <th data-sort-key="reasonRemark" tabindex="0" role="button" @click="sort('reasonRemark')" @keydown.enter="sort('reasonRemark')" @keydown.space.prevent="sort('reasonRemark')" :aria-sort="sortKey==='reasonRemark'?(sortDir==='asc'?'ascending':'descending'):'none'" style="min-width:230px">
    <div class="pdr-th-sort">
      <span>Reason / remark</span>
      <span class="sort-ico" aria-hidden="true">{{sortKey==='reasonRemark'?(sortDir==='asc'?'▲':'▼'):'↕'}}</span>
    </div>
    <span class="sub">max 25 words</span>
  </th>

</tr>
          </thead>
          <tbody id="tb"><tr v-for="r in pageRows" :key="r.inv" :class="r.st==='PENDING'?'':'st-'+r.st" :data-i="r.inv"><td class="ctr">{{filtered.indexOf(r)+1}}</td><td><span class="code">{{r.branch}}</span></td><td><RecoveryClientCell :row="r" :detail="clientDetails[r.inv]"/></td><td>{{ r.emp||'—' }}<span class="sub">{{ r.practitioner||'' }}</span></td><td>{{ r.inv }}<span class="sub">{{ dateText(r.invDate) }} · {{r.service}}</span></td><td class="num">{{ money(r.invAmt) }}</td><td class="num">{{ money(r.paid) }}</td><td class="num">{{ money(r.due) }}</td><td>{{ dateText(r.nextDue) }}<span class="sub"><span class="aging" :class="Number(r.age)<=30?'a0':Number(r.age)<=90?'a1':'a2'">{{Number(r.age)<=0?'Not yet due':r.age+' days over'}}</span></span></td><td><select class="mi" :class="'v-'+r.st" :value="r.st" @change="update(r,'st',$event.target.value)"><option v-if="r.st==='PARTIAL'" value="PARTIAL" disabled>Part collected</option><option v-for="[key,label] in statuses" :key="key" :value="key">{{ label }}</option></select></td><td><input class="mi" :value="r.colAmt?money(r.colAmt):''" type="text" inputmode="decimal" min="0" step="0.01" :max="r.due" :disabled="!['COLLECTED','PARTIAL'].includes(r.st)" @change="update(r,'colAmt',$event.target.value)"></td><td><input class="mi" :value="r.colDate" type="date" :min="today()" :max="today()" :disabled="!['COLLECTED','PARTIAL'].includes(r.st)" @change="update(r,'colDate',$event.target.value)"></td><td><select class="mi" :value="r.mode" :disabled="!['COLLECTED','PARTIAL'].includes(r.st)" @change="update(r,'mode',$event.target.value)"><option value="">Choose</option><option v-for="m in modes" :key="m">{{ m }}</option></select></td><td><input class="mi" :value="r.cmtAmt?money(r.cmtAmt):''" type="text" inputmode="decimal" min="0" step="0.01" :max="r.due" :disabled="!['PARTIAL','COMMITTED'].includes(r.st)" @change="update(r,'cmtAmt',$event.target.value)"></td><td><input class="mi" :value="r.cmtDate" type="date" :min="today()" :disabled="!['PARTIAL','COMMITTED'].includes(r.st)" @change="update(r,'cmtDate',$event.target.value)"></td><td><select v-if="r.st==='NOTCOLL'" class="mi" :value="r.reason" :disabled="r.st!=='NOTCOLL'" @change="update(r,'reason',$event.target.value)"><option value="">Choose reason</option><option v-for="reason in reasons" :key="reason">{{ reason }}</option></select><textarea class="mi" :value="r.remark" placeholder="Up to 25 words" :disabled="r.st==='PENDING'" @change="update(r,'remark',$event.target.value)"></textarea><div class="wc">{{words(r.remark).length}}/25 words</div><span class="pb-save" :class="{saved:saving[r.inv]==='saved',failed:!!saving[r.inv]&&saving[r.inv]!=='saved'&&saving[r.inv]!=='pending'}">{{ saving[r.inv]==='pending'?'Saving…':saving[r.inv]==='saved'?'Saved':saving[r.inv]||'—' }}</span></td></tr><tr v-if="!loading&&!pageRows.length"><td colspan="16">No invoices match these filters. Clear a filter or hit Refresh.</td></tr></tbody>
          <tfoot><tr id="tf"><td colspan="5" style="text-align:right">TOTAL - {{filtered.length}} invoices (all pages)</td><td class="num">{{money(invoiceTotals.invoice)}}</td><td class="num">{{money(invoiceTotals.paid)}}</td><td class="num">{{money(invoiceTotals.due)}}</td><td colspan="8"></td></tr></tfoot>
        </table>
        <div id="pager" class="pager"><span class="pg-info">Showing {{filtered.length?(page-1)*pageSize+1:0}}-{{Math.min(page*pageSize,filtered.length)}} of {{filtered.length}}</span><span class="pg-btns"><button class="pg-b" :disabled="page<=1" @click="goPage(1)">« First</button><button class="pg-b" :disabled="page<=1" @click="goPage(page-1)">‹ Prev</button><span v-if="pagerNumbers[0]>1" class="pg-dots">...</span><button v-for="number in pagerNumbers" :key="number" class="pg-b" :class="{cur:page===number}" @click="goPage(number)">{{number}}</button><span v-if="pagerNumbers[pagerNumbers.length-1]<pageCount" class="pg-dots">...</span><button class="pg-b" :disabled="page>=pageCount" @click="goPage(page+1)">Next ›</button><button class="pg-b" :disabled="page>=pageCount" @click="goPage(pageCount)">Last »</button></span><span class="pg-jump">Page <input id="pgInput" type="number" min="1" :max="pageCount" :value="page" @change="goPage($event.target.value)"> / {{pageCount}}</span></div>
      </div>
      <div class="legend">
        <span><i style="background:var(--g-mid)"></i>Collected</span>
        <span><i style="background:#2E6DA4"></i>Will collect</span>
        <span><i style="background:#C79100"></i>Part collected</span>
        <span><i style="background:#B4432E"></i>Not collectable — to be removed</span>
        <span><i style="background:#7B5EA7"></i>Disputed / on hold</span>
        <span><i style="background:#D8DEDA"></i>Not yet updated</span>
      </div>
    </div>
  </div>


  <div class="panel" id="pClean" tabindex="-1" aria-labelledby="pdr-title-pClean" :class="{collapsed:collapsed.includes('pClean'), 'pdr-print-target':printTarget==='pClean'}" :hidden="hidden.includes('pClean')" :style="{order:panelOrder.indexOf('pClean')}">
    <div class="panel-hd"><div class="pdr-section-caption"><h2 class="pdr-section-title" id="pdr-title-pClean">Balance Reconciliation</h2><span class="pdr-section-sub">Gross dues, collections and proposed removals</span></div><span class="tog">▾</span><div class="pdr-panel-tools"><button type="button" data-pdr-move="up" :disabled="panelOrder[0]==='pClean'" aria-label="Move section up">↑</button><button type="button" data-pdr-move="down" :disabled="panelOrder[panelOrder.length-1]==='pClean'" aria-label="Move section down">↓</button><button type="button" data-pdr-collapse :aria-expanded="!collapsed.includes('pClean')">{{collapsed.includes('pClean')?'Expand':'Collapse'}}</button><button type="button" data-pdr-extra="close" aria-label="Close section">✕</button><button type="button" data-pdr-extra="print" aria-label="Print section">🖨</button></div></div>
    <div class="panel-bd">
      <RecoverySourceTable :rows="filtered" kind="reconciliation"/>
      <div class="hint">Only rows marked <b>Not collectable</b> are proposed for removal. HO approves the list before anything is written off in the ERP.</div>
    </div>
  </div>


  <div class="panel" id="pBr" tabindex="-1" aria-labelledby="pdr-title-pBr" :class="{collapsed:collapsed.includes('pBr'), 'pdr-print-target':printTarget==='pBr'}" :hidden="hidden.includes('pBr')" :style="{order:panelOrder.indexOf('pBr')}">
    <div class="panel-hd"><div class="pdr-section-caption"><h2 class="pdr-section-title" id="pdr-title-pBr">Branch Recovery Summary</h2><span class="pdr-section-sub">Compare balances and update completion across branches</span></div><span class="tog">▾</span><div class="pdr-panel-tools"><button type="button" data-pdr-move="up" :disabled="panelOrder[0]==='pBr'" aria-label="Move section up">↑</button><button type="button" data-pdr-move="down" :disabled="panelOrder[panelOrder.length-1]==='pBr'" aria-label="Move section down">↓</button><button type="button" data-pdr-collapse :aria-expanded="!collapsed.includes('pBr')">{{collapsed.includes('pBr')?'Expand':'Collapse'}}</button><button type="button" data-pdr-extra="close" aria-label="Close section">✕</button><button type="button" data-pdr-extra="print" aria-label="Print section">🖨</button></div></div>
    <div class="panel-bd"><div class="tbl-scroll" style="max-height:400px"><RecoverySourceTable :rows="filtered" kind="branches"/></div></div>
  </div>


  <div class="panel" id="pFlow" tabindex="-1" aria-labelledby="pdr-title-pFlow" :class="{collapsed:collapsed.includes('pFlow'), 'pdr-print-target':printTarget==='pFlow'}" :hidden="hidden.includes('pFlow')" :style="{order:panelOrder.indexOf('pFlow')}">
    <div class="panel-hd"><div class="pdr-section-caption"><h2 class="pdr-section-title" id="pdr-title-pFlow">Recovery Process</h2><span class="pdr-section-sub">From client follow-up to Head Office review</span></div><span class="tog">▾</span><div class="pdr-panel-tools"><button type="button" data-pdr-move="up" :disabled="panelOrder[0]==='pFlow'" aria-label="Move section up">↑</button><button type="button" data-pdr-move="down" :disabled="panelOrder[panelOrder.length-1]==='pFlow'" aria-label="Move section down">↓</button><button type="button" data-pdr-collapse :aria-expanded="!collapsed.includes('pFlow')">{{collapsed.includes('pFlow')?'Expand':'Collapse'}}</button><button type="button" data-pdr-extra="close" aria-label="Close section">✕</button><button type="button" data-pdr-extra="print" aria-label="Print section">🖨</button></div></div>
    <div class="panel-bd">
      <div class="steps">
        <div class="step"><b>1 · HO extracts</b><span>All open invoices with a due balance load straight from the ERP into this sheet, branch-wise.</span></div>
        <div class="step"><b>2 · Branch calls the client</b><span>Counsellor and manager call every client on their list and record what actually happened.</span></div>
        <div class="step"><b>3 · Manager updates</b><span>Pick a status, then fill only the boxes that open up. Reason is compulsory for anything not collectable.</span></div>
        <div class="step"><b>4 · Auto-saved to ERP</b><span>Each update writes to the ERP instantly — no file to mail. HO sees it live.</span></div>
        <div class="step"><b>5 · HO reviews</b><span>HO checks every "not collectable" line with the reason and the manager name before approving.</span></div>
        <div class="step"><b>6 · ERP clean-up</b><span>Approved lines are written off, collections are receipted, and the balance left is the real recoverable due.</span></div>
      </div>
    </div>
  </div>

</div>
<div class="pdr-layout-status" role="status" aria-live="polite">{{announcement}}</div>
<div class="toast" id="toast" :class="{show:toastMessage,err:!!error}" role="status">{{toastMessage}}</div>
<div class="pdr-loader" id="loader" v-if="loading" style="display:flex"><div class="spin"></div><span>Loading live data…</span></div>

</div>
</main>
</template>
<style scoped src="../styles/recovery-source.css"></style>
