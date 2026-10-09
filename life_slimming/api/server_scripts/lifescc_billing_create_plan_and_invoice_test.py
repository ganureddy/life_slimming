"""lifescc.billing.create_plan_and_invoice_TEST

Original API: lifescc.billing.create_plan_and_invoice_TEST
Source modified: 2026-10-09 11:46:48.740138
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
    # LIFE-DOCTOR-CONSULTANT-V1
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

    # Separate Doctor Consultant.
    # This must never replace Consultant Employee.
    doctor_practitioner = args.get("doctor_practitioner") or ""
    doctor_name = ""

    if doctor_practitioner:
        if frappe.db.exists(
            "Healthcare Practitioner",
            doctor_practitioner
        ):
            doctor_name = frappe.db.get_value(
                "Healthcare Practitioner",
                doctor_practitioner,
                "practitioner_name"
            ) or doctor_practitioner

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
            ["name", "patient_name", "customer", "custom_branch", "custom_media", "custom_lead"],
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
                    [
                        "name",
                        "item_code",
                        "item",
                        "minimum_price",
                        "maximum_price",
                        "healthcare_service_unit"
                    ],
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
                            # Normalize imported Therapy Type links. Some older rows contain
                # leading/trailing spaces in item_code (for example GLP-1 1 Dose).
                # Prefer the cleaned item_code, then fall back to the cleaned item link.
                item_code = (tinfo.item_code or "").strip()
                fallback_item = (tinfo.item or "").strip()
                if not item_code or not frappe.db.exists("Item", item_code):
                    item_code = fallback_item
                if not item_code or not frappe.db.exists("Item", item_code):
                    err = "Item for therapy " + str(tt) + " was not found. Check Therapy Type item_code/item."
                    break

                # ---- Pre-flight item state check --------------------------------
                # ERPNext throws ValidationError (HTTP 417) at insert time if the
                # item is disabled or past its end_of_life date. Catch it here so
                # the client can show a clean red toast and stop the submission
                # BEFORE the Therapy Plan is created (no orphaned plans).
                item_state = frappe.db.get_value(
                    "Item",
                    item_code,
                    ["disabled", "end_of_life"],
                    as_dict=True,
                )
                if item_state and item_state.get("disabled"):
                    err = (
                        "Therapy \"" + str(tt) + "\" cannot be billed — its "
                        "underlying item (" + str(item_code) + ") is disabled. "
                        "Please re-enable the item or remove this therapy."
                    )
                    break
                if item_state and item_state.get("end_of_life"):
                    if str(item_state.get("end_of_life"))[:10] <= frappe.utils.today():
                        err = (
                            "Therapy \"" + str(tt) + "\" cannot be billed — its "
                            "underlying item (" + str(item_code) + ") reached "
                            "end of life on "
                            + str(item_state.get("end_of_life"))[:10] + "."
                        )
                        break
                # -----------------------------------------------------------------

                clean.append({
                    "therapy_type": tinfo.name,
                    "item_code": item_code,
                    "qty": qty,
                    "rate": rate,
                    "min": mn,
                    "max": mx,
                    "category": (
                        tinfo.healthcare_service_unit or ""
                    ),
                    "use_offer": use_offer,
                    "offer_rule": offer_rule,
                })

            # Doctor is mandatory only for medical categories.
            doctor_required = 0
            doctor_categories = (
                "skin",
                "hair",
                "laser",
                "dermat"
            )

            for clean_line in clean:
                category_text = str(
                    clean_line.get("category") or ""
                ).strip().lower()

                therapy_text = str(
                    clean_line.get("therapy_type") or ""
                ).strip().lower()

                combined_text = (
                    category_text + " " + therapy_text
                )

                for doctor_category in doctor_categories:
                    if doctor_category in combined_text:
                        doctor_required = 1

            if doctor_practitioner and not doctor_name:
                err = (
                    "Selected Doctor Consultant does not exist: "
                    + str(doctor_practitioner)
                )

            clean_comps = []
            comp_qty_by_item = {}
            comp_value_total = 0.0
            if not err:
                bill_subtotal = sum(float(line.get("qty") or 0) * float(line.get("rate") or 0) for line in clean)
                if bill_subtotal <= 25000 and comps:
                    err = "Complimentary sessions are available only when the bill subtotal exceeds 25,000."
                else:
                    comp_rate = 0.04 if bill_subtotal <= 100000 else (0.075 if bill_subtotal <= 200000 else 0.10)
                    comp_value_limit = bill_subtotal * comp_rate
                    for comp in comps:
                        item_code = (comp.get("item_code") or "").strip()
                        try:
                            qty_value = float(comp.get("qty") or 0)
                        except (TypeError, ValueError):
                            qty_value = 0
                        if not item_code or qty_value < 1 or not qty_value.is_integer():
                            err = "Select a complimentary item and enter a whole session quantity."
                            break
                        qty = int(qty_value)
                        item = frappe.db.get_value(
                            "Item", item_code,
                            ["item_name", "item_group", "disabled", "standard_rate", "custom_max_qty_per_bill"],
                            as_dict=True,
                        )
                        if not item or item.item_group != "Complimentary Sessions" or item.disabled:
                            err = "Invalid or inactive complimentary item: " + item_code
                            break
                        max_qty = int(item.custom_max_qty_per_bill or 0)
                        selected_qty = comp_qty_by_item.get(item_code, 0) + qty
                        if max_qty and selected_qty > max_qty:
                            err = (item.item_name or item_code) + " allows at most " + str(max_qty) + " complimentary session(s) per bill."
                            break
                        comp_qty_by_item[item_code] = selected_qty
                        therapy_type = frappe.db.get_value("Therapy Type", {"item_code": item_code}, "name")
                        if not therapy_type:
                            therapy_type = frappe.db.get_value("Therapy Type", {"item": item_code}, "name")
                        if not therapy_type:
                            err = "Complimentary item " + item_code + " is not linked to a Therapy Type, so it cannot be added to the Therapy Plan."
                            break
                        rate = float(item.standard_rate or 0)
                        comp_value_total += rate * qty
                        clean_comps.append({
                            "item_code": item_code,
                            "item_name": item.item_name or item_code,
                            "therapy_type": therapy_type,
                            "qty": qty,
                            "rate": rate,
                        })
                    if not err and comp_value_total > comp_value_limit + 0.01:
                        err = "Complimentary session value exceeds the allowed bill slab limit of " + str(round(comp_value_limit, 2)) + "."

            if err:
                fail(err)
            else:
                subtotal = 0
                for c in clean:
                    subtotal += c["qty"] * c["rate"]

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
                    same_day_cc = 0
                    sd_inv = frappe.get_all(
                        "Sales Invoice",
                        filters={"patient": pat.name, "posting_date": posting_date, "docstatus": ["<", 2]},
                        fields=["custom_therapy_plan"],
                        limit_page_length=0,
                    )
                    for sd in sd_inv:
                        if sd.get("custom_therapy_plan") and not same_day_cc:
                            if frappe.db.get_value("Therapy Plan", sd.get("custom_therapy_plan"), "media") == "Call Center":
                                same_day_cc = 1
                    has_paid = frappe.db.get_value(
                        "Sales Invoice",
                        {"patient": pat.name, "docstatus": 1,
                         "status": ["in", ["Paid", "Partly Paid", "Overdue"]]},
                        "name",
                    )
                    if same_day_cc and frappe.db.exists("Lead Source", "Call Center"):
                        plan_media = "Call Center"
                    elif has_paid and frappe.db.exists("Lead Source", "Existing Customer"):
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
                    tp.total_sessions = total_sessions + sum(comp["qty"] for comp in clean_comps)
                    tp.custom_total_plan_amount = total_plan
                    if consultant:
                        tp.custom_employee_name = consultant
                    if practitioner:
                        tp.consultant_name = practitioner

                    # Separate treating/prescribing Doctor Consultant.
                    if doctor_practitioner:
                        tp.custom_doctor__practitioner = (
                            doctor_practitioner
                        )
                        tp.custom_doctor_name = doctor_name

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
                    for comp in clean_comps:
                        tp.append("therapy_plan_details", {
                            "therapy_type": comp["therapy_type"],
                            "no_of_sessions": comp["qty"],
                            "custom_plan_amount": 0,
                            "custom_min_amount": 0,
                            "custom_max_amount": 0,
                            "custom_is_offer_": 1,
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

                    # Doctor Consultant is separate from ref_practitioner.
                    if doctor_practitioner:
                        si.custom_doctor_consultant = (
                            doctor_practitioner
                        )
                        si.custom_doctor_consultant_name = doctor_name

                    si.original_bill_total = subtotal
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

                    # COUPON (Option A): coupon rupee amount applied at creation on BOTH
                    # draft and non-draft paths - coupon reduces the bill immediately.
                    # Staff % added later by apply_invoice_discount_TEST (folds into 15% cap).
                    if coupon_ok and coupon_amt_final > 0 and pkg_price <= 0:
                        si.apply_discount_on = "Grand Total"
                        si.discount_amount = coupon_amt_final
                        si.discount_remarks = ("Coupon " + coupon_code_in + " applied: -"
                                               + str(coupon_amt_final) + " ("
                                               + str(coupon_pct_final) + "% of bill). Staff discount pending approval.")
                    elif (not draft_only) and discount_pct > 0 and pkg_price <= 0:
                        si.apply_discount_on = "Grand Total"
                        si.additional_discount_percentage = discount_pct
                        trail = ("Applied " + str(discount_pct) + "% via billing page")
                        if discount_by:
                            trail += ". Approver: " + discount_by
                        si.discount_remarks = trail + "."
                    elif (not draft_only) and discount_pct > 0 and pkg_price > 0:
                        si.discount_remarks = ("Fixed package price applied; the "
                                               + str(discount_pct)
                                               + "% discount was NOT applied on top.")
                                    # ---- Remarks for Office Use --------------------------------
                    # Long Text on Sales Invoice; allow_on_submit = 0, so it must
                    # be written on the DRAFT, before insert(). Client sends the
                    # key "office_remarks" from the billing web page.
                    raw_office_remarks = (
                        args.get("office_remarks") or ""
                    ).strip()

                    # Defence in depth: cap to 400 words server-side too.
                    if raw_office_remarks:
                        remark_words = raw_office_remarks.split()
                        if len(remark_words) > 400:
                            raw_office_remarks = " ".join(remark_words[:400])

                    si.custom_remarks_for_office_use = (
                        raw_office_remarks or None
                    )
                    # ------------------------------------------------------------
                    si.insert(ignore_permissions=False)

                    if draft_only:
                        frappe.db.commit()
                        frappe.response["message"] = {
                            "therapy_plan": tp.name,
                            "sales_invoice": si.name,
                            "grand_total": float(si.rounded_total or si.grand_total or 0),
                            "subtotal": subtotal,
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
                                    "subtotal": subtotal,
                                    "paid_amount": pay_amt,
                                    "outstanding": new_out,
                                    "discount_pct": discount_pct,
                                    "discount_amount": float(si.get("discount_amount") or 0),
                                    "coupon_applied": coupon_code_in if coupon_ok else "",
                                    "coupon_amount": coupon_amt_final if coupon_ok else 0,
                                    "coupon_percent": coupon_pct_final if coupon_ok else 0,
                                }
