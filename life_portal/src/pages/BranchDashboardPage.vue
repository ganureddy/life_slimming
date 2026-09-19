<script setup>
import { onBeforeUnmount, onMounted } from "vue";
import {
  getBranchCommandCenter,
  getBranches,
  getRosterEmployees,
} from "../api/branchCommandCenter";
import "../styles/branch-command-center.css";

let controller;

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setHtml(id, value) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = value;
}

function setValue(id, value) {
  const el = document.getElementById(id);
  if (el) el.value = value;
}

function scrollToPanel(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function esc(value) {
  return String(value ?? "").replace(/[<>&"']/g, (char) => ({
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function num(value) {
  return Number(value || 0);
}

function inr(value) {
  const amount = Math.round(num(value));
  if (amount >= 10000000) return "Rs " + (amount / 10000000).toFixed(2) + " Cr";
  if (amount >= 100000) return "Rs " + (amount / 100000).toFixed(2) + " L";
  return "Rs " + amount.toLocaleString("en-IN");
}

function pct(value, total) {
  return total ? Math.round((num(value) / num(total)) * 100) : 0;
}

function todayIso() {
  const d = new Date();
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
}

function renderTile(id, icon, label, value, note) {
  setHtml(
    id,
    '<div class="ti">' + esc(icon) + '</div><div><h3>' + esc(label) + '</h3><b class="num">' + esc(value) + '</b><p>' + esc(note) + '</p></div>',
  );
}

function renderStaticPreview() {
  const now = new Date();
  const day = String(now.getDate()).padStart(2, "0");
  const monthYear = now.toLocaleDateString("en-IN", { month: "long", year: "numeric" });
  const today = todayIso();

  setText("lastUpd", "Loading live data...");
  setValue("grFrom", today);
  setValue("grTo", today);
  setText("today-date", day);
  setText("today-month-year", monthYear);
  setText("today-occasion", "Branch command center");
  setText("today-wish", "Live data connection starting");
  setText("next-event-date", "Next");
  setText("next-event-name", "Connect offer package API");
  setText("offer-count-text", "3 sample offers");
  setText("timer-label", "Static preview");
  setText("attSum", "Loading...");
  setText("bcc-dues-branch", "Selected branch");
  setText("bcc-dues-updated", "Sample recovery snapshot");
  setText("bcc3-ap-status", "Showing sample appointments");
  setText("wkTitle", "Walk-ins assigned today");
  setText("wkPend", "4 pending");
  setText("wkNext", "11:30 AM");
  setText("bcc4-sales-status", "Loading employee performance...");

  setHtml("offer-track", [
    ["LIFE-01", "Weight Loss Starter Package", "10 sessions", "Rs 18,000"],
    ["LIFE-02", "Wellness Renewal Package", "15 sessions", "Rs 26,500"],
    ["LIFE-03", "Premium Transformation Plan", "30 sessions", "Rs 49,000"],
  ].map(([id, title, sessions, price]) => '<div class="offer-slide"><article class="offer-card"><span class="pkg-id">' + id + '</span><h4>' + title + '</h4><div class="offer-meta-row"><span class="offer-items">' + sessions + '</span><span class="detail-tag expiry">Limited period</span><span class="detail-tag minimum-sessions">Minimum sessions apply</span></div><div class="price-box"><span class="val">' + price + '</span><span class="lab">PACKAGE VALUE</span></div></article></div>').join(""));

  setHtml("strip", '<div class="chip"><b>Collections</b><span>Rs 4.8L</span></div><div class="chip"><b>Pending</b><span>Rs 1.2L</span></div><div class="chip"><b>Target</b><span>68%</span></div><div class="chip"><b>Walk-ins</b><span>24</span></div>');
  setHtml("branch-dashboard-hero", '<div class="bcc-exec-copy"><span>Branch dashboard</span><h3>Live performance overview</h3><p>Collections, pending recovery, targets and daily operations in one branch view.</p></div><div class="bcc-exec-score"><small>Cycle progress</small><strong class="num">68%</strong><em>Sample preview</em></div><div class="bcc-exec-mini"><b class="num">Rs 4.8L</b><span>Collections</span></div><div class="bcc-exec-mini warn"><b class="num">Rs 1.2L</b><span>Pending dues</span></div>');

  renderTile("tile-sales", "Rs", "Collections Analysis", "Loading", "Live billing summary");
  renderTile("tile-pending", "!", "Pending Balances", "Loading", "Recovery follow-up queue");
  renderTile("tile-target", "%", "Target & Realisation", "Loading", "Billing cycle progress");
  renderTile("tile-appointments", "Cal", "Appointments", "Loading", "Today and selected cycle");
  renderTile("tile-service", "Src", "Media / Source Mix", "Loading", "Lead source groups");
  renderTile("tile-leads", "Lead", "Leads & Walk-ins", "Loading", "Fresh leads");
  renderTile("tile-stock", "Box", "Stock", "Loading", "Low stock alerts");
  renderTile("tile-employee", "Staff", "Counselor Performance", "Loading", "Active staff");
  renderTile("tile-grievance", "Msg", "Grievances", "Loading", "Open issues");
  renderTile("tile-worklist", "Task", "My Tasks", "Loading", "Pending actions");

  setHtml("attWrap", '<table class="bcc3-table"><thead><tr><th>Employee</th><th>Punch In</th><th>Punch Out</th><th>Status</th></tr></thead><tbody><tr><td>Anita Sharma</td><td>09:54</td><td>-</td><td>Present</td></tr><tr><td>Rahul Mehta</td><td>10:08</td><td>-</td><td>Late</td></tr><tr><td>Neha Jain</td><td>-</td><td>-</td><td>Pending</td></tr></tbody></table>');
  setHtml("bcc-manager-visits", '<div class="note">Manager visit tracking placeholder.</div>');
  setHtml("bcc-dues-content", '<div class="grid r3"><div class="tile"><h3>Total Pending</h3><b class="num">Rs 1.2L</b><p>Sample amount</p></div><div class="tile"><h3>Due Today</h3><b class="num">18</b><p>Follow-ups</p></div><div class="tile"><h3>Recovered</h3><b class="num">Rs 42K</b><p>This cycle</p></div></div>');
  document.getElementById("bcc-dues-content")?.removeAttribute("aria-busy");

  setHtml("bcc3-ap-rows", '<tr><td>Priya S.<br><small>987***210</small></td><td>Today 11:30</td><td>Meera</td><td>WL</td><td>F / 34</td><td>Indiranagar</td><td>Anita</td><td>Interested in trial</td><td>2d</td><td>1d</td><td>1st</td><td>Scheduled</td></tr><tr><td>Karan P.<br><small>982***451</small></td><td>Today 16:00</td><td>Ritu</td><td>Laser</td><td>M / 29</td><td>Koramangala</td><td>Rahul</td><td>Price discussion</td><td>5d</td><td>3d</td><td>2nd</td><td>Follow-up</td></tr>');
  setHtml("wkList", '<div class="wk-row"><b>11:30 AM · Priya S.</b><span>Trial consultation · Pending update</span></div><div class="wk-row"><b>04:00 PM · Karan P.</b><span>Follow-up visit · Scheduled</span></div>');
  setHtml("bcc4-sales-summary", '<div class="gchips"><div class="gchip"><b class="num">Rs 3.2L</b><span>Fresh sales</span></div><div class="gchip"><b class="num">Rs 1.1L</b><span>Rebooking</span></div><div class="gchip"><b class="num">14</b><span>First visits</span></div></div>');
  setHtml("bcc4-sales-rows", '<tr><td>1</td><td>Anita Sharma</td><td>Rs 1.4L</td><td>Rs 42K</td><td>Rs 18K</td><td>Rs 92K</td><td>4</td><td>7</td><td>1</td></tr><tr><td>2</td><td>Rahul Mehta</td><td>Rs 96K</td><td>Rs 31K</td><td>Rs 11K</td><td>Rs 78K</td><td>5</td><td>3</td><td>0</td></tr>');
  setHtml("railPulse", '<h3>Branch Pulse</h3><p class="note">Sample people and operations signals will become live after API integration.</p>');
  setHtml("lscc-rp-status-cards", '<div class="tile"><h3>Weekly submitted</h3><b class="num">12 / 18</b></div><div class="tile"><h3>Monthly submitted</h3><b class="num">9 / 18</b></div>');
  setHtml("lscc-rp-content", '<div class="note">Weekly roster preview. API integration pending.</div>');
  setHtml("lscc-monthly-content", '<div class="note">Monthly attendance summary preview. API integration pending.</div>');

  document.querySelectorAll("[data-bcc-jump]").forEach((button) => {
    button.addEventListener("click", () => scrollToPanel(button.getAttribute("data-bcc-jump")));
  });
}

function renderAttendance(rows) {
  const list = Array.isArray(rows) ? rows : [];
  const present = list.filter((row) => String(row.st || "").toLowerCase() === "present").length;
  const late = list.filter((row) => String(row.st || "").toLowerCase() === "late").length;
  const absent = list.filter((row) => String(row.st || "").toLowerCase() === "absent").length;
  setText("attSum", present + " present · " + late + " late · " + absent + " absent");
  setHtml(
    "attWrap",
    '<table class="bcc3-table"><thead><tr><th>Employee</th><th>Designation</th><th>Punch In</th><th>Punch Out</th><th>Status</th></tr></thead><tbody>' +
      (list.length
        ? list.map((row) => '<tr><td>' + esc(row.n) + '</td><td>' + esc(row.dg || "-") + '</td><td>' + esc(row.pin || "-") + '</td><td>' + esc(row.pout || "-") + '</td><td>' + esc(row.st || "-") + '</td></tr>').join("")
        : '<tr><td colspan="5">No attendance rows returned.</td></tr>') +
      "</tbody></table>",
  );
}

function renderEmployeeSales(rows) {
  const list = Array.isArray(rows) ? rows : [];
  const total = list.reduce((sum, row) => sum + num(row.gross || row.net), 0);
  setText("bcc4-sales-status", "Live counselor collections from branch_command_center.");
  setHtml(
    "bcc4-sales-summary",
    '<div class="gchips"><div class="gchip"><b class="num">' + inr(total) + '</b><span>Total collections</span></div><div class="gchip"><b class="num">' + list.length + '</b><span>Performers</span></div></div>',
  );
  setHtml(
    "bcc4-sales-rows",
    list.length
      ? list.slice(0, 25).map((row, index) => '<tr><td>' + (index + 1) + '</td><td>' + esc(row.n) + '<br><small>' + esc(row.dg || "") + '</small></td><td>' + inr(row.gross) + '</td><td>-</td><td>' + inr(row.net) + '</td><td>-</td><td>' + esc(row.conv || 0) + '</td><td>-</td><td>-</td></tr>').join("")
      : '<tr><td colspan="9">No employee sales returned for this branch.</td></tr>',
  );
}

function renderDashboard(data) {
  const achieved = num(data.achieved);
  const target = num(data.target);
  const pending = num(data.pend_total || (Array.isArray(data.pend) ? data.pend.reduce((sum, row) => sum + num(row.due), 0) : 0));
  const apToday = data.ap_today || {};
  const apCycle = data.ap_cycle || {};
  const leads = data.leads || {};
  const stock = data.stock || {};
  const grv = data.grv || {};
  const work = data.work || {};
  const media = Array.isArray(data.media) ? data.media : [];
  const walkins = Array.isArray(data.walkins) ? data.walkins : [];

  setText("lastUpd", "Live · " + new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }));
  setText("wkPend", walkins.length + " today");
  setText("wkNext", walkins[0]?.t || "-");
  setText("bcc-dues-branch", data.branch || "Selected branch");

  setHtml("strip", '<div class="chip"><b>Today Gross</b><span>' + inr(data.paid_today_gross) + '</span></div><div class="chip"><b>Cycle Gross</b><span>' + inr(data.paid_mtd_gross || data.achieved_gross) + '</span></div><div class="chip"><b>Target</b><span>' + pct(achieved, target) + '%</span></div><div class="chip"><b>Walk-ins</b><span>' + walkins.length + '</span></div>');
  setHtml("branch-dashboard-hero", '<div class="bcc-exec-copy"><span>' + esc(data.branch || "Selected branch") + '</span><h3>Branch dashboard</h3><p>Current cycle summary from live branch command center data.</p></div><div class="bcc-exec-score"><small>Target realisation</small><strong class="num">' + pct(achieved, target) + '%</strong><em>' + inr(achieved) + " of " + inr(target) + '</em></div><div class="bcc-exec-mini"><b class="num">' + inr(data.paid_today_gross) + '</b><span>Today gross</span></div><div class="bcc-exec-mini warn"><b class="num">' + inr(pending) + '</b><span>Pending recovery</span></div>');

  renderTile("tile-sales", "Rs", "Collections Analysis", inr(achieved), "Gross " + inr(data.achieved_gross));
  renderTile("tile-pending", "!", "Pending Balances", inr(pending), (Array.isArray(data.pend) ? data.pend.length : 0) + " clients/invoices");
  renderTile("tile-target", "%", "Target & Realisation", pct(achieved, target) + "%", inr(achieved) + " of " + inr(target));
  renderTile("tile-appointments", "Cal", "Appointments", num(apToday.total), "Cycle " + num(apCycle.total) + " appointments");
  renderTile("tile-service", "Src", "Media / Source Mix", media.length, media[0]?.m ? "Top: " + media[0].m : "No source rows");
  renderTile("tile-leads", "Lead", "Leads & Walk-ins", num(leads.t), num(leads.w) + " walk-ins · " + num(leads.bk) + " booked");
  renderTile("tile-stock", "Box", "Stock", num(stock.items), num(stock.zero) + " zero stock items");
  renderTile("tile-grievance", "Msg", "Grievances", num(grv.open_), num(grv.esc) + " escalated · " + num(grv.red) + " red");
  renderTile("tile-worklist", "Task", "My Tasks", num(work.open_), num(work.over_) + " overdue · " + num(work.due) + " due today");

  renderAttendance(data.att);
  renderEmployeeSales(data.emps);
  setHtml(
    "wkList",
    walkins.length
      ? walkins.map((row) => '<div class="wk-row"><b>' + esc(row.t || "-") + " · " + esc(row.n || row.id) + '</b><span>' + esc(row.st || "Pending") + " · " + esc(row.by_ || "") + '</span></div>').join("")
      : '<div class="wk-row"><b>No walk-ins returned today</b><span>Use HO-CC appointment API next for details.</span></div>',
  );
}

async function loadBranch(branch) {
  if (!branch) return;
  controller?.abort();
  controller = new AbortController();
  setText("lastUpd", "Loading " + branch + "...");
  try {
    const data = await getBranchCommandCenter({ branch }, controller.signal);
    renderDashboard(data);
    const employees = await getRosterEmployees(branch, controller.signal);
    renderTile("tile-employee", "Staff", "Counselor Performance", employees.length, "Active roster employees");
    setHtml("railPulse", '<h3>Branch Pulse</h3><p class="note">' + esc(branch) + " · " + employees.length + " active employees loaded from roster_employees.</p>");
    setHtml("lscc-rp-content", '<div class="note">' + esc(employees.length) + " active employees available for weekly roster.</div>");
  } catch (error) {
    if (error.name === "AbortError") return;
    setText("lastUpd", "Live data unavailable");
    setHtml("railPulse", '<h3>Branch Pulse</h3><p class="note">Could not load live branch data. ' + esc(error.message) + "</p>");
  }
}

async function loadBranchesAndDashboard() {
  const branchSel = document.getElementById("branchSel");
  const rosterSel = document.getElementById("lscc-rp-branch");
  if (!branchSel) return;
  try {
    const branches = (await getBranches(controller?.signal)).filter((name) => name !== "Head Office" && name !== "Testing Branch");
    branchSel.innerHTML = branches.map((name) => '<option value="' + esc(name) + '">' + esc(name) + "</option>").join("");
    if (rosterSel) rosterSel.innerHTML = '<option value="">Select Branch</option>' + branchSel.innerHTML;
    const selected = branchSel.value || branches[0];
    branchSel.value = selected;
    if (rosterSel) rosterSel.value = selected;
    branchSel.addEventListener("change", () => {
      if (rosterSel) rosterSel.value = branchSel.value;
      loadBranch(branchSel.value);
    });
    rosterSel?.addEventListener("change", () => loadBranch(rosterSel.value || branchSel.value));
    await loadBranch(selected);
  } catch (error) {
    setText("lastUpd", "Branch list unavailable");
    setHtml("railPulse", '<h3>Branch Pulse</h3><p class="note">' + esc(error.message) + "</p>");
  }
}

onMounted(() => {
  renderStaticPreview();
  loadBranchesAndDashboard();
});

onBeforeUnmount(() => {
  controller?.abort();
});
</script>

<template>
<div class="lbcc" id="lbccRoot">
<div class="hdr"><div class="hdr-in">
  <div class="hdr-left"><div class="logo"><div><small>LIFE · BRANCH OPERATIONS</small><h1>Branch Command Center</h1></div></div></div>
  <a class="bcc-billing" href="https://portal.lifescc.com/billing-v2?view=billing" target="_blank" rel="noopener noreferrer" aria-label="Billing — opens a new window">🧾 Billing <span aria-hidden="true">↗</span></a><a class="bcc-billing bcc3-client-link" href="https://portal.lifescc.com/client-360-Bhuvan" target="_blank" rel="noopener noreferrer" aria-label="Client 360 — opens a new window">👤 Client 360 ↗</a><button class="bcc-billing bcc4-walk-button" type="button" data-bcc-jump="bcc-walkins">📣 CC Walk-in UPDATE ↗</button><button class="bcc-billing bcc5-roster-button" type="button" data-bcc-jump="bcc-roster">📅 Employee Roster ↗</button><div class="hdr-center"><div class="live-chip"><span class="pulse"></span><span id="lastUpd">Loading…</span></div><div class="br-filter"><label class="br-label" for="branchSel">Branch</label><select id="branchSel" aria-label="Branch"></select></div></div>
</div><nav class="bcc-nav" aria-label="Page sections"><button type="button" data-bcc-jump="bcc-ho-appointments">HO-CC Appointments</button><button type="button" data-bcc-jump="bcc-attendance">Today Attendance</button><button type="button" data-bcc-jump="bcc-dues">Pending Dues</button><button type="button" data-bcc-jump="bcc-dashboard">Dashboard</button><button type="button" data-bcc-jump="bcc-walkins">Walk-ins</button><button type="button" data-bcc-jump="bcc-operations">Operations</button><button type="button" data-bcc-jump="bcc-people">People</button><button type="button" data-bcc-jump="bcc-roster">Employee Roster</button><button type="button" data-bcc-jump="bcc-offers">Events & Offers</button><button type="button" class="bcc-reset-layout" data-bcc-reset>Reset layout</button></nav></div>
<div class="wrap bcc-panel-stack" data-bcc-stack="main"><section class="bcc-panel bcc-slate" id="bcc-offers" data-bcc-panel="offers" aria-labelledby="bcc-title-offers" tabindex="-1">
  <header class="bcc-panel-head"><div><h2 id="bcc-title-offers">Events & Offer Packages</h2><p>Today’s events and active offers</p></div><div class="bcc-panel-actions" data-bcc-controls></div></header>
  <div class="bcc-panel-body" id="bcc-body-offers"><div class="life-container"><div class="life-dashboard"><div class="life-event-panel"><div class="panel-tag">Today Events</div><div id="today-display"><h1 id="today-date">--</h1><p id="today-month-year">--</p><div class="today-occasion" id="today-occasion">No special occasion today</div><div class="today-wish" id="today-wish">Have a Great Day!</div></div><div class="next-event-strip"><span class="next-lbl">UPCOMING EVENTS</span><div class="next-details"><span id="next-event-date">--</span><span id="next-event-name">--</span></div></div><div class="life-leaf-icon">🌿</div></div><div class="life-gallery-panel"><div class="gallery-header"><div><h3>Offer Packages</h3><p id="offer-count-text">Loading offers...</p></div><div class="gallery-controls"><button class="nav-arrow" id="btn-prev" type="button" aria-label="Previous offer">‹</button><button class="nav-arrow" id="btn-next" type="button" aria-label="Next offer">›</button></div></div><div class="gallery-viewport"><div class="gallery-track" id="offer-track"></div></div><div class="life-timer-box"><div class="timer-bg"><div class="timer-line" id="progress-bar"></div></div><span class="timer-label" id="timer-label">Next offer in 15s</span></div></div></div></div></div>
</section><section class="bcc-panel bcc-green" id="bcc-attendance" data-bcc-panel="attendance" aria-labelledby="bcc-title-attendance" tabindex="-1">
  <header class="bcc-panel-head"><div><h2 id="bcc-title-attendance">Branch Today Attendance</h2><p>Live employee attendance for the selected branch</p></div><div class="bcc-panel-actions" data-bcc-controls></div></header>
  <div class="bcc-panel-body" id="bcc-body-attendance"><div class="card bcc-att-card"><h3>Live Attendance · Punch In → Out <span id="attSum" class="wk-pend"></span></h3><div id="attWrap" class="att-scroll"></div><div id="bcc-manager-visits" class="bcc-manager-visits" aria-live="polite"></div></div></div>
</section><section class="bcc-panel bcc-gold" id="bcc-dues" data-bcc-panel="dues" aria-labelledby="bcc-title-dues" tabindex="-1"><header class="bcc-panel-head"><div><h2 id="bcc-title-dues">Pending Dues & Recovery</h2><p>Branch balances · scheduled dues · employee accountability</p></div><div class="bcc-panel-actions" data-bcc-controls></div></header><div class="bcc-panel-body" id="bcc-body-dues"><div class="bcc-dues-tools"><div><b id="bcc-dues-branch">Selected branch</b><span id="bcc-dues-updated" role="status" aria-live="polite">Loading recovery data…</span></div><div><button type="button" id="bcc-dues-refresh">↻ Refresh dues</button><a href="https://portal.lifescc.com/pending-balances-updates-Bhuvan" target="_blank" rel="noopener noreferrer">Open Dues Recovery ↗</a></div></div><div id="bcc-dues-content" aria-busy="true"></div></div></section><section class="bcc-panel bcc-gold" id="bcc-dashboard" data-bcc-panel="dashboard" aria-labelledby="bcc-title-dashboard" tabindex="-1">
  <header class="bcc-panel-head"><div><h2 id="bcc-title-dashboard">Dashboard & Money Summary</h2><p>Collections, outstanding balances and target realisation</p></div><div class="bcc-panel-actions" data-bcc-controls></div></header>
  <div class="bcc-panel-body" id="bcc-body-dashboard"><div class="card bcc-range" id="globalRangeCard">
  <div class="bcc-range-caption"><b>Date Range</b><span>Billing cycle: 6th → 5th</span></div>
  <div class="bcc-filter-fields"><div><label for="grFrom">From</label><input type="date" id="grFrom" value="" min="1900-01-01" max="2099-12-31" autocomplete="off"></div><div><label for="grTo">To</label><input type="date" id="grTo" value="" min="1900-01-01" max="2099-12-31" autocomplete="off"></div><button type="button" class="wbtn bcc-primary" data-globalrangego="1">Apply</button><button type="button" class="wbtn" data-resetrange="1">Reset</button></div>
  <div class="gr-presets" id="grPresets"><span class="gr-presets-l">Quick</span><button type="button" class="gr-chip" data-preset="today">Today</button><button type="button" class="gr-chip" data-preset="yesterday">Yesterday</button><button type="button" class="gr-chip" data-preset="last7">Last 7 Days</button><button type="button" class="gr-chip" data-preset="thismonth">This Month</button><button type="button" class="gr-chip" data-preset="lastmonth">Last Month</button><button type="button" class="gr-chip" data-preset="thisyear">This Year</button></div></div><div class="bcc-exec-dashboard" id="branch-dashboard-hero"></div><div class="strip" id="strip"></div><div class="grid r1"><div class="tile" tabindex="0" role="button" data-tile="sales" id="tile-sales"></div><div class="tile" tabindex="0" role="button" data-tile="pending" id="tile-pending"></div><div class="tile" tabindex="0" role="button" data-tile="target" id="tile-target"></div></div></div>
</section><section class="bcc-panel bcc-blue" id="bcc-ho-appointments" data-bcc-panel="ho-appointments" aria-labelledby="bcc-title-ho-appointments" tabindex="-1"><header class="bcc-panel-head"><div><h2 id="bcc-title-ho-appointments">Walk In Appointments By HO-CC</h2><p>Branch appointments · client details · lead journey</p></div><div class="bcc-panel-actions" data-bcc-controls></div></header><div class="bcc-panel-body" id="bcc-body-ho-appointments"><div class="bcc3-toolbar" id="bcc3-periods"><button data-bcc3-period="today">Today</button><button data-bcc3-period="tomorrow">Tomorrow</button><button data-bcc3-period="week">This week</button><button data-bcc3-period="month">This month · 6–5</button><button data-bcc3-period="nextmonth">Next month · 6–5</button><input id="bcc3-ap-search" placeholder="Search client, agent or staff" aria-label="Search HO CC appointments"><button id="bcc3-ap-refresh">↻ Refresh</button></div><p id="bcc3-ap-status" class="bcc3-note" role="status">Loading appointments…</p><div class="bcc3-tablewrap"><table class="bcc3-table"><thead><tr><th>Client / Ph.</th><th>Appt.</th><th>CC Agent</th><th>Cat.</th><th>G / Age</th><th>Location</th><th>Branch Staff</th><th>CC Remarks</th><th title="Days since Lead creation">Lead Age</th><th title="Elapsed time from Lead creation to first recorded walk-in">L → WI</th><th title="Recorded visit order for the same mobile">Visit</th><th>Status</th></tr></thead><tbody id="bcc3-ap-rows"></tbody></table></div><div id="bcc3-ap-pager" class="bcc3-toolbar"></div><p class="bcc3-note">Ph. = phone · Appt. = appointment · Cat. = treatment category · G = gender · WI = recorded walk-in. Hover or focus a masked phone to reveal it. Visit order uses recorded history for the same number; unavailable history is not assumed to be a first visit. Appointment outcomes remain visible.</p></div></section><section class="bcc-panel bcc-blue" id="bcc-walkins" data-bcc-panel="walkins" aria-labelledby="bcc-title-walkins" tabindex="-1">
  <header class="bcc-panel-head"><div><h2 id="bcc-title-walkins">Walk-in UPDATE</h2><p>Appointments, client details and status actions</p></div><div class="bcc-panel-actions" data-bcc-controls></div></header>
  <div class="bcc-panel-body" id="bcc-body-walkins"><div class="card"><h3><span id="wkTitle">Walk-ins assigned today</span><span class="wk-pend" id="wkPend"></span><span class="wk-next">Now <b id="wkNext">—</b></span></h3>
<div id="wkFilterBar" class="bcc-wk-filter"><div class="bcc-filter-fields"><div><label for="wkFrom">From</label><input type="date" id="wkFrom"></div><div><label for="wkTo">To</label><input type="date" id="wkTo"></div><button type="button" class="wbtn bcc-primary" data-wkgo="1">Show</button><button type="button" class="wbtn" data-wktoday="1">Today</button></div><span class="bcc-filter-note">Independent of the dashboard date range</span></div><div id="wkList"></div></div></div>
</section><section class="bcc-panel bcc-teal" id="bcc-operations" data-bcc-panel="operations" aria-labelledby="bcc-title-operations" tabindex="-1">
  <header class="bcc-panel-head"><div><h2 id="bcc-title-operations">Branch Operations</h2><p>Appointments, source collections, leads and stock</p></div><div class="bcc-panel-actions" data-bcc-controls></div></header>
  <div class="bcc-panel-body" id="bcc-body-operations"><div class="grid r2"><div class="tile" tabindex="0" role="button" data-tile="appointments" id="tile-appointments"></div><div class="tile" tabindex="0" role="button" data-tile="service" id="tile-service"></div><div class="tile" tabindex="0" role="button" data-tile="leads" id="tile-leads"></div><div class="tile" tabindex="0" role="button" data-tile="stock" id="tile-stock"></div></div></div>
</section><section class="bcc-panel bcc-purple" id="bcc-people" data-bcc-panel="people" aria-labelledby="bcc-title-people" tabindex="-1">
  <header class="bcc-panel-head"><div><h2 id="bcc-title-people">Employee Sales & People</h2><p>Fresh sales, rebooking, collections and active staff performance</p></div><div class="bcc-panel-actions" data-bcc-controls></div></header>
  <div class="bcc-panel-body" id="bcc-body-people"><section id="bcc4-sales"><div class="bcc4-sales-toolbar"><h3>💼 Employee Sales · Active Staff</h3><select id="bcc4-sales-period" aria-label="Sales month"></select><button id="bcc4-sales-refresh" type="button">↻ Refresh sales</button></div><p id="bcc4-sales-status">Open this section to trace invoice and payment records.</p><div id="bcc4-sales-summary"></div><div class="bcc4-sales-tablewrap"><table><thead><tr><th>#</th><th>Employee</th><th>Fresh Sales</th><th>Rebooking</th><th>Balance · Later Receipts</th><th>Avg / Month</th><th>Male · 1st</th><th>Female · 1st</th><th>Unspecified</th></tr></thead><tbody id="bcc4-sales-rows"><tr><td colspan="9">Select a sales month to view employee performance.</td></tr></tbody></table></div><p id="bcc4-sales-note" class="bcc3-note">Read-only invoice and payment analysis.</p></section><div class="cols"><div class="grid r3"><div class="tile" tabindex="0" role="button" data-tile="employee" id="tile-employee"></div><div class="tile" tabindex="0" role="button" data-tile="grievance" id="tile-grievance"></div><div class="tile" tabindex="0" role="button" data-tile="worklist" id="tile-worklist"></div></div><aside class="rail"><div class="card" id="railPulse"></div></aside></div></div>
</section><section class="bcc-panel bcc-green" id="bcc-roster" data-bcc-panel="roster" aria-labelledby="bcc-title-roster" tabindex="-1">
  <header class="bcc-panel-head"><div><h2 id="bcc-title-roster">Employee Roster Tracking</h2><p>Clearly separated weekly planning and monthly attendance</p></div><div class="bcc-panel-actions" data-bcc-controls></div></header>
  <div class="bcc-panel-body" id="bcc-body-roster"><div class="lscc-roster-root"><div class="lscc-rp-page-title">Employee Roster Tracking<span class="lscc-rp-page-sub">Branch Schedule (Planned) vs Live Biometric (Actual) — Weekly &amp; Monthly</span></div><nav class="bcc-roster-nav" aria-label="Roster views"><button type="button" data-bcc-jump="bcc-weekly">Weekly view</button><button type="button" data-bcc-jump="bcc-monthly">Monthly view</button><button type="button" data-bcc-jump="bcc-submission">Submission status</button></nav><div class="bcc-panel-stack" data-bcc-stack="roster"><section class="bcc-panel bcc-slate" id="bcc-submission" data-bcc-panel="submission" aria-labelledby="bcc-title-submission" tabindex="-1">
  <header class="bcc-panel-head"><div><h2 id="bcc-title-submission">Roster Submission</h2><p>Weekly and monthly completion across branches</p></div><div class="bcc-panel-actions" data-bcc-controls></div></header>
  <div class="bcc-panel-body" id="bcc-body-submission"><div class="lscc-rp-status-section"><div class="lscc-rp-status-title">Roster Submission Status</div><div id="lscc-rp-status-cards" class="lscc-rp-status-cards"><div class="lscc-rp-status-loading">Checking branch statuses...</div></div></div></div>
</section><section class="bcc-panel bcc-green" id="bcc-weekly" data-bcc-panel="weekly" aria-labelledby="bcc-title-weekly" tabindex="-1">
  <header class="bcc-panel-head"><div><h2 id="bcc-title-weekly">Weekly · Planned vs Actual</h2><p>Day-by-day shifts and biometric attendance</p></div><div class="bcc-panel-actions" data-bcc-controls></div></header>
  <div class="bcc-panel-body" id="bcc-body-weekly"><div class="lscc-rp-header"><div class="lscc-rp-title">Weekly Employee Roster — Planned vs Actual</div><select class="lscc-rp-select" id="lscc-rp-branch" aria-label="Roster branch"><option value="">Select Branch</option></select><button type="button" class="lscc-rp-btn" id="lscc-rp-prev">‹ Prev Week</button><div class="lscc-rp-weeklabel" id="lscc-rp-weeklabel"></div><button type="button" class="lscc-rp-btn" id="lscc-rp-next">Next Week ›</button><button type="button" class="lscc-rp-btn" id="lscc-rp-refresh">⟳ Refresh</button><span class="lscc-rp-due-badge">Due every Friday for the following week</span></div>
<p class="bcc-view-help">Select a planned shift above the recorded biometric attendance for each day.</p>
<div class="lscc-rp-legend"><span><i class="lscc-rp-dot bcc-dot-present"></i>Present</span><span><i class="lscc-rp-dot bcc-dot-late"></i>Late</span><span><i class="lscc-rp-dot bcc-dot-absent"></i>Absent</span><span><i class="lscc-rp-dot bcc-dot-leave"></i>Leave</span><span><i class="lscc-rp-dot bcc-dot-off"></i>Weekly Off</span><span><i class="lscc-rp-dot bcc-dot-training"></i>Training</span></div>
<div class="lscc-rp-tablewrap"><div id="lscc-rp-content" class="lscc-rp-empty">Select a branch to load the roster.</div></div></div>
</section><section class="bcc-panel bcc-blue" id="bcc-monthly" data-bcc-panel="monthly" aria-labelledby="bcc-title-monthly" tabindex="-1">
  <header class="bcc-panel-head"><div><h2 id="bcc-title-monthly">Monthly · Attendance Summary</h2><p>Working days, attendance, leave and training</p></div><div class="bcc-panel-actions" data-bcc-controls></div></header>
  <div class="bcc-panel-body" id="bcc-body-monthly"><div class="lscc-monthly-wrap" id="lscc-monthly-wrap" style="display:none;"><div class="lscc-monthly-header"><div class="lscc-monthly-title" id="lscc-monthly-title">Monthly Roster Summary — Planned vs Actual</div><span class="lscc-rp-due-badge">Due on the 30th for the following month</span></div>
<div class="lscc-month-nav"><button type="button" class="lscc-year-btn" id="lscc-year-prev" aria-label="Previous year">‹</button><span class="lscc-year-label" id="lscc-year-label"></span><button type="button" class="lscc-year-btn" id="lscc-year-next" aria-label="Next year">›</button><div class="lscc-month-btns" id="lscc-month-btns"><button type="button" data-m="0">Jan</button><button type="button" data-m="1">Feb</button><button type="button" data-m="2">Mar</button><button type="button" data-m="3">Apr</button><button type="button" data-m="4">May</button><button type="button" data-m="5">Jun</button><button type="button" data-m="6">Jul</button><button type="button" data-m="7">Aug</button><button type="button" data-m="8">Sep</button><button type="button" data-m="9">Oct</button><button type="button" data-m="10">Nov</button><button type="button" data-m="11">Dec</button></div></div><div class="lscc-monthly-info">Monthly totals per employee. Late is included in Present; use the Weekly view for the daily comparison.</div><div class="lscc-rp-tablewrap"><div id="lscc-monthly-content" class="lscc-rp-empty">Loading monthly summary...</div></div></div></div>
</section></div></div></div>
</section></div>
<div class="ovl" id="ovl"><div class="modal" role="dialog" aria-modal="true"><div class="m-hd"><div class="mi" id="mIco"></div><div style="flex:1"><h2 id="mTitle">—</h2><div class="msub" id="mSub"></div></div><button type="button" class="m-x" id="mClose" aria-label="Close">✕</button></div><div class="m-kpis" id="mKpis"></div><div class="m-bd" id="mBody"></div><div class="m-ft"><span class="note" id="mNote"></span></div></div></div>
<div class="toast" id="toast"><span class="tk">✓</span><span id="toastMsg"></span></div><div class="loader" id="loader"><div class="spin"></div></div>
<div class="bcc-announcer" role="status" aria-live="polite" data-bcc-announcer></div></div>
</template>
