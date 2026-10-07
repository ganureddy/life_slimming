<script setup>
import { computed, onBeforeUnmount, ref } from 'vue';
import { billingCall, getBillingDoc, setBillingValue, uploadBillingFile } from '../../api/billing';
import { isOnlineMode, loanModes, normalizeMobile, validatePayments } from '../../lib/billing';
import { indiaStamp } from '../../lib/cc';
import BillingLoanVideo from './BillingLoanVideo.vue';
const props = defineProps({ invoice: Object, bootstrap: Object, mobile: String });
const emit = defineEmits(['recorded', 'close', 'busy-change']);
const rows = ref([]), busy = ref(false), error = ref(''), liveOutstanding = ref(Number(props.invoice.outstanding_amount)), receipt = ref(null), collectionAttempted = ref(false), receiptMobile = ref(props.mobile || '');
const money = value => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(value || 0));
const total = computed(() => rows.value.reduce((sum,p) => sum + Number(p.amount || 0), 0));
const timers = new Map(); let alive = true, sdkPromise, checkout;
function add() { rows.value.push({ id: crypto.randomUUID(), mode: props.bootstrap.modes?.[0]?.name || '', amount: 0, ref: '', mobile: props.mobile || '', online: null, loan: { files: {}, video: null, aadhaar_card: '', pan_card: '', transaction_id: '' } }); }
add();
function remove(p) { clearTimeout(timers.get(p.id)); timers.delete(p.id); rows.value = rows.value.filter(row => row !== p); }
async function action(fn) { if (busy.value) return; busy.value = true; emit('busy-change',true); error.value = ''; try { await fn(); } catch (e) { error.value = e.message; } finally { busy.value = false; emit('busy-change',false); } }
function guard(p) {
  if (Number(props.invoice.docstatus) !== 1) throw new Error('Submit the invoice before collecting payment.');
  if (!isOnlineMode(p.mode) || p.online?.status === 'paid') throw new Error('This online row cannot be changed.');
  const manual = rows.value.filter(row => row !== p && !row.online).reduce((sum,row) => sum + Number(row.amount || 0), 0);
  if (!(Number(p.amount) > 0) || Number(p.amount) + manual > liveOutstanding.value + .5) throw new Error('Enter an amount within the remaining outstanding balance.');
}
async function markPaid(p, result) {
  clearTimeout(timers.get(p.id)); timers.delete(p.id);
  p.online = { ...p.online, ...result, status: 'paid', amount: Number(p.amount) };
  p.ref = result.payment_id || result.payment_entry || '';
  const invoice = await getBillingDoc('Sales Invoice', props.invoice.name);
  if (alive) liveOutstanding.value = Number(invoice.outstanding_amount);
}
async function poll(p, quiet = false) {
  if (!alive || !p.online?.payment_link_id || p.online.status === 'paid') return;
  try {
    const result = await billingCall('life_slimming.razorpay_payment.check_payment_link_payment', { sales_invoice: props.invoice.name, payment_link_id: p.online.payment_link_id });
    if (!alive) return;
    if (result.status === 'paid') { await markPaid(p,result); return; }
    if (result.status === 'failed') { p.online.status = 'failed'; p.online.message = result.reason; return; }
    p.online.message = 'Waiting for payment';
  } catch (e) { if (!quiet) error.value = e.message; }
  if (alive && p.online.polls++ < 100) timers.set(p.id, setTimeout(() => poll(p,true), 6000));
}
function createLink(p, send = false) { return action(async () => {
  guard(p);
  if (send && !/^[6-9]\d{9}$/.test(normalizeMobile(p.mobile))) throw new Error('Enter a valid mobile number.');
  const result = await billingCall('life_slimming.razorpay_payment.' + (send ? 'send_payment_link' : 'create_payment_link'), { sales_invoice: props.invoice.name, amount: Number(p.amount), contact_mobile: normalizeMobile(p.mobile) });
  if (!result.short_url || !result.payment_link_id) throw new Error('No payment link returned.');
  p.online = { ...result, status: 'pending', polls: 0 }; poll(p,true);
}); }
function sdk() {
  if (window.Razorpay) return Promise.resolve();
  if (!sdkPromise) sdkPromise = new Promise((resolve,reject) => {
    const script = document.createElement('script'); script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.onload = resolve; script.onerror = () => { sdkPromise = null; script.remove(); reject(new Error('Razorpay could not be loaded.')); }; document.head.appendChild(script);
  });
  return sdkPromise;
}
function payNow(p) { return action(async () => {
  guard(p); await sdk();
  const order = await billingCall('life_slimming.razorpay_payment.create_order', { sales_invoice: props.invoice.name, amount: Number(p.amount) });
  if (!order.order_id) throw new Error('No Razorpay order returned.');
  if (!alive) return;
  p.online = { status: 'pending', order_id: order.order_id };
  checkout = new window.Razorpay({ key: order.key_id, order_id: order.order_id, amount: order.amount, currency: order.currency || 'INR', name: 'LIFE Slimming & Cosmetic Clinics', description: props.invoice.name, prefill: { name: props.invoice.patient_name, contact: normalizeMobile(p.mobile), email: order.contact_email || '' }, modal:{ondismiss:()=>{if(p.online?.status==='pending' && !p.online.payment_link_id)p.online=null;}}, handler: result => action(async () => {
    const recorded = await billingCall('life_slimming.razorpay_payment.verify_and_record_payment', { sales_invoice: props.invoice.name, ...result });
    if (recorded.status !== 'paid') throw new Error('Payment captured but recording is not confirmed. Check the invoice before retrying.');
    await markPaid(p,{ ...recorded, payment_id: result.razorpay_payment_id });
  }) }); checkout.open();
}); }
function share(text, mobile) { const number = normalizeMobile(mobile); if (!/^[6-9]\d{9}$/.test(number)) { error.value='Enter a valid mobile number.'; return; } window.open('https://wa.me/91' + number + '?text=' + encodeURIComponent(text), '_blank', 'noopener,noreferrer'); }
function record() { return action(async () => {
  if(collectionAttempted.value)throw new Error('The previous collection result is uncertain. Check the invoice and Payment Entries before recording again.');
  const active = validatePayments(rows.value, props.invoice.outstanding_amount, props.bootstrap.modes || []);
  const manual = active.filter(p => !isOnlineMode(p.mode));
  const fresh = await getBillingDoc('Sales Invoice', props.invoice.name);
  if (Number(fresh.docstatus) !== 1 || manual.reduce((sum,p)=>sum+Number(p.amount),0) > Number(fresh.outstanding_amount)+.5) throw new Error('The invoice balance changed. Refresh before recording.');
  const docs = [];
  for (const p of manual.filter(p=>loanModes.includes(p.mode))) {
    const d = { mode_of_payment: p.mode, aadhaar_card: p.loan.aadhaar_card, pan_card: p.loan.pan_card.toUpperCase(), transaction_id: p.loan.transaction_id, consent_video: p.loan.video.url };
    for (const [key,file] of Object.entries(p.loan.files)) d[key] = await uploadBillingFile(file,'Payment Entry');
    docs.push(d);
  }
  let result = { payment_entries: [], allocated: 0, outstanding: Number(fresh.outstanding_amount) };
  if (manual.length) collectionAttempted.value=true;
  if (manual.length) result = await billingCall('lifescc_billing_collect_payment_v4', { sales_invoice: props.invoice.name, reference_date: indiaStamp().slice(0,10), payments: JSON.stringify(manual.map(p=>({ mode_of_payment:p.mode, amount:Number(p.amount), reference_no:p.ref || '' }))), loan_docs: JSON.stringify(docs) });
  if (manual.length && !result.payment_entries?.length) throw new Error('No Payment Entries returned. Check the invoice before retrying.');
  receipt.value = { entries: [...(result.payment_entries || []), ...active.map(p=>p.online?.payment_entry).filter(Boolean)], outstanding: Number(result.outstanding), paid: Number(result.allocated || 0) + active.filter(p=>isOnlineMode(p.mode)).reduce((sum,p)=>sum+Number(p.online.amount || p.amount),0), rows: active.map(p=>({mode:p.mode,amount:Number(p.amount),ref:p.ref})) };
  const video = docs[0]?.consent_video;
  if (video) {
    try { await setBillingValue('Patient',props.invoice.patient,'custom_client_photo_attach',video); } catch { error.value = 'Payment recorded; patient video attachment could not be updated.'; }
    for (const name of result.payment_entries || []) {
      try { const entry = await getBillingDoc('Payment Entry',name); if (Number(entry.docstatus) === 0) await setBillingValue('Payment Entry',name,'custom_loan_consent_video',video); } catch { error.value = 'Payment recorded; a video attachment could not be updated.'; }
    }
  }
  emit('recorded');
}); }
const receiptText = computed(() => receipt.value ? ['LIFE Slimming & Cosmetic Clinics', 'Payment received — thank you!', 'Client: '+props.invoice.patient_name, 'Bill: '+props.invoice.name, 'Branch: '+props.invoice.branch, 'Date: '+indiaStamp().slice(0,10), ...receipt.value.rows.map(p=>p.mode+': '+money(p.amount)+(p.ref?' · Ref '+p.ref:'')), 'Amount paid: '+money(receipt.value.paid), 'Balance due: '+money(receipt.value.outstanding)].join('\n') : '');
onBeforeUnmount(()=>{alive=false;for(const timer of timers.values())clearTimeout(timer); checkout?.close();});
</script>
<template><section class="billing-panel"><h3>Collect payment · {{ invoice.name }}</h3><p>Outstanding: {{ money(liveOutstanding) }}</p>
<template v-if="!receipt"><div v-for="p in rows" :key="p.id" class="billing-panel">
<div class="billing-fields"><label>Mode<select v-model="p.mode" :disabled="busy || !!p.online" @change="p.loan.video=null"><option v-for="m in bootstrap.modes" :key="m.name" :value="m.name">{{ m.name }}</option></select></label><label>Amount<input v-model.number="p.amount" :disabled="busy || !!p.online" type="number" min="0" step=".01"></label><label>Reference / UTR<input v-model="p.ref" :disabled="busy || !!p.online"></label><button :disabled="busy || !!p.online" @click="remove(p)">Remove payment</button></div>
<div v-if="isOnlineMode(p.mode)" class="billing-fields"><label>Mobile<input v-model="p.mobile" inputmode="tel" :disabled="busy || !!p.online"></label><button :disabled="busy || !!p.online" @click="payNow(p)">Pay now</button><button :disabled="busy || !!p.online" @click="createLink(p)">Payment link + QR</button><button :disabled="busy || !!p.online" @click="createLink(p,true)">Send payment link on WhatsApp</button><template v-if="p.online"><p role="status">{{ p.online.status }} · {{ p.online.message }}</p><a v-if="p.online.short_url" :href="p.online.short_url" target="_blank" rel="noopener noreferrer">Open payment link</a><img v-if="p.online.qr_image" :src="p.online.qr_image" alt="Payment QR code" width="160"><button v-if="p.online.payment_link_id" :disabled="busy || p.online.status==='paid'" @click="poll(p)">Check payment status</button><button v-if="p.online.short_url" @click="share(p.online.short_url,p.mobile)">Share link</button><button v-if="p.online.status==='failed'" :disabled="busy" @click="p.online=null">Reset failed link</button></template></div>
<div v-if="loanModes.includes(p.mode)"><div class="billing-fields"><label>Aadhaar card<input v-model.trim="p.loan.aadhaar_card" :disabled="busy"></label><label>PAN card<input v-model.trim="p.loan.pan_card" :disabled="busy"></label><label>Loan transaction ID<input v-model.trim="p.loan.transaction_id" :disabled="busy"></label><label v-for="[key,label] in [['do_screenshot','D.O screenshot'],['aadhaar_image','Aadhaar image'],['pan_image','PAN image'],['consent_image','Loan consent image']]" :key="key">{{ label }}<input type="file" :disabled="busy" accept="image/*,application/pdf" @change="p.loan.files[key]=$event.target.files[0]"></label></div><BillingLoanVideo :client="invoice.patient_name" :branch="invoice.branch" @verified="p.loan.video=$event" /></div>
</div><p>Entered total: {{ money(total) }}</p><button :disabled="busy" @click="add">Add payment</button><button :disabled="busy" @click="record">Record collection</button></template>
<div v-else><h3>Payment receipt</h3><p>{{ receipt.entries.join(', ') }}</p><pre>{{ receiptText }}</pre><label>Receipt mobile<input v-model="receiptMobile" inputmode="tel"></label><button @click="action(()=>navigator.clipboard.writeText(receiptText))">Copy receipt</button><button @click="share(receiptText,receiptMobile)">Send receipt on WhatsApp</button></div>
<button :disabled="busy" @click="emit('close')">Close collection</button><p v-if="error" role="alert">{{ error }}</p><p v-if="busy" role="status">Processing payment…</p></section></template>
