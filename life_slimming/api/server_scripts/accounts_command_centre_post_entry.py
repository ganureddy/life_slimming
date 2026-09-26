"""accounts_command_centre_post_entry

Original API: accounts_command_centre_post_entry
Source modified: 2026-09-01 18:26:01.581898
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
    args = frappe.local.form_dict

    drcr = (args.get("drcr") or "").strip().upper()
    posting_date = args.get("date") or frappe.utils.nowdate()
    branch = (args.get("branch") or "").strip()
    led_code = (args.get("led_code") or "").strip()
    amount = frappe.utils.flt(args.get("amount"))
    mode = (args.get("mode") or "Cash").strip()
    narration = (args.get("narration") or "").strip()
    ref_no = (args.get("ref_no") or "").strip()
    party_label = (args.get("party") or "").strip()
    approved_by = (args.get("approved_by") or "").strip()

    COMPANY = "Life Slimming And Cosmetic Pvt Ltd"
    CASH_ACCOUNT = "173001 - Cash in Hand - LSACPL"
    HO_COST_CENTER = "Main - LSACPL"

    if drcr not in ["DR", "CR"]:
        frappe.throw("Entry type must be DR or CR")

    if not amount or amount <= 0:
        frappe.throw("Enter an amount greater than zero")

    if not led_code:
        frappe.throw("Select an Account Head / Ledger")

    if not narration:
        frappe.throw("Narration is required")

    # This version intentionally uses only the single 173001 Cash in Hand ledger.
    # Non-cash modes must be handled through their proper bank/payment accounts.
    if mode != "Cash":
        frappe.throw("This Entry Book currently permits Cash only. Use Payment Entry or the correct bank ledger for non-cash modes.")

    CC_MAP = {
        "HO": "Main - LSACPL",
        "MP": "Madhapur - LSACPL",
        "BH": "Banjara Hills - LSACPL",
        "CN": "Chandanagar - LSACPL",
        "CHN": "Chandanagar - LSACPL",
        "SRN": "SR Nagar - LSACPL",
        "HN": "Himayathnagar - LSACPL",
        "DN": "Dilsukhnagar - LSACPL",
        "DSK": "Dilsukhnagar - LSACPL",
        "GB": "Gachibowli - LSACPL",
        "GCB": "Gachibowli - LSACPL",
        "KP": "Kukatpally - LSACPL",
        "VW": "Vijayawada - LSACPL",
        "VJA": "Vijayawada - LSACPL",
        "VZ": "Vizag - LSACPL",
        "NLR": "Nellore - LSACPL"
    }

    # Entry Book display code -> actual ERPNext Account number.
    # New FY 2026-27 expense ledgers are included at the bottom.
    ACCT_NUM = {
        "4001": "411001",
        "4002": "412001",
        "4003": "412002",
        "4004": "421001",
        "4112": "226008",
        "4212": "173001",
        "5001": "5218",
        "5002": "611011",
        "5003": "911004",
        "5101": "611001",
        "5102": "611012",
        "5103": "5221",
        "5104": "611011",
        "5105": "611013",
        "5106": "611014",
        "5201": "812001",
        "5202": "812004",
        "5203": "812012",
        "5204": "911002",
        "5205": "813004",
        "5206": "812002",
        "5207": "812005",
        "5208": "813003",
        "5209": "811003",
        "5210": "812014",
        "5211": "813005",
        "EX001": "812002",
        "EX002": "522001",
        "EX003": "811002",
        "EX004": "813004",
        "EX005": "611001",
        "EX007": "813004",
        "EX008": "611011",
        "EX009": "911002",
        "EX010": "911004",
        "EX011": "812008",
        "EX012": "812007",
        "EX013": "812008",
        "EX014": "611011",
        "EX015": "812004",
        "EX016": "812002",
        "EX017": "812002",
        "EX018": "611011",
        "EX019": "611012",
        "EX020": "5221",
        "EX021": "812012",
        "EX022": "812012",
        "EX023": "812012",
        "EX024": "812005",
        "5301": "173001",
        "5302": "173001",
        "5303": "173001"
    }

    ACCT_NAME = {
        "EX006": "Director - LSACPL"
    }

    cost_center = CC_MAP.get(branch)

    if not cost_center:
        frappe.throw("No Cost Center mapping exists for branch " + branch)

    if not frappe.db.exists("Cost Center", cost_center):
        frappe.throw("Cost Center does not exist: " + cost_center)

    if not frappe.db.exists("Account", CASH_ACCOUNT):
        frappe.throw("Cash ledger does not exist: " + CASH_ACCOUNT)

    head_number = ACCT_NUM.get(led_code)
    ledger_account = ACCT_NAME.get(led_code)

    if not head_number and not ledger_account:
        frappe.throw("No ERPNext ledger mapping exists for Entry Book code " + led_code)

    if head_number:
        ledger_account = frappe.db.get_value(
            "Account",
            {
                "account_number": head_number,
                "company": COMPANY,
                "is_group": 0,
                "disabled": 0
            },
            "name"
        )
    else:
        ledger_account = frappe.db.get_value(
            "Account",
            {
                "name": ledger_account,
                "company": COMPANY,
                "is_group": 0,
                "disabled": 0
            },
            "name"
        )

    if not ledger_account:
        frappe.throw("Active posting ledger not found for Entry Book code " + led_code)

    if ledger_account == CASH_ACCOUNT and led_code not in ["4212", "5301", "5302", "5303"]:
        frappe.throw("The selected Account Head cannot be the Cash in Hand contra ledger")

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Cash Entry"
    je.posting_date = posting_date
    je.company = COMPANY

    if ref_no:
        je.cheque_no = ref_no
        je.cheque_date = posting_date

    remark = "Accounts Command Center | " + drcr + " | Branch: " + branch + " | " + narration

    if approved_by:
        remark = remark + " | Approved by: " + approved_by

    if party_label:
        remark = remark + " | Party: " + party_label

    je.user_remark = remark

    # Cash handover from a branch to Head Office:
    # Credit 173001 at branch Cost Center and debit 173001 at HO Cost Center.
    if led_code == "5301":
        if branch == "HO":
            frappe.throw("Select the sending branch for Cash Handover to HO")

        je.append("accounts", {
            "account": CASH_ACCOUNT,
            "credit_in_account_currency": amount,
            "cost_center": cost_center,
            "user_remark": narration
        })

        je.append("accounts", {
            "account": CASH_ACCOUNT,
            "debit_in_account_currency": amount,
            "cost_center": HO_COST_CENTER,
            "user_remark": narration
        })

    # Cash issued by HO to a branch:
    # Credit 173001 at HO and debit 173001 at receiving branch.
    elif led_code == "5303":
        if branch == "HO":
            frappe.throw("Select the receiving branch for Cash Issued by HO")

        je.append("accounts", {
            "account": CASH_ACCOUNT,
            "credit_in_account_currency": amount,
            "cost_center": HO_COST_CENTER,
            "user_remark": narration
        })

        je.append("accounts", {
            "account": CASH_ACCOUNT,
            "debit_in_account_currency": amount,
            "cost_center": cost_center,
            "user_remark": narration
        })

    # Normal cash payment/outflow:
    # Debit expense/asset/liability ledger and credit 173001 at the same Cost Center.
    elif drcr == "DR":
        je.append("accounts", {
            "account": ledger_account,
            "debit_in_account_currency": amount,
            "cost_center": cost_center,
            "user_remark": narration
        })

        je.append("accounts", {
            "account": CASH_ACCOUNT,
            "credit_in_account_currency": amount,
            "cost_center": cost_center,
            "user_remark": narration
        })

    # Normal cash receipt/inflow:
    # Debit 173001 and credit income/liability ledger at the same Cost Center.
    else:
        je.append("accounts", {
            "account": CASH_ACCOUNT,
            "debit_in_account_currency": amount,
            "cost_center": cost_center,
            "user_remark": narration
        })

        je.append("accounts", {
            "account": ledger_account,
            "credit_in_account_currency": amount,
            "cost_center": cost_center,
            "user_remark": narration
        })

    je.insert(ignore_permissions=True)
    je.submit()
    frappe.db.commit()

    frappe.response["message"] = {
        "ok": True,
        "voucher": je.name,
        "voucher_type": "Journal Entry",
        "posting_date": str(je.posting_date),
        "amount": amount,
        "drcr": drcr,
        "account": ledger_account,
        "contra": CASH_ACCOUNT,
        "cost_center": cost_center
    }
