<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { billingCall, billingList, getBillingDoc, invoicePrintViewUrl, refreshBillingOffers } from '../api/billing';
import { billingBranches, normalizeMobile, recentBillingRange, canApproveRequest } from '../lib/billing';
import { dateRange, indiaStamp } from '../lib/cc';
import BillingDialog from '../components/billing/BillingDialog.vue';
import BillingPendingGroups from '../components/billing/BillingPendingGroups.vue';
import BillingOverview from '../components/billing/BillingOverview.vue';
import BillingCollections from '../components/billing/BillingCollections.vue';
import BillingRegistration from '../components/billing/BillingRegistration.vue';
import BillingEditor from '../components/billing/BillingEditor.vue';
import BillingInvoice from '../components/billing/BillingInvoice.vue';
import '../styles/billing-native.css';
import { session } from '../lib/session';
const route=useRoute(),router=useRouter();
const tabs=[['billing','Billing'],['recent','Recent bills'],['pending','Pending dues'],['collections','Collections'],['approvals','Approvals']];
const view=ref(tabs.some(([id])=>id===route.query.view)?route.query.view:'billing');
const bootstrap=ref(null),branch=ref(''),branches=ref([]),headOffice=ref(false),busy=ref(false),error=ref(''),notice=ref(''),query=ref(''),clients=ref([]),client=ref(null),editing=ref(false),registering=ref(false),invoice=ref(''),rows=ref([]),page=ref(1),hasMore=ref(false),listQuery=ref(''),status=ref(''),warning=ref(''),offerWarning=ref(''),stockReceipts=ref([]),minimumDue=ref(0),overviewVersion=ref(0),clientTotals=ref(null),searchPerformed=ref(false),invoiceAction=ref(''),nextInvoice=ref(''),counts=ref({pending:null,approvals:null}),transactionBusy=ref(false);
const [cycleFrom,cycleTo]=dateRange('month');
const from=ref(view.value==='recent'?indiaStamp().slice(0,10):cycleFrom),to=ref(view.value==='recent'?indiaStamp().slice(0,10):cycleTo);
const money=v=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(Number(v || 0));
let generation=0,controller,searchTimer;
const scopeFilters=computed(()=>branch.value?[['branch','=',branch.value]]:headOffice.value?[]:[['branch','in',branches.value]]);
const displayed=computed(()=>rows.value);
async function action(fn){if(busy.value)return;busy.value=true;error.value='';try{await fn();}catch(e){error.value=e.message;}finally{busy.value=false;}}
async function loadList(reset=true){
  if(reset)page.value=1;
  const token=++generation;controller?.abort();controller=new AbortController();
  error.value='';rows.value=[];
  if(!from.value || !to.value || from.value>to.value)throw new Error('Choose a valid date range.');
  if(!branches.value.length && !headOffice.value)throw new Error('No permitted branch is available.');
  const approvals=view.value==='approvals';
  const filters=[...scopeFilters.value];
  if(approvals){filters.push(['status','=','Pending'],['creation','>=',from.value+' 00:00:00'],['creation','<=',to.value+' 23:59:59']);}
  else{filters.push(['docstatus','in',[0,1]],['posting_date','>=',from.value],['posting_date','<=',to.value]);if(view.value==='pending')filters.push(['docstatus','=',1],['outstanding_amount','>',0]);if(status.value)filters.push(['status','=',status.value]);}
  if(view.value==='pending' && Number(minimumDue.value)>0)filters.push(['outstanding_amount','>=',Number(minimumDue.value)]);
  const orFilters=[];
  const term=listQuery.value.trim();
  if(term){
    if(approvals)orFilters.push(['linked_invoice','like','%'+term+'%'],['selected_approver','like','%'+term+'%']);
    else{orFilters.push(['name','like','%'+term+'%'],['patient_name','like','%'+term+'%'],['patient','like','%'+term+'%']);
      const digits=normalizeMobile(term);
      if(/^[\d\s+()-]+$/.test(term)){const matches=await billingList('Patient',[['mobile','like','%'+digits+'%']],['name'],{limit:101,signal:controller.signal});if(matches.length>100)throw new Error('Narrow the mobile search.');if(matches.length)orFilters.push(['patient','in',matches.map(p=>p.name)]);}
    }
  }
  const fields=approvals?['name','linked_invoice','selected_approver','requested_by','approval_level','requested_discount_pct','requested_final_amount','bill_total','status','reason','creation','branch']:['name','patient','patient_name','posting_date','branch','grand_total','outstanding_amount','docstatus','status','custom_remarks_for_office_use'];
  const result=await billingList(approvals?'Discount Approval Request':'Sales Invoice',filters,fields,{start:(page.value-1)*40,limit:41,order:approvals?'creation desc':'posting_date desc, creation desc',signal:controller.signal,orFilters});
  if(token===generation){rows.value=result.slice(0,40);hasMore.value=result.length>40;}
}
async function initialize(){await action(async()=>{
  const boot=await billingCall('lifescc_billing_bootstrap');
  const scope=billingBranches(boot);if(!boot.modes?.some(m=>/razorpay/i.test(m.name)))boot.modes=[...(boot.modes || []),{name:'Razorpay Software Pvt Ltd -Link',type:'Bank'}];boot.modes.sort((a,b)=>(a.name==='Cash'?-1:b.name==='Cash'?1:/razorpay/i.test(a.name)?-1:/razorpay/i.test(b.name)?1:a.name.localeCompare(b.name)));bootstrap.value=boot;branches.value=scope.branches;headOffice.value=scope.headOffice;branch.value=scope.selected;
  if(!['billing','collections'].includes(view.value))await loadList();
  if(route.query.invoice)openInvoice(String(route.query.invoice));refreshCounts();
});
// Stock receipts are reminders only in the current Billing implementation.
if(bootstrap.value){try{bootstrap.value.offers=await refreshBillingOffers(bootstrap.value.offers || [],indiaStamp().slice(0,10));}catch{offerWarning.value='Using bootstrap offers; live pricing rule refresh was unavailable.';}}
if(bootstrap.value)try{const result=await billingCall('life_stock_fast_requests',{action:'billing_receipt_gate',payload:'{}'});stockReceipts.value=(result.overdue_receipts || []).filter(r=>!r.release_date || String(r.release_date)>='2026-08-01');if(stockReceipts.value.length)warning.value='Overdue stock receipts need attention. Billing remains available.';}catch{warning.value='Stock receipt reminder could not be checked.';}}
function switchView(id){if(busy.value)return;client.value=null;view.value=id;invoice.value='';editing.value=false;registering.value=false;status.value='';listQuery.value='';[from.value,to.value]=dateRange(id==='recent'?'today':'month');router.replace({query:{...route.query,view:id,invoice:undefined}});if(!['billing','collections'].includes(id))action(()=>loadList());}
function resetDates(){[from.value,to.value]=dateRange('month');action(()=>loadList());}
function recentPreset(id){[from.value,to.value]=recentBillingRange(id,indiaStamp().slice(0,10));action(()=>loadList());}
function search(){clearTimeout(searchTimer);return action(async()=>{
  clients.value=[];searchPerformed.value=false;const raw=query.value.trim();if(raw.length<3)throw new Error('Enter at least three characters.');
  const numeric=/^[\d\s+()-]+$/.test(raw),mobile=normalizeMobile(raw);
  const phone=numeric && mobile.length>=6 && mobile.length<=10 && /^[6-9]/.test(mobile);
  const orFilters=[['name','like','%'+raw+'%'],['patient_name','like','%'+raw+'%']];
  if(phone)orFilters.push(['mobile','like','%'+mobile+'%']);
  clients.value=await billingList('Patient',[],['name','patient_name','mobile','custom_branch','custom_lead','sex'],{limit:8,order:'modified desc',orFilters});searchPerformed.value=true;
});}
async function changePage(next){
  const previous=page.value;page.value=next;
  try{await action(()=>loadList(false));if(error.value)page.value=previous;}
  catch{page.value=previous;}
}
function queueSearch(){clearTimeout(searchTimer);if(query.value.trim().length>=3)searchTimer=setTimeout(search,250);else{clients.value=[];searchPerformed.value=false;}}
function backToSearch(){client.value=null;rows.value=[];clientTotals.value=null;query.value='';searchPerformed.value=false;}
function openInvoice(name,action=''){if(!name)return;invoiceAction.value=action;invoice.value=name;}
function viewInvoiceBill(name){if(!name)return;window.open(invoicePrintViewUrl(name,bootstrap.value?.latest_invoice_print_format || 'Consultaion Patient Sales Invoice'),'_blank','noopener,noreferrer');}
async function refreshCounts(){try{const [pending,approvals]=await Promise.all([billingCall('frappe.client.get_count',{doctype:'Sales Invoice',filters:[['docstatus','=',1],['outstanding_amount','>',0],...scopeFilters.value]}),billingCall('frappe.client.get_count',{doctype:'Discount Approval Request',filters:[['status','=','Pending'],...scopeFilters.value]})]);counts.value={pending:Number(pending),approvals:Number(approvals)};}catch{counts.value={pending:null,approvals:null};}}
function selectClient(name){clearTimeout(searchTimer);return action(async()=>{client.value=await getBillingDoc('Patient',name);clients.value=[];editing.value=false;registering.value=false;rows.value=await billingList('Sales Invoice',[['patient','=',name],...scopeFilters.value],['name','patient_name','posting_date','branch','grand_total','outstanding_amount','status','docstatus'],{limit:41,order:'posting_date desc, creation desc'});hasMore.value=rows.value.length>40;rows.value=rows.value.slice(0,40);const aggregate=await billingList('Sales Invoice',[['patient','=',name],...scopeFilters.value],['sum(grand_total) as billed','sum(outstanding_amount) as due','count(name) as count'],{limit:1,order:''});clientTotals.value=aggregate[0] || null;});}
function registered(name,message){notice.value=message || 'Client registered.';selectClient(name);}
function created(name){invoiceAction.value='';editing.value=false;invoice.value=name;notice.value='Draft invoice created.';}
function closeInvoice(){invoice.value='';if(client.value && view.value==='billing')selectClient(client.value.name);if(route.query.invoice)router.replace({query:{...route.query,invoice:undefined}});}
watch(()=>route.query.invoice,name=>{invoice.value=name?String(name):'';});
watch(()=>route.query.view,id=>{const next=tabs.some(([key])=>key===id)?id:'billing';if(next!==view.value)switchView(next);});
function changed(){refreshCounts();overviewVersion.value++;notice.value='Billing records updated.';if(view.value!=='billing' && view.value!=='collections')action(()=>loadList());}
function changeBranch(){refreshCounts();client.value=null;invoice.value='';editing.value=false;registering.value=false;clients.value=[];if(!['billing','collections'].includes(view.value))action(()=>loadList());}
onMounted(initialize);onBeforeUnmount(()=>{generation++;clearTimeout(searchTimer);controller?.abort();});
</script>
<template>
  <section class="billing-native">
    <header class="billing-workspace-head">
      <div class="billing-brand"><strong>LIFE CLINICS</strong><span>BILLING MODULE</span></div>
      <label v-if="bootstrap" class="billing-scope">Branch<select v-model="branch" :disabled="busy || editing || registering || !!invoice" @change="changeBranch"><option v-if="headOffice" value="">Head Office — All branches</option><option v-for="name in branches" :key="name">{{ name }}</option></select></label>
    </header>
    <nav class="billing-tabs" aria-label="Billing views">
      <button v-for="([id,label],index) in tabs" :key="id" :aria-current="view===id?'page':undefined" :disabled="busy || editing || registering || !!invoice" @click="switchView(id)"><span class="tab-icon" aria-hidden="true">{{ ['▣','▤','◷','▦','◇'][index] }}</span>{{ label }}<span v-if="id==='pending' && counts.pending!==null" class="billing-count">{{ counts.pending }}</span><span v-if="id==='approvals' && counts.approvals!==null" class="billing-count">{{ counts.approvals }}</span></button>
    </nav>
    <p v-if="warning" class="billing-notice tone-amber" role="status">{{ warning }}</p><ul v-if="stockReceipts.length"><li v-for="(receipt,index) in stockReceipts" :key="index">{{ receipt.name || receipt.stock_entry }} · {{ receipt.branch }} · {{ receipt.release_date }}</li></ul>
    <p v-if="offerWarning" class="billing-notice" role="status">{{ offerWarning }}</p><p v-if="notice" class="billing-notice tone-green" role="status">{{ notice }}</p>
    <div v-if="error" role="alert"><p>{{ error }}</p><button :disabled="busy" @click="bootstrap?(['billing','collections'].includes(view)?search():action(()=>loadList())):initialize()">Retry</button></div><p v-if="busy" class="billing-loading" role="status">Loading Billing…</p>
    <template v-if="bootstrap">
      <BillingDialog v-if="invoice" title="Invoice details" :can-close="!transactionBusy" @close="closeInvoice"><BillingInvoice :key="invoice" :name="invoice" :initial-action="invoiceAction" @busy-change="transactionBusy=$event" :bootstrap="bootstrap" :branches="branches" @close="closeInvoice" @changed="changed" /></BillingDialog>
      <template v-else-if="view==='billing'">
        <BillingDialog v-if="registering" title="Client registration" :can-close="!transactionBusy" @close="registering=false"><BillingRegistration @busy-change="transactionBusy=$event" :bootstrap="bootstrap" :branches="branches" :branch="branch" @cancel="registering=false" @registered="registered" /></BillingDialog>
        <BillingEditor v-else-if="editing && client" :client="client" :invoices="rows" :bootstrap="bootstrap" :branches="branches" :branch="branch" @cancel="editing=false" @created="created" />
        <template v-else>
          <section :class="client?'billing-mini-search':'billing-hero'">
            <template v-if="!client"><span class="billing-eyebrow">CLIENT BILLING</span><h2>Client billing</h2><p>Search by name, mobile number or client ID to begin.</p></template>
            <button v-else class="billing-secondary" :disabled="busy" @click="backToSearch">← Back to search</button>
            <form class="billing-search-form" @submit.prevent="search"><label>Search clients<input v-model="query" placeholder="Search client name / mobile / client ID…" autocomplete="off" @input="queueSearch"></label><button class="billing-primary" :disabled="busy">Search</button><button class="billing-secondary" type="button" :disabled="busy" @click="registering=true">Register client</button></form>
            <div v-if="clients.length" class="billing-search-results" aria-label="Client search results"><button v-for="p in clients" :key="p.name" :disabled="busy" @click="selectClient(p.name)"><span class="billing-avatar" aria-hidden="true">{{ (p.patient_name || 'C').split(' ').map(s=>s[0]).slice(0,2).join('') }}</span><span><strong>{{ p.patient_name }} · {{ p.name }}</strong><small>{{ p.mobile || 'No mobile' }} · {{ p.custom_branch || 'No branch' }}</small></span><span aria-hidden="true">→</span></button></div>
            <div v-else-if="searchPerformed && !busy && !client" class="billing-search-empty"><p>No client found for “{{ query }}”.</p><button @click="registering=true">Register a new client</button></div>
          </section>
          <BillingOverview v-if="!client" :key="branch+overviewVersion" :branch="branch" :branches="branches" :head-office="headOffice" @counts="counts.pending=$event" />
          <section v-if="!client && !clients.length" class="billing-empty"><span aria-hidden="true">◎</span><h3>Start with a client</h3><p>View their billing history, collect pending dues,<br>or create a new therapy plan and invoice.</p></section>
          <section v-if="client" class="billing-client-summary">
            <header class="billing-client-head"><span class="billing-avatar">{{ (client.patient_name || 'C').split(' ').map(s=>s[0]).slice(0,2).join('') }}</span><div><span class="billing-eyebrow">CLIENT SUMMARY</span><h2>{{ client.patient_name }}</h2><p>{{ client.name }} · {{ client.mobile || 'No mobile' }} · {{ client.custom_branch }}</p><p v-if="client.custom_lead">Lead {{ client.custom_lead }} · {{ client.custom_media }}</p></div><div v-if="clientTotals" class="billing-client-due"><span>Outstanding</span><strong>{{ money(clientTotals.due) }}</strong></div></header>
            <div v-if="clientTotals" class="billing-kpis"><article class="billing-kpi tone-blue"><h3>Lifetime billed</h3><strong>{{ money(clientTotals.billed) }}</strong></article><article class="billing-kpi tone-green"><h3>Lifetime paid</h3><strong>{{ money(Number(clientTotals.billed || 0)-Number(clientTotals.due || 0)) }}</strong></article><article class="billing-kpi tone-red"><h3>Outstanding</h3><strong>{{ money(clientTotals.due) }}</strong></article><article class="billing-kpi tone-amber"><h3>Total invoices</h3><strong>{{ clientTotals.count }}</strong></article></div>
            <div class="billing-client-actions"><button class="billing-primary" :disabled="busy" @click="editing=true">New bill</button><button :disabled="busy" @click="selectClient(client.name)">Refresh client</button></div>
            <p v-if="hasMore" class="billing-notice">Showing the latest 40 invoices. Use Recent bills for older invoices.</p>
            <section class="billing-panel"><header class="billing-section-head"><h3>Invoice history</h3><span class="billing-badge">{{ rows.length }} shown</span></header><div v-if="rows.length" class="table-wrap"><table><thead><tr><th>Invoice</th><th>Date</th><th>Branch</th><th>Total</th><th>Paid</th><th>Due</th><th>Status</th><th>Action</th></tr></thead><tbody><tr v-for="row in rows" :key="row.name"><td><strong>{{ row.name }}</strong></td><td>{{ row.posting_date }}</td><td>{{ row.branch }}</td><td>{{ money(row.grand_total) }}</td><td>{{ money(Number(row.grand_total)-Number(row.outstanding_amount)) }}</td><td class="billing-due">{{ money(row.outstanding_amount) }}</td><td><span class="billing-badge" :class="Number(row.docstatus)===0?'tone-grey':Number(row.outstanding_amount)>0?'tone-amber':'tone-green'">{{ row.status }}</span></td><td><button @click="openInvoice(row.name)">Open invoice</button><button v-if="Number(row.docstatus)===1 && Number(row.outstanding_amount)>0" class="billing-primary" @click="openInvoice(row.name,'collect')">Collect payment</button></td></tr></tbody></table></div><div v-else class="billing-empty"><h3>No invoices yet</h3><p>Create this client's first bill to get started.</p></div></section>
          </section>
        </template>
      </template>
      <BillingCollections v-else-if="view==='collections'" :key="branch" :bootstrap="bootstrap" :branch="branch" />
      <template v-else>
        <header class="billing-list-head"><div><h2>{{ view==='recent'?'Recent bills':view==='pending'?'Pending bills — month wise':'Discount approvals' }}</h2><p>{{ view==='approvals'?'Review requests and raise the next approval.':'Track invoices and balances for your selected branch.' }}</p></div><span class="billing-badge tone-green">{{ branch || 'Head Office — All branches' }}</span></header>
        <form class="billing-filter-bar" @submit.prevent="action(()=>loadList())"><label>Search invoices / clients / mobile<input v-model="listQuery" placeholder="Name, invoice or mobile"></label><label v-if="view!=='approvals'">Status<select v-model="status"><option value="">All statuses</option><option v-for="s in ['Draft','Unpaid','Partly Paid','Paid','Overdue']" :key="s">{{ s }}</option></select></label><label>From<input v-model="from" type="date" required></label><label>To<input v-model="to" type="date" required></label><label v-if="view==='pending'">Minimum due<select v-model.number="minimumDue"><option :value="0">Any due amount</option><option :value="5000">Due ≥ ₹5,000</option><option :value="20000">Due ≥ ₹20,000</option><option :value="50000">Due ≥ ₹50,000</option></select></label><button class="billing-primary" :disabled="busy">Apply</button><div v-if="view==='recent'" class="billing-presets"><button v-for="[id,label] in [['today','Today'],['yesterday','Yesterday'],['this_month','This business month'],['last_month','Last business month']]" :key="id" type="button" :disabled="busy" @click="recentPreset(id)">{{ label }}</button></div><button v-if="view==='approvals'" type="button" :disabled="busy" @click="resetDates">Reset dates</button></form>
        <section v-if="view==='approvals'" class="billing-next-approval"><div><h3>Raise the next approval</h3><p>L1 → L2 → L3 · up to 15% combined, or L4 final amount</p></div><label>Invoice number<input v-model.trim="nextInvoice" placeholder="SINV-26-xxxxx"></label><button class="billing-primary" :disabled="!nextInvoice || busy" @click="openInvoice(nextInvoice,'request')">Request next approval</button><button :disabled="!nextInvoice || busy" @click="viewInvoiceBill(nextInvoice)">View bill</button></section>
        <p v-if="rows.length && view!=='approvals'" class="billing-list-summary">This page: {{ rows.length }} invoices · Total <strong>{{ money(rows.reduce((sum,row)=>sum+Number(row.grand_total || 0),0)) }}</strong> · Due <strong>{{ money(rows.reduce((sum,row)=>sum+Number(row.outstanding_amount || 0),0)) }}</strong></p>
        <div v-if="!busy && !rows.length" class="billing-empty"><span aria-hidden="true">{{ view==='approvals'?'◇':'▤' }}</span><h3>No {{ view==='approvals'?'pending discount requests':'invoices' }} found.</h3><p>Try another date range or search.</p></div>
        <BillingPendingGroups v-if="view==='pending' && rows.length" :rows="displayed" @open="openInvoice($event)" @collect="openInvoice($event,'collect')" />
        <div v-else-if="rows.length" class="table-wrap" tabindex="0" aria-label="Billing records" role="region"><table><thead><tr><th>Invoice</th><th>{{ view==='approvals'?'Requested by / approver':'Client' }}</th><th>{{ view==='approvals'?'Level':'Date / branch' }}</th><th>Total</th><th>{{ view==='approvals'?'Requested discount':'Paid' }}</th><th v-if="view!=='approvals'">Due</th><th>{{ view==='approvals'?'Reason':'Status' }}</th><th>Action</th></tr></thead><tbody><tr v-for="row in displayed" :key="row.name"><td><strong>{{ row.linked_invoice || row.name }}</strong><small v-if="row.custom_remarks_for_office_use">{{ row.custom_remarks_for_office_use }}</small></td><td><strong>{{ row.requested_by || row.patient_name }}</strong><small>{{ row.selected_approver || row.patient }}</small></td><td>{{ row.approval_level || row.posting_date }}<small v-if="view!=='approvals'">{{ row.branch }}</small></td><td>{{ money(row.bill_total || row.grand_total) }}</td><td>{{ view==='approvals'?(Number(row.requested_final_amount)>0?money(row.requested_final_amount)+' final incl. GST':row.requested_discount_pct+'%'):money(Number(row.grand_total)-Number(row.outstanding_amount)) }}</td><td v-if="view!=='approvals'" class="billing-due">{{ money(row.outstanding_amount) }}</td><td><span v-if="view!=='approvals'" class="billing-badge" :class="Number(row.docstatus)===0?'tone-grey':Number(row.outstanding_amount)>0?'tone-amber':'tone-green'">{{ row.status }}</span><span v-else>{{ row.reason }}</span></td><td><button @click="openInvoice(row.linked_invoice || row.name)">Open invoice</button><template v-if="view==='approvals' && canApproveRequest(row,bootstrap.user || session.user)"><button class="billing-primary" @click="openInvoice(row.linked_invoice,'approve:'+row.name)">Approve</button><button class="billing-danger" @click="openInvoice(row.linked_invoice,'reject:'+row.name)">Reject</button></template><button v-else-if="view!=='approvals' && Number(row.docstatus)===1 && Number(row.outstanding_amount)>0" class="billing-primary" @click="openInvoice(row.name,'collect')">Collect payment</button></td></tr></tbody></table></div>
        <footer class="billing-pagination"><button :disabled="busy || page===1" @click="changePage(page-1)">Previous</button><span>Page {{ page }} · up to 40 records per page</span><button :disabled="busy || !hasMore" @click="changePage(page+1)">Next</button></footer>
      </template>
    </template>
  </section>
</template>
