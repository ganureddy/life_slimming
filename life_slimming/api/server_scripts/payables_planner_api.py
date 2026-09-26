"""payables_planner_api

Original API: payables_planner_api
Source modified: 2026-08-18 08:43:40.656790
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
