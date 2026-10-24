// Dashboard behavior maintained as a page-owned ES module.
export function mountTaskManager(page) {
const { document, window, frappe, fetch, MutationObserver, setTimeout, clearTimeout, setInterval, clearInterval } = page;
(function () {
  'use strict';

  /* ================================================================
     FIXED ADMINS (always full rights) — more can be added in Control Panel
  ================================================================ */
  var CORE_ADMINS = ['administrator', 'bhuvan@lifescc.com', 'narendhar@lifescc.com'];
  var CFG_TITLE = 'LIFE_TASK_CPANEL_CONFIG';
  var BRANCHES = ['Head Office', 'Madhapur', 'Chandanagar', 'Gachibowli', 'Kukatpally', 'Banjara Hills', 'SR Nagar', 'Dilsukhnagar', 'Himayathnagar', 'Vijayawada', 'Vizag', 'Nellore'];
  var PRI_KEYS = ['VVIMP', 'IMP', 'HI', 'MED', 'LOW'];
  var PRI_TODO = { VVIMP: 'High', IMP: 'High', HI: 'High', MED: 'Medium', LOW: 'Low' };
  var LEGACY_PRI = { High: 'HI', Medium: 'MED', Low: 'LOW' };
  var STATUSES = ['Open', 'In Progress', 'Review Pending', 'On Hold', 'Reopened', 'Completed', 'Cancelled'];
  var ST_CLS = { 'Open': 's-open', 'In Progress': 's-prog', 'Review Pending': 's-rev', 'On Hold': 's-hold', 'Reopened': 's-reo', 'Completed': 's-done', 'Cancelled': 's-cxl', 'Resolved': 's-rev', 'Closed': 's-done' };
  var REPORT_DEF = [
    { k: 'EOD', label: 'EOD (Daily)', d: 'Report every day by the set time' },
    { k: 'WEEKLY', label: 'Weekly', d: 'Report on the chosen weekday' },
    { k: 'MONTHLY', label: 'Monthly', d: 'Report on the chosen date every month' },
    { k: 'SPECIFIC', label: 'Specific Date & Time', d: 'One report at an exact date-time' },
    { k: 'COMPLETION', label: 'Only on Completion', d: 'No interim reports' }
  ];
  var WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  var UPD_TYPES = ['Update', 'Report', 'Delay Remark', 'Query'];
  var MAX_FILE = 5 * 1024 * 1024;
  var PAGE = 30;
  var TK_PRI = ['High', 'Medium', 'Low'];
  var TK_STATUSES = ['Open', 'Reopened', 'On Hold', 'Resolved', 'Closed'];
  var TICKET_CATEGORY_MAP = {
    "Electrical / Equipment": [
      "AC Not Working",
      "TV Not Working",
      "Lighting Issue / Bulb Fused",
      "Plumbing Issue",
      "Water Cooler / RO Not Working",
      "Generator / Power Backup Failure",
      "Fire Extinguisher Expired",
      "Other"
    ],
    "Clinical Machinery": [
      "Slimming Machine Not Working",
      "Laser Machine Malfunction",
      "Cavitation / RF Machine Issue",
      "Cryo / Fat Freezing Unit Issue",
      "Hydra Facial Machine Issue",
      "Machine Calibration Required",
      "Machine Annual Maintenance Due",
      "Spare Part Required",
      "Other"
    ],
    "IT / ERP / Software": [
      "Billing Software Issue",
      "ERP Login Issue",
      "Client Data Not Loading",
      "Network / WiFi Issue",
      "Printer Not Working",
      "Biometric / Attendance Device Issue",
      "CCTV Not Working",
      "Email Not Working",
      "Other"
    ],
    "Human Resources": [
      "Need HR Assistance",
      "Payroll / Salary Query",
      "Leave / Attendance Issue",
      "Policy Clarification",
      "Appointment Letter / Documents Request",
      "PF / ESI Query",
      "Training Request",
      "Other"
    ],
    "Asset / Missing Item": [
      "Missing Asset",
      "Lost Phone",
      "Lost Laptop",
      "Damaged Equipment",
      "Furniture Damaged",
      "Uniform Not Issued",
      "Stationery Shortage",
      "Other"
    ],
    "Employee Conduct": [
      "Facing Issue With Another Employee",
      "Harassment Complaint",
      "Behavioural Concern",
      "Discrimination Complaint",
      "Unprofessional Conduct by Staff",
      "Other"
    ],
    "Operations": [
      "Branch Maintenance Issue",
      "Staffing Shortage",
      "Process / Workflow Issue",
      "Appointment Scheduling Conflict",
      "Branch Cleanliness Issue",
      "Housekeeping Request",
      "Other"
    ],
    "Accounts / Billing": [
      "Payment Discrepancy",
      "Invoice Issue",
      "Reimbursement Query",
      "Refund Processing Delay",
      "GST / Tax Query",
      "Petty Cash Shortage",
      "Bank Deposit Issue",
      "Other"
    ],
    "Marketing": [
      "Campaign Material Request",
      "Marketing Collateral Damaged",
      "Social Media Query Escalation",
      "Lead / Enquiry Not Assigned",
      "Signage / Branding Issue",
      "Other"
    ],
    "Inventory / Stock": [
      "Consumable Stock Shortage",
      "Cosmetic Product Stock Shortage",
      "Stock Damage / Expiry",
      "Reorder Request",
      "Stock Mismatch",
      "Other"
    ],
    "Security": [
      "Theft",
      "Unauthorized Access",
      "Suspicious Activity",
      "CCTV Footage Request",
      "Visitor / Vendor Access Issue",
      "Other"
    ],
    "Client / Treatment Related": [
      "Client Allergic Reaction",
      "Client Dissatisfaction — Need Doctor Review",
      "Consent Form Missing",
      "Treatment Protocol Clarification Needed",
      "Client Photo / Before-After Missing",
      "Other"
    ],
    "Front Office / Reception": [
      "Appointment Double-Booked",
      "Walk-in Client Waiting Too Long",
      "Reception Handover Issue",
      "Client Call Not Returned",
      "Other"
    ],
    "Facility / Housekeeping": [
      "Washroom Maintenance",
      "Pest Control Required",
      "Linen / Towel Shortage",
      "Parking Issue",
      "Other"
    ]
  };

  var EMPLOYEE_INVOLVED_ISSUES = [
    "Facing Issue With Another Employee",
    "Harassment Complaint",
    "Discrimination Complaint",
    "Behavioural Concern"
  ];

  var CATEGORY_TAG_TO_SUGGEST = {
    "IT / ERP / Software": "narendhar",
    "Human Resources": "viveka",
    "Accounts / Billing": "satya",
    "Marketing": "sridevi",
    "Inventory / Stock": "valli",
    "Operations": "surya",
    "Clinical Machinery": "anand"
  };

  /* ================================================================
     PERMISSIONS CATALOGUE (shown as matrix in Control Panel)
  ================================================================ */
  var PERMS = [
    ['assign', 'Assign new tasks', 'Tasks'],
    ['all_tab', 'See “All Tasks” tab', 'Tasks'],
    ['manage', 'Manage others’ tasks (approve, extend, priority, reassign, cancel, queue)', 'Tasks'],
    ['group', 'Create group tasks', 'Tasks'],
    ['team', 'See “Team & Contacts” tab', 'People'],
    ['phones', 'See mobile numbers unmasked', 'People'],
    ['reports', 'See “Reports” tab', 'Reports'],
    ['export', 'Export CSV / Print', 'Reports'],
    ['viewas', 'Use “View as employee”', 'Admin'],
    ['t_raise', 'Raise tickets', 'Tickets'],
    ['t_all', 'See all tickets', 'Tickets'],
    ['t_manage', 'Manage any ticket (resolve, resolver, hold, priority)', 'Tickets']
  ];
  var SCOPES = [['own', 'Own only (mine, by me, CC, my groups)'], ['dept', 'My department + own'], ['branch', 'My branch + own'], ['all', 'All branches']];
  var MODULES = [
    ['tasks', 'Task Management', 'Whole Tasks module'], ['tickets', 'Ticket / Helpdesk', 'Whole Tickets module'], ['team', 'Team & Contacts tab', 'Employee directory with mobiles'],
    ['reports', 'Reports tab', 'Performance analytics'], ['viewas', 'View as employee', 'Preview any employee’s screen'], ['group', 'Group tasks', 'One task to many people with shared updates'],
    ['recent', 'Recent tasks panel', 'Last 5 assigned on the Assign screen'], ['checklist', 'Checklist / sub-steps', 'Optional steps inside a task'],
    ['email', 'Email notifications', 'Send ERP email on assign / remind'], ['wa', 'WhatsApp notifications', 'One-tap wa.me messages'],
    ['repMandatory', 'Reporting rule mandatory', 'Must choose EOD / Weekly / … before assigning'], ['delayMandatory', 'Delay remark mandatory', 'Overdue tasks need a delay remark before any action']
  ];
  function allPerms(v) { var o = { scope: 'all' }; PERMS.forEach(function (p) { o[p[0]] = v; }); return o; }
  function defaultCfg() {
    var tc = {};
    Object.keys(TICKET_CATEGORY_MAP).forEach(function (c) { tc[c] = { a: 1, issues: TICKET_CATEGORY_MAP[c].map(function (i) { return { n: i, a: 1 }; }) }; });
    return {
      v: 3,
      modules: { tasks: 1, tickets: 1, team: 1, reports: 1, viewas: 1, group: 1, recent: 1, checklist: 1, email: 1, wa: 1, repMandatory: 1, delayMandatory: 1 },
      roles: {
        'Admin': allPerms(1),
        'Manager': { scope: 'all', assign: 1, all_tab: 1, manage: 1, group: 1, team: 1, phones: 1, reports: 1, export: 1, viewas: 1, t_raise: 1, t_all: 1, t_manage: 1 },
        'Cluster Head': { scope: 'branch', assign: 1, all_tab: 1, manage: 1, group: 1, team: 1, phones: 1, reports: 1, export: 1, viewas: 0, t_raise: 1, t_all: 1, t_manage: 0 },
        'Team Lead': { scope: 'dept', assign: 1, all_tab: 1, manage: 0, group: 1, team: 0, phones: 0, reports: 1, export: 0, viewas: 0, t_raise: 1, t_all: 0, t_manage: 0 },
        'Employee': { scope: 'own', assign: 1, all_tab: 0, manage: 0, group: 0, team: 0, phones: 0, reports: 0, export: 0, viewas: 0, t_raise: 1, t_all: 0, t_manage: 0 }
      },
      userRoles: { 'bhuvan@lifescc.com': 'Admin', 'narendhar@lifescc.com': 'Admin' },
      desigRules: [['Cluster Head', 'Cluster Head'], ['Center Manager', 'Team Lead']],
      defaultRole: 'Employee',
      admins: [],
      categories: ['Sales', 'Services', 'Operations', 'Audit', 'Accounts', 'HR', 'IT', 'Marketing', 'Call Centre', 'Clinical / Medical', 'Machinery', 'Inventory / Stock', 'Facility / Maintenance', 'Training', 'Compliance / Licenses', 'Management'].map(function (n) { return { n: n, a: 1 }; }),
      pri: {
        VVIMP: { label: 'VV IMP', hint: 'Drop everything – do first' }, IMP: { label: 'IMP', hint: 'Top of queue, today' }, HI: { label: 'HI-Priority', hint: 'Before routine work' },
        MED: { label: 'Medium', hint: 'Normal working order' }, LOW: { label: 'Low', hint: 'When free' }
      },
      reports: { EOD: 1, WEEKLY: 1, MONTHLY: 1, SPECIFIC: 1, COMPLETION: 1 },
      tCats: tc, sla: { High: 24, Medium: 72, Low: 168 }, resolvers: {},
      phone: { mask: 1, codeHash: '', minutes: 15 },
      savedBy: '', savedOn: ''
    };
  }
  function mergeCfg(base, src) {
    if (!src || typeof src !== 'object') return base;
    Object.keys(src).forEach(function (k) {
      if (src[k] && typeof src[k] === 'object' && !Array.isArray(src[k]) && base[k] && typeof base[k] === 'object' && !Array.isArray(base[k]) && ['roles', 'userRoles', 'tCats', 'resolvers'].indexOf(k) < 0) base[k] = mergeCfg(base[k], src[k]);
      else base[k] = src[k];
    });
    return base;
  }

  /* ================================================================
     HELP TEXTS  (hover a 💡 to read, click to pin)
  ================================================================ */
  var HELP = {
    overview: ['How this screen works', ['Top switch: <b>Tasks</b> = work given to people. <b>Tickets</b> = problems raised by branches.', 'Tiles at top are live counts — click a tile to open that list.', 'Hover any 💡 for help on that part; click it to keep the help open.', 'Click a task / ticket title to open its full panel on the right.'], 'Mobile numbers are masked unless your role allows them — click 🔒 and enter the code to view.'],
    viewas: ['View as employee', ['Pick a person in <b>View as…</b> (top right).', 'The page shows exactly their screen and their rights.', 'Buttons are blocked in preview.', 'Choose “my own view” to return.'], ''],
    a_who: ['Who is this task for?', ['Choose <b>Employee(s)</b>, <b>Branch</b>, <b>Department</b> or <b>Designation</b>.', 'Employee(s): type a name and click to add — add as many as needed.', 'Branch / Dept / Designation: click chips; everyone with ERP login gets ticked — untick who you don’t want.', 'Greyed people have no ERP login and cannot receive tasks.', 'When more than one person is selected you choose <b>Group task</b> or <b>Individual tasks</b>.'], ''],
    a_mode: ['Group or individual?', ['<b>Individual tasks</b>: each person gets a separate task with own number; they only see their own updates.', '<b>Group task</b>: ONE task shared by everyone; all members see every member’s updates.', 'Group response = <b>Group</b>: any member’s Done completes it for all.', 'Group response = <b>Individual</b>: each member must report and complete their own part; the task closes when all are done.', 'Leader receives the main ERP assignment; others get a linked entry.'], ''],
    a_pri: ['Priority numbers', ['<b>P1 VV IMP</b> – drop everything, do first.', '<b>P2 IMP</b> – top of queue, today.', '<b>P3 HI-Priority</b> – before routine work.', '<b>P4 Medium</b> – normal working order.', '<b>P5 Low</b> – when free.', 'Queue # = working order per person; P1 always lands above P2, P2 above P3…', 'Tick “Force to #1” to override.'], 'Labels can be changed in Control Panel → Masters.'],
    a_what: ['Task details', ['Category + short clear title (max 80 characters).', 'Start is auto (now). Due is mandatory — duration shows beside the label.', 'Details: what exactly must be done (max 150 words).', 'Checklist: one step per line; ticking steps updates progress.'], ''],
    a_rep: ['Reporting rule', ['Choose EOD, Weekly (weekday), Monthly (date), Specific date-time, or Only on completion.', 'Late reports turn red in “Reports Due” and count in Reports.'], ''],
    a_notify: ['CC, notifications & files', ['CC: people who must see updates and completion (you are always included).', 'Email: ERP sends a formatted mail.', 'WhatsApp: after assigning, tap the green button per person.', 'Attach photos / PDF / Excel up to 5 MB each.'], ''],
    a_prev: ['Preview', ['Shows each person’s current load, new task number and queue #.', 'Red “Missing” items must be filled before Assign.'], ''],
    a_recent: ['Recent tasks', ['Your last 5 assigned tasks. Click one to open its details directly.'], ''],
    all: ['All Tasks', ['Filters narrow the list; search works on task no, title, person, branch.', 'Views: Table, Queue by Assignee (Manage Queue), Status Board.', 'Click a header to sort. Click a title to open.', 'What you can see depends on your role’s data scope (Control Panel).'], ''],
    my: ['My Tasks', ['The top card is your #1 — work on it first.', '▶ Start → 💬 Update → 📝 Report → ✓ Done.', 'Overdue tasks need a Delay Remark first.', 'Group tasks show 👥 — you can see all members’ updates.'], ''],
    team: ['Team & Contacts', ['All employees with designation, department, branch and mobile.', 'Mobiles are masked unless your role allows or you unlock with the code.', 'Assign opens the form with that person selected; Queue shows their working order.'], 'Visible only to roles allowed in Control Panel.'],
    reports: ['Reports', ['Pick period and Group by.', 'On-time % = closed before due ÷ all closed. Score drops for overdue, late closures and missed reports.'], ''],
    drawer: ['Task panel', ['Header: task no, queue #, priority, status.', 'Progress slider and checklist set % done.', 'Everyone involved can post Update / Report / Delay Remark / Query with files.', 'Buttons depend on your role.'], ''],
    t_raise: ['Raise a ticket', ['Pick branch, category and issue. “Other” needs a description; staff issues need the employee.', 'Resolver is suggested from Control Panel → Ticket masters.', 'Priority sets SLA.', 'Write details, attach photos, Submit.'], ''],
    t_all: ['All Tickets', ['Filter by status, priority, category, branch, resolver.', 'SLA turns red when breached.'], ''],
    t_my: ['My Tickets', ['Tagged to me: resolve and Mark Resolved.', 'Raised by me: Close if satisfied or Reopen.'], ''],
    t_drawer: ['Ticket panel', ['Resolver posts updates then Mark Resolved.', 'Raiser closes or reopens.'], ''],
    cpanel: ['Control Panel', ['Only admins (Bhuvan, Narendhar + added admins) see this.', '<b>Modules</b>: switch features on / off for everyone.', '<b>Roles & Rights</b>: tick what each role can do and its data scope.', '<b>Users</b>: set a person’s role, or let designation rules / default decide.', '<b>Masters</b>: categories, priority labels, reporting types, ticket categories / issues, SLA, default resolvers.', '<b>Phone privacy</b>: masking on/off, unlock code, unlock minutes.', 'Click <b>Save Control Panel</b> — changes apply to everyone after their next refresh.'], 'Settings are stored in ERP Note “' + CFG_TITLE + '”.']
  };

  /* ================================================================
     STATE
  ================================================================ */
  var S = {
    live: false, cfg: defaultCfg(), cfgNote: null, draft: null, me: {}, realMe: null, people: [], byUser: {}, tasks: [], files: {}, tickets: [], tfiles: {},
    mod: 'task', tab: { task: 'assign', ticket: 'traise' }, allView: 'table', myTab: 'tome', tmyTab: 'tagged', cpTab: 'mods', page: 1, sort: { k: 'q', d: 1 },
    f: { q: '', branch: '', dept: '', desig: '', assignee: '', by: '', cat: '', pri: '', status: 'Active', rep: '', from: '', to: '', grp: '' },
    tf: { q: '', status: 'Active', pri: '', cat: '', branch: '', tag: '' }, team: { q: '', branch: '', dept: '' }, cpq: '',
    form: null, tform: null, pendingFiles: [], tFiles: [], openTask: null, openTicket: null, rptDim: 'assignee', phoneUntil: 0
  };
  var root, clockTimer;

  /* ================================================================
     HELPERS
  ================================================================ */
  function q(s, el) { return (el || root).querySelector(s); }
  function qa(s, el) { return Array.prototype.slice.call((el || root).querySelectorAll(s)); }
  function esc(v) { return String(v == null ? '' : v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
  function pad(n) { return String(n).padStart(2, '0'); }
  function localStr(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + 'T' + pad(d.getHours()) + ':' + pad(d.getMinutes()); }
  function nowLocal() { return localStr(new Date()); }
  function todayStr() { return nowLocal().slice(0, 10); }
  function toDate(s) { if (!s) return null; s = String(s).replace(' ', 'T'); if (s.length === 10) s += 'T00:00'; var d = new Date(s.slice(0, 19)); return isNaN(d) ? null : d; }
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function fD(s) { var d = toDate(s); return d ? pad(d.getDate()) + '-' + MON[d.getMonth()] + '-' + String(d.getFullYear()).slice(2) : '—'; }
  function fDT(s) { var d = toDate(s); return d ? fD(s) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) : '—'; }
  function dur(ms) { ms = Math.abs(ms); var m = Math.floor(ms / 60000), d = Math.floor(m / 1440), h = Math.floor((m % 1440) / 60), mi = m % 60; if (d) return d + 'd ' + h + 'h'; if (h) return h + 'h ' + mi + 'm'; return mi + 'm'; }
  function initials(n) { return String(n || '?').trim().split(/\s+/).map(function (w) { return w.charAt(0); }).join('').slice(0, 2).toUpperCase(); }
  function words(t) { t = String(t || '').trim(); return t ? t.split(/\s+/).length : 0; }
  function uid(p) { return (p || 'U') + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }
  function norm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]/g, ''); }
  function uniq(a) { var o = {}, r = []; a.forEach(function (x) { if (x && !o[x]) { o[x] = 1; r.push(x); } }); return r; }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function fsize(b) { b = +b || 0; return b < 1024 ? b + ' B' : b < 1048576 ? Math.round(b / 1024) + ' KB' : (b / 1048576).toFixed(1) + ' MB'; }
  function htmlToText(v) {
    v = String(v || '').replace(/<!--[\s\S]*?-->/g, '').replace(/<br\s*\/?>/gi, '\n').replace(/<\/(p|div|li)>/gi, '\n').replace(/<li[^>]*>/gi, '• ').replace(/<[^>]+>/g, '');
    var t = document.createElement('textarea'); t.innerHTML = v; v = t.value;
    return v.replace(/\r/g, '').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
  }
  function person(u) { return S.byUser[String(u || '').toLowerCase()] || null; }
  function personName(u) { if (!u) return '—'; var p = person(u); if (p) return p.name; return String(u).indexOf('@') > -1 ? String(u).split('@')[0] : u; }
  function toast(msg, err) { var t = q('#toast'); t.textContent = msg; t.className = 'toast show' + (err ? ' err' : ''); clearTimeout(t._t); t._t = setTimeout(function () { t.className = 'toast'; }, 3400); }
  function csv(name, rows) {
    if (!can('export')) { toast('Your role cannot export', 1); return; }
    var out = rows.map(function (r) { return r.map(function (c) { c = String(c == null ? '' : c).replace(/"/g, '""'); return /[",\n]/.test(c) ? '"' + c + '"' : c; }).join(','); }).join('\n');
    var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob(['﻿' + out], { type: 'text/csv' })); a.download = name + '_' + todayStr() + '.csv'; document.body.appendChild(a); a.click(); a.remove();
  }
  function optList(arr, sel, all) { return (all === null ? '' : '<option value="">' + (all || 'All') + '</option>') + arr.map(function (x) { var v = Array.isArray(x) ? x[0] : x, l = Array.isArray(x) ? x[1] : x; return '<option value="' + esc(v) + '" ' + (sel === v ? 'selected' : '') + '>' + esc(l) + '</option>'; }).join(''); }
  function hb(k) { return '<button class="hb" data-help="' + k + '" title="">&#128161;</button>'; }
  function TD(l, h, cls) { return '<td data-l="' + esc(l) + '"' + (cls ? ' class="' + cls + '"' : '') + '>' + h + '</td>'; }
  function cols(arr) { return '<colgroup>' + arr.map(function (w) { return '<col style="width:' + w + '%">'; }).join('') + '</colgroup>'; }
  function guard() { if (S.me.preview) { toast('Preview mode — switch “View as” back to your own view to make changes', 1); return true; } return false; }

  /* ================================================================
     ROLES & PERMISSIONS
  ================================================================ */
  function isAdmin(u) { u = String(u || '').toLowerCase(); return CORE_ADMINS.indexOf(u) > -1 || (S.cfg.admins || []).map(function (x) { return x.toLowerCase(); }).indexOf(u) > -1; }
  function roleOf(u) {
    if (isAdmin(u)) return 'Admin';
    var c = S.cfg, r = c.userRoles[u] || c.userRoles[String(u || '').toLowerCase()];
    if (r && c.roles[r]) return r;
    var p = person(u);
    if (p) for (var i = 0; i < (c.desigRules || []).length; i++) { var rule = c.desigRules[i]; if (rule[0] && rule[1] && c.roles[rule[1]] && String(p.desig || '').toLowerCase() === String(rule[0]).toLowerCase()) return rule[1]; }
    return c.roles[c.defaultRole] ? c.defaultRole : 'Employee';
  }
  function roleSource(u) { if (isAdmin(u)) return 'Admin (core)'; if (S.cfg.userRoles[u]) return 'Set directly'; var p = person(u); if (p && (S.cfg.desigRules || []).some(function (r) { return String(p.desig || '').toLowerCase() === String(r[0]).toLowerCase(); })) return 'Designation rule'; return 'Default'; }
  function permsOf(u) { var r = S.cfg.roles[roleOf(u)] || S.cfg.roles.Employee || {}; return r; }
  function can(p) { if (S.me.admin && !S.me.preview) return true; var r = S.me.perms || {}; return !!r[p]; }
  function mod(k) { return !!(S.cfg.modules || {})[k]; }
  function scope() { return (S.me.admin && !S.me.preview) ? 'all' : ((S.me.perms || {}).scope || 'own'); }
  function setMe(u, name, extra) {
    var p = person(u) || {};
    var me = { user: u, name: name || p.name || u, dept: p.dept, branch: p.branch, desig: p.desig, image: extra && extra.image, admin: isAdmin(u), role: roleOf(u), perms: permsOf(u) };
    me.isMgr = me.admin || !!me.perms.manage;
    return me;
  }

  /* ================================================================
     PHONE MASKING
  ================================================================ */
  function digits(p) { return String(p || '').replace(/\D/g, '').replace(/^0+/, ''); }
  function phone91(p) { p = digits(p); if (p.length === 10) p = '91' + p; return p.length === 12 && p.indexOf('91') === 0 ? p : ''; }
  function mob(u) { var p = person(u); return p ? p.phone : ''; }
  function phonesOpen() { return !S.cfg.phone.mask || can('phones') || Date.now() < S.phoneUntil; }
  function maskNum(d) { d = d.slice(-10); return d.slice(0, 2) + 'XXXXXX' + d.slice(-2); }
  function showNum(ph) { var d = digits(ph); if (!d) return ''; return phonesOpen() ? d.slice(-10) : maskNum(d); }
  function phHtml(u, plain) {
    var ph = typeof u === 'object' ? (u && u.phone) : mob(u), d = digits(ph);
    if (!d) return '<span class="ph no">📞 —</span>';
    if (!phonesOpen()) return S.cfg.phone.codeHash ? '<span class="ph" data-act="unlock" style="color:var(--muted);cursor:pointer" title="Click and enter code to view numbers">🔒 ' + maskNum(d) + '</span>' : '<span class="ph" style="color:var(--muted)">📞 ' + maskNum(d) + '</span>';
    return plain ? '<span class="ph">📞 ' + esc(d.slice(-10)) + '</span>' : '<a class="ph" href="tel:+' + (phone91(ph) || d) + '" title="Call">📞 ' + esc(d.slice(-10)) + '</a>';
  }
  function sha256(s) {
    if (window.crypto && crypto.subtle && window.TextEncoder) return crypto.subtle.digest('SHA-256', new TextEncoder().encode('LIFE-TM|' + s)).then(function (b) { return Array.prototype.map.call(new Uint8Array(b), function (x) { return ('0' + x.toString(16)).slice(-2); }).join(''); });
    var h = 5381; s = 'LIFE-TM|' + s; for (var i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return Promise.resolve('d' + (h >>> 0).toString(16));
  }
  function unlockPhones() {
    if (!S.cfg.phone.codeHash) { toast('No unlock code set — ask admin', 1); return; }
    modal('🔒 Enter code to view mobile numbers', '<div class="hint" style="margin-bottom:6px">Numbers stay visible for ' + (S.cfg.phone.minutes || 15) + ' minutes on this device.</div><input type="password" id="m-code" placeholder="Unlock code" autocomplete="off">', [['Cancel', '', closeModal], ['Unlock', 'pri', function () {
      var c = q('#m-code').value.trim(); if (!c) return;
      sha256(c).then(function (h) {
        if (h !== S.cfg.phone.codeHash) { toast('Wrong code', 1); return; }
        S.phoneUntil = Date.now() + (S.cfg.phone.minutes || 15) * 60000;
        try { sessionStorage.setItem('life_tm_ph', String(S.phoneUntil)); } catch (e) { }
        closeModal(); toast('Numbers visible for ' + (S.cfg.phone.minutes || 15) + ' min'); render(); refreshOpen();
      });
    }]]);
    setTimeout(function () { var x = q('#m-code'); if (x) x.focus(); }, 50);
  }

  /* config-driven lists */
  function PRI_L(k) { var p = (S.cfg.pri || {})[k] || {}; return p.label || k; }
  function PRI_H(k) { return ((S.cfg.pri || {})[k] || {}).hint || ''; }
  function PRI_W(k) { var i = PRI_KEYS.indexOf(k); return i < 0 ? 4 : i + 1; }
  function PRI_N(k) { return 'P' + PRI_W(k); }
  function categories() { return S.cfg.categories.filter(function (c) { return c.a; }).map(function (c) { return c.n; }); }
  function reportTypes() { return REPORT_DEF.filter(function (r) { return S.cfg.reports[r.k]; }); }
  function REP(k) { return REPORT_DEF.filter(function (r) { return r.k === k; })[0] || REPORT_DEF[4]; }
  function tCats() { return Object.keys(S.cfg.tCats).filter(function (c) { return S.cfg.tCats[c].a; }); }
  function tIssues(c) { var x = S.cfg.tCats[c]; return x ? x.issues.filter(function (i) { return i.a; }).map(function (i) { return i.n; }) : []; }
  function SLA(p) { return +((S.cfg.sla || {})[p]) || 72; }

  /* ================================================================
     TASK STATUS HELPERS
  ================================================================ */
  function isClosed(t) { return t.status === 'Completed' || t.status === 'Cancelled'; }
  function isOverdue(t, now) { if (isClosed(t)) return false; var d = toDate(t.due); return d && d < (now || new Date()); }
  function dueToday(t) { return !isClosed(t) && t.due && t.due.slice(0, 10) === todayStr(); }
  function priPill(k) { return '<span class="pill p-' + k + '" title="' + esc(PRI_H(k)) + '">' + PRI_N(k) + ' · ' + esc(PRI_L(k)) + '</span>'; }
  function stPill(t) { return '<span class="pill ' + (ST_CLS[t.status] || 's-open') + '">' + esc(t.status) + '</span>' + (isOverdue(t) ? ' <span class="pill s-od">Overdue</span>' : ''); }
  function grpTag(t) { return t.grp ? ' <span class="grp" title="Group task · ' + t.grp.members.length + ' members · ' + (t.grp.response === 'group' ? 'group response' : 'individual response') + '">👥 ' + t.grp.members.length + '</span>' : ''; }
  function timeLeft(t) {
    if (t.status === 'Completed') { var c = toDate(t.completedOn), d = toDate(t.due); if (c && d) return c <= d ? '<span class="grn">On time</span>' : '<span class="red">Late ' + dur(c - d) + '</span>'; return '<span class="grn">Done</span>'; }
    if (t.status === 'Cancelled') return '<span class="mut">—</span>';
    var dd = toDate(t.due); if (!dd) return '—'; var ms = dd - new Date();
    return ms < 0 ? '<span class="red"><b>-' + dur(ms) + '</b></span>' : ms < 86400000 ? '<span class="amb"><b>' + dur(ms) + '</b></span>' : '<span class="mut">' + dur(ms) + '</span>';
  }
  function canManage(t) { return can('manage') || t.by === S.me.user || t.owner === S.me.user; }
  function isAssignee(t) { return t.assignee === S.me.user; }
  function fileKey(t) { return t.mid || t.id; }

  /* ================================================================
     TASK META  (compatible with old LIFE_TASK_META + custom_task_queue_no)
     Group task = one MASTER ToDo (leader) shared with members + MIRROR ToDos.
     In the UI a group task is shown as one row per member (virtual task).
  ================================================================ */
  function parseMeta(desc, type) { var m = String(desc || '').match(new RegExp('<!--LIFE_' + type + '_META:([\\s\\S]*?)-->')); if (!m) return {}; try { return JSON.parse(m[1]); } catch (e) { return {}; } }
  function legacyUpdates(m) {
    var out = [];
    var add = function (arr, type, label) { (arr || []).forEach(function (h) { out.push({ id: uid(), at: String(h.on || h.reviewed_on || h.at || h.date || '').replace(' ', 'T').slice(0, 16), by: h.by || h.reviewed_by || h.user || '', type: type, text: (label ? label + ': ' : '') + (h.remarks || h.text || h.update || h.message || h.status || '') }); }); };
    add(m.assigner_updates, 'Update'); add(m.status_history, 'System', 'Status'); add(m.completion_history, 'Completion', 'Completed'); add(m.close_history, 'System', 'Closed'); add(m.reopen_history, 'System', 'Reopened'); add(m.reassign_history, 'System', 'Reassigned'); add(m.queue_history, 'System', 'Queue');
    return out.sort(function (a, b) { return a.at > b.at ? 1 : -1; });
  }
  function base(r) {
    var m = parseMeta(r.description, 'TASK');
    var txt = htmlToText(r.description), title = m.title || '', details = txt;
    if (title) { var first = txt.split('\n')[0].trim(); if (first === title.trim()) details = txt.split('\n').slice(1).join('\n').trim(); }
    else title = txt.split('\n')[0].slice(0, 90) || '(No title)';
    if (m.grp) details = details.replace(/^👥 Group task[^\n]*\n?/, '').trim();
    var wf = m.workflow_state;
    var st = m.status || (r.status === 'Cancelled' ? 'Cancelled' : r.status === 'Closed' ? 'Completed' : wf === 'Completed' ? 'Review Pending' : wf === 'Reopened' ? 'Reopened' : 'Open');
    if (r.status === 'Cancelled') st = 'Cancelled';
    if (r.status === 'Closed' && st !== 'Cancelled' && !m.grp) st = 'Completed';
    var cc = m.cc || m.update_to || []; if (typeof cc === 'string') cc = cc.split(',').map(function (x) { return x.trim(); }).filter(Boolean);
    var created = m.created || String(r.creation || '').replace(' ', 'T').slice(0, 16), cq = +r.custom_task_queue_no || 0, cd = toDate(created);
    var t = {
      id: r.name, raw: r, meta: m, no: m.no || '', title: title, details: details, cat: m.cat || m.category || 'General',
      pri: PRI_KEYS.indexOf(m.pri) > -1 ? m.pri : (LEGACY_PRI[r.priority] || 'MED'), status: st,
      assignee: r.allocated_to || '', by: r.assigned_by || r.owner || '', owner: r.owner || '',
      created: created, start: m.start || (m.start_date ? m.start_date + 'T09:00' : created), due: m.due || m.deadline_datetime || (r.date ? r.date + 'T18:00' : ''),
      cc: cc, report: m.report || { type: 'COMPLETION' }, notify: m.notify || {}, checklist: m.checklist || [],
      progress: +m.progress || 0, updates: m.updates || legacyUpdates(m), delays: m.delays || m.delay_reviews || [],
      completedOn: m.completed_on || String(r.custom_completed_on || '').replace(' ', 'T').slice(0, 16), target: m.target || { type: 'Employee' },
      qk: cq > 0 ? cq : (m.qk != null ? +m.qk : 1000 + (cd ? cd.getTime() / 1e10 : 0)), cq: cq, legacy: !m.v, modified: r.modified || '', grp: m.grp || null
    };
    if (t.status === 'Completed' && !t.completedOn) t.completedOn = String(r.modified || '').replace(' ', 'T').slice(0, 16);
    if (t.status === 'Completed' || t.status === 'Review Pending') t.progress = 100;
    return t;
  }
  function enrich(t) { var p = person(t.assignee); t.branch = (p && p.branch) || t.meta.branch || ''; t.dept = (p && p.dept) || t.meta.dept || ''; t.desig = (p && p.desig) || t.meta.desig || ''; return t; }
  function explode(b) {
    var g = b.grp, out = [];
    (g.members || []).forEach(function (u) {
      var v = {}; Object.keys(b).forEach(function (k) { v[k] = b[k]; });
      v.id = b.id + '::' + u; v.mid = b.id; v.assignee = u; v.cq = 0;
      var ms = (b.meta.mstate || {})[u] || {};
      if (g.response === 'individual') { v.status = ms.status || 'Open'; v.progress = +ms.progress || 0; v.completedOn = ms.completedOn || ''; v.checklist = ms.checklist || clone(b.checklist); }
      else { v.checklist = b.checklist; }
      if (b.status === 'Cancelled') v.status = 'Cancelled';
      if (v.status === 'Completed' || v.status === 'Review Pending') v.progress = 100;
      var mq = (b.meta.mq || {})[u]; v.qk = mq != null ? +mq : b.qk; v.mqs = mq != null ? +mq : null;
      out.push(enrich(v));
    });
    return out;
  }
  function normalizeRows(rows) {
    var tasks = [], mirrors = [], have = {};
    rows.forEach(function (r) {
      var m = parseMeta(r.description, 'TASK');
      if (m.mirror_of) { mirrors.push({ id: r.name, master: m.mirror_of, user: r.allocated_to }); return; }
      var b = base(r); have[b.id] = 1;
      if (b.grp && b.grp.members && b.grp.members.length) tasks = tasks.concat(explode(b)); else tasks.push(enrich(b));
    });
    return { tasks: tasks, missing: uniq(mirrors.filter(function (x) { return !have[x.master]; }).map(function (x) { return x.master; })) };
  }
  function denormBase(b) {
    var meta = {}; Object.keys(b.meta || {}).forEach(function (k) { meta[k] = b.meta[k]; });
    var wf = b.status === 'Review Pending' ? 'Completed' : b.status === 'Completed' ? 'Closed' : b.status === 'Reopened' ? 'Reopened' : b.status === 'Cancelled' ? 'Cancelled' : 'Open';
    var add = { v: 3, no: b.no, title: b.title, cat: b.cat, category: b.cat, pri: b.pri, status: b.status, workflow_state: wf, start: b.start, start_date: (b.start || '').slice(0, 10), due: b.due, deadline_datetime: b.due, cc: b.cc, update_to: b.cc, report: b.report, notify: b.notify, checklist: b.checklist, progress: b.progress, updates: b.updates, delays: b.delays, delay_reviews: b.delays, completed_on: b.completedOn, created: b.created, target: b.target, qk: b.qk, branch: b.branch, dept: b.dept, desig: b.desig };
    Object.keys(add).forEach(function (k) { meta[k] = add[k]; });
    if (b.grp) meta.grp = b.grp;
    ['assigner_updates', 'status_history', 'completion_history', 'close_history', 'reopen_history', 'reassign_history', 'queue_history'].forEach(function (k) { delete meta[k]; });
    var json = JSON.stringify(meta).replace(/-->/g, '--\\u003e');
    return {
      description: '<!--LIFE_TASK_META:' + json + '-->\n<b>' + esc(b.title) + '</b><br>' + (b.grp ? '👥 Group task (' + b.grp.members.length + ' members)<br>' : '') + esc(b.details).replace(/\n/g, '<br>'),
      status: b.status === 'Completed' ? 'Closed' : b.status === 'Cancelled' ? 'Cancelled' : 'Open',
      priority: PRI_TODO[b.pri] || 'Medium', date: (b.due || '').slice(0, 10) || null
    };
  }
  function mirrorDoc(masterName, b, u) {
    var meta = { v: 3, mirror_of: masterName, no: b.no, title: b.title, grp_id: b.grp.id };
    return { doctype: 'ToDo', allocated_to: u, assigned_by: b.by, priority: PRI_TODO[b.pri], date: (b.due || '').slice(0, 10), status: 'Open', description: '<!--LIFE_TASK_META:' + JSON.stringify(meta) + '-->\n<b>' + esc(b.title) + '</b><br>👥 Group task ' + esc(b.no) + ' — open Task Management to see details and group updates.' };
  }
  function groupOverall(b) {
    if (b.status === 'Cancelled') return 'Cancelled';
    var g = b.grp; if (g.response !== 'individual') return b.status;
    var sts = g.members.map(function (u) { return ((b.meta.mstate || {})[u] || {}).status || 'Open'; });
    if (sts.every(function (s) { return s === 'Completed'; })) return 'Completed';
    if (sts.every(function (s) { return s === 'Completed' || s === 'Review Pending'; })) return 'Review Pending';
    if (sts.some(function (s) { return s === 'In Progress' || s === 'Completed' || s === 'Review Pending'; })) return 'In Progress';
    return 'Open';
  }

  /* ================================================================
     TICKETS (compatible with old LIFE_TICKET_META on Issue)
  ================================================================ */
  function ticketDetailsFrom(desc) { var txt = htmlToText(desc), i = txt.search(/Details:\s*/i); return i > -1 ? txt.slice(i).replace(/^Details:\s*/i, '').trim() : txt; }
  function normTicket(r) {
    var m = parseMeta(r.description, 'TICKET');
    var st = r.status === 'Closed' ? 'Closed' : r.status === 'Resolved' ? 'Resolved' : r.status === 'On Hold' ? 'On Hold' : (m.workflow_state === 'Reopened' && r.status === 'Open') ? 'Reopened' : (r.status || 'Open');
    if (st === 'Replied') st = 'Open';
    var cc = m.cc_to || []; if (typeof cc === 'string') cc = cc.split(',').map(function (x) { return x.trim(); }).filter(Boolean);
    var upd = m.updates ? m.updates.slice() : [];
    if (!m.updates) {
      (m.resolution_history || []).forEach(function (h) { upd.push({ at: String(h.on || '').slice(0, 16), by: h.by, type: 'Resolved', text: h.remarks || '' }); });
      (m.reopen_history || []).forEach(function (h) { upd.push({ at: String(h.on || '').slice(0, 16), by: h.by, type: 'Reopened', text: h.remarks || '' }); });
      (m.close_history || []).forEach(function (h) { upd.push({ at: String(h.on || '').slice(0, 16), by: h.by, type: 'Closed', text: h.remarks || '' }); });
      upd.sort(function (a, b) { return a.at > b.at ? 1 : -1; });
    }
    return {
      id: r.name, raw: r, meta: m, subject: r.subject || ((m.category || '') + ' - ' + (m.issue || '')), cat: m.category || '', issue: m.issue || '', other: m.other_text || '', emp: m.employee_involved || '',
      branch: m.branch || '', tag: m.tag_to || '', cc: cc, raiser: r.raised_by || r.owner || '', owner: r.owner || '', pri: TK_PRI.indexOf(r.priority) > -1 ? r.priority : 'Medium',
      status: st, details: ticketDetailsFrom(r.description), created: String(r.creation || r.opening_date || '').replace(' ', 'T').slice(0, 16), updates: upd, resolvedOn: m.resolved_on || '', closedOn: m.closed_on || '', modified: r.modified || ''
    };
  }
  function tkDesc(tk) {
    var m = {}; Object.keys(tk.meta || {}).forEach(function (k) { m[k] = tk.meta[k]; });
    m.branch = tk.branch; m.category = tk.cat; m.issue = tk.issue; m.other_text = tk.other; m.employee_involved = tk.emp; m.tag_to = tk.tag; m.cc_to = tk.cc;
    m.updates = tk.updates; m.workflow_state = tk.status; m.resolved_on = tk.resolvedOn; m.closed_on = tk.closedOn; m.v = 3;
    var parts = ['<!--LIFE_TICKET_META:' + JSON.stringify(m).replace(/-->/g, '--\\u003e') + '-->', '<b>Branch:</b> ' + esc(tk.branch), '<b>Category:</b> ' + esc(tk.cat), '<b>Issue:</b> ' + esc(tk.issue)];
    if (tk.other) parts.push('<b>Other Issue:</b> ' + esc(tk.other));
    if (tk.emp) parts.push('<b>Employee Involved:</b> ' + esc(tk.emp));
    parts.push('<b>Tagged To:</b> ' + esc(personName(tk.tag)));
    if (tk.cc.length) parts.push('<b>CC To:</b> ' + esc(tk.cc.map(personName).join(', ')));
    parts.push('<br><b>Details:</b><br>' + esc(tk.details).replace(/\n/g, '<br>'));
    return parts.join('<br>');
  }
  function tkStatusField(st) { return st === 'Reopened' ? 'Open' : st; }
  function tkClosed(tk) { return tk.status === 'Closed'; }
  function tkActive(tk) { return tk.status !== 'Closed' && tk.status !== 'Resolved'; }
  function tkSla(tk) { var c = toDate(tk.created); return c ? new Date(c.getTime() + SLA(tk.pri) * 3600000) : null; }
  function tkBreach(tk) { var s = tkSla(tk); return tkActive(tk) && s && s < new Date(); }
  function tkSlaHtml(tk) {
    if (!tkActive(tk)) { var r = toDate(tk.resolvedOn || tk.closedOn), s = tkSla(tk); return r && s ? (r <= s ? '<span class="grn">Within SLA</span>' : '<span class="red">Breached</span>') : '<span class="grn">Done</span>'; }
    var sl = tkSla(tk); if (!sl) return '—'; var ms = sl - new Date();
    return ms < 0 ? '<span class="red"><b>-' + dur(ms) + '</b></span>' : '<span class="' + (ms < 6 * 3600000 ? 'amb' : 'mut') + '">' + dur(ms) + '</span>';
  }
  function tkPill(tk) { return '<span class="pill ' + (ST_CLS[tk.status] || 's-open') + '">' + esc(tk.status === 'Resolved' ? 'Resolved – close?' : tk.status) + '</span>' + (tkBreach(tk) ? ' <span class="pill s-od">SLA</span>' : ''); }

  /* ================================================================
     API — LIVE (Frappe) / DEMO (localStorage)
  ================================================================ */
  function fcall(method, args) { return new Promise(function (res, rej) { frappe.call({ method: method, args: args || {}, callback: function (r) { res(r.message); }, error: function (e) { rej(e); } }); }); }
  function errMsg(e) {
    if (!e) return 'Something went wrong';
    try { if (e._server_messages) return JSON.parse(e._server_messages).map(function (m) { try { return JSON.parse(m).message; } catch (x) { return m; } }).join(' ').replace(/<[^>]+>/g, ''); } catch (x) { }
    if (e.responseJSON && e.responseJSON._server_messages) return errMsg(e.responseJSON);
    return e.message || e.exc_type || String(e);
  }
  function cookieUser() { var m = document.cookie.match(/(?:^|;\s*)user_id=([^;]*)/); var u = m ? decodeURIComponent(m[1]) : ''; return u && u !== 'Guest' ? u : ''; }
  function sessionUser() { var u = window.frappe && frappe.session && frappe.session.user; return (u && u !== 'Guest') ? u : cookieUser(); }
  function getList(doctype, fields, filters, order, limit) {
    var all = [], size = 500;
    function page(start) { return fcall('frappe.client.get_list', { doctype: doctype, fields: fields, filters: filters, order_by: order, limit_start: start, limit_page_length: size }).then(function (r) { r = r || []; all = all.concat(r); return (r.length === size && all.length < (limit || 6000)) ? page(start + size) : all; }); }
    return page(0);
  }
  function uploadXhr(doctype, name, file) {
    const data = new FormData(); data.append('file', file, file.name);
    data.append('is_private', '1'); data.append('doctype', doctype); data.append('docname', name);
    return page.upload(data);
  }
  var LiveAPI = {
    me: function () {
      var u = sessionUser();
      return fcall('frappe.client.get', { doctype: 'User', name: u }).then(function (d) { return { user: u, name: d.full_name || u, image: d.user_image || '' }; })
        .catch(function () { return { user: u, name: (window.frappe && frappe.session && frappe.session.user_fullname) || u, image: decodeURIComponent((document.cookie.match(/user_image=([^;]*)/) || [])[1] || '') }; });
    },
    cfg: function () { return fcall('frappe.client.get_list', { doctype: 'Note', fields: ['name', 'content', 'modified'], filters: { title: CFG_TITLE }, order_by: 'modified desc', limit_page_length: 1 }).then(function (r) { return (r && r[0]) || null; }).catch(function () { return null; }); },
    saveCfg: function (name, html) {
      if (name) return fcall('frappe.client.set_value', { doctype: 'Note', name: name, fieldname: { content: html } }).then(function () { return name; });
      return fcall('frappe.client.insert', { doc: { doctype: 'Note', title: CFG_TITLE, public: 0, content: html } }).then(function (d) { return d.name; });
    },
    users: function () { return getList('User', ['name', 'full_name', 'mobile_no', 'phone', 'user_image'], { enabled: 1, user_type: 'System User' }, 'full_name asc').catch(function () { return []; }); },
    emps: function () { return getList('Employee', ['name', 'employee_name', 'user_id', 'department', 'designation', 'branch', 'cell_number', 'company_email', 'personal_email', 'image'], { status: 'Active' }, 'employee_name asc').catch(function () { return []; }); },
    tasks: function () {
      var f = ['name', 'status', 'priority', 'allocated_to', 'assigned_by', 'owner', 'date', 'description', 'creation', 'modified', 'custom_task_queue_no', 'custom_completed_on'], flt = [['ToDo', 'reference_type', 'is', 'not set']];
      return getList('ToDo', f, flt, 'modified desc').catch(function () { return getList('ToDo', f.slice(0, 10), flt, 'modified desc'); });
    },
    tickets: function () { return getList('Issue', ['name', 'subject', 'description', 'priority', 'status', 'owner', 'raised_by', 'opening_date', 'creation', 'modified'], {}, 'modified desc', 3000).catch(function () { return []; }); },
    files: function (doctype, names) {
      if (!names.length) return Promise.resolve([]);
      var out = [], chunks = []; for (var i = 0; i < names.length; i += 150) chunks.push(names.slice(i, i + 150));
      return chunks.reduce(function (p, ch) { return p.then(function () { return fcall('frappe.client.get_list', { doctype: 'File', fields: ['name', 'file_name', 'file_url', 'attached_to_name', 'file_size'], filters: [['File', 'attached_to_doctype', '=', doctype], ['File', 'attached_to_name', 'in', ch]], limit_page_length: 3000 }).then(function (r) { out = out.concat(r || []); }).catch(function () { }); }); }, Promise.resolve()).then(function () { return out; });
    },
    get: function (dt, name) { return fcall('frappe.client.get', { doctype: dt, name: name }); },
    create: function (doc) { return fcall('frappe.client.insert', { doc: doc }); },
    save: function (dt, name, fields) { return fcall('frappe.client.set_value', { doctype: dt, name: name, fieldname: fields }); },
    share: function (dt, name, user, write) { return fcall('frappe.share.add', { doctype: dt, name: name, user: user, read: 1, write: write ? 1 : 0, share: 0, notify: 0 }); },
    upload: function (dt, name, file) { return uploadXhr(dt, name, file); },
    email: function (to, cc, subject, html, dt, name) { return fcall('frappe.core.doctype.communication.email.make', { recipients: to.join(','), cc: (cc || []).join(','), subject: subject, content: html, doctype: dt, name: name, send_email: 1 }); }
  };
  var DKEY = 'life_tm_demo_v4';
  var DemoAPI = {
    db: function () { try { var d = JSON.parse(localStorage.getItem(DKEY) || 'null'); if (d) return d; } catch (e) { } var s = demoSeed(); this.put(s); return s; },
    put: function (d) { try { localStorage.setItem(DKEY, JSON.stringify(d)); } catch (e) { } },
    me: function () { return Promise.resolve({ user: 'bhuvan@lifescc.com', name: 'K Bhuvan Prasad', image: '' }); },
    cfg: function () { var c = this.db().cfg; return Promise.resolve(c ? { name: 'demo-note', content: c } : null); },
    saveCfg: function (n, html) { var d = this.db(); d.cfg = html; this.put(d); return Promise.resolve('demo-note'); },
    users: function () { return Promise.resolve(this.db().users); },
    emps: function () { return Promise.resolve(this.db().emps); },
    tasks: function () { return Promise.resolve(this.db().todos.slice()); },
    tickets: function () { return Promise.resolve(this.db().issues.slice()); },
    files: function (dt) { return Promise.resolve((this.db().files || []).filter(function (f) { return f.dt === dt; })); },
    coll: function (dt) { return dt === 'Issue' ? 'issues' : 'todos'; },
    get: function (dt, n) { var t = this.db()[this.coll(dt)].filter(function (x) { return x.name === n; })[0]; return t ? Promise.resolve(clone(t)) : Promise.reject({ message: 'Not found' }); },
    create: function (doc) { var d = this.db(); doc.name = doc.doctype === 'Issue' ? 'ISS-2026-' + String(d.issues.length + 101).padStart(5, '0') : uid('td'); doc.owner = S.realMe.user; doc.creation = nowLocal().replace('T', ' ') + ':00'; doc.modified = doc.creation; d[this.coll(doc.doctype)].unshift(doc); this.put(d); return Promise.resolve(clone(doc)); },
    save: function (dt, n, f) { var d = this.db(); d[this.coll(dt)].forEach(function (t) { if (t.name === n) { Object.keys(f).forEach(function (k) { t[k] = f[k]; }); t.modified = nowLocal().replace('T', ' ') + ':00'; } }); this.put(d); return Promise.resolve({}); },
    share: function () { return Promise.resolve({}); },
    upload: function (dt, n, file) { var d = this.db(); var r = { name: uid('f'), file_name: file.name, file_url: '#', attached_to_name: n, file_size: file.size, dt: dt }; d.files = d.files || []; d.files.push(r); this.put(d); return Promise.resolve(r); },
    email: function () { return Promise.resolve({}); }
  };
  var API;

  /* ================================================================
     BOOT  (waits for the portal login → no false DEMO mode)
  ================================================================ */
  function fullWidth() {
    var el = root.parentElement;
    while (el && el !== document.body) { el.style.maxWidth = '100%'; el.style.width = '100%'; el.style.paddingLeft = '0'; el.style.paddingRight = '0'; el.style.marginLeft = '0'; el.style.marginRight = '0'; el = el.parentElement; }
    qa('nav.navbar, .navbar, .web-footer, footer', document).forEach(function (n) { if (!n.contains(root)) n.style.display = 'none'; });
  }
  function boot() {
    root = document.getElementById('life-tm');
    if (!root || root.dataset.booted) return;
    root.dataset.booted = '1';
    // PortalLayout owns the outer page width and navigation.
    S.live = !!(window.frappe && frappe.call && sessionUser());
    API = S.live ? LiveAPI : DemoAPI;
    try { S.phoneUntil = +sessionStorage.getItem('life_tm_ph') || 0; } catch (e) { }
    bindGlobal();
    loadAll();
  }
  function parseCfgNote(n) {
    if (!n || !n.content) return null;
    var m = String(n.content).match(/<!--LIFE_CPANEL:([\s\S]*?)-->/); if (!m) return null;
    try { return JSON.parse(m[1]); } catch (e) { return null; }
  }
  function loadAll() {
    q('#view').innerHTML = '<div class="loading"><div class="spin"></div>Loading tasks, tickets, employees &amp; settings…</div>';
    var meRaw;
    return Promise.all([API.me(), API.cfg()]).then(function (r) {
      meRaw = r[0]; S.cfgNote = r[1] ? r[1].name : null;
      S.cfg = mergeCfg(defaultCfg(), parseCfgNote(r[1]) || {});
      return Promise.all([API.users(), API.emps()]);
    }).then(function (res) {
      buildPeople(res[0] || [], res[1] || []);
      S.realMe = setMe(meRaw.user, meRaw.name, { image: meRaw.image || ((person(meRaw.user) || {}).image) });
      if (!S.me.preview) S.me = S.realMe; else S.me = setMe(S.me.user, S.me.name), S.me.preview = true;
      return Promise.all([API.tasks(), API.tickets()]);
    }).then(function (res) {
      var n = normalizeRows(res[0] || []);
      S.tickets = (res[1] || []).map(normTicket);
      var miss = n.missing.slice(0, 300);
      return miss.reduce(function (p, name) { return p.then(function () { return API.get('ToDo', name).then(function (r) { var b = base(r); if (b.grp) n.tasks = n.tasks.concat(explode(b)); }).catch(function () { }); }); }, Promise.resolve()).then(function () { return n.tasks; });
    }).then(function (tasks) {
      S.tasks = tasks;
      return Promise.all([API.files('ToDo', uniq(S.tasks.map(fileKey))), API.files('Issue', S.tickets.map(function (t) { return t.id; }))]);
    }).then(function (res) {
      S.files = {}; (res[0] || []).forEach(function (f) { (S.files[f.attached_to_name] = S.files[f.attached_to_name] || []).push(f); });
      S.tfiles = {}; (res[1] || []).forEach(function (f) { (S.tfiles[f.attached_to_name] = S.tfiles[f.attached_to_name] || []).push(f); });
      if (!S.form) resetForm(); if (!S.tform) resetTForm();
      if (!S._landed) { S._landed = 1; if (!can('assign')) S.tab.task = 'my'; if (!mod('tasks')) S.mod = 'ticket'; }
      renderHeader(); render();
    }).catch(function (e) {
      q('#view').innerHTML = '<div class="card"><div class="cb empty"><b>Could not load data</b>' + esc(errMsg(e)) + '<br><br><button class="btn pri" data-act="refresh">Retry</button></div></div>';
    });
  }
  function buildPeople(users, emps) {
    var map = {}, list = [];
    emps.forEach(function (e) {
      var u = (e.user_id || '').trim();
      var p = { user: u, name: e.employee_name || u, emp: e.name, branch: e.branch || '', dept: String(e.department || '').replace(/\s*-\s*LSACPL$/i, ''), desig: e.designation || '', phone: e.cell_number || '', image: e.image || '', email: u || e.company_email || e.personal_email || '', login: !!u };
      list.push(p); if (u) map[u.toLowerCase()] = p;
    });
    users.forEach(function (u) {
      if (!u.name || u.name === 'Administrator' || u.name === 'Guest') return;
      var k = u.name.toLowerCase();
      if (map[k]) { if (!map[k].phone) map[k].phone = u.mobile_no || u.phone || ''; if (u.user_image) map[k].image = u.user_image; return; }
      var br = '', nu = norm(u.name.split('@')[0]);
      BRANCHES.forEach(function (b) { if (norm(b).length > 3 && nu.indexOf(norm(b)) === 0) br = b; });
      var p = { user: u.name, name: u.full_name || u.name, emp: '', branch: br, dept: br ? 'Branch Login' : '', desig: br ? 'Branch Login' : '', phone: u.mobile_no || u.phone || '', image: u.user_image || '', email: u.name, login: true, branchLogin: !!br };
      map[k] = p; list.push(p);
    });
    list.sort(function (a, b) { return a.name.localeCompare(b.name); });
    S.people = list; S.byUser = map;
  }
  function renderHeader() {
    var me = S.realMe;
    q('#me-name').textContent = me.name;
    q('#me-role').textContent = (me.desig || me.role) + (me.branch ? ' · ' + me.branch : '');
    var pic = q('#me-pic');
    pic.innerHTML = me.image ? '<img src="' + esc(me.image) + '" alt="">' : initials(me.name);
    var img = q('img', pic); if (img) img.onerror = function () { pic.textContent = initials(me.name); };
    var va = q('#viewas');
    var allowed = mod('viewas') && (me.admin || (me.perms || {}).viewas);
    va.style.display = allowed ? '' : 'none';
    if (allowed) va.innerHTML = '<option value="">👁 View as… (my own view)</option>' + S.people.filter(function (p) { return p.login && p.user !== me.user; }).map(function (p) { return '<option value="' + esc(p.user) + '" ' + (S.me.preview && S.me.user === p.user ? 'selected' : '') + '>' + esc(p.name + (p.branch ? ' · ' + p.branch : '')) + '</option>'; }).join('');
  }
  function setViewAs(u) {
    if (!u) { S.me = S.realMe; S.tab.task = 'assign'; }
    else { S.me = setMe(u); S.me.preview = true; S.tab.task = 'my'; S.tab.ticket = 'tmy'; }
    closeDrawer(); render();
  }

  /* ================================================================
     QUEUE  (custom_task_queue_no for single tasks, meta.mq for group tasks)
  ================================================================ */
  function queueOf(user, excludeId) {
    return S.tasks.filter(function (t) { return t.assignee === user && !isClosed(t) && t.id !== excludeId; })
      .sort(function (a, b) { return a.qk - b.qk || (PRI_W(a.pri) - PRI_W(b.pri)) || (a.created > b.created ? 1 : -1); });
  }
  function qRank(t) { if (isClosed(t)) return ''; var l = queueOf(t.assignee); for (var i = 0; i < l.length; i++) if (l[i].id === t.id) return i + 1; return ''; }
  function placement(user, pri, top, excl) {
    var l = queueOf(user, excl), w = PRI_W(pri);
    if (!l.length) return { rank: 1, qk: 1 };
    if (top) return { rank: 1, qk: l[0].qk - 1 };
    var idx = l.length;
    for (var i = 0; i < l.length; i++) { if (PRI_W(l[i].pri) > w) { idx = i; break; } }
    var qk = idx === 0 ? l[0].qk - 1 : idx === l.length ? l[l.length - 1].qk + 1 : (l[idx - 1].qk + l[idx].qk) / 2;
    return { rank: idx + 1, qk: qk };
  }
  function writeGroupMq(mid, changes) {
    return API.get('ToDo', mid).then(function (raw) {
      var b = base(raw); b.meta.mq = b.meta.mq || {};
      Object.keys(changes).forEach(function (u) { b.meta.mq[u] = changes[u]; });
      return API.save('ToDo', mid, { description: denormBase(b).description });
    }).catch(function () { });
  }
  function syncQueue(user) {
    if (!user) return Promise.resolve();
    var l = queueOf(user), jobs = [], grp = {};
    l.forEach(function (t, i) {
      t.qk = i + 1;
      if (t.mid) { if (t.mqs !== i + 1) { t.mqs = i + 1; (grp[t.mid] = grp[t.mid] || {})[user] = i + 1; } }
      else if (t.cq !== i + 1) { t.cq = i + 1; jobs.push([t.id, { custom_task_queue_no: i + 1, custom_queue_active: 1 }]); }
    });
    S.tasks.forEach(function (t) { if (!t.mid && t.assignee === user && isClosed(t) && t.cq) { t.cq = 0; jobs.push([t.id, { custom_task_queue_no: 0, custom_queue_active: 0 }]); } });
    var p = jobs.reduce(function (p, j) { return p.then(function () { return API.save('ToDo', j[0], j[1]).catch(function () { }); }); }, Promise.resolve());
    return Object.keys(grp).reduce(function (p, mid) { return p.then(function () { return writeGroupMq(mid, grp[mid]); }); }, p);
  }
  function setOrder(user, ids) {
    if (guard()) return Promise.resolve();
    ids.forEach(function (id, i) { var t = findTask(id); if (t) t.qk = i + 1; });
    return syncQueue(user).then(function () { render(); refreshOpen(); });
  }
  function nextTaskNo(offset) {
    var pre = 'T' + String(new Date().getFullYear()).slice(2) + pad(new Date().getMonth() + 1) + '-';
    var max = 0; S.tasks.forEach(function (t) { if (t.no && t.no.indexOf(pre) === 0) { var n = parseInt(t.no.slice(pre.length), 10); if (n > max) max = n; } });
    return pre + String(max + 1 + (offset || 0)).padStart(4, '0');
  }
  function dispNo(t) { return t.no || ('#' + String(t.mid || t.id).slice(-6).toUpperCase()); }

  /* ================================================================
     REPORT-DUE / DELAY
  ================================================================ */
  function myUpdates(t) { return t.grp && t.grp.response === 'individual' ? t.updates.filter(function (u) { return u.by === t.assignee; }) : t.updates; }
  function lastReport(t) { var l = myUpdates(t).filter(function (u) { return u.type === 'Report'; }); return l.length ? toDate(l[l.length - 1].at) : null; }
  function reportDue(t) {
    if (isClosed(t) || !t.report || t.status === 'Review Pending') return null;
    var r = t.report, now = new Date(), last = lastReport(t), start = toDate(t.start) || toDate(t.created);
    if (start && start > now) return null;
    var time = r.time || '19:00', today = todayStr(), at;
    if (r.type === 'EOD') { at = toDate(today + 'T' + time); if (!last || localStr(last).slice(0, 10) !== today) return { label: 'EOD report', at: at, late: now > at }; return null; }
    if (r.type === 'WEEKLY') { var wd = +r.day; if (now.getDay() === wd) { at = toDate(today + 'T' + time); if (!last || (now - last) > 20 * 3600000) return { label: 'Weekly report', at: at, late: now > at }; } else if (last && (now - last) > 8 * 86400000) return { label: 'Weekly report missed', at: null, late: true }; return null; }
    if (r.type === 'MONTHLY') { var dm = +r.dom || 1; if (now.getDate() === dm) { at = toDate(today + 'T' + time); if (!last || (now - last) > 20 * 3600000) return { label: 'Monthly report', at: at, late: now > at }; } else if (last && (now - last) > 32 * 86400000) return { label: 'Monthly report missed', at: null, late: true }; return null; }
    if (r.type === 'SPECIFIC') { at = toDate(r.dt); if (at && now >= new Date(at.getTime() - 3600000) && (!last || last < new Date(at.getTime() - 86400000))) return { label: 'Report ' + fDT(r.dt), at: at, late: now > at }; return null; }
    return null;
  }
  function repText(r) {
    if (!r || !r.type) return '—';
    if (r.type === 'EOD') return 'EOD by ' + (r.time || '19:00');
    if (r.type === 'WEEKLY') return 'Weekly ' + WEEKDAYS[+r.day || 0].slice(0, 3) + ' ' + (r.time || '19:00');
    if (r.type === 'MONTHLY') return 'Monthly d' + (r.dom || 1) + ' ' + (r.time || '19:00');
    if (r.type === 'SPECIFIC') return 'On ' + fDT(r.dt);
    return 'On completion';
  }
  function needsDelayRemark(t) {
    if (!mod('delayMandatory') || !isOverdue(t)) return false;
    var dd = toDate(t.due);
    var anyone = t.grp && t.grp.response === 'group';
    return !t.updates.some(function (u) { return u.type === 'Delay Remark' && (anyone || u.by === t.assignee) && toDate(u.at) >= dd; });
  }

  /* ================================================================
     VISIBILITY (role data scope)
  ================================================================ */
  function involved(t, me) { return t.assignee === me || t.by === me || t.owner === me || t.cc.indexOf(me) > -1 || (t.grp && t.grp.members.indexOf(me) > -1); }
  function visible() {
    var sc = scope(), me = S.me.user;
    if (sc === 'all') return S.tasks;
    return S.tasks.filter(function (t) {
      if (involved(t, me)) return true;
      if (sc === 'dept') return S.me.dept && S.me.dept !== 'Branch Login' && t.dept === S.me.dept;
      if (sc === 'branch') return S.me.branch && t.branch === S.me.branch;
      return false;
    });
  }
  function tVisible() {
    if (can('t_all')) return S.tickets;
    var me = S.me.user;
    return S.tickets.filter(function (t) { return t.raiser === me || t.owner === me || t.tag === me || t.cc.indexOf(me) > -1; });
  }

  /* ================================================================
     RENDER ROOT
  ================================================================ */
  function taskTabs() {
    var t = [];
    if (can('assign')) t.push(['assign', '✚ Assign Task']);
    if (can('all_tab')) t.push(['all', '📋 All Tasks']);
    t.push(['my', '👤 My Tasks']);
    if (mod('team') && can('team')) t.push(['team', '👥 Team & Contacts']);
    if (mod('reports') && can('reports')) t.push(['reports', '📊 Reports']);
    if (S.me.admin && !S.me.preview) t.push(['cpanel', '⚙ Control Panel']);
    return t;
  }
  function ticketTabs() { var t = []; if (can('t_raise')) t.push(['traise', '✚ Raise Ticket']); t.push(['tall', '🎫 All Tickets']); t.push(['tmy', '👤 My Tickets']); return t; }
  function render() {
    var b = '';
    if (!S.live) b += '<div class="ban demo"><b>DEMO MODE</b> — opened outside the portal or not logged in, showing sample data. <button class="btn sm" data-act="demo-reset">Reset demo</button></div>';
    if (S.me.preview) b += '<div class="ban prev">👁 <b>Preview:</b> exactly what <b>' + esc(S.me.name) + '</b> (' + esc(S.me.role) + ') sees. Buttons are blocked. <button class="btn sm" data-act="exit-preview">Back to my view</button>' + hb('viewas') + '</div>';
    q('#banners').innerHTML = b;
    var mods = [];
    if (mod('tasks')) mods.push('task'); if (mod('tickets')) mods.push('ticket');
    if (S.me.admin && !S.me.preview && mods.indexOf('task') < 0) mods.unshift('task');
    if (mods.indexOf(S.mod) < 0) S.mod = mods[0] || 'task';
    qa('#modsw button').forEach(function (x) { x.style.display = mods.indexOf(x.dataset.mod) > -1 ? '' : 'none'; x.classList.toggle('on', x.dataset.mod === S.mod); });
    q('#h-title').textContent = S.mod === 'task' ? 'TASK MANAGEMENT PRO' : 'TICKET / HELPDESK';
    var vt = visible(), vk = tVisible();
    q('#mc-task').textContent = vt.filter(function (t) { return isOverdue(t); }).length || vt.filter(function (t) { return !isClosed(t); }).length;
    q('#mc-ticket').textContent = vk.filter(tkActive).length;
    var tabs = S.mod === 'task' ? taskTabs() : ticketTabs(), keys = tabs.map(function (t) { return t[0]; });
    if (keys.indexOf(S.tab[S.mod]) < 0) S.tab[S.mod] = keys[0];
    var cur = S.tab[S.mod];
    var counts = { all: vt.filter(function (t) { return !isClosed(t); }).length, my: queueOf(S.me.user).length, team: S.people.length, tall: vk.filter(tkActive).length, tmy: vk.filter(function (t) { return (t.tag === S.me.user && tkActive(t)) || (t.raiser === S.me.user && t.status === 'Resolved'); }).length };
    q('#tabs').innerHTML = tabs.map(function (t) { return '<button class="tab ' + (cur === t[0] ? 'on' : '') + '" data-tab="' + t[0] + '">' + t[1] + (counts[t[0]] != null ? ' <span class="cnt">' + counts[t[0]] + '</span>' : '') + '</button>'; }).join('') +
      hb({ assign: 'a_who', all: 'all', my: 'my', team: 'team', reports: 'reports', cpanel: 'cpanel', traise: 't_raise', tall: 't_all', tmy: 't_my' }[cur]);
    if (S.mod === 'task') {
      if (cur === 'cpanel') { q('#kpis').innerHTML = ''; renderCPanel(); return; }
      renderKpis(vt);
      if (cur === 'assign') renderAssign(); else if (cur === 'all') renderAll(); else if (cur === 'my') renderMy(); else if (cur === 'team') renderTeam(); else renderReports();
    } else {
      renderTKpis(vk);
      if (cur === 'traise') renderRaise(); else if (cur === 'tall') renderTAll(); else renderTMy();
    }
  }
  function kpiHtml(k) { return k.map(function (x) { return '<div class="kpi ' + x[3] + '" data-kpi="' + x[4] + '"><div class="kv">' + x[1] + '</div><div class="kl"><div class="kh">' + x[0] + '</div><div class="ks">' + x[2] + '</div></div></div>'; }).join(''); }
  function renderKpis(v) {
    var open = v.filter(function (t) { return !isClosed(t); }), d30 = Date.now() - 30 * 86400000;
    var done30 = v.filter(function (t) { return t.status === 'Completed' && toDate(t.completedOn) && toDate(t.completedOn).getTime() > d30; });
    var ontime = done30.filter(function (t) { var c = toDate(t.completedOn), d = toDate(t.due); return c && d && c <= d; }).length;
    q('#kpis').innerHTML = kpiHtml([
      ['Open', open.length, 'All active', '', 'Active'], ['In Progress', v.filter(function (t) { return t.status === 'In Progress'; }).length, 'Being worked', 'amb', 'In Progress'],
      ['Review Pending', v.filter(function (t) { return t.status === 'Review Pending'; }).length, 'Awaiting approval', 'pur', 'Review Pending'], ['Due Today', v.filter(dueToday).length, 'Deadline today', 'org', 'DueToday'],
      ['Overdue', v.filter(function (t) { return isOverdue(t); }).length, 'Past deadline', 'red', 'Overdue'], ['P1 + P2', open.filter(function (t) { return t.pri === 'VVIMP' || t.pri === 'IMP'; }).length, PRI_L('VVIMP') + ' / ' + PRI_L('IMP'), 'red', 'Critical'],
      ['Reports Due', v.filter(function (t) { return reportDue(t); }).length, 'EOD/Weekly/Monthly', 'blue', 'Reports'], ['On-Time %', done30.length ? Math.round(ontime * 100 / done30.length) + '%' : '—', done30.length + ' closed / 30d', 'teal', 'Completed']
    ]);
  }
  function renderTKpis(v) {
    var me = S.me.user;
    q('#kpis').innerHTML = kpiHtml([
      ['Open', v.filter(function (t) { return t.status === 'Open'; }).length, 'New / in work', '', 'Open'], ['Reopened', v.filter(function (t) { return t.status === 'Reopened'; }).length, 'Not satisfied', 'org', 'Reopened'],
      ['On Hold', v.filter(function (t) { return t.status === 'On Hold'; }).length, 'Paused', 'amb', 'On Hold'], ['Resolved', v.filter(function (t) { return t.status === 'Resolved'; }).length, 'Awaiting close', 'pur', 'Resolved'],
      ['SLA Breached', v.filter(tkBreach).length, 'High ' + SLA('High') + 'h · Med ' + SLA('Medium') + 'h', 'red', 'Breach'], ['High Open', v.filter(function (t) { return tkActive(t) && t.pri === 'High'; }).length, 'Urgent', 'red', 'HighOpen'],
      ['Tagged to Me', v.filter(function (t) { return t.tag === me && tkActive(t); }).length, 'I must resolve', 'blue', 'Mine'], ['Closed', v.filter(tkClosed).length, 'Completed', 'teal', 'Closed']
    ]);
  }

  /* ================================================================
     ASSIGN TAB
  ================================================================ */
  function resetForm() {
    var due = new Date(Date.now() + 86400000); due.setHours(18, 0, 0, 0);
    S.form = { mode: 'emp', sel: [], selBranches: [], selDepts: [], selDesigs: [], narrowBranch: '', cat: '', title: '', details: '', start: nowLocal(), due: localStr(due), pri: '', top: false, report: { type: '', time: '19:00', day: 6, dom: 1, dt: '' }, cc: [], email: true, wa: true, checklist: '', asGroup: false, response: 'group', leader: '' };
    S.pendingFiles = [];
  }
  function groupKey() { return S.form.mode === 'branch' ? 'branch' : S.form.mode === 'dept' ? 'dept' : 'desig'; }
  function groupSel() { var f = S.form; return f.mode === 'branch' ? f.selBranches : f.mode === 'dept' ? f.selDepts : f.selDesigs; }
  function peopleForMode() { var f = S.form, k = groupKey(), sel = groupSel(); if (f.mode === 'emp') return []; return S.people.filter(function (p) { return sel.indexOf(p[k]) > -1 && (f.mode === 'branch' || !f.narrowBranch || p.branch === f.narrowBranch); }); }
  function distinct(key) { return uniq(S.people.map(function (p) { return p[key]; })).sort(); }
  function allBranches() { return uniq(BRANCHES.concat(distinct('branch'))); }
  function prow(p, checked, withBox) {
    return '<label class="prow ' + (p.login ? '' : 'dis') + '">' + (withBox ? '<input type="checkbox" data-pu="' + esc(p.user) + '" ' + (checked ? 'checked' : '') + ' ' + (p.login ? '' : 'disabled') + '>' : '') +
      '<div class="av">' + initials(p.name) + '</div><div class="pi"><div class="pn">' + esc(p.name) + '</div><div class="pm">' + esc([p.desig, p.dept, p.branch].filter(Boolean).join(' · ')) + '</div></div>' +
      phHtml(p, true) + (p.branchLogin ? '<span class="tag b">Branch</span>' : '') + (p.login ? '<span class="tag">' + queueOf(p.user).length + ' open</span>' : '<span class="tag r">No login</span>') + '</label>';
  }
  function renderAssign() {
    var f = S.form, rep = f.report, multi = f.sel.length > 1, groupOK = mod('group') && can('group');
    if (!multi || !groupOK) f.asGroup = false;
    if (f.asGroup && f.sel.indexOf(f.leader) < 0) f.leader = f.sel[0];
    var modes = [['emp', '👤 Employee(s)'], ['branch', '🏢 Branch'], ['dept', '🗂 Dept'], ['desig', '🎖 Designation']].map(function (m) { return '<button data-mode="' + m[0] + '" class="' + (f.mode === m[0] ? 'on' : '') + '">' + m[1] + '</button>'; }).join('');
    var target = '';
    if (f.mode === 'emp') target = '<div class="picker"><input id="f-emp" placeholder="Type name, branch, department or designation…" autocomplete="off"><div class="pres" id="f-emp-res"></div></div>';
    else {
      var src = f.mode === 'branch' ? allBranches() : distinct(groupKey()), chosen = groupSel(), k = groupKey();
      target = '<div class="chips">' + src.map(function (s) { var n = S.people.filter(function (p) { return p[k] === s; }).length; return '<span class="chip ' + (chosen.indexOf(s) > -1 ? 'on' : '') + '" data-grp="' + esc(s) + '">' + esc(s) + ' <small>' + n + '</small></span>'; }).join('') + '</div>';
      if (chosen.length) {
        var pl = peopleForMode();
        target += '<div class="row" style="margin-top:6px">' + (f.mode !== 'branch' ? '<select id="f-narrow" style="width:160px;height:31px;padding:2px 8px;font-size:12px">' + optList(allBranches(), f.narrowBranch, 'All branches') + '</select>' : '') + '<button class="btn sm" data-act="sel-all">All with login</button>' + (f.mode === 'branch' ? '<button class="btn sm" data-act="sel-blogin">Branch login only</button>' : '') + '<button class="btn sm" data-act="sel-mgr">Managers only</button><button class="btn sm" data-act="sel-none">Clear</button><span class="hint">' + pl.filter(function (p) { return p.login; }).length + '/' + pl.length + ' have login</span></div>';
        target += '<div class="plist">' + (pl.length ? pl.map(function (p) { return prow(p, p.login && f.sel.indexOf(p.user) > -1, true); }).join('') : '<div class="empty">No people</div>') + '</div>';
      }
    }
    var groupUI = '';
    if (multi && groupOK) {
      groupUI = '<div class="sub" style="margin-top:10px">Assign as ' + hb('a_mode') + '</div><div class="seg fit" id="f-asg"><button data-asg="ind" class="' + (!f.asGroup ? 'on' : '') + '">👤 Individual tasks (' + f.sel.length + ')</button><button data-asg="grp" class="' + (f.asGroup ? 'on' : '') + '">👥 One group task</button></div>';
      if (f.asGroup) groupUI += '<div class="grid g2" style="margin-top:8px"><div class="fld"><label class="lbl">Task response</label><div class="seg fit" id="f-resp"><button data-resp="group" class="' + (f.response === 'group' ? 'on' : '') + '">Group</button><button data-resp="individual" class="' + (f.response === 'individual' ? 'on' : '') + '">Individual</button></div></div><div class="fld"><label class="lbl">Group leader</label><select id="f-leader">' + f.sel.map(function (u) { return '<option value="' + esc(u) + '" ' + (f.leader === u ? 'selected' : '') + '>' + esc(personName(u)) + '</option>'; }).join('') + '</select></div></div><div class="hint">' + (f.response === 'group' ? 'Group response: one shared status — any member’s Done completes it for all.' : 'Individual response: each member reports &amp; completes own part; all see everyone’s updates.') + '</div>';
    }
    var repX = '', rts = reportTypes();
    if (rep.type === 'EOD') repX = '<div class="fld"><label class="lbl">Report by</label><input type="time" id="f-rtime" value="' + esc(rep.time) + '"></div>';
    if (rep.type === 'WEEKLY') repX = '<div class="fld"><label class="lbl">Weekday</label><select id="f-rday">' + WEEKDAYS.map(function (d, i) { return '<option value="' + i + '" ' + (+rep.day === i ? 'selected' : '') + '>' + d + '</option>'; }).join('') + '</select></div><div class="fld"><label class="lbl">Time</label><input type="time" id="f-rtime" value="' + esc(rep.time) + '"></div>';
    if (rep.type === 'MONTHLY') repX = '<div class="fld"><label class="lbl">Date of month</label><select id="f-rdom">' + Array.apply(null, Array(28)).map(function (x, i) { return '<option ' + (+rep.dom === i + 1 ? 'selected' : '') + '>' + (i + 1) + '</option>'; }).join('') + '</select></div><div class="fld"><label class="lbl">Time</label><input type="time" id="f-rtime" value="' + esc(rep.time) + '"></div>';
    if (rep.type === 'SPECIFIC') repX = '<div class="fld" style="grid-column:span 2"><label class="lbl">Report date &amp; time</label><input type="datetime-local" id="f-rdt" value="' + esc(rep.dt) + '" min="' + nowLocal() + '"></div>';
    var req = mod('repMandatory') ? ' <span class="req" style="color:#ffd2d2">*</span>' : '';

    q('#view').innerHTML = '<div class="asg">' +
      '<div><div class="card"><div class="ch">① Assign to <span class="req" style="color:#ffd2d2">*</span><span class="sp">' + hb('a_who') + '</span></div><div class="cb">' +
      '<div class="minfo"><div><span>Assigned by</span><b>' + esc(S.me.name) + '</b></div><div><span>Assigned on (auto)</span><b id="f-clock">' + fDT(nowLocal()) + '</b></div><div><span>Task no. (auto)</span><b>' + esc(nextTaskNo()) + (multi && !f.asGroup ? ' +' + (f.sel.length - 1) : '') + '</b></div></div>' +
      '<div class="seg fit">' + modes + '</div><div style="margin-top:8px">' + target + '</div>' +
      '<div class="sub" style="margin-top:8px">Selected (' + f.sel.length + ')</div><div class="chips selbox">' + (f.sel.map(function (u) { return '<span class="chip sel">' + (f.asGroup && u === f.leader ? '⭐ ' : '') + esc(personName(u)) + ' <span class="x" data-unsel="' + esc(u) + '">×</span></span>'; }).join('') || '<span class="hint">Nobody selected yet</span>') + '</div>' + groupUI +
      '</div></div>' +
      '<div class="card"><div class="ch">③ Priority &amp; queue <span class="req" style="color:#ffd2d2">*</span><span class="sp">' + hb('a_pri') + '</span></div><div class="cb">' +
      '<div class="pg" id="f-pri">' + PRI_KEYS.map(function (k) { return '<button class="pb ' + (f.pri === k ? 'on' : '') + '" data-p="' + k + '"><span class="pn-num">' + PRI_N(k) + '</span>' + esc(PRI_L(k)) + '<small>' + esc(PRI_H(k)) + '</small></button>'; }).join('') + '</div>' +
      '<label class="tg" style="margin-top:9px"><input type="checkbox" id="f-top" ' + (f.top ? 'checked' : '') + '> Force to queue #1 for every assignee</label></div></div></div>' +
      '<div><div class="card"><div class="ch">② Task details<span class="sp">' + hb('a_what') + '</span></div><div class="cb">' +
      '<div class="grid" style="grid-template-columns:1fr 2fr"><div class="fld"><label class="lbl">Category <span class="req">*</span></label><select id="f-cat">' + optList(categories(), f.cat, 'Select') + '</select></div><div class="fld"><label class="lbl">Title <span class="req">*</span> (max 80)</label><input id="f-title" maxlength="80" value="' + esc(f.title) + '" placeholder="e.g. Update all October walk-ins in ERP"></div></div>' +
      '<div class="grid g2" style="margin-top:9px"><div class="fld"><label class="lbl">Start <span class="req">*</span></label><input type="datetime-local" id="f-start" value="' + esc(f.start) + '"></div><div class="fld"><label class="lbl">Due <span class="req">*</span> <span id="f-dur" class="grn"></span></label><input type="datetime-local" id="f-due" value="' + esc(f.due) + '" min="' + nowLocal() + '"></div></div>' +
      '<div class="fld" style="margin-top:9px"><label class="lbl">Details <span class="req">*</span> <span id="f-wc" style="float:right">0 / 150 words</span></label><textarea id="f-details" placeholder="What exactly must be done, expected standard, who to coordinate with…">' + esc(f.details) + '</textarea></div>' +
      (mod('checklist') ? '<details class="ck-d" ' + (f.checklist ? 'open' : '') + '><summary>＋ Checklist / sub-steps (optional)</summary><textarea id="f-check" style="min-height:56px" placeholder="One step per line">' + esc(f.checklist) + '</textarea></details>' : '') +
      '</div></div>' +
      '<div class="card"><div class="ch">④ Reporting rule' + req + '<span class="sp">' + hb('a_rep') + '</span></div><div class="cb">' +
      '<div class="seg" id="f-rep">' + rts.map(function (r) { return '<button data-r="' + r.k + '" class="' + (rep.type === r.k ? 'on' : '') + '" title="' + esc(r.d) + '">' + esc(r.label) + '</button>'; }).join('') + '</div>' +
      (repX ? '<div class="grid g3" style="margin-top:9px">' + repX + '</div>' : '<div class="hint">' + (rep.type ? esc(REP(rep.type).d) : (mod('repMandatory') ? 'Mandatory — choose how the assignee must report.' : 'Optional.')) + '</div>') +
      '</div></div>' +
      '<div class="card"><div class="ch">⑤ CC, notify &amp; files<span class="sp">' + hb('a_notify') + '</span></div><div class="cb">' +
      '<div class="picker"><input id="f-cc" placeholder="CC — once done / updates go to… (type name)" autocomplete="off"><div class="pres" id="f-cc-res"></div></div>' +
      '<div class="chips" style="margin-top:5px">' + f.cc.map(function (u) { return '<span class="chip sel">' + esc(personName(u)) + ' <span class="x" data-uncc="' + esc(u) + '">×</span></span>'; }).join('') + '<span class="chip sel" style="opacity:.7">' + esc(S.me.name) + ' (you)</span></div>' +
      '<div class="row" style="margin-top:9px;gap:16px">' + (mod('email') ? '<label class="tg"><input type="checkbox" id="f-email" ' + (f.email ? 'checked' : '') + '> ✉️ Email</label>' : '') + (mod('wa') ? '<label class="tg"><input type="checkbox" id="f-wa" ' + (f.wa ? 'checked' : '') + '> 🟢 WhatsApp</label>' : '') + '<span class="tg">🔔 ERP <span class="tag g">always</span></span></div>' +
      '<div class="drop" id="f-drop" style="margin-top:9px">📎 Click or drop files (max 5 MB each)</div><div class="chips" id="f-flist" style="margin-top:5px">' + fileChips() + '</div>' +
      '</div></div></div>' +
      '<div class="side"><div class="card"><div class="ch">Assignment preview<span class="sp">' + hb('a_prev') + '</span></div><div class="cb" id="f-preview"></div></div>' +
      (mod('recent') ? '<div class="card"><div class="ch lt">🕘 Recent assigned (last 5)<span class="sp">' + hb('a_recent') + '</span></div><div class="cb" id="f-recent">' + recentHtml() + '</div></div>' : '') +
      '</div></div>';
    updateDur(); updateWc(); renderPreview(); startClock();
  }
  function recentHtml() {
    var me = S.me.user, seen = {}, l = S.tasks.filter(function (t) { return t.by === me || t.owner === me; }).sort(function (a, b) { return (b.created || '') > (a.created || '') ? 1 : -1; }).filter(function (t) { var k = t.mid || t.id; if (seen[k]) return false; seen[k] = 1; return true; }).slice(0, 5);
    if (!l.length) return '<div class="hint">You have not assigned any task yet.</div>';
    return l.map(function (t) {
      var who = t.grp ? '👥 ' + t.grp.members.length + ' members' : personName(t.assignee);
      return '<div class="qi" style="padding:6px 0;cursor:pointer" data-open="' + esc(t.id) + '"><div class="pi"><div class="tl1" style="max-width:none">' + esc(dispNo(t)) + ' — ' + esc(t.title) + '</div><div class="pm">' + esc(who) + ' · ' + fDT(t.created) + '</div></div>' + priPill(t.pri) + '<span class="pill ' + (ST_CLS[t.status] || 's-open') + '">' + esc(t.status) + '</span></div>';
    }).join('');
  }
  function fileChips() { return S.pendingFiles.map(function (fl, i) { return '<span class="chip sel">📄 ' + esc(fl.name) + ' <small>' + fsize(fl.size) + '</small> <span class="x" data-unfile="' + i + '">×</span></span>'; }).join(''); }
  function startClock() { clearInterval(clockTimer); clockTimer = setInterval(function () { var c = q('#f-clock'); if (!c) { clearInterval(clockTimer); return; } c.textContent = fDT(nowLocal()); }, 15000); }
  function updateDur() { var s = toDate(S.form.start), d = toDate(S.form.due), el = q('#f-dur'); if (!el) return; if (s && d) { el.textContent = d <= s ? '⚠ before start' : '· ' + dur(d - s); el.className = d <= s ? 'red' : 'grn'; } else el.textContent = ''; }
  function updateWc() { var n = words(S.form.details), el = q('#f-wc'); if (el) { el.textContent = n + ' / 150 words'; el.className = n > 150 ? 'red' : 'mut'; } }
  function renderPreview() {
    var f = S.form, el = q('#f-preview'); if (!el) return;
    var h = '';
    if (!f.sel.length) h += '<div class="empty" style="padding:14px"><b>No assignee yet</b>Select people to see their queue and new task number.</div>';
    else {
      h += '<div class="sub">' + (f.asGroup ? '👥 Group task · ' + (f.response === 'group' ? 'group response' : 'individual response') : 'Assignees · queue position') + '</div>';
      f.sel.slice(0, 50).forEach(function (u, i) {
        var p = person(u) || { name: u }, l = queueOf(u), od = l.filter(function (t) { return isOverdue(t); }).length, pl = f.pri ? placement(u, f.pri, f.top) : null;
        h += '<div class="sc"><div class="av">' + initials(p.name) + '</div><div class="pi"><div class="pn">' + (f.asGroup && u === f.leader ? '⭐ ' : '') + esc(p.name) + '</div><div class="pm">' + esc([p.desig, p.branch].filter(Boolean).join(' · ')) + '</div><div class="row" style="gap:4px;margin-top:2px;flex-wrap:nowrap">' + phHtml(p, true) + '<span class="tag">Open ' + l.length + '</span>' + (od ? '<span class="tag r">OD ' + od + '</span>' : '') + '</div></div><div class="qb"><div class="tno">' + (f.asGroup ? nextTaskNo(0) : nextTaskNo(i)) + '</div>' + (pl ? '<span class="qn ' + (pl.rank === 1 ? 'q1' : '') + '" style="margin-top:3px">#' + pl.rank + '</span>' : '<span class="tag">pick priority</span>') + '</div></div>';
      });
      if (f.sel.length > 50) h += '<div class="hint">+ ' + (f.sel.length - 50) + ' more…</div>';
    }
    var miss = function (v, txt) { return v ? txt : '<span class="red">Missing</span>'; };
    h += '<div class="sub">Summary</div>' +
      '<div class="sr"><span>Category</span><span>' + miss(f.cat, esc(f.cat)) + '</span></div><div class="sr"><span>Title</span><span>' + miss(f.title.trim(), esc(f.title)) + '</span></div>' +
      '<div class="sr"><span>Priority</span><span>' + miss(f.pri, f.pri && priPill(f.pri)) + '</span></div><div class="sr"><span>Due</span><span>' + fDT(f.due) + '</span></div>' +
      '<div class="sr"><span>Reporting</span><span>' + (mod('repMandatory') ? miss(f.report.type, esc(repText(f.report))) : esc(repText(f.report))) + '</span></div>' +
      '<div class="sr"><span>Type</span><span>' + (f.asGroup ? '👥 Group (' + f.sel.length + ')' : f.sel.length > 1 ? f.sel.length + ' individual tasks' : 'Single task') + '</span></div>' +
      '<div class="sr"><span>Notify</span><span>ERP' + (f.email && mod('email') ? ' · Email' : '') + (f.wa && mod('wa') ? ' · WhatsApp' : '') + '</span></div>' +
      '<div class="row" style="margin-top:10px;flex-wrap:nowrap"><button class="btn pri lg" data-act="assign" style="flex:1;justify-content:center">✓ Assign ' + (f.asGroup ? 'Group Task' : 'Task' + (f.sel.length > 1 ? ' to ' + f.sel.length : '')) + '</button><button class="btn" data-act="form-reset">Clear</button></div>';
    el.innerHTML = h;
  }
  function pickerResults(inputId, resId, exclude, onPick) {
    var inp = q('#' + inputId), box = q('#' + resId); if (!inp || !box) return;
    var s = inp.value.trim().toLowerCase(); if (!s) { box.classList.remove('show'); return; }
    var m = S.people.filter(function (p) { return p.login && exclude.indexOf(p.user) < 0 && (p.name + ' ' + p.user + ' ' + p.branch + ' ' + p.dept + ' ' + p.desig + ' ' + (phonesOpen() ? digits(p.phone) : '')).toLowerCase().indexOf(s) > -1; }).slice(0, 14);
    box.innerHTML = m.length ? m.map(function (p) { return '<div data-pick="' + esc(p.user) + '">' + prow(p, false, false) + '</div>'; }).join('') : '<div class="prow dis">No matching employee with ERP login</div>';
    box.classList.add('show');
    qa('[data-pick]', box).forEach(function (r) { r.addEventListener('mousedown', function (e) { e.preventDefault(); onPick(r.dataset.pick); inp.value = ''; box.classList.remove('show'); }); });
  }
  function validateForm() {
    var f = S.form, e = [];
    if (!f.sel.length) e.push('Select at least one assignee');
    if (!f.cat) e.push('Select category'); if (!f.title.trim()) e.push('Enter task title'); if (!f.details.trim()) e.push('Enter task details');
    if (words(f.details) > 150) e.push('Details exceed 150 words'); if (!f.pri) e.push('Select priority');
    var s = toDate(f.start), d = toDate(f.due);
    if (!d) e.push('Select due date-time'); else if (d < new Date()) e.push('Due date-time cannot be in the past');
    if (s && d && d <= s) e.push('Due must be after start');
    if (mod('repMandatory') && !f.report.type) e.push('Choose reporting rule');
    if (f.report.type === 'SPECIFIC' && !f.report.dt) e.push('Pick report date & time');
    return e;
  }
  function confirmAssign() {
    if (guard()) return;
    var errs = validateForm();
    if (errs.length) { modal('⚠ Please complete the form', '<ul style="margin:0;padding-left:18px">' + errs.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>', [['OK', 'pri', closeModal]]); return; }
    var f = S.form;
    modal('Confirm assignment', '<div class="bn g">' + (f.asGroup ? '👥 One <b>group task</b> for <b>' + f.sel.length + '</b> members (leader: ' + esc(personName(f.leader)) + ', ' + f.response + ' response)' : 'Assigning <b>' + esc(f.title) + '</b> to <b>' + f.sel.length + '</b> ' + (f.sel.length > 1 ? 'people (separate tasks)' : 'person')) + '.</div>' +
      '<div class="sr"><span>Priority</span><span>' + priPill(f.pri) + (f.top ? ' · forced #1' : '') + '</span></div><div class="sr"><span>Due</span><span>' + fDT(f.due) + '</span></div><div class="sr"><span>Reporting</span><span>' + esc(repText(f.report)) + '</span></div><div class="sr"><span>Attachments</span><span>' + S.pendingFiles.length + '</span></div>',
      [['Back', '', closeModal], ['✓ Confirm &amp; Assign', 'pri', doAssign]]);
  }
  function newBase(f, u, extra) {
    var p = person(u) || {}, now = nowLocal();
    var checklist = mod('checklist') ? f.checklist.split('\n').map(function (x) { return x.trim(); }).filter(Boolean).map(function (x) { return { t: x, d: false }; }) : [];
    var b = { meta: {}, no: nextTaskNo(0), title: f.title.trim(), details: f.details.trim(), cat: f.cat, pri: f.pri, status: 'Open', assignee: u, by: S.me.user, created: now, start: f.start, due: f.due, cc: f.cc.slice(), report: clone(f.report), notify: { email: f.email, wa: f.wa }, checklist: checklist, progress: 0, updates: [], delays: [], completedOn: '', target: { type: f.mode === 'emp' ? 'Employee' : f.mode === 'branch' ? 'Branch' : f.mode === 'dept' ? 'Department' : 'Designation', values: f.mode === 'emp' ? [] : groupSel().slice() }, qk: 1, branch: p.branch || '', dept: p.dept || '', desig: p.desig || '', grp: null };
    Object.keys(extra || {}).forEach(function (k) { b[k] = extra[k]; });
    return b;
  }
  function doAssign() {
    var f = S.form, created = [], wantEmail = f.email && mod('email'), wantWa = f.wa && mod('wa');
    modalBusy(f.asGroup ? 'Creating group task…' : 'Assigning tasks…');
    var chain = Promise.resolve(), files = S.pendingFiles.slice();
    var upload = function (name) { return files.reduce(function (pp, fl) { return pp.then(function () { return API.upload('ToDo', name, fl).then(function (r) { (S.files[name] = S.files[name] || []).push(r); }).catch(function (e) { toast(String(e), 1); }); }); }, Promise.resolve()); };
    if (f.asGroup) {
      var members = f.sel.slice(), leader = f.leader || members[0], mq = {};
      members.forEach(function (u) { mq[u] = placement(u, f.pri, f.top).qk; });
      var b = newBase(f, leader, {});
      b.grp = { id: uid('G'), members: members, leader: leader, response: f.response, mirrors: {} };
      b.meta = { mq: mq, mstate: {} };
      b.updates = [{ id: uid(), at: nowLocal(), by: S.me.user, type: 'System', text: '👥 Group task assigned to ' + members.length + ' members · ' + PRI_N(f.pri) + ' ' + PRI_L(f.pri) + ' · ' + f.response + ' response · Reporting: ' + repText(f.report) }];
      var doc = denormBase(b); doc.doctype = 'ToDo'; doc.allocated_to = leader; doc.assigned_by = S.me.user;
      var masterName, shareFail = 0;
      chain = API.create(doc).then(function (d) {
        masterName = d.name;
        return members.filter(function (u) { return u !== leader; }).reduce(function (p, u) {
          return p.then(function () { return API.create(mirrorDoc(masterName, b, u)).then(function (md) { b.grp.mirrors[u] = md.name; }); })
            .then(function () { return API.share('ToDo', masterName, u, true).catch(function () { shareFail++; }); });
        }, Promise.resolve());
      }).then(function () { return API.save('ToDo', masterName, { description: denormBase(b).description }); })
        .then(function () { return upload(masterName); })
        .then(function () { return API.get('ToDo', masterName); })
        .then(function (raw) { var vs = explode(base(raw)); S.tasks = vs.concat(S.tasks); created = vs; if (shareFail) toast(shareFail + ' member(s) could not be given access — check ERP sharing', 1); return members.reduce(function (p, u) { return p.then(function () { return syncQueue(u); }); }, Promise.resolve()); });
    } else {
      f.sel.forEach(function (u) {
        chain = chain.then(function () {
          var pl = placement(u, f.pri, f.top), b = newBase(f, u, { qk: pl.qk });
          b.updates = [{ id: uid(), at: nowLocal(), by: S.me.user, type: 'System', text: 'Task assigned · ' + PRI_N(f.pri) + ' ' + PRI_L(f.pri) + ' · Queue #' + pl.rank + ' · Reporting: ' + repText(f.report) }];
          var doc = denormBase(b); doc.doctype = 'ToDo'; doc.allocated_to = u; doc.assigned_by = S.me.user;
          return API.create(doc).then(function (d) { b.id = d.name; b.owner = S.me.user; b.raw = d; b.cq = 0; enrich(b); S.tasks.unshift(b); created.push(b); return upload(d.name); }).then(function () { return syncQueue(u); });
        });
      });
    }
    chain.then(function () { return wantEmail ? sendEmails(created, 'new') : null; }).then(function () {
      resetForm(); render(); showDispatch(created, wantWa, 'new');
    }).catch(function (e) { closeModal(); toast('Failed: ' + errMsg(e), 1); render(); });
  }
  function taskMsg(t, kind) {
    var head = kind === 'reminder' ? '⏰ *LIFE Clinics — Task Reminder*' : '📌 *LIFE Clinics — New ' + (t.grp ? 'Group ' : '') + 'Task Assigned*';
    return head + '\n\nDear ' + personName(t.assignee) + ',\n\n*Task No:* ' + dispNo(t) + '   |   *Your Queue:* #' + (qRank(t) || '-') + (t.grp ? '\n*Group:* ' + t.grp.members.length + ' members (' + t.grp.response + ' response)' : '') +
      '\n*Priority:* ' + PRI_N(t.pri) + ' ' + PRI_L(t.pri) + '\n*Category:* ' + t.cat + '\n*Title:* ' + t.title + '\n\n' + t.details.slice(0, 600) +
      '\n\n*Assigned by:* ' + personName(t.by) + '\n*Assigned on:* ' + fDT(t.created) + '\n*Due:* ' + fDT(t.due) + '\n*Reporting:* ' + repText(t.report) +
      '\n\nOpen & update: ' + location.origin + location.pathname + '\n— LIFE Task Management';
  }
  function mailHtml(title, text) { return '<div style="font-family:Arial,sans-serif;font-size:14px;color:#1d2a23"><div style="background:#14532d;color:#fff;padding:12px 16px;border-radius:8px 8px 0 0;font-size:16px;font-weight:bold">LIFE Clinics — ' + esc(title) + '</div><div style="border:1px solid #d5e6db;border-top:0;padding:16px;border-radius:0 0 8px 8px">' + esc(text).replace(/\*/g, '').replace(/\n/g, '<br>') + '</div></div>'; }
  function sendEmails(list, kind) {
    return list.reduce(function (p, t) { return p.then(function () { return API.email([t.assignee], t.cc, '[' + PRI_N(t.pri) + ' ' + PRI_L(t.pri) + '] ' + dispNo(t) + ' — ' + t.title, mailHtml(kind === 'reminder' ? 'Task Reminder' : 'New Task Assigned', taskMsg(t, kind)), 'ToDo', fileKey(t)).catch(function (e) { toast('Email not sent to ' + personName(t.assignee) + ': ' + errMsg(e), 1); }); }); }, Promise.resolve());
  }
  function waRow(u, msg, sub) {
    var p = person(u) || {}, ph = phone91(p.phone);
    return '<div class="sc"><div class="av">' + initials(personName(u)) + '</div><div class="pi"><div class="pn">' + esc(personName(u)) + '</div><div class="pm">' + esc(sub || '') + '</div></div>' + phHtml(p, true) +
      (ph ? '<a class="btn wa sm" target="_blank" href="https://wa.me/' + ph + '?text=' + encodeURIComponent(msg) + '">WhatsApp</a>' : '<button class="btn sm" data-copymsg="' + esc(encodeURIComponent(msg)) + '">Copy msg</button>') + '</div>';
  }
  function showDispatch(list, wa, kind) {
    var rows = list.map(function (t) { return waRow(t.assignee, taskMsg(t, kind), dispNo(t) + ' · queue #' + (qRank(t) || '-')); }).join('');
    modal(kind === 'new' ? '✅ ' + (list[0] && list[0].grp ? 'Group task assigned to ' + list.length : list.length + ' task(s) assigned') : 'Send reminder', '<div class="bn g">Saved in ERP. ' + (wa ? 'Tap WhatsApp for each person to send the ready message.' : '') + '</div>' + (wa ? rows : ''), [['Done', 'pri', closeModal]], true);
  }

  /* ================================================================
     ALL TASKS
  ================================================================ */
  function applyFilters(list) {
    var f = S.f, s = f.q.toLowerCase(), now = new Date();
    return list.filter(function (t) {
      if (s && (dispNo(t) + ' ' + t.title + ' ' + t.details + ' ' + personName(t.assignee) + ' ' + personName(t.by) + ' ' + t.branch + ' ' + t.dept).toLowerCase().indexOf(s) < 0) return false;
      if (f.branch && t.branch !== f.branch) return false; if (f.dept && t.dept !== f.dept) return false; if (f.desig && t.desig !== f.desig) return false;
      if (f.assignee && t.assignee !== f.assignee) return false; if (f.by && t.by !== f.by) return false; if (f.cat && t.cat !== f.cat) return false;
      if (f.pri && t.pri !== f.pri) return false; if (f.rep && (t.report || {}).type !== f.rep) return false;
      if (f.grp === 'grp' && !t.grp) return false; if (f.grp === 'ind' && t.grp) return false;
      if (f.from && (t.created || '').slice(0, 10) < f.from) return false; if (f.to && (t.created || '').slice(0, 10) > f.to) return false;
      var st = f.status;
      if (st === 'Active' && isClosed(t)) return false; if (st === 'Overdue' && !isOverdue(t, now)) return false; if (st === 'DueToday' && !dueToday(t)) return false;
      if (st === 'Critical' && (isClosed(t) || (t.pri !== 'VVIMP' && t.pri !== 'IMP'))) return false; if (st === 'Reports' && !reportDue(t)) return false;
      if (STATUSES.indexOf(st) > -1 && t.status !== st) return false;
      return true;
    });
  }
  function sortList(list) {
    var k = S.sort.k, d = S.sort.d;
    var val = function (t) {
      if (k === 'q') return (isClosed(t) ? 1e7 : 0) + PRI_W(t.pri) * 1e5 + (+qRank(t) || 999);
      if (k === 'no') return dispNo(t); if (k === 'title') return t.title.toLowerCase(); if (k === 'to') return personName(t.assignee).toLowerCase(); if (k === 'by') return personName(t.by).toLowerCase();
      if (k === 'pri') return PRI_W(t.pri); if (k === 'created') return t.created; if (k === 'due') return t.due || '9'; if (k === 'status') return t.status; if (k === 'prog') return t.progress;
      return '';
    };
    return list.slice().sort(function (a, b) { var x = val(a), y = val(b); return (x > y ? 1 : x < y ? -1 : 0) * d; });
  }
  function fsel(key, opts, val, label, all) { return '<div class="fld"><label class="lbl">' + label + '</label><select data-ff="' + key + '">' + optList(opts, val, all) + '</select></div>'; }
  function renderAll() {
    var v = visible(), f = S.f;
    var names = function (arr) { return uniq(arr).map(function (u) { return [u, personName(u)]; }).sort(function (a, b) { return a[1].localeCompare(b[1]); }); };
    var stOpts = [['Active', 'Active (not closed)'], ['Overdue', 'Overdue'], ['DueToday', 'Due today'], ['Critical', 'P1 + P2 open'], ['Reports', 'Report due']].concat(STATUSES.map(function (s) { return [s, s]; }));
    var list = sortList(applyFilters(v));
    q('#view').innerHTML = '<div class="card"><div class="cb">' +
      '<div class="fbar"><div class="fld fq"><label class="lbl">Search</label><input id="ff-q" value="' + esc(f.q) + '" placeholder="Task no, title, employee, branch…"></div>' +
      fsel('status', stOpts, f.status, 'Status', 'All statuses') + fsel('pri', PRI_KEYS.map(function (k) { return [k, PRI_N(k) + ' ' + PRI_L(k)]; }), f.pri, 'Priority') + fsel('cat', uniq(categories().concat(v.map(function (t) { return t.cat; }))), f.cat, 'Category') +
      fsel('branch', uniq(v.map(function (t) { return t.branch; })).sort(), f.branch, 'Branch') + fsel('dept', uniq(v.map(function (t) { return t.dept; })).sort(), f.dept, 'Department') + fsel('assignee', names(v.map(function (t) { return t.assignee; })), f.assignee, 'Assigned to') +
      fsel('desig', uniq(v.map(function (t) { return t.desig; })).sort(), f.desig, 'Designation') + fsel('by', names(v.map(function (t) { return t.by; })), f.by, 'Assigned by') + fsel('rep', REPORT_DEF.map(function (r) { return [r.k, r.label]; }), f.rep, 'Reporting') + fsel('grp', [['grp', '👥 Group tasks'], ['ind', '👤 Individual tasks']], f.grp, 'Type') +
      '<div class="fld"><label class="lbl">Assigned from</label><input type="date" data-ff="from" value="' + esc(f.from) + '"></div><div class="fld"><label class="lbl">Assigned to</label><input type="date" data-ff="to" value="' + esc(f.to) + '"></div></div>' +
      '<div class="vbar">' + [['table', '☰ Table'], ['queue', '⇅ Queue by Assignee'], ['board', '▦ Status Board']].map(function (x) { return '<button class="btn sm ' + (S.allView === x[0] ? 'pri' : '') + '" data-view="' + x[0] + '">' + x[1] + '</button>'; }).join('') +
      '<span class="hint" style="margin-left:6px">' + list.length + ' tasks</span><span style="flex:1"></span><button class="btn sm" data-act="f-clear">✕ Clear filters</button>' + (can('export') ? '<button class="btn sm" data-act="export-all">⬇ CSV</button><button class="btn sm" data-act="print">🖨 Print</button>' : '') + hb('all') + '</div></div></div><div id="all-body"></div>';
    if (S.allView === 'table') renderTable(list, '#all-body'); else if (S.allView === 'queue') renderQueueView(list); else renderBoard(list);
  }
  function renderTable(list, sel) {
    var total = list.length, pages = Math.max(1, Math.ceil(total / PAGE)); if (S.page > pages) S.page = pages;
    var rows = list.slice((S.page - 1) * PAGE, S.page * PAGE);
    var th = function (k, l) { return '<th data-sort="' + k + '">' + l + (S.sort.k === k ? (S.sort.d > 0 ? ' ▲' : ' ▼') : '') + '</th>'; };
    q(sel).innerHTML = '<div class="card"><div class="tw"><table class="tt">' + cols([4, 19, 13, 9, 9, 8, 10, 7, 7, 5, 9]) + '<thead><tr>' + th('q', 'Q#') + th('title', 'Task') + th('to', 'Assigned To') + '<th>Mobile</th>' + th('by', 'By') + th('pri', 'Priority') + th('due', 'Assigned / Due') + '<th>Time left</th><th>Report</th>' + th('prog', '%') + th('status', 'Status') + '</tr></thead><tbody>' +
      (rows.length ? rows.map(rowHtml).join('') : '<tr><td colspan="11"><div class="empty"><b>No tasks match</b>Change filters or assign a new task.</div></td></tr>') +
      '</tbody></table></div><div class="pager"><span>' + (total ? (S.page - 1) * PAGE + 1 : 0) + '–' + Math.min(S.page * PAGE, total) + ' of ' + total + '</span><button class="btn sm" data-pg="-1" ' + (S.page <= 1 ? 'disabled' : '') + '>‹ Prev</button><span>' + S.page + ' / ' + pages + '</span><button class="btn sm" data-pg="1" ' + (S.page >= pages ? 'disabled' : '') + '>Next ›</button></div></div>';
  }
  function rowHtml(t) {
    var rk = qRank(t), rd = reportDue(t), nf = (S.files[fileKey(t)] || []).length, nu = t.updates.filter(function (u) { return u.type !== 'System'; }).length;
    return '<tr class="' + (isOverdue(t) ? 'od' : '') + '" data-open="' + esc(t.id) + '" style="cursor:pointer">' +
      TD('Q#', rk ? '<span class="qn ' + (rk === 1 ? 'q1' : '') + '">#' + rk + '</span>' : '<span class="mut">—</span>') +
      TD('Task', '<span class="tl1" title="' + esc(t.title + '\n\n' + t.details) + '">' + esc(t.title) + '</span><div class="pm"><span class="tno">' + esc(dispNo(t)) + '</span>' + grpTag(t) + ' · ' + esc(t.cat) + ' · 📎' + nf + ' 💬' + nu + '</div>') +
      TD('Assigned to', '<div class="pn">' + esc(personName(t.assignee)) + '</div><div class="pm">' + esc([t.desig, t.branch].filter(Boolean).join(' · ')) + '</div>') +
      TD('Mobile', phHtml(t.assignee)) + TD('By', '<div class="pn" style="font-weight:500">' + esc(personName(t.by)) + '</div>') + TD('Priority', priPill(t.pri)) +
      TD('Assigned / Due', '<div class="pm">' + fDT(t.created) + '</div><div style="font-weight:600">' + fDT(t.due) + '</div>') + TD('Time left', timeLeft(t)) +
      TD('Report', rd ? '<span class="tag ' + (rd.late ? 'r' : 'b') + '">' + esc(rd.label) + '</span>' : '<span class="pm">' + esc(repText(t.report)) + '</span>') +
      TD('Progress', '<span class="pm" style="display:block">' + t.progress + '%</span><span class="bar"><i style="width:' + t.progress + '%"></i></span>') + TD('Status', stPill(t), 'wr') + '</tr>';
  }
  function renderQueueView(list) {
    var groups = {};
    list.forEach(function (t) { (groups[t.assignee] = groups[t.assignee] || []).push(t); });
    var keys = Object.keys(groups).sort(function (a, b) { var oa = groups[a].filter(function (t) { return isOverdue(t); }).length, ob = groups[b].filter(function (t) { return isOverdue(t); }).length; return ob - oa || groups[b].length - groups[a].length; });
    q('#all-body').innerHTML = '<div class="card"><div class="ch lt">Tasks by assignee — working order<span class="sp"><button class="btn sm" data-act="q-expand">Expand all</button><button class="btn sm" data-act="q-collapse">Collapse</button></span></div><div class="cb" style="max-height:calc(100vh - 330px);overflow:auto">' +
      (keys.length ? keys.map(function (u) {
        var l = groups[u].slice().sort(function (a, b) { return (isClosed(a) - isClosed(b)) || a.qk - b.qk; }), p = person(u) || {}, open = l.filter(function (t) { return !isClosed(t); }), od = open.filter(function (t) { return isOverdue(t); }).length, top = open[0];
        return '<div class="qg"><div class="qh" data-qtoggle="1"><span class="arr">▶</span><div class="av">' + initials(personName(u)) + '</div><div class="pi"><div class="pn">' + esc(personName(u)) + ' <span class="pm" style="display:inline">' + esc([p.desig, p.branch].filter(Boolean).join(' · ')) + '</span></div><div class="pm">Now: ' + (top ? esc(dispNo(top) + ' — ' + top.title) : '—') + '</div></div>' + phHtml(p) +
          '<span class="tag g">' + open.length + ' open</span>' + (od ? '<span class="tag r">OD ' + od + '</span>' : '') +
          (can('manage') || open.some(canManage) ? '<button class="btn sm pri" data-mq="' + esc(u) + '">Manage Queue</button>' : '') + '</div>' +
          '<div class="qbd">' + l.map(function (t) { var rk = qRank(t); return '<div class="qi" data-open="' + esc(t.id) + '" style="cursor:pointer">' + (rk ? '<span class="qn ' + (rk === 1 ? 'q1' : '') + '">#' + rk + '</span>' : '<span class="qn" style="background:#aaa">✓</span>') + '<div class="pi"><div class="tl1" style="max-width:none">' + esc(dispNo(t)) + ' — ' + esc(t.title) + grpTag(t) + '</div><div class="pm">' + esc(t.cat) + ' · due ' + fDT(t.due) + ' · by ' + esc(personName(t.by)) + '</div></div>' + priPill(t.pri) + stPill(t) + '<span style="width:80px;text-align:right">' + timeLeft(t) + '</span></div>'; }).join('') + '</div></div>';
      }).join('') : '<div class="empty"><b>No tasks match</b></div>') + '</div></div>';
  }
  function renderBoard(list) {
    var c5 = [['Open', ['Open', 'Reopened']], ['In Progress', ['In Progress']], ['On Hold', ['On Hold']], ['Review Pending', ['Review Pending']], ['Completed', ['Completed']]];
    q('#all-body').innerHTML = '<div class="board">' + c5.map(function (c) {
      var l = list.filter(function (t) { return c[1].indexOf(t.status) > -1; }).sort(function (a, b) { return PRI_W(a.pri) - PRI_W(b.pri) || (a.due > b.due ? 1 : -1); });
      return '<div class="bcol"><div class="bh"><span>' + c[0] + '</span><span class="tag">' + l.length + '</span></div><div class="bb">' + l.slice(0, 80).map(function (t) { return '<div class="bc" data-open="' + esc(t.id) + '"><div class="row" style="justify-content:space-between;flex-wrap:nowrap"><span class="tno">' + esc(dispNo(t)) + grpTag(t) + '</span>' + priPill(t.pri) + '</div><div class="pn" style="margin:3px 0">' + esc(t.title) + '</div><div class="pm">' + esc(personName(t.assignee)) + ' · ' + esc(t.branch) + '</div><div class="row" style="justify-content:space-between;flex-wrap:nowrap">' + phHtml(t.assignee, true) + '<span style="font-size:11.5px">' + timeLeft(t) + '</span></div></div>'; }).join('') + '</div></div>';
    }).join('') + '</div>';
  }

  /* ================================================================
     MY TASKS
  ================================================================ */
  function renderMy() {
    var me = S.me.user, tome = queueOf(me);
    var byme = S.tasks.filter(function (t) { return (t.by === me || t.owner === me) && t.assignee !== me; });
    var ccme = S.tasks.filter(function (t) { return t.cc.indexOf(me) > -1; });
    var reps = S.tasks.filter(function (t) { return t.assignee === me && reportDue(t); });
    var review = byme.filter(function (t) { return t.status === 'Review Pending'; });
    var groups = S.tasks.filter(function (t) { return t.grp && t.assignee === me; });
    var done = S.tasks.filter(function (t) { return t.assignee === me && isClosed(t); }).sort(function (a, b) { return (b.completedOn || b.modified) > (a.completedOn || a.modified) ? 1 : -1; });
    var tabs = [['tome', 'Assigned to Me', tome.length], ['reps', 'Reports Due', reps.length], ['review', 'Awaiting My Review', review.length], ['byme', 'Assigned by Me', byme.filter(function (t) { return !isClosed(t); }).length], ['groups', '👥 My Groups', groups.filter(function (t) { return !isClosed(t); }).length], ['cc', 'Following (CC)', ccme.filter(function (t) { return !isClosed(t); }).length], ['done', 'My Closed', done.length]];
    var h = '<div class="stabs">' + tabs.map(function (x) { return '<button class="btn ' + (S.myTab === x[0] ? 'pri' : '') + '" data-my="' + x[0] + '">' + x[1] + ' <span class="tag">' + x[2] + '</span></button>'; }).join('') + hb('my') + '</div>';
    if (S.myTab === 'tome') {
      var od = tome.filter(function (t) { return isOverdue(t); }).length, top = tome[0];
      if (od) h += '<div class="bn r">⚠ ' + od + ' overdue task(s)' + (mod('delayMandatory') ? ' — post a Delay Remark on each.' : '.') + '</div>';
      if (top) h += '<div class="hero"><span class="qn q1">#1</span><div class="pi"><div class="pm">DO THIS NOW · ' + esc(dispNo(top)) + ' · ' + esc(top.cat) + ' · by ' + esc(personName(top.by)) + grpTag(top) + '</div><div class="tl1" data-open="' + esc(top.id) + '" style="font-size:16px;max-width:none">' + esc(top.title) + '</div><div class="row" style="margin-top:3px">' + priPill(top.pri) + stPill(top) + '<span class="tag">Due ' + fDT(top.due) + '</span>' + timeLeft(top) + '</div></div><div class="row" style="flex:none">' + myBtns(top) + '</div></div>';
      h += tome.length > 1 ? '<div class="mtg">' + tome.slice(1).map(myCard).join('') + '</div>' : (top ? '' : '<div class="card"><div class="empty"><b>Queue is clear 🎉</b>No open tasks assigned to you.</div></div>');
    } else if (S.myTab === 'reps' || S.myTab === 'review') {
      var l = S.myTab === 'reps' ? reps : review;
      h += l.length ? '<div class="mtg">' + l.map(myCard).join('') + '</div>' : '<div class="card"><div class="empty"><b>Nothing pending</b></div></div>';
    } else {
      var l2 = sortList(S.myTab === 'byme' ? byme : S.myTab === 'cc' ? ccme : S.myTab === 'groups' ? groups : done);
      h += '<div id="my-tbl"></div>'; q('#view').innerHTML = h; renderTable(l2, '#my-tbl'); return;
    }
    q('#view').innerHTML = h;
  }
  function myBtns(t) {
    var mine = isAssignee(t), rd = reportDue(t), b = '';
    if (mine && (t.status === 'Open' || t.status === 'Reopened' || t.status === 'On Hold')) b += '<button class="btn sm amb" data-qa="start" data-id="' + esc(t.id) + '">▶ Start</button>';
    if (mine && !isClosed(t)) b += '<button class="btn sm" data-qa="update" data-id="' + esc(t.id) + '">💬 Update</button>';
    if (rd && mine) b += '<button class="btn sm blue" data-qa="report" data-id="' + esc(t.id) + '">📝 Report</button>';
    if (mine && !isClosed(t) && t.status !== 'Review Pending') b += '<button class="btn sm pri" data-qa="submit" data-id="' + esc(t.id) + '">✓ Done</button>';
    if (t.status === 'Review Pending' && canManage(t)) b += '<button class="btn sm pri" data-qa="approve" data-id="' + esc(t.id) + '">✓ Approve</button><button class="btn sm red" data-qa="reopen" data-id="' + esc(t.id) + '">↺ Reopen</button>';
    return b + '<button class="btn sm" data-open="' + esc(t.id) + '">Open</button>';
  }
  function myCard(t) {
    var rk = qRank(t), od = isOverdue(t), rd = reportDue(t), mine = isAssignee(t);
    return '<div class="mc ' + (od ? 'od' : '') + '"><div class="mh"><span class="qn ' + (rk === 1 ? 'q1' : '') + '">#' + (rk || '-') + '</span><div class="pi"><div class="tno">' + esc(dispNo(t)) + grpTag(t) + '</div><div class="pm">' + esc(t.cat) + (mine ? ' · by ' + esc(personName(t.by)) : ' · ' + esc(personName(t.assignee))) + '</div></div>' + priPill(t.pri) + '</div>' +
      '<div class="mb"><div class="tl1" data-open="' + esc(t.id) + '" style="max-width:none">' + esc(t.title) + '</div>' +
      '<div class="row" style="margin-top:4px;gap:4px">' + stPill(t) + '<span class="tag">Due ' + fDT(t.due) + '</span>' + timeLeft(t) + '</div>' +
      (rd ? '<div class="tag ' + (rd.late ? 'r' : 'a') + '" style="display:inline-block;margin-top:4px">📝 ' + esc(rd.label) + '</div>' : '') + (needsDelayRemark(t) && mine ? ' <span class="tag r">Delay remark required</span>' : '') +
      '<div style="margin-top:5px"><span class="bar" style="max-width:none"><i style="width:' + t.progress + '%"></i></span></div></div><div class="mf">' + myBtns(t) + '</div></div>';
  }

  /* ================================================================
     TEAM & CONTACTS
  ================================================================ */
  function renderTeam() {
    if (!can('team')) { q('#view').innerHTML = '<div class="card"><div class="empty"><b>Not allowed</b>Your role cannot see Team &amp; Contacts.</div></div>'; return; }
    var f = S.team, s = f.q.toLowerCase();
    var list = S.people.filter(function (p) { return (!f.branch || p.branch === f.branch) && (!f.dept || p.dept === f.dept) && (!s || (p.name + ' ' + p.desig + ' ' + p.dept + ' ' + p.branch + ' ' + (phonesOpen() ? digits(p.phone) : '') + ' ' + p.user).toLowerCase().indexOf(s) > -1); });
    var noPh = S.people.filter(function (p) { return !digits(p.phone); }).length, noLogin = S.people.filter(function (p) { return !p.login; }).length;
    q('#view').innerHTML = '<div class="card"><div class="cb"><div class="fbar">' +
      '<div class="fld fq"><label class="lbl">Search</label><input id="tm-q" value="' + esc(f.q) + '" placeholder="Name, designation, branch…"></div>' +
      '<div class="fld"><label class="lbl">Branch</label><select data-tf2="branch">' + optList(allBranches(), f.branch) + '</select></div>' +
      '<div class="fld"><label class="lbl">Department</label><select data-tf2="dept">' + optList(distinct('dept'), f.dept) + '</select></div></div>' +
      '<div class="vbar"><span class="hint">' + list.length + ' people · <span class="red">' + noPh + ' without mobile</span> · ' + noLogin + ' without ERP login · Mobiles ' + (phonesOpen() ? '<b class="grn">visible</b>' : '<b>masked</b>' + (S.cfg.phone.codeHash ? ' <button class="lock" data-act="unlock">🔒 Unlock</button>' : '')) + '</span><span style="flex:1"></span>' + (can('export') ? '<button class="btn sm" data-act="export-team">⬇ CSV</button>' : '') + hb('team') + '</div></div></div>' +
      '<div class="card"><div class="tw"><table class="tt">' + cols([15, 11, 9, 9, 11, 6, 11, 5, 6, 10, 7]) + '<thead><tr><th>Employee</th><th>Designation</th><th>Department</th><th>Branch</th><th>Mobile</th><th>WA</th><th>ERP Login</th><th>Open</th><th>Overdue</th><th>Now (#1)</th><th></th></tr></thead><tbody>' +
      list.map(function (p) {
        var l = p.login ? queueOf(p.user) : [], od = l.filter(function (t) { return isOverdue(t); }).length, ph = phone91(p.phone);
        return '<tr>' + TD('Employee', '<div class="row" style="flex-wrap:nowrap"><div class="av">' + initials(p.name) + '</div><b class="nw">' + esc(p.name) + '</b></div>') + TD('Designation', esc(p.desig || '—')) + TD('Department', esc(p.dept || '—')) + TD('Branch', esc(p.branch || '—')) + TD('Mobile', phHtml(p)) +
          TD('WhatsApp', ph && mod('wa') ? '<a class="btn wa sm" target="_blank" href="https://wa.me/' + ph + '">Chat</a>' : '<span class="mut">—</span>') + TD('ERP login', p.login ? '<span class="tag g">' + esc(p.user) + '</span>' : '<span class="tag r">No login</span>') +
          TD('Open', p.login ? String(l.length) : '—') + TD('Overdue', '<b class="' + (od ? 'red' : '') + '">' + (p.login ? od : '—') + '</b>') + TD('Now (#1)', l[0] ? '<span class="tl1" data-open="' + esc(l[0].id) + '">' + esc(dispNo(l[0]) + ' — ' + l[0].title) + '</span>' : '<span class="mut">—</span>') +
          TD('', p.login ? (can('assign') ? '<button class="btn sm pri" data-assignto="' + esc(p.user) + '">Assign</button> ' : '') + (l.length ? '<button class="btn sm" data-mq="' + esc(p.user) + '">Queue</button>' : '') : '') + '</tr>';
      }).join('') + '</tbody></table></div></div>';
  }

  /* ================================================================
     REPORTS
  ================================================================ */
  function stats(list) {
    var o = { n: list.length, open: 0, prog: 0, rev: 0, done: 0, cxl: 0, od: 0, ontime: 0, late: 0, days: 0, missed: 0 };
    list.forEach(function (t) {
      if (t.status === 'Completed') { o.done++; var c = toDate(t.completedOn), d = toDate(t.due), s = toDate(t.start) || toDate(t.created); if (c && d) { if (c <= d) o.ontime++; else o.late++; } if (c && s) o.days += Math.max(0, (c - s) / 86400000); }
      else if (t.status === 'Cancelled') o.cxl++;
      else { o.open++; if (t.status === 'In Progress') o.prog++; if (t.status === 'Review Pending') o.rev++; if (isOverdue(t)) o.od++; var rd = reportDue(t); if (rd && rd.late) o.missed++; }
    });
    o.pct = o.done ? Math.round(o.ontime * 100 / o.done) : null; o.avg = o.done ? (o.days / o.done).toFixed(1) : '—';
    return o;
  }
  function renderReports() {
    var f = S.f, list = visible().filter(function (t) { return (!f.from || (t.created || '').slice(0, 10) >= f.from) && (!f.to || (t.created || '').slice(0, 10) <= f.to); });
    var dims = [['assignee', 'Employee'], ['branch', 'Branch'], ['dept', 'Department'], ['desig', 'Designation'], ['by', 'Assigned By'], ['cat', 'Category'], ['pri', 'Priority']];
    var dimLabel = dims.filter(function (d) { return d[0] === S.rptDim; })[0][1], groups = {};
    list.forEach(function (t) { var k = S.rptDim === 'pri' ? PRI_N(t.pri) + ' ' + PRI_L(t.pri) : (S.rptDim === 'assignee' || S.rptDim === 'by') ? personName(t[S.rptDim]) : (t[S.rptDim] || '(blank)'); (groups[k] = groups[k] || []).push(t); });
    var rows = Object.keys(groups).map(function (k) { return [k, stats(groups[k]), groups[k][0]]; }).sort(function (a, b) { return b[1].od - a[1].od || b[1].open - a[1].open; });
    var tot = stats(list);
    var aging = [['0–1 day', 0, 1], ['2–3 days', 1, 3], ['4–7 days', 3, 7], ['8–15 days', 7, 15], ['16–30 days', 15, 30], ['30+ days', 30, 1e5]].map(function (b) { return [b[0], list.filter(function (t) { if (isClosed(t)) return false; var c = toDate(t.created), a = c ? (Date.now() - c) / 86400000 : 0; return a >= b[1] && a < b[2]; }).length]; });
    var maxA = Math.max.apply(null, aging.map(function (a) { return a[1]; }).concat([1]));
    var pr = PRI_KEYS.map(function (k) { return [k, stats(list.filter(function (t) { return t.pri === k; }))]; }), maxP = Math.max.apply(null, pr.map(function (r) { return r[1].n; }).concat([1]));
    S._rptRows = rows;
    var emp = S.rptDim === 'assignee';
    q('#view').innerHTML = '<div class="card"><div class="cb"><div class="fbar">' +
      '<div class="fld"><label class="lbl">Assigned from</label><input type="date" data-ff="from" value="' + esc(f.from) + '"></div><div class="fld"><label class="lbl">Assigned to</label><input type="date" data-ff="to" value="' + esc(f.to) + '"></div>' +
      '<div class="fld"><label class="lbl">Group by</label><select id="rp-dim">' + dims.map(function (d) { return '<option value="' + d[0] + '" ' + (S.rptDim === d[0] ? 'selected' : '') + '>' + d[1] + '</option>'; }).join('') + '</select></div>' +
      '<div class="fld"><label class="lbl">Quick period</label><div class="row" style="flex-wrap:nowrap"><button class="btn sm" data-rq="7">7d</button><button class="btn sm" data-rq="30">30d</button><button class="btn sm" data-rq="90">90d</button><button class="btn sm" data-rq="0">All</button></div></div>' +
      '<div class="fld"><label class="lbl">&nbsp;</label><div class="row" style="flex-wrap:nowrap">' + (can('export') ? '<button class="btn sm" data-act="export-rpt">⬇ CSV</button><button class="btn sm" data-act="print">🖨</button>' : '') + hb('reports') + '</div></div></div>' +
      '<div class="ig" style="grid-template-columns:repeat(auto-fit,minmax(110px,1fr));margin-top:9px">' + [['Total', tot.n], ['Open', tot.open], ['Overdue', tot.od], ['Completed', tot.done], ['On-time %', tot.pct == null ? '—' : tot.pct + '%'], ['Late closures', tot.late], ['Avg days', tot.avg], ['Reports late', tot.missed]].map(function (x) { return '<div class="ii"><div class="k">' + x[0] + '</div><div class="v" style="font-size:18px">' + x[1] + '</div></div>'; }).join('') + '</div></div></div>' +
      '<div class="tk2" style="grid-template-columns:minmax(0,1.8fr) minmax(0,1fr)"><div class="card"><div class="ch">Performance by ' + esc(dimLabel) + '</div><div class="tw" style="max-height:calc(100vh - 380px);overflow-y:auto"><table class="tt">' + cols(emp ? [17, 11, 6, 6, 7, 6, 7, 6, 7, 5, 7, 6, 6, 7] : [20, 7, 7, 7, 7, 7, 7, 7, 6, 8, 6, 6, 5]) + '<thead><tr><th>' + esc(dimLabel) + '</th>' + (emp ? '<th>Mobile</th>' : '') + '<th>Total</th><th>Open</th><th>In Prog</th><th>Review</th><th>Overdue</th><th>Done</th><th>On-time</th><th>Late</th><th>On-time %</th><th>Avg d</th><th>Rep late</th><th>Score</th></tr></thead><tbody>' +
      (rows.length ? rows.map(function (r) { var s = r[1], score = s.n ? Math.min(100, Math.max(0, Math.round(100 - s.od * 15 - s.late * 5 - s.missed * 5 + (s.pct || 0) * 0.2))) : 0; return '<tr>' + TD(dimLabel, '<b>' + esc(r[0]) + '</b>') + (emp ? TD('Mobile', phHtml(r[2].assignee)) : '') + TD('Total', s.n) + TD('Open', s.open) + TD('In progress', s.prog) + TD('Review', s.rev) + TD('Overdue', '<b class="' + (s.od ? 'red' : '') + '">' + s.od + '</b>') + TD('Done', s.done) + TD('On-time', '<span class="grn">' + s.ontime + '</span>') + TD('Late', '<span class="' + (s.late ? 'red' : '') + '">' + s.late + '</span>') + TD('On-time %', s.pct == null ? '—' : s.pct + '%') + TD('Avg days', s.avg) + TD('Reports late', '<span class="' + (s.missed ? 'red' : '') + '">' + s.missed + '</span>') + TD('Score', '<span class="pill ' + (score >= 80 ? 's-done' : score >= 50 ? 's-prog' : 's-od') + '">' + score + '</span>') + '</tr>'; }).join('') : '<tr><td colspan="14"><div class="empty"><b>No data</b></div></td></tr>') +
      '</tbody></table></div></div><div>' +
      '<div class="card"><div class="ch">Open-task aging</div><div class="cb">' + aging.map(function (a) { return '<div class="hbar"><span class="hl">' + a[0] + '</span><span class="ht"><i style="width:' + (a[1] * 100 / maxA) + '%;background:var(--g600)"></i></span><span class="hv">' + a[1] + '</span></div>'; }).join('') + '</div></div>' +
      '<div class="card"><div class="ch">Priority mix</div><div class="cb"><div class="legend"><span><i style="background:var(--g600)"></i>Done</span><span><i style="background:var(--blue)"></i>Open</span><span><i style="background:var(--red)"></i>Overdue</span></div>' + pr.map(function (r) { var s = r[1]; return '<div class="hbar"><span class="hl">' + PRI_N(r[0]) + ' ' + esc(PRI_L(r[0])) + '</span><span class="ht"><i style="width:' + (s.done * 100 / maxP) + '%;background:var(--g600)"></i><i style="width:' + ((s.open - s.od) * 100 / maxP) + '%;background:var(--blue)"></i><i style="width:' + (s.od * 100 / maxP) + '%;background:var(--red)"></i></span><span class="hv">' + s.n + '</span></div>'; }).join('') + '</div></div></div></div>';
  }

  /* ================================================================
     TASK PANEL (drawer) + ACTIONS
  ================================================================ */
  function findTask(id) { return S.tasks.filter(function (t) { return t.id === id; })[0]; }
  function info(k, v, raw) { return '<div class="ii"><div class="k">' + esc(k) + '</div><div class="v" title="' + esc(raw ? '' : v) + '">' + (raw ? v : esc(v)) + '</div></div>'; }
  function openTask(id) {
    var t = findTask(id); if (!t) return; S.openTask = id; S.openTicket = null;
    var p = person(t.assignee) || {}, rk = qRank(t), files = S.files[fileKey(t)] || [], mgr = canManage(t), mine = isAssignee(t), rd = reportDue(t), can2 = (mine || mgr) && !isClosed(t);
    var ckDone = t.checklist.filter(function (c) { return c.d; }).length, A = [];
    var b = function (cls, qa2, txt) { A.push('<button class="btn ' + cls + '" data-qa="' + qa2 + '" data-id="' + esc(t.id) + '">' + txt + '</button>'); };
    if (mine && (t.status === 'Open' || t.status === 'Reopened' || t.status === 'On Hold')) b('amb', 'start', '▶ Start');
    if (mine && rd) b('blue', 'report', '📝 Submit ' + esc(rd.label));
    if (mine && !isClosed(t) && t.status !== 'Review Pending') b('pri', 'submit', '✓ Done → Review');
    if (mgr && t.status === 'Review Pending') b('pri', 'approve', '✓ Approve &amp; Close');
    if (mgr && !isClosed(t) && t.status !== 'Review Pending') b('pri', 'closeNow', '✓ Close');
    if (mgr && (t.status === 'Review Pending' || isClosed(t))) b('red', 'reopen', '↺ Reopen');
    if (mgr && !isClosed(t)) { b('', 'extend', '🗓 Extend'); b('', 'pri', '⚑ Priority'); b('', 'top', '⬆ Make #1'); if (!t.grp) b('', 'reassign', '⇄ Reassign'); b('', 'hold', '⏸ Hold'); b('red', 'cancel', t.grp ? '✕ Cancel group' : '✕ Cancel'); }
    if (!isClosed(t) && (mgr || t.cc.indexOf(S.me.user) > -1)) b('wa', 'notify', '🔔 Remind');
    var members = '';
    if (t.grp) {
      var vs = S.tasks.filter(function (x) { return x.mid === t.mid; });
      members = '<div class="sub" style="margin-top:10px">👥 Group members (' + t.grp.members.length + ') · ' + (t.grp.response === 'group' ? 'Group response — one shared status' : 'Individual response — each completes own part') + '</div><div class="ig" style="grid-template-columns:repeat(auto-fill,minmax(210px,1fr))">' +
        t.grp.members.map(function (u) { var v = vs.filter(function (x) { return x.assignee === u; })[0] || {}; return '<div class="ii"><div class="k">' + (u === t.grp.leader ? '⭐ Leader' : 'Member') + '</div><div class="v">' + esc(personName(u)) + '</div><div class="row" style="flex-wrap:nowrap;gap:4px;margin-top:2px">' + phHtml(u, true) + '<span class="pill ' + (ST_CLS[v.status] || 's-open') + '">' + esc(v.status || '—') + '</span>' + (v.progress != null ? '<span class="pm">' + v.progress + '%</span>' : '') + '</div></div>'; }).join('') + '</div>';
    }
    var h = '<div class="dh"><span class="qn ' + (rk === 1 ? 'q1' : '') + '" style="min-width:40px;height:40px;font-size:15px">' + (rk ? '#' + rk : '✓') + '</span><div class="pi"><div style="font-size:11.5px;opacity:.85">' + esc(dispNo(t)) + ' · ' + esc(t.cat) + (t.grp ? ' · 👥 Group task' : '') + '</div><div style="font-size:16px;font-weight:700" class="nw">' + esc(t.title) + '</div><div class="row" style="margin-top:3px">' + priPill(t.pri) + stPill(t) + '</div></div>' + hb('drawer') + '<button class="x" data-act="close-drawer">×</button></div>' +
      '<div class="db">' +
      (needsDelayRemark(t) ? '<div class="bn r">⚠ Overdue by ' + dur(new Date() - toDate(t.due)) + '. ' + (mine ? 'Post a <b>Delay Remark</b> — reason + new expected time.' : 'Assignee has not posted a delay remark.') + '</div>' : (isOverdue(t) ? '<div class="bn a">Overdue by ' + dur(new Date() - toDate(t.due)) + '.</div>' : '')) +
      (rd ? '<div class="bn ' + (rd.late ? 'r' : 'a') + '">📝 ' + esc(rd.label) + (rd.late ? ' — LATE' : '') + '</div>' : '') +
      '<div class="ig">' + info(t.grp ? 'Viewing as member' : 'Assigned to', personName(t.assignee)) + info('Mobile', phHtml(p), true) + info('Designation', t.desig || '—') + info('Branch / Dept', [t.branch, t.dept].filter(Boolean).join(' · ') || '—') +
      info('Assigned by', personName(t.by)) + info('Assigner mobile', phHtml(t.by), true) + info('Assigned on', fDT(t.created)) + info('Start', fDT(t.start)) +
      info('Due', fDT(t.due)) + info('Time left', timeLeft(t), true) + info('Reporting', repText(t.report)) + info('Queue', rk ? '#' + rk + ' of ' + queueOf(t.assignee).length : '—') +
      info('CC', t.cc.map(personName).join(', ') || '—') + info('Target', (t.target.type || 'Employee') + (t.target.values && t.target.values.length ? ': ' + t.target.values.join(', ') : '')) + info('Completed', t.completedOn ? fDT(t.completedOn) : '—') + info('Files', files.length) + '</div>' +
      members +
      '<div class="sub" style="margin-top:10px">Details</div><div class="dbox">' + esc(t.details || '—') + '</div>' +
      '<div class="grid g2" style="margin-top:10px"><div><div class="sub">Progress' + (t.grp && t.grp.response === 'individual' ? ' (' + esc(personName(t.assignee)) + ')' : '') + '</div><div class="row" style="flex-wrap:nowrap"><input type="range" min="0" max="100" step="5" value="' + t.progress + '" id="d-prog" ' + (can2 ? '' : 'disabled') + ' style="flex:1"><b id="d-progv" style="width:40px;text-align:right">' + t.progress + '%</b>' + (can2 ? '<button class="btn sm pri" data-act="save-prog">Save</button>' : '') + '</div>' +
      (t.checklist.length ? '<div class="lbl" style="margin-top:6px">Checklist ' + ckDone + '/' + t.checklist.length + '</div>' + t.checklist.map(function (c, i) { return '<label class="ck ' + (c.d ? 'done' : '') + '"><input type="checkbox" data-ck="' + i + '" ' + (c.d ? 'checked' : '') + ' ' + (can2 ? '' : 'disabled') + '><span>' + esc(c.t) + '</span></label>'; }).join('') : '') + '</div>' +
      '<div><div class="sub">Attachments (' + files.length + ')</div><div class="chips">' + (files.length ? files.map(function (fl) { return '<a class="chip" target="_blank" href="' + esc(fl.file_url) + '">📄 ' + esc(fl.file_name || 'file') + '</a>'; }).join('') : '<span class="hint">No files</span>') + (isClosed(t) ? '' : '<button class="btn sm" data-act="add-file">＋ Add</button>') + '</div>' +
      (t.delays.length ? '<div class="sub">Deadline changes</div>' + t.delays.map(function (d, i) { return '<div class="pm" style="white-space:normal">#' + (i + 1) + ' ' + fDT(d.old_deadline) + ' → <b>' + fDT(d.new_deadline) + '</b> · ' + esc(d.reviewed_by_name || personName(d.reviewed_by)) + ' — ' + esc(d.remarks || '') + '</div>'; }).join('') : '') + '</div></div>' +
      '<div class="sub" style="margin-top:10px">' + (t.grp ? '👥 Group updates — everyone sees all (' : 'Updates &amp; reports (') + t.updates.length + ')</div>' +
      (isClosed(t) ? '' : '<div class="card" style="margin-bottom:8px"><div class="cb"><div class="row" style="flex-wrap:nowrap;align-items:flex-start"><select id="d-utype" style="width:150px;flex:none">' + UPD_TYPES.map(function (x) { return '<option ' + ((x === 'Delay Remark' && needsDelayRemark(t) && mine) || (x === 'Report' && rd && mine && !needsDelayRemark(t)) ? 'selected' : '') + '>' + x + '</option>'; }).join('') + '</select><textarea id="d-utext" style="min-height:40px;height:40px" placeholder="Write update, report, query or delay reason…"></textarea><button class="btn sm" data-act="upd-file" title="Attach" style="height:40px">📎</button><button class="btn pri" data-act="post-upd" style="height:40px">Post</button></div><div class="hint" id="d-ufiles"></div></div></div>') +
      '<div class="tl">' + (t.updates.length ? t.updates.slice().reverse().map(updHtml).join('') : '<div class="hint">No updates yet</div>') + '</div></div>' +
      '<div class="da">' + (A.join('') || '<span class="hint">No actions available for you on this task.</span>') + '</div>';
    showDrawer(h); S.updFiles = [];
  }
  function updHtml(u) {
    return '<div class="te ' + (u.type === 'Report' ? 't-report' : u.type === 'Delay Remark' ? 't-delay' : u.type === 'System' ? 't-system' : '') + '"><div class="teh"><b>' + esc(personName(u.by)) + '</b><span class="tag ' + (u.type === 'Report' ? 'b' : u.type === 'Delay Remark' || u.type === 'Reopened' ? 'r' : u.type === 'Completion' || u.type === 'Resolved' || u.type === 'Closed' ? 'g' : '') + '">' + esc(u.type) + '</span><span>' + fDT(u.at) + '</span></div><div class="tet">' + esc(u.text) + '</div>' +
      (u.files && u.files.length ? '<div class="chips" style="margin-top:3px">' + u.files.map(function (fl) { return '<a class="chip" target="_blank" href="' + esc(fl.url) + '">📄 ' + esc(fl.name) + '</a>'; }).join('') + '</div>' : '') + '</div>';
  }
  function showDrawer(h) { var dr = q('#drawer'); dr.innerHTML = h; dr.classList.add('show'); q('#ovl').classList.add('show'); }
  function closeDrawer() { q('#drawer').classList.remove('show'); q('#ovl').classList.remove('show'); S.openTask = null; S.openTicket = null; }
  function refreshOpen() { if (S.openTask) { if (findTask(S.openTask)) openTask(S.openTask); else closeDrawer(); } else if (S.openTicket) openTicket(S.openTicket); }

  /* persist: fresh read + merge, single or group */
  function persist(id, mutate, okMsg) {
    if (guard()) return Promise.reject('preview');
    var t = findTask(id); if (!t) return Promise.reject('missing');
    if (t.mid) return persistGroup(t, mutate, okMsg);
    return API.get('ToDo', id).then(function (raw) {
      var fresh = enrich(base(raw)); fresh.qk = t.qk; fresh.cq = t.cq;
      var before = isClosed(fresh);
      mutate(fresh);
      var d = denormBase(fresh);
      return API.save('ToDo', id, d).then(function () {
        raw.description = d.description; raw.status = d.status; fresh.raw = raw;
        var i = S.tasks.indexOf(t); if (i > -1) S.tasks[i] = fresh; else S.tasks.unshift(fresh);
        return (before !== isClosed(fresh) ? syncQueue(fresh.assignee) : Promise.resolve()).then(function () { if (okMsg) toast(okMsg); render(); refreshOpen(); return fresh; });
      });
    }).catch(function (e) { if (e !== 'preview') toast('Not saved: ' + errMsg(e), 1); throw e; });
  }
  function persistGroup(t, mutate, okMsg) {
    var mid = t.mid, u = t.assignee;
    return API.get('ToDo', mid).then(function (raw) {
      var b = base(raw), vs = explode(b), v = vs.filter(function (x) { return x.assignee === u; })[0];
      if (!v) throw { message: 'You are not a member of this group task' };
      var beforeOverall = b.status, beforeMine = v.status;
      v.qk = t.qk; mutate(v);
      ['title', 'details', 'cat', 'pri', 'due', 'start', 'cc', 'report', 'updates', 'delays', 'target'].forEach(function (k) { b[k] = v[k]; });
      b.meta.mq = b.meta.mq || {}; b.meta.mq[u] = v.qk;
      if (b.grp.response === 'individual') {
        b.meta.mstate = b.meta.mstate || {};
        b.meta.mstate[u] = { status: v.status, progress: v.progress, completedOn: v.completedOn, checklist: v.checklist };
        b.status = v._cancelAll ? 'Cancelled' : groupOverall(b);
        b.progress = Math.round(b.grp.members.reduce(function (s, m) { return s + (+((b.meta.mstate[m] || {}).progress) || 0); }, 0) / b.grp.members.length);
        if (b.status === 'Completed' && !b.completedOn) b.completedOn = nowLocal();
        if (b.status !== 'Completed') b.completedOn = '';
      } else {
        b.status = v._cancelAll ? 'Cancelled' : v.status; b.progress = v.progress; b.completedOn = v.completedOn; b.checklist = v.checklist;
      }
      var d = denormBase(b);
      return API.save('ToDo', mid, d).then(function () {
        raw.description = d.description; raw.status = d.status;
        var nb = base(raw), nvs = explode(nb);
        S.tasks = S.tasks.filter(function (x) { return x.mid !== mid; }).concat(nvs);
        var jobs = Promise.resolve();
        var changed = beforeOverall !== nb.status || beforeMine !== (nvs.filter(function (x) { return x.assignee === u; })[0] || {}).status;
        if (changed) {
          Object.keys(nb.grp.mirrors || {}).forEach(function (m) {
            var mv = nvs.filter(function (x) { return x.assignee === m; })[0] || {}, st = isClosed(nb) || isClosed(mv) ? (nb.status === 'Cancelled' ? 'Cancelled' : 'Closed') : 'Open';
            jobs = jobs.then(function () { return API.save('ToDo', nb.grp.mirrors[m], { status: st }).catch(function () { }); });
          });
          nb.grp.members.forEach(function (m) { jobs = jobs.then(function () { return syncQueue(m); }); });
        }
        return jobs.then(function () { if (okMsg) toast(okMsg); render(); S.openTask = mid + '::' + u; refreshOpen(); return findTask(mid + '::' + u); });
      });
    }).catch(function (e) { if (e !== 'preview') toast('Not saved: ' + errMsg(e), 1); throw e; });
  }
  function addUpd(t, type, text, files) { t.updates.push({ id: uid(), at: nowLocal(), by: S.me.user, type: type, text: text, files: files || [] }); }
  function uploadPending(dt, id, cache) {
    var fl = S.updFiles || [], out = [];
    return fl.reduce(function (p, f) { return p.then(function () { return API.upload(dt, id, f).then(function (r) { out.push({ name: r.file_name || f.name, url: r.file_url }); (cache[id] = cache[id] || []).push(r); }); }); }, Promise.resolve()).then(function () { S.updFiles = []; return out; });
  }
  function postUpdate() {
    if (guard()) return;
    var id = S.openTask, t = findTask(id), type = q('#d-utype').value, text = q('#d-utext').value.trim();
    if (!text) { toast('Write something first', 1); return; }
    if (needsDelayRemark(t) && isAssignee(t) && type !== 'Delay Remark') { toast('Task is overdue — post a Delay Remark first', 1); q('#d-utype').value = 'Delay Remark'; return; }
    uploadPending('ToDo', fileKey(t), S.files).then(function (files) { return persist(id, function (f) { addUpd(f, type, text, files); if ((type === 'Report' || type === 'Update') && f.status === 'Open' && f.assignee === S.me.user) f.status = 'In Progress'; }, type + ' posted'); }).catch(function () { });
  }
  function quickAction(act, id) {
    if (guard()) return;
    var t = findTask(id); if (!t) return;
    var mine = isAssignee(t);
    var gate = function (next) {
      if (mine && needsDelayRemark(t)) promptBox('Delay remark required', 'Overdue by ' + dur(new Date() - toDate(t.due)) + '. Explain the reason and your new expected completion.', 'Reason for delay…', function (txt) { persist(id, function (f) { addUpd(f, 'Delay Remark', txt); }, 'Delay remark saved').then(function () { t = findTask(S.openTask || id) || t; next(); }).catch(function () { }); });
      else next();
    };
    var P = function (fn, msg) { persist(id, fn, msg).catch(function () { }); };
    if (act === 'start') return gate(function () { P(function (f) { f.status = 'In Progress'; addUpd(f, 'System', 'Work started'); }, 'Started'); });
    if (act === 'update') { openTask(id); setTimeout(function () { var x = q('#d-utext'); if (x) x.focus(); }, 250); return; }
    if (act === 'report') return gate(function () { promptBox('Submit ' + ((reportDue(t) || {}).label || 'report'), 'What was done, what is pending, any blockers.', 'Report…', function (txt) { P(function (f) { addUpd(f, 'Report', txt); if (f.status === 'Open') f.status = 'In Progress'; }, 'Report submitted'); }); });
    if (act === 'submit') return gate(function () { var open = t.checklist.filter(function (c) { return !c.d; }).length; promptBox('Mark done → send for review', (open ? '⚠ ' + open + ' checklist item(s) still unticked. ' : '') + 'Completion remarks — the assigner will approve or reopen.', 'Completion remarks…', function (txt) { P(function (f) { f.status = 'Review Pending'; f.progress = 100; addUpd(f, 'Completion', txt); }, 'Sent for review'); }); });
    if (act === 'approve' || act === 'closeNow') return promptBox(act === 'approve' ? 'Approve & close' : 'Close as completed', 'Optional closing remark.', 'Remark (optional)…', function (txt) { P(function (f) { f.status = 'Completed'; f.progress = 100; f.completedOn = nowLocal(); addUpd(f, 'System', 'Approved & closed by ' + S.me.name + (t.grp && t.grp.response === 'individual' ? ' for ' + personName(f.assignee) : '') + (txt ? ' — ' + txt : '')); }, 'Closed'); }, true);
    if (act === 'reopen') return promptBox('Reopen task', 'Reason (shared with assignee).', 'Reason…', function (txt) { P(function (f) { f.status = 'Reopened'; f.completedOn = ''; f.progress = Math.min(f.progress, 80); addUpd(f, 'System', 'Reopened by ' + S.me.name + ': ' + txt); }, 'Reopened'); });
    if (act === 'hold') return promptBox('Put on hold', 'Reason.', 'Reason…', function (txt) { P(function (f) { f.status = 'On Hold'; addUpd(f, 'System', 'On hold: ' + txt); }, 'On hold'); });
    if (act === 'cancel') return promptBox(t.grp ? 'Cancel whole group task' : 'Cancel task', 'Reason for cancelling.', 'Reason…', function (txt) { P(function (f) { f.status = 'Cancelled'; f._cancelAll = true; addUpd(f, 'System', 'Cancelled: ' + txt); }, 'Cancelled'); });
    if (act === 'extend') {
      modal('Extend deadline — ' + esc(dispNo(t)), '<div class="grid g2"><div class="fld"><label class="lbl">Current due</label><input readonly value="' + fDT(t.due) + '"></div><div class="fld"><label class="lbl">New due *</label><input type="datetime-local" id="m-due" min="' + nowLocal() + '" value="' + esc(t.due) + '"></div></div><div class="fld" style="margin-top:8px"><label class="lbl">Remarks *</label><textarea id="m-txt" placeholder="Why extended"></textarea></div>', [['Cancel', '', closeModal], ['Save', 'pri', function () {
        var nd = q('#m-due').value, tx = q('#m-txt').value.trim(); if (!nd || !tx) { toast('New date and remark required', 1); return; } if (toDate(nd) < new Date()) { toast('Date is in the past', 1); return; }
        closeModal(); P(function (f) { f.delays.push({ old_deadline: f.due, new_deadline: nd, remarks: tx, reviewed_by: S.me.user, reviewed_by_name: S.me.name, reviewed_on: fDT(nowLocal()) }); addUpd(f, 'System', 'Deadline ' + fDT(f.due) + ' → ' + fDT(nd) + ': ' + tx); f.due = nd; }, 'Deadline updated');
      }]]); return;
    }
    if (act === 'pri') {
      modal('Change priority — ' + esc(dispNo(t)), '<div class="pg" id="m-pri">' + PRI_KEYS.map(function (k) { return '<button class="pb ' + (t.pri === k ? 'on' : '') + '" data-mp="' + k + '" data-p="' + k + '"><span class="pn-num">' + PRI_N(k) + '</span>' + esc(PRI_L(k)) + '<small>' + esc(PRI_H(k)) + '</small></button>'; }).join('') + '</div><label class="tg" style="margin-top:10px"><input type="checkbox" id="m-reorder" checked> Re-position in queue by new priority</label>', [['Cancel', '', closeModal], ['Save', 'pri', function () {
        var sel = q('#m-pri .pb.on'); if (!sel) return; var np = sel.dataset.mp, re = q('#m-reorder').checked; closeModal();
        persist(id, function (f) { addUpd(f, 'System', 'Priority ' + PRI_N(f.pri) + ' → ' + PRI_N(np) + ' ' + PRI_L(np)); f.pri = np; if (re) f.qk = placement(f.assignee, np, false, t.id).qk; }, 'Priority updated').then(function () { return syncQueue(t.assignee).then(function () { render(); refreshOpen(); }); }).catch(function () { });
      }]]); return;
    }
    if (act === 'top') { var l = queueOf(t.assignee).map(function (x) { return x.id; }).filter(function (x) { return x !== id; }); l.unshift(id); return setOrder(t.assignee, l).then(function () { P(function (f) { f.qk = findTask(id) ? findTask(id).qk : f.qk; addUpd(f, 'System', 'Moved to queue #1 by ' + S.me.name); }, 'Moved to #1'); }); }
    if (act === 'reassign') {
      S._ra = null;
      modal('Reassign — ' + esc(dispNo(t)), '<div class="fld"><label class="lbl">New assignee</label><div class="picker"><input id="m-ra" placeholder="Type name…" autocomplete="off"><div class="pres" id="m-ra-res"></div></div><div id="m-ra-sel" class="hint" style="margin-top:5px"></div></div><div class="fld" style="margin-top:8px"><label class="lbl">Reason</label><textarea id="m-txt"></textarea></div>', [['Cancel', '', closeModal], ['Reassign', 'pri', function () {
        var nu = S._ra, tx = q('#m-txt').value.trim(), old = t.assignee; if (!nu) { toast('Pick a person', 1); return; } closeModal();
        var pl = placement(nu, t.pri, false);
        persist(id, function (f) { addUpd(f, 'System', 'Reassigned ' + personName(f.assignee) + ' → ' + personName(nu) + (tx ? ': ' + tx : '')); f.qk = pl.qk; f.status = 'Open'; })
          .then(function () { return API.save('ToDo', id, { allocated_to: nu }); })
          .then(function () { var x = findTask(id); x.assignee = nu; enrich(x); return syncQueue(old).then(function () { return syncQueue(nu); }).then(function () { toast('Reassigned'); render(); refreshOpen(); showDispatch([x], mod('wa'), 'new'); }); }).catch(function (e) { toast(errMsg(e), 1); });
      }]]);
      q('#m-ra').addEventListener('input', function () { pickerResults('m-ra', 'm-ra-res', [t.assignee], function (u) { S._ra = u; q('#m-ra-sel').innerHTML = 'Selected: <b>' + esc(personName(u)) + '</b> · ' + queueOf(u).length + ' open'; }); });
      return;
    }
    if (act === 'notify') {
      var targets = t.grp ? t.grp.members.map(function (u) { return S.tasks.filter(function (x) { return x.mid === t.mid && x.assignee === u; })[0]; }).filter(function (x) { return x && !isClosed(x); }) : [t];
      modal('Remind', '<div class="bn a">Reminder for <b>' + esc(dispNo(t) + ' — ' + t.title) + '</b></div>' + (mod('wa') ? targets.map(function (x) { return waRow(x.assignee, taskMsg(x, 'reminder'), dispNo(x)); }).join('') : ''), (mod('email') ? [['✉️ Send Email', 'blue', function () { closeModal(); sendEmails(targets, 'reminder').then(function () { toast('Email sent'); }); P(function (f) { addUpd(f, 'System', 'Email reminder sent by ' + S.me.name); }); }]] : []).concat([['Close', '', closeModal]]), true);
    }
  }
  function manageQueue(u) {
    var draw = function () {
      var l = queueOf(u);
      return '<div class="hint" style="margin-bottom:6px">⤒ = make #1, ▲▼ = move. #1 is worked first. Saved instantly.</div>' + (l.map(function (t, i) { return '<div class="qi"><span class="qn ' + (i === 0 ? 'q1' : '') + '">#' + (i + 1) + '</span><div class="pi"><div class="pn">' + esc(dispNo(t)) + ' — ' + esc(t.title) + grpTag(t) + '</div><div class="pm">Due ' + fDT(t.due) + ' · ' + esc(t.status) + '</div></div>' + priPill(t.pri) + '<div class="row" style="flex-wrap:nowrap">' + (canManage(t) ? '<button class="btn sm" data-mv="top" data-id="' + esc(t.id) + '" ' + (i === 0 ? 'disabled' : '') + '>⤒</button><button class="btn sm" data-mv="up" data-id="' + esc(t.id) + '" ' + (i === 0 ? 'disabled' : '') + '>▲</button><button class="btn sm" data-mv="down" data-id="' + esc(t.id) + '" ' + (i === l.length - 1 ? 'disabled' : '') + '>▼</button>' : '<span class="tag">not yours</span>') + '</div></div>'; }).join('') || '<div class="empty"><b>No open tasks</b></div>');
    };
    var bindMq = function () {
      qa('[data-mv]', q('#modal')).forEach(function (bt) {
        bt.addEventListener('click', function () {
          var ids = queueOf(u).map(function (x) { return x.id; }), i = ids.indexOf(bt.dataset.id);
          if (bt.dataset.mv === 'top') { ids.splice(i, 1); ids.unshift(bt.dataset.id); } else { var j = bt.dataset.mv === 'up' ? i - 1 : i + 1, tmp = ids[j]; ids[j] = ids[i]; ids[i] = tmp; }
          setOrder(u, ids).then(function () { q('#mq-body').innerHTML = draw(); bindMq(); toast('Queue updated'); });
        });
      });
    };
    modal('Manage queue — ' + esc(personName(u)), '<div id="mq-body">' + draw() + '</div>', [['Auto-sort by priority', '', function () {
      var ids = queueOf(u).sort(function (a, b) { return PRI_W(a.pri) - PRI_W(b.pri) || (a.created > b.created ? 1 : -1); }).map(function (x) { return x.id; });
      setOrder(u, ids).then(function () { q('#mq-body').innerHTML = draw(); bindMq(); toast('Sorted by priority'); });
    }], ['Done', 'pri', closeModal]], true);
    bindMq();
  }

  /* ================================================================
     TICKETS
  ================================================================ */
  function resetTForm() { var mp = person(S.me.user || ''); S.tform = { branch: (mp && mp.branch) || 'Head Office', cat: '', issue: '', other: '', emp: '', tag: '', cc: [], pri: '', details: '', wa: true, email: true }; S.tFiles = []; }
  function suggestResolver(cat) {
    if (S.cfg.resolvers[cat]) return S.cfg.resolvers[cat];
    var s = CATEGORY_TAG_TO_SUGGEST[cat]; if (!s) return '';
    var m = S.people.filter(function (p) { return p.login && (p.name.toLowerCase().indexOf(s) > -1 || p.user.toLowerCase().indexOf(s) > -1); })[0];
    return m ? m.user : '';
  }
  function renderRaise() {
    var f = S.tform, issues = tIssues(f.cat), tp = f.tag ? person(f.tag) || { name: f.tag } : null;
    q('#view').innerHTML = '<div class="tk2"><div class="card"><div class="ch">✚ Raise New Ticket<span class="sp">' + hb('t_raise') + '</span></div><div class="cb">' +
      '<div class="grid g3"><div class="fld"><label class="lbl">Raised by</label><input readonly value="' + esc(S.me.name) + '"></div><div class="fld"><label class="lbl">Branch *</label><select id="k-branch">' + allBranches().map(function (b) { return '<option ' + (f.branch === b ? 'selected' : '') + '>' + esc(b) + '</option>'; }).join('') + '</select></div>' +
      '<div class="fld"><label class="lbl">Priority * (SLA)</label><div class="pg" style="grid-template-columns:repeat(3,1fr)" id="k-pri">' + TK_PRI.map(function (p) { return '<button class="pb ' + (f.pri === p ? 'on' : '') + '" data-kp="' + p + '" data-p="' + p + '" style="padding:3px">' + p + '<small>' + (SLA(p) < 48 ? SLA(p) + ' h' : Math.round(SLA(p) / 24) + ' days') + '</small></button>'; }).join('') + '</div></div></div>' +
      '<div class="grid g2" style="margin-top:9px"><div class="fld"><label class="lbl">Issue category *</label><select id="k-cat">' + optList(tCats(), f.cat, 'Select category') + '</select></div><div class="fld"><label class="lbl">Specific issue *</label><select id="k-issue">' + optList(issues, f.issue, f.cat ? 'Select issue' : 'Select category first') + '</select></div></div>' +
      (f.issue === 'Other' ? '<div class="fld" style="margin-top:9px"><label class="lbl">Describe the issue *</label><input id="k-other" value="' + esc(f.other) + '" maxlength="200"></div>' : '') +
      (EMPLOYEE_INVOLVED_ISSUES.indexOf(f.issue) > -1 ? '<div class="fld" style="margin-top:9px"><label class="lbl">Employee involved *</label><select id="k-emp">' + optList(S.people.map(function (p) { return p.name; }), f.emp, 'Select employee') + '</select></div>' : '') +
      '<div class="grid g2" style="margin-top:9px"><div class="fld"><label class="lbl">Tag to resolver *</label><div class="picker"><input id="k-tag" placeholder="' + (tp ? esc(tp.name) + ' — type to change' : 'Type name…') + '" autocomplete="off"><div class="pres" id="k-tag-res"></div></div></div>' +
      '<div class="fld"><label class="lbl">CC (optional)</label><div class="picker"><input id="k-cc" placeholder="Type name to add CC…" autocomplete="off"><div class="pres" id="k-cc-res"></div></div></div></div>' +
      '<div class="chips" style="margin-top:5px">' + (tp ? '<span class="chip on">Resolver: ' + esc(tp.name) + '</span>' : '') + f.cc.map(function (u) { return '<span class="chip sel">CC: ' + esc(personName(u)) + ' <span class="x" data-uncc2="' + esc(u) + '">×</span></span>'; }).join('') + '</div>' +
      '<div class="fld" style="margin-top:9px"><label class="lbl">Issue details *</label><textarea id="k-details" placeholder="What happened, since when, what you already tried…">' + esc(f.details) + '</textarea></div>' +
      '<div class="row" style="margin-top:9px;gap:14px"><div class="drop" id="k-drop" style="flex:1">📎 Attach photos / screenshots (max 5 MB)</div>' + (mod('wa') ? '<label class="tg"><input type="checkbox" id="k-wa" ' + (f.wa ? 'checked' : '') + '> 🟢 WhatsApp resolver</label>' : '') + (mod('email') ? '<label class="tg"><input type="checkbox" id="k-email" ' + (f.email ? 'checked' : '') + '> ✉️ Email</label>' : '') + '</div>' +
      '<div class="chips" style="margin-top:5px">' + S.tFiles.map(function (fl, i) { return '<span class="chip sel">📄 ' + esc(fl.name) + ' <span class="x" data-untf="' + i + '">×</span></span>'; }).join('') + '</div>' +
      '<div class="row" style="margin-top:10px"><button class="btn pri lg" data-act="tk-submit">✓ Submit Ticket</button><button class="btn" data-act="tk-reset">Clear</button></div></div></div>' +
      '<div class="side"><div class="card"><div class="ch">Resolver &amp; my recent tickets</div><div class="cb">' +
      (tp ? '<div class="sc"><div class="av">' + initials(tp.name) + '</div><div class="pi"><div class="pn">' + esc(tp.name) + '</div><div class="pm">' + esc([tp.desig, tp.branch].filter(Boolean).join(' · ')) + '</div></div>' + phHtml(tp, true) + '<span class="tag">' + S.tickets.filter(function (x) { return x.tag === f.tag && tkActive(x); }).length + ' open</span></div>' : '<div class="hint">Pick a category — the default resolver is filled in automatically.</div>') +
      '<div class="sub">My recent tickets</div>' + (S.tickets.filter(function (x) { return x.raiser === S.me.user; }).slice(0, 6).map(function (x) { return '<div class="qi" style="padding:5px 0;cursor:pointer" data-otk="' + esc(x.id) + '"><div class="pi"><div class="tl1" style="max-width:none">' + esc(x.issue || x.subject) + '</div><div class="pm">' + esc(x.id) + ' · ' + fD(x.created) + '</div></div>' + tkPill(x) + '</div>'; }).join('') || '<div class="hint">None yet</div>') +
      '</div></div></div></div>';
  }
  function submitTicket() {
    if (guard()) return;
    var f = S.tform, e = [];
    if (!f.cat) e.push('Select category'); if (!f.issue) e.push('Select specific issue');
    if (f.issue === 'Other' && !f.other.trim()) e.push('Describe the issue');
    if (EMPLOYEE_INVOLVED_ISSUES.indexOf(f.issue) > -1 && !f.emp) e.push('Select employee involved');
    if (!f.tag) e.push('Select resolver'); if (!f.pri) e.push('Select priority'); if (!f.details.trim()) e.push('Write issue details');
    if (e.length) { modal('⚠ Please complete the ticket', '<ul style="margin:0;padding-left:18px">' + e.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>', [['OK', 'pri', closeModal]]); return; }
    modalBusy('Submitting ticket…');
    var tk = { meta: {}, branch: f.branch, cat: f.cat, issue: f.issue, other: f.other.trim(), emp: f.emp, tag: f.tag, cc: f.cc.slice(), details: f.details.trim(), status: 'Open', updates: [{ id: uid(), at: nowLocal(), by: S.me.user, type: 'System', text: 'Ticket raised · ' + f.pri + ' · resolver ' + personName(f.tag) }], resolvedOn: '', closedOn: '' };
    var doc = { doctype: 'Issue', subject: f.cat + ' - ' + f.issue, description: tkDesc(tk), priority: f.pri, status: 'Open', raised_by: S.me.user };
    var wa = f.wa && mod('wa'), em = f.email && mod('email');
    API.create(doc).then(function (d) {
      var r = {}; Object.keys(doc).forEach(function (k) { r[k] = doc[k]; }); Object.keys(d || {}).forEach(function (k) { r[k] = d[k]; });
      var row = normTicket(r); S.tickets.unshift(row);
      return S.tFiles.reduce(function (p, fl) { return p.then(function () { return API.upload('Issue', row.id, fl).then(function (x) { (S.tfiles[row.id] = S.tfiles[row.id] || []).push(x); }).catch(function (x) { toast(String(x), 1); }); }); }, Promise.resolve()).then(function () { return row; });
    }).then(function (row) {
      var msg = tkMsg(row, 'new');
      if (em) API.email([row.tag], row.cc, '[Ticket ' + row.pri + '] ' + row.id + ' — ' + row.subject, mailHtml('New Ticket', msg), 'Issue', row.id).catch(function () { });
      resetTForm(); render();
      modal('✅ Ticket ' + esc(row.id) + ' submitted', '<div class="bn g">Tagged to <b>' + esc(personName(row.tag)) + '</b>. SLA: ' + fDT(localStr(tkSla(row))) + '.</div>' + (wa ? waRow(row.tag, msg, 'Resolver') : ''), [['Done', 'pri', closeModal]]);
    }).catch(function (x) { closeModal(); toast('Ticket not saved: ' + errMsg(x), 1); });
  }
  function tkMsg(tk, kind) {
    return (kind === 'new' ? '🎫 *LIFE Clinics — New Ticket*' : '⏰ *LIFE Clinics — Ticket Reminder*') + '\n\n*Ticket:* ' + tk.id + '\n*Priority:* ' + tk.pri + '   *SLA:* ' + fDT(localStr(tkSla(tk) || new Date())) + '\n*Branch:* ' + tk.branch + '\n*Category:* ' + tk.cat + '\n*Issue:* ' + tk.issue + (tk.other ? ' — ' + tk.other : '') + '\n\n' + tk.details.slice(0, 600) + '\n\n*Raised by:* ' + personName(tk.raiser) + '\n\nOpen: ' + location.origin + location.pathname;
  }
  function tApply(list) {
    var f = S.tf, s = f.q.toLowerCase(), me = S.me.user;
    return list.filter(function (t) {
      if (s && (t.id + ' ' + t.subject + ' ' + t.details + ' ' + personName(t.raiser) + ' ' + personName(t.tag) + ' ' + t.branch).toLowerCase().indexOf(s) < 0) return false;
      if (f.pri && t.pri !== f.pri) return false; if (f.cat && t.cat !== f.cat) return false; if (f.branch && t.branch !== f.branch) return false; if (f.tag && t.tag !== f.tag) return false;
      var st = f.status;
      if (st === 'Active' && !tkActive(t)) return false; if (st === 'Breach' && !tkBreach(t)) return false; if (st === 'HighOpen' && !(tkActive(t) && t.pri === 'High')) return false;
      if (st === 'Mine' && !(t.tag === me && tkActive(t))) return false; if (TK_STATUSES.indexOf(st) > -1 && t.status !== st) return false;
      return true;
    }).sort(function (a, b) { return (tkActive(b) - tkActive(a)) || (tkBreach(b) - tkBreach(a)) || (TK_PRI.indexOf(a.pri) - TK_PRI.indexOf(b.pri)) || (b.created > a.created ? 1 : -1); });
  }
  function tRow(t) {
    var nf = (S.tfiles[t.id] || []).length;
    return '<tr class="' + (tkBreach(t) ? 'od' : '') + '" data-otk="' + esc(t.id) + '" style="cursor:pointer">' + TD('Ticket', '<span class="tno">' + esc(t.id) + '</span><div class="pm">📎' + nf + ' 💬' + t.updates.filter(function (u) { return u.type !== 'System'; }).length + '</div>') +
      TD('Issue', '<span class="tl1" title="' + esc(t.details) + '">' + esc(t.issue || t.subject) + '</span><div class="pm">' + esc(t.cat) + '</div>') + TD('Branch', esc(t.branch || '—')) +
      TD('Raised by', '<div class="pn">' + esc(personName(t.raiser)) + '</div>' + phHtml(t.raiser, true)) + TD('Resolver', '<div class="pn">' + esc(personName(t.tag)) + '</div>' + phHtml(t.tag, true)) +
      TD('Priority', '<span class="pill p-' + t.pri + '">' + t.pri + '</span>') + TD('Raised on', fDT(t.created)) + TD('SLA', tkSlaHtml(t)) + TD('Status', tkPill(t), 'wr') + '</tr>';
  }
  function tTable(list) { return '<div class="card"><div class="tw"><table class="tt">' + cols([11, 20, 9, 14, 14, 7, 9, 7, 9]) + '<thead><tr><th>Ticket</th><th>Issue</th><th>Branch</th><th>Raised by</th><th>Resolver</th><th>Priority</th><th>Raised on</th><th>SLA</th><th>Status</th></tr></thead><tbody>' + (list.length ? list.slice(0, 300).map(tRow).join('') : '<tr><td colspan="9"><div class="empty"><b>No tickets</b></div></td></tr>') + '</tbody></table></div>' + (list.length > 300 ? '<div class="pager">Showing 300 of ' + list.length + ' — narrow filters</div>' : '') + '</div>'; }
  function renderTAll() {
    var v = tVisible(), f = S.tf, list = tApply(v);
    var sts = [['Active', 'Active (not resolved/closed)'], ['Breach', 'SLA breached'], ['HighOpen', 'High open'], ['Mine', 'Tagged to me']].concat(TK_STATUSES.map(function (s) { return [s, s]; }));
    q('#view').innerHTML = '<div class="card"><div class="cb"><div class="fbar">' +
      '<div class="fld fq"><label class="lbl">Search</label><input id="tf-q" value="' + esc(f.q) + '" placeholder="Ticket no, issue, person, branch…"></div>' +
      '<div class="fld"><label class="lbl">Status</label><select data-tf="status">' + optList(sts, f.status, 'All') + '</select></div>' +
      '<div class="fld"><label class="lbl">Priority</label><select data-tf="pri">' + optList(TK_PRI, f.pri) + '</select></div>' +
      '<div class="fld"><label class="lbl">Category</label><select data-tf="cat">' + optList(Object.keys(S.cfg.tCats), f.cat) + '</select></div>' +
      '<div class="fld"><label class="lbl">Branch</label><select data-tf="branch">' + optList(uniq(v.map(function (t) { return t.branch; })).sort(), f.branch) + '</select></div>' +
      '<div class="fld"><label class="lbl">Resolver</label><select data-tf="tag">' + optList(uniq(v.map(function (t) { return t.tag; })).map(function (u) { return [u, personName(u)]; }), f.tag) + '</select></div></div>' +
      '<div class="vbar"><span class="hint">' + list.length + ' tickets</span><span style="flex:1"></span>' + (can('export') ? '<button class="btn sm" data-act="tk-export">⬇ CSV</button>' : '') + hb('t_all') + '</div></div></div>' + tTable(list);
  }
  function renderTMy() {
    var me = S.me.user, v = S.tickets;
    var sets = { tagged: v.filter(function (t) { return t.tag === me; }), raised: v.filter(function (t) { return t.raiser === me || t.owner === me; }), close: v.filter(function (t) { return (t.raiser === me || t.owner === me) && t.status === 'Resolved'; }), cc: v.filter(function (t) { return t.cc.indexOf(me) > -1; }) };
    var tabs = [['tagged', 'Tagged to Me', sets.tagged.filter(tkActive).length], ['close', 'Awaiting My Close', sets.close.length], ['raised', 'Raised by Me', sets.raised.length], ['cc', 'CC to Me', sets.cc.length]];
    var list = sets[S.tmyTab].slice().sort(function (a, b) { return (tkActive(b) - tkActive(a)) || (b.created > a.created ? 1 : -1); });
    q('#view').innerHTML = '<div class="stabs">' + tabs.map(function (x) { return '<button class="btn ' + (S.tmyTab === x[0] ? 'pri' : '') + '" data-tmy="' + x[0] + '">' + x[1] + ' <span class="tag">' + x[2] + '</span></button>'; }).join('') + hb('t_my') + '</div>' + tTable(list);
  }
  function findTk(id) { return S.tickets.filter(function (t) { return t.id === id; })[0]; }
  function openTicket(id) {
    var tk = findTk(id); if (!tk) return; S.openTicket = id; S.openTask = null;
    var me = S.me.user, isRes = tk.tag === me, isRai = tk.raiser === me || tk.owner === me, mgr = can('t_manage'), files = S.tfiles[tk.id] || [], A = [];
    var b = function (cls, a, txt) { A.push('<button class="btn ' + cls + '" data-tka="' + a + '" data-id="' + esc(tk.id) + '">' + txt + '</button>'); };
    if ((isRes || mgr) && tkActive(tk)) b('pri', 'resolve', '✓ Mark Resolved');
    if ((isRai || mgr) && tk.status === 'Resolved') { b('pri', 'close', '✓ Satisfied – Close'); b('red', 'reopen', '↺ Not satisfied – Reopen'); }
    if ((isRai || mgr) && tk.status === 'Closed') b('red', 'reopen', '↺ Reopen');
    if ((mgr || isRai) && tkActive(tk)) b('', 'retag', '⇄ Change resolver');
    if (mgr && tkActive(tk)) { b('', 'tpri', '⚑ Priority'); b('', tk.status === 'On Hold' ? 'unhold' : 'hold', tk.status === 'On Hold' ? '▶ Resume' : '⏸ Hold'); }
    if (tkActive(tk) && (isRai || mgr) && mod('wa')) b('wa', 'remind', '🔔 Remind resolver');
    var h = '<div class="dh"><span class="qn" style="min-width:40px;height:40px;font-size:18px;background:#fff;color:var(--g800)">🎫</span><div class="pi"><div style="font-size:11.5px;opacity:.85">' + esc(tk.id) + ' · ' + esc(tk.cat) + '</div><div style="font-size:16px;font-weight:700" class="nw">' + esc(tk.issue || tk.subject) + '</div><div class="row" style="margin-top:3px"><span class="pill p-' + tk.pri + '">' + tk.pri + '</span>' + tkPill(tk) + '</div></div>' + hb('t_drawer') + '<button class="x" data-act="close-drawer">×</button></div>' +
      '<div class="db">' + (tkBreach(tk) ? '<div class="bn r">⚠ SLA breached by ' + dur(new Date() - tkSla(tk)) + '</div>' : '') + (tk.status === 'Resolved' && isRai ? '<div class="bn a">Resolver marked this resolved. Close if satisfied, or Reopen with reason.</div>' : '') +
      '<div class="ig">' + info('Branch', tk.branch || '—') + info('Raised by', personName(tk.raiser)) + info('Raiser mobile', phHtml(tk.raiser), true) + info('Raised on', fDT(tk.created)) +
      info('Resolver', personName(tk.tag)) + info('Resolver mobile', phHtml(tk.tag), true) + info('SLA', tkSla(tk) ? fDT(localStr(tkSla(tk))) : '—') + info('SLA status', tkSlaHtml(tk), true) +
      info('CC', tk.cc.map(personName).join(', ') || '—') + info('Employee involved', tk.emp || '—') + info('Other', tk.other || '—') + info('Files', files.length) + '</div>' +
      '<div class="sub" style="margin-top:10px">Issue details</div><div class="dbox">' + esc(tk.details || '—') + '</div>' +
      '<div class="sub" style="margin-top:10px">Attachments</div><div class="chips">' + (files.length ? files.map(function (fl) { return '<a class="chip" target="_blank" href="' + esc(fl.file_url) + '">📄 ' + esc(fl.file_name || 'file') + '</a>'; }).join('') : '<span class="hint">No files</span>') + '</div>' +
      '<div class="sub" style="margin-top:10px">Updates (' + tk.updates.length + ')</div>' +
      (tk.status !== 'Closed' ? '<div class="card" style="margin-bottom:8px"><div class="cb"><div class="row" style="flex-wrap:nowrap"><textarea id="k-utext" style="min-height:40px;height:40px" placeholder="Write an update / reply…"></textarea><button class="btn sm" data-act="tupd-file" style="height:40px">📎</button><button class="btn pri" data-act="tk-post" style="height:40px">Post</button></div><div class="hint" id="d-ufiles"></div></div></div>' : '') +
      '<div class="tl">' + (tk.updates.length ? tk.updates.slice().reverse().map(updHtml).join('') : '<div class="hint">No updates yet</div>') + '</div></div>' +
      '<div class="da">' + (A.join('') || '<span class="hint">View only.</span>') + '</div>';
    showDrawer(h); S.updFiles = [];
  }
  function tPersist(id, mutate, okMsg) {
    if (guard()) return Promise.reject('preview');
    return API.get('Issue', id).then(function (raw) {
      var fresh = normTicket(raw); mutate(fresh);
      var fields = { description: tkDesc(fresh), status: tkStatusField(fresh.status) };
      if (fresh._pri) fields.priority = fresh.pri;
      return API.save('Issue', id, fields).then(function () {
        raw.description = fields.description; raw.status = fields.status; if (fields.priority) raw.priority = fields.priority;
        var nt = normTicket(raw), i = S.tickets.indexOf(findTk(id)); if (i > -1) S.tickets[i] = nt;
        if (okMsg) toast(okMsg); render(); refreshOpen(); return nt;
      });
    }).catch(function (e) { if (e !== 'preview') toast('Not saved: ' + errMsg(e), 1); throw e; });
  }
  function tkAction(a, id) {
    if (guard()) return;
    var tk = findTk(id), P = function (fn, m) { tPersist(id, fn, m).catch(function () { }); };
    if (a === 'resolve') return promptBox('Mark resolved', 'Resolution remarks — what was done.', 'Remarks…', function (x) { P(function (f) { f.status = 'Resolved'; f.resolvedOn = nowLocal(); addUpd(f, 'Resolved', x); }, 'Marked resolved'); });
    if (a === 'close') return promptBox('Close ticket', 'Optional feedback.', 'Feedback (optional)…', function (x) { P(function (f) { f.status = 'Closed'; f.closedOn = nowLocal(); addUpd(f, 'Closed', x || 'Accepted and closed by raiser'); }, 'Ticket closed'); }, true);
    if (a === 'reopen') return promptBox('Reopen ticket', 'Why are you not satisfied?', 'Reason…', function (x) { P(function (f) { f.status = 'Reopened'; addUpd(f, 'Reopened', x); }, 'Reopened'); });
    if (a === 'hold') return promptBox('Put on hold', 'Reason.', 'Reason…', function (x) { P(function (f) { f.status = 'On Hold'; addUpd(f, 'System', 'On hold: ' + x); }, 'On hold'); });
    if (a === 'unhold') return P(function (f) { f.status = 'Open'; addUpd(f, 'System', 'Resumed'); }, 'Resumed');
    if (a === 'tpri') return modal('Change ticket priority', '<div class="pg" style="grid-template-columns:repeat(3,1fr)" id="m-tp">' + TK_PRI.map(function (p) { return '<button class="pb ' + (tk.pri === p ? 'on' : '') + '" data-mp="' + p + '" data-p="' + p + '">' + p + '</button>'; }).join('') + '</div>', [['Cancel', '', closeModal], ['Save', 'pri', function () { var s = q('#m-tp .pb.on'); closeModal(); if (s) P(function (f) { addUpd(f, 'System', 'Priority ' + f.pri + ' → ' + s.dataset.mp); f.pri = s.dataset.mp; f._pri = 1; }, 'Priority updated'); }]]);
    if (a === 'retag') {
      S._ra = null;
      modal('Change resolver', '<div class="picker"><input id="m-ra" placeholder="Type name…" autocomplete="off"><div class="pres" id="m-ra-res"></div></div><div id="m-ra-sel" class="hint" style="margin-top:5px"></div>', [['Cancel', '', closeModal], ['Save', 'pri', function () { var nu = S._ra; if (!nu) { toast('Pick a person', 1); return; } closeModal(); P(function (f) { addUpd(f, 'System', 'Resolver ' + personName(f.tag) + ' → ' + personName(nu)); f.tag = nu; }, 'Resolver changed'); }]]);
      q('#m-ra').addEventListener('input', function () { pickerResults('m-ra', 'm-ra-res', [tk.tag], function (u) { S._ra = u; q('#m-ra-sel').innerHTML = 'Selected: <b>' + esc(personName(u)) + '</b>'; }); });
      return;
    }
    if (a === 'remind') return modal('Remind resolver', waRow(tk.tag, tkMsg(tk, 'remind'), 'Resolver'), [['Close', '', closeModal]]);
  }
  function tkPost() {
    if (guard()) return;
    var id = S.openTicket, x = q('#k-utext').value.trim(); if (!x) { toast('Write something first', 1); return; }
    uploadPending('Issue', id, S.tfiles).then(function (files) { return tPersist(id, function (f) { addUpd(f, 'Update', x, files); }, 'Update posted'); }).catch(function () { });
  }

  /* ================================================================
     CONTROL PANEL (admins only)
  ================================================================ */
  function sw(attr, on) { return '<label class="sw"><input type="checkbox" ' + attr + ' ' + (on ? 'checked' : '') + '><span></span></label>'; }
  function cpDirty() { return JSON.stringify(S.draft) !== JSON.stringify(S.cfg); }
  function renderCPanel() {
    if (!S.me.admin || S.me.preview) { q('#view').innerHTML = '<div class="card"><div class="empty"><b>Admins only</b></div></div>'; return; }
    if (!S.draft) S.draft = clone(S.cfg);
    var d = S.draft, roles = Object.keys(d.roles);
    var tabs = [['mods', '🧩 Modules'], ['roles', '🛡 Roles & Rights'], ['users', '👤 Users & Admins'], ['tmast', '📋 Task Masters'], ['kmast', '🎫 Ticket Masters'], ['phone', '🔒 Phone Privacy']];
    var h = '<div class="cpbar">⚙ <b>Control Panel</b><span class="hint" style="margin:0">' + (S.cfg.savedOn ? 'Last saved ' + fDT(S.cfg.savedOn) + ' by ' + esc(personName(S.cfg.savedBy)) : 'Not saved yet — defaults in use') + '</span><span style="flex:1"></span>' + (cpDirty() ? '<span class="tag a">Unsaved changes</span><button class="btn sm" data-act="cp-discard">Discard</button>' : '') + '<button class="btn pri" data-act="cp-save">💾 Save Control Panel</button>' + hb('cpanel') + '</div>';
    h += '<div class="stabs">' + tabs.map(function (t) { return '<button class="btn ' + (S.cpTab === t[0] ? 'pri' : '') + '" data-cpt="' + t[0] + '">' + t[1] + '</button>'; }).join('') + '</div>';
    var c = S.cpTab;
    if (c === 'mods') {
      h += '<div class="card"><div class="ch">Modules &amp; features — switch on / off for everyone</div><div class="cb"><div class="grid g3">' + MODULES.map(function (m) { return '<div class="tgl"><div style="min-width:0"><div class="tt2">' + esc(m[1]) + '</div><div class="ds">' + esc(m[2]) + '</div></div>' + sw('data-cpmod="' + m[0] + '"', d.modules[m[0]]) + '</div>'; }).join('') + '</div><div class="hint" style="margin-top:8px">Admins always keep access to Control Panel even if Tasks is switched off.</div></div></div>';
    }
    if (c === 'roles') {
      var groups = uniq(PERMS.map(function (p) { return p[2]; }));
      h += '<div class="card"><div class="ch">Roles &amp; rights — who can see / do what<span class="sp"><input id="cp-newrole" placeholder="New role name" style="height:31px;width:170px;padding:3px 8px;font-size:12.5px"><button class="btn sm" data-act="cp-addrole">＋ Add role</button></span></div><div class="tw"><table class="tt cp-mat">' + cols([34].concat(roles.map(function () { return Math.floor(66 / roles.length); }))) +
        '<thead><tr><th>Permission</th>' + roles.map(function (r) { return '<th>' + esc(r) + (r !== 'Admin' && r !== 'Employee' ? ' <button class="lock" data-cpdelrole="' + esc(r) + '" title="Delete role">✕</button>' : '') + '</th>'; }).join('') + '</tr></thead><tbody>' +
        '<tr><td><b>Data scope</b><div class="pm">Which tasks the role can see</div></td>' + roles.map(function (r) { return '<td><select data-rs="' + esc(r) + '" style="height:32px;font-size:12px;padding:2px 6px" ' + (r === 'Admin' ? 'disabled' : '') + '>' + SCOPES.map(function (s) { return '<option value="' + s[0] + '" ' + (d.roles[r].scope === s[0] ? 'selected' : '') + '>' + s[0].toUpperCase() + '</option>'; }).join('') + '</select></td>'; }).join('') + '</tr>' +
        groups.map(function (g) { return '<tr><td colspan="' + (roles.length + 1) + '" style="background:#fbf7e9;font-weight:700;color:#7a5600;font-size:11px;letter-spacing:.5px;text-transform:uppercase">' + esc(g) + '</td></tr>' + PERMS.filter(function (p) { return p[2] === g; }).map(function (p) { return '<tr><td title="' + esc(p[1]) + '">' + esc(p[1]) + '</td>' + roles.map(function (r) { return '<td><input type="checkbox" data-rp="' + esc(r) + '|' + p[0] + '" ' + (d.roles[r][p[0]] ? 'checked' : '') + ' ' + (r === 'Admin' ? 'disabled' : '') + '></td>'; }).join('') + '</tr>'; }).join(''); }).join('') +
        '</tbody></table></div><div class="cb hint">Scope: OWN = mine / by me / CC / my groups · DEPT = my department · BRANCH = my branch · ALL = everything. Admin role always has everything.</div></div>';
    }
    if (c === 'users') {
      var s = S.cpq.toLowerCase(), ppl = S.people.filter(function (p) { return p.login && (!s || (p.name + ' ' + p.user + ' ' + p.desig + ' ' + p.branch).toLowerCase().indexOf(s) > -1); });
      var desigs = distinct('desig');
      h += '<div class="tk2" style="grid-template-columns:minmax(0,1.6fr) minmax(0,1fr)"><div class="card"><div class="ch">User → role<span class="sp"><input id="cp-q" value="' + esc(S.cpq) + '" placeholder="Search user…" style="height:31px;width:200px;padding:3px 8px;font-size:12.5px"></span></div><div class="tw" style="max-height:calc(100vh - 330px);overflow-y:auto"><table class="tt">' + cols([28, 20, 14, 20, 18]) + '<thead><tr><th>Employee</th><th>Designation</th><th>Branch</th><th>Role</th><th>Comes from</th></tr></thead><tbody>' +
        ppl.map(function (p) { var src = isAdmin(p.user) ? 'Admin (core)' : d.userRoles[p.user] ? 'Set directly' : 'Rule / default'; return '<tr>' + TD('Employee', '<div class="pn">' + esc(p.name) + '</div><div class="pm">' + esc(p.user) + '</div>') + TD('Designation', esc(p.desig || '—')) + TD('Branch', esc(p.branch || '—')) + TD('Role', '<select data-ur="' + esc(p.user) + '" style="height:32px;font-size:12px;padding:2px 6px" ' + (CORE_ADMINS.indexOf(p.user.toLowerCase()) > -1 ? 'disabled' : '') + '>' + optList(Object.keys(d.roles), d.userRoles[p.user] || '', '— auto —') + '</select>') + TD('From', '<span class="tag ' + (src === 'Set directly' ? 'g' : '') + '">' + src + '</span>') + '</tr>'; }).join('') + '</tbody></table></div></div>' +
        '<div><div class="card"><div class="ch">Designation rules</div><div class="cb">' + (d.desigRules || []).map(function (r, i) { return '<div class="row" style="flex-wrap:nowrap;margin-bottom:6px"><select data-dr="' + i + '|0" style="height:34px">' + optList(desigs, r[0], 'Designation') + '</select><span>→</span><select data-dr="' + i + '|1" style="height:34px">' + optList(Object.keys(d.roles), r[1], 'Role') + '</select><button class="btn sm red" data-cpdeldr="' + i + '">✕</button></div>'; }).join('') +
        '<button class="btn sm" data-act="cp-adddr">＋ Add rule</button><div class="sub" style="margin-top:12px">Default role (everyone else)</div><select id="cp-defrole">' + optList(Object.keys(d.roles), d.defaultRole, null) + '</select></div></div>' +
        '<div class="card"><div class="ch">Admins (full rights + Control Panel)</div><div class="cb"><div class="chips">' + CORE_ADMINS.filter(function (x) { return x !== 'administrator'; }).map(function (u) { return '<span class="chip on">⭐ ' + esc(personName(u)) + '</span>'; }).join('') + (d.admins || []).map(function (u) { return '<span class="chip sel">' + esc(personName(u)) + ' <span class="x" data-cpdeladm="' + esc(u) + '">×</span></span>'; }).join('') + '</div><div class="picker" style="margin-top:8px"><input id="cp-admin" placeholder="Add another admin…" autocomplete="off"><div class="pres" id="cp-admin-res"></div></div></div></div></div></div>';
    }
    if (c === 'tmast') {
      h += '<div class="rg"><div class="card"><div class="ch">Task categories<span class="sp"><input id="cp-newcat" placeholder="New category" style="height:31px;width:160px;padding:3px 8px;font-size:12.5px"><button class="btn sm" data-act="cp-addcat">＋ Add</button></span></div><div class="cb" style="max-height:calc(100vh - 330px);overflow:auto">' + d.categories.map(function (cat, i) { return '<div class="mitem ' + (cat.a ? '' : 'off') + '"><span class="mtx">' + esc(cat.n) + '</span>' + sw('data-cat="' + i + '"', cat.a) + '</div>'; }).join('') + '</div></div>' +
        '<div><div class="card"><div class="ch">Priority numbers &amp; labels</div><div class="cb">' + PRI_KEYS.map(function (k, i) { return '<div class="row" style="flex-wrap:nowrap;margin-bottom:6px"><span class="pill p-' + k + '" style="width:44px;justify-content:center">P' + (i + 1) + '</span><input data-pl="' + k + '" value="' + esc(d.pri[k].label) + '" style="width:140px;flex:none"><input data-ph="' + k + '" value="' + esc(d.pri[k].hint) + '"></div>'; }).join('') + '<div class="hint">Order is fixed: P1 is always worked before P2, P2 before P3 …</div></div></div>' +
        '<div class="card"><div class="ch">Reporting types</div><div class="cb">' + REPORT_DEF.map(function (r) { return '<div class="mitem ' + (d.reports[r.k] ? '' : 'off') + '"><span class="mtx">' + esc(r.label) + ' <span class="pm" style="display:inline">— ' + esc(r.d) + '</span></span>' + sw('data-rt="' + r.k + '"', d.reports[r.k]) + '</div>'; }).join('') + '</div></div></div></div>';
    }
    if (c === 'kmast') {
      var resPeople = S.people.filter(function (p) { return p.login; }).map(function (p) { return [p.user, p.name]; });
      h += '<div class="tk2" style="grid-template-columns:minmax(0,1.7fr) minmax(0,1fr)"><div class="card"><div class="ch">Ticket categories, issues &amp; default resolver<span class="sp"><input id="cp-newtc" placeholder="New category" style="height:31px;width:160px;padding:3px 8px;font-size:12.5px"><button class="btn sm" data-act="cp-addtc">＋ Add</button></span></div><div class="cb" style="max-height:calc(100vh - 330px);overflow:auto">' +
        Object.keys(d.tCats).map(function (cat) { var x = d.tCats[cat]; return '<details class="qg" style="padding:0" data-dc="' + esc(cat) + '" ' + ((S.cpOpen || {})[cat] ? 'open' : '') + '><summary class="qh" style="list-style:none"><b class="mtx">' + esc(cat) + '</b><span class="tag">' + x.issues.filter(function (i) { return i.a; }).length + ' issues</span><select data-res="' + esc(cat) + '" style="width:190px;height:31px;font-size:12px;padding:2px 6px" onclick="event.stopPropagation()">' + optList(resPeople, d.resolvers[cat] || '', 'Resolver: auto') + '</select>' + sw('data-tc="' + esc(cat) + '"', x.a) + '</summary><div class="cb">' + x.issues.map(function (iss, i) { return '<div class="mitem ' + (iss.a ? '' : 'off') + '"><span class="mtx">' + esc(iss.n) + '</span>' + sw('data-ti="' + esc(cat) + '|' + i + '"', iss.a) + '</div>'; }).join('') + '<div class="row" style="margin-top:6px;flex-wrap:nowrap"><input data-newissue="' + esc(cat) + '" placeholder="New issue under ' + esc(cat) + '"><button class="btn sm" data-cpaddissue="' + esc(cat) + '">＋ Add</button></div></div></details>'; }).join('') + '</div></div>' +
        '<div class="card"><div class="ch">SLA hours by priority</div><div class="cb">' + TK_PRI.map(function (p) { return '<div class="row" style="flex-wrap:nowrap;margin-bottom:6px"><span class="pill p-' + p + '" style="width:80px;justify-content:center">' + p + '</span><input type="number" min="1" data-sla="' + p + '" value="' + esc(d.sla[p]) + '" style="width:110px"><span class="hint">hours</span></div>'; }).join('') + '</div></div></div>';
    }
    if (c === 'phone') {
      var withPh = Object.keys(d.roles).filter(function (r) { return d.roles[r].phones; });
      h += '<div class="rg"><div class="card"><div class="ch">Mobile number masking</div><div class="cb">' +
        '<div class="tgl"><div><div class="tt2">Mask mobile numbers everywhere</div><div class="ds">Shows 98XXXXXX17 unless the role is allowed or the code is entered</div></div>' + sw('id="cp-mask"', d.phone.mask) + '</div>' +
        '<div class="grid g2" style="margin-top:10px"><div class="fld"><label class="lbl">Unlock lasts (minutes)</label><input type="number" min="1" max="480" id="cp-min" value="' + esc(d.phone.minutes) + '"></div><div class="fld"><label class="lbl">Unlock code status</label><input readonly value="' + (d.phone.codeHash ? 'Code is set ✔' : 'No code set') + '"></div></div>' +
        '<div class="sub" style="margin-top:12px">Set / change unlock code</div><div class="grid g2"><input type="password" id="cp-code1" placeholder="New code (min 4)" autocomplete="new-password"><input type="password" id="cp-code2" placeholder="Repeat code" autocomplete="new-password"></div>' +
        '<div class="row" style="margin-top:8px"><button class="btn pri sm" data-act="cp-setcode">Set code</button>' + (d.phone.codeHash ? '<button class="btn sm red" data-act="cp-clrcode">Remove code</button>' : '') + '</div><div class="hint">Only a fingerprint (hash) of the code is stored, never the code itself.</div></div></div>' +
        '<div class="card"><div class="ch">Who can always see numbers</div><div class="cb">' + (withPh.length ? withPh.map(function (r) { return '<span class="chip on" style="margin:0 5px 5px 0">' + esc(r) + '</span>'; }).join('') : '<span class="hint">No role</span>') + '<div class="hint" style="margin-top:8px">Change this in <b>Roles &amp; Rights</b> → “See mobile numbers unmasked”.</div><div class="bn a" style="margin-top:10px">Masking hides numbers on screen. The numbers still come from the Employee master, so for full protection also restrict Employee read permission in ERP.</div></div></div></div>';
    }
    q('#view').innerHTML = h;
  }
  function cpSave() {
    var d = S.draft; d.savedBy = S.realMe.user; d.savedOn = nowLocal();
    var html = '<!--LIFE_CPANEL:' + JSON.stringify(d).replace(/-->/g, '--\\u003e') + '-->\n<p><b>LIFE Task Management — Control Panel settings.</b> Do not edit by hand. Saved by ' + esc(S.realMe.name) + ' on ' + fDT(d.savedOn) + '.</p>';
    modalBusy('Saving Control Panel…');
    var isNew = !S.cfgNote;
    API.saveCfg(S.cfgNote, html).then(function (name) {
      S.cfgNote = name;
      var admins = uniq(CORE_ADMINS.concat(d.admins || [])).filter(function (u) { return u !== 'administrator' && u !== S.realMe.user; });
      return admins.reduce(function (p, u) { return p.then(function () { return API.share('Note', name, u, true).catch(function () { }); }); }, Promise.resolve());
    }).then(function () {
      S.cfg = clone(d); S.draft = clone(d);
      S.realMe = setMe(S.realMe.user, S.realMe.name, { image: S.realMe.image }); S.me = S.realMe;
      closeModal(); toast('Control Panel saved' + (isNew ? ' (settings note created)' : '')); renderHeader(); render();
    }).catch(function (e) { closeModal(); toast('Not saved: ' + errMsg(e), 1); });
  }
  function cpClick(el) {
    var d = S.draft, ds = el.dataset;
    if (ds.cpt) { S.cpTab = ds.cpt; render(); return true; }
    if (ds.cpdelrole) { if (!confirm('Delete role “' + ds.cpdelrole + '”? Users with it fall back to rules / default.')) return true; delete d.roles[ds.cpdelrole]; Object.keys(d.userRoles).forEach(function (u) { if (d.userRoles[u] === ds.cpdelrole) delete d.userRoles[u]; }); if (d.defaultRole === ds.cpdelrole) d.defaultRole = 'Employee'; render(); return true; }
    if (ds.cpdeldr != null) { d.desigRules.splice(+ds.cpdeldr, 1); render(); return true; }
    if (ds.cpdeladm) { d.admins = (d.admins || []).filter(function (u) { return u !== ds.cpdeladm; }); render(); return true; }
    if (ds.cpaddissue) { var inp = q('[data-newissue="' + ds.cpaddissue.replace(/"/g, '\\"') + '"]'), v = inp && inp.value.trim(); if (!v) return true; d.tCats[ds.cpaddissue].issues.push({ n: v, a: 1 }); render(); return true; }
    var a = ds.act;
    if (a === 'cp-save') { cpSave(); return true; }
    if (a === 'cp-discard') { S.draft = clone(S.cfg); render(); return true; }
    if (a === 'cp-addrole') { var n = q('#cp-newrole').value.trim(); if (!n || d.roles[n]) { toast(n ? 'Role exists' : 'Type a role name', 1); return true; } d.roles[n] = clone(d.roles.Employee || allPerms(0)); render(); return true; }
    if (a === 'cp-adddr') { d.desigRules.push(['', '']); render(); return true; }
    if (a === 'cp-addcat') { var c = q('#cp-newcat').value.trim(); if (!c) return true; if (d.categories.some(function (x) { return x.n.toLowerCase() === c.toLowerCase(); })) { toast('Already exists', 1); return true; } d.categories.push({ n: c, a: 1 }); render(); return true; }
    if (a === 'cp-addtc') { var t = q('#cp-newtc').value.trim(); if (!t || d.tCats[t]) return true; d.tCats[t] = { a: 1, issues: [{ n: 'Other', a: 1 }] }; render(); return true; }
    if (a === 'cp-setcode') {
      var c1 = q('#cp-code1').value, c2 = q('#cp-code2').value;
      if (c1.length < 4) { toast('Code must be at least 4 characters', 1); return true; } if (c1 !== c2) { toast('Codes do not match', 1); return true; }
      sha256(c1).then(function (h) { d.phone.codeHash = h; toast('Code set — click Save Control Panel'); render(); }); return true;
    }
    if (a === 'cp-clrcode') { d.phone.codeHash = ''; render(); return true; }
    return false;
  }
  function cpChange(t) {
    var d = S.draft; if (!d) return false; var ds = t.dataset;
    if (ds.cpmod) { d.modules[ds.cpmod] = t.checked ? 1 : 0; render(); return true; }
    if (ds.rp) { var x = ds.rp.split('|'); d.roles[x[0]][x[1]] = t.checked ? 1 : 0; render(); return true; }
    if (ds.rs) { d.roles[ds.rs].scope = t.value; render(); return true; }
    if (ds.ur) { if (t.value) d.userRoles[ds.ur] = t.value; else delete d.userRoles[ds.ur]; render(); return true; }
    if (ds.dr) { var y = ds.dr.split('|'); d.desigRules[+y[0]][+y[1]] = t.value; render(); return true; }
    if (ds.cat != null) { d.categories[+ds.cat].a = t.checked ? 1 : 0; render(); return true; }
    if (ds.pl) { d.pri[ds.pl].label = t.value.trim() || d.pri[ds.pl].label; render(); return true; }
    if (ds.ph) { d.pri[ds.ph].hint = t.value.trim(); render(); return true; }
    if (ds.rt) { d.reports[ds.rt] = t.checked ? 1 : 0; render(); return true; }
    if (ds.tc) { d.tCats[ds.tc].a = t.checked ? 1 : 0; render(); return true; }
    if (ds.ti) { var z = ds.ti.split('|'); d.tCats[z[0]].issues[+z[1]].a = t.checked ? 1 : 0; render(); return true; }
    if (ds.sla) { d.sla[ds.sla] = Math.max(1, +t.value || 1); render(); return true; }
    if (ds.res) { if (t.value) d.resolvers[ds.res] = t.value; else delete d.resolvers[ds.res]; render(); return true; }
    if (t.id === 'cp-mask') { d.phone.mask = t.checked ? 1 : 0; render(); return true; }
    if (t.id === 'cp-min') { d.phone.minutes = Math.max(1, +t.value || 15); render(); return true; }
    if (t.id === 'cp-defrole') { d.defaultRole = t.value; render(); return true; }
    return false;
  }

  /* ================================================================
     MODAL / HELP (hover tip + click to pin)
  ================================================================ */
  function modal(title, body, buttons, wide, cls) {
    var m = q('#modal');
    m.className = 'modal show' + (wide ? ' wide' : '');
    m.innerHTML = '<div class="mdh ' + (cls || '') + '">' + title + '<button class="x" data-act="close-modal">×</button></div><div class="mdb">' + body + '</div><div class="mdf"></div>';
    var foot = q('.mdf', m);
    (buttons || []).forEach(function (b) { var x = document.createElement('button'); x.className = 'btn ' + (b[1] || ''); x.innerHTML = b[0]; x.addEventListener('click', b[2]); foot.appendChild(x); });
    qa('[data-mp]', m).forEach(function (bt) { bt.addEventListener('click', function () { qa('[data-mp]', m).forEach(function (o) { o.classList.remove('on'); }); bt.classList.add('on'); }); });
    q('#ovl2').classList.add('show');
  }
  function modalBusy(msg) { modal('Please wait', '<div class="loading" style="padding:16px"><div class="spin"></div>' + esc(msg) + '</div>', []); }
  function closeModal() { q('#modal').className = 'modal'; q('#ovl2').classList.remove('show'); }
  function promptBox(title, hint, ph, cb, optional) {
    modal(esc(title), '<div class="hint" style="margin:0 0 6px">' + esc(hint) + '</div><textarea id="m-txt" placeholder="' + esc(ph) + '"></textarea>', [['Cancel', '', closeModal], ['Submit', 'pri', function () { var v = q('#m-txt').value.trim(); if (!v && !optional) { toast('Please write a remark', 1); return; } closeModal(); cb(v); }]]);
    setTimeout(function () { var x = q('#m-txt'); if (x) x.focus(); }, 50);
  }
  function helpHtml(k) { var h = HELP[k] || HELP.overview; return '<b>💡 ' + h[0] + '</b><ol>' + h[1].map(function (x) { return '<li>' + x + '</li>'; }).join('') + '</ol>' + (h[2] ? '<div style="margin-top:6px;font-style:italic">' + h[2] + '</div>' : ''); }
  function showHelp(k) { hideTip(); var h = HELP[k] || HELP.overview; modal('💡 ' + esc(h[0]), '<div class="help"><ol>' + h[1].map(function (x) { return '<li>' + x + '</li>'; }).join('') + '</ol>' + (h[2] ? '<div class="tip2" style="background:#fff7d6;border:1px solid #f2dc8c;border-radius:8px;padding:7px 10px;margin-top:10px;font-size:12.5px">💡 ' + h[2] + '</div>' : '') + '</div>', [['Got it', 'pri', closeModal]], false, 'help'); }
  function showTip(el) {
    var tip = q('#tip'); tip.innerHTML = helpHtml(el.dataset.help); tip.style.display = 'block';
    var r = el.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
    var left = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8), top = r.bottom + 8;
    if (top + h > window.innerHeight - 8) top = Math.max(8, r.top - h - 8);
    tip.style.left = left + 'px'; tip.style.top = top + 'px';
  }
  function hideTip() { var t = q('#tip'); if (t) t.style.display = 'none'; }

  /* ================================================================
     EVENTS
  ================================================================ */
  function bindGlobal() {
    root.addEventListener('mouseover', function (e) { var b = e.target.closest && e.target.closest('[data-help]'); if (b && root.contains(b)) showTip(b); });
    root.addEventListener('mouseout', function (e) { var b = e.target.closest && e.target.closest('[data-help]'); if (b && !(e.relatedTarget && b.contains(e.relatedTarget))) hideTip(); });
    root.addEventListener('toggle', function (e) { var d = e.target; if (d && d.dataset && d.dataset.dc) { S.cpOpen = S.cpOpen || {}; S.cpOpen[d.dataset.dc] = d.open; } }, true);
    root.addEventListener('click', function (e) {
      var el = e.target.closest('[data-help],[data-mod],[data-tab],[data-act],[data-otk],[data-qa],[data-tka],[data-mode],[data-grp],[data-unsel],[data-uncc],[data-uncc2],[data-unfile],[data-untf],[data-p],[data-kp],[data-r],[data-asg],[data-resp],[data-view],[data-sort],[data-pg],[data-kpi],[data-my],[data-tmy],[data-qtoggle],[data-mq],[data-rq],[data-assignto],[data-copymsg],[data-cpt],[data-cpdelrole],[data-cpdeldr],[data-cpdeladm],[data-cpaddissue],[data-open]');
      if (!el || !root.contains(el)) { qa('.pres').forEach(function (b) { if (!b.parentNode.contains(e.target)) b.classList.remove('show'); }); return; }
      if (e.target.closest('a.ph,a.btn,a.chip,select,input[type=checkbox]')) { if (!el.dataset.act) return; }
      var d = el.dataset;
      if (S.draft && S.tab.task === 'cpanel' && cpClick(el)) return;
      if (d.help) { e.stopPropagation(); showHelp(d.help); return; }
      if (d.mod) { S.mod = d.mod; S.page = 1; render(); return; }
      if (d.tab) { S.tab[S.mod] = d.tab; S.page = 1; if (d.tab === 'cpanel' && !S.draft) S.draft = clone(S.cfg); render(); return; }
      if (d.mq) { e.stopPropagation(); manageQueue(d.mq); return; }
      if (d.otk) { openTicket(d.otk); return; }
      if (d.qa) { quickAction(d.qa, d.id); return; }
      if (d.tka) { tkAction(d.tka, d.id); return; }
      if (d.copymsg) { if (navigator.clipboard) navigator.clipboard.writeText(decodeURIComponent(d.copymsg)); toast('Message copied — paste in WhatsApp'); return; }
      if (d.assignto) { resetForm(); S.form.sel = [d.assignto]; S.tab.task = 'assign'; render(); return; }
      if (d.kpi) { if (S.mod === 'task') { S.f.status = d.kpi; S.tab.task = can('all_tab') ? 'all' : 'my'; } else { S.tf.status = d.kpi; S.tab.ticket = 'tall'; } S.page = 1; render(); return; }
      if (d.my) { S.myTab = d.my; render(); return; }
      if (d.tmy) { S.tmyTab = d.tmy; render(); return; }
      if (d.view) { S.allView = d.view; render(); return; }
      if (d.sort) { if (S.sort.k === d.sort) S.sort.d *= -1; else S.sort = { k: d.sort, d: 1 }; render(); return; }
      if (d.pg) { S.page += +d.pg; render(); return; }
      if (d.qtoggle) { if (e.target.closest('[data-mq],.lock,a')) return; el.parentNode.classList.toggle('open'); return; }
      if (d.rq != null) { var n = +d.rq; S.f.to = n ? todayStr() : ''; S.f.from = n ? localStr(new Date(Date.now() - n * 86400000)).slice(0, 10) : ''; render(); return; }
      if (d.mode) { S.form.mode = d.mode; render(); return; }
      if (d.asg) { S.form.asGroup = d.asg === 'grp'; if (S.form.asGroup && !S.form.leader) S.form.leader = S.form.sel[0]; render(); return; }
      if (d.resp) { S.form.response = d.resp; render(); return; }
      if (d.grp != null) {
        var arr = groupSel(), i = arr.indexOf(d.grp), k = groupKey();
        if (i > -1) arr.splice(i, 1); else { arr.push(d.grp); S.people.forEach(function (p) { if (p.login && p[k] === d.grp && (S.form.mode === 'branch' || !S.form.narrowBranch || p.branch === S.form.narrowBranch) && S.form.sel.indexOf(p.user) < 0) S.form.sel.push(p.user); }); }
        render(); return;
      }
      if (d.unsel) { S.form.sel = S.form.sel.filter(function (u) { return u !== d.unsel; }); render(); return; }
      if (d.uncc) { S.form.cc = S.form.cc.filter(function (u) { return u !== d.uncc; }); render(); return; }
      if (d.uncc2) { S.tform.cc = S.tform.cc.filter(function (u) { return u !== d.uncc2; }); render(); return; }
      if (d.unfile != null) { S.pendingFiles.splice(+d.unfile, 1); q('#f-flist').innerHTML = fileChips(); renderPreview(); return; }
      if (d.untf != null) { S.tFiles.splice(+d.untf, 1); render(); return; }
      if (d.kp) { S.tform.pri = d.kp; render(); return; }
      if (d.p && el.closest('#f-pri')) { S.form.pri = d.p; qa('#f-pri .pb').forEach(function (b) { b.classList.toggle('on', b.dataset.p === d.p); }); renderPreview(); return; }
      if (d.r && el.closest('#f-rep')) { S.form.report.type = d.r; render(); return; }
      if (d.open) { openTask(d.open); return; }
      var a = d.act;
      if (a === 'refresh') { loadAll().then(function () { toast('Refreshed'); }); return; }
      if (a === 'unlock') { e.stopPropagation(); unlockPhones(); return; }
      if (a === 'demo-reset') { localStorage.removeItem(DKEY); S.draft = null; loadAll(); return; }
      if (a === 'exit-preview') { q('#viewas').value = ''; setViewAs(''); return; }
      if (a === 'assign') { confirmAssign(); return; }
      if (a === 'form-reset') { resetForm(); render(); return; }
      if (a === 'tk-submit') { submitTicket(); return; }
      if (a === 'tk-reset') { resetTForm(); render(); return; }
      if (a === 'tk-post') { tkPost(); return; }
      if (a === 'sel-all' || a === 'sel-blogin' || a === 'sel-mgr' || a === 'sel-none') {
        var pl = peopleForMode().filter(function (p) { return p.login; }), pool = pl.map(function (p) { return p.user; }), ff = S.form;
        ff.sel = ff.sel.filter(function (u) { return pool.indexOf(u) < 0; });
        if (a === 'sel-all') ff.sel = ff.sel.concat(pool);
        if (a === 'sel-blogin') ff.sel = ff.sel.concat(pl.filter(function (p) { return p.branchLogin; }).map(function (p) { return p.user; }));
        if (a === 'sel-mgr') ff.sel = ff.sel.concat(pl.filter(function (p) { return /manager|head|incharge|in-charge|cluster/i.test(p.desig); }).map(function (p) { return p.user; }));
        render(); return;
      }
      if (a === 'f-clear') { S.f = { q: '', branch: '', dept: '', desig: '', assignee: '', by: '', cat: '', pri: '', status: 'Active', rep: '', from: '', to: '', grp: '' }; S.page = 1; render(); return; }
      if (a === 'export-all') { exportTasks(sortList(applyFilters(visible()))); return; }
      if (a === 'export-team') { csv('LIFE_Team_Contacts', [['Name', 'Designation', 'Department', 'Branch', 'Mobile', 'ERP Login', 'Open', 'Overdue']].concat(S.people.map(function (p) { var l = p.login ? queueOf(p.user) : []; return [p.name, p.desig, p.dept, p.branch, showNum(p.phone), p.user, l.length, l.filter(function (t) { return isOverdue(t); }).length]; }))); return; }
      if (a === 'tk-export') { csv('LIFE_Tickets', [['Ticket', 'Category', 'Issue', 'Branch', 'Raised by', 'Raiser mobile', 'Resolver', 'Resolver mobile', 'Priority', 'Raised on', 'Status', 'SLA breached', 'Details']].concat(tApply(tVisible()).map(function (t) { return [t.id, t.cat, t.issue, t.branch, personName(t.raiser), showNum(mob(t.raiser)), personName(t.tag), showNum(mob(t.tag)), t.pri, fDT(t.created), t.status, tkBreach(t) ? 'Yes' : '', t.details]; }))); return; }
      if (a === 'export-rpt') { csv('LIFE_Task_Performance', [['Group', 'Total', 'Open', 'In Progress', 'Review', 'Overdue', 'Done', 'On-time', 'Late', 'On-time %', 'Avg days', 'Reports late']].concat((S._rptRows || []).map(function (r) { var s = r[1]; return [r[0], s.n, s.open, s.prog, s.rev, s.od, s.done, s.ontime, s.late, s.pct == null ? '' : s.pct, s.avg, s.missed]; }))); return; }
      if (a === 'print') { window.print(); return; }
      if (a === 'q-expand' || a === 'q-collapse') { qa('.qg').forEach(function (g) { g.classList.toggle('open', a === 'q-expand'); }); return; }
      if (a === 'close-drawer') { closeDrawer(); return; }
      if (a === 'close-modal') { closeModal(); return; }
      if (a === 'post-upd') { postUpdate(); return; }
      if (a === 'save-prog') { var v = +q('#d-prog').value; persist(S.openTask, function (f2) { f2.progress = v; addUpd(f2, 'System', 'Progress ' + v + '%'); if (f2.status === 'Open' || f2.status === 'Reopened') f2.status = 'In Progress'; }, 'Progress saved').catch(function () { }); return; }
      if (a === 'add-file') { S._ft = 'task'; q('#fileinp').click(); return; }
      if (a === 'upd-file' || a === 'tupd-file') { S._ft = 'upd'; q('#fileinp').click(); return; }
    });
    q('#ovl').addEventListener('click', closeDrawer);
    q('#ovl2').addEventListener('click', closeModal);
    q('#viewas').addEventListener('change', function (e) { setViewAs(e.target.value); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { if (q('#modal').classList.contains('show')) closeModal(); else closeDrawer(); } });
    root.addEventListener('input', function (e) {
      var t = e.target, id = t.id, f = S.form, tf = S.tform;
      if (id === 'f-emp') return pickerResults('f-emp', 'f-emp-res', f.sel, function (u) { f.sel.push(u); render(); });
      if (id === 'f-cc') return pickerResults('f-cc', 'f-cc-res', f.cc.concat([S.me.user]), function (u) { f.cc.push(u); render(); });
      if (id === 'k-tag') return pickerResults('k-tag', 'k-tag-res', [S.me.user], function (u) { tf.tag = u; render(); });
      if (id === 'k-cc') return pickerResults('k-cc', 'k-cc-res', tf.cc.concat([S.me.user, tf.tag]), function (u) { tf.cc.push(u); render(); });
      if (id === 'cp-admin') return pickerResults('cp-admin', 'cp-admin-res', CORE_ADMINS.concat(S.draft.admins || []), function (u) { S.draft.admins = (S.draft.admins || []).concat([u]); render(); });
      if (id === 'f-title') { f.title = t.value; return; }
      if (id === 'f-details') { if (words(t.value) > 150) t.value = t.value.split(/\s+/).slice(0, 150).join(' '); f.details = t.value; updateWc(); return; }
      if (id === 'f-check') { f.checklist = t.value; return; }
      if (id === 'k-details') { tf.details = t.value; return; }
      if (id === 'k-other') { tf.other = t.value; return; }
      var live = { 'ff-q': [S.f, 'q'], 'tf-q': [S.tf, 'q'], 'tm-q': [S.team, 'q'], 'cp-q': [S, 'cpq'] }[id];
      if (live) { live[0][live[1]] = t.value; S.page = 1; clearTimeout(S._qt); S._qt = setTimeout(function () { var pos = t.selectionStart; render(); var n = q('#' + id); if (n) { n.focus(); n.setSelectionRange(pos, pos); } }, 250); return; }
      if (id === 'd-prog') { q('#d-progv').textContent = t.value + '%'; return; }
    });
    root.addEventListener('change', function (e) {
      var t = e.target, id = t.id, f = S.form, tf = S.tform;
      if (S.tab.task === 'cpanel' && S.mod === 'task' && cpChange(t)) return;
      if (t.dataset.pu) { var u = t.dataset.pu; if (t.checked) { if (f.sel.indexOf(u) < 0) f.sel.push(u); } else f.sel = f.sel.filter(function (x) { return x !== u; }); render(); return; }
      if (t.dataset.ff) { S.f[t.dataset.ff] = t.value; S.page = 1; render(); return; }
      if (t.dataset.tf) { S.tf[t.dataset.tf] = t.value; render(); return; }
      if (t.dataset.tf2) { S.team[t.dataset.tf2] = t.value; render(); return; }
      if (t.dataset.ck != null && S.openTask) { var i = +t.dataset.ck, ck = t.checked; persist(S.openTask, function (x) { x.checklist[i].d = ck; var dn = x.checklist.filter(function (c) { return c.d; }).length; x.progress = Math.max(x.progress, Math.round(dn * 20 / x.checklist.length) * 5); if (x.status === 'Open') x.status = 'In Progress'; }).catch(function () { }); return; }
      if (id === 'rp-dim') { S.rptDim = t.value; render(); return; }
      if (id === 'f-cat') { f.cat = t.value; renderPreview(); return; }
      if (id === 'f-title') { f.title = t.value; renderPreview(); return; }
      if (id === 'f-start') { f.start = t.value; updateDur(); return; }
      if (id === 'f-due') { if (toDate(t.value) && toDate(t.value) < new Date()) { toast('Due cannot be in the past', 1); t.value = f.due; return; } f.due = t.value; updateDur(); renderPreview(); return; }
      if (id === 'f-top') { f.top = t.checked; renderPreview(); return; }
      if (id === 'f-email') { f.email = t.checked; renderPreview(); return; }
      if (id === 'f-wa') { f.wa = t.checked; renderPreview(); return; }
      if (id === 'f-leader') { f.leader = t.value; render(); return; }
      if (id === 'f-narrow') { f.narrowBranch = t.value; render(); return; }
      if (id === 'f-rtime') { f.report.time = t.value; renderPreview(); return; }
      if (id === 'f-rday') { f.report.day = +t.value; renderPreview(); return; }
      if (id === 'f-rdom') { f.report.dom = +t.value; renderPreview(); return; }
      if (id === 'f-rdt') { f.report.dt = t.value; renderPreview(); return; }
      if (id === 'k-branch') { tf.branch = t.value; return; }
      if (id === 'k-cat') { tf.cat = t.value; tf.issue = ''; var sg = suggestResolver(t.value); if (sg) tf.tag = sg; render(); return; }
      if (id === 'k-issue') { tf.issue = t.value; render(); return; }
      if (id === 'k-emp') { tf.emp = t.value; return; }
      if (id === 'k-wa') { tf.wa = t.checked; return; }
      if (id === 'k-email') { tf.email = t.checked; return; }
    });
    q('#fileinp').addEventListener('change', function (e) {
      var files = Array.prototype.slice.call(e.target.files || []); e.target.value = '';
      var ok = files.filter(function (fl) { if (fl.size > MAX_FILE) { toast(fl.name + ' is over 5 MB', 1); return false; } return true; });
      if (S._ft === 'form') { S.pendingFiles = S.pendingFiles.concat(ok); var fl = q('#f-flist'); if (fl) fl.innerHTML = fileChips(); renderPreview(); }
      else if (S._ft === 'tform') { S.tFiles = S.tFiles.concat(ok); render(); }
      else if (S._ft === 'upd') { S.updFiles = (S.updFiles || []).concat(ok); var h = q('#d-ufiles'); if (h) h.textContent = '📎 ' + S.updFiles.map(function (x) { return x.name; }).join(', '); }
      else if (S._ft === 'task' && S.openTask) {
        if (guard()) return;
        var t0 = findTask(S.openTask), key = fileKey(t0), id = S.openTask;
        ok.reduce(function (p, f) { return p.then(function () { return API.upload('ToDo', key, f).then(function (r) { (S.files[key] = S.files[key] || []).push(r); }); }); }, Promise.resolve())
          .then(function () { return persist(id, function (x) { addUpd(x, 'System', 'Attached: ' + ok.map(function (f) { return f.name; }).join(', ')); }, 'File attached'); }).catch(function (er) { toast(String(errMsg(er)), 1); });
      }
    });
    root.addEventListener('click', function (e) { if (e.target.closest('#f-drop')) { S._ft = 'form'; q('#fileinp').click(); } if (e.target.closest('#k-drop')) { S._ft = 'tform'; q('#fileinp').click(); } });
    root.addEventListener('dragover', function (e) { var d = e.target.closest && e.target.closest('.drop'); if (d) { e.preventDefault(); d.classList.add('over'); } });
    root.addEventListener('dragleave', function (e) { var d = e.target.closest && e.target.closest('.drop'); if (d) d.classList.remove('over'); });
    root.addEventListener('drop', function (e) {
      var d = e.target.closest && e.target.closest('.drop'); if (!d) return; e.preventDefault(); d.classList.remove('over');
      var ok = Array.prototype.slice.call(e.dataTransfer.files || []).filter(function (fl) { return fl.size <= MAX_FILE || (toast(fl.name + ' over 5 MB', 1), false); });
      if (d.id === 'k-drop') { S.tFiles = S.tFiles.concat(ok); render(); } else { S.pendingFiles = S.pendingFiles.concat(ok); q('#f-flist').innerHTML = fileChips(); renderPreview(); }
    });
  }
  function exportTasks(list) {
    csv('LIFE_Tasks', [['Task No', 'Type', 'Queue', 'Title', 'Details', 'Category', 'Assigned To', 'Mobile', 'Designation', 'Branch', 'Department', 'Assigned By', 'Priority', 'Status', 'Overdue', 'Assigned On', 'Start', 'Due', 'Completed On', 'Reporting', 'Progress %', 'Updates', 'Last Update', 'CC']].concat(list.map(function (t) {
      var lu = t.updates.filter(function (u) { return u.type !== 'System'; }).slice(-1)[0];
      return [dispNo(t), t.grp ? 'Group (' + t.grp.response + ')' : 'Individual', qRank(t), t.title, t.details, t.cat, personName(t.assignee), showNum(mob(t.assignee)), t.desig, t.branch, t.dept, personName(t.by), PRI_N(t.pri) + ' ' + PRI_L(t.pri), t.status, isOverdue(t) ? 'Yes' : '', fDT(t.created), fDT(t.start), fDT(t.due), t.completedOn ? fDT(t.completedOn) : '', repText(t.report), t.progress, t.updates.length, lu ? fDT(lu.at) + ' ' + personName(lu.by) + ': ' + lu.text : '', t.cc.map(personName).join('; ')];
    })));
  }

  /* ================================================================
     DEMO SEED (only used outside the portal)
  ================================================================ */
  function demoSeed() {
    var people = [
      ['bhuvan@lifescc.com', 'K Bhuvan Prasad', 'Management', 'COO', 'Head Office', '9000000001'], ['gachibowli@lifescc.com', 'Gachibowli branch', 'Branch Login', 'Branch Login', 'Gachibowli', '9000000020'],
      ['madhapur@lifescc.com', 'Madhapur branch', 'Branch Login', 'Branch Login', 'Madhapur', ''], ['vizag@lifescc.com', 'Vizag branch', 'Branch Login', 'Branch Login', 'Vizag', '9000000021'],
      ['teena@lifescc.com', 'Teena Mahur', 'Operations', 'Cluster Head', 'Madhapur', '9000000002'], ['preethi@lifescc.com', 'Preethi', 'Operations', 'Cluster Head', 'Vijayawada', '9000000003'],
      ['narendhar@lifescc.com', 'Narendhar', 'IT', 'ERP Developer', 'Head Office', '9000000005'], ['yaswanth@lifescc.com', 'yaswanthkumaryy1234', 'IT', 'ERP Developer', 'Head Office', '9000000006'],
      ['kavya@lifescc.com', 'Kavya', 'IT', 'ERP Developer', 'Head Office', '9000000007'], ['viveka@lifescc.com', 'Viveka', 'HR', 'HR Manager', 'Head Office', '9000000008'],
      ['valli@lifescc.com', 'Valli', 'Stock', 'Store Incharge', 'Head Office', '9000000009'], ['ravikishore@lifescc.com', 'Ravi Kishore', 'Audit', 'Audit Manager', 'Head Office', '9000000010'],
      ['sairaj@lifescc.com', 'Nampally Sai Raj', 'Sales', 'Center Manager', 'Kukatpally', '9000000011'], ['ishwarya@lifescc.com', 'Anupoju Ishwarya', 'Sales', 'Center Manager', 'Banjara Hills', '9044488817'],
      ['madhavi@lifescc.com', 'Komara Sai Madhavi', 'Medical', 'Consultant Doctor', 'SR Nagar', '9700035832'], ['satya@lifescc.com', 'Satya', 'Accounts', 'Accounts Manager', 'Head Office', '9000000013'],
      ['surya@lifescc.com', 'Surya Teja', 'Operations', 'Ops Coordinator', 'Head Office', '9000000014'], ['', 'Sabitri Oraon', 'Service', 'Dr.Assistant', 'Kukatpally', '8106024089'], ['', 'Yatagiri Haritha', 'Service', 'Therapist', 'SR Nagar', '']
    ];
    var users = [], emps = [];
    people.forEach(function (p, i) { if (p[0]) users.push({ name: p[0], full_name: p[1], mobile_no: p[5] }); if (p[2] !== 'Branch Login') emps.push({ name: 'HR-EMP-' + (100 + i), employee_name: p[1], user_id: p[0] || null, department: p[2], designation: p[3], branch: p[4], cell_number: p[5] }); });
    var titles = [['Update all walk-ins in ERP with proper data', 'Audit will be there after 6th. Every walk-in from 1st Oct must be entered with lead source, concern and counsellor.', 'Operations'], ['Pending products from corporate — follow up', 'Pending products yet to receive from corporate; check indent and update status.', 'Inventory / Stock'], ['Machine AMC renewal documents', 'Collect AMC docs for laser and cavitation machines and upload.', 'Machinery'], ['Weekly sales MIS to COO', 'Branch-wise booking, visits and ticket size.', 'Sales'], ['Fix CC dashboard lead filter', 'Lead source filter shows duplicates; fix and test.', 'IT'], ['Consent forms audit — October', 'Verify every procedure has signed consent and before/after photos.', 'Audit'], ['Staff attendance correction list', 'Prepare biometric mismatch list for payroll.', 'HR'], ['Branch cleanliness checklist photos', 'Daily 10am photos of reception, rooms, washroom.', 'Facility / Maintenance'], ['Pending dues recovery — top 20 clients', 'Call and confirm payment dates; update ERP remarks.', 'Accounts'], ['Diwali offer creatives', 'Coordinate with marketing for branch standees.', 'Marketing']];
    var asg = ['gachibowli@lifescc.com', 'teena@lifescc.com', 'sairaj@lifescc.com', 'yaswanth@lifescc.com', 'narendhar@lifescc.com', 'kavya@lifescc.com', 'valli@lifescc.com', 'ravikishore@lifescc.com', 'ishwarya@lifescc.com', 'madhapur@lifescc.com', 'vizag@lifescc.com', 'viveka@lifescc.com', 'bhuvan@lifescc.com'];
    var pris = ['VVIMP', 'IMP', 'HI', 'MED', 'LOW', 'HI', 'MED'], sts = ['Open', 'In Progress', 'Open', 'Review Pending', 'Completed', 'In Progress', 'Open', 'Completed', 'On Hold', 'Open'], reps = ['EOD', 'WEEKLY', 'COMPLETION', 'EOD', 'MONTHLY'];
    var todos = [], now = Date.now(), pre = 'T' + String(new Date().getFullYear()).slice(2) + pad(new Date().getMonth() + 1) + '-';
    for (var i = 0; i < 30; i++) {
      var tt = titles[i % titles.length], u = asg[i % asg.length], pp = people.filter(function (x) { return x[0] === u; })[0];
      var created = new Date(now - (i * 0.9 + 0.2) * 86400000), due = new Date(created.getTime() + ((i % 5) + 1) * 86400000), st = sts[i % sts.length];
      var t = { meta: {}, no: pre + String(i + 1).padStart(4, '0'), title: tt[0], details: tt[1], cat: tt[2], pri: pris[i % pris.length], status: st, assignee: u, by: i % 4 === 0 ? 'teena@lifescc.com' : 'bhuvan@lifescc.com', created: localStr(created), start: localStr(created), due: localStr(due), cc: i % 3 === 0 ? ['ravikishore@lifescc.com'] : [], report: { type: reps[i % reps.length], time: '19:00', day: 6, dom: 1 }, notify: {}, checklist: i % 2 ? [{ t: 'Collect data', d: true }, { t: 'Enter in ERP', d: st === 'Completed' }, { t: 'Share proof', d: false }] : [], progress: (i * 13) % 90, updates: [{ id: 'u' + i, at: localStr(created), by: 'bhuvan@lifescc.com', type: 'System', text: 'Task assigned' }].concat(i % 3 === 1 ? [{ id: 'v' + i, at: localStr(new Date(created.getTime() + 6 * 3600000)), by: u, type: 'Report', text: 'Started collecting data, 40% done.' }] : []), delays: [], completedOn: st === 'Completed' ? localStr(new Date(due.getTime() + (i % 2 ? -3600000 : 7200000))) : '', target: { type: 'Employee' }, qk: PRI_W(pris[i % pris.length]) * 10 + i / 100, branch: pp[4], dept: pp[2], desig: pp[3] };
      var d = denormBase(t); d.name = 'td' + i; d.allocated_to = u; d.assigned_by = t.by; d.owner = t.by; d.creation = t.created.replace('T', ' ') + ':00'; d.modified = d.creation; d.custom_task_queue_no = 0;
      todos.push(d);
    }
    // one demo group task (individual response)
    var gm = ['teena@lifescc.com', 'preethi@lifescc.com', 'sairaj@lifescc.com'], gc = new Date(now - 86400000);
    var g = { meta: { mq: { 'teena@lifescc.com': 0.5, 'preethi@lifescc.com': 0.5, 'sairaj@lifescc.com': 0.5 }, mstate: { 'teena@lifescc.com': { status: 'In Progress', progress: 40 }, 'preethi@lifescc.com': { status: 'Open', progress: 0 }, 'sairaj@lifescc.com': { status: 'Review Pending', progress: 100 } } }, no: pre + '0031', title: 'Branch Diwali footfall plan — all clusters', details: 'Each cluster to submit footfall plan, staff roster and offer standee placement.', cat: 'Operations', pri: 'IMP', status: 'In Progress', assignee: gm[0], by: 'bhuvan@lifescc.com', created: localStr(gc), start: localStr(gc), due: localStr(new Date(now + 2 * 86400000)), cc: [], report: { type: 'EOD', time: '19:00' }, notify: {}, checklist: [], progress: 47, updates: [{ id: 'g1', at: localStr(gc), by: 'bhuvan@lifescc.com', type: 'System', text: '👥 Group task assigned to 3 members' }, { id: 'g2', at: localStr(new Date(gc.getTime() + 5 * 3600000)), by: 'teena@lifescc.com', type: 'Report', text: 'Madhapur & Gachibowli roster ready.' }, { id: 'g3', at: localStr(new Date(gc.getTime() + 7 * 3600000)), by: 'sairaj@lifescc.com', type: 'Completion', text: 'Kukatpally plan done and shared.' }], delays: [], completedOn: '', target: { type: 'Employee' }, qk: 1, grp: { id: 'Gdemo', members: gm, leader: gm[0], response: 'individual', mirrors: {} } };
    var gd = denormBase(g); gd.name = 'tdg'; gd.allocated_to = gm[0]; gd.assigned_by = 'bhuvan@lifescc.com'; gd.owner = 'bhuvan@lifescc.com'; gd.creation = g.created.replace('T', ' ') + ':00'; gd.modified = gd.creation;
    todos.unshift(gd);
    var issues = [], cats = Object.keys(TICKET_CATEGORY_MAP), res = ['narendhar@lifescc.com', 'viveka@lifescc.com', 'satya@lifescc.com', 'valli@lifescc.com', 'surya@lifescc.com'], raisers = ['gachibowli@lifescc.com', 'madhapur@lifescc.com', 'vizag@lifescc.com', 'bhuvan@lifescc.com', 'sairaj@lifescc.com'], tsts = ['Open', 'Open', 'Resolved', 'Closed', 'Reopened', 'On Hold'];
    for (var j = 0; j < 16; j++) {
      var c = cats[j % cats.length], iss = TICKET_CATEGORY_MAP[c][j % 3], cr = new Date(now - (j * 0.7 + 0.3) * 86400000), s2 = tsts[j % tsts.length];
      var tk = { meta: {}, branch: BRANCHES[j % BRANCHES.length], cat: c, issue: iss, other: '', emp: '', tag: res[j % res.length], cc: [], details: 'Issue noticed at branch: ' + iss + '. Please check and resolve.', status: s2, updates: [{ at: localStr(cr), by: raisers[j % raisers.length], type: 'System', text: 'Ticket raised' }], resolvedOn: s2 === 'Resolved' || s2 === 'Closed' ? localStr(new Date(cr.getTime() + 20 * 3600000)) : '', closedOn: s2 === 'Closed' ? localStr(new Date(cr.getTime() + 30 * 3600000)) : '' };
      issues.push({ name: 'ISS-2026-' + String(j + 1).padStart(5, '0'), subject: c + ' - ' + iss, description: tkDesc(tk), priority: TK_PRI[j % 3], status: tkStatusField(s2), raised_by: raisers[j % raisers.length], owner: raisers[j % raisers.length], creation: localStr(cr).replace('T', ' ') + ':00', modified: localStr(cr).replace('T', ' ') + ':00' });
    }
    return { users: users, emps: emps, todos: todos, issues: issues, files: [], cfg: null };
  }

  /* ================================================================
     START — waits for frappe login; never falls into demo on the portal
  ================================================================ */
  var tries = 0;
  function start() {
    if (!document.getElementById('life-tm')) return;
    if (window.frappe && frappe.call && !sessionUser() && tries < 20) { tries++; setTimeout(start, 250); return; }
    boot();
  }
  if (window.frappe && typeof frappe.ready === 'function') frappe.ready(start);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { setTimeout(start, 50); }); else setTimeout(start, 50);
})();
return { refresh: () => document.getElementById('life-tm')?.querySelector('[data-act=refresh]')?.click() };
}
