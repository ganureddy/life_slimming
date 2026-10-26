// Invoice normalization and employee allocation rules owned by Vue.
const num = value => Number.isFinite(Number(value)) ? Number(value) : 0;
export function normalizeReportRow(row) {
    row = row || {};

    var oldCreditType = String(row.credit_type || '').toLowerCase();

    var refName = row.referring_employee || row.custom_referring_name ||
      (oldCreditType === 'ref' ? row.sales_person_name : '') || '';

    var incName = row.incentive_employee || row.custom_incentive_employee_name ||
      (oldCreditType === 'incentive' ? row.sales_person_name : '') || '';

    var refEmployeeId = row.referring_employee_id ||
      (oldCreditType === 'ref' ? row.employee_id : '') || '';

    var incEmployeeId = row.incentive_employee_id ||
      (oldCreditType === 'incentive' ? row.employee_id : '') || '';

    var refPractitionerId = row.referring_practitioner_id ||
      row.sales_person_id || row.ref_practitioner || '';

    var paid = num(row.paid_amount);
    var exGst = num(row.paid_amount_without_gst);
    if (!exGst) exGst = num(row.paid_amount_without_tax);

    var gst = num(row.gst_amount);
    if (!gst) gst = num(row.tax_amount);

    if (!exGst && paid) exGst = paid / 1.05;
    if (!gst && paid) gst = paid - exGst;

    var refShare = num(row.referring_employee_share);
    var incShare = num(row.incentive_employee_share);

    /* Backward compatibility for old report output. */
    if (!refShare && !incShare && exGst) {
      if (oldCreditType === 'ref') {
        refShare = exGst;
      } else if (oldCreditType === 'incentive') {
        incShare = exGst;
      } else if (refName && incName) {
        refShare = exGst / 2;
        incShare = exGst - refShare;
      } else if (refName) {
        refShare = exGst;
      } else if (incName) {
        incShare = exGst;
      }
    }

    var employeeCount = num(row.employee_count);

    var refIdNorm = String(refEmployeeId || '')
      .normalize('NFKC')
      .replace(/\u00A0/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();

    var incIdNorm = String(incEmployeeId || '')
      .normalize('NFKC')
      .replace(/\u00A0/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();

    /*
      If both fields resolve to the same Employee ID, this is one employee,
      not two different employees.
    */
    if (refIdNorm && incIdNorm && refIdNorm === incIdNorm) {
      employeeCount = 1;
    } else if (!employeeCount) {
      employeeCount = (refName ? 1 : 0) + (incName ? 1 : 0);
    }

    return {
      invoice: row.invoice || '',
      invoice_date: row.invoice_date || row.posting_date || '',
      posting_date: row.invoice_date || row.posting_date || '',
      branch: row.branch || '',
      customer: row.customer || '',
      client_name: row.client_name || row.patient_name || '',
      booking_type: row.booking_type || row.media || '',

      payment_ids: row.payment_ids || '',
      payment_dates: row.payment_dates || '',
      mode_of_payment: row.mode_of_payment || '',

      referring_employee: refName,
      referring_practitioner_id: refPractitionerId,
      referring_employee_id: refEmployeeId,
      incentive_employee: incName,
      incentive_employee_id: incEmployeeId,

      sharing_type: row.sharing_type || '',
      employee_count: employeeCount,

      paid_amount: paid,
      gst_amount: gst,
      tax_amount: gst,
      paid_amount_without_gst: exGst,
      paid_amount_without_tax: exGst,
      referring_employee_share: refShare,
      incentive_employee_share: incShare,
      total_distributed_amount: num(row.total_distributed_amount) || exGst,
      grand_total: num(row.grand_total),
      outstanding_amount: num(row.outstanding_amount)
    };
  }

export function buildEmployeeCreditRows(invoiceRows) {
    var credits = [];

    (invoiceRows || []).forEach(function (r) {
      var totalEx = num(r.total_distributed_amount) || num(r.paid_amount_without_gst);

      function normId(v) {
        return String(v || '')
          .normalize('NFKC')
          .replace(/\u00A0/g, ' ')
          .replace(/\s+/g, ' ')
          .trim()
          .toLowerCase();
      }

      function pushCredit(type, name, employeeId, practitionerId, share) {
        share = num(share);
        if (!name || share <= 0) return;

        var ratio = totalEx > 0 ? share / totalEx : 1;
        if (!isFinite(ratio) || ratio < 0) ratio = 0;
        if (ratio > 1) ratio = 1;

        credits.push({
          invoice: r.invoice,
          invoice_date: r.invoice_date,
          posting_date: r.invoice_date,
          branch: r.branch,
          customer: r.customer,
          client_name: r.client_name,
          booking_type: r.booking_type,
          payment_ids: r.payment_ids,
          payment_dates: r.payment_dates,
          mode_of_payment: r.mode_of_payment,

          credit_type: type,
          sales_person_name: name,
          employee_id: employeeId || '',
          sales_person_id: practitionerId || '',

          paid_amount_without_tax: share,
          paid_amount_without_gst: share,
          tax_amount: num(r.gst_amount) * ratio,
          gst_amount: num(r.gst_amount) * ratio,
          paid_amount: num(r.paid_amount) * ratio,
          grand_total: num(r.grand_total) * ratio,
          outstanding_amount: num(r.outstanding_amount) * ratio
        });
      }

      var refId = normId(r.referring_employee_id);
      var incId = normId(r.incentive_employee_id);

      /*
        Same employee used as both Referring and Incentive:
        create ONE employee-credit row for this invoice.
        This prevents duplicate employee records in Employee Wise summary.
      */
      if (refId && incId && refId === incId) {
        var combinedShare =
          num(r.referring_employee_share) +
          num(r.incentive_employee_share);

        if (!combinedShare) {
          combinedShare = totalEx;
        }

        pushCredit(
          'ref',
          r.referring_employee || r.incentive_employee,
          r.referring_employee_id || r.incentive_employee_id,
          r.referring_practitioner_id,
          combinedShare
        );

        return;
      }

      pushCredit(
        'ref',
        r.referring_employee,
        r.referring_employee_id,
        r.referring_practitioner_id,
        r.referring_employee_share
      );

      pushCredit(
        'incentive',
        r.incentive_employee,
        r.incentive_employee_id,
        '',
        r.incentive_employee_share
      );
    });

    return credits;
  }


export function groupEmployeeCredits(data) {
 let EMPLOYEE_NAME_ID_MAP = {};
  function normalizedEmployeeName(v) {
    return String(v || '')
      .normalize('NFKC')
      .replace(/\u00A0/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
  }

  function normalizedEmployeeId(v) {
    return String(v || '')
      .normalize('NFKC')
      .replace(/\u00A0/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
  }

  function rebuildEmployeeNameIdMap(rows) {
    var candidates = {};

    (rows || []).forEach(function (r) {
      var nameKey = normalizedEmployeeName(r && r.sales_person_name);
      var employeeId = normalizedEmployeeId(r && r.employee_id);

      if (!nameKey || !employeeId) return;

      if (!candidates[nameKey]) {
        candidates[nameKey] = {};
      }

      candidates[nameKey][employeeId] = true;
    });

    EMPLOYEE_NAME_ID_MAP = {};

    Object.keys(candidates).forEach(function (nameKey) {
      var ids = Object.keys(candidates[nameKey]);

      /*
        Only create an alias when the visible name resolves unambiguously
        to one Employee ID. If two different Employee IDs genuinely share
        the same display name, keep them separate.
      */
      if (ids.length === 1) {
        EMPLOYEE_NAME_ID_MAP[nameKey] = ids[0];
      }
    });

    void 0;
  }

  function employeeGroupKey(r) {
    r = r || {};

    var employeeId = normalizedEmployeeId(r.employee_id);
    if (employeeId) {
      return 'employee|' + employeeId;
    }

    var nameKey = normalizedEmployeeName(r.sales_person_name);

    /*
      If this row has no Employee ID but another row with the same visible
      name has one, group this row under that real Employee ID.
    */
    if (nameKey && EMPLOYEE_NAME_ID_MAP[nameKey]) {
      return 'employee|' + EMPLOYEE_NAME_ID_MAP[nameKey];
    }

    /*
      Practitioner ID is used only when Employee ID and name-to-ID alias
      are unavailable.
    */
    var practitionerId = normalizedEmployeeId(r.sales_person_id);
    if (practitionerId) {
      return 'practitioner|' + practitionerId;
    }

    return 'name|' + nameKey;
  }

  function cleanEmployeeDisplayName(v) {
    return String(v || '')
      .normalize('NFKC')
      .replace(/\u00A0/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }


rebuildEmployeeNameIdMap(data);
    var empMap = {};

    (data || []).forEach(function (r) {
      var key = employeeGroupKey(r);
      var displayName = cleanEmployeeDisplayName(r.sales_person_name) || '(No Employee)';

      if (!empMap[key]) {
        var groupedEmpId =
          r.employee_id ||
          EMPLOYEE_NAME_ID_MAP[normalizedEmployeeName(r.sales_person_name)] ||
          r.sales_person_id ||
          '';

        empMap[key] = {
          name: displayName,
          empId: groupedEmpId,
          branches: [],
          invoiceSeen: {},
          cnt: 0,
          paid: 0,
          tax: 0,
          exTax: 0,
          gt: 0,
          out: 0,
          refEx: 0,
          incEx: 0,
          bkCounts: {},
          modes: []
        };
      }

      var e = empMap[key];

      /* Prefer a real Employee ID over a Practitioner ID whenever available. */
      if (r.employee_id) {
        e.empId = r.employee_id;
      } else if (!e.empId && r.sales_person_id) {
        e.empId = r.sales_person_id;
      }

      if (r.branch && e.branches.indexOf(r.branch) < 0) e.branches.push(r.branch);

      if (!e.invoiceSeen[r.invoice]) {
        e.invoiceSeen[r.invoice] = true;
        e.cnt += 1;
      }

      e.paid += num(r.paid_amount);
      e.tax += num(r.tax_amount);
      e.exTax += num(r.paid_amount_without_tax);
      e.gt += num(r.grand_total);
      e.out += num(r.outstanding_amount);

      if (String(r.credit_type || '').toLowerCase() === 'incentive') {
        e.incEx += num(r.paid_amount_without_tax);
      } else {
        e.refEx += num(r.paid_amount_without_tax);
      }

      var bt = r.booking_type || 'Unknown';
      e.bkCounts[bt] = (e.bkCounts[bt] || 0) + 1;

      if (r.mode_of_payment) {
        String(r.mode_of_payment).split(',').forEach(function (mo) {
          var mt = mo.trim();
          if (mt && e.modes.indexOf(mt) < 0) e.modes.push(mt);
        });
      }
    });

    var rows = Object.values(empMap)
      .map(function (e) {
        e.branch = e.branches.join(', ');
        return e;
      })
      .sort(function (a, b) { return b.exTax - a.exTax; });


return rows;
}
export function groupBranchCredits(employeeCredits) {
    var bMap = {};

    employeeCredits.forEach(function (r) {
      var key = r.branch || 'Unknown';
      if (!bMap[key]) {
        bMap[key] = {
          name: key,
          invoiceSeen: {},
          cnt: 0,
          paid: 0,
          tax: 0,
          exTax: 0,
          gt: 0,
          out: 0,
          emps: [],
          bkCounts: {}
        };
      }

      var b = bMap[key];
      if (r.invoice && !b.invoiceSeen[r.invoice]) {
        b.invoiceSeen[r.invoice] = true;
        b.cnt += 1;
      }

      b.paid += num(r.paid_amount);
      b.tax += num(r.tax_amount);
      b.exTax += num(r.paid_amount_without_tax);
      b.gt += num(r.grand_total);
      b.out += num(r.outstanding_amount);

      if (r.sales_person_name && b.emps.indexOf(r.sales_person_name) < 0) {
        b.emps.push(r.sales_person_name);
      }

      var bt = r.booking_type || 'Unknown';
      b.bkCounts[bt] = (b.bkCounts[bt] || 0) + 1;
    });

    var rows = Object.values(bMap).sort(function (a, b) { return b.exTax - a.exTax; });

return rows;
}
