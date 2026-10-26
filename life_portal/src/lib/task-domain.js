// Task domain and persistence rules. No screen rendering or global DOM access.
export const CORE_ADMINS=['administrator', 'bhuvan@lifescc.com', 'narendhar@lifescc.com'];
export const CFG_TITLE='LIFE_TASK_CPANEL_CONFIG';
export const BRANCHES=['Head Office', 'Madhapur', 'Chandanagar', 'Gachibowli', 'Kukatpally', 'Banjara Hills', 'SR Nagar', 'Dilsukhnagar', 'Himayathnagar', 'Vijayawada', 'Vizag', 'Nellore'];
export const PRI_KEYS=['VVIMP', 'IMP', 'HI', 'MED', 'LOW'];
export const PRI_TODO={ VVIMP: 'High', IMP: 'High', HI: 'High', MED: 'Medium', LOW: 'Low' };
export const LEGACY_PRI={ High: 'HI', Medium: 'MED', Low: 'LOW' };
export const STATUSES=['Open', 'In Progress', 'Review Pending', 'On Hold', 'Reopened', 'Completed', 'Cancelled'];
export const ST_CLS={ 'Open': 's-open', 'In Progress': 's-prog', 'Review Pending': 's-rev', 'On Hold': 's-hold', 'Reopened': 's-reo', 'Completed': 's-done', 'Cancelled': 's-cxl', 'Resolved': 's-rev', 'Closed': 's-done' };

export function ticketActionAllowed(ticket,kind,user,manager=false){
 const resolver=ticket.tag===user,raiser=ticket.raiser===user||ticket.owner===user,active=!['Resolved','Closed','Cancelled'].includes(ticket.status);
 if(kind==='resolve')return active&&(resolver||manager);
 if(kind==='close')return ticket.status==='Resolved'&&(raiser||manager);
 if(kind==='reopen')return ['Resolved','Closed'].includes(ticket.status)&&(raiser||manager);
 if(kind==='retag'||kind==='remind')return active&&(raiser||manager);
 if(['hold','unhold','tpri'].includes(kind))return active&&manager;
 return false;
}
export const REPORT_DEF=[
    { k: 'EOD', label: 'EOD (Daily)', d: 'Report every day by the set time' },
    { k: 'WEEKLY', label: 'Weekly', d: 'Report on the chosen weekday' },
    { k: 'MONTHLY', label: 'Monthly', d: 'Report on the chosen date every month' },
    { k: 'SPECIFIC', label: 'Specific Date & Time', d: 'One report at an exact date-time' },
    { k: 'COMPLETION', label: 'Only on Completion', d: 'No interim reports' }
  ];
export const WEEKDAYS=['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
export const UPD_TYPES=['Update', 'Report', 'Delay Remark', 'Query'];
export const MAX_FILE=5 * 1024 * 1024;
export const TK_PRI=['High', 'Medium', 'Low'];
export const TK_STATUSES=['Open', 'Reopened', 'On Hold', 'Resolved', 'Closed'];
export const TICKET_CATEGORY_MAP={
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
export const EMPLOYEE_INVOLVED_ISSUES=[
    "Facing Issue With Another Employee",
    "Harassment Complaint",
    "Discrimination Complaint",
    "Behavioural Concern"
  ];
export const PERMS=[
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
export const SCOPES=[['own', 'Own only (mine, by me, CC, my groups)'], ['dept', 'My department + own'], ['branch', 'My branch + own'], ['all', 'All branches']];
export const MODULES=[
    ['tasks', 'Task Management', 'Whole Tasks module'], ['tickets', 'Ticket / Helpdesk', 'Whole Tickets module'], ['team', 'Team & Contacts tab', 'Employee directory with mobiles'],
    ['reports', 'Reports tab', 'Performance analytics'], ['viewas', 'View as employee', 'Preview any employee’s screen'], ['group', 'Group tasks', 'One task to many people with shared updates'],
    ['recent', 'Recent tasks panel', 'Last 5 assigned on the Assign screen'], ['checklist', 'Checklist / sub-steps', 'Optional steps inside a task'],
    ['email', 'Email notifications', 'Send ERP email on assign / remind'], ['wa', 'WhatsApp notifications', 'One-tap wa.me messages'],
    ['repMandatory', 'Reporting rule mandatory', 'Must choose EOD / Weekly / … before assigning'], ['delayMandatory', 'Delay remark mandatory', 'Overdue tasks need a delay remark before any action']
  ];
export const MON=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export function createTaskDomain(S,API,toast){
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
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

function pad(n) { return String(n).padStart(2, '0'); }

function localStr(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + 'T' + pad(d.getHours()) + ':' + pad(d.getMinutes()); }

function nowLocal() { return localStr(new Date()); }

function todayStr() { return nowLocal().slice(0, 10); }

function toDate(s) { if (!s) return null; s = String(s).replace(' ', 'T'); if (s.length === 10) s += 'T00:00'; var d = new Date(s.slice(0, 19)); return isNaN(d) ? null : d; }

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

function htmlToText(value){return String(value||'').replace(/<!--[\s\S]*?-->/g,'').replace(/<br\s*\/?\s*>/gi,'\n').replace(/<\/(?:p|div|li)>/gi,'\n').replace(/<[^>]*>/g,'').replace(/&(?:amp|lt|gt|quot|apos|nbsp);|&#(?:x[0-9a-f]+|[0-9]+);/gi,entity=>{const map={'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&apos;':"'",'&nbsp;':' '};if(map[entity])return map[entity];const number=entity[2]?.toLowerCase()==='x'?parseInt(entity.slice(3),16):parseInt(entity.slice(2),10);return Number.isFinite(number)&&number<=0x10ffff?String.fromCodePoint(number):entity;}).trim();}

function person(u) { return S.byUser[String(u || '').toLowerCase()] || null; }

function personName(u) { if (!u) return '—'; var p = person(u); if (p) return p.name; return String(u).indexOf('@') > -1 ? String(u).split('@')[0] : u; }

function guard() { if (S.me.preview) { toast('Preview mode — switch “View as” back to your own view to make changes', 1); return true; } return false; }

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

function digits(p) { return String(p || '').replace(/\D/g, '').replace(/^0+/, ''); }

function phone91(p) { p = digits(p); if (p.length === 10) p = '91' + p; return p.length === 12 && p.indexOf('91') === 0 ? p : ''; }

function mob(u) { var p = person(u); return p ? p.phone : ''; }

function phonesOpen() { return !S.cfg.phone.mask || can('phones') || Date.now() < S.phoneUntil; }

function maskNum(d) { d = d.slice(-10); return d.slice(0, 2) + 'XXXXXX' + d.slice(-2); }

function showNum(ph) { var d = digits(ph); if (!d) return ''; return phonesOpen() ? d.slice(-10) : maskNum(d); }

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

function isClosed(t) { return t.status === 'Completed' || t.status === 'Cancelled'; }

function isOverdue(t, now) { if (isClosed(t)) return false; var d = toDate(t.due); return d && d < (now || new Date()); }

function dueToday(t) { return !isClosed(t) && t.due && t.due.slice(0, 10) === todayStr(); }

function timeLeft(t){if(t.status==='Completed')return toDate(t.completedOn)<=toDate(t.due)?'On time':'Late';if(t.status==='Cancelled')return '—';const due=toDate(t.due);return due?(due<new Date()?'-':'')+dur(due-new Date()):'—';}

function canManage(t) { return can('manage') || t.by === S.me.user || t.owner === S.me.user; }

function isAssignee(t) { return t.assignee === S.me.user; }

function fileKey(t) { return t.mid || t.id; }

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

function parseCfgNote(n) {
    if (!n || !n.content) return null;
    var m = String(n.content).match(/<!--LIFE_CPANEL:([\s\S]*?)-->/); if (!m) return null;
    try { return JSON.parse(m[1]); } catch (e) { return null; }
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
    });
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
    var p = jobs.reduce(function (p, j) { return p.then(function () { return API.save('ToDo', j[0], j[1]); }); }, Promise.resolve());
    return Object.keys(grp).reduce(function (p, mid) { return p.then(function () { return writeGroupMq(mid, grp[mid]); }); }, p);
  }

function setOrder(user, ids) {
    if (guard()) return Promise.resolve();
    ids.forEach(function (id, i) { var t = findTask(id); if (t) t.qk = i + 1; });
    return syncQueue(user).then(function () {   });
  }

function nextTaskNo(offset) {
    var pre = 'T' + String(new Date().getFullYear()).slice(2) + pad(new Date().getMonth() + 1) + '-';
    var max = 0; S.tasks.forEach(function (t) { if (t.no && t.no.indexOf(pre) === 0) { var n = parseInt(t.no.slice(pre.length), 10); if (n > max) max = n; } });
    return pre + String(max + 1 + (offset || 0)).padStart(4, '0');
  }

function dispNo(t) { return t.no || ('#' + String(t.mid || t.id).slice(-6).toUpperCase()); }

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

function newBase(f, u, extra) {
    var p = person(u) || {}, now = nowLocal();
    var checklist = mod('checklist') ? f.checklist.split('\n').map(function (x) { return x.trim(); }).filter(Boolean).map(function (x) { return { t: x, d: false }; }) : [];
    var b = { meta: {}, no: nextTaskNo(0), title: f.title.trim(), details: f.details.trim(), cat: f.cat, pri: f.pri, status: 'Open', assignee: u, by: S.me.user, created: now, start: f.start, due: f.due, cc: f.cc.slice(), report: clone(f.report), notify: { email: f.email, wa: f.wa }, checklist: checklist, progress: 0, updates: [], delays: [], completedOn: '', target: { type: f.mode === 'emp' ? 'Employee' : f.mode === 'branch' ? 'Branch' : f.mode === 'dept' ? 'Department' : 'Designation', values: f.mode === 'emp' ? [] : groupSel().slice() }, qk: 1, branch: p.branch || '', dept: p.dept || '', desig: p.desig || '', grp: null };
    Object.keys(extra || {}).forEach(function (k) { b[k] = extra[k]; });
    return b;
  }

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

function findTask(id) { return S.tasks.filter(function (t) { return t.id === id; })[0]; }

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
        return (before !== isClosed(fresh) ? syncQueue(fresh.assignee) : Promise.resolve()).then(function () { if (okMsg) toast(okMsg);   return fresh; });
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
        return jobs.then(function () { if (okMsg) toast(okMsg);  S.openTask = mid + '::' + u;  return findTask(mid + '::' + u); });
      });
    }).catch(function (e) { if (e !== 'preview') toast('Not saved: ' + errMsg(e), 1); throw e; });
  }

function addUpd(t, type, text, files) { t.updates.push({ id: uid(), at: nowLocal(), by: S.me.user, type: type, text: text, files: files || [] }); }

function findTk(id) { return S.tickets.filter(function (t) { return t.id === id; })[0]; }

function tPersist(id, mutate, okMsg) {
    if (guard()) return Promise.reject('preview');
    return API.get('Issue', id).then(function (raw) {
      var fresh = normTicket(raw); mutate(fresh);
      var fields = { description: tkDesc(fresh), status: tkStatusField(fresh.status) };
      if (fresh._pri) fields.priority = fresh.pri;
      return API.save('Issue', id, fields).then(function () {
        raw.description = fields.description; raw.status = fields.status; if (fields.priority) raw.priority = fields.priority;
        var nt = normTicket(raw), i = S.tickets.indexOf(findTk(id)); if (i > -1) S.tickets[i] = nt;
        if (okMsg) toast(okMsg);   return nt;
      });
    }).catch(function (e) { if (e !== 'preview') toast('Not saved: ' + errMsg(e), 1); throw e; });
  }

function resetTForm() { var mp = person(S.me.user || ''); S.tform = { branch: (mp && mp.branch) || 'Head Office', cat: '', issue: '', other: '', emp: '', tag: '', cc: [], pri: '', details: '', wa: true, email: true }; S.tFiles = []; }

function suggestResolver(cat) {
    if (S.cfg.resolvers[cat]) return S.cfg.resolvers[cat];
    var s = CATEGORY_TAG_TO_SUGGEST[cat]; if (!s) return '';
    var m = S.people.filter(function (p) { return p.login && (p.name.toLowerCase().indexOf(s) > -1 || p.user.toLowerCase().indexOf(s) > -1); })[0];
    return m ? m.user : '';
  }

function taskMsg(t, kind) {
    var head = kind === 'reminder' ? '⏰ *LIFE Clinics — Task Reminder*' : '📌 *LIFE Clinics — New ' + (t.grp ? 'Group ' : '') + 'Task Assigned*';
    return head + '\n\nDear ' + personName(t.assignee) + ',\n\n*Task No:* ' + dispNo(t) + '   |   *Your Queue:* #' + (qRank(t) || '-') + (t.grp ? '\n*Group:* ' + t.grp.members.length + ' members (' + t.grp.response + ' response)' : '') +
      '\n*Priority:* ' + PRI_N(t.pri) + ' ' + PRI_L(t.pri) + '\n*Category:* ' + t.cat + '\n*Title:* ' + t.title + '\n\n' + t.details.slice(0, 600) +
      '\n\n*Assigned by:* ' + personName(t.by) + '\n*Assigned on:* ' + fDT(t.created) + '\n*Due:* ' + fDT(t.due) + '\n*Reporting:* ' + repText(t.report) +
      '\n\nOpen & update: ' + location.origin + location.pathname + '\n— LIFE Task Management';
  }

function tkMsg(tk, kind) {
    return (kind === 'new' ? '🎫 *LIFE Clinics — New Ticket*' : '⏰ *LIFE Clinics — Ticket Reminder*') + '\n\n*Ticket:* ' + tk.id + '\n*Priority:* ' + tk.pri + '   *SLA:* ' + fDT(localStr(tkSla(tk) || new Date())) + '\n*Branch:* ' + tk.branch + '\n*Category:* ' + tk.cat + '\n*Issue:* ' + tk.issue + (tk.other ? ' — ' + tk.other : '') + '\n\n' + tk.details.slice(0, 600) + '\n\n*Raised by:* ' + personName(tk.raiser) + '\n\nOpen: ' + location.origin + location.pathname;
  }

function mailHtml(title, text) { return '<div style="font-family:Arial,sans-serif;font-size:14px;color:#1d2a23"><div style="background:#14532d;color:#fff;padding:12px 16px;border-radius:8px 8px 0 0;font-size:16px;font-weight:bold">LIFE Clinics — ' + esc(title) + '</div><div style="border:1px solid #d5e6db;border-top:0;padding:16px;border-radius:0 0 8px 8px">' + esc(text).replace(/\*/g, '').replace(/\n/g, '<br>') + '</div></div>'; }
return {allPerms,defaultCfg,mergeCfg,pad,localStr,nowLocal,todayStr,toDate,fD,fDT,dur,initials,words,uid,norm,uniq,clone,fsize,htmlToText,person,personName,guard,isAdmin,roleOf,roleSource,permsOf,can,mod,scope,setMe,digits,phone91,mob,phonesOpen,maskNum,showNum,PRI_L,PRI_H,PRI_W,PRI_N,categories,reportTypes,REP,tCats,tIssues,SLA,isClosed,isOverdue,dueToday,timeLeft,canManage,isAssignee,fileKey,parseMeta,legacyUpdates,base,enrich,explode,normalizeRows,denormBase,mirrorDoc,groupOverall,ticketDetailsFrom,normTicket,tkDesc,tkStatusField,tkClosed,tkActive,tkSla,tkBreach,parseCfgNote,buildPeople,queueOf,qRank,placement,writeGroupMq,syncQueue,setOrder,nextTaskNo,dispNo,myUpdates,lastReport,reportDue,repText,needsDelayRemark,involved,visible,tVisible,taskTabs,ticketTabs,resetForm,groupKey,groupSel,peopleForMode,distinct,allBranches,validateForm,newBase,stats,findTask,persist,persistGroup,addUpd,findTk,tPersist,resetTForm,suggestResolver,taskMsg,tkMsg,mailHtml};
}

const CATEGORY_TAG_TO_SUGGEST={
    "IT / ERP / Software": "narendhar",
    "Human Resources": "viveka",
    "Accounts / Billing": "satya",
    "Marketing": "sridevi",
    "Inventory / Stock": "valli",
    "Operations": "surya",
    "Clinical Machinery": "anand"
  };
