<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { billingCall, billingList } from '../api/billing';
import { indiaStamp } from '../lib/cc';
import { elapsedTargetDays, targetCycleRange, targetKpis } from '../lib/branch-target';
import AccordionSection from '../components/AccordionSection.vue';

const [initialFrom, initialTo] = targetCycleRange();
const from = ref(initialFrom), to = ref(initialTo), preset = ref('this');
const branches = ref([]), branch = ref(''), loading = ref(false), error = ref(''), data = ref(null);
const viewVersion = ref(0);
const branchLoading = ref(true), branchError = ref('');
let controller, mounted = true;
const tracker = computed(() => data.value?.daily || null);
const days = computed(() => elapsedTargetDays(tracker.value));
const maxBar = computed(() => Math.max(1, ...days.value.flatMap(day => [Number(day.got || 0), Number(day.req || 0)])));
const kpis = computed(() => {
  const values = targetKpis(tracker.value);
  const labels = tracker.value?.is_closed ? ['Final Realisation', 'Achieved', 'Target', Number(tracker.value.gap) > 0 ? 'Shortfall' : 'Surplus', 'Days Hit', 'Days Missed'] : ['Cycle Realisation', 'Achieved (net)', 'Gross receipts', 'Monthly Target', 'Gap to close', 'NEEDED PER DAY', 'Days Left'];
  return values.map(([label, value], index) => ({ label: labels[index], value, count: /days/i.test(label), class: index === 0 ? Number(tracker.value.pct) < 70 ? 'r' : Number(tracker.value.pct) < 85 ? 'a' : '' : /gap|needed|missed|shortfall/i.test(labels[index]) ? 'r' : '' }));
});
const money = value => '₹' + Math.round(Number(value || 0)).toLocaleString('en-IN');
const compact = value => { const n = Number(value || 0); return n >= 10000000 ? `₹${(n / 10000000).toFixed(2)} Cr` : n >= 100000 ? `₹${(n / 100000).toFixed(2)} L` : money(n); };
const date = value => value ? String(value).slice(0, 10).split('-').reverse().join('/') : '—';

async function loadBranches() {
  branchLoading.value = true; branchError.value = '';
  try {
    const rows = await billingList('Branch', [['name', 'not in', ['Head Office', 'Testing Branch']]], ['name'], { limit: 1000, order: 'name asc' });
    if (!mounted) return;
    branches.value = rows.map(row => row.name);
    if (!branches.value.length) throw new Error('No permitted branch is available.');
    branch.value = branches.value[0];
    await load();
  } catch (failure) { if (mounted) branchError.value = failure.message; }
  finally { if (mounted) branchLoading.value = false; }
}
async function load() {
  if (!branch.value) { error.value = 'Choose a branch.'; return; }
  if (!from.value || !to.value || from.value > to.value) { error.value = 'Choose a valid date range.'; return; }
  controller?.abort(); const current = new AbortController(); controller = current;
  loading.value = true; error.value = ''; data.value = null;
  try {
    const result = await billingCall('branch_command_center', { branch: branch.value, from_date: from.value, to_date: to.value }, current.signal);
    if (mounted && controller === current) { data.value = result; viewVersion.value++; }
  } catch (failure) { if (mounted && controller === current) error.value = failure.message; }
  finally { if (mounted && controller === current) loading.value = false; }
}
function selectPreset(value) { preset.value = value; [from.value, to.value] = targetCycleRange(value); load(); }
function apply() { preset.value = ''; load(); }
onMounted(loadBranches); onBeforeUnmount(() => { mounted = false; controller?.abort(); });
</script>

<template>
  <section class="btgt branch-target">
    <form class="btgt-head target-filters" @submit.prevent="apply">
      <span class="btgt-title">🎯 Target &amp; Realisation</span>
      <select id="btgtBranch" v-model="branch" :disabled="branchLoading || loading" aria-label="Branch" @change="load"><option v-if="branchLoading" value="">Loading branches…</option><option v-for="name in branches" :key="name" :value="name">{{ name }}</option></select>
      <label for="btgtFrom">From</label><input id="btgtFrom" v-model="from" type="date" @change="preset = ''"><label for="btgtTo">To</label><input id="btgtTo" v-model="to" type="date" @change="preset = ''">
      <button id="btgtApply" class="btgt-btn" type="submit" :disabled="loading || !branch">Apply</button><button class="btgt-chip" :class="{active:preset === 'this', selected:preset === 'this'}" type="button" :disabled="loading || !branch" @click="selectPreset('this')">This Cycle</button><button class="btgt-chip" :class="{active:preset === 'last', selected:preset === 'last'}" type="button" :disabled="loading || !branch" @click="selectPreset('last')">Last Cycle</button>
    </form>
    <p v-if="branchError" class="note r" role="alert">{{ branchError }} <button @click="loadBranches">Retry</button></p>
    <div id="mKpis" class="m-kpis target-kpis">
      <div v-if="loading || branchLoading" class="m-kpi"><b>…</b><span>Loading</span></div>
      <div v-else-if="!tracker?.days" class="m-kpi"><b>—</b><span>Daily tracker unavailable</span></div>
      <div v-for="item in loading || !tracker?.days ? [] : kpis" :key="item.label" class="m-kpi"><b class="num" :class="item.class">{{ typeof item.value === 'number' && !item.count ? compact(item.value) : item.value }}</b><span>{{ item.label }}</span></div>
    </div>
    <div id="mBody" class="m-bd">
      <p v-if="loading || branchLoading" class="note" role="status">Loading target data…</p><p v-else-if="error" class="note r" role="alert">Error: {{ error }} <button @click="load">Retry</button></p>
      <div v-else-if="!tracker?.days" class="note">Daily target tracking is unavailable for this branch.</div>
      <template v-else>
        <div class="tgt-need" :class="tracker.is_closed ? Number(tracker.pct) >= 100 ? 'ok' : 'warn' : tracker.on_track ? 'ok' : 'warn'">
          <div class="tgt-need-l">{{ tracker.is_closed ? 'Closed cycle · ' + date(tracker.cycle_from) + ' → ' + date(tracker.cycle_to) : 'To hit ' + compact(tracker.target) + ' by ' + date(tracker.cycle_to) }}</div>
          <div class="tgt-need-v">{{ tracker.is_closed ? tracker.pct + '%' : money(tracker.req_per_day) }}<span>{{ tracker.is_closed ? ' of target' : ' / day' }}</span></div>
          <div v-if="tracker.is_closed" class="tgt-need-s">{{ compact(tracker.achieved) }} collected against {{ compact(tracker.target) }} — {{ Number(tracker.gap) > 0 ? 'short by ' + compact(tracker.gap) : 'exceeded by ' + compact(Number(tracker.achieved) - Number(tracker.target)) }} · {{ tracker.hit_days }} of {{ tracker.total_days }} days hit</div>
          <div v-else class="tgt-need-s">{{ compact(tracker.gap) }} still to collect across {{ tracker.days_left }} remaining day{{ Number(tracker.days_left) === 1 ? '' : 's' }}</div>
        </div>
        <AccordionSection :key="'pace' + viewVersion" title="Pace check" :count="6" default-open>
          <div class="tgt-grid">
            <template v-if="tracker.is_closed"><div class="tgt-cell"><span>Average per day</span><b>{{ money(tracker.run_rate) }} / day</b></div><div class="tgt-cell"><span>Needed per day</span><b>{{ money(Number(tracker.target) / Math.max(1, Number(tracker.total_days))) }} / day</b></div><div class="tgt-cell"><span>Result</span><b :class="{r:Number(tracker.pct) < 100}">{{ Number(tracker.pct) >= 100 ? 'TARGET MET' : 'MISSED by ' + compact(tracker.gap) }}</b></div><div class="tgt-cell"><span>Cycle length</span><b>{{ tracker.total_days }} days</b></div></template>
            <template v-else><div class="tgt-cell"><span>Current run rate</span><b>{{ money(tracker.run_rate) }} / day</b></div><div class="tgt-cell"><span>Required run rate</span><b class="r">{{ money(tracker.req_per_day) }} / day</b></div><div class="tgt-cell"><span>Projected at this pace</span><b :class="{r:!tracker.on_track}">{{ compact(tracker.projected) }}</b></div><div class="tgt-cell"><span>Status</span><b :class="{r:!tracker.on_track}">{{ tracker.on_track ? 'ON TRACK' : 'BEHIND by ' + compact(Math.max(Number(tracker.target) - Number(tracker.projected), 0)) }}</b></div></template>
            <div class="tgt-cell"><span>Days hit</span><b>{{ tracker.hit_days }}</b></div><div class="tgt-cell"><span>Days missed</span><b class="r">{{ tracker.miss_days }}</b></div>
          </div>
        </AccordionSection>
        <AccordionSection :key="'bars' + viewVersion" title="Daily collections vs required" :count="days.length" default-open>
          <div class="tgt-strip"><div v-for="day in days" :key="day.d" class="tgt-bar target-bar" :title="date(day.d) + ' — collected ' + money(day.got) + ' of ' + money(day.req)"><div class="tgt-bar-wrap"><i :class="day.hit ? 'ok' : 'no'" :style="{height:Math.round(Number(day.got) / maxBar * 100) + '%'}"></i><u :style="{bottom:Math.round(Number(day.req) / maxBar * 100) + '%'}"></u></div><span>{{ String(day.d).slice(8,10) }}</span></div></div>
          <div class="tgt-legend"><span><i class="sw ok"></i>Hit</span><span><i class="sw no"></i>Miss</span><span><i class="sw line"></i>Required that day</span></div>
        </AccordionSection>
        <AccordionSection :key="'table' + viewVersion" title="Day by day — newest first" :count="days.length" default-open red>
          <div v-if="days.length" class="mx-wrap target-table-wrap"><table class="tbl tgt-tbl"><thead><tr><th>Date</th><th class="num">Gross</th><th class="num">GST</th><th class="num">Loan cut</th><th class="num">Collected (net)</th><th class="num">Target that day</th><th class="num">+/-</th><th class="num">Cumulative</th><th>Result</th></tr></thead><tbody><tr v-for="day in [...days].reverse()" :key="day.d" :class="day.hit === 1 ? 'tgt-hit' : 'tgt-miss'"><td><b>{{ date(day.d) }}</b></td><td class="num" style="color:var(--mut)">{{ money(day.gross) }}</td><td class="num a">{{ money(day.gst) }}</td><td class="num" :style="{color:Number(day.cut)>0?'#C62828':'var(--mut)'}">{{ Number(day.cut)>0 ? '-' + money(day.cut) : '—' }}</td><td class="num" style="font-weight:800">{{ money(day.got) }}</td><td class="num">{{ money(day.req) }}</td><td class="num" :style="{color:day.hit === 1?'#2E7D32':'#C62828'}">{{ Number(day.diff)>=0 ? '+' : '' }}{{ money(day.diff) }}</td><td class="num" style="color:var(--mut)">{{ compact(day.cum) }}</td><td><span class="pill" :class="day.hit === 1 ? 'p-g' : 'p-r'">{{ day.hit === 1 ? 'HIT' : 'MISS' }}</span></td></tr><tr style="background:#F1F8E9;font-weight:800"><td>TOTAL</td><td class="num">{{ money(tracker.gross) }}</td><td class="num">{{ money(tracker.gst) }}</td><td class="num">{{ Number(tracker.cut)>0 ? '-' + money(tracker.cut) : '—' }}</td><td class="num">{{ money(tracker.achieved) }}</td><td></td><td></td><td class="num">{{ compact(tracker.achieved) }}</td><td></td></tr></tbody></table></div><div v-else class="note">No elapsed days in this cycle yet.</div>
        </AccordionSection>
        <AccordionSection :key="'formula' + viewVersion" title="How the daily target works" :count="1">
          <div class="formula"><b>Basis — realisation is measured NET, not on gross receipts.</b><br>For every Payment Entry: <code>ex-GST = paid_amount × 100/105</code>, then loan modes lose a further <code>15% of ex-GST</code>. <code>Collected (net) = ex-GST − loan cut</code>.<br>Loan modes: Bajaj, Sai Roshini, Fibe, Carepay, Savein, Loan Tap / Uno, ShopSE, Liqui Loans. Every other mode (Cash, Card, UPI, Bank, Razorpay) has GST removed but no cut.<br>This cycle: gross <b>{{ money(tracker.gross) }}</b> − GST <b>{{ money(tracker.gst) }}</b> − loan cut <b>{{ money(tracker.cut) }}</b> = <b>{{ money(tracker.achieved) }}</b>.<br><br>This uses the <b>deficit method</b>, not a flat daily split.<br><br>Each day: <code>target that day = (monthly target − collected so far) ÷ days still remaining</code>.<br><br>So a miss automatically raises the bar for every day after it, and a big day lowers it. Cycle is <b>{{ date(tracker.cycle_from) }} → {{ date(tracker.cycle_to) }}</b> ({{ tracker.total_days }} days, 6th→5th).<br><br>This tracker reports on whichever cycle the <b>range start</b> falls in, so the <b>Last Cycle</b> preset shows that cycle’s target and day-by-day result. The target is not pro-rated for a partial range — it is always the full cycle target of <b>{{ compact(tracker.target) }}</b>. Collections come from Payment Entry, <code>docstatus=1</code>, branch <b>{{ branch }}</b>.</div>
        </AccordionSection>
      </template>
    </div>
  </section>
</template>

<style>
.btgt{
  --g900:#0F3D1E;--g800:#14501F;--g700:#1B5E20;--g600:#2E7D32;--g500:#43A047;--g400:#66BB6A;
  --g100:#E8F5E9;--g50:#F3FAF4;--ink:#152418;--mut:#5F6F63;--line:#DCE9DE;--red:#C62828;--amb:#E65100;
  --card:#FFFFFF;--shadow:0 1px 2px rgba(15,61,30,.06),0 4px 14px rgba(15,61,30,.07);--r:14px;
  font-family:'Inter','Segoe UI',system-ui,sans-serif;background:var(--g50);color:var(--ink);
  font-size:14px;line-height:1.45;display:block;position:relative;min-height:100vh;padding:16px 18px;box-sizing:border-box;
}


.btgt *{box-sizing:border-box}
.btgt .btgt-head{
    display:flex;
    align-items:center;
    gap:12px;
    flex-wrap:wrap;
    margin-bottom:16px;

    /* space for Portal Home fullscreen back button */
    padding-left:44px;
}
.btgt .btgt-title{font-size:16px;font-weight:800;color:var(--g800);letter-spacing:.3px}
.btgt select,.btgt input[type=date]{height:34px;padding:5px 10px;border:1px solid #b0bec5;border-radius:8px;font-size:13px;background:#fff;color:var(--ink)}
.btgt .btgt-btn{height:34px;padding:6px 16px;border:none;border-radius:8px;background:var(--g600);color:#fff;font-weight:700;font-size:13px;cursor:pointer}
.btgt .btgt-chip{height:34px;padding:6px 12px;border:1px solid #a5d6a7;border-radius:8px;background:#e8f5e9;color:#2e7d32;font-weight:600;font-size:12px;cursor:pointer}
.btgt .btgt-chip.active{background:#2e7d32;color:#fff;border-color:#2e7d32}
.btgt .m-kpis{display:flex;gap:10px;padding:14px 16px;background:#F3FAF4;border:1px solid #DCE9DE;border-radius:12px;flex-wrap:wrap;margin-bottom:14px}
.btgt .m-kpi{flex:1;min-width:100px;text-align:center}
.btgt .m-kpi b{display:block;font-size:18px;color:#14501F}
.btgt .m-kpi b.r{color:#C62828}.btgt .m-kpi b.a{color:#E65100}
.btgt .m-kpi span{font-size:9px;color:#5F6F63;text-transform:uppercase;letter-spacing:.6px;font-weight:700}
.btgt .tbl{width:100%;border-collapse:collapse;font-size:12px}
.btgt .tbl th,.btgt .tbl td{border:1px solid #E3EEE5;padding:6px 8px;text-align:left;white-space:nowrap}
.btgt .tbl th{background:#37474f;color:#fff;font-weight:700}
.btgt .tbl td.num,.btgt .tbl th.num{text-align:right}
.btgt .formula{background:#F3FAF4;border-left:3px solid var(--g500);padding:10px 12px;font-size:11.5px;color:#37474f;border-radius:6px;line-height:1.6}
.btgt .formula code{background:#E8F5E9;padding:1px 5px;border-radius:4px;font-size:11px}
.btgt .note{color:var(--mut);font-size:12px;padding:8px}


/* ===== extracted target modal styles ===== */
.btgt .num {
    font-variant-numeric: tabular-nums;
    font-feature-settings: "tnum";
}
/* ============================================================
   CARDS
   ============================================================ */
.btgt .card {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: var(--r);
    padding: 14px 16px;
    box-shadow: var(--shadow);
    margin-bottom: 14px;
}
.btgt .card h3 {
    font-size: 12.5px;
    font-weight: 700;
    letter-spacing: .6px;
    color: var(--g800);
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    text-transform: uppercase;
}
/* ============================================================
   PILLS
   ============================================================ */
.btgt .pill {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 99px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: .5px;
}
.btgt .p-g {
    background: #E8F5E9;
    color: #1B5E20;
}
.btgt .p-r {
    background: #FDECEA;
    color: #C62828;
}
.btgt .p-gr {
    background: #ECEFF1;
    color: #546E7A;
}
.btgt .m-kpis {
    display: flex;
    gap: 10px;
    padding: 14px 22px;
    background: #F3FAF4;
    border-bottom: 1px solid #DCE9DE;
    flex-wrap: wrap;
    flex-shrink: 0;
}
.btgt .m-kpi {
    flex: 1;
    min-width: 100px;
    text-align: center;
}
.btgt .m-kpi b {
    display: block;
    font-size: 18px;
    color: #14501F;
}
.btgt .m-kpi b.r { color: #C62828; }
.btgt .m-kpi b.a { color: #E65100; }
.btgt .m-kpi span {
    font-size: 9px;
    color: #5F6F63;
    text-transform: uppercase;
    letter-spacing: .6px;
    font-weight: 700;
}
.btgt {
    padding: 16px 22px;
    overflow-y: auto;
    flex: 1;
    color: #152418;
    background: #fff;
}
.btgt .csec {
    border: 1px solid #DCE9DE;
    border-radius: 10px;
    margin-bottom: 10px;
    overflow: hidden;
}
.btgt .csec-h {
    width: 100%;
    background: #F3FAF4;
    border: none;
    padding: 10px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 700;
    font-size: 12px;
    color: #14501F;
    text-align: left;
    cursor: pointer;
}
.btgt .csec-h .cnt {
    margin-left: auto;
    background: #E8F5E9;
    color: #1B5E20;
    padding: 2px 8px;
    border-radius: 99px;
    font-size: 10px;
}
.btgt .csec-h .cnt.r {
    background: #FDECEA;
    color: #C62828;
}
.btgt .csec-b {
    display: none;
    padding: 12px 14px;
}
.btgt .csec.open .csec-b {
    display: block;
}
.btgt .csec.open .car {
    transform: rotate(180deg);
}
.btgt .car {
    transition: transform .2s;
    font-size: 9px;
}
.btgt .mx-wrap {
    overflow-x: auto;
}
.btgt table {
    border-collapse: collapse;
    width: 100%;
    font-size: 11px;
}
.btgt table th,
.btgt table td {
    border: 1px solid #DCE9DE;
    padding: 5px 8px;
    text-align: right;
    white-space: nowrap;
}
.btgt table th:first-child,
.btgt table td:first-child {
    text-align: left;
}
.btgt table th {
    background: #E8F5E9;
    color: #14501F;
    font-weight: 800;
    font-size: 10px;
    text-transform: uppercase;
}
.btgt table tr.tot td {
    background: #F3FAF4;
    font-weight: 800;
}
.btgt table tr.net td {
    background: #F1F8E9;
    font-weight: 800;
    color: #14501F;
}
.btgt table tr.grp td {
    background: #1B5E20;
    color: #fff;
    font-weight: 800;
    font-size: 9px;
    text-transform: uppercase;
}
.btgt .who {
    display: flex;
    align-items: center;
    gap: 8px;
}
.btgt .ww {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #E8F5E9;
    color: #1B5E20;
    font-size: 9px;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
}
.btgt .wn {
    font-weight: 700;
}
.btgt .gchips {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
.btgt .gchip {
    flex: 1;
    min-width: 80px;
    border: 1px solid #DCE9DE;
    border-radius: 10px;
    padding: 9px;
    text-align: center;
    background: #F3FAF4;
}
.btgt .gchip b {
    display: block;
    font-size: 16px;
    color: #14501F;
}
.btgt .gchip.r b { color: #C62828; }
.btgt .gchip.a b { color: #E65100; }
.btgt .gchip span {
    font-size: 9px;
    color: #5F6F63;
    text-transform: uppercase;
    font-weight: 700;
}
.btgt .formula {
    background: #F3FAF4;
    border-left: 3px solid #43A047;
    padding: 8px 12px;
    border-radius: 0 8px 8px 0;
    font-size: 11.5px;
    color: #5F6F63;
}
.btgt .note {
    font-size: 11px;
    color: #5F6F63;
}
.btgt .hbar {
    height: 7px;
    border-radius: 99px;
    background: #E8F5E9;
    overflow: hidden;
    flex: 1;
}
.btgt .hbar i {
    display: block;
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, #43A047, #1B5E20);
}
.btgt .pill {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 99px;
    font-size: 10px;
    font-weight: 800;
}
.btgt .p-g {
    background: #E8F5E9;
    color: #1B5E20;
}
.btgt .p-a {
    background: #FFF3E0;
    color: #E65100;
}
.btgt .p-r {
    background: #FDECEA;
    color: #C62828;
}
.btgt .p-gr {
    background: #ECEFF1;
    color: #546E7A;
}
/* ============================================================
   NOTE / GCHIPS / FORMULA / CSC
   ============================================================ */
.btgt .note {
    font-size: 11px;
    color: var(--mut);
}
.btgt .formula {
    background: var(--g50);
    border-left: 3px solid var(--g500);
    padding: 8px 12px;
    border-radius: 0 8px 8px 0;
    font-size: 11.5px;
    color: var(--mut);
}
.btgt .csec {
    border: 1px solid var(--line);
    border-radius: 10px;
    margin-bottom: 10px;
    overflow: hidden;
}
.btgt .csec-h {
    width: 100%;
    background: var(--g50);
    border: none;
    padding: 10px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 700;
    font-size: 12px;
    color: var(--g800);
    text-align: left;
}
.btgt .csec-h .cnt {
    margin-left: auto;
    background: var(--g100);
    color: var(--g700);
    padding: 2px 8px;
    border-radius: 99px;
    font-size: 10px;
}
.btgt .csec-h .cnt.r {
    background: #FDECEA;
    color: var(--red);
}
.btgt .csec-b {
    display: none;
    padding: 12px 14px;
}
.btgt .csec.open .csec-b {
    display: block;
}
.btgt .csec.open .car {
    transform: rotate(180deg);
}
.btgt .car {
    transition: transform .2s;
    font-size: 9px;
}
/* ============================================================
   v16 — Daily target tracker (deficit method)
   ============================================================ */
.btgt .tgt-mini {
    margin-top: 6px;
    display: inline-block;
    padding: 2px 9px;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.03em;
}
.btgt .tgt-mini.ok { background: #E8F5E9; color: #1B5E20; }
.btgt .tgt-mini.warn { background: #FDECEA; color: #C62828; }
.btgt .tgt-need {
    padding: 16px 18px;
    border-radius: 12px;
    margin-bottom: 14px;
    border-left: 5px solid #C62828;
    background: linear-gradient(135deg, #FFF5F5 0%, #FDECEA 100%);
}
.btgt .tgt-need.ok {
    border-left-color: #2E7D32;
    background: linear-gradient(135deg, #F4FBF5 0%, #E8F5E9 100%);
}
.btgt .tgt-need-l {
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #5F6F63;
}
.btgt .tgt-need-v {
    font-size: 34px;
    font-weight: 800;
    line-height: 1.15;
    margin: 4px 0 2px;
    color: #C62828;
}
.btgt .tgt-need.ok .tgt-need-v { color: #1B5E20; }
.btgt .tgt-need-v span {
    font-size: 15px;
    font-weight: 700;
    color: #5F6F63;
    margin-left: 4px;
}
.btgt .tgt-need-s { font-size: 12px; color: #5F6F63; }
.btgt .tgt-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 8px;
}
.btgt .tgt-cell {
    padding: 9px 12px;
    border: 1px solid #E3EEE5;
    border-radius: 8px;
    background: #FAFCFA;
}
.btgt .tgt-cell span {
    display: block;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #7A8B7E;
    margin-bottom: 3px;
}
.btgt .tgt-cell b { font-size: 14px; font-weight: 800; color: #1B5E20; }
.btgt .tgt-cell b.r { color: #C62828; }
/* Day-by-day bar strip */
.btgt .tgt-strip {
    display: flex;
    align-items: flex-end;
    gap: 3px;
    overflow-x: auto;
    padding: 6px 2px 0;
}
.btgt .tgt-bar {
    flex: 1 0 22px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
}
.btgt .tgt-bar-wrap {
    position: relative;
    width: 100%;
    height: 96px;
    background: #F1F6F2;
    border-radius: 4px;
    overflow: hidden;
}
.btgt .tgt-bar-wrap i {
    position: absolute;
    left: 0;
    bottom: 0;
    width: 100%;
    display: block;
    border-radius: 4px 4px 0 0;
}
.btgt .tgt-bar-wrap i.ok { background: linear-gradient(180deg, #43A047, #1B5E20); }
.btgt .tgt-bar-wrap i.no { background: linear-gradient(180deg, #EF9A9A, #C62828); }
.btgt .tgt-bar-wrap u {
    position: absolute;
    left: 0;
    width: 100%;
    height: 0;
    border-top: 2px dashed #33475B;
    opacity: 0.55;
}
.btgt .tgt-bar span {
    font-size: 9px;
    font-weight: 700;
    color: #7A8B7E;
}
.btgt .tgt-legend {
    display: flex;
    gap: 14px;
    margin-top: 10px;
    font-size: 11px;
    font-weight: 600;
    color: #5F6F63;
}
.btgt .tgt-legend span { display: flex; align-items: center; gap: 5px; }
.btgt .tgt-legend i.sw {
    width: 11px;
    height: 11px;
    border-radius: 3px;
    display: inline-block;
}
.btgt .tgt-legend i.sw.ok { background: #2E7D32; }
.btgt .tgt-legend i.sw.no { background: #C62828; }
.btgt .tgt-legend i.sw.line {
    height: 0;
    border-top: 2px dashed #33475B;
    border-radius: 0;
    width: 16px;
}
.btgt .tgt-tbl tr.tgt-hit  td { background: #F6FBF7; }
.btgt .tgt-tbl tr.tgt-miss td { background: #FFFAFA; }
/* --- Source Wise / CC Leads drawer tables --- */
.btgt .mx .tbl td.a,
.btgt .tbl td.a {
    color: #E65100;
}
/* Keep the wider GST tables readable inside the drawer */
.btgt .btgt .m-bd .tbl th,
.btgt .btgt .m-bd .tbl td {
    white-space: nowrap;
}

/* =========================================================
   PORTAL FULLSCREEN BACK BUTTON SPACE
========================================================= */

.btgt .btgt-head{
    padding-left:44px;
    min-height:40px;
}
</style>
