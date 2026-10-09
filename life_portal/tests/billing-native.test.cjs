const { test } = require('node:test');
const assert = require('node:assert/strict');
const lib = import('../src/lib/billing.js');
test('collections handle decimal strings, missing derived totals and explicit zero', async () => {
  const { collectionRow, collectionTotals } = await lib;
  const rows = [collectionRow({ branch: 'A', billed_gst: '105', billed_nongst: '50', collected_gst: '105', collected_nongst: '20', collected_ex_gst: '120', outstanding: '30' }), collectionRow({ branch: 'B', billed_total: 0, billed_gst: 999, collected_total: 0, collected_gst: 999, outstanding: 'invalid' })];
  assert.equal(rows[0].billed_total, 155);
  assert.equal(rows[0].collected_total, 125);
  assert.equal(rows[1].billed_total, 0);
  assert.equal(rows[1].collected_total, 0);
  const total = collectionTotals(rows);
  assert.equal(total.billed_total, 155);
  assert.equal(total.collected_total, 125);
  assert.equal(total.outstanding, 30);
  assert.equal(total.collected_ex_gst, 120);
});
test('branch defaults stay within permitted branches; missing scope fails closed', async () => {
  const { billingBranches } = await lib;
  assert.deepEqual(billingBranches({ branches: ['A', 'B'], allowed_branches: ['A'], user_branch: 'B', is_head_office: 0 }), { branches: ['A'], selected: 'A', headOffice: false });
  assert.deepEqual(billingBranches({ branches: ['A', 'B'] }), { branches: [], selected: '', headOffice: false });
  assert.deepEqual(billingBranches({ branches: ['A', 'B'], user_branch: 'B', is_head_office: '1' }), { branches: ['A', 'B'], selected: 'B', headOffice: true });
});
test('native bill calculations preserve package discounts, coupons and tax rounding', async () => {
  const { billTotals, offerPrice, eligibleOffers } = await lib;
  assert.deepEqual(billTotals([{ no_of_sessions: 2, rate: 1000 }], { coupon: { discount_type: 'Fixed Amount', discount_value: 100 }, discountPct: 5, packagePrice: 1800 }), { subtotal: 2000, couponAmount: 0, discount: 0, packageDiscount: 200, net: 1800, gst: 90, total: 1890 });
  assert.equal(offerPrice({ price_or_product_discount: 'Price', discount_percentage: 10 }, 123), 110.7);
  assert.equal(eligibleOffers([{ apply_on: 'Item Code', item_code: 'T', valid_upto: '2026-10-04' }, { apply_on: 'Item Code', item_code: 'T', min_qty: 2 }], 'T', 1, '2026-10-05').length, 0);
});
test('manual and online payments cannot double post, overcollect or omit references and loan proof', async () => {
  const { validatePayments } = await lib;
  const modes = [{ name: 'Cash', type: 'Cash' }, { name: 'Bank', type: 'Bank' }, { name: 'Razorpay', type: 'Bank' }, { name: 'Carepay', type: 'Bank' }];
  assert.throws(() => validatePayments([{ mode: 'Cash', amount: 101 }], 100, modes), /exceed/);
  assert.throws(() => validatePayments([{ mode: 'Bank', amount: 10 }], 100, modes), /UTR/);
  assert.throws(() => validatePayments([{ mode: 'Razorpay', amount: 10 }], 100, modes), /online payment/);
  assert.throws(() => validatePayments([{ mode: 'Carepay', amount: 25000, ref: 'ref' }], 25000, modes), /Aadhaar/);
  assert.equal(validatePayments([{ mode: 'Cash', amount: 50 }, { mode: 'Razorpay', amount: 50, online: { status: 'paid' } }], 100, modes).length, 2);
});
test('practitioner defaults, Indian mobile normalization and approval visibility preserve current rules', async () => {
  const { practitionersFor, normalizeMobile, canApproveRequest } = await lib;
  const rows = [{ name:'old', practitioner_name:'Doctor', branch:'A', last_used:'2026-01-01' }, { name:'new', practitioner_name:'Doctor', branch:'A', last_used:'2026-10-01' }, { name:'wrong', practitioner_name:'Other', branch:'B' }, { name:'disabled', practitioner_name:'Disabled', branch:'A', status:'Disabled' }];
  assert.deepEqual(practitionersFor(rows,'A').map(p=>p.name), ['new']);
  assert.equal(normalizeMobile('+91 98765 43210'), '9876543210');
  assert.equal(normalizeMobile('9187654321'), '9187654321');
  assert.equal(canApproveRequest({status:'Pending',selected_approver:'a'},'b'), false);
  assert.equal(canApproveRequest({status:'Pending',selected_approver:'a'},'a'), true);
  assert.equal(canApproveRequest({status:'Approved',selected_approver:'a'},'Administrator'), false);
});
test('recent presets preserve the 6th–5th business cycle and cap the current cycle at today', async () => {
  const { recentBillingRange } = await lib;
  assert.deepEqual(recentBillingRange('this_month','2026-10-05'), ['2026-09-06','2026-10-05']);
  assert.deepEqual(recentBillingRange('this_month','2026-10-06'), ['2026-10-06','2026-10-06']);
  assert.deepEqual(recentBillingRange('last_month','2026-01-06'), ['2025-12-06','2026-01-05']);
  assert.deepEqual(recentBillingRange('yesterday','2026-03-01'), ['2026-02-28','2026-02-28']);
});
test('grand-total auto-adjust redistributes capped rates and retains offer flags', async () => {
 const {adjustBillingRates,billTotals}=await lib;
 const catalog=[{n:'A',rate:1000,min:800,max:900},{n:'B',rate:1000,min:800,max:1400}];
 const lines=[{therapy_type:'A',no_of_sessions:1,rate:1000},{therapy_type:'B',no_of_sessions:1,rate:1000,use_offer:1,offer_rule:'OFFER'}];
 const adjusted=adjustBillingRates(lines,catalog,2310);
 assert.deepEqual(adjusted.map(r=>r.rate),[900,1300]);
 assert.equal(adjusted[1].use_offer,1);assert.equal(adjusted[1].offer_rule,'OFFER');
 assert.equal(billTotals(adjusted).total,2310);
 assert.throws(()=>adjustBillingRates(lines,catalog,100),/outside/);
 const withCoupon=adjustBillingRates(lines,catalog,1995,{coupon:{discount_type:'Fixed Amount',discount_value:100}});
 assert.equal(billTotals(withCoupon,{coupon:{discount_type:'Fixed Amount',discount_value:100}}).total,1995);
});

test('doctor selection stays within the physical branch, including legacy branch aliases', async () => {
 const { doctorsFor } = await lib;
 const list=[{name:'D1',practitioner_name:'Doctor A',designation:'Dermatologist',branch:'Himayathnagar'}, {name:'D2',designation:'Doctor',branch:'B',all_branches:1}, {name:'C1',designation:'Consultant',branch:'Himayatnagar'}, {name:'D3',designation:'Physician',branch:'Himayatnagar',status:'Disabled'}];
 assert.deepEqual(doctorsFor(list,'Himayatnagar').map(p=>p.name),['D1']);
 assert.deepEqual(doctorsFor(list,''),[]);
});
test('cost justification preserves an explicit zero profit and uses absent-field fallbacks', async () => {
 const { invoiceCosts } = await lib;
 const values=Object.fromEntries(invoiceCosts({grand_total:1050,custom_product_cost:300,custom_clinical_operational_cost:700,total_taxes_and_charges:50,custom_net_profit:0}));
 assert.equal(values['Total cost'],1050);assert.equal(values['Net profit'],0);
});
test('invalid payment amounts are rejected before collection', async () => {
 const {validatePayments}=await lib;
 for(const amount of [-1,Infinity,NaN])assert.throws(()=>validatePayments([{mode:'Cash',amount}],100,[{name:'Cash',type:'Cash'}]),/non-negative/);
});
