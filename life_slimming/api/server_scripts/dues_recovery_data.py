"""dues_recovery_data

Original API: dues_recovery_data
Source modified: 2026-07-25 23:09:36.354447
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

    args = frappe.form_dict
    branch  = args.get("branch") or ""
    d_from  = args.get("from") or ""
    d_to    = args.get("to") or ""
    q       = (args.get("q") or "").strip()
    q_low   = q.lower()

    limit = 500
    try:
        limit = int(args.get("limit") or 500)
    except Exception:
        limit = 500
    if limit > 1500:
        limit = 1500

    min_due = 0
    try:
        min_due = float(args.get("min_due") or 0)
    except Exception:
        min_due = 0

    # ---- branch scoping from User Permission (allow = "Branch") ----
    # If the logged-in user has Branch permissions, they may ONLY see those
    # branches. HO / System Manager (no Branch permission) see everything.
    me = frappe.session.user
    allowed_branches = []
    uperms = frappe.get_all(
        "User Permission",
        filters={"user": me, "allow": "Branch"},
        fields=["for_value"],
        limit_page_length=0,
    )
    for up in uperms:
        v = up.get("for_value")
        if v and v not in allowed_branches:
            allowed_branches.append(v)

    # is this user allowed to see all branches?
    see_all = 1
    if allowed_branches:
        see_all = 0

    # ---- plain dict filters only ----
    inv_filters = {}
    inv_filters["docstatus"] = 1
    inv_filters["outstanding_amount"] = [">", 0]

    if see_all:
        if branch:
            inv_filters["branch"] = branch
    else:
        # user is branch-restricted
        if branch and branch in allowed_branches:
            inv_filters["branch"] = branch
        elif len(allowed_branches) == 1:
            inv_filters["branch"] = allowed_branches[0]
        else:
            inv_filters["branch"] = ["in", allowed_branches]

    if d_from and d_to:
        inv_filters["due_date"] = ["between", [d_from, d_to]]
    elif d_from:
        inv_filters["due_date"] = [">=", d_from]
    elif d_to:
        inv_filters["due_date"] = ["<=", d_to]

    # fetch a bit extra when searching, since q is filtered in python
    fetch_len = limit
    if q:
        fetch_len = limit * 3
        if fetch_len > 3000:
            fetch_len = 3000

    inv = frappe.get_all(
        "Sales Invoice",
        filters=inv_filters,
        fields=[
            "name", "branch", "customer_name", "contact_mobile",
            "posting_date", "due_date", "grand_total", "outstanding_amount",
            "owner", "custom_incentive_employee_name", "ref_practitioner", "status"
        ],
        order_by="outstanding_amount desc",
        limit_page_length=fetch_len,
    )

    # ---- branch summary (respects scoping) ----
    open_filters = {"docstatus": 1, "outstanding_amount": [">", 0]}
    if not see_all:
        if len(allowed_branches) == 1:
            open_filters["branch"] = allowed_branches[0]
        else:
            open_filters["branch"] = ["in", allowed_branches]
    all_open = frappe.get_all(
        "Sales Invoice",
        filters=open_filters,
        fields=["branch", "outstanding_amount"],
        limit_page_length=0,
    )
    bmap = {}
    for r in all_open:
        b = r.get("branch") or "(no branch)"
        if b not in bmap:
            bmap[b] = {"branch": b, "n": 0, "due": 0}
        bmap[b]["n"] = bmap[b]["n"] + 1
        bmap[b]["due"] = bmap[b]["due"] + (r.get("outstanding_amount") or 0)
    branches = []
    for k in bmap:
        branches.append(bmap[k])
    # manual descending sort by due
    nb = len(branches)
    x = 0
    while x < nb:
        y = x + 1
        while y < nb:
            if branches[y]["due"] > branches[x]["due"]:
                t = branches[x]
                branches[x] = branches[y]
                branches[y] = t
            y = y + 1
        x = x + 1

    today = frappe.utils.getdate(frappe.utils.nowdate())

    prac_cache = {}

    out = []
    count = 0
    for r in inv:
        if count >= limit:
            break

        client = r.get("customer_name") or ""
        mobile = r.get("contact_mobile") or ""
        nm = r.get("name") or ""

        # python-side search filter
        if q:
            hit = False
            if q_low in client.lower():
                hit = True
            if (not hit) and (q in mobile):
                hit = True
            if (not hit) and (q_low in nm.lower()):
                hit = True
            if not hit:
                continue

        count = count + 1

        emp = r.get("custom_incentive_employee_name") or ""
        if not emp:
            ob = r.get("owner") or ""
            if "@" in ob:
                emp = ob.split("@")[0]
            else:
                emp = ob

        dd = r.get("due_date")
        age = 0
        if dd:
            try:
                age = frappe.utils.date_diff(today, dd)
            except Exception:
                age = 0
        if age < 0:
            age = 0

        inv_amt = r.get("grand_total") or 0
        due = r.get("outstanding_amount") or 0

        # saved manager update (single get, no IN-list)
        u = {}
        if frappe.db.exists("Dues Recovery Update", nm):
            u = frappe.db.get_value(
                "Dues Recovery Update", nm,
                ["manager_status", "collected_amount", "collected_on",
                 "mode_of_payment", "committed_amount", "committed_by", "reason", "remark"],
                as_dict=True
            ) or {}

        # first item name = service (single query per invoice, small)
        svc = ""
        it = frappe.get_all(
            "Sales Invoice Item",
            filters={"parent": nm},
            fields=["item_name"],
            order_by="idx asc",
            limit_page_length=1,
        )
        if it:
            svc = it[0].get("item_name") or ""

        ca = u.get("collected_amount")
        ma = u.get("committed_amount")

        # resolve practitioner ID -> name (cached)
        prac_id = r.get("ref_practitioner") or ""
        prac_name = ""
        if prac_id:
            if prac_id in prac_cache:
                prac_name = prac_cache[prac_id]
            else:
                pn = frappe.db.get_value("Healthcare Practitioner", prac_id, "practitioner_name")
                prac_name = pn or prac_id
                prac_cache[prac_id] = prac_name

        row = {
            "sno": count,
            "branch": r.get("branch") or "",
            "client": client,
            "mobile": mobile,
            "emp": emp,
            "practitioner": prac_name,
            "inv": nm,
            "invDate": str(r.get("posting_date") or ""),
            "service": svc,
            "invAmt": float(inv_amt),
            "paid": float(inv_amt) - float(due),
            "due": float(due),
            "nextDue": str(dd or ""),
            "age": int(age),
            "erpStatus": r.get("status") or "",
            "st": u.get("manager_status") or "PENDING",
            "colAmt": ("" if (ca in (None, 0)) else str(ca)),
            "colDate": str(u.get("collected_on") or ""),
            "mode": u.get("mode_of_payment") or "",
            "cmtAmt": ("" if (ma in (None, 0)) else str(ma)),
            "cmtDate": str(u.get("committed_by") or ""),
            "reason": u.get("reason") or "",
            "remark": u.get("remark") or "",
        }
        out.append(row)

    frappe.response["message"] = {"branches": branches, "rows": out, "count": len(out)}
