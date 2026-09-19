"""lifescc.billing.create_plan_and_invoice

Original API: lifescc.billing.create_plan_and_invoice
Source modified: 2026-08-23 13:38:17.566795
See ../CATALOG.md for migration notes and validation limits.
"""

import json
import re

import frappe
from frappe.integrations.utils import make_post_request as _make_post_request
from frappe.utils.safe_exec import read_sql as _read_sql
from frappe.utils.safe_exec import call_whitelisted_function as _call_whitelisted
from life_slimming.api._runtime import script_endpoint


@script_endpoint(allow_guest=False)
def run(**kwargs):









    # # ═══════════════════════════════════════════════════════════════════
    # # SERVER SCRIPT  #2   (the heart of the flow)   ·   v12
    # # Type:        API
    # # Method Name: lifescc.billing.create_plan_and_invoice
    # # Allow Guest: No
    # #
    # # Purpose:  One call =
    # #   Therapy Plan  ->  Sales Invoice (discount + complimentary + GST 5%)
    # #   ->  Payment Entry (collection).
    # #
    # # v12 CHANGES (two additions, everything else identical):
    # #   A) draft_only : when 1, the invoice is LEFT AS A DRAFT (not submitted)
    # #      and NO Payment Entry is created. Used by the discount-approval flow:
    # #      the page creates the draft, then raises a Discount Approval Request;
    # #      collection happens after approval. When 0 (default) the original
    # #      one-shot submit + mandatory-payment behaviour runs unchanged.
    # #   B) per-line offers : each line may carry use_offer=1 + offer_rule.
    # #      If ANY line uses an offer we DO NOT force ignore_pricing_rule=1,
    # #      so the Pricing Rule engine applies the offer. If no line uses an
    # #      offer, ignore_pricing_rule stays 1 (manual rate, as before).
    # #
    # # INPUT (frappe.form_dict):
    # #   patient, branch, consultant
    # #   lines : JSON [{therapy_type, no_of_sessions, rate, use_offer?, offer_rule?}]
    # #   comps : JSON [{item_code, item_name, qty, comp_price, max_qty_allowed}]
    # #   draft_only            : 0/1   (NEW)
    # #   discount_pct          : cumulative % (0-15)   (only used when draft_only=0)
    # #   discount_by           : approver label
    # #   advance_amount        : amount to collect now (required when draft_only=0)
    # #   advance_mode, advance_ref, posting_date
    # # ═══════════════════════════════════════════════════════════════════

    # args = frappe.form_dict

    # patient        = args.get("patient")
    # branch         = args.get("branch")
    # consultant     = args.get("consultant") or ""
    # # the page now sends a Healthcare Practitioner ID for the consultant —
    # # convert it to the person's name for the name fields
    # if consultant and frappe.db.exists("Healthcare Practitioner", consultant):
    #     cons_nm = frappe.db.get_value(
    #         "Healthcare Practitioner", consultant, "practitioner_name")
    #     if cons_nm:
    #         consultant = cons_nm
    # practitioner   = args.get("practitioner") or ""
    # draft_only     = int(args.get("draft_only") or 0)          # NEW
    # discount_pct   = float(args.get("discount_pct") or 0)
    # discount_by    = args.get("discount_by") or ""
    # advance_amount = float(args.get("advance_amount") or 0)
    # advance_mode   = args.get("advance_mode") or "Cash"
    # advance_ref    = args.get("advance_ref") or ""
    # posting_date   = args.get("posting_date") or frappe.utils.today()

    # def load_json(raw):
    #     # safe_exec forbids "import", but it DOES provide a `json` global with
    #     # loads/dumps — so json.loads works, frappe.parse_json does not.
    #     if isinstance(raw, str):
    #         if not raw:
    #             return []
    #         return json.loads(raw)
    #     return raw or []

    # lines = load_json(args.get("lines"))
    # comps = load_json(args.get("comps"))

    # # does any line opt into an offer? -> then let pricing rules apply
    # any_offer = 0
    # for ln in lines:
    #     if int(ln.get("use_offer") or 0):
    #         any_offer = 1

    # def fail(msg):
    #     frappe.response["message"] = {"error": msg}

    # # ── top-level validation ────────────────────────────────────────────
    # if not patient:
    #     fail("Patient is required")

    # elif not lines:
    #     fail("At least one therapy line is required")

    # elif discount_pct > 15:
    #     fail("Discount cannot exceed 15%")

    # # Payment is mandatory ONLY on the normal (non-draft) path.
    # elif (not draft_only) and advance_amount <= 0:
    #     fail("A collection amount is required. Enter the amount received to generate the bill.")

    # elif (not draft_only) and advance_mode not in ("Cash",) and not advance_ref:
    #     fail("Reference / UTR number is required for " + str(advance_mode))

    # else:
    #     pat = frappe.db.get_value(
    #         "Patient", patient,
    #         ["name", "patient_name", "customer", "custom_branch", "custom_media"],
    #         as_dict=True,
    #     )
    #     if not pat:
    #         fail("Patient not found")
    #     else:
    #         customer = pat.customer or pat.patient_name
    #         media    = pat.custom_media or "InHouse"

    #         # ── validate therapy rates against Therapy Type min/max ─────────
    #         clean = []
    #         err = None
    #         for ln in lines:
    #             tt = ln.get("therapy_type")
    #             qty = float(ln.get("no_of_sessions") or 0)
    #             rate = float(ln.get("rate") or 0)
    #             use_offer = int(ln.get("use_offer") or 0)
    #             offer_rule = ln.get("offer_rule") or ""
    #             tinfo = frappe.db.get_value(
    #                 "Therapy Type", tt,
    #                 ["name", "item_code", "item", "minimum_price", "maximum_price"],
    #                 as_dict=True,
    #             )
    #             if not tinfo:
    #                 err = "Unknown therapy: " + str(tt); break
    #             if qty <= 0:
    #                 err = "Sessions must be > 0 for " + str(tt); break
    #             mn = float(tinfo.minimum_price or 0)
    #             mx = float(tinfo.maximum_price or 0)
    #             # When an offer is applied, the offer rate may be below the
    #             # normal minimum on purpose -> skip the min/max guard for it.
    #             if not use_offer:
    #                 if mn and rate < mn:
    #                     err = str(tt) + " rate below minimum " + str(mn); break
    #                 if mx and rate > mx:
    #                     err = str(tt) + " rate above maximum " + str(mx); break
    #             clean.append({
    #                 "therapy_type": tinfo.name,
    #                 "item_code": tinfo.item_code or tinfo.item,
    #                 "qty": qty, "rate": rate, "min": mn, "max": mx,
    #                 "use_offer": use_offer, "offer_rule": offer_rule,
    #             })

    #         if err:
    #             fail(err)
    #         else:
    #             # ═══ 1) THERAPY PLAN ═══════════════════════════════════════
    #             total_plan = 0
    #             total_sessions = 0
    #             for c in clean:
    #                 total_plan += c["qty"] * c["rate"]
    #                 total_sessions += c["qty"]

    #             # category (MANDATORY, Link to Healthcare Service Unit)
    #             # Some Therapy Types have no healthcare_service_unit set (e.g.
    #             # "Botox (25 Units)"), so we scan EVERY line for the first one
    #             # that has a unit, then fall back to the catch-all unit.
    #             plan_category = ""
    #             for c in clean:
    #                 if plan_category:
    #                     continue
    #                 u = frappe.db.get_value("Therapy Type", c["therapy_type"], "healthcare_service_unit")
    #                 if u:
    #                     plan_category = u
    #             if not plan_category:
    #                 if args.get("plan_category") and frappe.db.exists("Healthcare Service Unit", args.get("plan_category")):
    #                     plan_category = args.get("plan_category")
    #                 elif frappe.db.exists("Healthcare Service Unit", "All Healthcare Service Units - LSACPL"):
    #                     plan_category = "All Healthcare Service Units - LSACPL"
    #                 else:
    #                     plan_category = frappe.db.get_value("Healthcare Service Unit", {}, "name") or ""

    #             # media / source (MANDATORY, Link to Lead Source).
    #             # The live Therapy Plan client script restricts media to exactly:
    #             #   Call Center, Existing Customer, Reference, DIRECT WALKIN
    #             # and auto-sets "Existing Customer" if the client already has a
    #             # paid / partly-paid / overdue Sales Invoice. We mirror that here.
    #             plan_media = ""
    #             has_paid = frappe.db.get_value(
    #                 "Sales Invoice",
    #                 {"patient": pat.name, "docstatus": 1,
    #                  "status": ["in", ["Paid", "Partly Paid", "Overdue"]]},
    #                 "name",
    #             )
    #             if has_paid and frappe.db.exists("Lead Source", "Existing Customer"):
    #                 plan_media = "Existing Customer"
    #             else:
    #                 # map the incoming source (if the page sent one) to an allowed value
    #                 allowed = ["Call Center", "Existing Customer", "Reference", "DIRECT WALKIN"]
    #                 incoming = args.get("plan_media") or ""
    #                 if incoming in allowed and frappe.db.exists("Lead Source", incoming):
    #                     plan_media = incoming
    #                 elif frappe.db.exists("Lead Source", "DIRECT WALKIN"):
    #                     plan_media = "DIRECT WALKIN"
    #                 elif frappe.db.exists("Lead Source", "Call Center"):
    #                     plan_media = "Call Center"

    #             tp = frappe.new_doc("Therapy Plan")
    #             tp.patient        = pat.name
    #             tp.patient_name   = pat.patient_name
    #             tp.company        = "Life Slimming And Cosmetic Pvt Ltd"
    #             tp.start_date     = posting_date
    #             tp.branch         = branch
    #             tp.custom_transfer_branch = branch
    #             if plan_category:
    #                 tp.category = plan_category
    #             if plan_media:
    #                 tp.media = plan_media
    #             tp.status         = "Not Started"
    #             tp.total_sessions = total_sessions
    #             tp.custom_total_plan_amount = total_plan
    #             if consultant:
    #                 tp.custom_employee_name = consultant
    #             if practitioner:
    #                 tp.consultant_name = practitioner

    #             # Sharing incentive (Therapy Plan: sharing_incentive /
    #             # select_incentive_employee / custom_incentive_employee_name)
    #             if int(args.get("sharing_incentive") or 0):
    #                 inc_emp = args.get("incentive_employee") or ""
    #                 if inc_emp:
    #                     tp.sharing_incentive = 1
    #                     tp.select_incentive_employee = inc_emp
    #                     inc_name = frappe.db.get_value(
    #                         "Healthcare Practitioner", inc_emp, "practitioner_name")
    #                     if inc_name:
    #                         tp.custom_incentive_employee_name = inc_name

    #             # When the source is "Reference", record where it came from —
    #             # an existing client, an employee, or both. Therapy Plan has no
    #             # remarks field, so the employee goes on custom_employee_name
    #             # and the full trail is written to the invoice remarks below.
    #             ref_emp = args.get("reference_employee") or ""
    #             ref_client = args.get("reference_client") or ""
    #             ref_client_name = args.get("reference_client_name") or ""
    #             ref_note = ""
    #             if ref_emp:
    #                 ref_name = frappe.db.get_value(
    #                     "Healthcare Practitioner", ref_emp, "practitioner_name")
    #                 if ref_name:
    #                     if not tp.custom_employee_name:
    #                         tp.custom_employee_name = ref_name
    #                     ref_note = "Referred by employee: " + ref_name
    #             if ref_client:
    #                 if not ref_client_name:
    #                     ref_client_name = frappe.db.get_value(
    #                         "Patient", ref_client, "patient_name") or ref_client
    #                 if ref_note:
    #                     ref_note += " | "
    #                 ref_note += "Referred by client: " + ref_client_name + " (" + ref_client + ")"
    #             for c in clean:
    #                 tp.append("therapy_plan_details", {
    #                     "therapy_type": c["therapy_type"],
    #                     "no_of_sessions": c["qty"],
    #                     "custom_plan_amount": c["qty"] * c["rate"],
    #                     "custom_min_amount": c["min"],
    #                     "custom_max_amount": c["max"],
    #                 })
    #             tp.insert(ignore_permissions=False)

    #             # ═══ 2) SALES INVOICE (discount + comp + GST) ══════════════
    #             si = frappe.new_doc("Sales Invoice")
    #             si.patient        = pat.name
    #             si.patient_name   = pat.patient_name
    #             si.customer       = customer
    #             si.posting_date   = posting_date
    #             si.set_posting_time = 1
    #             si.branch         = branch
    #             si.custom_transfer_branch = branch
    #             si.custom_therapy_plan = tp.name
    #             si.therapy_plan_reference_id = tp.name
    #             # Pricing rules must NEVER be re-applied by ERPNext: we already
    #             # send the exact rate for every line (offer rate where the user
    #             # ticked the offer, standard rate otherwise). Leaving this at 0
    #             # made ERPNext apply the pricing rule to EVERY matching item —
    #             # so an offer got added to lines the user had not opted into.
    #             si.ignore_pricing_rule = 1
    #             if consultant:
    #                 si.custom_referring_name = consultant
    #             if practitioner:
    #                 si.ref_practitioner = practitioner
    #                 # custom_referring_name is the field that shows the
    #                 # practitioner's NAME on the invoice / print format — fill
    #                 # it from the practitioner when no consultant was typed.
    #                 if not si.custom_referring_name:
    #                     pr_name = frappe.db.get_value(
    #                         "Healthcare Practitioner", practitioner, "practitioner_name")
    #                     if pr_name:
    #                         si.custom_referring_name = pr_name

    #             # Referral trail (source = Reference) onto the invoice remarks
    #             if ref_note:
    #                 prev_rem = si.get("remarks") or ""
    #                 if prev_rem:
    #                     si.remarks = prev_rem + " | " + ref_note
    #                 else:
    #                     si.remarks = ref_note

    #             # Sharing incentive — the Sales Invoice only carries the NAME
    #             # (custom_incentive_employee_name); the flag and the link field
    #             # live on the Therapy Plan.
    #             if int(args.get("sharing_incentive") or 0):
    #                 inc_emp_si = args.get("incentive_employee") or ""
    #                 if inc_emp_si:
    #                     inc_nm = frappe.db.get_value(
    #                         "Healthcare Practitioner", inc_emp_si, "practitioner_name")
    #                     if inc_nm:
    #                         si.custom_incentive_employee_name = inc_nm

    #             for c in clean:
    #                 si.append("items", {
    #                     "item_code": c["item_code"],
    #                     "qty": c["qty"],
    #                     "rate": c["rate"],
    #                 })
    #                 si.append("therapy_types_", {
    #                     "therapy_type": c["therapy_type"],
    #                     "no_of_sessions": c["qty"],
    #                 })

    #             # ── COMPLIMENTARY SESSIONS ──────────────────────────────────
    #             # NOTE: complimentary sessions are a POST-PAYMENT step in this
    #             # portal. The script "save_comp_sessions_on_submitted_invoice"
    #             # writes them (with comp-limit validation via custom_comp_limit_
    #             # and a push into the Therapy Plan as custom_is_offer_ rows) only
    #             # AFTER the invoice is submitted and fully paid. So we do NOT add
    #             # comps here at creation time — doing so would bypass those rules.
    #             # The comps[] payload is accepted for forward-compatibility but
    #             # intentionally not written onto the draft/new invoice.

    #             # ── FIXED PACKAGE PRICE ────────────────────────────────────
    #             # Mirrors the live Sales Invoice script: item rates are kept
    #             # and the gap is booked as a Net Total discount, so
    #             # Net Total = package price and GST is charged on that.
    #             pkg_price = float(args.get("pkg_price") or 0)
    #             pkg_tc = args.get("pkg_tc") or ""
    #             if pkg_price > 0:
    #                 items_total = 0
    #                 for c in clean:
    #                     items_total += c["qty"] * c["rate"]
    #                 if items_total > pkg_price:
    #                     si.apply_discount_on = "Net Total"
    #                     si.additional_discount_percentage = 0
    #                     si.discount_amount = items_total - pkg_price
    #                 if pkg_tc:
    #                     si.tc_name = pkg_tc

    #             # ── GST 5% (SGST 2.5 + CGST 2.5) ────────────────────────────
    #             # Setting taxes_and_charges only NAMES the template — it does
    #             # NOT copy the tax rows when the doc is built server-side, so
    #             # the invoice came out with 0 GST. Copy the rows explicitly.
    #             tax_tmpl = "Output GST In-state - LSACPL"
    #             si.taxes_and_charges = tax_tmpl
    #             tax_rows = frappe.get_all(
    #                 "Sales Taxes and Charges",
    #                 filters={"parent": tax_tmpl,
    #                          "parenttype": "Sales Taxes and Charges Template"},
    #                 fields=["charge_type", "account_head", "description", "rate",
    #                         "cost_center", "included_in_print_rate"],
    #                 order_by="idx asc",
    #             )
    #             for tr in tax_rows:
    #                 si.append("taxes", {
    #                     "charge_type": tr.get("charge_type") or "On Net Total",
    #                     "account_head": tr.get("account_head"),
    #                     "description": tr.get("description"),
    #                     "rate": tr.get("rate") or 0,
    #                     "cost_center": tr.get("cost_center"),
    #                     "included_in_print_rate": tr.get("included_in_print_rate") or 0,
    #                 })

    #             # ── COST CENTER (branch-wise) ───────────────────────────────
    #             # Branch names and cost centre names don't match exactly
    #             # (e.g. "Banjara Hills" -> "Banjarahills - LSACPL"), so match
    #             # on a normalised form, then fall back to a loose match.
    #             def normname(v):
    #                 out = ""
    #                 for ch in (v or "").lower():
    #                     if ch.isalnum():
    #                         out += ch
    #                 return out

    #             cc_name = ""
    #             if branch:
    #                 target = normname(branch)
    #                 ccs = frappe.get_all(
    #                     "Cost Center",
    #                     filters={"company": "Life Slimming And Cosmetic Pvt Ltd",
    #                              "is_group": 0},
    #                     fields=["name", "cost_center_name"],
    #                     limit_page_length=0,
    #                 )
    #                 # 1) exact match on the normalised name
    #                 for cc in ccs:
    #                     if not cc_name and normname(cc.get("cost_center_name")) == target:
    #                         cc_name = cc.get("name")
    #                 # 2) otherwise the closest name sharing at least 5 leading
    #                 #    characters (handles "Himayathnagar" -> "HimaytNagar")
    #                 if not cc_name:
    #                     best_len = 0
    #                     for cc in ccs:
    #                         n = normname(cc.get("cost_center_name"))
    #                         i = 0
    #                         while i < len(n) and i < len(target) and n[i] == target[i]:
    #                             i += 1
    #                         if i >= 5 and i > best_len:
    #                             best_len = i
    #                             cc_name = cc.get("name")
    #             if cc_name:
    #                 si.cost_center = cc_name
    #                 for it in si.items:
    #                     if not it.cost_center:
    #                         it.cost_center = cc_name

    #             # ── DISCOUNT (non-draft only) ──────────────────────────────
    #             # On the draft path the % is NOT applied here — the Discount
    #             # Approval Request + apply_invoice_discount own it after approval.
    #             # A fixed package price already occupies discount_amount /
    #             # apply_discount_on, so a package price always wins and the
    #             # percentage is ignored rather than silently overwriting it.
    #             if (not draft_only) and discount_pct > 0 and pkg_price <= 0:
    #                 si.apply_discount_on = "Grand Total"
    #                 si.additional_discount_percentage = discount_pct
    #                 trail = ("Applied " + str(discount_pct) + "% via billing page")
    #                 if discount_by:
    #                     trail += ". Approver: " + discount_by
    #                 si.discount_remarks = trail + "."
    #             elif (not draft_only) and discount_pct > 0 and pkg_price > 0:
    #                 si.discount_remarks = ("Fixed package price applied; the "
    #                                       + str(discount_pct)
    #                                       + "% discount was NOT applied on top.")

    #             si.insert(ignore_permissions=False)

    #             # ═══════════════════════════════════════════════════════════
    #             #  A) DRAFT-ONLY PATH  (discount approval flow)
    #             #     leave invoice as draft, no submit, no payment
    #             # ═══════════════════════════════════════════════════════════
    #             if draft_only:
    #                 frappe.db.commit()
    #                 frappe.response["message"] = {
    #                     "therapy_plan": tp.name,
    #                     "sales_invoice": si.name,
    #                     "grand_total": float(si.rounded_total or si.grand_total or 0),
    #                     "draft": 1,
    #                 }

    #             # ═══════════════════════════════════════════════════════════
    #             #  B) NORMAL PATH  (submit + mandatory payment)  — unchanged
    #             # ═══════════════════════════════════════════════════════════
    #             else:
    #                 si.submit()
    #                 # NOTE: no commit yet — payment must succeed first.

    #                 grand = float(si.rounded_total or si.grand_total or 0)
    #                 outstanding = float(si.outstanding_amount or 0)

    #                 # cap the collection at the outstanding
    #                 pay_amt = advance_amount
    #                 if pay_amt > outstanding:
    #                     pay_amt = outstanding

    #                 # paid_to = Mode of Payment default account for this company
    #                 paid_to = frappe.db.get_value(
    #                     "Mode of Payment Account",
    #                     {"parent": advance_mode, "company": "Life Slimming And Cosmetic Pvt Ltd"},
    #                     "default_account",
    #                 )

    #                 # ═══ 3) PAYMENT ENTRY (MANDATORY) ══════════════════════
    #                 if not paid_to:
    #                     frappe.db.rollback()
    #                     fail("No default account set for mode '" + str(advance_mode) +
    #                          "'. Set it in Mode of Payment, then retry.")
    #                 else:
    #                     try:
    #                         pe = frappe.get_doc({
    #                             "doctype": "Payment Entry",
    #                             "payment_type": "Receive",
    #                             "posting_date": posting_date,
    #                             "company": "Life Slimming And Cosmetic Pvt Ltd",
    #                             "mode_of_payment": advance_mode,
    #                             "party_type": "Customer",
    #                             "party": customer,
    #                             "branch": branch,
    #                             "paid_to": paid_to,
    #                             "paid_amount": pay_amt,
    #                             "received_amount": pay_amt,
    #                             "source_exchange_rate": 1,
    #                             "target_exchange_rate": 1,
    #                             "reference_no": advance_ref or None,
    #                             "reference_date": posting_date if advance_ref else None,
    #                             "references": [{
    #                                 "reference_doctype": "Sales Invoice",
    #                                 "reference_name": si.name,
    #                                 "allocated_amount": pay_amt,
    #                             }],
    #                         })
    #                         pe.insert(ignore_permissions=False)
    #                         pe.submit()
    #                     except Exception as e:
    #                         # roll back invoice + plan so no unpaid bill is left behind
    #                         frappe.db.rollback()
    #                         fail("Payment failed, nothing was saved: " + str(e))
    #                     else:
    #                         frappe.db.commit()
    #                         new_out = float(
    #                             frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount") or 0
    #                         )
    #                         frappe.response["message"] = {
    #                             "therapy_plan": tp.name,
    #                             "sales_invoice": si.name,
    #                             "payment_entry": pe.name,
    #                             "grand_total": grand,
    #                             "paid_amount": pay_amt,
    #                             "outstanding": new_out,
    #                             "discount_pct": float(si.get("total_approver_discount_pct") or discount_pct or 0),
    #                             "discount_amount": float(si.get("discount_amount") or 0),
    #                             "comp_slab": si.get("custom_comp_slab") or "",
    #                             "comp_used": float(si.get("custom_comp_used_") or 0),
    #                             "approval_status": si.get("approval_workflow_status") or "",
    #                         }





















    args = frappe.form_dict

    patient        = args.get("patient")
    branch         = args.get("branch")
    consultant     = args.get("consultant") or ""
    if consultant and frappe.db.exists("Healthcare Practitioner", consultant):
        cons_nm = frappe.db.get_value(
            "Healthcare Practitioner", consultant, "practitioner_name")
        if cons_nm:
            consultant = cons_nm
    practitioner   = args.get("practitioner") or ""
    draft_only     = int(args.get("draft_only") or 0)
    discount_pct   = float(args.get("discount_pct") or 0)
    discount_by    = args.get("discount_by") or ""
    advance_amount = float(args.get("advance_amount") or 0)
    advance_mode   = args.get("advance_mode") or "Cash"
    advance_ref    = args.get("advance_ref") or ""
    posting_date   = args.get("posting_date") or frappe.utils.today()

    # COUPON: read + validate (both types, minimum enforced)
    coupon_code_in = args.get("coupon_code") or ""
    coupon_type_in = ""
    coupon_val_in = 0
    coupon_min_in = 0
    coupon_ok = 0
    coupon_amt_final = 0
    coupon_pct_final = 0
    coupon_error = ""
    if coupon_code_in and frappe.db.exists("Web Coupon", coupon_code_in):
        cpn = frappe.get_doc("Web Coupon", coupon_code_in)
        tdc = frappe.utils.getdate(frappe.utils.today())
        if cpn.status != "Active":
            coupon_error = "This coupon is not active."
        elif cpn.valid_until and frappe.utils.getdate(cpn.valid_until) < tdc:
            coupon_error = "This coupon has expired."
        else:
            coupon_type_in = cpn.discount_type
            coupon_val_in = float(cpn.discount_value or 0)
            coupon_min_in = float(cpn.get("min_spend") or 0)
            coupon_ok = 1

    def load_json(raw):
        if isinstance(raw, str):
            if not raw:
                return []
            return json.loads(raw)
        return raw or []

    lines = load_json(args.get("lines"))
    comps = load_json(args.get("comps"))

    any_offer = 0
    for ln in lines:
        if int(ln.get("use_offer") or 0):
            any_offer = 1

    def fail(msg):
        frappe.response["message"] = {"error": msg}

    if not patient:
        fail("Patient is required")

    elif not lines:
        fail("At least one therapy line is required")

    elif coupon_code_in and not coupon_ok:
        fail("Coupon problem: " + (coupon_error or "coupon not valid"))

    elif discount_pct > 15 and not coupon_code_in:
        fail("Discount cannot exceed 15%")

    elif (not draft_only) and advance_amount <= 0:
        fail("A collection amount is required. Enter the amount received to generate the bill.")

    elif (not draft_only) and advance_mode not in ("Cash",) and not advance_ref:
        fail("Reference / UTR number is required for " + str(advance_mode))

    else:
        pat = frappe.db.get_value(
            "Patient", patient,
            ["name", "patient_name", "customer", "custom_branch", "custom_media"],
            as_dict=True,
        )
        if not pat:
            fail("Patient not found")
        else:
            customer = pat.customer or pat.patient_name
            media    = pat.custom_media or "InHouse"

            clean = []
            err = None
            for ln in lines:
                tt = ln.get("therapy_type")
                qty = float(ln.get("no_of_sessions") or 0)
                rate = float(ln.get("rate") or 0)
                use_offer = int(ln.get("use_offer") or 0)
                offer_rule = ln.get("offer_rule") or ""
                tinfo = frappe.db.get_value(
                    "Therapy Type", tt,
                    ["name", "item_code", "item", "minimum_price", "maximum_price"],
                    as_dict=True,
                )
                if not tinfo:
                    err = "Unknown therapy: " + str(tt); break
                if qty <= 0:
                    err = "Sessions must be > 0 for " + str(tt); break
                mn = float(tinfo.minimum_price or 0)
                mx = float(tinfo.maximum_price or 0)
                if not use_offer:
                    if mn and rate < mn:
                        err = str(tt) + " rate below minimum " + str(mn); break
                    if mx and rate > mx:
                        err = str(tt) + " rate above maximum " + str(mx); break
                clean.append({
                    "therapy_type": tinfo.name,
                    "item_code": tinfo.item_code or tinfo.item,
                    "qty": qty, "rate": rate, "min": mn, "max": mx,
                    "use_offer": use_offer, "offer_rule": offer_rule,
                })

            if err:
                fail(err)
            else:
                # subtotal before any discount
                subtotal = 0
                for c in clean:
                    subtotal += c["qty"] * c["rate"]

                # COUPON: enforce minimum, compute the coupon's rupee value + equivalent %
                coupon_block_msg = ""
                if coupon_ok:
                    if coupon_min_in and subtotal < coupon_min_in:
                        coupon_ok = 0
                        coupon_block_msg = ("Coupon needs a bill of at least "
                            + str(int(coupon_min_in)) + "; this bill is "
                            + str(int(subtotal)) + ".")
                    else:
                        if coupon_type_in == "Fixed Amount":
                            coupon_amt_final = coupon_val_in
                            if coupon_amt_final > subtotal:
                                coupon_amt_final = subtotal
                        else:
                            coupon_amt_final = round(subtotal * coupon_val_in / 100.0, 2)
                        if subtotal > 0:
                            coupon_pct_final = round(coupon_amt_final * 100.0 / subtotal, 2)

                if coupon_block_msg:
                    fail(coupon_block_msg)
                else:
                    # combined discount % = coupon% + staff% (coupon applied first, staff on remainder base handled by page)
                    effective_pct = discount_pct
                    if coupon_ok and coupon_pct_final > 0:
                        effective_pct = round(discount_pct + coupon_pct_final, 2)

                    total_plan = 0
                    total_sessions = 0
                    for c in clean:
                        total_plan += c["qty"] * c["rate"]
                        total_sessions += c["qty"]

                    plan_category = ""
                    for c in clean:
                        if plan_category:
                            continue
                        u = frappe.db.get_value("Therapy Type", c["therapy_type"], "healthcare_service_unit")
                        if u:
                            plan_category = u
                    if not plan_category:
                        if args.get("plan_category") and frappe.db.exists("Healthcare Service Unit", args.get("plan_category")):
                            plan_category = args.get("plan_category")
                        elif frappe.db.exists("Healthcare Service Unit", "All Healthcare Service Units - LSACPL"):
                            plan_category = "All Healthcare Service Units - LSACPL"
                        else:
                            plan_category = frappe.db.get_value("Healthcare Service Unit", {}, "name") or ""

                    plan_media = ""
                    has_paid = frappe.db.get_value(
                        "Sales Invoice",
                        {"patient": pat.name, "docstatus": 1,
                         "status": ["in", ["Paid", "Partly Paid", "Overdue"]]},
                        "name",
                    )
                    if has_paid and frappe.db.exists("Lead Source", "Existing Customer"):
                        plan_media = "Existing Customer"
                    else:
                        allowed = ["Call Center", "Existing Customer", "Reference", "DIRECT WALKIN"]
                        incoming = args.get("plan_media") or ""
                        if incoming in allowed and frappe.db.exists("Lead Source", incoming):
                            plan_media = incoming
                        elif frappe.db.exists("Lead Source", "DIRECT WALKIN"):
                            plan_media = "DIRECT WALKIN"
                        elif frappe.db.exists("Lead Source", "Call Center"):
                            plan_media = "Call Center"

                    tp = frappe.new_doc("Therapy Plan")
                    tp.patient        = pat.name
                    tp.patient_name   = pat.patient_name
                    tp.company        = "Life Slimming And Cosmetic Pvt Ltd"
                    tp.start_date     = posting_date
                    tp.branch         = branch
                    tp.custom_transfer_branch = branch
                    if plan_category:
                        tp.category = plan_category
                    if plan_media:
                        tp.media = plan_media
                    tp.status         = "Not Started"
                    tp.total_sessions = total_sessions
                    tp.custom_total_plan_amount = total_plan
                    if consultant:
                        tp.custom_employee_name = consultant
                    if practitioner:
                        tp.consultant_name = practitioner

                    if int(args.get("sharing_incentive") or 0):
                        inc_emp = args.get("incentive_employee") or ""
                        if inc_emp:
                            tp.sharing_incentive = 1
                            tp.select_incentive_employee = inc_emp
                            inc_name = frappe.db.get_value(
                                "Healthcare Practitioner", inc_emp, "practitioner_name")
                            if inc_name:
                                tp.custom_incentive_employee_name = inc_name

                    ref_emp = args.get("reference_employee") or ""
                    ref_client = args.get("reference_client") or ""
                    ref_client_name = args.get("reference_client_name") or ""
                    ref_note = ""
                    if ref_emp:
                        ref_name = frappe.db.get_value(
                            "Healthcare Practitioner", ref_emp, "practitioner_name")
                        if ref_name:
                            if not tp.custom_employee_name:
                                tp.custom_employee_name = ref_name
                            ref_note = "Referred by employee: " + ref_name
                    if ref_client:
                        if not ref_client_name:
                            ref_client_name = frappe.db.get_value(
                                "Patient", ref_client, "patient_name") or ref_client
                        if ref_note:
                            ref_note += " | "
                        ref_note += "Referred by client: " + ref_client_name + " (" + ref_client + ")"
                    for c in clean:
                        tp.append("therapy_plan_details", {
                            "therapy_type": c["therapy_type"],
                            "no_of_sessions": c["qty"],
                            "custom_plan_amount": c["qty"] * c["rate"],
                            "custom_min_amount": c["min"],
                            "custom_max_amount": c["max"],
                        })
                    tp.insert(ignore_permissions=False)

                    si = frappe.new_doc("Sales Invoice")
                    si.patient        = pat.name
                    si.patient_name   = pat.patient_name
                    si.customer       = customer
                    si.posting_date   = posting_date
                    si.set_posting_time = 1
                    si.branch         = branch
                    si.custom_transfer_branch = branch
                    si.custom_therapy_plan = tp.name
                    si.therapy_plan_reference_id = tp.name
                    if coupon_ok:
                        si.custom_coupon_applied = coupon_code_in
                        si.custom_coupon_percent = coupon_amt_final
                    si.ignore_pricing_rule = 1
                    if consultant:
                        si.custom_referring_name = consultant
                    if practitioner:
                        si.ref_practitioner = practitioner
                        if not si.custom_referring_name:
                            pr_name = frappe.db.get_value(
                                "Healthcare Practitioner", practitioner, "practitioner_name")
                            if pr_name:
                                si.custom_referring_name = pr_name

                    if ref_note:
                        prev_rem = si.get("remarks") or ""
                        if prev_rem:
                            si.remarks = prev_rem + " | " + ref_note
                        else:
                            si.remarks = ref_note

                    if int(args.get("sharing_incentive") or 0):
                        inc_emp_si = args.get("incentive_employee") or ""
                        if inc_emp_si:
                            inc_nm = frappe.db.get_value(
                                "Healthcare Practitioner", inc_emp_si, "practitioner_name")
                            if inc_nm:
                                si.custom_incentive_employee_name = inc_nm

                    for c in clean:
                        si.append("items", {
                            "item_code": c["item_code"],
                            "qty": c["qty"],
                            "rate": c["rate"],
                        })
                        si.append("therapy_types_", {
                            "therapy_type": c["therapy_type"],
                            "no_of_sessions": c["qty"],
                        })

                    pkg_price = float(args.get("pkg_price") or 0)
                    pkg_tc = args.get("pkg_tc") or ""
                    if pkg_price > 0:
                        items_total = 0
                        for c in clean:
                            items_total += c["qty"] * c["rate"]
                        if items_total > pkg_price:
                            si.apply_discount_on = "Net Total"
                            si.additional_discount_percentage = 0
                            si.discount_amount = items_total - pkg_price
                        if pkg_tc:
                            si.tc_name = pkg_tc

                    tax_tmpl = "Output GST In-state - LSACPL"
                    si.taxes_and_charges = tax_tmpl
                    tax_rows = frappe.get_all(
                        "Sales Taxes and Charges",
                        filters={"parent": tax_tmpl,
                                 "parenttype": "Sales Taxes and Charges Template"},
                        fields=["charge_type", "account_head", "description", "rate",
                                "cost_center", "included_in_print_rate"],
                        order_by="idx asc",
                    )
                    for tr in tax_rows:
                        si.append("taxes", {
                            "charge_type": tr.get("charge_type") or "On Net Total",
                            "account_head": tr.get("account_head"),
                            "description": tr.get("description"),
                            "rate": tr.get("rate") or 0,
                            "cost_center": tr.get("cost_center"),
                            "included_in_print_rate": tr.get("included_in_print_rate") or 0,
                        })

                    def normname(v):
                        out = ""
                        for ch in (v or "").lower():
                            if ch.isalnum():
                                out += ch
                        return out

                    cc_name = ""
                    if branch:
                        target = normname(branch)
                        ccs = frappe.get_all(
                            "Cost Center",
                            filters={"company": "Life Slimming And Cosmetic Pvt Ltd",
                                     "is_group": 0},
                            fields=["name", "cost_center_name"],
                            limit_page_length=0,
                        )
                        for cc in ccs:
                            if not cc_name and normname(cc.get("cost_center_name")) == target:
                                cc_name = cc.get("name")
                        if not cc_name:
                            best_len = 0
                            for cc in ccs:
                                n = normname(cc.get("cost_center_name"))
                                i = 0
                                while i < len(n) and i < len(target) and n[i] == target[i]:
                                    i += 1
                                if i >= 5 and i > best_len:
                                    best_len = i
                                    cc_name = cc.get("name")
                    if cc_name:
                        si.cost_center = cc_name
                        for it in si.items:
                            if not it.cost_center:
                                it.cost_center = cc_name

                    if (not draft_only) and effective_pct > 0 and pkg_price <= 0:
                        si.apply_discount_on = "Grand Total"
                        si.additional_discount_percentage = effective_pct
                        trail = ("Applied " + str(effective_pct) + "% (")
                        if coupon_ok and coupon_pct_final > 0:
                            trail += "coupon " + coupon_code_in + " = " + str(coupon_pct_final) + "%"
                            if discount_pct > 0:
                                trail += " + staff " + str(discount_pct) + "%"
                        else:
                            trail += "staff " + str(discount_pct) + "%"
                        trail += ")"
                        if discount_by:
                            trail += ". Approver: " + discount_by
                        si.discount_remarks = trail + "."
                    elif (not draft_only) and effective_pct > 0 and pkg_price > 0:
                        si.discount_remarks = ("Fixed package price applied; the "
                                               + str(effective_pct)
                                               + "% discount was NOT applied on top.")

                    si.insert(ignore_permissions=False)

                    if draft_only:
                        frappe.db.commit()
                        frappe.response["message"] = {
                            "therapy_plan": tp.name,
                            "sales_invoice": si.name,
                            "grand_total": float(si.rounded_total or si.grand_total or 0),
                            "draft": 1,
                            "coupon_applied": coupon_code_in if coupon_ok else "",
                            "coupon_amount": coupon_amt_final if coupon_ok else 0,
                            "coupon_percent": coupon_pct_final if coupon_ok else 0,
                        }

                    else:
                        si.submit()

                        grand = float(si.rounded_total or si.grand_total or 0)
                        outstanding = float(si.outstanding_amount or 0)

                        pay_amt = advance_amount
                        if pay_amt > outstanding:
                            pay_amt = outstanding

                        paid_to = frappe.db.get_value(
                            "Mode of Payment Account",
                            {"parent": advance_mode, "company": "Life Slimming And Cosmetic Pvt Ltd"},
                            "default_account",
                        )

                        if not paid_to:
                            frappe.db.rollback()
                            fail("No default account set for mode '" + str(advance_mode) +
                                 "'. Set it in Mode of Payment, then retry.")
                        else:
                            try:
                                pe = frappe.get_doc({
                                    "doctype": "Payment Entry",
                                    "payment_type": "Receive",
                                    "posting_date": posting_date,
                                    "company": "Life Slimming And Cosmetic Pvt Ltd",
                                    "mode_of_payment": advance_mode,
                                    "party_type": "Customer",
                                    "party": customer,
                                    "branch": branch,
                                    "paid_to": paid_to,
                                    "paid_amount": pay_amt,
                                    "received_amount": pay_amt,
                                    "source_exchange_rate": 1,
                                    "target_exchange_rate": 1,
                                    "reference_no": advance_ref or None,
                                    "reference_date": posting_date if advance_ref else None,
                                    "references": [{
                                        "reference_doctype": "Sales Invoice",
                                        "reference_name": si.name,
                                        "allocated_amount": pay_amt,
                                    }],
                                })
                                pe.insert(ignore_permissions=False)
                                pe.submit()
                            except Exception as e:
                                frappe.db.rollback()
                                fail("Payment failed, nothing was saved: " + str(e))
                            else:
                                if coupon_ok:
                                    frappe.db.set_value("Web Coupon", coupon_code_in, {
                                        "status": "Used",
                                        "used_on": frappe.utils.now_datetime(),
                                        "used_in_invoice": si.name,
                                        "used_by_patient": pat.name
                                    })
                                frappe.db.commit()
                                new_out = float(
                                    frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount") or 0
                                )
                                frappe.response["message"] = {
                                    "therapy_plan": tp.name,
                                    "sales_invoice": si.name,
                                    "payment_entry": pe.name,
                                    "grand_total": grand,
                                    "paid_amount": pay_amt,
                                    "outstanding": new_out,
                                    "discount_pct": effective_pct,
                                    "discount_amount": float(si.get("discount_amount") or 0),
                                    "comp_slab": si.get("custom_comp_slab") or "",
                                    "comp_used": float(si.get("custom_comp_used_") or 0),
                                    "approval_status": si.get("approval_workflow_status") or "",
                                    "coupon_applied": coupon_code_in if coupon_ok else "",
                                    "coupon_amount": coupon_amt_final if coupon_ok else 0,
                                    "coupon_percent": coupon_pct_final if coupon_ok else 0,
                                }
