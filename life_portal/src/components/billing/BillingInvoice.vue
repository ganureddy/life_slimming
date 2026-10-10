<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { billingCall, getBillingDoc, invoicePdfUrl, invoicePrintViewUrl, setBillingValue } from '../../api/billing';
import { canApproveRequest, invoiceCosts } from '../../lib/billing';
import { indiaStamp } from '../../lib/cc';
import { session } from '../../lib/session';
import BillingPayments from './BillingPayments.vue';
const props = defineProps({ name: String, bootstrap: Object, branches: Array, initialAction: String });
const emit = defineEmits(['changed', 'close', 'busy-change']);
const doc = ref(null), requests = ref([]), busy = ref(false), error = ref(''), notice = ref(''), collecting = ref(false), mobile = ref(''), approval = ref(null), approvedAmount = ref(0), rejection = ref(null), reason = ref(''), requesting = ref(false), selections = ref([]), finalApprover = ref(''), finalAmount = ref(0), requestReason = ref(''), confirmSubmit = ref(false),paymentBusy=ref(false),printFormat=ref(props.bootstrap?.latest_invoice_print_format || 'Consultaion Patient Sales Invoice');
watch(()=>busy.value || paymentBusy.value,value=>emit('busy-change',value));
const currentUser=computed(()=>props.bootstrap.user || session.user);
const money = v => new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(Number(v || 0));
const costs = computed(()=>invoiceCosts(doc.value || {}));
const hasCosts = computed(()=>['custom_product_cost','custom_clinical_operational_cost','custom_total_cost','custom_net_profit'].some(key=>doc.value?.[key]!=null));
const usedLevels = computed(()=>new Set(requests.value.filter(r=>['Pending','Approved'].includes(r.status)).map(r=>r.approval_level)));
const canSubmit = computed(()=>doc.value && Number(doc.value.docstatus)===0 && !doc.value.discount_locked && !requests.value.some(r=>r.status==='Pending'));
async function refresh() {
  const [invoice,boot] = await Promise.all([getBillingDoc('Sales Invoice',props.name),billingCall('lifescc_billing_bootstrap',{invoice_name:props.name})]);
  if (!props.branches.includes(invoice.branch)) throw new Error('This invoice is outside your available branches.');
  if (!Array.isArray(boot.discount_requests)) throw new Error('Complete discount approval history could not be loaded.');
  doc.value=invoice;requests.value=boot.discount_requests;printFormat.value=boot.latest_invoice_print_format || props.bootstrap?.latest_invoice_print_format || 'Consultaion Patient Sales Invoice';
  if (invoice.patient) { const client=await getBillingDoc('Patient',invoice.patient);mobile.value=client.mobile || ''; }
}
async function action(fn) {if(busy.value || paymentBusy.value)return;busy.value=true;error.value='';try{await fn();}catch(e){error.value=e.message;}finally{busy.value=false;}}
function load(){return action(refresh);}
function submit(){return action(async()=>{await refresh();if(!canSubmit.value)throw new Error('Resolve pending discounts before submitting.');await billingCall('lifescc_billing_submit_invoice',{invoice_name:props.name});confirmSubmit.value=false;notice.value='Invoice submitted.';await refresh();collecting.value=Number(doc.value.outstanding_amount)>0;emit('changed');});}
function approve(){return action(async()=>{
  const name=approval.value.name;await refresh();const row=requests.value.find(r=>r.name===name);
  if(!row || !canApproveRequest(row,currentUser.value))throw new Error('This approval is no longer available to you.');
  const args={request_name:name,invoice_name:props.name};
  if(row.approval_level==='L4' || Number(row.requested_final_amount)>0){if(!(approvedAmount.value>0) || approvedAmount.value>=Number(doc.value.grand_total))throw new Error('Final amount including GST must be positive and below the current total.');args.approved_amount=Number(approvedAmount.value);}
  await billingCall('apply_invoice_discount_net_final_v2',args);approval.value=null;notice.value='Discount approved.';await refresh();emit('changed');
});}
function reject(){return action(async()=>{
  if(!reason.value.trim())throw new Error('Enter a rejection reason.');
  const name=rejection.value.name;await refresh();const row=requests.value.find(r=>r.name===name);
  if(!row || !canApproveRequest(row,currentUser.value))throw new Error('This request is no longer available to you.');
  await setBillingValue('Discount Approval Request',name,{status:'Rejected',rejection_reason:reason.value,approved_by:currentUser.value,approved_at:indiaStamp()});
  await refresh();const earlier=requests.value.some(r=>r.status==='Approved');
  await setBillingValue('Sales Invoice',props.name,{discount_locked:0,approval_workflow_status:earlier?'Approved':'Rejected'});
  rejection.value=null;reason.value='';notice.value='Request rejected.';await refresh();emit('changed');
});}
function requestDiscount(){return action(async()=>{
  await refresh();if(Number(doc.value.docstatus)!==0)throw new Error('Discount requests require a draft invoice.');
  if(!requestReason.value.trim())throw new Error('Enter a discount reason.');
  if(finalApprover.value){
    if(usedLevels.value.has('L4'))throw new Error('L4 is already pending or approved.');
    if(!(finalAmount.value>0) || finalAmount.value>=Number(doc.value.grand_total))throw new Error('L4 amount must be below the current total, including GST.');
    await billingCall('create_discount_approval_request',{invoice_name:props.name,selected_approver:finalApprover.value,approval_level:'L4',requested_discount_pct:0,requested_final_amount:Number(finalAmount.value),reason:requestReason.value});
  }else{
    const chosen=selections.value.filter(s=>s.user);
    if(!chosen.length)throw new Error('Select at least one approver.');
    const approved=requests.value.filter(r=>r.status==='Approved' && r.approval_level!=='L4').reduce((sum,r)=>sum+Number(r.approved_discount_pct || r.requested_discount_pct || 0),0);
    const pending=requests.value.filter(r=>r.status==='Pending' && r.approval_level!=='L4').reduce((sum,r)=>sum+Number(r.requested_discount_pct || 0),0);
    if(new Set(chosen.map(s=>s.level)).size!==chosen.length || new Set(chosen.map(s=>s.user)).size!==chosen.length)throw new Error('Select one unique approver per level.');
    for(const s of chosen)if(usedLevels.value.has(s.level) || !(s.pct>=0.5) || s.pct>5)throw new Error('Each unused level must request between 0.5% and 5%.');
    if(approved+pending+chosen.reduce((sum,s)=>sum+Number(s.pct),0)>15.000001)throw new Error('Combined percentage discounts cannot exceed 15%.');
    await billingCall('create_multiple_discount_approval_requests_v2',{invoice_name:props.name,requests:JSON.stringify(chosen.map(s=>({selected_approver:s.user,approval_level:s.level,requested_discount_pct:Number(s.pct),reason:requestReason.value})))});
  }
  requesting.value=false;notice.value='Discount request sent.';await refresh();emit('changed');
});}
function beginRequest(){selections.value=['L1','L2','L3'].map(level=>({level,user:'',pct:5}));finalApprover.value='';finalAmount.value=0;requestReason.value='';requesting.value=true;}
function viewBill(){window.open(invoicePrintViewUrl(props.name,printFormat.value),'_blank','noopener,noreferrer');}
function pdf(){return action(async()=>{await refresh();if(String(doc.value.posting_date).slice(0,10)!==indiaStamp().slice(0,10))throw new Error('PDF download is available only for bills posted today.');window.open(invoicePdfUrl(props.name,printFormat.value),'_blank','noopener,noreferrer');});}
onMounted(async()=>{
 await load();if(!doc.value)return;
 const [kind,name]=(props.initialAction || '').split(':');
 if(kind==='collect' && Number(doc.value.docstatus)===1 && Number(doc.value.outstanding_amount)>0)collecting.value=true;
 if(kind==='request' && Number(doc.value.docstatus)===0)beginRequest();
 const row=requests.value.find(r=>r.name===name);
 if(row && canApproveRequest(row,currentUser.value)){if(kind==='approve'){approval.value=row;approvedAmount.value=Number(row.requested_final_amount || 0);}if(kind==='reject')rejection.value=row;}
});
</script>
<template><section class="billing-panel billing-invoice"><header class="billing-invoice-head"><div><span class="billing-eyebrow">INVOICE WORKSPACE</span><h2>Invoice {{ name }}</h2></div><button :disabled="busy || paymentBusy" @click="emit('close')">Close invoice</button></header><p v-if="error" role="alert">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p><p v-if="busy" role="status">Loading invoice…</p><button :disabled="busy || paymentBusy" @click="load">Refresh invoice</button>
<template v-if="doc"><p>{{ doc.patient_name }} · {{ doc.branch }} · {{ doc.posting_date }} · {{ doc.status }} · {{ Number(doc.docstatus)===0?'Draft':Number(doc.docstatus)===1?'Submitted':'Cancelled' }}</p><div class="billing-invoice-amounts"><article class="billing-kpi tone-blue"><h3>Grand total</h3><strong>{{ money(doc.grand_total) }}</strong></article><article class="billing-kpi tone-green"><h3>Paid</h3><strong>{{ money(Number(doc.grand_total)-Number(doc.outstanding_amount)) }}</strong></article><article class="billing-kpi tone-red"><h3>Outstanding</h3><strong>{{ money(doc.outstanding_amount) }}</strong></article></div><h3 class="billing-subheading">Invoice line items</h3><div class="table-wrap"><table><thead><tr><th>Item</th><th>Quantity</th><th>Rate</th><th>Amount</th></tr></thead><tbody><tr v-for="item in doc.items" :key="item.name"><td>{{ item.item_name || item.item_code }}</td><td>{{ item.qty }}</td><td>{{ money(item.rate) }}</td><td>{{ money(item.amount) }}</td></tr></tbody></table></div>
<section class="billing-summary-breakdown"><h3>Invoice breakdown</h3><dl><dt>Net total</dt><dd>{{ money(doc.net_total) }}</dd><template v-if="Number(doc.discount_amount)"><dt>Discount</dt><dd>{{ money(doc.discount_amount) }}</dd></template><dt>GST</dt><dd>{{ money(doc.total_taxes_and_charges) }}</dd><dt>Grand total</dt><dd>{{ money(doc.grand_total) }}</dd></dl><p v-if="doc.custom_doctor_consultant_name">Doctor: {{ doc.custom_doctor_consultant_name }}</p><p v-if="doc.custom_therapy_plan">Therapy plan: {{ doc.custom_therapy_plan }}</p></section>
<details v-if="hasCosts" class="billing-cost-details"><summary>Cost justification</summary><div class="table-wrap" tabindex="0" role="region" aria-label="Invoice cost justification"><table><thead><tr><th>Component</th><th>Amount</th><th>Share of selling price</th></tr></thead><tbody><tr v-for="[label,value] in costs" :key="label"><th scope="row">{{ label }}</th><td>{{ money(value) }}</td><td>{{ Number(doc.grand_total)?(value/Number(doc.grand_total)*100).toFixed(2):'0.00' }}%</td></tr></tbody></table></div></details>
<p v-if="doc.custom_remarks_for_office_use">Office remarks: {{ doc.custom_remarks_for_office_use }}</p>
<div class="billing-invoice-actions"><button :disabled="busy || paymentBusy" @click="viewBill">View bill</button><button :disabled="busy || paymentBusy" @click="pdf">Download PDF</button><button v-if="canSubmit" :disabled="busy || paymentBusy" @click="confirmSubmit=true">Submit invoice</button><button v-if="Number(doc.docstatus)===0" :disabled="busy || paymentBusy" @click="beginRequest">Request discount approval</button><button v-if="Number(doc.docstatus)===1 && Number(doc.outstanding_amount)>0 && !collecting" :disabled="busy || paymentBusy" @click="collecting=true">Collect payment</button></div>
<div v-if="confirmSubmit" class="billing-panel"><h3>Confirm invoice submission</h3><p>{{ money(doc.grand_total) }} · Once submitted, this invoice is final.</p><button :disabled="busy || paymentBusy" @click="submit">Confirm submit</button><button :disabled="busy || paymentBusy" @click="confirmSubmit=false">Cancel submission</button></div>
<h3 class="billing-subheading">Discount approval history</h3><p v-if="!requests.length">No discount requests.</p><div v-for="r in requests" :key="r.name" class="billing-panel billing-approval-entry"><p>{{ r.approval_level }} · {{ r.status }} · {{ r.selected_approver }} · {{ r.creation }}</p><p>{{ r.requested_final_amount>0?money(r.requested_final_amount)+' final incl. GST':r.requested_discount_pct+'%' }} · {{ r.reason }}</p><p v-if="r.approved_by">Approved by {{ r.approved_by }} · {{ r.approved_at }}</p><p v-if="r.rejection_reason">{{ r.rejection_reason }}</p><template v-if="canApproveRequest(r,currentUser)"><button :disabled="busy || paymentBusy" @click="approval=r;approvedAmount=Number(r.requested_final_amount || 0)">Approve discount</button><button :disabled="busy || paymentBusy" @click="rejection=r;reason=''">Reject discount</button></template></div>
<div v-if="approval" class="billing-panel"><h3>Confirm {{ approval.approval_level }} approval</h3><p>Current grand total {{ money(doc.grand_total) }} including GST.</p><label v-if="approval.approval_level==='L4'">Final invoice amount including GST<input v-model.number="approvedAmount" type="number" min=".01" step=".01"></label><p v-else>Requested discount {{ approval.requested_discount_pct }}%</p><button :disabled="busy || paymentBusy" @click="approve">Confirm approval</button><button :disabled="busy || paymentBusy" @click="approval=null">Cancel approval</button></div>
<div v-if="rejection" class="billing-panel"><label>Rejection reason<textarea v-model="reason"></textarea></label><button :disabled="busy || paymentBusy" @click="reject">Confirm rejection</button><button :disabled="busy || paymentBusy" @click="rejection=null">Cancel rejection</button></div>
<div v-if="requesting" class="billing-panel"><h3>Request further discount</h3><div v-for="s in selections" :key="s.level" class="billing-fields"><label>{{ s.level }} approver<select v-model="s.user" :disabled="usedLevels.has(s.level) || !!finalApprover"><option value="">Not selected</option><option v-for="a in bootstrap.approvers.filter(a=>a.approval_level===s.level)" :key="a.user" :value="a.user">{{ a.full_name }}</option></select></label><label>Percentage<input v-model.number="s.pct" :disabled="usedLevels.has(s.level) || !!finalApprover" type="number" min="0.5" max="5" step="0.5"></label></div><label>L4 approver<select v-model="finalApprover" :disabled="usedLevels.has('L4')"><option value="">Use percentage levels</option><option v-for="a in bootstrap.approvers.filter(a=>a.approval_level==='L4')" :key="a.user" :value="a.user">{{ a.full_name }}</option></select></label><label v-if="finalApprover">Final amount including GST<input v-model.number="finalAmount" type="number" min=".01" step=".01"></label><label>Reason<textarea v-model="requestReason"></textarea></label><button :disabled="busy || paymentBusy" @click="requestDiscount">Send discount request</button><button :disabled="busy || paymentBusy" @click="requesting=false">Cancel request</button></div>
<BillingPayments v-if="collecting" :invoice="doc" :bootstrap="bootstrap" :mobile="mobile" @busy-change="paymentBusy=$event" @recorded="emit('changed')" @close="collecting=false;load()" />
</template></section></template>
