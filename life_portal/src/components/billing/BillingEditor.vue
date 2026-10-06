<script setup>
import { computed, reactive, ref, watch } from 'vue';
import { billingCall, billingList } from '../../api/billing';
import { billTotals, eligibleOffers, offerPrice, practitionersFor, adjustBillingRates } from '../../lib/billing';
import BillingDialog from './BillingDialog.vue';
import { LIFERISE_PACKAGES } from '../../lib/billing-packages';
import { indiaStamp } from '../../lib/cc';
const props = defineProps({ client: Object, bootstrap: Object, branches: Array, branch: String, invoices: {type:Array,default:()=>[]} });
const sourceLocked=!!props.client.custom_lead || String(props.client.custom_media || '').trim().toLowerCase()==='call center' || props.invoices.some(i=>['Paid','Partly Paid','Overdue'].includes(i.status));
const hasLead=!!props.client.custom_lead || String(props.client.custom_media||'').trim().toLowerCase()==='call center';
const sourceLockMessage=hasLead?'🔗 Call Center lead → source set to Call Center for this bill.':sourceLocked?'🔒 Existing client (has paid bills) → source locked to Existing Customer.':'Select how this client came in. Choose Call Center for a call center lead.';
const initialSource=props.client.custom_lead || String(props.client.custom_media || '').toLowerCase()==='call center'?'Call Center':sourceLocked?'Existing Customer':'';
const emit = defineEmits(['created', 'cancel']);
const form = reactive({ branch: props.branch || props.client.custom_branch || props.branches[0], practitioner: '', plan_media: initialSource, reference_employee: '', reference_client: '', reference_client_name: '', sharing_incentive: false, incentive_employee: '', office_remarks: '', discount_pct: 0, discount_final_amount: 0, discount_approver: '', discount_reason: '', pkg_price: 0, pkg_name: '', pkg_tc: '' });
const lines = ref([{therapy_type:'',therapyQuery:'',therapyOpen:false,no_of_sessions:1,rate:0,baseRate:0,offer_rule:'',use_offer:0}]), comps = ref([]), mode = ref('individual'), template = ref(''), couponCode = ref(''), coupon = ref(null), couponStatus=ref(''),error = ref(''), busy = ref(false), preview = ref(false), createdInvoice = ref(''), createAttempted = ref(false), refQuery = ref(''), refClients = ref([]), refSearchDone=ref(false), target = ref(0),adjustNote=ref(''),discountEnabled=ref(false),compEnabled=ref(false),category=ref(''),practitionerQuery=ref(''),practitionerOpen=ref(false),referenceClientEnabled=ref(false),referenceEmployeeEnabled=ref(false);
const discountRequests = ref(['L1','L2','L3'].map(level => ({ level, enabled:false, approver:'', pct:5 })));
const discountReason = ref('');
const practitioners = computed(() => practitionersFor(props.bootstrap.practitioners, form.branch));
const totals = computed(() => billTotals(lines.value, { coupon: coupon.value, discountPct: form.discount_pct, packagePrice: form.pkg_price }));
const compSlabInfo=computed(()=>{const subtotal=totals.value.subtotal;if(subtotal<=25000)return null;if(subtotal<=100000)return {label:'S1',rate:.04};if(subtotal<=200000)return {label:'S2',rate:.075};return {label:'S3',rate:.1};});
const compLimit = computed(() => Number((totals.value.subtotal*(compSlabInfo.value?.rate||0)).toFixed(2)));
const money = value => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(value || 0);
const packageOnly = item => Number(item.pkg_only) === 1 || /^(lif erise|liferise|ih)(?:\s|-|$)|-(?:sle|aage)$/i.test(item.n || item.name || '');
const catalog = computed(() => (props.bootstrap.therapies || []).filter(t => mode.value === 'package' || (Number(t.show_in_billing) === 1 && !packageOnly(t))));
function approversForLevel(level){const rows=(props.bootstrap.approvers||[]).filter(a=>a.approval_level===level);if(level==='L1'&&props.bootstrap.user&&!rows.some(a=>a.user===props.bootstrap.user))rows.unshift({user:props.bootstrap.user,full_name:props.bootstrap.user,approval_level:'L1',designation:'Self'});return rows;}
const filteredCatalog=computed(()=>catalog.value.filter(t=>!category.value || (t.category || 'Other')===category.value));
const remarksCount=computed(()=>form.office_remarks.trim().split(/\s+/).filter(Boolean).length);
const compUsed=computed(()=>comps.value.reduce((sum,c)=>sum+Number(c.qty)*Number(c.comp_price),0));
const today = () => indiaStamp().slice(0, 10);
watch(() => form.branch, () => { form.practitioner = ''; practitionerQuery.value=''; practitionerOpen.value=false; });
watch(() => form.plan_media, value => {if(value!=='Reference'){referenceClientEnabled.value=false;referenceEmployeeEnabled.value=false;form.reference_employee='';form.reference_client='';form.reference_client_name='';refQuery.value='';refClients.value=[];}});
watch(() => totals.value.subtotal, value => { if (value <= 25000) comps.value = []; });
async function action(fn) { if (busy.value) return; busy.value = true; error.value = ''; try { await fn(); } catch (e) { error.value = e.message; } finally { busy.value = false; } }
function addLine() { lines.value.push({ therapy_type: '', therapyQuery: '', therapyOpen: false, no_of_sessions: 1, rate: 0, baseRate: 0, offer_rule: '', use_offer: 0 }); }
function therapyMatches(line) {
  const query = String(line.therapyQuery || '').trim().toLowerCase();
  return filteredCatalog.value.filter(t => {
    const name = t.n || t.name || '';
    return !lines.value.some(other => other !== line && other.therapy_type === name) && (!query || name.toLowerCase().includes(query));
  }).slice(0, 50);
}
function chooseTherapy(line, therapy) {
  line.therapy_type = therapy.n || therapy.name;
  line.therapyQuery = line.therapy_type;
  line.therapyOpen = false;
  selectTherapy(line);
}
function toggleOffer(line, offer, enabled) {
  line.offer_rule = enabled ? offer.name : '';
  applyOffer(line);
}
function selectTherapy(line) {
  const item = props.bootstrap.therapies.find(t => t.n === line.therapy_type || t.name === line.therapy_type);
  if (item) line.therapyQuery = item.n || item.name;
  line.baseRate = Number(item?.rate || 0); line.rate = line.baseRate; line.offer_rule = ''; line.use_offer = 0;
}
function offers(line) { const item = props.bootstrap.therapies.find(t => t.n === line.therapy_type || t.name === line.therapy_type); return eligibleOffers(props.bootstrap.offers, item?.item, Number(line.no_of_sessions), today()); }
function applyOffer(line) { const offer = offers(line).find(o => o.name === line.offer_rule); line.use_offer = offer ? 1 : 0; line.rate = offer ? offerPrice(offer, line.baseRate) : line.baseRate; }
function setMode(value){ mode.value=value; }
function choosePractitioner(p){form.practitioner=p.name;practitionerQuery.value=p.practitioner_name;practitionerOpen.value=false;}
const filteredPractitioners=computed(()=>practitioners.value.filter(p=>!practitionerQuery.value||String(p.practitioner_name||'').toLowerCase().includes(practitionerQuery.value.toLowerCase())).slice(0,50));
function setReferenceKind(kind,enabled){if(kind==='client'){referenceClientEnabled.value=enabled;if(!enabled){form.reference_client='';form.reference_client_name='';refQuery.value='';refClients.value=[];refSearchDone.value=false;}}else{referenceEmployeeEnabled.value=enabled;if(!enabled)form.reference_employee='';}}
function loadTemplate() {
  const selected = props.bootstrap.templates.find(t => t.name === template.value);
  if (!selected?.lines?.length) { error.value = 'This template has no therapy lines.'; return; }
  lines.value = selected.lines.map(l => {const baseRate=Number(l.rate || props.bootstrap.therapies.find(t=>t.n===l.therapy_type || t.name===l.therapy_type)?.rate || 0);return {...l,therapyQuery:l.therapy_type,therapyOpen:false,no_of_sessions:Number(l.no_of_sessions||1),rate:baseRate,baseRate,use_offer:0,offer_rule:''};});
  const fixed = LIFERISE_PACKAGES[selected.name];
  form.pkg_price = Number(fixed?.price || selected.offer_price || 0); form.pkg_name = selected.plan_name || selected.name; form.pkg_tc = fixed?.tc || '';
}
function resetRates() { for (const line of lines.value) { selectTherapy(line); } }
function adjust() {
  error.value='';adjustNote.value='';
  try{
    if(form.pkg_price>0)throw new Error('This package has a fixed net price. Clear the template before adjusting individual prices.');
    const active=lines.value.filter(l=>l.therapy_type);const updated=adjustBillingRates(active,props.bootstrap.therapies,Number(target.value),{discountPct:form.discount_pct,coupon:coupon.value});let n=0;lines.value=lines.value.map(l=>l.therapy_type?updated[n++]:l);
    adjustNote.value='Adjusted grand total: '+money(totals.value.total)+' including GST. All rates remain within their permitted bands.';
  }catch(e){error.value=e.message;}
}
function clearTemplate(){lines.value=[];template.value='';form.pkg_price=0;form.pkg_name='';form.pkg_tc='';adjustNote.value='';addLine();}
function toggleDiscount(){if(!discountEnabled.value){discountRequests.value.forEach(r=>{r.enabled=false;r.approver='';r.pct=5;});discountReason.value='';form.discount_pct=0;form.discount_final_amount=0;form.discount_approver='';form.discount_reason='';}}
function lineInfo(line){return props.bootstrap.therapies.find(t=>t.n===line.therapy_type || t.name===line.therapy_type);}

function addComp() { comps.value.push({ item_code: '', item_name: '', itemQuery:'', itemOpen:true, qty: 1, comp_price: 0, max_qty_allowed: 0 }); }
function selectComp(comp) { const item = props.bootstrap.comp_items.find(i => i.item_code === comp.item_code); Object.assign(comp, { item_name: item?.item_name || '', itemQuery:item?.item_name||'', comp_price: Number(item?.rate || 0), max_qty_allowed: Number(item?.max_qty || 0) }); }
function clampCompQty(comp){if(comp.max_qty_allowed>0&&Number(comp.qty)>comp.max_qty_allowed)comp.qty=comp.max_qty_allowed;}
function checkCoupon() { return action(async () => {
  coupon.value = null;
  couponStatus.value='Checking…';
  const result = await billingCall('validate_coupon', couponCode.value ? { coupon_code: couponCode.value } : { mobile: props.client.mobile });
  if (Number(result.valid) !== 1) {couponStatus.value='✕ '+(result.error || 'Coupon not valid');return;}
  coupon.value = result; couponCode.value = result.coupon_code; couponStatus.value=`✓ ${result.discount_type==='Fixed Amount'?money(result.discount_value)+' off':result.discount_value+'% off'} coupon applied for ${result.client_name||'client'} (valid till ${result.valid_until||''})`;
}); }
function searchReference() { return action(async () => {const query=refQuery.value.trim();if(query.length<3){refClients.value=[];refSearchDone.value=false;return;}const digits=query.replace(/\D/g,'');const filters=digits.length>=4?[['mobile','like','%'+digits+'%']]:[['patient_name','like','%'+query+'%']];refClients.value = await billingList('Patient',filters,['name','patient_name','mobile','custom_branch'],{limit:12});refSearchDone.value=true; }); }
let referenceSearchTimer;
function scheduleReferenceSearch(){clearTimeout(referenceSearchTimer);form.reference_client='';form.reference_client_name='';refSearchDone.value=false;if(referenceClientEnabled.value)referenceSearchTimer=setTimeout(searchReference,280);}
function compMatches(comp){const q=String(comp.itemQuery||'').toLowerCase();return (props.bootstrap.comp_items||[]).filter(i=>(`${i.item_name} ${i.item_code}`).toLowerCase().includes(q)).slice(0,50);}
function searchComp(comp){comp.item_code='';comp.comp_price=0;comp.max_qty_allowed=0;comp.itemQuery=comp.item_name;comp.itemOpen=true;}
function limitRemarks(){const words=form.office_remarks.trim().split(/\s+/).filter(Boolean);if(words.length>400)form.office_remarks=words.slice(0,400).join(' ');}
function validate() {
  if (!props.branches.includes(form.branch)) throw new Error('Select a permitted branch.');
  if (!practitioners.value.some(p => p.name === form.practitioner)) throw new Error('Select a consultation employee for this branch.');
  if (!form.plan_media) throw new Error('Select the source / media.');
  if (form.plan_media === 'Reference' && !form.reference_employee && !form.reference_client) throw new Error('Select the referring employee or client.');
  if (form.sharing_incentive && !form.incentive_employee) throw new Error('Select an incentive employee.');
  const activeLines=lines.value.filter(l=>l.therapy_type);
  if (!activeLines.length || activeLines.some(l => !(Number(l.no_of_sessions) > 0) || !Number.isInteger(Number(l.no_of_sessions)) || !(Number(l.rate) > 0))) throw new Error('Add valid therapies, session quantities and rates.');
  if (new Set(activeLines.map(l => l.therapy_type)).size !== activeLines.length) throw new Error('A therapy may only be selected once.');
  for (const line of activeLines) {
    const item = props.bootstrap.therapies.find(t => t.n === line.therapy_type || t.name === line.therapy_type);
    if (!item || (mode.value !== 'package' && packageOnly(item))) throw new Error('Package-only therapies require a template.');
    if (!line.use_offer && mode.value !== 'package' && ((Number(item.min) && line.rate < Number(item.min)) || (Number(item.max) && line.rate > Number(item.max)))) throw new Error(`Rate for ${line.therapy_type} is outside its permitted range.`);
    if (line.use_offer && !offers(line).some(o => o.name === line.offer_rule)) throw new Error('An offer is no longer eligible for its quantity.');
  }
  const used = comps.value.reduce((sum, c) => sum + Number(c.qty) * Number(c.comp_price), 0);
  if (used > compLimit.value) throw new Error('Complimentary items exceed the slab limit.');
  const counts = new Map();
  for (const c of comps.value) {
    counts.set(c.item_code, (counts.get(c.item_code) || 0) + Number(c.qty));
    if (!c.item_code || !Number.isInteger(Number(c.qty)) || c.qty <= 0 || (c.max_qty_allowed > 0 && counts.get(c.item_code) > c.max_qty_allowed)) throw new Error('Check complimentary item quantities.');
  }
  if (form.office_remarks.trim().split(/\s+/).filter(Boolean).length > 400) throw new Error('Office remarks may contain at most 400 words.');
  const selectedDiscounts=discountRequests.value.filter(r=>r.enabled);
  if (discountEnabled.value && !selectedDiscounts.length) throw new Error('Select at least one discount approval level.');
  if (selectedDiscounts.some(r=>!r.approver)) throw new Error('Select an approver for every selected level.');
  if (new Set(selectedDiscounts.map(r=>r.approver)).size!==selectedDiscounts.length) throw new Error('Select a unique approver for each level.');
  if (selectedDiscounts.some(r=>!(Number(r.pct)>=0.5) || Number(r.pct)>5)) throw new Error('Each level must request between 0.5% and 5%.');
  if (selectedDiscounts.reduce((sum,r)=>sum+Number(r.pct),0)>15) throw new Error('L1 + L2 + L3 combined discount cannot exceed 15%.');
  if (discountEnabled.value && !discountReason.value.trim()) throw new Error('Enter the discount reason.');
  if (coupon.value && Number(coupon.value.min_spend) > totals.value.subtotal) throw new Error('The bill does not meet the coupon minimum spend.');
  if (totals.value.subtotal && (totals.value.couponAmount / totals.value.subtotal * 100 + selectedDiscounts.reduce((sum,r)=>sum+Number(r.pct),0)) > 15) throw new Error('Coupon and percentage discounts cannot exceed 15%.');
}
function review() { error.value = ''; if(!lines.value.some(l=>l.therapy_type&&Number(l.no_of_sessions)>0)){error.value='Add at least one therapy line';return;}preview.value = true; }
function printPreview(){window.print();}
function create() { return action(async () => {
  validate();
  let invoice = createdInvoice.value;
  if (!invoice) {
    if (createAttempted.value) throw new Error('The previous creation result is uncertain. Check Recent bills before creating another invoice.');
    const firstDiscount=discountRequests.value.find(r=>r.enabled);
    const payload = { ...form, discount_approver:firstDiscount?.approver || '', discount_pct:Number(firstDiscount?.pct || 0), discount_reason:firstDiscount?discountReason.value:'', discount_final_amount:0, patient: props.client.name, draft_only: 1, posting_date: today(), sharing_incentive: form.sharing_incentive ? 1 : 0, coupon_code: coupon.value?.coupon_code || '', coupon_amount: coupon.value?.discount_type === 'Fixed Amount' ? Number(coupon.value.discount_value) : 0, advance_amount: 0, lines: lines.value.filter(l=>l.therapy_type).map(l => ({ therapy_type: l.therapy_type, no_of_sessions: Number(l.no_of_sessions), rate: Number(l.rate), use_offer: l.use_offer, offer_rule: l.offer_rule })), comps: comps.value.map(c => ({ item_code:c.item_code, item_name:c.item_name, qty:Number(c.qty), comp_price:Number(c.comp_price), max_qty_allowed:Number(c.max_qty_allowed) })) };
    createAttempted.value = true;
    const result = await billingCall('lifescc_billing_create_plan_and_invoice_test', payload);
    if (!result.sales_invoice) throw new Error('No invoice was returned. Check the server before retrying.');
    invoice = result.sales_invoice; createdInvoice.value = invoice;
  }
  const selectedDiscounts=discountRequests.value.filter(r=>r.enabled);
  if (selectedDiscounts.length) await billingCall('create_multiple_discount_approval_requests_v2', { invoice_name:invoice, requests:JSON.stringify(selectedDiscounts.map(r=>({selected_approver:r.approver,approval_level:r.level,requested_discount_pct:Number(r.pct),reason:discountReason.value.trim()}))) });
  emit('created', invoice);
}); }
</script>
<template>
  <section class="billing-editor">
    <header class="billing-editor-head"><button :disabled="busy" @click="emit('cancel')">← Back to summary</button><div><h2>➕ New Bill — {{ client.patient_name }}</h2></div><span class="billing-badge tone-grey">{{ client.name }}</span></header>
    <p v-if="createdInvoice" class="billing-notice tone-green" role="status">Draft {{ createdInvoice }} created. Retry will use this draft.</p>
    <p v-if="error" role="alert">{{ error }}</p><p v-if="busy" class="billing-loading" role="status">Processing bill…</p>
    <div class="billing-editor-grid">
      <fieldset class="billing-editor-main" :disabled="busy || !!createdInvoice">
        <section class="billing-block"><header class="billing-block-head"><span class="billing-step">1</span><div><h3>Therapy Plan Lines</h3><p>Choose individual therapies or load a package.</p></div></header><div class="billing-block-body">
          <div class="billing-mode-switch legacy-billing-modes"><strong>Billing type:</strong><button type="button" :class="{'is-active':mode==='individual'}" @click="setMode('individual')">🧾 Individual Therapy</button><button type="button" :class="{'is-active':mode==='package'}" @click="setMode('package')">📦 Package / Template</button><span>{{ mode==='package'?'Load a package, then add individual therapies if needed. The package price is retained.':'Add therapies one by one.' }}</span></div>
          <div v-if="mode==='package'" class="billing-template-picker"><label>📋 Load from Therapy Plan Template<select v-model="template" @change="template && loadTemplate()"><option value="">— Pick a package template —</option><option v-for="t in bootstrap.templates" :key="t.name" :value="t.name">{{ t.plan_name || t.name }} · {{ t.total_sessions || 0 }} sess · {{ money(t.total_amount || 0) }}</option></select></label><button class="billing-primary" @click="loadTemplate">Load bundle</button><button @click="clearTemplate">Clear lines</button></div>
          <p v-if="form.pkg_price" class="billing-notice tone-green">{{ form.pkg_name }} · Fixed net price {{ money(form.pkg_price) }} + GST. Item rates stay as listed.</p>
          <div v-for="(line,index) in lines" :key="index" class="billing-therapy-row">
            <div class="billing-therapy-fields"><label>Therapy<div v-if="lineInfo(line)" class="billing-picked-category">{{ lineInfo(line).category && lineInfo(line).category!=='Other'?'🏥 '+lineInfo(line).category:'⚠️ No healthcare service unit on this therapy' }}</div><div class="billing-therapy-search"><input v-model="line.therapyQuery" type="search" placeholder="Type to search…" autocomplete="off" @focus="line.therapyOpen=true" @input="line.therapyOpen=true" @keydown.esc="line.therapyOpen=false" @keydown.enter.prevent="therapyMatches(line)[0] && chooseTherapy(line,therapyMatches(line)[0])"><button v-if="line.therapy_type" type="button" aria-label="Clear therapy" @click="line.therapy_type='';line.therapyQuery='';line.therapyOpen=true;selectTherapy(line)">×</button><div v-if="line.therapyOpen" class="billing-therapy-results"><button v-for="t in therapyMatches(line)" :key="t.n || t.name" type="button" @click="chooseTherapy(line,t)"><span>{{ t.n || t.name }}<small>{{ t.category && t.category!=='Other'?'🏥 '+t.category:'⚠️ no service unit' }}</small></span><small>{{ money(t.rate) }}</small></button><p v-if="!therapyMatches(line).length">{{ catalog.length?'No matching therapies':'No therapies loaded — billing reference data is unavailable. Reload the page or check the billing bootstrap API.' }}</p></div></div></label><label>Sessions<input v-model.number="line.no_of_sessions" type="number" min="1" step="1" @change="applyOffer(line)"></label><label>Rate/session<input v-model.number="line.rate" type="number" min="0" step=".01" :disabled="!!line.use_offer"></label><label>Amount<input :value="(Number(line.no_of_sessions||0)*Number(line.rate||0)).toFixed(0)" readonly></label><label>Range<span class="billing-line-range">{{ lineInfo(line)?money(lineInfo(line).min)+' – '+money(lineInfo(line).max):'—' }}</span></label><button class="billing-danger billing-remove-line" title="Remove" aria-label="Remove therapy" @click="lines.splice(index,1)">✕</button></div>
            <div class="billing-offer-row"><div v-if="offers(line).length" class="billing-offer-list"><div class="billing-offer-card"><span><strong>🏷️ Offer: {{ offers(line)[0].title || offers(line)[0].name }}</strong><small>{{ money(line.use_offer?line.rate:offerPrice(offers(line)[0],line.baseRate)) }}/session<span v-if="offers(line)[0].min_qty"> (min qty {{ offers(line)[0].min_qty }})</span></small></span><label class="billing-offer-toggle"><input type="checkbox" :checked="line.offer_rule===offers(line)[0].name" @change="toggleOffer(line,offers(line)[0],$event.target.checked)"><span>{{ line.offer_rule===offers(line)[0].name?'Applied':'Apply offer' }}</span></label></div></div></div>
          </div>
          <button class="billing-primary" @click="addLine">＋ Add Therapy</button>
          <div class="billing-adjust-box"><label>🎯 Auto-adjust to a target GRAND TOTAL ₹ (incl. GST)<input v-model.number="target" type="number" min="0" step=".01" placeholder="e.g. 20000 (final payable)"></label><button @click="adjust">⚖️ Auto adjust prices</button><button @click="resetRates">↺ Reset to standard</button><p v-if="adjustNote" role="status">{{ adjustNote }}</p></div>
          <p v-if="lines.some(l=>l.therapy_type)" class="billing-category-note">Plan categories: {{ [...new Set(lines.map(l=>lineInfo(l)?.category).filter(Boolean))].join(' · ') }}</p>
        </div></section>
        <section class="billing-block"><header class="billing-block-head"><span class="billing-step">2</span><div><h3>Branch, Consultant Employee &amp; Source</h3></div></header><div class="billing-block-body">
          <div class="billing-form-grid billing-branch-grid"><label>Billing Branch<select v-model="form.branch"><option v-for="b in branches" :key="b">{{ b }}</option></select></label><label>Consultant Employee<div class="billing-therapy-search"><input v-model="practitionerQuery" placeholder="Type to search consultant employee…" autocomplete="off" @focus="practitionerOpen=true" @input="form.practitioner='';practitionerOpen=true" @keydown.esc="practitionerOpen=false"><button v-if="form.practitioner" type="button" aria-label="Clear consultant" @click="form.practitioner='';practitionerQuery='';practitionerOpen=true">×</button><div v-if="practitionerOpen" class="billing-therapy-results"><button v-for="p in filteredPractitioners" :key="p.name" type="button" @click="choosePractitioner(p)">{{ p.practitioner_name }}</button><p v-if="!filteredPractitioners.length">{{ form.branch?'No consultant mapped to '+form.branch:'No consultant found' }}</p></div></div><small v-if="form.practitioner" class="billing-picked">✔ {{ practitionerQuery }}</small></label><label>Source / Media<select v-model="form.plan_media" :disabled="sourceLocked"><option value="">— Select source —</option><option v-for="name in ['Call Center','Reference','DIRECT WALKIN','Existing Customer']" :key="name">{{ name }}</option></select></label></div>
          <p class="billing-notice" :class="sourceLocked?'tone-amber':'bl-media-note'" role="status">{{ sourceLockMessage }}</p>
          <section v-if="form.plan_media==='Reference'" class="billing-reference-box"><h4>Who referred this client? <span class="billing-required">*</span></h4><div class="billing-reference-kind"><label class="billing-checkbox"><input type="checkbox" :checked="referenceClientEnabled" @change="setReferenceKind('client',$event.target.checked)">From a client</label><label class="billing-checkbox"><input type="checkbox" :checked="referenceEmployeeEnabled" @change="setReferenceKind('employee',$event.target.checked)">From an employee</label></div><label v-if="referenceClientEnabled">Referring client<input v-model="refQuery" placeholder="Search client by name or mobile…" autocomplete="off" @input="scheduleReferenceSearch"><div v-if="refClients.length" class="billing-reference-results"><button v-for="p in refClients" :key="p.name" type="button" @click="form.reference_client=p.name;form.reference_client_name=p.patient_name;refQuery=p.patient_name;refClients=[]">{{ p.patient_name }} <small>{{ p.name }} · {{ p.mobile }}<template v-if="p.custom_branch"> · {{ p.custom_branch }}</template></small></button></div><div v-else-if="refSearchDone" class="billing-reference-results"><p class="billing-reference-no-results">No client matches “{{ refQuery }}”</p></div><small v-if="form.reference_client" class="billing-picked">✔ {{ form.reference_client_name }} ({{ form.reference_client }})</small></label><label v-if="referenceEmployeeEnabled">Referring employee<select v-model="form.reference_employee"><option value="">Select employee</option><option v-for="p in practitionersFor(bootstrap.practitioners,'')" :key="p.name" :value="p.name">{{ p.practitioner_name }}</option></select></label></section>
          <div class="billing-incentive-box"><label class="billing-checkbox"><input v-model="form.sharing_incentive" type="checkbox"> Sharing incentive</label><label v-if="form.sharing_incentive">Incentive employee<select v-model="form.incentive_employee"><option value="">Select</option><option v-for="p in practitionersFor(bootstrap.practitioners,'')" :key="p.name" :value="p.name">{{ p.practitioner_name }}</option></select></label></div>
          <div class="billing-remarks-box"><label>📝 Remarks for Office Use <textarea v-model="form.office_remarks" rows="3" placeholder="Internal note — visible to staff after submission." @input="limitRemarks"></textarea></label><div><small>Not shown to the client. Optional. Max 400 words.</small><strong>{{ remarksCount }} / 400</strong></div></div>
        </div></section>
        <section class="billing-block" id="bl-coupon-sec"><header class="billing-block-head"><span class="billing-step">3</span><div><h3>Coupon</h3><p>Apply the client's website coupon. Type the code, or leave blank to auto-find by their mobile number.</p></div></header><div class="billing-block-body"><div class="billing-fields"><label>Coupon<input v-model.trim="couponCode" placeholder="Type code or leave blank to auto-find"></label><button class="billing-primary" @click="checkCoupon">Apply</button><button v-if="coupon" @click="coupon=null;couponCode='';couponStatus=''">Remove coupon</button></div><p v-if="couponStatus" class="billing-notice" :class="coupon?'tone-green':'tone-amber'">{{ couponStatus }}</p></div></section>
        <section class="billing-block" id="bl-disc-sec"><header class="billing-block-head"><span class="billing-step">4</span><div><h3>Discount (approval workflow)</h3><p>Up to 5% per level · L4 uses a final amount including GST.</p></div><label class="billing-switch"><input v-model="discountEnabled" type="checkbox" @change="toggleDiscount">Request discount</label></header><div v-if="discountEnabled" class="billing-block-body"><p class="billing-muted">Select L1, L2 and L3 together. All selected requests are created at the same time—no need to wait for the previous approval. Each level can approve up to 5%; combined maximum is 15%.</p><div class="billing-discount-levels"><section v-for="request in discountRequests" :key="request.level" class="billing-discount-level"><label class="billing-checkbox"><input v-model="request.enabled" type="checkbox"><strong>{{ request.level }} · {{ request.level==='L1'?'Branch Level':request.level==='L2'?'Cluster Level':'Corporate Level' }}</strong></label><div v-if="request.enabled" class="billing-form-grid"><label>Approver<select v-model="request.approver"><option value="">— Select {{ request.level }} approver —</option><option v-for="a in approversForLevel(request.level)" :key="a.user" :value="a.user">{{ a.full_name || a.user }} · {{ request.level }}<template v-if="a.designation"> · {{ a.designation }}</template></option></select></label><label>Discount % (max 5%)<input v-model.number="request.pct" type="number" min="0.5" max="5" step="0.5"></label></div></section></div><p v-if="discountRequests.some(r=>r.enabled)" class="billing-notice tone-green"><strong>{{ discountRequests.filter(r=>r.enabled).length }} approval request{{ discountRequests.filter(r=>r.enabled).length===1?'':'s' }}</strong> will be sent together · Total requested: <strong>{{ discountRequests.filter(r=>r.enabled).reduce((sum,r)=>sum+Number(r.pct||0),0) }}%</strong> of the original grand total including GST.</p><p v-else class="billing-notice">Select one or more approval levels.</p><label>Common reason for all selected approvals<input v-model="discountReason" placeholder="Why is this discount needed?"></label><p class="billing-notice tone-amber">The invoice is created as a Draft and collected only after approval. L4 (MD) exact-final-amount approval is available separately from the bill.</p></div></section>
        <section class="billing-block" id="bl-comp-sec"><header class="billing-block-head"><span class="billing-step">5</span><div><h3>Complimentary Sessions</h3></div><label class="billing-switch"><input v-model="compEnabled" type="checkbox" :disabled="compLimit<=0" @change="!compEnabled && (comps=[])">Add complimentary</label></header><div v-if="compEnabled && compLimit>0" class="billing-block-body"><p class="billing-notice tone-green">{{ compUsed>compLimit?'Limit exceeded — reduce items.':'Slab '+compSlabInfo.label+' · rate '+(compSlabInfo.rate*100)+'% (reduced — balance pending) · limit '+money(compLimit)+' · used '+money(compUsed)+' · remaining '+money(compLimit-compUsed) }}</p><div v-for="(c,index) in comps" :key="index" class="billing-fields"><label>Complimentary session<div class="billing-therapy-search"><input v-model="c.item_name" placeholder="Type to search…" autocomplete="off" @focus="c.itemOpen=true" @input="searchComp(c)"><div v-if="c.itemOpen" class="billing-therapy-results"><button v-for="item in compMatches(c)" :key="item.item_code" type="button" @click="c.item_code=item.item_code;selectComp(c);c.itemOpen=false">{{ item.item_name }}<small>{{ item.item_code }}</small></button><p v-if="!compMatches(c).length">No complimentary items found (item group “Complimentary Sessions”).</p></div></div></label><label>Value ₹ / max qty<span>{{ c.item_code?money(c.comp_price)+' · max '+(c.max_qty_allowed||'—')+'/bill':'—' }}</span></label><label>Qty<input v-model.number="c.qty" type="number" min="1" step="1" :max="c.max_qty_allowed||undefined" @change="clampCompQty(c)"></label><button class="billing-danger" @click="comps.splice(index,1)">✕</button></div><button @click="addComp">＋ Add complimentary</button><p class="billing-muted">Comp items are free (₹0).</p></div><div v-else class="billing-block-body"><p class="billing-muted">Not eligible — subtotal must exceed ₹25,000.</p></div></section>
      </fieldset>
      <aside class="billing-sticky-summary" aria-label="Invoice summary">
        <div class="billing-subtotal-box"><span>Subtotal before GST</span><strong>{{ money(totals.subtotal) }}</strong><p>The bill is created as a draft. Submit it and collect payment from the bill screen, where you can split across payment modes, including Razorpay.</p></div>
        <section class="billing-summary-breakdown"><h3>Bill breakdown</h3><dl><dt>Subtotal</dt><dd>{{ money(totals.subtotal) }}</dd><template v-if="totals.couponAmount"><dt>Coupon</dt><dd class="billing-due">− {{ money(totals.couponAmount) }}</dd></template><template v-if="totals.packageDiscount"><dt>Package discount</dt><dd class="billing-due">− {{ money(totals.packageDiscount) }}</dd></template><template v-if="totals.discount"><dt>Requested discount</dt><dd class="billing-due">− {{ money(totals.discount) }}</dd></template><dt>Net total</dt><dd>{{ money(totals.net) }}</dd><dt>GST 5%</dt><dd>{{ money(totals.gst) }}</dd><dt class="billing-grand-total">Grand total</dt><dd class="billing-grand-total">{{ money(totals.total) }}</dd></dl><p v-if="form.discount_final_amount>0">L4 requested payable: {{ money(form.discount_final_amount) }} incl. GST</p></section>
        <button class="billing-secondary" :disabled="busy || !!createdInvoice" @click="review">👁 Preview Invoice</button><button class="billing-primary" :disabled="busy || !!createdInvoice || !lines.length" @click="create">✅ Generate Therapy Plan + Invoice</button>
      </aside>
    </div>
    <BillingDialog v-if="preview" title="👁 Invoice Preview — check everything before confirming" :can-close="!busy && !createdInvoice" @close="preview=false"><section class="billing-review-panel" aria-label="Invoice preview"><div class="billing-preview-title"><strong>👁 Invoice Preview — check everything before confirming</strong><button :disabled="busy" @click="preview=false">✕</button></div><header><div><strong class="billing-preview-brand">🌿 LIFE CLINICS</strong><p>{{ form.branch }} Branch</p><span class="billing-eyebrow">Draft — not yet submitted · {{ today() }}</span></div><button @click="printPreview">🖨 Print</button></header><p class="billing-preview-client"><b>{{ client.patient_name }}</b> · {{ client.name }} · 📱 {{ client.mobile || '—' }}</p><div class="table-wrap"><table><thead><tr><th>Therapy</th><th>Sessions</th><th>Rate</th><th>Amount</th></tr></thead><tbody><tr v-for="(line,index) in lines.filter(l=>l.therapy_type)" :key="index"><td>{{ line.therapy_type }}<small>{{ lineInfo(line)?.category }}</small></td><td>{{ line.no_of_sessions }}</td><td>{{ money(line.rate) }}</td><td>{{ money(line.rate*line.no_of_sessions) }}</td></tr></tbody></table></div><div v-if="comps.length" class="billing-preview-comps"><strong>🎁 Complimentary (free)</strong><div v-for="c in comps" :key="c.item_code">{{ c.item_name }} ({{ c.item_code }}) · {{ c.qty }} · ₹0.00</div></div><dl class="billing-preview-totals"><dt>Subtotal</dt><dd>{{ money(totals.subtotal) }}</dd><template v-if="totals.couponAmount"><dt>Coupon ({{ coupon?.coupon_code }})</dt><dd>− {{ money(totals.couponAmount) }}</dd></template><template v-if="totals.packageDiscount"><dt>Package price ({{ form.pkg_name || 'fixed' }})</dt><dd>− {{ money(totals.packageDiscount) }}</dd></template><template v-if="discountRequests.some(r=>r.enabled)"><dt>Discount approvals requested</dt><dd>{{ discountRequests.filter(r=>r.enabled).map(r=>r.level+' '+r.pct+'%').join(' · ') }}</dd></template><dt>GST 5%</dt><dd>{{ money(totals.gst) }}</dd><dt class="billing-grand-total">Grand total</dt><dd class="billing-grand-total">{{ money(totals.total) }}</dd><dt>Payable on submission</dt><dd>{{ money(totals.total) }}</dd></dl><p class="billing-notice tone-amber">{{ discountRequests.some(r=>r.enabled)?'A discount is requested. This creates a Therapy Plan and a DRAFT Sales Invoice and sends the selected discount approval requests. Collect payment after approval.':'On confirm this creates a Therapy Plan and a DRAFT Sales Invoice. Submit it on the bill screen, then collect the payment.' }}</p><footer><button :disabled="busy || !!createdInvoice" @click="preview=false">← Go Back &amp; Edit</button><button class="billing-primary" :disabled="busy" @click="create">✅ Confirm &amp; Generate Invoice</button><button v-if="createdInvoice" :disabled="busy" @click="emit('created',createdInvoice)">Open created draft</button></footer><p v-if="error" role="alert">{{ error }}</p></section></BillingDialog>
  </section>
</template>
