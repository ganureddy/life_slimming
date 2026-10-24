// Dashboard behavior maintained as a page-owned ES module.
export function mountEmployeeSaleMaster(page) {
const { document, window, frappe, fetch, MutationObserver, setTimeout, clearTimeout, setInterval, clearInterval } = page;
/* ═══════════════════════════════════════════════════════════════
   LIFE · EMPLOYEE SALE REPORT — Web Page JavaScript
   Paste into Web Page > Scripting > Javascript.
   Data source: Query Report "REFERRAL REPORT – FIXED" (unchanged).

   What this version does
   • Period (payment date) loads from server; every other filter is
     instant and client-side — no re-fetch per filter change.
   • Filters grouped: Period · People & Place · Treatment · Payment & Amount
   • Treatment cascade: Main Category › Therapy Group › Therapy Type
     (multi-select, searchable, live counts, "(Unmapped)" option)
   • Amount basis: Full Invoice  /  Treatment Share
   • Tabs: Overview · Employee · Branch (+ Branch × Category) ·
     Treatment Category tree (+ unmapped therapy types) · Transactions
   • Every table: search, sort, totals row; drill-down modals
   • One-click Excel workbook (Filters + 6 sheets) and A4 print
   • Branch permission logic kept from the previous version
   ═══════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var VERSION = '2026-10-24.1';
  var REPORT_NAME = 'REFERRAL REPORT – FIXED';
  var EXCLUDED_BRANCHES = ['head office', 'testing branch'];
  var ALL_BRANCH_ROLES = ['System Manager'];
  var NONE = '__NONE__';
  var NONE_LABEL = '(Unmapped)';
  var NO_LINES = '(No therapy lines)';
  var tries = 0;

  function boot() {
    var R = document.getElementById('esr-root');
    if (!R || typeof window.frappe === 'undefined') {
      if (tries++ < 150) setTimeout(boot, 100);
      return;
    }
    if (R.__esrInit) return;
    R.__esrInit = true;
    try { app(R); } catch (e) {
      void 0;
      var st = document.getElementById('esr-status');
      if (st) st.innerHTML = '<div class="esr-msg esr-msg-err">Report failed to start: ' + String(e && e.message || e) + '</div>';
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();

  /* ═════════════════════════════════════════════════════════ */
  function app(R) {
    void 0;

    var $ = function (id) { return R.querySelector('#' + id); };
    var today = new Date();

    var S = {
      raw: [], allCredits: [], loaded: null, loading: false,
      perm: [], restricted: false, allAccess: false, locked: null,
      alias: {}, empInfo: {},
      basis: 'full', tab: 'overview',
      ms: {}, tables: {}, view: null, treeOpen: {}, renderTimer: null
    };

    /* ─────────────── formatters & helpers ─────────────── */
    function num(v) { var n = Number(v); return isFinite(n) ? n : 0; }
    function r2(v) { return Math.round((num(v) + Number.EPSILON) * 100) / 100; }
    function esc(v) {
      return String(v === null || v === undefined ? '' : v)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }
    function clean(v) { return String(v || '').normalize('NFKC').replace(/ /g, ' ').replace(/\s+/g, ' ').trim(); }
    function lc(v) { return clean(v).toLowerCase(); }
    function fmt(n) {
      return '₹' + num(n).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }
    function compact(n) {
      var v = num(n), a = Math.abs(v), d, s;
      if (a >= 1e7) { d = 1e7; s = ' Cr'; } else if (a >= 1e5) { d = 1e5; s = ' L'; } else if (a >= 1e3) { d = 1e3; s = ' K'; } else return fmt(v);
      return '₹' + (v / d).toFixed(2).replace(/\.00$/, '').replace(/(\.\d)0$/, '$1') + s;
    }
    function pct(a, b) { return b ? (a / b * 100) : 0; }
    function iso(d) { return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
    var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    function dmy(s) {
      if (!s) return '';
      var p = String(s).slice(0, 10).split('-');
      if (p.length !== 3) return String(s);
      return p[2] + '-' + MON[Number(p[1]) - 1] + '-' + p[0].slice(2);
    }
    function dmyList(s) { return String(s || '').split(',').map(function (x) { return dmy(x.trim()); }).filter(Boolean).join(', '); }
    function keys(o) { return Object.keys(o).length; }
    function top(counter) {
      var best = '', bv = -1;
      Object.keys(counter).forEach(function (k) { if (counter[k] > bv) { bv = counter[k]; best = k; } });
      return best;
    }
    function lbl(k) { return k === NONE ? NONE_LABEL : k; }
    function uniq(a) { var o = {}; return a.filter(function (x) { if (o[x]) return false; o[x] = 1; return true; }); }

    function cycleOf(d) {
      var y = d.getFullYear(), m = d.getMonth();
      return d.getDate() >= 6 ? { s: new Date(y, m, 6), e: new Date(y, m + 1, 5) } : { s: new Date(y, m - 1, 6), e: new Date(y, m, 5) };
    }
    function rangeFor(k) {
      var t = new Date(today), c, p, y;
      if (k === 'today') return { s: t, e: t };
      if (k === 'yesterday') { y = new Date(t); y.setDate(y.getDate() - 1); return { s: y, e: y }; }
      if (k === 'cycle') return cycleOf(t);
      if (k === 'lastcycle') { c = cycleOf(t); p = new Date(c.s); p.setDate(p.getDate() - 1); return cycleOf(p); }
      if (k === 'calmonth') return { s: new Date(t.getFullYear(), t.getMonth(), 1), e: new Date(t.getFullYear(), t.getMonth() + 1, 0) };
      if (k === 'fy') return t.getMonth() >= 3 ? { s: new Date(t.getFullYear(), 3, 1), e: new Date(t.getFullYear() + 1, 2, 31) } : { s: new Date(t.getFullYear() - 1, 3, 1), e: new Date(t.getFullYear(), 2, 31) };
      return cycleOf(t);
    }

    function status(msg, kind) {
      $('esr-status').innerHTML = msg ? '<div class="esr-msg esr-msg-' + (kind || 'info') + '">' + msg + '</div>' : '';
    }

    /* ─────────────── data normalisation ─────────────── */
    function parseLines(v) {
      var arr = [];
      if (v) {
        try { arr = typeof v === 'string' ? JSON.parse(v) : v; } catch (e) { arr = []; }
        if (!Array.isArray(arr)) arr = [];
      }
      var hasAmt = arr.some(function (d) { return d && num(d.amount) > 0; });
      var lines = arr.filter(function (d) { return d && (d.type || d.category || d.group); }).map(function (d) {
        var cat = clean(d.category), grp = clean(d.group), typ = clean(d.type) || '(Blank type)';
        return { type: typ, category: cat, group: grp, catKey: cat || NONE, grpKey: grp || NONE, w: hasAmt ? Math.max(num(d.amount), 0) : 1 };
      });
      if (!lines.length) lines = [{ type: NO_LINES, category: '', group: '', catKey: NONE, grpKey: NONE, w: 1 }];
      var tw = lines.reduce(function (s, l) { return s + l.w; }, 0);
      if (tw <= 0) { lines.forEach(function (l) { l.w = 1; }); tw = lines.length; }
      return { lines: lines, totalW: tw };
    }

    function normalize(row) {
      row = row || {};
      var oldType = String(row.credit_type || '').toLowerCase();
      var refName = clean(row.referring_employee || row.custom_referring_name || (oldType === 'ref' ? row.sales_person_name : ''));
      var incName = clean(row.incentive_employee || row.custom_incentive_employee_name || (oldType === 'incentive' ? row.sales_person_name : ''));
      var refId = clean(row.referring_employee_id || (oldType === 'ref' ? row.employee_id : ''));
      var incId = clean(row.incentive_employee_id || (oldType === 'incentive' ? row.employee_id : ''));
      var pracId = clean(row.referring_practitioner_id || row.sales_person_id || row.ref_practitioner);

      var paid = num(row.paid_amount);
      var ex = num(row.paid_amount_without_gst) || num(row.paid_amount_without_tax);
      var gst = num(row.gst_amount) || num(row.tax_amount);
      if (!ex && paid) ex = paid / 1.05;
      if (!gst && paid) gst = paid - ex;

      var refShare = num(row.referring_employee_share), incShare = num(row.incentive_employee_share);
      if (!refShare && !incShare && ex) {
        if (oldType === 'ref') refShare = ex;
        else if (oldType === 'incentive') incShare = ex;
        else if (refName && incName) { refShare = ex / 2; incShare = ex - refShare; }
        else if (refName) refShare = ex;
        else if (incName) incShare = ex;
      }

      var tl = parseLines(row.therapy_details);
      var mops = uniq(String(row.mode_of_payment || '').split(',').map(clean).filter(Boolean));
      var booking = clean(row.booking_type || row.media);
      var sharing = clean(row.sharing_type) || (refName && incName ? 'Shared - Half Each' : refName ? 'Referring Employee Only' : incName ? 'Incentive Employee Only' : 'No Employee');

      return {
        invoice: clean(row.invoice),
        invoice_date: row.invoice_date || row.posting_date || '',
        payment_dates: row.payment_dates || '',
        payment_ids: row.payment_ids || '',
        branch: clean(row.branch),
        customer: clean(row.customer),
        client_name: clean(row.client_name || row.patient_name),
        booking: booking || NONE,
        sharing: sharing,
        mop: mops.join(', '),
        mops: mops.length ? mops : [NONE],
        refName: refName, refId: refId, pracId: pracId,
        incName: incName, incId: incId,
        paid: paid, gst: gst, ex: ex,
        refShare: refShare, incShare: incShare,
        dist: num(row.total_distributed_amount) || ex,
        gt: num(row.grand_total),
        out: num(row.outstanding_amount),
        lines: tl.lines, totalW: tl.totalW,
        cats: uniq(tl.lines.map(function (l) { return l.catKey; })),
        grps: uniq(tl.lines.map(function (l) { return l.grpKey; })),
        types: uniq(tl.lines.map(function (l) { return l.type; }))
      };
    }

    /* ─────────────── employee identity ─────────────── */
    function buildAlias(credits) {
      var cand = {};
      credits.forEach(function (c) {
        var n = lc(c.name), id = lc(c.empId);
        if (!n || !id) return;
        (cand[n] = cand[n] || {})[id] = true;
      });
      S.alias = {};
      Object.keys(cand).forEach(function (n) { var ids = Object.keys(cand[n]); if (ids.length === 1) S.alias[n] = ids[0]; });
    }
    function empKey(c) {
      var id = lc(c.empId);
      if (id) return 'E|' + id;
      var n = lc(c.name);
      if (n && S.alias[n]) return 'E|' + S.alias[n];
      if (c.role === 'ref' && lc(c.pracId)) return 'P|' + lc(c.pracId);
      return 'N|' + n;
    }

    function buildCredits(invs) {
      var out = [];
      invs.forEach(function (v) {
        var total = v.dist || v.ex;
        function push(role, name, id, prac, share, refPart, incPart, dual) {
          share = num(share);
          if (!name || share <= 0) return;
          var ratio = total > 0 ? Math.min(Math.max(share / total, 0), 1) : 1;
          var c = {
            inv: v, role: role, dual: !!dual, name: name, empId: id || '', pracId: prac || '',
            ex: share, exFull: v.factor > 0 ? share / v.factor : share,
            refPart: refPart, incPart: incPart,
            paid: v.paid * ratio, gst: v.gst * ratio, gt: v.gt * ratio, out: v.out * ratio
          };
          c.key = empKey(c);
          out.push(c);
        }
        var rid = lc(v.refId), iid = lc(v.incId);
        if (rid && iid && rid === iid) {
          var both = num(v.refShare) + num(v.incShare) || total;
          push('ref', v.refName || v.incName, v.refId || v.incId, v.pracId, both, num(v.refShare), num(v.incShare), true);
          return;
        }
        push('ref', v.refName, v.refId, v.pracId, v.refShare, num(v.refShare), 0, false);
        push('inc', v.incName, v.incId, '', v.incShare, 0, num(v.incShare), false);
      });
      return out;
    }

    function scaleInv(r, f) {
      if (f === 1) { r.factor = 1; return r; }
      var v = Object.assign({}, r);
      v.factor = f;
      ['paid', 'gst', 'ex', 'refShare', 'incShare', 'dist', 'gt', 'out'].forEach(function (k) { v[k] = r[k] * f; });
      return v;
    }

    /* ─────────────── multi-select component ─────────────── */
    var openDD = null;
    function MultiSelect(host) {
      var key = host.getAttribute('data-key');
      var allLabel = host.getAttribute('data-all') || 'All';
      var opts = [], sel = [], onChange = function () {};

      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'esr-ms-btn';
      btn.innerHTML = '<span class="esr-ms-txt"></span>';
      host.appendChild(btn);

      var dd = document.createElement('div');
      dd.className = 'esr-dd';
      dd.innerHTML =
        '<div class="esr-dd-top"><input class="esr-dd-search" type="text" placeholder="Search…" autocomplete="off">' +
        '<div class="esr-dd-acts"><button type="button" data-a="all">Select shown</button><button type="button" data-a="none">Clear</button></div></div>' +
        '<div class="esr-dd-list"></div><div class="esr-dd-foot"><span class="f1"></span><span class="f2"></span></div>';
      document.body.appendChild(dd);
      var search = dd.querySelector('.esr-dd-search'), list = dd.querySelector('.esr-dd-list');

      function labelOf(v) { for (var i = 0; i < opts.length; i++) if (opts[i].v === v) return opts[i].l; return lbl(v); }
      function paintBtn() {
        var t = btn.querySelector('.esr-ms-txt');
        var old = btn.querySelector('.esr-ms-n'); if (old) old.parentNode.removeChild(old);
        if (!sel.length) { t.textContent = allLabel; btn.classList.remove('has'); return; }
        btn.classList.add('has');
        t.textContent = sel.length === 1 ? labelOf(sel[0]) : labelOf(sel[0]) + ' + ' + (sel.length - 1) + ' more';
        if (sel.length > 1) { var n = document.createElement('span'); n.className = 'esr-ms-n'; n.textContent = sel.length; btn.appendChild(n); }
        btn.title = sel.map(labelOf).join(', ');
      }
      function shown() {
        var q = lc(search.value);
        return opts.filter(function (o) { return !q || lc(o.l + ' ' + (o.sub || '') + ' ' + o.v).indexOf(q) >= 0; });
      }
      function paintList() {
        var items = shown();
        list.innerHTML = items.length ? items.map(function (o) {
          var on = sel.indexOf(o.v) >= 0;
          return '<label class="esr-dd-item' + (o.v === NONE ? ' none' : '') + '" data-v="' + esc(o.v) + '"><input type="checkbox"' + (on ? ' checked' : '') + '>' +
            '<span class="t" title="' + esc(o.l + (o.sub ? ' · ' + o.sub : '')) + '">' + esc(o.l) + (o.sub ? '<small>' + esc(o.sub) + '</small>' : '') + '</span>' +
            (o.c !== undefined ? '<span class="c">' + o.c + '</span>' : '') + '</label>';
        }).join('') : '<div class="esr-dd-empty">No match</div>';
        dd.querySelector('.f1').textContent = items.length + ' of ' + opts.length;
        dd.querySelector('.f2').textContent = sel.length ? sel.length + ' selected' : '';
      }
      function place() {
        var r = btn.getBoundingClientRect(), w = Math.max(r.width, 270), vh = window.innerHeight;
        dd.style.width = w + 'px';
        dd.style.left = Math.max(8, Math.min(r.left, window.innerWidth - w - 8)) + 'px';
        var below = vh - r.bottom;
        if (below < 260 && r.top > below) { dd.style.top = ''; dd.style.bottom = (vh - r.top + 4) + 'px'; dd.style.maxHeight = Math.min(360, r.top - 12) + 'px'; }
        else { dd.style.bottom = ''; dd.style.top = (r.bottom + 4) + 'px'; dd.style.maxHeight = Math.min(360, below - 12) + 'px'; }
      }
      function open() {
        if (btn.disabled) return;
        if (openDD && openDD !== api) openDD.close();
        openDD = api; search.value = ''; paintList(); place(); dd.classList.add('open');
        setTimeout(function () { search.focus(); }, 0);
      }
      function close() { dd.classList.remove('open'); if (openDD === api) openDD = null; }
      function changed() { paintBtn(); paintList(); onChange(key); }

      btn.addEventListener('click', function (e) { e.preventDefault(); dd.classList.contains('open') ? close() : open(); });
      search.addEventListener('input', paintList);
      search.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
      list.addEventListener('click', function (e) {
        var it = e.target.closest('.esr-dd-item'); if (!it) return;
        e.preventDefault();
        var v = it.getAttribute('data-v'), i = sel.indexOf(v);
        if (i >= 0) sel.splice(i, 1); else sel.push(v);
        changed();
      });
      dd.querySelector('.esr-dd-acts').addEventListener('click', function (e) {
        var a = e.target.getAttribute('data-a'); if (!a) return;
        if (a === 'none') sel = [];
        else shown().forEach(function (o) { if (sel.indexOf(o.v) < 0) sel.push(o.v); });
        changed();
      });
      document.addEventListener('mousedown', function (e) {
        if (dd.classList.contains('open') && !dd.contains(e.target) && !btn.contains(e.target)) close();
      }, true);
      window.addEventListener('resize', function () { if (dd.classList.contains('open')) place(); });
      window.addEventListener('scroll', function (e) { if (dd.classList.contains('open') && !dd.contains(e.target)) place(); }, true);

      var api = {
        key: key, close: close,
        val: function () { return sel.slice(); },
        labels: function () { return sel.map(labelOf); },
        labelOf: labelOf,
        set: function (a, silent) { sel = (a || []).slice(); paintBtn(); if (!silent) onChange(key); },
        setOptions: function (o) {
          opts = o || [];
          var valid = {}; opts.forEach(function (x) { valid[x.v] = 1; });
          var before = sel.length;
          sel = sel.filter(function (v) { return valid[v]; });
          paintBtn(); if (dd.classList.contains('open')) paintList();
          return before !== sel.length;
        },
        disable: function (d) { btn.disabled = !!d; },
        onChange: function (fn) { onChange = fn; }
      };
      paintBtn();
      return api;
    }

    R.querySelectorAll('.esr-ms').forEach(function (h) {
      var m = MultiSelect(h);
      S.ms[m.key] = m;
      m.onChange(function (k) {
        if (k === 'category' || k === 'group') rebuildTreatmentOptions();
        scheduleRender();
      });
    });

    /* ─────────────── generic table ─────────────── */
    function cellVal(col, row) { return col.v ? col.v(row) : row[col.k]; }
    function cellHtml(col, row) {
      if (col.h) return col.h(row);
      var v = cellVal(col, row);
      if (col.t === 'amt') return fmt(v);
      if (col.t === 'int') return num(v).toLocaleString('en-IN');
      if (col.t === 'pct') return num(v).toFixed(1) + '%';
      if (col.t === 'date') return esc(dmy(v));
      return esc(v);
    }
    function isNum(col) { return col.t === 'amt' || col.t === 'int' || col.t === 'pct'; }

    function table(id, cols, rows, opt, boxEl) {
      opt = opt || {};
      var box = boxEl || R.querySelector('[data-tbl="' + id + '"]');
      if (!box) return;
      var st = S.tables[id];
      if (!st || st.box !== box) {
        st = S.tables[id] = { box: box, q: '', sort: opt.sort || null, dir: opt.dir || -1, limit: opt.limit || 250 };
        box.innerHTML =
          (opt.search === false ? '' : '<div class="esr-tbar"><input class="esr-tsearch" type="text" placeholder="🔍 Search ' + esc(opt.what || 'rows') + '…"><span class="esr-tcount"></span></div>') +
          '<div class="esr-tblwrap"><table class="esr-table"><thead></thead><tbody></tbody><tfoot></tfoot></table></div><div class="esr-more"></div>';
        var s = box.querySelector('.esr-tsearch');
        if (s) s.addEventListener('input', function () { st.q = s.value; st.limit = opt.limit || 250; paint(id); });
        box.addEventListener('click', function (e) {
          var th = e.target.closest('th.sort');
          if (th) {
            var k = th.getAttribute('data-k');
            if (st.sort === k) st.dir = -st.dir; else { st.sort = k; st.dir = th.classList.contains('n') ? -1 : 1; }
            paint(id); return;
          }
          var mb = e.target.closest('.esr-more button');
          if (mb) { st.limit = mb.getAttribute('data-all') ? 1e9 : st.limit + 250; paint(id); return; }
          if (e.target.closest('a')) return;
          var tr = e.target.closest('tbody tr[data-i]');
          if (tr && st.opt.rowClick) st.opt.rowClick(st.vis[Number(tr.getAttribute('data-i'))]);
        });
      }
      st.cols = cols; st.rows = rows || []; st.opt = opt;
      paint(id);
    }

    function paint(id) {
      var st = S.tables[id], cols = st.cols, opt = st.opt;
      var rows = st.rows;
      if (st.q) {
        var q = lc(st.q);
        rows = rows.filter(function (r) {
          return cols.some(function (c) { return c.search !== false && lc(cellVal(c, r)).indexOf(q) >= 0; });
        });
      }
      if (st.sort) {
        var sc = cols.filter(function (c) { return c.k === st.sort; })[0];
        if (sc) {
          var n = isNum(sc);
          rows = rows.slice().sort(function (a, b) {
            var x = cellVal(sc, a), y = cellVal(sc, b);
            if (n) return (num(x) - num(y)) * st.dir;
            return String(x || '').localeCompare(String(y || ''), undefined, { numeric: true, sensitivity: 'base' }) * st.dir;
          });
        }
      }
      st.vis = rows.slice(0, st.limit);

      var thead = '<tr>' + cols.map(function (c) {
        var cls = (isNum(c) ? 'n ' : '') + (c.nosort ? '' : 'sort ') + (st.sort === c.k ? 'active ' : '') + (c.stick ? 'stick' : '');
        var ar = c.nosort ? '' : '<span class="ar">' + (st.sort === c.k ? (st.dir > 0 ? '▲' : '▼') : '⇅') + '</span>';
        return '<th class="' + cls + '" data-k="' + esc(c.k) + '"' + (c.tip ? ' title="' + esc(c.tip) + '"' : '') + '>' + esc(c.l) + ar + '</th>';
      }).join('') + '</tr>';

      var body = st.vis.map(function (r, i) {
        return '<tr data-i="' + i + '"' + (opt.rowClick ? ' class="click"' : '') + '>' + cols.map(function (c) {
          var cls = (isNum(c) ? 'n ' : '') + (c.cls ? (typeof c.cls === 'function' ? c.cls(r) : c.cls) + ' ' : '') + (c.stick ? 'stick' : '');
          return '<td class="' + cls + '">' + cellHtml(c, r) + '</td>';
        }).join('') + '</tr>';
      }).join('');
      if (!body) body = '<tr><td colspan="' + cols.length + '"><div class="esr-empty">' + (st.rows.length ? 'No rows match the search.' : (opt.empty || 'No data for the selected filters.')) + '</div></td></tr>';

      var foot = '';
      if (opt.totals !== false && rows.length) {
        var first = true;
        foot = '<tr>' + cols.map(function (c) {
          var cls = (isNum(c) ? 'n ' : '') + (c.stick ? 'stick' : '');
          if (c.sum) {
            var s = rows.reduce(function (a, r) { return a + num(cellVal(c, r)); }, 0);
            return '<td class="' + cls + '">' + (c.t === 'amt' ? fmt(s) : s.toLocaleString('en-IN')) + '</td>';
          }
          if (c.sumFn) return '<td class="' + cls + '">' + c.sumFn(rows) + '</td>';
          if (first) { first = false; return '<td class="' + cls + '">Total (' + rows.length.toLocaleString('en-IN') + ')</td>'; }
          return '<td class="' + cls + '"></td>';
        }).join('') + '</tr>';
      }
      var t = st.box.querySelector('table');
      t.querySelector('thead').innerHTML = thead;
      t.querySelector('tbody').innerHTML = body;
      t.querySelector('tfoot').innerHTML = foot;
      var cnt = st.box.querySelector('.esr-tcount');
      if (cnt) cnt.textContent = (st.q ? rows.length + ' of ' + st.rows.length : st.rows.length.toLocaleString('en-IN')) + ' ' + (opt.what || 'rows');
      var more = st.box.querySelector('.esr-more');
      more.innerHTML = rows.length > st.vis.length
        ? 'Showing ' + st.vis.length + ' of ' + rows.length + ' &nbsp; <button type="button" class="esr-btn esr-btn-xs">Show 250 more</button> <button type="button" class="esr-btn esr-btn-xs" data-all="1">Show all</button>'
        : '';
      more.style.display = more.innerHTML ? '' : 'none';
    }

    /* ─────────────── permissions ─────────────── */
    function hasAllAccess() {
      if (frappe.session && frappe.session.user === 'Administrator') return true;
      if (frappe.user && typeof frappe.user.has_role === 'function') {
        for (var i = 0; i < ALL_BRANCH_ROLES.length; i++) if (frappe.user.has_role(ALL_BRANCH_ROLES[i])) return true;
      }
      var roles = frappe.user_roles || (frappe.boot && frappe.boot.user && frappe.boot.user.roles) || [];
      return ALL_BRANCH_ROLES.some(function (r) { return roles.indexOf(r) !== -1; });
    }
    function loadBranches() {
      return new Promise(function (resolve, reject) {
        frappe.call({
          method: 'frappe.client.get_list',
          args: { doctype: 'Branch', fields: ['name'], limit_page_length: 200, order_by: 'name asc' },
          callback: function (r) {
            var names = uniq(((r && r.message) || []).map(function (b) { return clean(b && b.name); }).filter(Boolean))
              .filter(function (n) { return EXCLUDED_BRANCHES.indexOf(n.toLowerCase()) === -1; })
              .sort(function (a, b) { return a.localeCompare(b, undefined, { sensitivity: 'base' }); });
            S.allAccess = hasAllAccess();
            S.restricted = !S.allAccess;
            S.perm = names;
            if (S.restricted && !names.length) { reject(new Error('No permitted Branch was returned for this login.')); return; }
            S.locked = (S.restricted && names.length === 1) ? names[0] : null;
            resolve();
          },
          error: function (e) { reject(e || new Error('Unable to determine Branch access.')); }
        });
      });
    }
    function initBranchSelect() {
      var sel = $('esr-f-branch');
      if (S.locked) {
        sel.innerHTML = '<option value="' + esc(S.locked) + '">' + esc(S.locked) + '</option>';
        sel.disabled = true;
        return;
      }
      sel.innerHTML = '<option value="">' + (S.restricted ? 'All Permitted Branches' : 'All Branches') + '</option>' +
        S.perm.map(function (b) { return '<option value="' + esc(b) + '">' + esc(b) + '</option>'; }).join('');
    }

    /* ─────────────── fetch ─────────────── */
    function runReport(from, to, branch) {
      return new Promise(function (resolve, reject) {
        frappe.call({
          method: 'frappe.desk.query_report.run',
          args: { report_name: REPORT_NAME, filters: { from_date: from, to_date: to, branch: branch || '' }, ignore_prepared_report: 1 },
          callback: function (r) {
            if (r && r.exc) { reject(new Error('Report error')); return; }
            var raw = (r && r.message && Array.isArray(r.message.result)) ? r.message.result : [];
            var rows = raw.filter(function (x) { return x && typeof x === 'object' && !Array.isArray(x); }).map(normalize).filter(function (x) { return !!x.invoice; });
            if (raw.length && !rows.length && raw.some(function (x) { return x && !Array.isArray(x); })) {
              reject(new Error(REPORT_NAME + ' returned data without an Invoice field. This page needs the invoice-wise report output.'));
              return;
            }
            resolve(rows);
          },
          error: function (e) { reject(e || new Error('Report request failed.')); }
        });
      });
    }
    function keepPermitted(rows) {
      if (!S.restricted) return rows;
      return rows.filter(function (r) { return S.perm.indexOf(r.branch) !== -1; });
    }
    function dedupe(rows) {
      var seen = {};
      return rows.filter(function (r) { var k = r.invoice + '|' + r.payment_ids; if (seen[k]) return false; seen[k] = 1; return true; });
    }
    function fetchAll(from, to) {
      if (S.locked) return runReport(from, to, S.locked).then(function (rows) { return rows.filter(function (r) { return r.branch === S.locked; }); });
      if (S.restricted) {
        var first = S.perm[0];
        return runReport(from, to, first).then(function (rows) {
          // Report SQL ignores the branch filter → first call already returned every branch.
          if (rows.some(function (r) { return r.branch && r.branch !== first; })) return keepPermitted(dedupe(rows));
          return Promise.all(S.perm.slice(1).map(function (b) { return runReport(from, to, b); })).then(function (groups) {
            var all = rows; groups.forEach(function (g) { all = all.concat(g); });
            return keepPermitted(dedupe(all));
          });
        });
      }
      return runReport(from, to, '').then(dedupe);
    }

    function load() {
      var from = $('esr-f-from').value, to = $('esr-f-to').value;
      if (!from || !to) { status('Select both From and To dates.', 'err'); return; }
      if (from > to) { status('From date cannot be after To date.', 'err'); return; }
      if (S.loading) return;
      S.loading = true;
      var btn = $('esr-btn-load');
      btn.disabled = true; btn.classList.remove('esr-dirty');
      status('<span class="esr-spin"></span>Loading collections from ' + dmy(from) + ' to ' + dmy(to) + ' for ' +
        esc(S.locked || (S.restricted ? 'all permitted branches' : 'all branches')) + '…');
      fetchAll(from, to).then(function (rows) {
        S.raw = rows;
        S.loaded = { from: from, to: to, at: new Date() };
        afterLoad();
      }).catch(function (e) {
        void 0;
        status('Could not load the report: ' + esc(e && e.message ? e.message : 'unknown error'), 'err');
      }).then(function () {
        S.loading = false; btn.disabled = false; markDirty();
      });
    }

    function afterLoad() {
      S.raw.forEach(function (r) { r.factor = 1; });
      var cr = buildCredits(S.raw);
      buildAlias(cr);
      cr.forEach(function (c) { c.key = empKey(c); });
      S.allCredits = cr;
      S.empInfo = {};
      cr.forEach(function (c) {
        var e = S.empInfo[c.key] || (S.empInfo[c.key] = { name: c.name, id: '' });
        if (c.empId && !e.id) e.id = c.empId;
      });
      Object.keys(S.empInfo).forEach(function (k) {
        if (!S.empInfo[k].id && k.indexOf('P|') === 0) S.empInfo[k].id = k.slice(2).toUpperCase();
      });
      $('esr-meta-period').textContent = dmy(S.loaded.from) + ' → ' + dmy(S.loaded.to);
      $('esr-meta-loaded').textContent = S.loaded.at.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
      rebuildOptions();
      status(S.raw.length ? '' : 'No collections with a referring or incentive employee in this period.', S.raw.length ? 'info' : 'warn');
      renderNow();
    }

    /* ─────────────── filter options ─────────────── */
    function branchRows() {
      var b = $('esr-f-branch').value;
      return b ? S.raw.filter(function (r) { return r.branch === b; }) : S.raw;
    }
    function countOpts(map, sortByLabel) {
      return Object.keys(map).map(function (k) { return { v: k, l: lbl(k), c: map[k] }; })
        .sort(function (a, b) {
          if (a.v === NONE) return 1; if (b.v === NONE) return -1;
          return sortByLabel ? a.l.localeCompare(b.l) : (b.c - a.c || a.l.localeCompare(b.l));
        });
    }
    function rebuildOptions() {
      var rows = branchRows(), b = $('esr-f-branch').value;
      var bk = {}, sh = {}, mp = {};
      rows.forEach(function (r) {
        bk[r.booking] = (bk[r.booking] || 0) + 1;
        sh[r.sharing] = (sh[r.sharing] || 0) + 1;
        r.mops.forEach(function (m) { mp[m] = (mp[m] || 0) + 1; });
      });
      S.ms.booking.setOptions(countOpts(bk));
      S.ms.sharing.setOptions(countOpts(sh));
      S.ms.mop.setOptions(countOpts(mp));

      var em = {}, emInv = {}, rc = { ref: 0, inc: 0 };
      S.allCredits.forEach(function (c) {
        if (b && c.inv.branch !== b) return;
        (emInv[c.key] = emInv[c.key] || {})[c.inv.invoice] = 1;
        em[c.key] = 1;
        if (c.dual) { rc.ref++; rc.inc++; } else rc[c.role]++;
      });
      S.ms.emp.setOptions(Object.keys(em).map(function (k) {
        var i = S.empInfo[k] || { name: k, id: '' };
        return { v: k, l: i.name || '(No name)', sub: i.id, c: keys(emInv[k]) };
      }).sort(function (a, b2) { return a.l.localeCompare(b2.l, undefined, { sensitivity: 'base' }); }));
      S.ms.role.setOptions([{ v: 'ref', l: 'Referring Employee', c: rc.ref }, { v: 'inc', l: 'Incentive Employee', c: rc.inc }]);
      rebuildTreatmentOptions();
    }
    function rebuildTreatmentOptions() {
      var rows = branchRows();
      var cats = S.ms.category.val(), grps;
      var cm = {}, gm = {}, tm = {};
      rows.forEach(function (r) {
        var cs = {}, gs = {}, ts = {};
        r.lines.forEach(function (l) {
          cs[l.catKey] = 1;
          if (!cats.length || cats.indexOf(l.catKey) >= 0) gs[l.grpKey] = 1;
        });
        Object.keys(cs).forEach(function (k) { cm[k] = (cm[k] || 0) + 1; });
        Object.keys(gs).forEach(function (k) { gm[k] = (gm[k] || 0) + 1; });
      });
      S.ms.category.setOptions(countOpts(cm));
      S.ms.group.setOptions(countOpts(gm));
      grps = S.ms.group.val();
      rows.forEach(function (r) {
        var ts = {};
        r.lines.forEach(function (l) {
          if ((!cats.length || cats.indexOf(l.catKey) >= 0) && (!grps.length || grps.indexOf(l.grpKey) >= 0)) ts[l.type] = 1;
        });
        Object.keys(ts).forEach(function (k) { tm[k] = (tm[k] || 0) + 1; });
      });
      S.ms.type.setOptions(countOpts(tm));
    }

    /* ─────────────── amount inputs ─────────────── */
    function amt(id) {
      var v = $(id).value.trim();
      if (v === '') return null;
      var n = Number(v);
      return isFinite(n) ? n : null;
    }
    function validateAmounts() {
      var ok = true;
      [['esr-f-paid-min', 'esr-f-paid-max'], ['esr-f-out-min', 'esr-f-out-max']].forEach(function (p) {
        var a = amt(p[0]), b = amt(p[1]), bad = a !== null && b !== null && a > b;
        $(p[0]).classList.toggle('esr-invalid', bad);
        $(p[1]).classList.toggle('esr-invalid', bad);
        if (bad) ok = false;
      });
      return ok;
    }
    R.querySelectorAll('.esr-amt').forEach(function (el) {
      el.addEventListener('input', function () {
        var c = el.value.replace(/[^\d.]/g, '').replace(/^(\d*\.?\d{0,2}).*$/, '$1');
        if (c !== el.value) el.value = c;
        scheduleRender();
      });
    });

    /* ─────────────── compute ─────────────── */
    function readFilters() {
      var f = {
        branch: $('esr-f-branch').value,
        emp: S.ms.emp.val(), role: S.ms.role.val(), sharing: S.ms.sharing.val(),
        category: S.ms.category.val(), group: S.ms.group.val(), type: S.ms.type.val(),
        booking: S.ms.booking.val(), mop: S.ms.mop.val(),
        paidMin: amt('esr-f-paid-min'), paidMax: amt('esr-f-paid-max'),
        outMin: amt('esr-f-out-min'), outMax: amt('esr-f-out-max'),
        onlyOut: $('esr-f-onlyout').checked
      };
      f.amountsOk = validateAmounts();
      if (!f.amountsOk) { f.paidMin = f.paidMax = f.outMin = f.outMax = null; }
      f.treat = !!(f.category.length || f.group.length || f.type.length);
      return f;
    }
    function lineOk(l, f) {
      return (!f.category.length || f.category.indexOf(l.catKey) >= 0) &&
        (!f.group.length || f.group.indexOf(l.grpKey) >= 0) &&
        (!f.type.length || f.type.indexOf(l.type) >= 0);
    }
    function roleOk(c, roles) {
      if (!roles.length) return true;
      if (c.dual) return true;
      return roles.indexOf(c.role) >= 0;
    }

    function compute() {
      var f = readFilters(), invs = [];
      S.raw.forEach(function (r) {
        if (f.branch && r.branch !== f.branch) return;
        if (f.booking.length && f.booking.indexOf(r.booking) < 0) return;
        if (f.sharing.length && f.sharing.indexOf(r.sharing) < 0) return;
        if (f.mop.length && !r.mops.some(function (m) { return f.mop.indexOf(m) >= 0; })) return;
        if (f.onlyOut && r.out <= 0.5) return;
        var matched = r.lines, mw = r.totalW;
        if (f.treat) {
          matched = r.lines.filter(function (l) { return lineOk(l, f); });
          if (!matched.length) return;
          mw = matched.reduce(function (s, l) { return s + l.w; }, 0);
        }
        var v = scaleInv(r, f.treat && S.basis === 'share' ? mw / r.totalW : 1);
        if (v === r) { r.matched = matched; } else v.matched = matched;
        if (f.paidMin !== null && v.ex < f.paidMin) return;
        if (f.paidMax !== null && v.ex > f.paidMax) return;
        if (f.outMin !== null && v.out < f.outMin) return;
        if (f.outMax !== null && v.out > f.outMax) return;
        invs.push(v);
      });
      var credits = buildCredits(invs);
      var empOn = f.emp.length || f.role.length;
      if (empOn) {
        credits = credits.filter(function (c) {
          if (f.emp.length && f.emp.indexOf(c.key) < 0) return false;
          return roleOk(c, f.role);
        });
        if (f.role.length === 1) {
          credits.forEach(function (c) {
            if (!c.dual) return;
            var part = f.role[0] === 'ref' ? c.refPart : c.incPart, tot = c.refPart + c.incPart;
            if (tot > 0 && part >= 0) {
              var k = part / tot;
              c.ex *= k; c.exFull *= k; c.paid *= k; c.gst *= k; c.gt *= k; c.out *= k;
              c.refPart = f.role[0] === 'ref' ? c.refPart : 0; c.incPart = f.role[0] === 'inc' ? c.incPart : 0;
            }
          });
        }
        var keep = {};
        credits.forEach(function (c) { keep[c.inv.invoice + '|' + c.inv.payment_ids] = 1; });
        invs = invs.filter(function (v) { return keep[v.invoice + '|' + v.payment_ids]; });
      }
      return { f: f, invs: invs, credits: credits, empOn: !!empOn };
    }

    /* ─────────────── aggregations ─────────────── */
    function aggEmployees(credits) {
      var m = {}, totalEx = 0;
      credits.forEach(function (c) {
        var e = m[c.key];
        if (!e) {
          var info = S.empInfo[c.key] || {};
          e = m[c.key] = { key: c.key, name: info.name || c.name, id: info.id || c.empId || '', br: {}, inv: {}, cli: {}, ref: 0, inc: 0, ex: 0, gst: 0, paid: 0, gt: 0, out: 0, cat: {}, bk: {}, mop: {} };
        }
        e.br[c.inv.branch] = 1;
        e.inv[c.inv.invoice] = 1;
        e.cli[c.inv.customer] = 1;
        if (c.dual) { var t = c.refPart + c.incPart || 1; e.ref += c.ex * c.refPart / t; e.inc += c.ex * c.incPart / t; }
        else if (c.role === 'inc') e.inc += c.ex; else e.ref += c.ex;
        e.ex += c.ex; e.gst += c.gst; e.paid += c.paid; e.gt += c.gt; e.out += c.out;
        totalEx += c.ex;
        c.inv.cats.forEach(function (k) { e.cat[k] = (e.cat[k] || 0) + 1; });
        e.bk[c.inv.booking] = (e.bk[c.inv.booking] || 0) + 1;
        c.inv.mops.forEach(function (k) { e.mop[k] = 1; });
      });
      var rows = Object.keys(m).map(function (k) {
        var e = m[k];
        e.branches = Object.keys(e.br).sort().join(', ');
        e.invoices = keys(e.inv); e.clients = keys(e.cli);
        e.avg = e.invoices ? e.ex / e.invoices : 0;
        e.share = pct(e.ex, totalEx);
        e.topCat = lbl(top(e.cat)); e.topBk = lbl(top(e.bk));
        e.modes = Object.keys(e.mop).map(lbl).sort().join(', ');
        return e;
      }).sort(function (a, b) { return b.ex - a.ex; });
      rows.forEach(function (e, i) { e.rank = i + 1; });
      return rows;
    }
    function aggBranches(credits) {
      var m = {}, total = 0;
      credits.forEach(function (c) {
        var k = c.inv.branch || 'Unknown';
        var b = m[k] || (m[k] = { name: k, inv: {}, cli: {}, emp: {}, ex: 0, gst: 0, paid: 0, gt: 0, out: 0, ref: 0, inc: 0, cat: {}, bk: {} });
        b.inv[c.inv.invoice] = 1; b.cli[c.inv.customer] = 1; b.emp[c.key] = 1;
        b.ex += c.ex; b.gst += c.gst; b.paid += c.paid; b.gt += c.gt; b.out += c.out; total += c.ex;
        if (c.dual) { var s = c.refPart + c.incPart || 1; b.ref += c.ex * c.refPart / s; b.inc += c.ex * c.incPart / s; }
        else if (c.role === 'inc') b.inc += c.ex; else b.ref += c.ex;
        c.inv.cats.forEach(function (x) { b.cat[x] = (b.cat[x] || 0) + c.ex; });
        b.bk[c.inv.booking] = (b.bk[c.inv.booking] || 0) + 1;
      });
      var rows = Object.keys(m).map(function (k) {
        var b = m[k];
        b.invoices = keys(b.inv); b.clients = keys(b.cli); b.employees = keys(b.emp);
        b.share = pct(b.ex, total); b.avg = b.invoices ? b.ex / b.invoices : 0;
        b.topCat = lbl(top(b.cat)); b.topBk = lbl(top(b.bk));
        return b;
      }).sort(function (a, b) { return b.ex - a.ex; });
      rows.forEach(function (b, i) { b.rank = i + 1; });
      return rows;
    }
    function aggTree(credits, f) {
      var cats = {}, unm = {};
      function node(map, k) { return map[k] || (map[k] = { k: k, inv: {}, cli: {}, emp: {}, fs: {}, share: 0, full: 0, kids: {} }); }
      function add(n, amtv, c, ci) {
        n.share += amtv; n.inv[c.inv.invoice] = 1; n.cli[c.inv.customer] = 1; n.emp[c.key] = 1;
        if (!n.fs[ci]) { n.fs[ci] = 1; n.full += c.exFull; }
      }
      credits.forEach(function (c, ci) {
        var lines = f.treat ? c.inv.matched : c.inv.lines;
        lines.forEach(function (l) {
          var a = c.exFull * l.w / c.inv.totalW;
          var cn = node(cats, l.catKey), gn = node(cn.kids, l.grpKey), tn = node(gn.kids, l.type);
          add(cn, a, c, ci); add(gn, a, c, ci); add(tn, a, c, ci);
          if (l.catKey === NONE || l.grpKey === NONE) {
            var u = unm[l.type] || (unm[l.type] = { type: l.type, category: l.category, group: l.group, inv: {}, share: 0 });
            u.inv[c.inv.invoice] = 1; u.share += a;
          }
        });
      });
      function flat(map) {
        return Object.keys(map).map(function (k) {
          var n = map[k];
          return { k: k, invoices: keys(n.inv), clients: keys(n.cli), employees: keys(n.emp), share: n.share, full: n.full, kids: flat(n.kids) };
        }).sort(function (a, b) { return (a.k === NONE) - (b.k === NONE) || b.share - a.share; });
      }
      var tree = flat(cats);
      var total = tree.reduce(function (s, n) { return s + n.share; }, 0);
      var unmapped = Object.keys(unm).map(function (k) {
        var u = unm[k];
        return { type: u.type, category: u.category || NONE_LABEL, group: u.group || NONE_LABEL, invoices: keys(u.inv), share: u.share };
      }).sort(function (a, b) { return b.invoices - a.invoices; });
      return { tree: tree, total: total, unmapped: unmapped };
    }

    /* ─────────────── render helpers ─────────────── */
    function kpi(l, v, s, cls) {
      return '<div class="esr-kpi ' + (cls || '') + '"><div class="l">' + l + '</div><div class="v">' + v + '</div>' + (s ? '<div class="s">' + s + '</div>' : '') + '</div>';
    }
    function bars(el, items, cls) {
      if (!items.length) { el.innerHTML = '<div class="esr-empty">No data</div>'; return; }
      var max = Math.max.apply(null, items.map(function (i) { return i.value; })) || 1;
      el.innerHTML = items.map(function (i) {
        return '<div class="esr-bar ' + (cls || '') + '"><div class="esr-bar-l" title="' + esc(i.label) + '">' + esc(i.label) + (i.sub ? ' <small>' + esc(i.sub) + '</small>' : '') + '</div>' +
          '<div class="esr-bar-t"><div class="esr-bar-f" style="width:' + Math.max(1, Math.round(i.value / max * 100)) + '%"></div></div>' +
          '<div class="esr-bar-v">' + fmt(i.value) + (i.note ? '<small>' + esc(i.note) + '</small>' : '') + '</div></div>';
      }).join('');
    }
    function rankHtml(n) { return '<span class="esr-rank' + (n <= 3 ? ' r' + n : '') + '">' + n + '</span>'; }
    function pill(t, cls) { return t ? '<span class="esr-pill ' + (cls || '') + '">' + esc(t) + '</span>' : ''; }
    function pills(list, cls) { return '<div class="esr-pills">' + list.map(function (x) { return pill(lbl(x), x === NONE ? 'p-amber' : cls); }).join('') + '</div>'; }
    function invLink(inv) { return '<a class="esr-link" href="/app/sales-invoice/' + encodeURIComponent(inv) + '" target="_blank" rel="noopener">' + esc(inv) + '</a>'; }
    function outCls(v) { return v > 10000 ? 'esr-c-red' : v > 0.5 ? 'esr-c-amb' : 'esr-c-mute'; }

    /* ─────────────── column definitions ─────────────── */
    var COL = {
      employee: [
        { k: 'rank', l: '#', t: 'int', h: function (r) { return rankHtml(r.rank); }, search: false },
        { k: 'name', l: 'Employee', stick: true, h: function (r) { return '<strong>' + esc(r.name) + '</strong>'; } },
        { k: 'id', l: 'Emp ID', h: function (r) { return '<span class="esr-id">' + esc(r.id) + '</span>'; } },
        { k: 'branches', l: 'Branch' , cls: 'wrap' },
        { k: 'invoices', l: 'Invoices', t: 'int', sum: false, sumFn: function (rows) { return countUnique(rows, 'inv'); } },
        { k: 'clients', l: 'Clients', t: 'int', sumFn: function (rows) { return countUnique(rows, 'cli'); } },
        { k: 'ref', l: 'Referrer Share', t: 'amt', sum: true, cls: 'esr-c-ref' },
        { k: 'inc', l: 'Incentive Share', t: 'amt', sum: true, cls: 'esr-c-inc' },
        { k: 'ex', l: 'Paid ex-GST', t: 'amt', sum: true, cls: 'esr-c-main' },
        { k: 'gst', l: 'GST', t: 'amt', sum: true },
        { k: 'paid', l: 'Paid w/ GST', t: 'amt', sum: true },
        { k: 'out', l: 'Outstanding', t: 'amt', sum: true, cls: function (r) { return outCls(r.out); } },
        { k: 'avg', l: 'Avg / Invoice', t: 'amt' },
        { k: 'share', l: 'Share %', t: 'pct' },
        { k: 'topCat', l: 'Top Category', h: function (r) { return pill(r.topCat, 'p-teal'); } },
        { k: 'topBk', l: 'Top Booking', h: function (r) { return pill(r.topBk); } },
        { k: 'modes', l: 'Modes of Payment', cls: 'wrap' }
      ],
      branch: [
        { k: 'rank', l: '#', t: 'int', h: function (r) { return rankHtml(r.rank); }, search: false },
        { k: 'name', l: 'Branch', stick: true, h: function (r) { return '<strong>' + esc(r.name) + '</strong>'; } },
        { k: 'invoices', l: 'Invoices', t: 'int', sum: true },
        { k: 'clients', l: 'Clients', t: 'int', sum: true },
        { k: 'employees', l: 'Employees', t: 'int', sum: true },
        { k: 'ref', l: 'Referrer Share', t: 'amt', sum: true, cls: 'esr-c-ref' },
        { k: 'inc', l: 'Incentive Share', t: 'amt', sum: true, cls: 'esr-c-inc' },
        { k: 'ex', l: 'Paid ex-GST', t: 'amt', sum: true, cls: 'esr-c-main' },
        { k: 'gst', l: 'GST', t: 'amt', sum: true },
        { k: 'paid', l: 'Paid w/ GST', t: 'amt', sum: true },
        { k: 'gt', l: 'Grand Total', t: 'amt', sum: true, tip: 'Invoice grand total allocated by employee share' },
        { k: 'out', l: 'Outstanding', t: 'amt', sum: true, cls: function (r) { return outCls(r.out); } },
        { k: 'avg', l: 'Avg / Invoice', t: 'amt' },
        { k: 'share', l: 'Share %', t: 'pct' },
        { k: 'topCat', l: 'Top Category', h: function (r) { return pill(r.topCat, 'p-teal'); } },
        { k: 'topBk', l: 'Top Booking', h: function (r) { return pill(r.topBk); } }
      ],
      txn: [
        { k: 'invoice', l: 'Invoice', stick: true, h: function (r) { return invLink(r.invoice); } },
        { k: 'invoice_date', l: 'Invoice Date', t: 'date' },
        { k: 'payment_dates', l: 'Payment Date(s)', v: function (r) { return r.payment_dates; }, h: function (r) { return esc(dmyList(r.payment_dates)); } },
        { k: 'payment_ids', l: 'Payment IDs', cls: 'wrap', h: function (r) { return '<span class="esr-id">' + esc(r.payment_ids) + '</span>'; } },
        { k: 'branch', l: 'Branch', h: function (r) { return pill(r.branch); } },
        { k: 'customer', l: 'Customer' },
        { k: 'client_name', l: 'Client Name' },
        { k: 'booking', l: 'Booking Type', v: function (r) { return lbl(r.booking); }, h: function (r) { return pill(lbl(r.booking), r.booking === NONE ? 'p-amber' : ''); } },
        { k: 'sharing', l: 'Sharing Type', h: function (r) { return pill(r.sharing, /shared/i.test(r.sharing) ? 'p-purple' : 'p-grey'); } },
        { k: 'refName', l: 'Referring Employee', h: function (r) { return '<strong>' + esc(r.refName || '—') + '</strong>'; } },
        { k: 'refId', l: 'Ref Emp ID', v: function (r) { return r.refId || r.pracId; }, h: function (r) { return '<span class="esr-id">' + esc(r.refId || r.pracId) + '</span>'; } },
        { k: 'refShare', l: 'Ref Share ex-GST', t: 'amt', sum: true, cls: 'esr-c-ref' },
        { k: 'incName', l: 'Incentive Employee', h: function (r) { return '<strong>' + esc(r.incName || '—') + '</strong>'; } },
        { k: 'incId', l: 'Inc Emp ID', h: function (r) { return r.incName && !r.incId ? '<span class="esr-pill p-amber" title="Incentive employee name does not match an active Employee record">No ID</span>' : '<span class="esr-id">' + esc(r.incId) + '</span>'; } },
        { k: 'incShare', l: 'Inc Share ex-GST', t: 'amt', sum: true, cls: 'esr-c-inc' },
        { k: 'mop', l: 'Mode of Payment', cls: 'wrap' },
        { k: 'cats', l: 'Main Category', v: function (r) { return r.cats.map(lbl).join(', '); }, h: function (r) { return pills(r.cats, 'p-teal'); }, cls: 'wrap' },
        { k: 'grps', l: 'Therapy Group', v: function (r) { return r.grps.map(lbl).join(', '); }, h: function (r) { return pills(r.grps); }, cls: 'wrap' },
        { k: 'types', l: 'Therapy Types', v: function (r) { return r.types.join(', '); }, cls: 'wrap',
          h: function (r) { return '<span title="' + esc(r.types.join('\n')) + '">' + esc(r.types.slice(0, 2).join(', ')) + (r.types.length > 2 ? ' <b class="esr-c-mute">+' + (r.types.length - 2) + '</b>' : '') + '</span>'; } },
        { k: 'ex', l: 'Paid ex-GST', t: 'amt', sum: true, cls: 'esr-c-main' },
        { k: 'gst', l: 'GST', t: 'amt', sum: true },
        { k: 'paid', l: 'Paid w/ GST', t: 'amt', sum: true },
        { k: 'gt', l: 'Grand Total', t: 'amt', sum: true },
        { k: 'out', l: 'Outstanding', t: 'amt', sum: true, cls: function (r) { return outCls(r.out); }, tip: 'Current outstanding on the invoice' }
      ],
      booking: [
        { k: 'name', l: 'Booking Type', h: function (r) { return pill(r.name, r.raw === NONE ? 'p-amber' : ''); } },
        { k: 'invoices', l: 'Invoices', t: 'int', sum: true },
        { k: 'clients', l: 'Clients', t: 'int', sum: true },
        { k: 'ex', l: 'Paid ex-GST', t: 'amt', sum: true, cls: 'esr-c-main' },
        { k: 'gst', l: 'GST', t: 'amt', sum: true },
        { k: 'paid', l: 'Paid w/ GST', t: 'amt', sum: true },
        { k: 'out', l: 'Outstanding', t: 'amt', sum: true, cls: function (r) { return outCls(r.out); } },
        { k: 'share', l: 'Share %', t: 'pct' }
      ],
      unmapped: [
        { k: 'type', l: 'Therapy Type', h: function (r) { return '<strong>' + esc(r.type) + '</strong>'; } },
        { k: 'category', l: 'Main Category', h: function (r) { return r.category === NONE_LABEL ? pill(NONE_LABEL, 'p-amber') : esc(r.category); } },
        { k: 'group', l: 'Therapy Group', h: function (r) { return r.group === NONE_LABEL ? pill(NONE_LABEL, 'p-amber') : esc(r.group); } },
        { k: 'invoices', l: 'Invoices', t: 'int', sum: true },
        { k: 'share', l: 'Treatment Share ex-GST', t: 'amt', sum: true }
      ],
      drill: [
        { k: 'invoice', l: 'Invoice', h: function (r) { return invLink(r.invoice); } },
        { k: 'invoice_date', l: 'Inv Date', t: 'date' },
        { k: 'payment_dates', l: 'Paid On', h: function (r) { return esc(dmyList(r.payment_dates)); } },
        { k: 'branch', l: 'Branch' },
        { k: 'client', l: 'Client' },
        { k: 'booking', l: 'Booking', h: function (r) { return pill(r.booking); } },
        { k: 'roleL', l: 'Role', h: function (r) { return pill(r.roleL, r.roleL === 'Referrer' ? 'p-blue' : r.roleL === 'Incentive' ? 'p-orange' : 'p-purple'); } },
        { k: 'catL', l: 'Main Category', cls: 'wrap' },
        { k: 'typeL', l: 'Therapy Types', cls: 'wrap' },
        { k: 'mop', l: 'Mode', cls: 'wrap' },
        { k: 'ex', l: 'Share ex-GST', t: 'amt', sum: true, cls: 'esr-c-main' },
        { k: 'paid', l: 'Share w/ GST', t: 'amt', sum: true },
        { k: 'out', l: 'Outstanding (alloc.)', t: 'amt', sum: true, cls: function (r) { return outCls(r.out); } }
      ]
    };
    function countUnique(rows, field) {
      var o = {}; rows.forEach(function (r) { Object.keys(r[field] || {}).forEach(function (k) { o[k] = 1; }); });
      return keys(o).toLocaleString('en-IN');
    }

    /* ─────────────── render ─────────────── */
    function scheduleRender() { clearTimeout(S.renderTimer); S.renderTimer = setTimeout(renderNow, 120); }

    function renderNow() {
      if (!S.loaded) return;
      var V = compute();
      V.emp = aggEmployees(V.credits);
      V.br = aggBranches(V.credits);
      V.tr = aggTree(V.credits, V.f);
      S.view = V;
      renderChips(V.f);
      renderOverview(V);
      table('employee', COL.employee, V.emp, { what: 'employees', sort: 'ex', dir: -1, rowClick: drillEmployee });
      renderBranch(V);
      renderTreatment(V);
      table('txn', COL.txn, V.invs, { what: 'invoices', sort: 'invoice_date', dir: -1, limit: 200 });
      $('esr-tc-employee').textContent = V.emp.length;
      $('esr-tc-branch').textContent = V.br.length;
      $('esr-tc-treatment').textContent = V.tr.tree.length;
      $('esr-tc-txn').textContent = V.invs.length.toLocaleString('en-IN');
      if (!V.f.amountsOk) status('Amount range is invalid (From is greater than To) — that range is being ignored.', 'warn');
      else if ($('esr-status').querySelector('.esr-msg-warn') && S.raw.length) status('');
    }

    function totals(V) {
      var t = { ex: 0, gst: 0, paid: 0, out: 0, ref: 0, inc: 0, inv: {}, cli: {}, emp: {}, shared: {} };
      V.credits.forEach(function (c) {
        t.ex += c.ex; t.gst += c.gst; t.paid += c.paid; t.out += c.out;
        if (c.dual) { var s = c.refPart + c.incPart || 1; t.ref += c.ex * c.refPart / s; t.inc += c.ex * c.incPart / s; }
        else if (c.role === 'inc') t.inc += c.ex; else t.ref += c.ex;
        t.inv[c.inv.invoice] = 1; t.cli[c.inv.customer] = 1; t.emp[c.key] = 1;
        if (/shared/i.test(c.inv.sharing)) t.shared[c.inv.invoice] = 1;
      });
      t.invoices = keys(t.inv); t.clients = keys(t.cli); t.employees = keys(t.emp);
      return t;
    }

    function renderOverview(V) {
      var t = totals(V);
      var note = '';
      if (V.f.treat) {
        note = S.basis === 'full'
          ? '<div class="esr-msg esr-msg-info">Treatment filter is on · <b>Full Invoice</b> basis — amounts are the whole collection of every invoice whose plan includes the selected treatment. Switch Amount Basis to <b>Treatment Share</b> to see only that treatment’s portion.</div>'
          : '<div class="esr-msg esr-msg-info">Treatment filter is on · <b>Treatment Share</b> basis — each invoice’s collection is split across its plan’s therapy lines and only the selected treatment’s portion is counted.</div>';
      }
      if (V.empOn) note += (note ? '' : '') + '<div class="esr-msg esr-msg-info" style="margin-top:6px">Employee / role filter is on — amounts are the selected employees’ credited share only (shared invoices count half).</div>';
      $('esr-basis-note').innerHTML = note;

      $('esr-kpis').innerHTML =
        kpi('Invoices', t.invoices.toLocaleString('en-IN'), t.clients.toLocaleString('en-IN') + ' clients') +
        kpi('Employees Credited', t.employees.toLocaleString('en-IN'), keys(t.shared) + ' shared invoices', 'k-grey') +
        kpi('Paid ex-GST', fmt(t.ex), compact(t.ex), 'k-mint') +
        kpi('Referrer Share', fmt(t.ref), pct(t.ref, t.ex).toFixed(1) + '% of ex-GST', 'k-blue') +
        kpi('Incentive Share', fmt(t.inc), pct(t.inc, t.ex).toFixed(1) + '% of ex-GST', 'k-orange') +
        kpi('GST', fmt(t.gst), compact(t.gst), 'k-teal') +
        kpi('Paid w/ GST', fmt(t.paid), compact(t.paid)) +
        kpi('Avg per Invoice', fmt(t.invoices ? t.ex / t.invoices : 0), 'ex-GST', 'k-grey') +
        kpi('Current Outstanding', fmt(t.out), 'on credited invoices', 'k-red');

      bars($('esr-ov-emp'), V.emp.slice(0, 10).map(function (e) { return { label: e.name, sub: e.branches, value: e.ex, note: e.invoices + ' inv' }; }));
      bars($('esr-ov-branch'), V.br.map(function (b) { return { label: b.name, value: b.ex, note: b.share.toFixed(1) + '%' }; }));
      bars($('esr-ov-cat'), V.tr.tree.map(function (n) { return { label: lbl(n.k), value: n.share, note: pct(n.share, V.tr.total).toFixed(1) + '% · ' + n.invoices + ' inv' }; }), 'teal');

      var mm = {};
      V.credits.forEach(function (c) {
        var k = c.inv.mop || NONE_LABEL;
        var x = mm[k] || (mm[k] = { inv: {}, ex: 0 });
        x.inv[c.inv.invoice] = 1; x.ex += c.ex;
      });
      bars($('esr-ov-mop'), Object.keys(mm).map(function (k) { return { label: k, value: mm[k].ex, note: keys(mm[k].inv) + ' inv' }; })
        .sort(function (a, b) { return b.value - a.value; }).slice(0, 10));

      var bm = {}, tot = 0;
      V.credits.forEach(function (c) {
        var k = c.inv.booking;
        var b = bm[k] || (bm[k] = { raw: k, name: lbl(k), inv: {}, cli: {}, ex: 0, gst: 0, paid: 0, out: 0 });
        b.inv[c.inv.invoice] = 1; b.cli[c.inv.customer] = 1; b.ex += c.ex; b.gst += c.gst; b.paid += c.paid; b.out += c.out; tot += c.ex;
      });
      var brows = Object.keys(bm).map(function (k) { var b = bm[k]; b.invoices = keys(b.inv); b.clients = keys(b.cli); b.share = pct(b.ex, tot); return b; });
      V.booking = brows;
      table('booking', COL.booking, brows, { search: false, sort: 'ex', dir: -1 });
    }

    function renderBranch(V) {
      var t = totals(V), best = V.br[0];
      $('esr-br-kpis').innerHTML =
        kpi('Active Branches', V.br.length, '') +
        kpi('Paid ex-GST', fmt(t.ex), compact(t.ex), 'k-mint') +
        kpi('Top Branch', best ? esc(best.name) : '—', best ? fmt(best.ex) + ' · ' + best.share.toFixed(1) + '%' : '', 'k-teal') +
        kpi('Current Outstanding', fmt(t.out), compact(t.out), 'k-red');
      table('branch', COL.branch, V.br, { what: 'branches', sort: 'ex', dir: -1, rowClick: drillBranch });

      // Branch × Main Category (treatment share)
      var catOrder = V.tr.tree.map(function (n) { return n.k; });
      var mx = {};
      V.credits.forEach(function (c) {
        var lines = V.f.treat ? c.inv.matched : c.inv.lines;
        var b = mx[c.inv.branch] || (mx[c.inv.branch] = { name: c.inv.branch, total: 0 });
        lines.forEach(function (l) { var a = c.exFull * l.w / c.inv.totalW; b[l.catKey] = (b[l.catKey] || 0) + a; b.total += a; });
      });
      var cols = [{ k: 'name', l: 'Branch', stick: true, h: function (r) { return '<strong>' + esc(r.name) + '</strong>'; } }]
        .concat(catOrder.map(function (k) {
          return { k: k, l: lbl(k), t: 'amt', sum: true, v: function (r) { return r[k] || 0; }, h: function (r) { return r[k] ? fmt(r[k]) : '<span class="esr-c-mute">—</span>'; } };
        }))
        .concat([{ k: 'total', l: 'Total', t: 'amt', sum: true, cls: 'esr-c-main' }]);
      V.matrixCols = cols;
      V.matrix = Object.keys(mx).map(function (k) { return mx[k]; });
      table('matrix', cols, V.matrix, { search: false, sort: 'total', dir: -1 });
    }

    function renderTreatment(V) {
      var tr = V.tr, mapped = tr.tree.filter(function (n) { return n.k !== NONE; });
      var unmShare = tr.unmapped.reduce(function (s, u) { return s + u.share; }, 0);
      var topN = mapped[0];
      $('esr-tr-kpis').innerHTML =
        kpi('Main Categories', mapped.length, tr.tree.reduce(function (s, n) { return s + n.kids.length; }, 0) + ' therapy groups') +
        kpi('Treatment Share ex-GST', fmt(tr.total), compact(tr.total), 'k-mint') +
        kpi('Leading Category', topN ? esc(lbl(topN.k)) : '—', topN ? fmt(topN.share) + ' · ' + pct(topN.share, tr.total).toFixed(1) + '%' : '', 'k-teal') +
        kpi('Unmapped Treatments', tr.unmapped.length, fmt(unmShare) + ' missing category / group', tr.unmapped.length ? 'k-orange' : 'k-grey');

      var html = '', ci = 0;
      tr.tree.forEach(function (c) {
        var cid = 'c' + (ci++), open = S.treeOpen[cid] !== false;
        html += treeRow(c, 0, cid, '', false, open, tr.total);
        c.kids.forEach(function (g, gi) {
          var gid = cid + 'g' + gi, gopen = S.treeOpen[gid] === true;
          html += treeRow(g, 1, gid, cid, !open, gopen, tr.total);
          g.kids.forEach(function (t) { html += treeRow(t, 2, '', gid, !(open && gopen), false, tr.total); });
        });
      });
      if (tr.tree.length) {
        html += '<tr class="lv0"><td>Total</td><td class="n"></td><td class="n"></td><td class="n"></td><td class="n">' + fmt(tr.total) + '</td><td class="n">100.0%</td><td class="n"></td></tr>';
      }
      $('esr-tree-body').innerHTML = html || '<tr><td colspan="7"><div class="esr-empty">No data for the selected filters.</div></td></tr>';
      $('esr-unmapped-card').style.display = tr.unmapped.length ? '' : 'none';
      table('unmapped', COL.unmapped, tr.unmapped, { what: 'therapy types', sort: 'invoices', dir: -1 });
    }
    function treeRow(n, lv, id, parent, hidden, open, total) {
      var tg = lv < 2 && n.kids.length ? '<span class="tg" data-t="' + id + '">' + (open ? '−' : '+') + '</span>' : '';
      var p = pct(n.share, total);
      return '<tr class="lv' + lv + (hidden ? ' hide' : '') + '" data-id="' + id + '" data-p="' + parent + '">' +
        '<td>' + tg + (n.k === NONE ? pill(NONE_LABEL, 'p-amber') : esc(n.k)) + (lv < 2 ? ' <span class="esr-c-mute">(' + n.kids.length + ')</span>' : '') + '</td>' +
        '<td class="n">' + n.invoices.toLocaleString('en-IN') + '</td><td class="n">' + n.clients + '</td><td class="n">' + n.employees + '</td>' +
        '<td class="n esr-c-main">' + fmt(n.share) + '</td>' +
        '<td class="n"><span class="esr-share"><i style="width:' + Math.min(100, p).toFixed(1) + '%"></i></span>' + p.toFixed(1) + '%</td>' +
        '<td class="n esr-c-mute">' + fmt(n.full) + '</td></tr>';
    }
    $('esr-tree-body').addEventListener('click', function (e) {
      var tg = e.target.closest('.tg'); if (!tg) return;
      var id = tg.getAttribute('data-t'), body = $('esr-tree-body');
      var row = body.querySelector('tr[data-id="' + id + '"]');
      var lv1 = row.classList.contains('lv1');
      var opening = tg.textContent === '+';
      tg.textContent = opening ? '−' : '+';
      S.treeOpen[id] = opening;
      body.querySelectorAll('tr[data-p="' + id + '"]').forEach(function (ch) {
        ch.classList.toggle('hide', !opening);
        if (!lv1 && !opening) {
          body.querySelectorAll('tr[data-p="' + ch.getAttribute('data-id') + '"]').forEach(function (g) { g.classList.add('hide'); });
        } else if (!lv1 && opening && S.treeOpen[ch.getAttribute('data-id')] === true) {
          body.querySelectorAll('tr[data-p="' + ch.getAttribute('data-id') + '"]').forEach(function (g) { g.classList.remove('hide'); });
        }
      });
    });
    function treeAll(open) {
      var body = $('esr-tree-body');
      body.querySelectorAll('tr[data-p]').forEach(function (r) { if (r.getAttribute('data-p')) r.classList.toggle('hide', !open); });
      body.querySelectorAll('.tg').forEach(function (t) { t.textContent = open ? '−' : '+'; S.treeOpen[t.getAttribute('data-t')] = open; });
    }
    $('esr-tr-expand').addEventListener('click', function () { treeAll(true); });
    $('esr-tr-collapse').addEventListener('click', function () { treeAll(false); });

    /* ─────────────── drill-downs ─────────────── */
    var modal = $('esr-modal');
    function openModal(title, sub, html) {
      $('esr-modal-title').textContent = title;
      $('esr-modal-sub').textContent = sub || '';
      $('esr-modal-body').innerHTML = html;
      modal.classList.add('open');
      modal.setAttribute('aria-hidden', 'false');
    }
    function closeModal() { modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); }
    $('esr-modal-x').addEventListener('click', closeModal);
    modal.addEventListener('mousedown', function (e) { if (e.target === modal) closeModal(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && modal.classList.contains('open')) closeModal(); });

    function drillEmployee(e) {
      var rows = S.view.credits.filter(function (c) { return c.key === e.key; }).map(function (c) {
        return {
          invoice: c.inv.invoice, invoice_date: c.inv.invoice_date, payment_dates: c.inv.payment_dates, branch: c.inv.branch,
          client: c.inv.client_name || c.inv.customer, booking: lbl(c.inv.booking),
          roleL: c.dual ? 'Ref + Inc' : c.role === 'inc' ? 'Incentive' : 'Referrer',
          catL: c.inv.cats.map(lbl).join(', '), typeL: c.inv.types.join(', '), mop: c.inv.mop,
          ex: c.ex, paid: c.paid, out: c.out
        };
      });
      openModal(e.name, (e.id ? e.id + ' · ' : '') + e.branches,
        '<div class="esr-kpis">' +
        kpi('Invoices', e.invoices, e.clients + ' clients') +
        kpi('Paid ex-GST', fmt(e.ex), compact(e.ex), 'k-mint') +
        kpi('Referrer Share', fmt(e.ref), '', 'k-blue') +
        kpi('Incentive Share', fmt(e.inc), '', 'k-orange') +
        kpi('Outstanding', fmt(e.out), 'allocated', 'k-red') +
        '</div><div class="esr-card"><div class="esr-tblbox" id="esr-drill-box"></div></div>');
      delete S.tables.drill;
      table('drill', COL.drill, rows, { what: 'credits', sort: 'invoice_date', dir: -1 }, $('esr-drill-box'));
    }
    function drillBranch(b) {
      var emp = aggEmployees(S.view.credits.filter(function (c) { return c.inv.branch === b.name; }));
      openModal(b.name, b.invoices + ' invoices · ' + b.employees + ' employees · ' + fmt(b.ex) + ' ex-GST',
        '<div class="esr-card"><div class="esr-tblbox" id="esr-drill-box"></div></div>');
      delete S.tables.drillb;
      table('drillb', COL.employee, emp, { what: 'employees', sort: 'ex', dir: -1, rowClick: function (e) { closeModal(); setTimeout(function () { drillEmployee(e); }, 0); } }, $('esr-drill-box'));
    }

    /* ─────────────── chips ─────────────── */
    function renderChips(f) {
      var chips = [];
      function chip(name, text, clear) { chips.push({ name: name, text: text, clear: clear }); }
      if (f.branch && !S.locked) chip('Branch', f.branch, function () { $('esr-f-branch').value = ''; rebuildOptions(); });
      [['emp', 'Employee'], ['role', 'Role'], ['sharing', 'Sharing'], ['category', 'Main Category'], ['group', 'Therapy Group'], ['type', 'Therapy Type'], ['booking', 'Booking'], ['mop', 'Mode']].forEach(function (p) {
        var m = S.ms[p[0]], l = m.labels();
        if (l.length) chip(p[1], l.length > 3 ? l.slice(0, 3).join(', ') + ' +' + (l.length - 3) : l.join(', '), function () {
          m.set([], true);
          if (p[0] === 'category' || p[0] === 'group') rebuildTreatmentOptions();
        });
      });
      if (f.treat && S.basis === 'share') chip('Basis', 'Treatment Share', function () { setBasis('full'); });
      if (f.paidMin !== null || f.paidMax !== null) chip('Paid ex-GST', (f.paidMin !== null ? fmt(f.paidMin) : '0') + ' – ' + (f.paidMax !== null ? fmt(f.paidMax) : '∞'), function () { $('esr-f-paid-min').value = ''; $('esr-f-paid-max').value = ''; });
      if (f.outMin !== null || f.outMax !== null) chip('Outstanding', (f.outMin !== null ? fmt(f.outMin) : '0') + ' – ' + (f.outMax !== null ? fmt(f.outMax) : '∞'), function () { $('esr-f-out-min').value = ''; $('esr-f-out-max').value = ''; });
      if (f.onlyOut) chip('Only', 'with outstanding', function () { $('esr-f-onlyout').checked = false; });
      S.chips = chips;
      var el = $('esr-chips');
      el.innerHTML = chips.map(function (c, i) {
        return '<span class="esr-chip"><b>' + esc(c.name) + ':</b><span title="' + esc(c.text) + '">' + esc(c.text) + '</span><button type="button" data-i="' + i + '" title="Remove">&times;</button></span>';
      }).join('') + (chips.length > 1 ? '<span class="esr-chip esr-chip-clear" data-clear="1">Clear all filters</span>' : '');
    }
    $('esr-chips').addEventListener('click', function (e) {
      if (e.target.closest('[data-clear]')) { clearFilters(); renderNow(); return; }
      var b = e.target.closest('button[data-i]'); if (!b) return;
      S.chips[Number(b.getAttribute('data-i'))].clear();
      renderNow();
    });

    function clearFilters() {
      if (!S.locked) $('esr-f-branch').value = '';
      Object.keys(S.ms).forEach(function (k) { S.ms[k].set([], true); });
      ['esr-f-paid-min', 'esr-f-paid-max', 'esr-f-out-min', 'esr-f-out-max'].forEach(function (id) { $(id).value = ''; });
      $('esr-f-onlyout').checked = false;
      setBasis('full', true);
      if (S.loaded) rebuildOptions();
    }

    /* ─────────────── period / controls ─────────────── */
    function setRange(k) {
      var r = rangeFor(k);
      $('esr-f-from').value = iso(r.s);
      $('esr-f-to').value = iso(r.e);
      R.querySelectorAll('.esr-q').forEach(function (b) { b.classList.toggle('on', b.getAttribute('data-range') === k); });
    }
    function markDirty() {
      var dirty = S.loaded && ($('esr-f-from').value !== S.loaded.from || $('esr-f-to').value !== S.loaded.to);
      $('esr-btn-load').classList.toggle('esr-dirty', !!dirty);
      $('esr-btn-load').innerHTML = dirty ? '&#9654; Load New Period' : '&#9654; Load Data';
    }
    $('esr-quick').addEventListener('click', function (e) {
      var b = e.target.closest('.esr-q'); if (!b) return;
      setRange(b.getAttribute('data-range'));
      load();
    });
    ['esr-f-from', 'esr-f-to'].forEach(function (id) {
      $(id).addEventListener('change', function () {
        R.querySelectorAll('.esr-q').forEach(function (b) { b.classList.remove('on'); });
        markDirty();
      });
    });
    $('esr-btn-load').addEventListener('click', load);
    $('esr-f-branch').addEventListener('change', function () { if (S.loaded) rebuildOptions(); scheduleRender(); });
    $('esr-f-onlyout').addEventListener('change', scheduleRender);
    function setBasis(b, silent) {
      S.basis = b;
      $('esr-basis').querySelectorAll('button').forEach(function (x) { x.classList.toggle('on', x.getAttribute('data-basis') === b); });
      if (!silent) scheduleRender();
    }
    $('esr-basis').addEventListener('click', function (e) { var b = e.target.closest('button'); if (b) setBasis(b.getAttribute('data-basis')); });
    $('esr-btn-reset').addEventListener('click', function () {
      clearFilters();
      setRange('cycle');
      if (!S.loaded || $('esr-f-from').value !== S.loaded.from || $('esr-f-to').value !== S.loaded.to) load(); else renderNow();
    });
    $('esr-fcollapse').addEventListener('click', function () {
      var c = $('esr-filters').classList.toggle('collapsed');
      try { localStorage.setItem('esr-collapsed', c ? '1' : '0'); } catch (e) { /* storage unavailable */ }
    });
    try { if (localStorage.getItem('esr-collapsed') === '1') $('esr-filters').classList.add('collapsed'); } catch (e) { /* ignore */ }

    $('esr-tabs').addEventListener('click', function (e) {
      var t = e.target.closest('.esr-tab'); if (!t) return;
      S.tab = t.getAttribute('data-tab');
      R.querySelectorAll('.esr-tab').forEach(function (x) { x.classList.toggle('on', x === t); });
      R.querySelectorAll('.esr-pane').forEach(function (p) { p.classList.toggle('on', p.getAttribute('data-pane') === S.tab); });
      try { localStorage.setItem('esr-tab', S.tab); } catch (err) { /* ignore */ }
    });
    try {
      var savedTab = localStorage.getItem('esr-tab');
      if (savedTab) { var tb = R.querySelector('.esr-tab[data-tab="' + savedTab + '"]'); if (tb) tb.click(); }
    } catch (e) { /* ignore */ }

    $('esr-btn-print').addEventListener('click', function () { window.print(); });
    $('esr-btn-export').addEventListener('click', exportExcel);

    /* ─────────────── Excel export (multi-sheet SpreadsheetML) ─────────────── */
    function xesc(v) { return String(v === null || v === undefined ? '' : v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
    function xcols(cols) {
      return cols.filter(function (c) { return c.k !== 'rank' || true; }).map(function (c) {
        return { l: c.l, n: isNum(c) && c.t !== 'pct' ? 'n' : c.t === 'pct' ? 'p' : 's', v: function (r) {
          var v = cellVal(c, r);
          if (c.t === 'date') return dmy(v);
          if (c.k === 'payment_dates') return dmyList(v);
          if (Array.isArray(v)) return v.map(lbl).join(', ');
          if (c.t === 'amt') return r2(v);
          if (c.t === 'pct') return Math.round(num(v) * 10) / 10;
          return v === NONE ? NONE_LABEL : v;
        } };
      });
    }
    function sheet(name, cols, rows) {
      var x = '<Worksheet ss:Name="' + xesc(name).slice(0, 31) + '"><Table>';
      x += '<Row>' + cols.map(function (c) { return '<Cell ss:StyleID="h"><Data ss:Type="String">' + xesc(c.l) + '</Data></Cell>'; }).join('') + '</Row>';
      rows.forEach(function (r) {
        x += '<Row>' + cols.map(function (c) {
          var v = c.v(r);
          if ((c.n === 'n' || c.n === 'p') && v !== '' && isFinite(Number(v))) return '<Cell ss:StyleID="' + (c.n === 'p' ? 'p' : 'm') + '"><Data ss:Type="Number">' + Number(v) + '</Data></Cell>';
          return '<Cell><Data ss:Type="String">' + xesc(v) + '</Data></Cell>';
        }).join('') + '</Row>';
      });
      x += '</Table><WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel"><FreezePanes/><FrozenNoSplit/><SplitHorizontal>1</SplitHorizontal><TopRowBottomPane>1</TopRowBottomPane><ActivePane>2</ActivePane></WorksheetOptions></Worksheet>';
      return x;
    }
    function exportExcel() {
      if (!S.view || !S.loaded) { frappe.msgprint('Load the report first.'); return; }
      var V = S.view;
      if (!V.invs.length) { frappe.msgprint('No records match the current filters.'); return; }
      var f = V.f;
      var meta = [
        ['Report', 'Employee Sale Report'], ['Source', REPORT_NAME],
        ['Payment period', dmy(S.loaded.from) + ' to ' + dmy(S.loaded.to)],
        ['Branch', f.branch || S.locked || (S.restricted ? 'All Permitted Branches' : 'All Branches')],
        ['Amount basis', f.treat ? (S.basis === 'share' ? 'Treatment Share' : 'Full Invoice') : 'Full Invoice']
      ];
      [['emp', 'Employee'], ['role', 'Credit Role'], ['sharing', 'Sharing Type'], ['category', 'Main Category'], ['group', 'Therapy Group'], ['type', 'Therapy Type'], ['booking', 'Booking Type'], ['mop', 'Mode of Payment']].forEach(function (p) {
        var l = S.ms[p[0]].labels(); if (l.length) meta.push([p[1], l.join(', ')]);
      });
      if (f.paidMin !== null || f.paidMax !== null) meta.push(['Paid ex-GST range', (f.paidMin || 0) + ' to ' + (f.paidMax !== null ? f.paidMax : 'any')]);
      if (f.outMin !== null || f.outMax !== null) meta.push(['Outstanding range', (f.outMin || 0) + ' to ' + (f.outMax !== null ? f.outMax : 'any')]);
      if (f.onlyOut) meta.push(['Only', 'Invoices with outstanding']);
      meta.push(['Exported by', (frappe.session && frappe.session.user) || '']);
      meta.push(['Exported at', new Date().toLocaleString('en-IN')]);

      var treeRows = [];
      V.tr.tree.forEach(function (c) {
        c.kids.forEach(function (g) {
          g.kids.forEach(function (t) {
            treeRows.push({ cat: lbl(c.k), grp: lbl(g.k), type: t.k, invoices: t.invoices, clients: t.clients, employees: t.employees, share: t.share, pct: pct(t.share, V.tr.total), full: t.full });
          });
        });
      });
      var treeCols = [
        { l: 'Main Category', n: 's', v: function (r) { return r.cat; } }, { l: 'Therapy Group', n: 's', v: function (r) { return r.grp; } },
        { l: 'Therapy Type', n: 's', v: function (r) { return r.type; } }, { l: 'Invoices', n: 'n', v: function (r) { return r.invoices; } },
        { l: 'Clients', n: 'n', v: function (r) { return r.clients; } }, { l: 'Employees', n: 'n', v: function (r) { return r.employees; } },
        { l: 'Treatment Share ex-GST', n: 'n', v: function (r) { return r2(r.share); } }, { l: 'Share %', n: 'p', v: function (r) { return Math.round(r.pct * 10) / 10; } },
        { l: 'Full-Invoice ex-GST', n: 'n', v: function (r) { return r2(r.full); } }
      ];
      var empCols = xcols(COL.employee.map(function (c) { return c.k === 'invoices' || c.k === 'clients' ? Object.assign({}, c, { t: 'int' }) : c; }));

      var xml = '<?xml version="1.0"?><?mso-application progid="Excel.Sheet"?>' +
        '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">' +
        '<Styles><Style ss:ID="h"><Font ss:Bold="1" ss:Color="#FFFFFF"/><Interior ss:Color="#1B5E20" ss:Pattern="Solid"/></Style>' +
        '<Style ss:ID="m"><NumberFormat ss:Format="#,##0.00"/></Style><Style ss:ID="p"><NumberFormat ss:Format="0.0"/></Style><Style ss:ID="k"><Font ss:Bold="1" ss:Color="#0F3D1E"/></Style></Styles>' +
        '<Worksheet ss:Name="Filters"><Table><Column ss:Width="140"/><Column ss:Width="420"/>' +
        meta.map(function (m) { return '<Row><Cell ss:StyleID="k"><Data ss:Type="String">' + xesc(m[0]) + '</Data></Cell><Cell><Data ss:Type="String">' + xesc(m[1]) + '</Data></Cell></Row>'; }).join('') +
        '</Table></Worksheet>' +
        sheet('Transactions', xcols(COL.txn), V.invs) +
        sheet('Employee Wise', empCols, V.emp) +
        sheet('Branch Wise', xcols(COL.branch), V.br) +
        sheet('Treatment Detail', treeCols, treeRows) +
        sheet('Branch x Category', xcols(V.matrixCols), V.matrix) +
        sheet('Booking Type', xcols(COL.booking), V.booking) +
        (V.tr.unmapped.length ? sheet('Unmapped Treatments', xcols(COL.unmapped), V.tr.unmapped) : '') +
        '</Workbook>';

      var blob = new Blob([xml], { type: 'application/vnd.ms-excel;charset=utf-8' });
      var a = document.createElement('a');
      var br = (f.branch || S.locked || 'All').replace(/[^\w-]+/g, '_');
      a.href = URL.createObjectURL(blob);
      a.download = 'LIFE_Employee_Sale_' + br + '_' + S.loaded.from + '_to_' + S.loaded.to + '.xls';
      document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
    }

    /* ─────────────── boot ─────────────── */
    setRange('cycle');
    loadBranches().then(function () {
      initBranchSelect();
      load();
    }).catch(function (e) {
      void 0;
      status('Branch access could not be verified for this login. Report loading has been blocked.', 'err');
      $('esr-btn-load').disabled = true;
    });
  }
})();
return { refresh: () => document.getElementById('esr-generate')?.click() };
}
