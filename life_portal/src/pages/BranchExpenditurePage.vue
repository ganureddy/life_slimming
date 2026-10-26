<script setup>
import {computed} from 'vue';
import {useBranchExpenditure} from '../composables/useBranchExpenditure';
import {billUrl,displayDate,money,rowFlow} from '../lib/expenditure-domain';
import ExpenditureJournalDialog from '../components/native/ExpenditureJournalDialog.vue';
const {ledgers,config,booting,staff,staffLoading,entries,summary,loading,busy,exporting,error,notice,hasMore,finished,unsaved,quick,clock,filters,applied,rows,form,total,grandTotal,accounts,disabled,journalOpen,journal,journalLoading,journalBusy,journalError,journalNotice,journalDate,initialize,addRow,clearForm,typeChanged,removeRow,billChanged,fileChanged,loadStaff,loadHistory,chooseRange,save,openDraft,exportCsv,viewJournal,changeJournalDate}=useBranchExpenditure();
const dateText=computed(()=>clock.value.toLocaleDateString('en-GB',{timeZone:'Asia/Kolkata',day:'2-digit',month:'short',year:'2-digit'}).replace(/ /g,'-'));
const timeText=computed(()=>clock.value.toLocaleTimeString('en-IN',{timeZone:'Asia/Kolkata',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:true}));
const options=row=>ledgers.LM_OPTIONS[row.type]||[ledgers.LM[row.type]].filter(Boolean);
const partyRequired=row=>['Receivable','Payable'].includes(config.value?.accounts.find(a=>a.name===row.account)?.account_type);
const historyRows=computed(()=>entries.value.flatMap(e=>e.items.map((item,index)=>({entry:e,item,first:index===0}))));
const savedBill=item=>{let url=item.bill_url;if(item.legacy_bill_encoded)try{url=decodeURIComponent(url);}catch{}return billUrl(url);};
</script>
<template><section class="branch-expenditure-page"><div id="expApp" class="life-exp-shell"><p v-if="booting" role="status">Loading expenditure configuration…</p>


  <header class="life-exp-hero">
    <div class="life-exp-brand">
      <div class="life-exp-logo" aria-label="LIFE">
        <div class="life-exp-logo-letter">L</div>
      </div>
      <div class="life-exp-brand-copy">
        <h1>LIFE SLIMMING &amp; COSMETIC PVT.LTD.</h1>
        <p>BRANCH EXPENDITURE • CASH CONTROL • JOURNAL ENTRY • HO &amp; BRANCH</p>
        <a class="life-exp-go-app-btn"
           href="https://portal.lifescc.com/app/healthcare"
           target="_self"
           aria-label="Go to LIFE Healthcare App">
          <span aria-hidden="true">↗</span> Go to App
        </a>
      </div>
    </div>

    <div class="life-exp-header-status">
      <div class="life-exp-branch-pill">
        <span class="life-exp-dot"></span>
        <span id="lifeLoginBranch">{{config?config.branches.length===1?'Login Branch: '+config.branches[0]:'Branches: '+config.branches.length+' permitted':booting?'Loading…':'Unable to initialize'}}</span>
      </div>
      <div class="life-exp-clock-pill">
        <span id="lifeExpDate">{{dateText}}</span>
        <strong id="lifeExpTime">{{timeText}}</strong>
      </div>
    </div>
  </header>



  <section class="life-panel" id="expOverview">
    <div class="life-section-head">
      <div>
        <div class="life-section-kicker">BRANCH CASH POSITION</div>
        <h2>Cash Overview</h2>
      </div>
      <div class="life-cycle-badge">Business cycle: 6th to 5th</div>
    </div>

    <div class="topfilter">
      <div class="filter-field filter-field-branch">
        <label for="eFilterBranch">Branch</label>
        <select id="eFilterBranch" v-model="filters.branch" :disabled="!config||loading" class="fsel">
          <option value="">All Branches</option>
        <option v-for="b in config?.branches||[]" :key="b">{{b}}</option></select>
      </div>

      <div class="filter-field">
        <label for="eFilterFrom">From</label>
        <input type="date" id="eFilterFrom" v-model="filters.from_date" :disabled="!config||loading" @input="quick=''" class="finput" />
      </div>

      <div class="filter-field">
        <label for="eFilterTo">To</label>
        <input type="date" id="eFilterTo" v-model="filters.to_date" :disabled="!config||loading" @input="quick=''" class="finput" />
      </div>

      <div class="filter-actions"><button v-for="[key,label] in [['today','Today'],['yesterday','Yesterday'],['month','This Month'],['lastmonth','Last Month'],['fy','This FY']]" :key="key" type="button" class="resetbtn exp-quick-date" :data-range="key" :aria-pressed="quick===key" :disabled="!config||loading" @click="chooseRange(key)">{{label}}</button>
        <button class="filterbtn" id="eFilterBtn" @click="loadHistory()" :disabled="!config||loading">Apply</button>
        <button class="resetbtn" id="eResetBtn" @click="chooseRange('month')" :disabled="!config||loading">Reset</button>
      </div>
    </div>


    <div class="scards scards-all">
      <article class="scard scard-in">
        <div class="scard-topline">
          <div class="scard-icon">💵</div>
          <div class="scard-chip">CASH IN</div>
        </div>
        <div class="scard-amt" id="sCashIn">{{money(summary?.cash_in)}}</div>
        <div class="scard-label">Cash Collected</div>
        <div class="scard-sub">All posted cash debits for the selected cost centers</div>
        <div class="scard-count" id="sCashInCount">Posted cash debits</div>
        <div class="scard-detail" id="sCashInDetail">Includes cash receipts and incoming cash transfers.</div>
      </article>

      <article class="scard scard-exp">
        <div class="scard-topline">
          <div class="scard-icon">📤</div>
          <div class="scard-chip">CASH OUT</div>
        </div>
        <div class="scard-amt" id="sCashOut">{{money(summary?.cash_out)}}</div>
        <div class="scard-label">Cash Spent</div>
        <div class="scard-sub">All posted cash credits, including HO transfers</div>
        <div class="scard-count" id="sCashOutCount">Posted cash credits</div>
        <div class="scard-detail" id="sCashOutDetail">Includes cash expenditure and outgoing cash transfers.</div>
      </article>

      <article class="scard scard-bal">
        <div class="scard-topline">
          <div class="scard-icon">🏦</div>
          <div class="scard-chip">AVAILABLE</div>
        </div>
        <div class="scard-amt" id="sBalance">{{money(summary?.balance)}}</div>
        <div class="scard-label" id="sBalanceLabel">{{summary?.balance<0?'Cash Deficit':'Closing Cash'}}</div>
        <div class="scard-sub">Opening + cash debits − cash credits</div>
        <div class="scard-count">Current available cash</div>
        <div class="scard-detail" id="sBalanceDetail">{{applied?'As of '+displayDate(applied.to_date):''}}</div>
      </article>


      <article class="scard scard-opening" id="sOpeningCard">
        <div class="scard-topline">
          <div class="scard-icon">📅</div>
          <div class="scard-chip">CARRY FORWARD</div>
        </div>
        <div class="scard-amt" id="sOpening">{{money(summary?.opening)}}</div>
        <div class="scard-label" id="sOpeningLabel">Opening Cash</div>
        <div class="scard-sub">Posted ledger balance before the selected From date</div>
        <div class="scard-count">Previous period balance</div>
        <div class="scard-detail" id="sOpeningDetail">{{applied?'Before '+displayDate(applied.from_date):''}}</div>
      </article>

      <article class="scard scard-ho" id="sHOCard">
        <div class="scard-topline">
          <div class="scard-icon">🏢</div>
          <div class="scard-chip">HEAD OFFICE</div>
        </div>
        <div class="scard-amt" id="sHOCash">{{money(summary?.ho_sent)}}</div>
        <div class="scard-label">Cash Sent to HO</div>
        <div class="scard-sub">Branch cash credited; Main cash debited</div>
        <div class="scard-count">Same cash account • different cost centers</div>
        <div class="scard-detail" id="sHODetail">Cash received from branch → Main: {{money(summary?.ho_received)}}; transfers already included in cash debits/credits.</div>
      </article>
    </div>
  </section>


  <section class="expenditure-form" id="eForm">
    <div class="life-panel" id="expEntry">
      <div class="life-section-head life-entry-title">
        <div>
          <div class="life-section-kicker">BRANCH PAYMENT RECORD</div>
          <h2>New Expenditure Entry</h2>
        </div>
        <div class="entry-status-wrap">
          <span class="eno" id="edocno">{{form.name||'New Entry'}}</span>
          <span class="esp" :class="finished?'posted':'draft'" id="estatus">{{finished?'● Submitted':form.name?'● Saved Draft':'● Draft'}}</span>
        </div>
      </div>

      <div class="eh">
        <div class="entry-head-fields">
          <div class="entry-field entry-field-branch">
            <label class="elbl" for="eBranch">Branch <span class="req">*</span></label>
            <select id="eBranch" v-model="form.branch" :disabled="disabled" @change="loadStaff(form.branch)" class="hsel">
              <option value="">— Select Branch —</option>
            <option v-for="b in config?.branches||[]" :key="b">{{b}}</option></select>
          </div>

          <div class="entry-field">
            <label class="elbl" for="eEntryDate">Date <span class="req">*</span></label>
            <input type="date" id="eEntryDate" v-model="form.date" :min="config?.entry_min_date" :max="config?.today" :disabled="disabled" title="Today and the previous two days only" class="hdate" />
          </div>

          <div class="entry-field entry-series">
            <label class="elbl">Series</label>
            <span id="eSeriesDisp">EXP-YYYY-MM-####</span>
          </div>
        </div>
      </div>

      <div class="ec item-card">
        <div class="ech">
          <div>
            <span class="echt">📋 Expenditure Items</span>
            <span class="ech-sub">Add each bill or expense as a separate row</span>
          </div>
          <button class="addbtn" id="eAddBtn" @click="addRow()" :disabled="disabled">+ Add Row</button>
        </div>

        <div class="table-scroll table-scroll-items">
          <table id="eItemTable">
            <thead>
              <tr>
                <th class="c" style="width:38px">#</th>
                <th style="min-width:205px">Expenditure Type</th>
                <th style="min-width:175px">Description</th>
                <th style="min-width:185px">Ledger Category (Auto)</th>
                <th class="r" style="width:125px">Amount (₹)</th>
                <th style="min-width:165px">Remarks</th>
                <th class="c" style="width:58px">Bill?</th>
                <th style="min-width:190px">Attach Bill</th>
                <th style="width:42px"></th>
              </tr>
            </thead>
            <tbody id="eTbody"><tr v-for="(r,i) in rows" :key="r.id" :data-row-id="r.id"><td class="rn">{{i+1}}</td><td><select v-model="r.type" class="etsel" aria-label="Expenditure type" :disabled="disabled" @change="typeChanged(r)"><option value="">Select expenditure</option><option v-for="type in Object.keys(ledgers.LM).sort()" :key="type">{{type}}</option></select><div class="exp-flow">{{rowFlow(r,form,config)}}</div></td><td><input v-model="r.description" class="edesc" type="text" maxlength="500" aria-label="Description" :disabled="disabled"></td><td><select v-model="r.account" class="eledger" aria-label="Ledger" :disabled="disabled"><option value="">Select ledger</option><option v-for="account in options(r)" :key="account">{{account}}</option></select><div v-if="partyRequired(r)" class="exp-item-extra"><select v-model="r.party_type" class="ePartyType" aria-label="Party type" :disabled="disabled"><option value="">Party type</option><option>Customer</option><option>Supplier</option><option>Employee</option></select><input v-model="r.party" class="eParty" placeholder="Exact party ID" aria-label="Party ID" :disabled="disabled"></div></td><td><input v-model="r.amount" class="eamt" type="number" min="0.01" max="1000000000" step="0.01" aria-label="Amount" :disabled="disabled"></td><td><input v-model="r.remarks" class="erm" type="text" maxlength="500" aria-label="Remarks" :disabled="disabled"></td><td class="c"><input v-model="r.bill_required" class="ebill" type="checkbox" aria-label="Bill available" :disabled="disabled" @change="billChanged(r)"></td><td><input class="efile" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" :disabled="disabled" @change="fileChanged(r,$event.target.files?.[0])"><div class="file-preview"><template v-if="r.file">{{r.file.name}} (uploads privately when saved)</template><a v-else-if="billUrl(r.bill_url)" :href="billUrl(r.bill_url)" target="_blank" rel="noopener noreferrer">Saved bill</a></div></td><td><button type="button" class="delbtn" aria-label="Remove row" :disabled="disabled" @click="removeRow(r)">✕</button></td></tr></tbody>
          </table>
        </div>

        <div class="totbar">
          <span class="totlbl">Total Expenditure</span>
          <span class="totamt" id="eTotal">{{money(total)}}</span>
        </div>
      </div>

      <div class="ec payment-card">
        <div class="ech">
          <div>
            <span class="echt">💳 Payment Details</span>
            <span class="ech-sub">Select the branch to load permitted staff and managers</span>
          </div>
          <span id="eBranchHint" class="branch-hint">{{staffLoading?'Loading staff…':staff.length+' staff • '+staff.filter(e=>e.is_approver).length+' approvers'}}</span>
        </div>

        <div class="pgrid">
          <div>
            <label class="flbl" for="ePaidBy">Paid By — Branch Staff <span class="req">*</span></label>
            <input type="text"
                   id="ePaidBy" v-model="form.paid_by" :disabled="disabled||staffLoading||!staff.length"
                   class="staff-combo-input"
                   list="ePaidByOptions"
                   placeholder="— Select Branch First —"
                   autocomplete="off" />
            <datalist id="ePaidByOptions"><option v-for="p in staff" :key="p.name" :value="p.employee_name+' ['+p.name+']'" :label="p.designation"/></datalist>
            <div class="fhint" id="ePaidByHint"></div>
          </div>

          <div>
            <label class="flbl" for="eApprovedBy">Approved By — Branch Manager <span class="req">*</span></label>
            <input type="text"
                   id="eApprovedBy" v-model="form.approved_by" :disabled="disabled||staffLoading||!staff.length"
                   class="staff-combo-input"
                   list="eApprovedByOptions"
                   placeholder="— Select Branch First —"
                   autocomplete="off" />
            <datalist id="eApprovedByOptions"><option v-for="p in staff.filter(e=>e.is_approver)" :key="p.name" :value="p.employee_name+' ['+p.name+']'" :label="p.designation"/></datalist>
            <div class="fhint" id="eApprovedByHint">{{staff.some(e=>e.is_approver)?'Select a manager from suggestions.':'No manager configured. Ask HR to update branch/designation.'}}</div>
          </div>

          <div>
            <label class="flbl" for="ePayMode">Payment Mode <span class="req">*</span></label>
            <select id="ePayMode" v-model="form.payment_mode" :disabled="disabled">
              <option value="">— Select Mode —</option>
              <option>Petty Cash</option>
              <option>Bank</option>
              <option>UPI</option>
              <option>Cheque</option>
              <option>NEFT/RTGS</option>
            </select>
          </div>
        <div><label class="flbl" for="eFundingAccount">Payment Account *</label><select id="eFundingAccount" v-model="form.funding_account" :disabled="disabled||form.payment_mode==='Petty Cash'"><option value="">Select payment ledger</option><option v-for="account in accounts" :key="account">{{account}}</option></select><div class="fhint">Cash is separated by cost center. Select a bank ledger for Bank/UPI/Cheque/NEFT.</div><label class="flbl" for="eReference">Payment Reference</label><input id="eReference" v-model="form.reference" type="text" maxlength="140" placeholder="Bank/UPI/Cheque reference" :disabled="disabled"></div></div>

        <div class="exp-page-actions"><button type="button" class="resetbtn" id="eFresh" :disabled="busy||!config" @click="clearForm()">+ New Entry</button><span id="eDraftHint">Drafts are saved in ERP and can be reopened from the history list.</span></div><div class="acts">
          <button class="bdraft" id="eDraftBtn" @click="save('save')" :disabled="disabled||!config?.can_create">{{busy?'Saving…':'💾 Save Draft'}}</button>
          <button class="bsubmit" id="eSubmitBtn" @click="save('submit')" :disabled="disabled||!config?.can_submit">{{busy?'Saving…':finished?'✓ Submitted':'✓ Submit & Create Journal Entry'}}</button>
        </div>
      </div>
    </div>
  </section>

  <div class="jebox" id="eJeBox" v-show="error||notice" :role="error?'alert':'status'" :style="{color:error?'#b91c1c':'#14532d'}">{{error||notice}} <button v-if="!config&&!booting" type="button" class="resetbtn" @click="initialize">Retry</button><a v-if="form.name" :href="'/app/journal-entry/'+encodeURIComponent(form.name)" target="_blank" rel="noopener">Open Journal Entry</a></div>


  <section class="life-panel history-panel" id="eHistoryCard">
    <div class="life-section-head history-heading">
      <div>
        <div class="life-section-kicker">AUDIT &amp; REVIEW</div>
        <h2>Entries &amp; Saved Drafts</h2>
      </div>
      <div class="history-actions">
        <span class="history-legend">
          <span class="legend-in">↑</span> Cash In
          <span class="legend-ho">→HO</span> To Head Office
        </span>
        <button class="exportbtn" id="eExportBtn" @click="exportCsv" :disabled="!config?.can_export||loading||exporting||!applied">{{exporting?'Exporting…':'↓ Export CSV'}}</button>
      </div>
    </div>

    <div class="table-scroll history-scroll">
      <table id="eHistoryTable">
        <thead>
          <tr>
            <th style="width:38px">#</th>
            <th>Date</th>
            <th>Branch</th>
            <th>Expenditure Type</th>
            <th>Ledger Category</th>
            <th>Description</th>
            <th class="r">Amount (₹)</th>
            <th>Paid By</th>
            <th>Approved By</th>
            <th>Mode</th>
            <th class="c">Bill</th>
            <th class="c">Attach</th>
            <th>Remarks</th><th>Entry / Status</th>
          </tr>
        </thead>
        <tbody id="eHistoryBody"><tr v-if="loading&&!entries.length"><td colspan="14" class="nodata">Loading entries…</td></tr><tr v-else-if="!historyRows.length"><td colspan="14" class="nodata">{{hasMore?'No matching entries in this page. Click Load more to continue.':'No entries in this date range.'}}</td></tr><tr v-for="({entry:e,item:i,first},index) in historyRows" :key="e.name+'|'+index"><td>{{index+1}}</td><td>{{displayDate(e.date)}}</td><td>{{e.branch}}</td><td>{{i.type}}</td><td>{{i.account}}</td><td>{{i.description}}</td><td class="r">{{money(i.amount)}}</td><td>{{first?e.paid_by:''}}</td><td>{{first?e.approved_by:''}}</td><td>{{first?e.payment_mode:''}}</td><td>{{i.bill_url?'Yes':'No'}}</td><td><a v-if="savedBill(i)" :href="savedBill(i)" target="_blank" rel="noopener noreferrer">View bill</a></td><td>{{i.remarks}}</td><td><template v-if="first"><a :href="'/app/journal-entry/'+encodeURIComponent(e.name)" @click.prevent="viewJournal(e.name)">{{e.name}}</a><button type="button" class="resetbtn" @click="viewJournal(e.name)">View JV</button><span class="exp-small">{{e.docstatus===1?e.legacy?'Submitted • legacy posting':'Submitted':'Saved Draft'}}</span><span v-if="billUrl(e.legacy_bill_url)" class="exp-small"><a :href="billUrl(e.legacy_bill_url)" target="_blank" rel="noopener noreferrer">Legacy parent bill</a></span><button v-if="e.docstatus===0&&e.payload" type="button" class="resetbtn" :disabled="busy" @click="openDraft(e)">Open Draft</button></template></td></tr></tbody>
      </table>
    </div>

    <div class="totbar history-total">
      <span class="totlbl">Grand Total (shown)</span>
      <span class="totamt" id="eGrandTotal">{{money(grandTotal)}}</span>
    </div>
  </section>

  <div class="exp-page-actions"><button v-if="hasMore" type="button" class="filterbtn" id="eLoadMore" :disabled="loading" @click="loadHistory(true)">Load more</button><span id="ePageInfo">{{entries.length}} entries loaded • submitted row total shown (includes transfers and receipts)</span></div><ExpenditureJournalDialog v-model="journalOpen" v-model:date="journalDate" :journal="journal" :loading="journalLoading" :busy="journalBusy" :error="journalError" :notice="journalNotice" @save="changeJournalDate"/><footer class="life-exp-footer">
    LIFE Branch Expenditure Control • ERPNext
  </footer>

</div></section></template>
<style scoped src="../styles/branch-expenditure-source.css"></style>
<style scoped>#expApp{width:100%;left:auto;transform:none;margin:0 auto 30px}.exp-page-actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:12px 0}button:disabled{opacity:.55;cursor:wait}.life-exp-shell{min-width:0}.jebox[role=alert]{display:block}@media(max-width:600px){#expApp{width:100%}}</style>
