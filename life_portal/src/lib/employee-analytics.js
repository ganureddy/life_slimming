// Pure report calculations. Rendering and selection state belong to Vue.
export const NONE='__NONE__';
export function createEmployeeAnalytics(S){
const NONE_LABEL='(Unmapped)',NO_LINES='(No therapy lines)',today=new Date(),MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function num(v) { var n = Number(v); return isFinite(n) ? n : 0; }

function r2(v) { return Math.round((num(v) + Number.EPSILON) * 100) / 100; }

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
      if (f === 1) return { ...r, factor: 1 };
      var v = Object.assign({}, r);
      v.factor = f;
      ['paid', 'gst', 'ex', 'refShare', 'incShare', 'dist', 'gt', 'out'].forEach(function (k) { v[k] = r[k] * f; });
      return v;
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

function compute(f) {
      var invs = [];
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

function countUnique(rows, field) {
      var o = {}; rows.forEach(function (r) { Object.keys(r[field] || {}).forEach(function (k) { o[k] = 1; }); });
      return keys(o).toLocaleString('en-IN');
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

function outCls(v) { return v > 10000 ? 'esr-c-red' : v > 0.5 ? 'esr-c-amb' : 'esr-c-mute'; }
const columns={
      employee: [
        { k: 'rank', l: '#', t: 'int', search: false },
        { k: 'name', l: 'Employee', stick: true},
        { k: 'id', l: 'Emp ID'},
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
        { k: 'topCat', l: 'Top Category'},
        { k: 'topBk', l: 'Top Booking'},
        { k: 'modes', l: 'Modes of Payment', cls: 'wrap' }
      ],
      branch: [
        { k: 'rank', l: '#', t: 'int', search: false },
        { k: 'name', l: 'Branch', stick: true},
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
        { k: 'topCat', l: 'Top Category'},
        { k: 'topBk', l: 'Top Booking'}
      ],
      txn: [
        { k: 'invoice', l: 'Invoice', stick: true},
        { k: 'invoice_date', l: 'Invoice Date', t: 'date' },
        { k: 'payment_dates', l: 'Payment Date(s)', v: function (r) { return r.payment_dates; }},
        { k: 'payment_ids', l: 'Payment IDs', cls: 'wrap'},
        { k: 'branch', l: 'Branch'},
        { k: 'customer', l: 'Customer' },
        { k: 'client_name', l: 'Client Name' },
        { k: 'booking', l: 'Booking Type', v: function (r) { return lbl(r.booking); }},
        { k: 'sharing', l: 'Sharing Type'},
        { k: 'refName', l: 'Referring Employee'},
        { k: 'refId', l: 'Ref Emp ID', v: function (r) { return r.refId || r.pracId; }},
        { k: 'refShare', l: 'Ref Share ex-GST', t: 'amt', sum: true, cls: 'esr-c-ref' },
        { k: 'incName', l: 'Incentive Employee'},
        { k: 'incId', l: 'Inc Emp ID'},
        { k: 'incShare', l: 'Inc Share ex-GST', t: 'amt', sum: true, cls: 'esr-c-inc' },
        { k: 'mop', l: 'Mode of Payment', cls: 'wrap' },
        { k: 'cats', l: 'Main Category', v: function (r) { return r.cats.map(lbl).join(', '); }, cls: 'wrap' },
        { k: 'grps', l: 'Therapy Group', v: function (r) { return r.grps.map(lbl).join(', '); }, cls: 'wrap' },
        { k: 'types', l: 'Therapy Types', v: function (r) { return r.types.join(', '); }, cls: 'wrap'},
        { k: 'ex', l: 'Paid ex-GST', t: 'amt', sum: true, cls: 'esr-c-main' },
        { k: 'gst', l: 'GST', t: 'amt', sum: true },
        { k: 'paid', l: 'Paid w/ GST', t: 'amt', sum: true },
        { k: 'gt', l: 'Grand Total', t: 'amt', sum: true },
        { k: 'out', l: 'Outstanding', t: 'amt', sum: true, cls: function (r) { return outCls(r.out); }, tip: 'Current outstanding on the invoice' }
      ],
      booking: [
        { k: 'name', l: 'Booking Type'},
        { k: 'invoices', l: 'Invoices', t: 'int', sum: true },
        { k: 'clients', l: 'Clients', t: 'int', sum: true },
        { k: 'ex', l: 'Paid ex-GST', t: 'amt', sum: true, cls: 'esr-c-main' },
        { k: 'gst', l: 'GST', t: 'amt', sum: true },
        { k: 'paid', l: 'Paid w/ GST', t: 'amt', sum: true },
        { k: 'out', l: 'Outstanding', t: 'amt', sum: true, cls: function (r) { return outCls(r.out); } },
        { k: 'share', l: 'Share %', t: 'pct' }
      ],
      unmapped: [
        { k: 'type', l: 'Therapy Type'},
        { k: 'category', l: 'Main Category'},
        { k: 'group', l: 'Therapy Group'},
        { k: 'invoices', l: 'Invoices', t: 'int', sum: true },
        { k: 'share', l: 'Treatment Share ex-GST', t: 'amt', sum: true }
      ],
      drill: [
        { k: 'invoice', l: 'Invoice'},
        { k: 'invoice_date', l: 'Inv Date', t: 'date' },
        { k: 'payment_dates', l: 'Paid On'},
        { k: 'branch', l: 'Branch' },
        { k: 'client', l: 'Client' },
        { k: 'booking', l: 'Booking'},
        { k: 'roleL', l: 'Role'},
        { k: 'catL', l: 'Main Category', cls: 'wrap' },
        { k: 'typeL', l: 'Therapy Types', cls: 'wrap' },
        { k: 'mop', l: 'Mode', cls: 'wrap' },
        { k: 'ex', l: 'Share ex-GST', t: 'amt', sum: true, cls: 'esr-c-main' },
        { k: 'paid', l: 'Share w/ GST', t: 'amt', sum: true },
        { k: 'out', l: 'Outstanding (alloc.)', t: 'amt', sum: true, cls: function (r) { return outCls(r.out); } }
      ]
    };
return {num,r2,clean,lc,fmt,compact,pct,iso,dmy,dmyList,keys,top,lbl,uniq,cycleOf,rangeFor,parseLines,normalize,buildAlias,empKey,buildCredits,scaleInv,lineOk,roleOk,compute,aggEmployees,aggBranches,aggTree,countUnique,totals,outCls,columns};
}
