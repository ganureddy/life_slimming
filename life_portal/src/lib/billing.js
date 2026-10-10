export const collectionColumns = [
  ['billed_total', 'Grand total'], ['billed_ex_gst', 'Total (excl. GST)'],
  ['collected_total', 'Paid amount'], ['collected_ex_gst', 'Paid (excl. GST)'],
  ['outstanding', 'Outstanding'], ['billed_gst', 'Billed · GST'],
  ['billed_nongst', 'Billed · Non-GST'],
];
const amount = value => Number.isFinite(Number(value)) ? Number(value) : 0;
export function collectionRow(row) {
  const result = { branch: row.branch || '—' };
  for (const [key] of collectionColumns) result[key] = amount(row[key]);
  // Older responses can omit derived totals. Explicit zero remains authoritative.
  result.billed_total = amount(row.billed_total ?? (amount(row.billed_gst) + amount(row.billed_nongst)));
  result.collected_total = amount(row.collected_total ?? (amount(row.collected_gst) + amount(row.collected_nongst)));
  return result;
}
export function collectionTotals(rows) {
  return rows.reduce((total, row) => {
    for (const [key] of collectionColumns) total[key] += amount(row[key]);
    return total;
  }, Object.fromEntries(collectionColumns.map(([key]) => [key, 0])));
}
export function billingBranches(bootstrap) {
  const allowed = [...new Set(bootstrap.allowed_branches || [])];
  const headOffice = Number(bootstrap.is_head_office) === 1;
  const branches = headOffice ? [...new Set(bootstrap.branches || [])] : allowed;
  const selected = branches.includes(bootstrap.user_branch) ? bootstrap.user_branch : branches[0] || '';
  return { branches, selected, headOffice };
}

export const loanModes = ['Bajaj Card Charges', 'Carepay', 'Fibe Finance', 'ShopSE', 'Savein Fintech Card Charges', 'Sai Roshini Card Charges', 'Liqui Loans Charges', 'Loan Tap / Uno Finance Charges'];
export const isOnlineMode = name => /razorpay/i.test(name || '');
export function normalizeMobile(value) {
  let digits = String(value || '').replace(/\D/g, '');
  if (digits.length === 12 && digits.startsWith('91')) digits = digits.slice(2);
  if (digits.length === 11 && digits.startsWith('0')) digits = digits.slice(1);
  return digits;
}
export function practitionersFor(list, branch) {
  const best = new Map();
  for (const p of list || []) {
    if (p.status && String(p.status).toLowerCase() !== 'active') continue;
    if (branch && !(p.all_branches || p.branch === branch || p.branches?.includes(branch))) continue;
    const key = `${p.practitioner_name || p.name}|${p.branch || ''}`.toLowerCase();
    if (!best.has(key) || String(p.last_used || '') > String(best.get(key).last_used || '')) best.set(key, p);
  }
  return [...best.values()].sort((a, b) => (a.practitioner_name || a.name).localeCompare(b.practitioner_name || b.name));
}
export function doctorsFor(list, branch) {
  const normalize = value => {
    const name = String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    return ({ himayathnagar: 'himayatnagar', chandhanagar: 'chandanagar' })[name] || name;
  };
  if (!branch) return [];
  return practitionersFor((list || []).filter(p =>
    /doctor|dermat|physician|medical officer/i.test(p.designation || '') &&
    normalize(p.branch) === normalize(branch)
  ), '');
}
export function invoiceCosts(doc) {
  const product = amount(doc.custom_product_cost), clinical = amount(doc.custom_clinical_operational_cost);
  const gst = amount(doc.total_taxes_and_charges), selling = amount(doc.grand_total);
  const total = doc.custom_total_cost == null ? product + clinical + gst : amount(doc.custom_total_cost);
  const profit = doc.custom_net_profit == null ? selling - total : amount(doc.custom_net_profit);
  return [['Final selling price', selling], ['Product cost', product], ['Clinical & operational cost', clinical], ['GST', gst], ['Total cost', total], ['Net profit', profit]];
}
export function offerPrice(offer, base) {
  if (offer.price_or_product_discount !== 'Price') return Number(base);
  if (Number(offer.rate) > 0) return Number(offer.rate);
  if (Number(offer.discount_percentage) > 0) return Math.round(Number(base) * (1 - Number(offer.discount_percentage) / 100) * 100) / 100;
  return Math.max(0, Number(base) - Number(offer.discount_amount || 0));
}
export function eligibleOffers(offers, item, qty, today) {
  return (offers || []).filter(o => o.apply_on === 'Item Code' && o.item_code === item && (!o.valid_from || String(o.valid_from).slice(0, 10) <= today) && (!o.valid_upto || String(o.valid_upto).slice(0, 10) >= today) && (!Number(o.min_qty) || qty >= Number(o.min_qty)) && (!Number(o.max_qty) || qty <= Number(o.max_qty)));
}
export function billTotals(lines, { coupon = null, discountPct = 0, packagePrice = 0 } = {}) {
  const subtotal = lines.reduce((sum, line) => sum + Number(line.no_of_sessions || 0) * Number(line.rate || 0), 0);
  const couponAmount = coupon && !(packagePrice > 0) ? Math.min(subtotal, coupon.discount_type === 'Fixed Amount' ? Number(coupon.discount_value || 0) : Math.round(subtotal * Number(coupon.discount_value || 0)) / 100) : 0;
  const discount = packagePrice > 0 ? 0 : Math.round(subtotal * Math.min(5, Math.max(0, Number(discountPct))) / 100);
  const packageDiscount = packagePrice > 0 ? Math.max(0, Math.round((subtotal - packagePrice) * 100) / 100) : 0;
  const net = Math.max(0, subtotal - couponAmount - discount - packageDiscount);
  const gst = Math.round(net * 5) / 100;
  return { subtotal, couponAmount, discount, packageDiscount, net, gst, total: Math.round((net + gst) * 100) / 100 };
}
export function validatePayments(payments, outstanding, modes) {
  if (payments.some(p => !Number.isFinite(Number(p.amount)) || Number(p.amount) < 0)) throw new Error('Payment amounts must be finite, non-negative numbers.');
  const active = payments.filter(p => Number(p.amount) > 0);
  if (!active.length) throw new Error('Enter at least one payment amount.');
  if (active.some(p => !modes.some(m => m.name === p.mode))) throw new Error('Select a valid payment mode.');
  if (active.reduce((sum, p) => sum + Number(p.amount), 0) > Number(outstanding) + 0.5) throw new Error('Payments exceed the outstanding amount.');
  for (const p of active) {
    if (isOnlineMode(p.mode)) {
      if (p.online?.status !== 'paid') throw new Error('Complete the online payment before recording collection.');
      continue;
    }
    const mode = modes.find(m => m.name === p.mode);
    if (mode?.type !== 'Cash' && mode?.acct_type !== 'Cash' && !String(p.ref || '').trim()) throw new Error(`Reference / UTR is required for ${p.mode}.`);
    if (loanModes.includes(p.mode)) {
      if (Number(p.amount) < 25000) throw new Error(`${p.mode} requires at least ₹25,000.`);
      if (!p.loan?.aadhaar_card || !p.loan?.pan_card || !p.loan?.transaction_id) throw new Error('Loan Aadhaar, PAN and transaction ID are required.');
      if (!['do_screenshot', 'aadhaar_image', 'pan_image', 'consent_image'].every(key => p.loan.files?.[key])) throw new Error('All four loan attachments are required.');
      if (!p.loan.video?.verified || !p.loan.video?.url) throw new Error('Record and verify, or review and upload, the loan declaration video.');
    }
  }
  return active;
}
export function canApproveRequest(row, user) {
  return row.status === 'Pending' && !(row.approval_level === 'L4' && row.requested_by === user) && (row.selected_approver === user || ['bhuvan@lifescc.com', 'narendhar@lifescc.com', 'Administrator'].includes(user));
}

export function recentBillingRange(preset, today) {
  const shift = (value, days) => { const date = new Date(value + 'T12:00:00Z'); date.setUTCDate(date.getUTCDate() + days); return date.toISOString().slice(0,10); };
  const cycle = value => {
    const date = new Date(value + 'T12:00:00Z'); date.setUTCMonth(date.getUTCMonth() - (date.getUTCDate() < 6 ? 1 : 0), 6);
    const from = date.toISOString().slice(0,10); date.setUTCMonth(date.getUTCMonth()+1,5); return [from,date.toISOString().slice(0,10)];
  };
  if(preset==='yesterday'){const date=shift(today,-1);return [date,date];}
  const [from,to]=cycle(today);
  if(preset==='last_month')return cycle(shift(from,-1));
  if(preset==='this_month')return [from,to>today?today:to];
  return [today,today];
}

export function adjustBillingRates(lines, therapies, grandTarget, { discountPct=0, coupon=null }={}) {
  if (!(grandTarget>0) || !lines.length) throw new Error('Enter a target grand total and add therapy lines.');
  const percent=Math.min(5,Math.max(0,Number(discountPct))) + (coupon?.discount_type==='Fixed Amount'?0:Number(coupon?.discount_value || 0));
  if(percent>=100)throw new Error('The percentage discount is invalid.');
  const target=(grandTarget/1.05 + (coupon?.discount_type==='Fixed Amount'?Number(coupon.discount_value || 0):0))/(1-percent/100);
  const rows=lines.map(line=>{
    const item=therapies.find(t=>t.n===line.therapy_type || t.name===line.therapy_type);
    if(!item || !(Number(line.no_of_sessions)>0))throw new Error('Select valid therapies and session quantities first.');
    const rate=Number(line.rate || item.rate || 0),min=Number(item.min || 0);
    return {line,qty:Number(line.no_of_sessions),rate,min:line.use_offer?Math.min(rate,min):min,max:Number(item.max)>0?Math.max(Number(item.max),line.use_offer?rate:0):Infinity,pinned:false};
  });
  const low=rows.reduce((sum,r)=>sum+r.min*r.qty,0),high=rows.reduce((sum,r)=>sum+r.max*r.qty,0);
  if(target<low-.5 || target>high+.5)throw new Error('The target is outside the permitted therapy rate range.');
  for(let pass=0;pass<=rows.length;pass++){
    const pinned=rows.filter(r=>r.pinned).reduce((sum,r)=>sum+r.rate*r.qty,0);
    const free=rows.filter(r=>!r.pinned).reduce((sum,r)=>sum+r.rate*r.qty,0);
    if(!free)break;
    let changed=false;
    for(const r of rows.filter(r=>!r.pinned)){const next=r.rate*(target-pinned)/free;r.rate=Math.max(r.min,Math.min(r.max,next));if(next<r.min || next>r.max){r.pinned=true;changed=true;}}
    if(!changed)break;
  }
  for(const r of rows)r.rate=Math.max(r.min,Math.min(r.max,Math.round(r.rate)));
  let drift=Math.round(target-rows.reduce((sum,r)=>sum+r.rate*r.qty,0));
  for(const r of rows){const per=Math.round(drift/r.qty),next=r.rate+per;if(next>=r.min && next<=r.max){r.rate=next;drift-=per*r.qty;}}
  return rows.map(r=>({...r.line,rate:r.rate}));
}
