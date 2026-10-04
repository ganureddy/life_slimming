"""payables_planner_api

Original API: payables_planner_api
Source modified: 2026-09-24 20:22:15.322164
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
    if frappe.form_dict.get("action") == "v4_documents":
        if frappe.session.user == "Guest":
            frappe.throw("Sign in to view documents")
        root_type = frappe.form_dict.get("source")
        root_name = frappe.form_dict.get("reference")
        if root_type not in ["Purchase Invoice", "Purchase Order", "Payment Entry", "Journal Entry"]:
            frappe.throw("Unsupported document type")
        root = frappe.get_doc(root_type, root_name)
        root.check_permission("read")
        documents = []
        files = []
        seen_docs = []
        seen_files = []
        pending = [{"type":root_type,"name":root_name}]
        # Only explicit ERP document relationships; never match by supplier alone.
        for step in range(0, 2):
            following = []
            for ref in pending:
                identity = ref["type"] + "|" + ref["name"]
                if identity in seen_docs:
                    continue
                seen_docs.append(identity)
                doc = None
                try:
                    doc = frappe.get_doc(ref["type"], ref["name"])
                    doc.check_permission("read")
                except Exception:
                    doc = None
                if doc and doc.get("company") == root.get("company"):
                    documents.append({"source":ref["type"],"reference":ref["name"],"status":doc.get("status") or doc.get("workflow_state") or str(doc.docstatus)})
                    attached = frappe.get_all("File", filters={"attached_to_doctype":ref["type"],"attached_to_name":ref["name"],"is_folder":0}, fields=["name","file_name","file_url","is_private","creation","owner"], limit_page_length=0)
                    for f in attached:
                        readable = False
                        try:
                            frappe.get_doc("File", f.name).check_permission("read")
                            readable = True
                        except Exception:
                            readable = False
                        if readable and f.file_url and f.file_url not in seen_files:
                            seen_files.append(f.file_url)
                            files.append({"name":f.file_name,"url":f.file_url,"private":f.is_private,"uploaded_at":str(f.creation),"uploaded_by":f.owner,"source":ref["type"],"reference":ref["name"]})
                    if step == 0:
                        if ref["type"] == "Purchase Invoice":
                            for item in doc.get("items") or []:
                                if item.get("purchase_order"):
                                    following.append({"type":"Purchase Order","name":item.purchase_order})
                        if ref["type"] == "Payment Entry":
                            for item in doc.get("references") or []:
                                if item.get("reference_doctype") in ["Purchase Invoice","Purchase Order"] and item.get("reference_name"):
                                    following.append({"type":item.reference_doctype,"name":item.reference_name})
                        if ref["type"] == "Purchase Order":
                            linked = []
                            try:
                                linked = frappe.get_list("Purchase Invoice", filters=[["Purchase Invoice Item","purchase_order","=",ref["name"]]], fields=["name"], limit_page_length=1000)
                            except Exception:
                                linked = []
                            for item in linked:
                                following.append({"type":"Purchase Invoice","name":item.name})
                        if ref["type"] in ["Purchase Invoice","Purchase Order"]:
                            linked = []
                            try:
                                linked = frappe.get_list("Payment Entry", filters=[["Payment Entry Reference","reference_doctype","=",ref["type"]],["Payment Entry Reference","reference_name","=",ref["name"]]], fields=["name"], limit_page_length=1000)
                            except Exception:
                                linked = []
                            for item in linked:
                                following.append({"type":"Payment Entry","name":item.name})
            pending = following
        frappe.response["message"] = {"ok":1,"documents":documents,"files":files}
    elif (frappe.form_dict.get("action") or "").startswith("v3_"):
        # LIFE Payables v3: permission-aware reporting and shared planning
        if frappe.session.user == "Guest":
            frappe.throw("Sign in to use Payables")
        companies = frappe.get_list("Company", fields=["name", "default_currency"], limit_page_length=100)
        company = frappe.form_dict.get("company") or (companies[0].name if companies else "")
        allowed = [c.name for c in companies]
        if company not in allowed:
            frappe.throw("Company is not accessible")
        company_doc = frappe.get_doc("Company", company)
        company_doc.check_permission("read")
        today = frappe.utils.nowdate()
        start = str(frappe.utils.get_first_day(frappe.utils.add_months(today, -6)))
        field = "custom_life_payables_workspace"
        configured = bool(frappe.get_meta("Company").has_field(field))
        workspace = json.loads(company_doc.get(field) or "{}") if configured else {}
        revision = workspace.get("revision", 0)
        mode = frappe.form_dict.get("action")
        if mode == "v3_setup":
            company_doc.check_permission("write")
            if not configured:
                frappe.get_doc({"doctype":"Custom Field", "dt":"Company", "fieldname":field, "label":"LIFE Payables Workspace", "fieldtype":"Code", "options":"JSON", "hidden":1, "no_copy":1}).insert()
            frappe.response["message"] = {"ok":1}
        elif mode == "v3_lookup":
            source = frappe.form_dict.get("source")
            if source not in ["Purchase Invoice","Purchase Order","Payment Entry","Journal Entry"]:
                frappe.throw("Unsupported document type")
            query = str(frappe.form_dict.get("query") or "")[:100]
            rows = frappe.get_list(source, filters={"company":company,"docstatus":["<",2],"name":["like","%"+query+"%"]}, fields=["name"], order_by="modified desc", limit_page_length=25)
            frappe.response["message"] = {"ok":1,"rows":rows}
        elif mode == "v3_masters":
            suppliers = frappe.get_list("Supplier", filters={"disabled":0}, fields=["name","supplier_name"], order_by="supplier_name asc", limit_page_length=10000)
            accounts = frappe.get_list("Account", filters={"company":company,"is_group":0,"disabled":0}, fields=["name","account_name","account_type","root_type"], order_by="name asc", limit_page_length=10000)
            centres = frappe.get_list("Cost Center", filters={"company":company,"is_group":0}, fields=["name"], limit_page_length=1000)
            frappe.response["message"] = {"ok":1,"suppliers":suppliers,"accounts":accounts,"centres":centres}
        elif mode in ["v3_save", "v3_validate_plan"]:
            company_doc.check_permission("write")
            if not configured:
                frappe.throw("Initialize shared planning first")
            proposed = frappe.form_dict.get("workspace") or {}
            if proposed.get("revision", -1) != revision:
                frappe.throw("Another user saved a newer plan. Refresh before saving.")
            if len(json.dumps(proposed)) > 1000000:
                frappe.throw("Plan is too large")
            for key in ["schedules", "recurring", "funding", "mapping", "baselines"]:
                if key not in proposed:
                    frappe.throw("Incomplete planning workspace")
            for old_month in workspace.get("baselines", {}):
                if json.dumps(workspace["baselines"][old_month]) != json.dumps(proposed["baselines"].get(old_month)):
                    frappe.throw("Saved monthly baselines cannot be overwritten")
            for month in proposed.get("baselines", {}):
                if month not in workspace.get("baselines", {}) and month != today[:7]:
                    frappe.throw("A new baseline can only be captured for the current month")
            latest_balances = {}
            changed_schedules = [s for s in proposed.get("schedules", []) if s not in workspace.get("schedules", [])]
            if changed_schedules:
                current_ap = _call_whitelisted("frappe.desk.query_report.run", report_name="Accounts Payable", filters={"company":company,"report_date":today,"ageing_based_on":"Due Date","range":"30, 60, 90, 120","calculate_ageing_with":"Report Date","in_party_currency":0,"show_future_payments":0}, ignore_prepared_report=True)
                for balance_row in current_ap.get("result", []):
                    if isinstance(balance_row, dict) and balance_row.get("voucher_no"):
                        balance_key = str(balance_row.get("voucher_type") or "") + "|" + str(balance_row.get("voucher_no") or "") + "|" + str(balance_row.get("party") or balance_row.get("supplier") or "") + "|" + str(balance_row.get("party_account") or balance_row.get("account") or "")
                        latest_balances[balance_key] = latest_balances.get(balance_key, 0) + frappe.utils.flt(balance_row.get("outstanding"))
            for schedule in proposed.get("schedules", []):
                if schedule in workspace.get("schedules", []):
                    continue
                if not schedule.get("reference") or not schedule.get("source"):
                    frappe.throw("Each schedule needs an ERP source")
                if schedule.get("source") not in ["Purchase Invoice", "Journal Entry", "Payment Entry"]:
                    frappe.throw("Unsupported source")
                source_doc = frappe.get_doc(schedule["source"], schedule["reference"])
                source_doc.check_permission("read")
                if source_doc.get("custom_payables_hold"):
                    frappe.throw("Resolve the ERP hold before scheduling this document")
                if source_doc.get("company") != company or source_doc.docstatus != 1:
                    frappe.throw("Only submitted documents in this company can be scheduled")
                if frappe.utils.flt(schedule.get("amount")) <= 0 or not schedule.get("date"):
                    frappe.throw("A positive amount and payout date are required")
                parts = schedule.get("installments") or [{"date":schedule.get("date"),"amount":schedule.get("amount")}]
                total_parts = 0
                for part in parts:
                    if not part.get("date") or frappe.utils.flt(part.get("amount")) <= 0:
                        frappe.throw("Each installment requires a payout date and positive amount")
                    if str(frappe.utils.getdate(part["date"])) < today:
                        frappe.throw("Revised installments cannot be dated before today")
                    total_parts = total_parts + frappe.utils.flt(part["amount"])
                if abs(total_parts - frappe.utils.flt(schedule.get("amount"))) > 0.01:
                    frappe.throw("Installment total does not match scheduled amount")
                if schedule.get("key") not in latest_balances:
                    frappe.throw("Source balance is no longer open. Refresh before planning")
                if abs(latest_balances[schedule["key"]] - frappe.utils.flt(schedule.get("outstanding_at_plan"))) > 0.01:
                    frappe.throw("ERP outstanding changed. Refresh and review the payout plan")
                if total_parts > latest_balances[schedule["key"]] + 0.01:
                    frappe.throw("Installments exceed the outstanding balance")
                if str(frappe.utils.getdate(schedule["date"])) < today and schedule not in workspace.get("schedules", []):
                    frappe.throw("New or revised payout plans cannot be dated before today")
            for recurring in proposed.get("recurring", []):
                if frappe.utils.flt(recurring.get("amount")) <= 0 or frappe.utils.cint(recurring.get("day")) < 1 or frappe.utils.cint(recurring.get("day")) > 31:
                    frappe.throw("Recurring commitment amount or day is invalid")
                if recurring.get("frequency") not in ["Monthly", "Weekly", "Quarterly", "One time"]:
                    frappe.throw("Invalid recurrence")
            for funding_key in proposed.get("funding", {}):
                funding = proposed["funding"][funding_key]
                for amount_key in ["collections", "additional", "reserve", "target"]:
                    value = frappe.utils.flt(funding.get(amount_key))
                    if value < 0 or value > 1000000000000:
                        frappe.throw("Funding values must be non-negative and within range")
            # Direct commitments remain forecasts until matched to a submitted ERP source.
            direct = proposed.get("direct_plans", workspace.get("direct_plans", []))
            proposed["direct_plans"] = direct
            direct_ids = []
            direct_references = []
            for plan in direct:
                if not plan.get("id") or plan["id"] in direct_ids:
                    frappe.throw("Each direct plan requires a unique reference")
                direct_ids.append(plan["id"])
                if plan.get("kind") not in ["Supplier advance","Expected bill","Other expense"]:
                    frappe.throw("Invalid direct plan type")
                if not plan.get("title") or not plan.get("date") or frappe.utils.flt(plan.get("amount")) <= 0:
                    frappe.throw("Direct plan needs a name, date and positive amount")
                old_plan = None
                for existing in workspace.get("direct_plans", []):
                    if existing.get("id") == plan["id"]:
                        old_plan = existing
                if plan != old_plan and str(frappe.utils.getdate(plan["date"])) < today:
                    frappe.throw("New or revised direct plans cannot be backdated")
                if plan.get("kind") != "Other expense" and not plan.get("supplier"):
                    frappe.throw("Select an existing supplier")
                if plan.get("supplier"):
                    supplier = frappe.get_doc("Supplier", plan["supplier"])
                    supplier.check_permission("read")
                    if supplier.get("disabled"):
                        frappe.throw("Supplier is disabled")
                account = frappe.get_doc("Account", plan.get("account"))
                account.check_permission("read")
                if account.company != company or account.is_group or account.get("disabled"):
                    frappe.throw("Select an active posting account in this company")
                if plan.get("branch") not in ["ALL","Unassigned",None,""]:
                    centre = frappe.get_doc("Cost Center", plan["branch"])
                    centre.check_permission("read")
                    if centre.company != company:
                        frappe.throw("Cost centre belongs to another company")
                plan["matched"] = False
                plan["matched_amount"] = 0
                if plan.get("reference"):
                    if plan.get("source") not in ["Purchase Invoice","Purchase Order","Payment Entry","Journal Entry"]:
                        frappe.throw("Select the linked ERP document type")
                    link_key = plan["source"] + "|" + plan["reference"]
                    if link_key in direct_references:
                        frappe.throw("An ERP document can be linked to only one direct plan")
                    direct_references.append(link_key)
                    linked_doc = frappe.get_doc(plan["source"], plan["reference"])
                    linked_doc.check_permission("read")
                    if linked_doc.company != company or linked_doc.docstatus == 2:
                        frappe.throw("Linked document is cancelled or belongs to another company")
                    linked_supplier = linked_doc.get("supplier") or (linked_doc.get("party") if linked_doc.get("party_type") == "Supplier" else "")
                    if plan.get("supplier") and linked_supplier and linked_supplier != plan["supplier"]:
                        frappe.throw("Linked document belongs to another supplier")
                    if linked_doc.docstatus == 1:
                        if plan["source"] == "Purchase Invoice":
                            plan["matched_amount"] = max(0, frappe.utils.flt(linked_doc.get("base_grand_total")))
                        elif plan["source"] == "Payment Entry" and linked_doc.get("payment_type") == "Pay":
                            plan["matched_amount"] = max(0, frappe.utils.flt(linked_doc.get("base_paid_amount")))
                        elif plan["source"] == "Journal Entry":
                            plan["matched_amount"] = max(0, frappe.utils.flt(linked_doc.get("total_debit")))
                    plan["matched"] = plan["matched_amount"] >= frappe.utils.flt(plan["amount"])
            # Client-supplied audit records are ignored. Changes are recorded by the server.
            plan_changes = []
            for collection in ["schedules","direct_plans","recurring"]:
                old_entries = workspace.get(collection, [])
                new_entries = proposed.get(collection, [])
                old_map = {}
                new_map = {}
                identity_field = "key" if collection == "schedules" else ("id" if collection == "direct_plans" else "name")
                for entry in old_entries:
                    old_map[entry.get(identity_field)] = entry
                for entry in new_entries:
                    new_map[entry.get(identity_field)] = entry
                identities = list(old_map.keys())
                for entry_id in new_map:
                    if entry_id not in identities:
                        identities.append(entry_id)
                for entry_id in identities:
                    before = old_map.get(entry_id)
                    after = new_map.get(entry_id)
                    if before != after:
                        plan_changes.append({"collection":collection,"key":entry_id,"before":before,"after":after})
            if workspace.get("mapping", {}) != proposed.get("mapping", {}):
                plan_changes.append({"collection":"mapping","key":"Account and reporting categories","before":json.dumps(workspace.get("mapping", {})),"after":json.dumps(proposed.get("mapping", {}))})
            if mode == "v3_save" and plan_changes:
                reason = str(frappe.form_dict.get("revision_reason") or "").strip()
                if not reason:
                    if frappe.form_dict.get("require_reason"):
                        frappe.throw("Enter a reason for this plan revision")
                    reason = "Saved from an earlier planner version; reason not captured"
            if mode == "v3_validate_plan":
                frappe.response["message"] = {"ok":1, "validated":1}
            else:
                proposed["plan_history"] = workspace.get("plan_history", [])
                if plan_changes:
                    proposed["plan_history"].append({"revision":revision+1,"by":frappe.session.user,"at":str(frappe.utils.now()),"reason":reason,"changes":plan_changes})
                if len(json.dumps(proposed)) > 1000000:
                    frappe.throw("Planning history needs archiving before further changes; no history was removed")
                proposed["revision"] = revision + 1
                proposed["saved_by"] = frappe.session.user
                proposed["saved_at"] = str(frappe.utils.now())
                company_doc.set(field, json.dumps(proposed))
                company_doc.save()
                frappe.response["message"] = {"ok":1, "workspace":proposed}
        else:
            issues = []
            def permitted_rows(dt, requested, filters):
                fields = [f for f in requested if f in ["name", "docstatus"] or frappe.get_meta(dt).has_field(f)]
                out = []
                for page in range(0, 51):
                    batch = frappe.get_list(dt, filters=filters, fields=fields, order_by="name asc", limit_start=page*1000, limit_page_length=1000)
                    out.extend(batch)
                    if len(batch) < 1000:
                        break
                if len(out) >= 51000:
                    frappe.throw("More than 51,000 source records: narrow the company or use a server report. Totals are not truncated.")
                return out
            ap = {}
            try:
                ap = _call_whitelisted("frappe.desk.query_report.run", report_name="Accounts Payable", filters={"company":company, "report_date":today, "ageing_based_on":"Due Date", "range":"30, 60, 90, 120", "calculate_ageing_with":"Report Date", "in_party_currency":0, "show_future_payments":0}, ignore_prepared_report=True)
            except Exception as error:
                frappe.throw("Accounts Payable report unavailable: " + str(error))
            invoices = permitted_rows("Purchase Invoice", ["name","supplier","supplier_name","posting_date","bill_date","bill_no","creation","payment_terms_template","due_date","docstatus","status","workflow_state","currency","conversion_rate","outstanding_amount","base_grand_total","grand_total","cost_center","branch","custom_branch","custom_payables_branch","custom_payables_head","custom_payables_hold","custom_payables_hold_reason"], {"company":company,"docstatus":["<",2],"posting_date":["<=",today]})
            # Child rows are restricted to the already permission-filtered parent IDs.
            invoice_ids = [r.name for r in invoices]
            item_map = {}
            if invoice_ids:
                item_rows = frappe.get_all("Purchase Invoice Item", filters={"parent":["in",invoice_ids],"parenttype":"Purchase Invoice"}, fields=["parent","expense_account","base_net_amount","cost_center","item_code"], limit_page_length=0)
                for item in item_rows:
                    if item.parent not in item_map:
                        item_map[item.parent] = []
                    item_map[item.parent].append({"account":item.expense_account,"amount":item.base_net_amount,"cost_center":item.cost_center,"item":item.item_code})
            for row in invoices:
                row["items"] = item_map.get(row.name, [])
            sales = permitted_rows("Sales Invoice", ["name","posting_date","base_net_total","base_grand_total","is_return","cost_center","branch","custom_branch"], {"company":company,"docstatus":1,"posting_date":["between",[start,today]]})
            payments = permitted_rows("Payment Entry", ["name","posting_date","payment_type","party_type","party","party_name","base_paid_amount","base_received_amount","source_exchange_rate","paid_from","paid_to","unallocated_amount","cost_center","branch","custom_branch"], {"company":company,"docstatus":1,"posting_date":["<=",today]})
            payment_ids = [r.name for r in payments]
            reference_map = {}
            if payment_ids:
                reference_rows = frappe.get_all("Payment Entry Reference", filters={"parent":["in",payment_ids],"parenttype":"Payment Entry"}, fields=["parent","reference_doctype","reference_name","allocated_amount"], limit_page_length=0)
                for ref in reference_rows:
                    if ref.parent not in reference_map:
                        reference_map[ref.parent] = []
                    reference_map[ref.parent].append({"source":ref.reference_doctype,"reference":ref.reference_name,"amount":ref.allocated_amount})
            for row in payments:
                row["references"] = reference_map.get(row.name, [])
            accounts = permitted_rows("Account", ["name","account_name","account_type","root_type","parent_account","account_currency"], {"company":company,"is_group":0})
            balances = []
            cashflows = []
            try:
                balances = frappe.get_list("GL Entry", filters={"company":company,"is_cancelled":0,"posting_date":["<=",today]}, fields=["account","party_type","sum(debit) as debit","sum(credit) as credit"], group_by="account, party_type", limit_page_length=10000)
                banks = [a.name for a in accounts if a.account_type in ["Bank","Cash"]]
                if banks:
                    cashflows = permitted_rows("GL Entry", ["name","posting_date","account","debit","credit","voucher_type","voucher_no","cost_center"], {"company":company,"is_cancelled":0,"posting_date":["between",[start,today]],"account":["in",banks]})
            except Exception as error:
                issues.append("Cash ledger unavailable: " + str(error))
            journal_names = []
            for row in ap.get("result", []):
                if not isinstance(row, dict):
                    continue
                if row.get("voucher_type") == "Journal Entry" and row.get("voucher_no") not in journal_names:
                    journal_names.append(row.get("voucher_no"))
            for row in cashflows:
                if row.get("voucher_type") == "Journal Entry" and row.get("voucher_no") not in journal_names:
                    journal_names.append(row.get("voucher_no"))
            journals = []
            if journal_names:
                journals = permitted_rows("Journal Entry", ["name","posting_date","voucher_type"], {"company":company,"docstatus":1,"name":["in",journal_names]})
                permitted_journals = [r.name for r in journals]
                journal_map = {}
                if permitted_journals:
                    journal_items = frappe.get_all("Journal Entry Account", filters={"parent":["in",permitted_journals],"parenttype":"Journal Entry"}, fields=["parent","account","debit","credit","cost_center","party_type","party","reference_type","reference_name"], limit_page_length=0)
                    for item in journal_items:
                        if item.parent not in journal_map:
                            journal_map[item.parent] = []
                        journal_map[item.parent].append(item)
                for row in journals:
                    row["accounts"] = journal_map.get(row.name, [])
            payroll = []
            if frappe.db.exists("DocType", "Salary Slip"):
                try:
                    payroll = permitted_rows("Salary Slip", ["name","start_date","end_date","posting_date","net_pay","base_net_pay","currency","status","branch"], {"company":company,"docstatus":1,"start_date":[">=",start]})
                except Exception as error:
                    issues.append("Salary Slip unavailable: " + str(error))
            direct_links = {}
            for planned in workspace.get("direct_plans", []):
                if planned.get("source") in ["Purchase Invoice","Payment Entry","Journal Entry","Purchase Order"] and planned.get("reference"):
                    direct_links[planned["source"]+"|"+planned["reference"]] = {"amount":0,"docstatus":0}
                    matched_doc = None
                    try:
                        matched_doc = frappe.get_doc(planned["source"], planned["reference"])
                        matched_doc.check_permission("read")
                    except Exception:
                        matched_doc = None
                    if matched_doc and matched_doc.company == company:
                        amount = 0
                        if matched_doc.docstatus == 1:
                            if planned["source"] == "Purchase Invoice":
                                amount = max(0, frappe.utils.flt(matched_doc.get("base_grand_total")))
                            elif planned["source"] == "Payment Entry" and matched_doc.get("payment_type") == "Pay":
                                amount = max(0, frappe.utils.flt(matched_doc.get("base_paid_amount")))
                            elif planned["source"] == "Journal Entry":
                                amount = max(0, frappe.utils.flt(matched_doc.get("total_debit")))
                        direct_links[planned["source"]+"|"+planned["reference"]] = {"amount":amount,"docstatus":matched_doc.docstatus}
            frappe.response["message"] = {"direct_links":direct_links,"ok":1,"today":today,"start":start,"company":company,"companies":companies,"currency":company_doc.default_currency,"user":frappe.session.user,"configured":configured,"workspace":workspace,"ap":ap,"invoices":invoices,"sales":sales,"payments":payments,"accounts":accounts,"balances":balances,"cashflows":cashflows,"payroll":payroll,"journals":journals,"issues":issues,"loaded_at":str(frappe.utils.now())}

    else:
        # =============================================================================
        # SERVER SCRIPT · payables_planner_api
        # TYPE        : API
        # API METHOD  : payables_planner_api
        #
        # Frappe / ERPNext v15
        #
        # Does NOT call the Accounts Payable Query Report.
        # Builds the payable book directly from GL Entry.
        #
        # Sources:
        #   PI = Purchase Invoice
        #   JE = Journal Entry
        #   PE = Payment Entry
        #
        # Response:
        #   book
        #   advances
        #   branches
        #   count
        #   advances_count
        #
        # Safe Server Script compatible:
        #   no import
        #   no f-string
        #   no try/except
        #   no tuple unpacking
        #   no augmented dict assignment
        # =============================================================================


        action = frappe.form_dict.get("action") or "load"

        today = frappe.utils.nowdate()

        company = frappe.form_dict.get("company") or "Life Slimming And Cosmetic Pvt Ltd"

        suffix = " - LSACPL"


        # =============================================================================
        # EXPENSE HEAD MAPPING
        # =============================================================================

        head_map = {
            "812000 - Office/General Administrative Expenses - LSACPL": "Office & Admin",
            "813000 - Repairs and Maintenance - LSACPL": "Repairs & Maintenance",
            "911000 - Advertising and Marketing - LSACPL": "Advertisement",
            "811000 - Legal & Professional Fees - LSACPL": "Professional Fees",
            "611000 - Payroll Expenses - LSACPL": "Salaries",
            "511000 - Consumables - Weight Loss - LSACPL": "Consumables",
            "512000 - Consumables - Skin - LSACPL": "Consumables",
            "513000 - Consumables - Hair - LSACPL": "Consumables",
            "521000 - Purchase - Weight Loss - LSACPL": "Consumables",
            "522000 - Purchase - Skin - LSACPL": "Consumables",
            "523000 - Purchase - Hair - LSACPL": "Consumables",
            "5200 - Indirect Expenses - LSACPL": "Office & Admin",
            "951100 - Interest & Bank Charges - LSACPL": "Interest & Bank",
        }


        acct_override = {
            "812013 - Security Services - LSACPL": "Housekeeping & Security",
            "812003 - Laundry Charges - LSACPL": "Laundry",
            "812001 - Rent - LSACPL": "Rent",
            "813002 - AMC-Software - LSACPL": "Software AMC",
            "813003 - AMC-Plant & Equipment - LSACPL": "Machinery AMC",
            "812005 - Printing & Stationary - LSACPL": "Office Supplies",
            "911002 - Digital Marketing Expenses - LSACPL": "Advertisement",
            "911001 - Outdoor Advertising Expenses - LSACPL": "Advertisement",
        }


        # =============================================================================
        # HELPERS
        # =============================================================================

        def branch_from_cc(cc):
            if not cc:
                return ""

            label = frappe.db.get_value(
                "Cost Center",
                cc,
                "cost_center_name"
            )

            if label:
                return label

            if cc.endswith(suffix):
                return cc[: -len(suffix)]

            return cc


        def bucket_of(days):
            if days <= 0:
                return "Current"

            if days <= 30:
                return "0-30"

            if days <= 60:
                return "31-60"

            if days <= 90:
                return "61-90"

            if days <= 120:
                return "91-120"

            return "120+"


        def src_of(vtype):
            if vtype == "Purchase Invoice":
                return "PI"

            if vtype == "Journal Entry":
                return "JE"

            if vtype == "Payment Entry":
                return "PE"

            return "OT"


        def doctype_of(src):
            if src == "PI":
                return "Purchase Invoice"

            if src == "JE":
                return "Journal Entry"

            if src == "PE":
                return "Payment Entry"

            return ""


        def has_field(doctype, fieldname):
            hit = frappe.db.get_value(
                "Custom Field",
                {
                    "dt": doctype,
                    "fieldname": fieldname
                },
                "name"
            )

            if hit:
                return 1

            return 0


        def head_for_pi(invoice_name):

            rows = frappe.get_all(
                "Purchase Invoice Item",
                filters={
                    "parent": invoice_name
                },
                fields=[
                    "expense_account",
                    "amount"
                ],
                order_by="amount desc"
            )

            head = ""

            for row in rows:

                acct = row.get("expense_account") or ""

                if not head and acct:

                    if acct in acct_override:
                        head = acct_override[acct]

                    else:

                        parent = frappe.db.get_value(
                            "Account",
                            acct,
                            "parent_account"
                        ) or ""

                        if parent in head_map:
                            head = head_map[parent]

            return head


        def party_name(voucher_type, voucher_no):

            if voucher_type == "Purchase Invoice":

                return frappe.db.get_value(
                    "Purchase Invoice",
                    voucher_no,
                    "supplier"
                ) or ""

            if voucher_type == "Payment Entry":

                return frappe.db.get_value(
                    "Payment Entry",
                    voucher_no,
                    "party_name"
                ) or frappe.db.get_value(
                    "Payment Entry",
                    voucher_no,
                    "party"
                ) or ""

            if voucher_type == "Journal Entry":

                return frappe.db.get_value(
                    "Journal Entry Account",
                    {
                        "parent": voucher_no,
                        "party_type": "Supplier"
                    },
                    "party"
                ) or ""

            return ""


        def bill_number(voucher_type, voucher_no):

            if voucher_type == "Purchase Invoice":

                return frappe.db.get_value(
                    "Purchase Invoice",
                    voucher_no,
                    "bill_no"
                ) or voucher_no

            return voucher_no


        def supplier_name_from_party(party):

            if not party:
                return ""

            return frappe.db.get_value(
                "Supplier",
                party,
                "supplier_name"
            ) or party


        # =============================================================================
        # WRITE ACTIONS
        # =============================================================================

        if action == "save_plan":

            name = frappe.form_dict.get("name")

            src = frappe.form_dict.get("src") or "PI"

            plan = frappe.form_dict.get("plan") or "{}"

            dt = doctype_of(src)

            if not name or not dt:
                frappe.throw("Missing invoice name or source")

            if has_field(dt, "custom_payables_plan"):

                frappe.db.set_value(
                    dt,
                    name,
                    "custom_payables_plan",
                    plan
                )

                frappe.db.commit()

            frappe.response["message"] = {
                "ok": 1,
                "name": name
            }


        # =============================================================================
        # SET HOLD
        # =============================================================================

        elif action == "set_hold":

            name = frappe.form_dict.get("name")

            src = frappe.form_dict.get("src") or "PI"

            hold = frappe.form_dict.get("hold")

            reason = frappe.form_dict.get("reason") or ""

            dt = doctype_of(src)

            if not name or not dt:
                frappe.throw("Missing invoice name or source")

            holdval = 0

            if str(hold) in [
                "1",
                "true",
                "True",
                "yes"
            ]:
                holdval = 1

            if has_field(dt, "custom_payables_hold"):

                frappe.db.set_value(
                    dt,
                    name,
                    "custom_payables_hold",
                    holdval
                )

                if has_field(
                    dt,
                    "custom_payables_hold_reason"
                ):

                    frappe.db.set_value(
                        dt,
                        name,
                        "custom_payables_hold_reason",
                        reason
                    )

                if holdval:

                    if has_field(
                        dt,
                        "custom_payables_plan"
                    ):

                        frappe.db.set_value(
                            dt,
                            name,
                            "custom_payables_plan",
                            "{}"
                        )

                frappe.db.commit()

            frappe.response["message"] = {
                "ok": 1,
                "name": name,
                "hold": holdval
            }


        # =============================================================================
        # COMPLETE
        # =============================================================================

        elif action == "complete":

            name = frappe.form_dict.get("name")

            src = frappe.form_dict.get("src") or "PI"

            head = frappe.form_dict.get("head") or ""

            branch = frappe.form_dict.get("branch") or ""

            dt = doctype_of(src)

            if not name or not dt:
                frappe.throw("Missing invoice name or source")

            if has_field(
                dt,
                "custom_payables_head"
            ):

                frappe.db.set_value(
                    dt,
                    name,
                    "custom_payables_head",
                    head
                )

                if has_field(
                    dt,
                    "custom_payables_branch"
                ):

                    frappe.db.set_value(
                        dt,
                        name,
                        "custom_payables_branch",
                        branch
                    )

                frappe.db.commit()

            frappe.response["message"] = {
                "ok": 1,
                "name": name
            }


        # =============================================================================
        # LOAD
        # =============================================================================

        else:

            # -------------------------------------------------------------------------
            # STEP 1
            # Get payable GL entries.
            #
            # In ERPNext supplier payable entries normally have:
            #
            # party_type = Supplier
            # party      = supplier
            # account    = payable account
            #
            # We first get submitted GL entries for the company.
            # -------------------------------------------------------------------------

            gl_rows = frappe.get_all(
                "GL Entry",
                filters={
                    "company": company,
                    "party_type": "Supplier",
                    "is_cancelled": 0
                },
                fields=[
                    "name",
                    "posting_date",
                    "account",
                    "party",
                    "party_type",
                    "debit",
                    "credit",
                    "debit_in_account_currency",
                    "credit_in_account_currency",
                    "account_currency",
                    "voucher_type",
                    "voucher_no",
                    "cost_center"
                ],
                order_by="posting_date asc"
            )


            # -------------------------------------------------------------------------
            # STEP 2
            # Aggregate by voucher + supplier + account.
            # -------------------------------------------------------------------------

            voucher_map = {}


            for gl in gl_rows:

                voucher_no = gl.get("voucher_no")

                if not voucher_no:
                    continue

                voucher_type = gl.get("voucher_type") or ""

                if voucher_type not in [
                    "Purchase Invoice",
                    "Journal Entry",
                    "Payment Entry"
                ]:
                    continue

                party = gl.get("party") or ""

                if not party:
                    continue

                key = (
                    voucher_type
                    + "||"
                    + voucher_no
                    + "||"
                    + party
                )

                if key not in voucher_map:

                    voucher_map[key] = {
                        "voucher_type": voucher_type,
                        "voucher_no": voucher_no,
                        "party": party,
                        "posting_date": gl.get("posting_date"),
                        "cost_center": gl.get("cost_center") or "",
                        "debit": 0,
                        "credit": 0
                    }

                obj = voucher_map[key]

                obj["debit"] = (
                    obj["debit"]
                    + (gl.get("debit_in_account_currency") or gl.get("debit") or 0)
                )

                obj["credit"] = (
                    obj["credit"]
                    + (gl.get("credit_in_account_currency") or gl.get("credit") or 0)
                )

                if not obj.get("cost_center") and gl.get("cost_center"):
                    obj["cost_center"] = gl.get("cost_center")


            # -------------------------------------------------------------------------
            # STEP 3
            # Build payable rows.
            #
            # For supplier accounts:
            #
            # credit > debit  = payable
            # debit > credit  = advance / credit balance
            # -------------------------------------------------------------------------

            book = []

            advances = []

            branch_set = {}


            for key in voucher_map:

                obj = voucher_map[key]

                voucher_type = obj.get("voucher_type") or ""

                voucher_no = obj.get("voucher_no") or ""

                party = obj.get("party") or ""

                debit = obj.get("debit") or 0

                credit = obj.get("credit") or 0

                outstanding = credit - debit

                if outstanding == 0:
                    continue


                # ---------------------------------------------------------------------
                # Purchase Invoice due date
                # ---------------------------------------------------------------------

                due = obj.get("posting_date")


                if voucher_type == "Purchase Invoice":

                    due = frappe.db.get_value(
                        "Purchase Invoice",
                        voucher_no,
                        "due_date"
                    ) or obj.get("posting_date")


                # ---------------------------------------------------------------------
                # Journal Entry / Payment Entry
                # ---------------------------------------------------------------------

                if voucher_type == "Journal Entry":

                    due = frappe.db.get_value(
                        "Journal Entry",
                        voucher_no,
                        "posting_date"
                    ) or obj.get("posting_date")


                if voucher_type == "Payment Entry":

                    due = frappe.db.get_value(
                        "Payment Entry",
                        voucher_no,
                        "posting_date"
                    ) or obj.get("posting_date")


                # ---------------------------------------------------------------------
                # Age
                # ---------------------------------------------------------------------

                days = frappe.utils.date_diff(
                    today,
                    due
                )


                # ---------------------------------------------------------------------
                # Branch
                # ---------------------------------------------------------------------

                cc = obj.get("cost_center") or ""

                branch = branch_from_cc(cc)


                # ---------------------------------------------------------------------
                # Source
                # ---------------------------------------------------------------------

                src = src_of(voucher_type)

                dt = doctype_of(src)


                # ---------------------------------------------------------------------
                # Head
                # ---------------------------------------------------------------------

                head = ""

                if src == "PI":
                    head = head_for_pi(voucher_no)


                # ---------------------------------------------------------------------
                # Stored custom fields
                # ---------------------------------------------------------------------

                plan = {}

                hold = 0

                hold_reason = ""


                if dt and has_field(
                    dt,
                    "custom_payables_plan"
                ):

                    stored_branch = frappe.db.get_value(
                        dt,
                        voucher_no,
                        "custom_payables_branch"
                    )

                    if stored_branch:
                        branch = stored_branch


                    stored_head = frappe.db.get_value(
                        dt,
                        voucher_no,
                        "custom_payables_head"
                    )

                    if stored_head:
                        head = stored_head


                    plan_raw = frappe.db.get_value(
                        dt,
                        voucher_no,
                        "custom_payables_plan"
                    )

                    if plan_raw:

                        plan = frappe.parse_json(
                            plan_raw
                        ) or {}


                    hold = frappe.db.get_value(
                        dt,
                        voucher_no,
                        "custom_payables_hold"
                    ) or 0


                    hold_reason = frappe.db.get_value(
                        dt,
                        voucher_no,
                        "custom_payables_hold_reason"
                    ) or ""


                # ---------------------------------------------------------------------
                # Branch fallback
                # ---------------------------------------------------------------------

                if not branch:
                    branch = "Unassigned"


                # ---------------------------------------------------------------------
                # Incomplete
                # ---------------------------------------------------------------------

                incomplete = 0

                if not head or branch == "Unassigned":
                    incomplete = 1


                # ---------------------------------------------------------------------
                # Supplier
                # ---------------------------------------------------------------------

                supplier = supplier_name_from_party(
                    party
                )


                # ---------------------------------------------------------------------
                # Bill number
                # ---------------------------------------------------------------------

                bill_no = bill_number(
                    voucher_type,
                    voucher_no
                )


                # ---------------------------------------------------------------------
                # Final row
                # ---------------------------------------------------------------------

                row = {
                    "i": voucher_no,
                    "src": src,
                    "s": voucher_type,
                    "b": branch,
                    "d": str(obj.get("posting_date") or ""),
                    "n": bill_no,
                    "v": supplier,
                    "e": head,
                    "t": 30,
                    "u": str(due or ""),
                    "a": abs(outstanding),
                    "g": days,
                    "bk": bucket_of(days),
                    "x": "H" if hold else "R",
                    "hr": hold_reason,
                    "inc": incomplete,
                    "p": plan
                }


                # ---------------------------------------------------------------------
                # Negative payable balance = advance / credit
                # ---------------------------------------------------------------------

                if outstanding < 0:

                    advances.append(row)

                else:

                    branch_set[branch] = 1

                    book.append(row)


            # =========================================================================
            # SORT
            # =========================================================================

            book.sort(
                key=lambda x: (
                    -x.get("a", 0),
                    x.get("u", "")
                )
            )

            advances.sort(
                key=lambda x: (
                    -x.get("a", 0),
                    x.get("u", "")
                )
            )


            # =========================================================================
            # BRANCH LIST
            # =========================================================================

            branch_list = []

            for bkey in branch_set:

                if bkey != "Unassigned":
                    branch_list.append(bkey)


            branch_list.sort()


            if "Unassigned" in branch_set:
                branch_list.append("Unassigned")


            # =========================================================================
            # RESPONSE
            # =========================================================================

            frappe.response["message"] = {
                "ok": 1,
                "today": today,
                "book": book,
                "advances": advances,
                "branches": branch_list,
                "count": len(book),
                "advances_count": len(advances)
            }
