<script setup>
import { computed, ref } from "vue";

const props = defineProps({ title: String, description: String });
const activeTab = ref("");
const query = ref("");
const branch = ref("All Branches");
const toast = ref("");

const groups = {
  tasks: ["My Tasks", "Approvals Pending"],
  stock: ["Stores 360", "Stock", "Price-List", "Assets"],
  form: ["Branch Expenditures", "Audit Reports", "Billing & Invoices", "Conversions", "Buying / Purchase Orders", "Vendors", "Masters"],
  people: ["Client Info", "Unjoined Clients", "Appointments", "Dietitian Feedback", "Follow-ups", "Employees", "Leaves", "RISE Clients", "Users & Roles"],
  report: ["Employee Sale Master", "Sale Master Data", "WL Results Report", "Financial Reports", "Report Master", "Discount Audit Report", "Approvals Report", "Pending Balances", "Receivables"],
};
const kind = computed(() => Object.keys(groups).find((key) => groups[key].includes(props.title)) || "dashboard");

const special = {
  "My Tasks": {
    tabs: ["Assign Task", "All Tasks", "Assigned By Me", "Assigned To Me", "Tickets"],
    columns: ["Assigned By", "Assigned To", "Category", "Details", "Priority", "Deadline", "Status"],
    rows: [["Priya Rao", "Arjun K", "Operations", "Verify closing checklist", "High", "Today 5:30 PM", "Open"], ["Naveen", "Kavya", "Client Care", "Call pending consultation", "Medium", "21 Sep", "In Progress"], ["Branch Manager", "Accounts Team", "Finance", "Reconcile daily cash", "High", "20 Sep", "Overdue"]],
    action: "Assign Task",
  },
  "Approvals Pending": {
    tabs: ["All Approvals", "Billing", "Expenditure", "Purchase", "Client Requests"],
    columns: ["Request", "Branch", "Requested By", "Type", "Amount", "Stage", "Status"],
    rows: [["APR-2026-0182", "Banjara Hills", "S. Kavya", "Discount", "Rs 18,500", "Level 2 - Audit", "Pending"], ["APR-2026-0179", "Madhapur", "R. Prasad", "Expenditure", "Rs 9,840", "Centre Manager", "Pending"], ["APR-2026-0168", "SR Nagar", "A. Swathi", "Purchase", "Rs 42,100", "Management", "Held"]],
    action: "Refresh",
  },
  "Stores 360": {
    tabs: ["Stock Overview", "Indent Reports", "Indent 360 Info", "Next Order List"],
    columns: ["Item", "Category", "HO Stock", "Branch Stock", "In Transit", "Movement", "Vendor", "Action"],
    rows: [["LIFE Protein Powder", "Nutrition", "186", "24", "40", "High moving", "HealthKart", "+ Add to order"], ["Disposable Bedsheet", "Consumables", "420", "58", "100", "Medium moving", "Med Supply Co.", "+ Add to order"], ["Derma Roller 1.0mm", "Dermatology", "62", "8", "0", "Low stock", "Aesthetic India", "+ Add to order"]],
    action: "Generate Report",
  },
  "Employee Sale Master": {
    tabs: ["Overview", "Employee Wise", "Branch Wise", "Transaction Detail"],
    columns: ["Rank", "Employee", "Branch", "Invoices", "Paid (ex-GST)", "GST Amt", "Grand Total", "Outstanding"],
    rows: [["1", "Anusha Reddy", "Banjara Hills", "38", "Rs 6,42,370", "Rs 32,118", "Rs 6,74,488", "Rs 18,000"], ["2", "Kiran Kumar", "Madhapur", "31", "Rs 5,86,900", "Rs 29,345", "Rs 6,16,245", "Rs 24,500"], ["3", "Pooja Singh", "SR Nagar", "27", "Rs 4,92,150", "Rs 24,608", "Rs 5,16,758", "Rs 12,000"]],
    action: "Generate Report",
  },
  "Sale Master Data": {
    tabs: ["Sales Register", "Branch Summary", "Booking Type", "Payment Mode"],
    columns: ["Invoice", "Date", "Branch", "Customer", "Booking Type", "Employee", "Paid", "Outstanding"],
    rows: [["SINV-26418", "19 Sep 2026", "Madhapur", "Ritika Sharma", "Walk In", "Kavya", "Rs 48,000", "Rs 12,000"], ["SINV-26402", "18 Sep 2026", "Banjara Hills", "Meena Rao", "Reference", "Anusha", "Rs 65,500", "Rs 0"], ["SINV-26391", "18 Sep 2026", "SR Nagar", "Asha Nair", "Existing Customer", "Pooja", "Rs 32,000", "Rs 8,000"]],
    action: "Apply Filters",
  },
  "Branch Expenditures": {
    tabs: ["New Expenditure Entry", "Submitted Entries", "Cash Overview"],
    columns: ["Date", "Branch", "Expenditure Type", "Ledger Category", "Description", "Amount", "Paid By", "Mode"],
    rows: [["19 Sep", "Madhapur", "Housekeeping", "Branch Expenses", "Cleaning supplies", "Rs 3,420", "Ramesh", "Petty Cash"], ["18 Sep", "Banjara Hills", "Repairs", "Maintenance", "AC service", "Rs 6,800", "Harish", "UPI"], ["18 Sep", "SR Nagar", "Utilities", "Electricity", "Power bill", "Rs 18,260", "Swathi", "Bank"]],
    action: "Submit & Create Journal Entry",
  },
  "Audit Reports": {
    tabs: ["New Audit", "All Audits", "Master Audit Report", "Topic Approvals"],
    columns: ["Audit ID", "Branch / Date", "Auditor", "Topic Marks", "Total", "%", "Grade", "Status"],
    rows: [["AUD-26094", "Madhapur / 18 Sep", "V. Reddy", "184 / 200", "92", "92%", "Outstanding", "Verified"], ["AUD-26091", "SR Nagar / 17 Sep", "S. Mehta", "168 / 200", "84", "84%", "Excellent", "Submitted"], ["AUD-26087", "Kukatpally / 16 Sep", "V. Reddy", "142 / 200", "71", "71%", "Good", "Actioned"]],
    action: "Submit Audit",
  },
  Leads: {
    tabs: ["Call Dashboard", "Lead Queue", "Walk-ins", "Agent Performance", "Upload Leads"],
    columns: ["Lead", "Mobile", "Source", "Category", "Agent", "Last Call", "Next Follow-up", "Status"],
    rows: [["Sneha Kapoor", "98XXXX4210", "Instagram", "Slimming", "Divya", "10:42 AM", "Today 4 PM", "Follow-Up"], ["Aparna Das", "99XXXX1834", "Google", "Dermat", "Rohit", "9:18 AM", "Tomorrow", "Appointment"], ["Farah Khan", "97XXXX6632", "Referral", "Hair", "Neha", "Yesterday", "21 Sep", "Untouched"]],
    action: "Start Call",
  },
  Appointments: {
    tabs: ["Scheduler", "Today", "Upcoming", "Cancelled"],
    columns: ["Time", "Client", "Branch", "Practitioner", "Service", "Room", "Status"],
    rows: [["09:30 AM", "Ritika Sharma", "Madhapur", "Dr. Nidhi", "Consultation", "Cabin 2", "Checked In"], ["11:00 AM", "Meena Rao", "Banjara Hills", "Kavya", "Therapy", "Room 4", "Confirmed"], ["02:30 PM", "Asha Nair", "SR Nagar", "Dr. Priya", "Review", "Cabin 1", "Waiting"]],
    action: "New Appointment",
  },
};

const defaults = {
  report: { tabs: ["Report", "Summary", "Details"], columns: ["Reference", "Date", "Branch", "Category", "Value", "Owner", "Status"], action: "Run Report" },
  form: { tabs: ["New Entry", "Recent Entries", "History"], columns: ["Reference", "Date", "Branch", "Description", "Amount", "Owner", "Status"], action: "Save Entry" },
  people: { tabs: ["Directory", "Schedule", "Activity", "Documents"], columns: ["Name", "ID", "Branch", "Mobile", "Owner", "Last Activity", "Status"], action: "New Record" },
  dashboard: { tabs: ["Overview", "Performance", "Activity", "Reports"], columns: ["Metric", "Branch", "Today", "Month", "Target", "Achievement", "Status"], action: "Refresh Dashboard" },
  stock: { tabs: ["Overview", "Items", "Movement", "Reports"], columns: ["Item", "Code", "Location", "Quantity", "Rate", "Value", "Status"], action: "Run Report" },
  tasks: { tabs: ["Overview", "Pending", "Completed"], columns: ["Reference", "Branch", "Type", "Owner", "Date", "Stage", "Status"], action: "Refresh" },
};

const page = computed(() => {
  if (special[props.title]) return special[props.title];
  const base = defaults[kind.value];
  return { ...base, rows: [[props.title + " record 01", "LIFE-2601", "Madhapur", "19 Sep 2026", "Rs 24,500", "Anusha", "Active"], [props.title + " record 02", "LIFE-2602", "Banjara Hills", "18 Sep 2026", "Rs 18,200", "Kiran", "Pending"], [props.title + " record 03", "LIFE-2603", "SR Nagar", "17 Sep 2026", "Rs 31,750", "Pooja", "Completed"]] };
});
const tab = computed(() => activeTab.value || page.value.tabs[0]);
const rows = computed(() => page.value.rows.filter((row) => !query.value || row.join(" ").toLowerCase().includes(query.value.toLowerCase())));
const metricLabels = computed(() => kind.value === "stock" ? ["Total Items", "Low Stock", "In Transit", "Order Value"] : kind.value === "tasks" ? ["Open", "Overdue", "Completed Today", "High Priority"] : kind.value === "people" ? ["Total", "Today", "Follow-ups", "Completed"] : ["Records", "Current Value", "Pending", "Completion"]);
function act(message) { toast.value = message; clearTimeout(act.timer); act.timer = setTimeout(() => toast.value = "", 2200); }
</script>

<template>
  <section class="erp-replica" :class="'replica-' + kind">
    <header class="replica-head">
      <div><p class="replica-kicker">LIFE SLIMMING &amp; COSMETIC CLINIC PVT. LTD.</p><h1>{{ title }}</h1><p>{{ description }}</p></div>
      <div class="replica-head-actions"><button @click="act('Data refreshed')">↻ Refresh</button><button class="replica-primary" @click="act(page.action + ' opened')">{{ page.action }}</button></div>
    </header>
    <nav class="replica-tabs"><button v-for="item in page.tabs" :key="item" :class="{ active: tab === item }" @click="activeTab = item">{{ item }}</button></nav>

    <section v-if="kind === 'form' || (kind === 'tasks' && tab === page.tabs[0])" class="entry-sheet">
      <div class="sheet-title"><div><h2>{{ tab }}</h2><p>Complete the information below</p></div><span>Draft</span></div>
      <div class="entry-grid">
        <label>Branch *<select v-model="branch"><option>All Branches</option><option>Madhapur</option><option>Banjara Hills</option><option>SR Nagar</option></select></label>
        <label>Date *<input type="date" value="2026-09-19"></label>
        <label>Category *<select><option>Select category</option><option>Operations</option><option>Client Care</option><option>Finance</option></select></label>
        <label>Assigned / Paid By *<input value="Anusha Reddy"></label>
        <label class="entry-wide">Description *<textarea rows="3" placeholder="Enter details"></textarea></label>
        <label>Amount / Priority<input placeholder="Rs 0.00"></label><label>Attachment<input type="file"></label>
      </div>
      <div class="sheet-actions"><button @click="act('Draft saved')">Save Draft</button><button class="replica-primary" @click="act(page.action + ' completed')">{{ page.action }}</button></div>
    </section>

    <section class="replica-filters">
      <label>From Date<input type="date" value="2026-09-01"></label><label>To Date<input type="date" value="2026-09-19"></label>
      <label>Branch<select v-model="branch"><option>All Branches</option><option>Madhapur</option><option>Banjara Hills</option><option>SR Nagar</option></select></label>
      <label>Status<select><option>All Status</option><option>Pending</option><option>Completed</option><option>Rejected</option></select></label>
      <label class="replica-search">Search<input v-model="query" type="search" placeholder="Search records"></label>
      <button class="replica-primary" @click="act('Filters applied')">Apply</button><button @click="query = ''; branch = 'All Branches'">Reset</button>
    </section>

    <section class="replica-metrics"><article v-for="(label, i) in metricLabels" :key="label"><span>{{ label }}</span><strong>{{ ["128", "Rs 8.42L", "14", "86%"][i] }}</strong><small>{{ ["+12 today", "+8.4%", "Needs review", "On target"][i] }}</small></article></section>

    <section v-if="kind === 'dashboard'" class="replica-charts">
      <article><h2>Target vs Achievement</h2><div v-for="(n, i) in [84, 71, 66, 59]" :key="n" class="replica-bar"><span>{{ ["Madhapur", "Banjara Hills", "SR Nagar", "Kukatpally"][i] }}</span><i><b :style="{ width: n + '%' }"></b></i><strong>{{ n }}%</strong></div></article>
      <article><h2>Today Activity</h2><ol><li><b>09:15</b> Branch opening completed</li><li><b>11:40</b> Daily collection updated</li><li><b>02:10</b> Approval moved to Level 2</li><li><b>04:30</b> Target review scheduled</li></ol></article>
    </section>

    <section class="replica-table-card">
      <div class="replica-table-title"><div><h2>{{ tab }}</h2><p>{{ rows.length }} static records</p></div><div><button @click="act('CSV prepared')">↓ CSV</button><button @click="act('Print view opened')">⎙ Print</button></div></div>
      <div class="data-table-wrap"><table class="module-table"><thead><tr><th v-for="column in page.columns" :key="column">{{ column }}</th></tr></thead><tbody><tr v-for="(row, ri) in rows" :key="ri"><td v-for="(cell, ci) in row" :key="ci"><span v-if="ci === row.length - 1" class="status-pill">{{ cell }}</span><template v-else>{{ cell }}</template></td></tr><tr v-if="!rows.length"><td :colspan="page.columns.length" class="replica-empty">No matching records</td></tr></tbody></table></div>
    </section>
    <div v-if="toast" class="replica-toast" role="status">✓ {{ toast }}</div>
  </section>
</template>
