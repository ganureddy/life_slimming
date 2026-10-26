<script setup>
import {computed,onBeforeUnmount,onMounted,ref,watch,nextTick} from 'vue';
import {useEmployeeAnalytics} from '../composables/useEmployeeAnalytics';
import EmployeeReportTable from '../components/employee-sale/EmployeeReportTable.vue';
import EmployeeReportSelect from '../components/employee-sale/EmployeeReportSelect.vue';
import EmployeeReportKpis from '../components/employee-sale/EmployeeReportKpis.vue';
import EmployeeReportBars from '../components/employee-sale/EmployeeReportBars.vue';
import TreatmentTree from '../components/employee-sale/TreatmentTree.vue';
const {S,calc,from,to,period,setPeriod,filters,options,tab,branches,locked,loading,error,amountError,loaded,view,matrix,matrixColumns,bookingRows,load,reset,modal,drill,openEmployee,openBranch,exportExcel}=useEmployeeAnalytics();
const collapsed=ref(false),tree=ref(null),print=()=>window.print();
const overviewKpis=computed(()=>{const t=view.value.totals;return [['Invoices',t.invoices,t.clients+' clients'],['Employees Credited',t.employees,calc.keys(t.shared)+' shared invoices','k-grey'],['Paid ex-GST',calc.fmt(t.ex),calc.compact(t.ex),'k-mint'],['Referrer Share',calc.fmt(t.ref),calc.pct(t.ref,t.ex).toFixed(1)+'% of ex-GST','k-blue'],['Incentive Share',calc.fmt(t.inc),calc.pct(t.inc,t.ex).toFixed(1)+'% of ex-GST','k-orange'],['GST',calc.fmt(t.gst),calc.compact(t.gst),'k-teal'],['Paid w/ GST',calc.fmt(t.paid),calc.compact(t.paid)],['Avg per Invoice',calc.fmt(t.invoices?t.ex/t.invoices:0),'ex-GST','k-grey'],['Current Outstanding',calc.fmt(t.out),'on credited invoices','k-red']];});
const branchKpis=computed(()=>{const t=view.value.totals,b=view.value.br[0];return [['Active Branches',view.value.br.length],['Paid ex-GST',calc.fmt(t.ex),calc.compact(t.ex),'k-mint'],['Top Branch',b?.name||'—',b?calc.fmt(b.ex)+' · '+b.share.toFixed(1)+'%':'','k-teal'],['Current Outstanding',calc.fmt(t.out),calc.compact(t.out),'k-red']];});
const treatmentKpis=computed(()=>{const tr=view.value.tr,mapped=tr.tree.filter(n=>n.k!=='__NONE__'),top=mapped[0];return [['Main Categories',mapped.length,tr.tree.reduce((s,n)=>s+n.kids.length,0)+' therapy groups'],['Treatment Share ex-GST',calc.fmt(tr.total),calc.compact(tr.total),'k-mint'],['Leading Category',top?calc.lbl(top.k):'—',top?calc.fmt(top.share)+' · '+calc.pct(top.share,tr.total).toFixed(1)+'%':'','k-teal'],['Unmapped Treatments',tr.unmapped.length,calc.fmt(tr.unmapped.reduce((s,n)=>s+n.share,0))+' missing category / group',tr.unmapped.length?'k-orange':'k-grey']];});
const employeeBars=computed(()=>view.value.emp.slice(0,10).map(e=>({label:e.name,sub:e.branches,value:e.ex,note:e.invoices+' inv'})));
const branchBars=computed(()=>view.value.br.map(b=>({label:b.name,value:b.ex,note:b.share.toFixed(1)+'%'})));
const categoryBars=computed(()=>view.value.tr.tree.map(n=>({label:calc.lbl(n.k),value:n.share,note:calc.pct(n.share,view.value.tr.total).toFixed(1)+'% · '+n.invoices+' inv'})));
const modeBars=computed(()=>{const m=new Map();for(const c of view.value.credits){const k=c.inv.mop||'(Unmapped)',r=m.get(k)||{label:k,value:0,inv:new Set()};r.value+=c.ex;r.inv.add(c.inv.invoice);m.set(k,r);}return [...m.values()].sort((a,b)=>b.value-a.value).slice(0,10).map(r=>({...r,note:r.inv.size+' inv'}));});
const drillKpis=computed(()=>{const e=drill.value?.summary;if(!e)return [];return [['Invoices',e.invoices,e.clients+' clients'],['Paid ex-GST',calc.fmt(e.ex),calc.compact(e.ex),'k-mint'],['Referrer Share',calc.fmt(e.ref),'','k-blue'],['Incentive Share',calc.fmt(e.inc),'','k-orange'],['Outstanding',calc.fmt(e.out),'allocated','k-red']];});
const chips=computed(()=>Object.entries(filters).flatMap(([key,value])=>Array.isArray(value)?value.map(v=>({key,value:v,label:(options.value[key]?.find(o=>o.value===v)?.label||v)})):value&&key!=='branch'||value&&key==='branch'&&!locked.value?[{key,value,label:key+': '+value}]:[]));
function removeChip(c){if(Array.isArray(filters[c.key]))filters[c.key]=filters[c.key].filter(v=>v!==c.value);else filters[c.key]=typeof c.value==='boolean'?false:'';}
let returnFocus,previousOverflow;
watch(modal,async open=>{if(open){returnFocus=document.activeElement;previousOverflow=document.body.style.overflow;document.body.style.overflow='hidden';await nextTick();document.getElementById('esr-modal-x')?.focus();}else{document.body.style.overflow=previousOverflow??'';returnFocus?.focus();}});
function keydown(e){if(!modal.value)return;if(e.key==='Escape')modal.value=false;if(e.key==='Tab'){const items=[...document.querySelectorAll('#esr-modal button,#esr-modal input,#esr-modal a')].filter(el=>el.getClientRects().length);const first=items[0],last=items.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}}}
onMounted(()=>document.addEventListener('keydown',keydown));onBeforeUnmount(()=>{document.removeEventListener('keydown',keydown);if(modal.value)document.body.style.overflow=previousOverflow??'';});
</script>
<template><section class="employee-sale-master-page">
<div class="esr" id="esr-root">


  <header class="esr-head">
    <div class="esr-head-main">
      <div class="esr-kicker">Sales &amp; Collection Analytics</div>
      <h1 class="esr-title">Sales Master Report</h1>
      <div class="esr-sub">Collections credited to referring &amp; incentive employees — by employee, branch, treatment category and payment mode</div>
    </div>
    <div class="esr-head-side">
      <div class="esr-meta">
        <span class="esr-meta-chip"><em>Source</em> REFERRAL REPORT – FIXED</span>
        <span class="esr-meta-chip"><em>Period</em> <b id="esr-meta-period">{{loaded?calc.dmy(loaded.from)+' to '+calc.dmy(loaded.to):'—'}}</b></span>
        <span class="esr-meta-chip"><em>Loaded</em> <b id="esr-meta-loaded">{{loaded?.at||'—'}}</b></span>
      </div>
      <div class="esr-head-actions">
        <button type="button" class="esr-btn esr-btn-ghost" id="esr-btn-export" @click="exportExcel" :disabled="loading||!loaded||!!amountError">&#11015; Export Excel</button>
        <button type="button" class="esr-btn esr-btn-ghost" id="esr-btn-print" @click="print">&#128424; Print</button>
      </div>
    </div>
  </header>


  <section class="esr-filters" id="esr-filters">
    <div class="esr-fhead">
      <div class="esr-fhead-l">
        <button type="button" class="esr-collapse" id="esr-fcollapse" @click="collapsed=!collapsed" :aria-expanded="!collapsed" title="Show / hide filters">&#9662;</button>
        <div>
          <div class="esr-ftitle">Report Filters</div>
          <div class="esr-fhint">Period loads data from the server. Every other filter applies instantly.</div>
        </div>
      </div>
      <div class="esr-fhead-r">
        <button type="button" class="esr-btn esr-btn-outline" id="esr-btn-reset" @click="reset">&#8634; Reset</button>
        <button type="button" class="esr-btn esr-btn-primary" id="esr-btn-load" @click="load" :disabled="loading">&#9654; Load Data</button>
      </div>
    </div>

    <div class="esr-fbody" id="esr-fbody" v-show="!collapsed">
      <div class="esr-fgrid">


        <div class="esr-fgroup esr-g-period">
          <div class="esr-fg-hdr"><span class="esr-fg-ico">&#128197;</span>Period <small>Payment date</small></div>
          <div class="esr-fg-body">
            <div class="esr-frow2">
              <label class="esr-field"><span class="esr-lbl">From</span><input type="date" class="esr-input" id="esr-f-from" v-model="from" @input="period=''"></label>
              <label class="esr-field"><span class="esr-lbl">To</span><input type="date" class="esr-input" id="esr-f-to" v-model="to" @input="period=''"></label>
            </div>
            <div class="esr-quick" id="esr-quick">
              <button type="button" class="esr-q" data-range="today" :class="{on:period==='today'}" @click="period='today';setPeriod()">Today</button>
              <button type="button" class="esr-q" data-range="yesterday" :class="{on:period==='yesterday'}" @click="period='yesterday';setPeriod()">Yesterday</button>
              <button type="button" class="esr-q on" data-range="cycle" :class="{on:period==='cycle'}" @click="period='cycle';setPeriod()">This Cycle</button>
              <button type="button" class="esr-q" data-range="lastcycle" :class="{on:period==='lastcycle'}" @click="period='lastcycle';setPeriod()">Last Cycle</button>
              <button type="button" class="esr-q" data-range="calmonth" :class="{on:period==='calmonth'}" @click="period='calmonth';setPeriod()">Calendar Month</button>
              <button type="button" class="esr-q" data-range="fy" :class="{on:period==='fy'}" @click="period='fy';setPeriod()">This FY</button>
            </div>
            <div class="esr-fnote">Cycle = 6th to 5th of next month</div>
          </div>
        </div>


        <div class="esr-fgroup">
          <div class="esr-fg-hdr"><span class="esr-fg-ico">&#128101;</span>People &amp; Place</div>
          <div class="esr-fg-body">
            <label class="esr-field"><span class="esr-lbl">Branch</span>
              <select class="esr-input" id="esr-f-branch" v-model="filters.branch" :disabled="!!locked"><option value="">All Branches</option><option v-for="b in branches" :key="b">{{b}}</option></select>
            </label>
            <div class="esr-field"><span class="esr-lbl">Employee</span><EmployeeReportSelect v-model="filters.emp" :options="options.emp||[]" label="emp" all-label="All Employees"/></div>
            <div class="esr-frow2">
              <div class="esr-field"><span class="esr-lbl">Credit Role</span><EmployeeReportSelect v-model="filters.role" :options="options.role||[]" label="role" all-label="Both Roles"/></div>
              <div class="esr-field"><span class="esr-lbl">Sharing Type</span><EmployeeReportSelect v-model="filters.sharing" :options="options.sharing||[]" label="sharing" all-label="All Types"/></div>
            </div>
          </div>
        </div>


        <div class="esr-fgroup esr-g-treat">
          <div class="esr-fg-hdr"><span class="esr-fg-ico">&#10022;</span>Treatment</div>
          <div class="esr-fg-body">
            <div class="esr-field"><span class="esr-lbl">Main Category</span><EmployeeReportSelect v-model="filters.category" :options="options.category||[]" label="category" all-label="All Main Categories"/></div>
            <div class="esr-field"><span class="esr-lbl">Therapy Group</span><EmployeeReportSelect v-model="filters.group" :options="options.group||[]" label="group" all-label="All Therapy Groups"/></div>
            <div class="esr-field"><span class="esr-lbl">Therapy Type</span><EmployeeReportSelect v-model="filters.type" :options="options.type||[]" label="type" all-label="All Therapy Types"/></div>
            <div class="esr-field">
              <span class="esr-lbl">Amount Basis <i class="esr-tip" title="Full Invoice: the whole collected amount of every invoice whose plan contains the selected treatment. Treatment Share: only the part of the collection that belongs to the selected treatment lines (split across the plan's therapy lines).">?</i></span>
              <div class="esr-seg" id="esr-basis">
                <button type="button" data-basis="full" :class="{on:S.basis==='full'}" @click="S.basis='full'">Full Invoice</button>
                <button type="button" data-basis="share" :class="{on:S.basis==='share'}" @click="S.basis='share'">Treatment Share</button>
              </div>
            </div>
          </div>
        </div>


        <div class="esr-fgroup">
          <div class="esr-fg-hdr"><span class="esr-fg-ico">&#8377;</span>Payment &amp; Amount</div>
          <div class="esr-fg-body">
            <div class="esr-frow2">
              <div class="esr-field"><span class="esr-lbl">Booking Type</span><EmployeeReportSelect v-model="filters.booking" :options="options.booking||[]" label="booking" all-label="All Booking Types"/></div>
              <div class="esr-field"><span class="esr-lbl">Mode of Payment</span><EmployeeReportSelect v-model="filters.mop" :options="options.mop||[]" label="mop" all-label="All Modes"/></div>
            </div>
            <div class="esr-frow2">
              <label class="esr-field"><span class="esr-lbl">Paid ex-GST from</span><input type="text" inputmode="decimal" class="esr-input esr-amt" id="esr-f-paid-min" v-model="filters.paidMin" placeholder="Min ₹"></label>
              <label class="esr-field"><span class="esr-lbl">to</span><input type="text" inputmode="decimal" class="esr-input esr-amt" id="esr-f-paid-max" v-model="filters.paidMax" placeholder="Max ₹"></label>
            </div>
            <div class="esr-frow2">
              <label class="esr-field"><span class="esr-lbl">Outstanding from</span><input type="text" inputmode="decimal" class="esr-input esr-amt" id="esr-f-out-min" v-model="filters.outMin" placeholder="Min ₹"></label>
              <label class="esr-field"><span class="esr-lbl">to</span><input type="text" inputmode="decimal" class="esr-input esr-amt" id="esr-f-out-max" v-model="filters.outMax" placeholder="Max ₹"></label>
            </div>
            <label class="esr-check"><input type="checkbox" id="esr-f-onlyout" v-model="filters.onlyOut"> Only invoices with outstanding</label>
          </div>
        </div>

      </div>
    </div>

    <div class="esr-chips" id="esr-chips"><button v-for="chip in chips" :key="chip.key+chip.value" type="button" class="esr-chip" @click="removeChip(chip)">{{chip.label}} ×</button></div>
  </section>

  <div id="esr-status" class="esr-status-wrap"><div v-if="error||amountError" class="esr-msg esr-msg-err" role="alert">{{error||amountError}} <button @click="load">Retry</button></div><div v-else-if="loading" class="esr-msg esr-msg-info" role="status">Loading report…</div></div>


  <nav class="esr-tabs" id="esr-tabs">
    <button type="button" class="esr-tab" :class="{on:tab==='overview'}" @click="tab='overview'" data-tab="overview">&#128202; Overview</button>
    <button type="button" class="esr-tab" :class="{on:tab==='employee'}" @click="tab='employee'" data-tab="employee">&#128100; Employee Wise <b class="esr-tc" id="esr-tc-employee">{{view.emp.length}}</b></button>
    <button type="button" class="esr-tab" :class="{on:tab==='branch'}" @click="tab='branch'" data-tab="branch">&#127970; Branch Wise <b class="esr-tc" id="esr-tc-branch">{{view.br.length}}</b></button>
    <button type="button" class="esr-tab" :class="{on:tab==='treatment'}" @click="tab='treatment'" data-tab="treatment">&#10022; Treatment Category <b class="esr-tc" id="esr-tc-treatment">{{view.tr.tree.length}}</b></button>
    <button type="button" class="esr-tab" :class="{on:tab==='txn'}" @click="tab='txn'" data-tab="txn">&#128203; Transaction Detail <b class="esr-tc" id="esr-tc-txn">{{view.invs.length}}</b></button>
  </nav>

  <main class="esr-main">


    <section class="esr-pane" :class="{on:tab==='overview'}" data-pane="overview">
      <div class="esr-basis-note" id="esr-basis-note"><div v-if="view.f.treat" class="esr-msg esr-msg-info">Treatment filter is on · {{S.basis==='share'?'Treatment Share — only the selected therapy portion is counted.':'Full Invoice — whole collections for invoices containing the selected treatment.'}}</div><div v-if="view.empOn" class="esr-msg esr-msg-info">Employee / role filter is on — amounts are the selected employees’ credited share only.</div></div>
      <EmployeeReportKpis id="esr-kpis" :items="overviewKpis"/>
      <div class="esr-grid2">
        <div class="esr-card"><div class="esr-card-hdr"><span>Top Employees</span><span class="esr-badge">Paid ex-GST</span></div><EmployeeReportBars class="esr-card-body" id="esr-ov-emp" :calc="calc" :items="employeeBars" tone=""/></div>
        <div class="esr-card"><div class="esr-card-hdr"><span>Branches</span><span class="esr-badge">Paid ex-GST</span></div><EmployeeReportBars class="esr-card-body" id="esr-ov-branch" :calc="calc" :items="branchBars" tone=""/></div>
      </div>
      <div class="esr-grid2">
        <div class="esr-card"><div class="esr-card-hdr"><span>Main Category Mix</span><span class="esr-badge esr-badge-alt">Treatment share</span></div><EmployeeReportBars class="esr-card-body" id="esr-ov-cat" :calc="calc" :items="categoryBars" tone="teal"/></div>
        <div class="esr-card"><div class="esr-card-hdr"><span>Mode of Payment Mix</span><span class="esr-badge">Invoices · Paid ex-GST</span></div><EmployeeReportBars class="esr-card-body" id="esr-ov-mop" :calc="calc" :items="modeBars" tone=""/></div>
      </div>
      <div class="esr-card">
        <div class="esr-card-hdr"><span>Booking Type Breakdown</span><span class="esr-hsub">Invoices &amp; amounts by booking type</span></div>
        <EmployeeReportTable class="esr-tblbox" data-tbl="booking" :rows="bookingRows" :columns="calc.columns.booking" :calc="calc" :searchable="false" sort-by="ex"/>
      </div>
    </section>


    <section class="esr-pane" :class="{on:tab==='employee'}" data-pane="employee">
      <div class="esr-card">
        <div class="esr-card-hdr"><span>Employee Wise Summary</span><span class="esr-hsub">Click a row for invoice-level drill-down</span></div>
        <EmployeeReportTable class="esr-tblbox" data-tbl="employee" :rows="view.emp" :columns="calc.columns.employee" :calc="calc" what="employees" sort-by="ex" clickable @open="openEmployee"/>
      </div>
    </section>


    <section class="esr-pane" :class="{on:tab==='branch'}" data-pane="branch">
      <EmployeeReportKpis id="esr-br-kpis" :items="branchKpis"/>
      <div class="esr-card">
        <div class="esr-card-hdr"><span>Branch Wise Summary</span><span class="esr-hsub">Click a row to see that branch's employees</span></div>
        <EmployeeReportTable class="esr-tblbox" data-tbl="branch" :rows="view.br" :columns="calc.columns.branch" :calc="calc" what="branches" sort-by="ex" clickable @open="openBranch"/>
      </div>
      <div class="esr-card">
        <div class="esr-card-hdr"><span>Branch × Main Category</span><span class="esr-badge esr-badge-alt">Treatment share · ex-GST</span></div>
        <EmployeeReportTable class="esr-tblbox" data-tbl="matrix" :rows="matrix" :columns="matrixColumns" :calc="calc" :searchable="false" sort-by="total"/>
      </div>
    </section>


    <section class="esr-pane" :class="{on:tab==='treatment'}" data-pane="treatment">
      <EmployeeReportKpis id="esr-tr-kpis" :items="treatmentKpis"/>
      <div class="esr-card">
        <div class="esr-card-hdr">
          <span>Main Category › Therapy Group › Therapy Type</span>
          <span class="esr-hdr-actions">
            <button type="button" class="esr-btn esr-btn-xs" id="esr-tr-expand" @click="tree?.expandAll(true)">Expand all</button>
            <button type="button" class="esr-btn esr-btn-xs" id="esr-tr-collapse" @click="tree?.expandAll(false)">Collapse all</button>
          </span>
        </div>
        <div class="esr-tree-note">Amounts are the collected ex-GST value split across the therapy lines of each plan. Invoice count = invoices whose plan contains that treatment.</div>
        <div class="esr-tblwrap"><table class="esr-table esr-tree"><thead><tr>
          <th>Treatment</th><th class="n">Invoices</th><th class="n">Clients</th><th class="n">Employees</th><th class="n">Treatment Share ex-GST</th><th class="n">Share %</th><th class="n">Full-Invoice ex-GST</th>
        </tr></thead><TreatmentTree ref="tree" :nodes="view.tr.tree" :total="view.tr.total" :calc="calc"/></table></div>
      </div>
      <div class="esr-card esr-card-warn" id="esr-unmapped-card" v-show="view.tr.unmapped.length">
        <div class="esr-card-hdr"><span>Unmapped Therapy Types</span><span class="esr-hsub">No Main Category / Therapy Group in the Therapy Type master — fix these to complete category reporting</span></div>
        <EmployeeReportTable class="esr-tblbox" data-tbl="unmapped" :rows="view.tr.unmapped" :columns="calc.columns.unmapped" :calc="calc" what="therapy types" sort-by="invoices"/>
      </div>
    </section>


    <section class="esr-pane" :class="{on:tab==='txn'}" data-pane="txn">
      <div class="esr-card">
        <div class="esr-card-hdr"><span>Transaction Detail</span><span class="esr-hsub">One row per invoice · click invoice no. to open in ERP</span></div>
        <EmployeeReportTable class="esr-tblbox" data-tbl="txn" :rows="view.invs" :columns="calc.columns.txn" :calc="calc" what="invoices" sort-by="invoice_date" :limit="200"/>
      </div>
    </section>

  </main>


  <div class="esr-modal" id="esr-modal" :class="{open:modal}" :aria-hidden="!modal" role="dialog" aria-modal="true" :aria-label="drill?.title" @mousedown.self="modal=false">
    <div class="esr-modal-box">
      <div class="esr-modal-hdr">
        <div><div class="esr-modal-title" id="esr-modal-title">{{drill?.title}}</div><div class="esr-modal-sub" id="esr-modal-sub">{{drill?.subtitle}}</div></div>
        <button type="button" class="esr-modal-x" id="esr-modal-x" @click="modal=false">&times;</button>
      </div>
      <div class="esr-modal-body" id="esr-modal-body"><template v-if="drill"><EmployeeReportKpis v-if="drill.summary" :items="drillKpis"/><div class="esr-card"><EmployeeReportTable :key="drill.title+drill.kind" id="esr-drill-box" class="esr-tblbox" :rows="drill.rows" :columns="drill.columns" :calc="calc" :sort-by="drill.kind==='branch'?'ex':'invoice_date'" :clickable="drill.kind==='branch'" @open="openEmployee"/></div></template></div>
    </div>
  </div>

</div></section></template>
<style scoped src="../styles/employee-sale-master.css"></style>
