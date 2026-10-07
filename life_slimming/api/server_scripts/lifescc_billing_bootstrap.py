"""lifescc.billing.bootstrap

Original API: lifescc.billing.bootstrap
Source modified: 2026-09-16 18:07:53.725729
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
    # LIFE-DOCTOR-DESIGNATION-V1
    # # ═══════════════════════════════════════════════════════════════════════════
    # # SERVER SCRIPT  #4 (NEW)   ·   lifescc.billing.bootstrap
    # # Type: API   ·   Method: lifescc.billing.bootstrap   ·   Guest: No
    # #
    # # WHY: portal users are blocked from reading Therapy Type / Branch /
    # # Healthcare Practitioner / Therapy Plan Template directly via
    # # frappe.client.get_list, so those dropdowns came up EMPTY on the page.
    # # This one server-side call returns every reference list the billing
    # # page needs, where permissions are not a problem.
    # #
    # # RETURNS (frappe.response["message"]):
    # #   branches      : [ "Vijayawada", ... ]
    # #   therapies     : [ {n,item,rate,min,max,unit,category}, ... ]
    # #   templates     : [ {name,plan_name,total_sessions,total_amount,
    # #                       lines:[{therapy_type,no_of_sessions,rate,amount,category}]}, ... ]
    # #   practitioners : [ {name,practitioner_name,branch,status,last_used}, ... ]
    # #   modes         : [ {name,type}, ... ]
    # #   approvers     : [ {user,full_name,approval_level,designation}, ... ]
    # # ═══════════════════════════════════════════════════════════════════════════

    # COMPANY = "Life Slimming And Cosmetic Pvt Ltd"

    # # ---- Branches (exclude Head Office / Testing) ----
    # branches = []
    # brows = frappe.get_all("Branch", fields=["name"], order_by="name asc")
    # for b in brows:
    #     nm = b.get("name")
    #     if nm and nm not in ("Head Office", "Testing Branch"):
    #         branches.append(nm)

    # # ---- Therapies for billing ----
    # # is_billable = 1  -> can be sold individually
    # # is_billable = 0  -> component of a package only (still needed so that
    # #                     package/template lines can resolve their rate,
    # #                     category and min/max) — flagged pkg_only = 1 so the
    # #                     page can hide them from Individual Therapy search.
    # therapies = []
    # trows = frappe.get_all(
    #     "Therapy Type",
    #     filters={"disabled": 0},
    #     fields=["name", "therapy_type", "item_code", "item", "rate",
    #             "minimum_price", "maximum_price", "healthcare_service_unit",
    #             "is_billable"],
    #     order_by="healthcare_service_unit asc, therapy_type asc",
    #     limit_page_length=0,
    # )
    # for t in trows:
    #     therapies.append({
    #         "n": t.get("therapy_type") or t.get("name"),
    #         "item": t.get("item_code") or t.get("item"),
    #         "rate": t.get("rate") or 0,
    #         "min": t.get("minimum_price") or 0,
    #         "max": t.get("maximum_price") or 0,
    #         "unit": t.get("healthcare_service_unit") or "",
    #         "category": t.get("healthcare_service_unit") or "Other",
    #         "pkg_only": 0 if t.get("is_billable") else 1,
    #     })

    # # quick lookup: therapy_type -> category (for template lines)
    # cat_map = {}
    # for t in therapies:
    #     cat_map[t["n"]] = t["category"]

    # # ---- Active Therapy Plan Templates + their child therapy_types ----
    # templates = []
    # tpls = frappe.get_all(
    #     "Therapy Plan Template",
    #     filters={"is_active": 1},
    #     fields=["name", "plan_name", "total_sessions", "total_amount",
    #             "item_code", "offer_price"],
    #     order_by="plan_name asc",
    #     limit_page_length=0,
    # )
    # for tp in tpls:
    #     lines = []
    #     dets = frappe.get_all(
    #         "Therapy Plan Template Detail",
    #         filters={"parent": tp.get("name")},
    #         fields=["therapy_type", "no_of_sessions", "rate", "amount"],
    #         order_by="idx asc",
    #         limit_page_length=0,
    #     )
    #     for d in dets:
    #         tt = d.get("therapy_type")
    #         lines.append({
    #             "therapy_type": tt,
    #             "no_of_sessions": d.get("no_of_sessions") or 0,
    #             "rate": d.get("rate") or 0,
    #             "amount": d.get("amount") or 0,
    #             "category": cat_map.get(tt, "Other"),
    #         })
    #     templates.append({
    #         "name": tp.get("name"),
    #         "plan_name": tp.get("plan_name") or tp.get("name"),
    #         "total_sessions": tp.get("total_sessions") or 0,
    #         "total_amount": tp.get("total_amount") or 0,
    #         "offer_price": tp.get("offer_price") or 0,
    #         "item_code": tp.get("item_code") or "",
    #         "lines": lines,
    #     })

    # # ---- Healthcare Practitioners (active only, with last-used date) ----
    # # Duplicate practitioner ids exist for the same person (e.g. two "Pattala
    # # Sukanya" ids in Nellore). The billing page keeps only the most recently used
    # # one, so we send status + last_used and drop inactive ids here.
    # practitioners = []
    # prows = frappe.get_all(
    #     "Healthcare Practitioner",
    #     fields=["name", "practitioner_name", "branch", "status"],
    #     order_by="practitioner_name asc",
    #     limit_page_length=0,
    # )
    # last_used_map = {}
    # # Only the recent window matters for "most recently used"; bounding the scan
    # # keeps the bootstrap fast even with tens of thousands of invoices.
    # lu_cutoff = frappe.utils.add_months(frappe.utils.today(), -18)
    # lu_rows = frappe.get_all(
    #     "Sales Invoice",
    #     filters={"ref_practitioner": ["is", "set"],
    #              "posting_date": [">=", lu_cutoff]},
    #     fields=["ref_practitioner", "max(posting_date) as last_used"],
    #     group_by="ref_practitioner",
    #     limit_page_length=0,
    # )
    # for lr in lu_rows:
    #     rp = lr.get("ref_practitioner")
    #     if rp:
    #         last_used_map[rp] = str(lr.get("last_used") or "")
    # for p in prows:
    #     st = p.get("status") or "Active"
    #     if str(st).lower() != "active":
    #         continue
    #     practitioners.append({
    #         "name": p.get("name"),
    #         "practitioner_name": p.get("practitioner_name") or p.get("name"),
    #         "branch": p.get("branch") or "",
    #         "status": st,
    #         "last_used": last_used_map.get(p.get("name"), ""),
    #     })

    # # ---- Enabled Modes of Payment that HAVE a company account ----
    # modes = []
    # mrows = frappe.get_all(
    #     "Mode of Payment",
    #     filters={"enabled": 1},
    #     fields=["name", "type"],
    #     order_by="name asc",
    #     limit_page_length=0,
    # )
    # for m in mrows:
    #     acc = frappe.db.get_value(
    #         "Mode of Payment Account",
    #         {"parent": m.get("name"), "company": COMPANY},
    #         "default_account",
    #     )
    #     if acc:
    #         # Some modes are typed "Cash" but actually settle into a BANK
    #         # account (e.g. "mobile payments" -> ICICI). Use the real account
    #         # type so the UI knows when a reference / UTR is required.
    #         acct_type = frappe.db.get_value("Account", acc, "account_type") or ""
    #         modes.append({
    #             "name": m.get("name"),
    #             "type": m.get("type") or "Bank",
    #             "account": acc,
    #             "acct_type": acct_type,
    #         })

    # # ---- Discount approvers ----
    # approvers = []
    # arows = frappe.get_all(
    #     "Discount Approver Master",
    #     fields=["user", "full_name", "approval_level", "designation"],
    #     order_by="approval_level asc",
    #     limit_page_length=0,
    # )
    # for a in arows:
    #     approvers.append({
    #         "user": a.get("user"),
    #         "full_name": a.get("full_name") or a.get("user"),
    #         "approval_level": a.get("approval_level") or "L1",
    #         "designation": a.get("designation") or "",
    #     })

    # # ---- Active offers (Pricing Rules) valid today, item-code price offers ----
    # offers = []
    # today = frappe.utils.today()
    # prrows = frappe.get_all(
    #     "Pricing Rule",
    #     filters={"disable": 0, "selling": 1},
    #     fields=["name", "title", "apply_on", "price_or_product_discount", "rate",
    #             "discount_percentage", "discount_amount", "min_qty", "max_qty",
    #             "valid_from", "valid_upto"],
    #     order_by="modified desc",
    #     limit_page_length=0,
    # )
    # for o in prrows:
    #     vf = o.get("valid_from")
    #     vu = o.get("valid_upto")
    #     # validity window check (server-side)
    #     if vf and str(vf)[:10] > today:
    #         continue
    #     if vu and str(vu)[:10] < today:
    #         continue
    #     ic = ""
    #     if o.get("apply_on") == "Item Code":
    #         # item_code lives on the child table "Pricing Rule Item Code"
    #         icrow = frappe.db.get_value(
    #             "Pricing Rule Item Code",
    #             {"parent": o.get("name")},
    #             "item_code",
    #         )
    #         ic = icrow or ""
    #     offers.append({
    #         "name": o.get("name"),
    #         "title": o.get("title") or o.get("name"),
    #         "apply_on": o.get("apply_on") or "",
    #         "item_code": ic,
    #         "price_or_product_discount": o.get("price_or_product_discount") or "Price",
    #         "rate": o.get("rate") or 0,
    #         "discount_percentage": o.get("discount_percentage") or 0,
    #         "discount_amount": o.get("discount_amount") or 0,
    #         "min_qty": o.get("min_qty") or 0,
    #         "max_qty": o.get("max_qty") or 0,
    #         "valid_from": vf,
    #         "valid_upto": vu,
    #     })

    # # ---- Complimentary session items (item group "Complimentary Sessions") ----
    # comp_items = []
    # citems = frappe.get_all(
    #     "Item",
    #     filters={"item_group": "Complimentary Sessions", "disabled": 0},
    #     fields=["name", "item_name", "custom_max_qty_per_bill", "standard_rate"],
    #     order_by="item_name asc",
    #     limit_page_length=0,
    # )
    # for c in citems:
    #     comp_items.append({
    #         "item_code": c.get("name"),
    #         "item_name": c.get("item_name") or c.get("name"),
    #         "max_qty": c.get("custom_max_qty_per_bill") or 0,
    #         "rate": c.get("standard_rate") or 0,
    #     })

    # # ---- Which branches may THIS user see? ----
    # # Branch users are restricted with User Permissions on Branch, so that is
    # # the source of truth. If they have none, they are treated as Head Office
    # # and may see every branch.
    # allowed_branches = []
    # uprows = frappe.get_all(
    #     "User Permission",
    #     filters={"user": frappe.session.user, "allow": "Branch"},
    #     fields=["for_value"],
    #     limit_page_length=0,
    # )
    # for u in uprows:
    #     v = u.get("for_value")
    #     if v and v not in allowed_branches:
    #         allowed_branches.append(v)

    # # the user's own branch from their Employee record (may be blank)
    # user_branch = ""
    # emp = frappe.db.get_value(
    #     "Employee", {"user_id": frappe.session.user}, ["branch"], as_dict=True
    # )
    # if emp and emp.get("branch"):
    #     user_branch = emp.get("branch")
    # if not user_branch and len(allowed_branches) == 1:
    #     user_branch = allowed_branches[0]

    # # a user with no branch restriction is a Head Office / all-branch user
    # is_head_office = 1
    # if allowed_branches:
    #     is_head_office = 0

    # frappe.response["message"] = {
    #     "user": frappe.session.user,
    #     "user_branch": user_branch,
    #     "allowed_branches": allowed_branches,
    #     "is_head_office": is_head_office,
    #     "branches": branches,
    #     "therapies": therapies,
    #     "templates": templates,
    #     "practitioners": practitioners,
    #     "modes": modes,
    #     "approvers": approvers,
    #     "offers": offers,
    #     "comp_items": comp_items,
    # }

















































    # # ═══════════════════════════════════════════════════════════════════════════
    # # SERVER SCRIPT  #4 (NEW)   ·   lifescc.billing.bootstrap
    # # Type: API   ·   Method: lifescc.billing.bootstrap   ·   Guest: No
    # #
    # # WHY: portal users are blocked from reading Therapy Type / Branch /
    # # Healthcare Practitioner / Therapy Plan Template directly via
    # # frappe.client.get_list, so those dropdowns came up EMPTY on the page.
    # # This one server-side call returns every reference list the billing
    # # page needs, where permissions are not a problem.
    # #
    # # RETURNS (frappe.response["message"]):
    # #   branches      : [ "Vijayawada", ... ]
    # #   therapies     : [ {n,item,rate,min,max,unit,category}, ... ]
    # #   templates     : [ {name,plan_name,total_sessions,total_amount,
    # #                       lines:[{therapy_type,no_of_sessions,rate,amount,category}]}, ... ]
    # #   practitioners : [ {name,practitioner_name,branch,status,last_used}, ... ]
    # #   modes         : [ {name,type}, ... ]
    # #   approvers     : [ {user,full_name,approval_level,designation}, ... ]
    # # ═══════════════════════════════════════════════════════════════════════════

    # COMPANY = "Life Slimming And Cosmetic Pvt Ltd"

    # # ---- Branches (exclude Head Office / Testing) ----
    # branches = []
    # brows = frappe.get_all("Branch", fields=["name"], order_by="name asc")
    # for b in brows:
    #     nm = b.get("name")
    #     if nm and nm not in ("Head Office", "Testing Branch"):
    #         branches.append(nm)

    # # ---- Therapies for billing ----
    # # is_billable = 1  -> can be sold individually
    # # is_billable = 0  -> component of a package only (still needed so that
    # #                     package/template lines can resolve their rate,
    # #                     category and min/max) — flagged pkg_only = 1 so the
    # #                     page can hide them from Individual Therapy search.
    # therapies = []
    # trows = frappe.get_all(
    #     "Therapy Type",
    #     filters={"disabled": 0},
    #     fields=["name", "therapy_type", "item_code", "item", "rate",
    #             "minimum_price", "maximum_price", "healthcare_service_unit",
    #             "is_billable", "custom_show_in_billing"],
    #     order_by="healthcare_service_unit asc, therapy_type asc",
    #     limit_page_length=0,
    # )
    # for t in trows:
    #     therapies.append({
    #         "n": t.get("therapy_type") or t.get("name"),
    #         "item": t.get("item_code") or t.get("item"),
    #         "rate": t.get("rate") or 0,
    #         "min": t.get("minimum_price") or 0,
    #         "max": t.get("maximum_price") or 0,
    #         "unit": t.get("healthcare_service_unit") or "",
    #         "category": t.get("healthcare_service_unit") or "Other",
    #         "pkg_only": 0 if t.get("is_billable") else 1,
    #         "show_in_billing": 1 if t.get("custom_show_in_billing") else 0,
    #     })

    # # quick lookup: therapy_type -> category (for template lines)
    # cat_map = {}
    # for t in therapies:
    #     cat_map[t["n"]] = t["category"]

    # # ---- Active Therapy Plan Templates + their child therapy_types ----
    # templates = []
    # tpls = frappe.get_all(
    #     "Therapy Plan Template",
    #     filters={"is_active": 1},
    #     fields=["name", "plan_name", "total_sessions", "total_amount",
    #             "item_code", "offer_price"],
    #     order_by="plan_name asc",
    #     limit_page_length=0,
    # )
    # for tp in tpls:
    #     lines = []
    #     dets = frappe.get_all(
    #         "Therapy Plan Template Detail",
    #         filters={"parent": tp.get("name")},
    #         fields=["therapy_type", "no_of_sessions", "rate", "amount"],
    #         order_by="idx asc",
    #         limit_page_length=0,
    #     )
    #     for d in dets:
    #         tt = d.get("therapy_type")
    #         lines.append({
    #             "therapy_type": tt,
    #             "no_of_sessions": d.get("no_of_sessions") or 0,
    #             "rate": d.get("rate") or 0,
    #             "amount": d.get("amount") or 0,
    #             "category": cat_map.get(tt, "Other"),
    #         })
    #     templates.append({
    #         "name": tp.get("name"),
    #         "plan_name": tp.get("plan_name") or tp.get("name"),
    #         "total_sessions": tp.get("total_sessions") or 0,
    #         "total_amount": tp.get("total_amount") or 0,
    #         "offer_price": tp.get("offer_price") or 0,
    #         "item_code": tp.get("item_code") or "",
    #         "lines": lines,
    #     })

    # # ---- Healthcare Practitioners (active only, with last-used date) ----
    # # Duplicate practitioner ids exist for the same person (e.g. two "Pattala
    # # Sukanya" ids in Nellore). The billing page keeps only the most recently used
    # # one, so we send status + last_used and drop inactive ids here.
    # practitioners = []
    # prows = frappe.get_all(
    #     "Healthcare Practitioner",
    #     fields=["name", "practitioner_name", "branch", "status"],
    #     order_by="practitioner_name asc",
    #     limit_page_length=0,
    # )
    # last_used_map = {}
    # # Only the recent window matters for "most recently used"; bounding the scan
    # # keeps the bootstrap fast even with tens of thousands of invoices.
    # lu_cutoff = frappe.utils.add_months(frappe.utils.today(), -18)
    # lu_rows = frappe.get_all(
    #     "Sales Invoice",
    #     filters={"ref_practitioner": ["is", "set"],
    #              "posting_date": [">=", lu_cutoff]},
    #     fields=["ref_practitioner", "max(posting_date) as last_used"],
    #     group_by="ref_practitioner",
    #     limit_page_length=0,
    # )
    # for lr in lu_rows:
    #     rp = lr.get("ref_practitioner")
    #     if rp:
    #         last_used_map[rp] = str(lr.get("last_used") or "")
    # for p in prows:
    #     st = p.get("status") or "Active"
    #     if str(st).lower() != "active":
    #         continue
    #     practitioners.append({
    #         "name": p.get("name"),
    #         "practitioner_name": p.get("practitioner_name") or p.get("name"),
    #         "branch": p.get("branch") or "",
    #         "status": st,
    #         "last_used": last_used_map.get(p.get("name"), ""),
    #     })

    # # ---- Enabled Modes of Payment that HAVE a company account ----
    # modes = []
    # mrows = frappe.get_all(
    #     "Mode of Payment",
    #     filters={"enabled": 1},
    #     fields=["name", "type"],
    #     order_by="name asc",
    #     limit_page_length=0,
    # )
    # for m in mrows:
    #     acc = frappe.db.get_value(
    #         "Mode of Payment Account",
    #         {"parent": m.get("name"), "company": COMPANY},
    #         "default_account",
    #     )
    #     if acc:
    #         # Some modes are typed "Cash" but actually settle into a BANK
    #         # account (e.g. "mobile payments" -> ICICI). Use the real account
    #         # type so the UI knows when a reference / UTR is required.
    #         acct_type = frappe.db.get_value("Account", acc, "account_type") or ""
    #         modes.append({
    #             "name": m.get("name"),
    #             "type": m.get("type") or "Bank",
    #             "account": acc,
    #             "acct_type": acct_type,
    #         })

    # # ---- Discount approvers ----
    # approvers = []
    # arows = frappe.get_all(
    #     "Discount Approver Master",
    #     fields=["user", "full_name", "approval_level", "designation"],
    #     order_by="approval_level asc",
    #     limit_page_length=0,
    # )
    # for a in arows:
    #     approvers.append({
    #         "user": a.get("user"),
    #         "full_name": a.get("full_name") or a.get("user"),
    #         "approval_level": a.get("approval_level") or "L1",
    #         "designation": a.get("designation") or "",
    #     })

    # # ---- Active offers (Pricing Rules) valid today, item-code price offers ----
    # offers = []
    # today = frappe.utils.today()
    # prrows = frappe.get_all(
    #     "Pricing Rule",
    #     filters={"disable": 0, "selling": 1},
    #     fields=["name", "title", "apply_on", "price_or_product_discount", "rate",
    #             "discount_percentage", "discount_amount", "min_qty", "max_qty",
    #             "valid_from", "valid_upto"],
    #     order_by="modified desc",
    #     limit_page_length=0,
    # )
    # for o in prrows:
    #     vf = o.get("valid_from")
    #     vu = o.get("valid_upto")
    #     # validity window check (server-side)
    #     if vf and str(vf)[:10] > today:
    #         continue
    #     if vu and str(vu)[:10] < today:
    #         continue
    #     ic = ""
    #     if o.get("apply_on") == "Item Code":
    #         # item_code lives on the child table "Pricing Rule Item Code"
    #         icrow = frappe.db.get_value(
    #             "Pricing Rule Item Code",
    #             {"parent": o.get("name")},
    #             "item_code",
    #         )
    #         ic = icrow or ""
    #     offers.append({
    #         "name": o.get("name"),
    #         "title": o.get("title") or o.get("name"),
    #         "apply_on": o.get("apply_on") or "",
    #         "item_code": ic,
    #         "price_or_product_discount": o.get("price_or_product_discount") or "Price",
    #         "rate": o.get("rate") or 0,
    #         "discount_percentage": o.get("discount_percentage") or 0,
    #         "discount_amount": o.get("discount_amount") or 0,
    #         "min_qty": o.get("min_qty") or 0,
    #         "max_qty": o.get("max_qty") or 0,
    #         "valid_from": vf,
    #         "valid_upto": vu,
    #     })

    # # ---- Complimentary session items (item group "Complimentary Sessions") ----
    # comp_items = []
    # citems = frappe.get_all(
    #     "Item",
    #     filters={"item_group": "Complimentary Sessions", "disabled": 0},
    #     fields=["name", "item_name", "custom_max_qty_per_bill", "standard_rate"],
    #     order_by="item_name asc",
    #     limit_page_length=0,
    # )
    # for c in citems:
    #     comp_items.append({
    #         "item_code": c.get("name"),
    #         "item_name": c.get("item_name") or c.get("name"),
    #         "max_qty": c.get("custom_max_qty_per_bill") or 0,
    #         "rate": c.get("standard_rate") or 0,
    #     })

    # # ---- Which branches may THIS user see? ----
    # # Branch users are restricted with User Permissions on Branch, so that is
    # # the source of truth. If they have none, they are treated as Head Office
    # # and may see every branch.
    # allowed_branches = []
    # uprows = frappe.get_all(
    #     "User Permission",
    #     filters={"user": frappe.session.user, "allow": "Branch"},
    #     fields=["for_value"],
    #     limit_page_length=0,
    # )
    # for u in uprows:
    #     v = u.get("for_value")
    #     if v and v not in allowed_branches:
    #         allowed_branches.append(v)

    # # the user's own branch from their Employee record (may be blank)
    # user_branch = ""
    # emp = frappe.db.get_value(
    #     "Employee", {"user_id": frappe.session.user}, ["branch"], as_dict=True
    # )
    # if emp and emp.get("branch"):
    #     user_branch = emp.get("branch")
    # if not user_branch and len(allowed_branches) == 1:
    #     user_branch = allowed_branches[0]

    # # a user with no branch restriction is a Head Office / all-branch user
    # is_head_office = 1
    # if allowed_branches:
    #     is_head_office = 0

    # frappe.response["message"] = {
    #     "user": frappe.session.user,
    #     "user_branch": user_branch,
    #     "allowed_branches": allowed_branches,
    #     "is_head_office": is_head_office,
    #     "branches": branches,
    #     "therapies": therapies,
    #     "templates": templates,
    #     "practitioners": practitioners,
    #     "modes": modes,
    #     "approvers": approvers,
    #     "offers": offers,
    #     "comp_items": comp_items,
    # }
















    # LIFE Billing Bootstrap
    # Server Script Type: API
    # API Method: lifescc.billing.bootstrap
    # Allow Guest: No

    COMPANY = "Life Slimming And Cosmetic Pvt Ltd"


    # ============================================================
    # BRANCHES
    # Exclude Head Office and Testing Branch
    # ============================================================

    branches = []

    branch_rows = frappe.get_all(
        "Branch",
        fields=["name"],
        order_by="name asc",
        limit_page_length=0
    )

    for branch_row in branch_rows:
        branch_name = branch_row.get("name")

        if (
            branch_name
            and branch_name not in ("Head Office", "Testing Branch")
        ):
            branches.append(branch_name)


    # ============================================================
    # THERAPY TYPES
    # ============================================================

    therapies = []

    therapy_rows = frappe.get_all(
        "Therapy Type",
        filters={
            "disabled": 0
        },
        fields=[
            "name",
            "therapy_type",
            "item_code",
            "item",
            "rate",
            "minimum_price",
            "maximum_price",
            "healthcare_service_unit",
            "is_billable",
            "custom_show_in_billing"
        ],
        order_by="healthcare_service_unit asc, therapy_type asc",
        limit_page_length=0
    )

    for therapy_row in therapy_rows:
        therapies.append({
            "n": (
                therapy_row.get("therapy_type")
                or therapy_row.get("name")
            ),
            "item": (
                therapy_row.get("item_code")
                or therapy_row.get("item")
            ),
            "rate": therapy_row.get("rate") or 0,
            "min": therapy_row.get("minimum_price") or 0,
            "max": therapy_row.get("maximum_price") or 0,
            "unit": (
                therapy_row.get("healthcare_service_unit")
                or ""
            ),
            "category": (
                therapy_row.get("healthcare_service_unit")
                or "Other"
            ),
            "pkg_only": (
                0 if therapy_row.get("is_billable") else 1
            ),
            "show_in_billing": (
                1
                if therapy_row.get("custom_show_in_billing")
                else 0
            )
        })


    # Therapy Type → Category lookup
    category_map = {}

    for therapy in therapies:
        category_map[therapy["n"]] = therapy["category"]


    # ============================================================
    # ACTIVE THERAPY PLAN TEMPLATES
    # ============================================================

    templates = []

    template_rows = frappe.get_all(
        "Therapy Plan Template",
        filters={
            "is_active": 1
        },
        fields=[
            "name",
            "plan_name",
            "total_sessions",
            "total_amount",
            "item_code",
            "offer_price"
        ],
        order_by="plan_name asc",
        limit_page_length=0
    )

    for template_row in template_rows:
        template_lines = []

        detail_rows = frappe.get_all(
            "Therapy Plan Template Detail",
            filters={
                "parent": template_row.get("name")
            },
            fields=[
                "therapy_type",
                "no_of_sessions",
                "rate",
                "amount"
            ],
            order_by="idx asc",
            limit_page_length=0
        )

        for detail_row in detail_rows:
            therapy_type = detail_row.get("therapy_type")

            template_lines.append({
                "therapy_type": therapy_type,
                "no_of_sessions": (
                    detail_row.get("no_of_sessions") or 0
                ),
                "rate": detail_row.get("rate") or 0,
                "amount": detail_row.get("amount") or 0,
                "category": (
                    category_map.get(therapy_type, "Other")
                )
            })

        templates.append({
            "name": template_row.get("name"),
            "plan_name": (
                template_row.get("plan_name")
                or template_row.get("name")
            ),
            "total_sessions": (
                template_row.get("total_sessions") or 0
            ),
            "total_amount": (
                template_row.get("total_amount") or 0
            ),
            "offer_price": (
                template_row.get("offer_price") or 0
            ),
            "item_code": (
                template_row.get("item_code") or ""
            ),
            "lines": template_lines
        })


    # ============================================================
    # ACTIVE HEALTHCARE PRACTITIONERS
    # ============================================================

    practitioners = []

    practitioner_rows = frappe.get_all(
        "Healthcare Practitioner",
        fields=[
            "name",
            "practitioner_name",
            "branch",
            "status",
            "designation",
            "custom_available_all_branches",
            "custom_additional_branches"
        ],
        order_by="practitioner_name asc",
        limit_page_length=0
    )

    practitioner_names = [row.get("name") for row in practitioner_rows if row.get("name")]
    practitioner_branch_map = {}
    if practitioner_names:
        for branch_row in frappe.get_all(
            "Practitioner Branches",
            filters={"parent": ["in", practitioner_names]},
            fields=["parent", "branch"],
            limit_page_length=0,
        ):
            parent = branch_row.get("parent")
            branch_name = branch_row.get("branch")
            if parent and branch_name:
                practitioner_branch_map.setdefault(parent, []).append(branch_name)

    # Determine which duplicate practitioner record was used recently
    last_used_map = {}

    last_used_cutoff = frappe.utils.add_months(
        frappe.utils.today(),
        -18
    )

    last_used_rows = frappe.get_all(
        "Sales Invoice",
        filters={
            "ref_practitioner": ["is", "set"],
            "posting_date": [">=", last_used_cutoff]
        },
        fields=[
            "ref_practitioner",
            "max(posting_date) as last_used"
        ],
        group_by="ref_practitioner",
        limit_page_length=0
    )

    for last_used_row in last_used_rows:
        practitioner_id = last_used_row.get("ref_practitioner")

        if practitioner_id:
            last_used_map[practitioner_id] = str(
                last_used_row.get("last_used") or ""
            )


    for practitioner_row in practitioner_rows:
        practitioner_status = (
            practitioner_row.get("status") or "Active"
        )

        if str(practitioner_status).lower() != "active":
            continue

        practitioners.append({
            "name": practitioner_row.get("name"),
            "practitioner_name": (
                practitioner_row.get("practitioner_name")
                or practitioner_row.get("name")
            ),
            "branch": practitioner_row.get("branch") or "",
            "branches": list(dict.fromkeys(
                ([practitioner_row.get("branch")] if practitioner_row.get("branch") else [])
                + practitioner_branch_map.get(practitioner_row.get("name"), [])
            )),
            "status": practitioner_status,
            "designation": practitioner_row.get("designation") or "",
            "all_branches": (
                practitioner_row.get("custom_available_all_branches") or 0
            ),
            "additional_branches": (
                practitioner_row.get("custom_additional_branches") or ""
            ),
            "last_used": last_used_map.get(
                practitioner_row.get("name"),
                ""
            )
        })


    # ============================================================
    # ENABLED MODES OF PAYMENT
    # Only include modes having a company account
    # ============================================================

    modes = []

    mode_rows = frappe.get_all(
        "Mode of Payment",
        filters={
            "enabled": 1
        },
        fields=[
            "name",
            "type"
        ],
        order_by="name asc",
        limit_page_length=0
    )

    for mode_row in mode_rows:
        default_account = frappe.db.get_value(
            "Mode of Payment Account",
            {
                "parent": mode_row.get("name"),
                "company": COMPANY
            },
            "default_account"
        )

        if not default_account:
            continue

        account_type = frappe.db.get_value(
            "Account",
            default_account,
            "account_type"
        ) or ""

        modes.append({
            "name": mode_row.get("name"),
            "type": mode_row.get("type") or "Bank",
            "account": default_account,
            "acct_type": account_type
        })


    # ============================================================
    # DISCOUNT APPROVERS
    # IMPORTANT: Only Is Active = 1 records will be returned
    # ============================================================

    approvers = []

    approver_rows = frappe.get_all(
        "Discount Approver Master",
        filters={
            "is_active": 1
        },
        fields=[
            "user",
            "full_name",
            "approval_level",
            "designation",
            "email",
            "monthly_ceiling",
            "is_active"
        ],
        order_by="approval_level asc, full_name asc",
        limit_page_length=0
    )

    for approver_row in approver_rows:
        approver_user = approver_row.get("user")

        # Skip master rows without a linked user
        if not approver_user:
            continue

        approvers.append({
            "user": approver_user,
            "full_name": (
                approver_row.get("full_name")
                or approver_user
            ),
            "approval_level": (
                approver_row.get("approval_level")
                or "L1"
            ),
            "designation": (
                approver_row.get("designation")
                or ""
            )
        })


    # ============================================================
    # ACTIVE PRICING RULE OFFERS
    # ============================================================

    offers = []

    today = frappe.utils.today()

    pricing_rule_rows = frappe.get_all(
        "Pricing Rule",
        filters={
            "disable": 0,
            "selling": 1
        },
        fields=[
            "name",
            "title",
            "apply_on",
            "price_or_product_discount",
            "rate",
            "discount_percentage",
            "discount_amount",
            "min_qty",
            "max_qty",
            "valid_from",
            "valid_upto"
        ],
        order_by="modified desc",
        limit_page_length=0
    )

    for pricing_rule_row in pricing_rule_rows:
        valid_from = pricing_rule_row.get("valid_from")
        valid_upto = pricing_rule_row.get("valid_upto")

        # Ignore future offers
        if valid_from and str(valid_from)[:10] > today:
            continue

        # Ignore expired offers
        if valid_upto and str(valid_upto)[:10] < today:
            continue

        item_code = ""

        if pricing_rule_row.get("apply_on") == "Item Code":
            pricing_item_code = frappe.db.get_value(
                "Pricing Rule Item Code",
                {
                    "parent": pricing_rule_row.get("name")
                },
                "item_code"
            )

            item_code = pricing_item_code or ""

        offers.append({
            "name": pricing_rule_row.get("name"),
            "title": (
                pricing_rule_row.get("title")
                or pricing_rule_row.get("name")
            ),
            "apply_on": (
                pricing_rule_row.get("apply_on") or ""
            ),
            "item_code": item_code,
            "price_or_product_discount": (
                pricing_rule_row.get(
                    "price_or_product_discount"
                )
                or "Price"
            ),
            "rate": pricing_rule_row.get("rate") or 0,
            "discount_percentage": (
                pricing_rule_row.get("discount_percentage")
                or 0
            ),
            "discount_amount": (
                pricing_rule_row.get("discount_amount")
                or 0
            ),
            "min_qty": (
                pricing_rule_row.get("min_qty") or 0
            ),
            "max_qty": (
                pricing_rule_row.get("max_qty") or 0
            ),
            "valid_from": valid_from,
            "valid_upto": valid_upto
        })


    # ============================================================
    # COMPLIMENTARY SESSION ITEMS
    # ============================================================

    complimentary_items = []

    complimentary_rows = frappe.get_all(
        "Item",
        filters={
            "item_group": "Complimentary Sessions",
            "disabled": 0
        },
        fields=[
            "name",
            "item_name",
            "custom_max_qty_per_bill",
            "standard_rate"
        ],
        order_by="item_name asc",
        limit_page_length=0
    )

    for complimentary_row in complimentary_rows:
        complimentary_items.append({
            "item_code": complimentary_row.get("name"),
            "item_name": (
                complimentary_row.get("item_name")
                or complimentary_row.get("name")
            ),
            "max_qty": (
                complimentary_row.get(
                    "custom_max_qty_per_bill"
                )
                or 0
            ),
            "rate": (
                complimentary_row.get("standard_rate")
                or 0
            )
        })


    # ============================================================
    # CURRENT USER BRANCH ACCESS
    # ============================================================

    allowed_branches = []

    user_permission_rows = frappe.get_all(
        "User Permission",
        filters={
            "user": frappe.session.user,
            "allow": "Branch"
        },
        fields=[
            "for_value"
        ],
        limit_page_length=0
    )

    for permission_row in user_permission_rows:
        allowed_branch = permission_row.get("for_value")

        if (
            allowed_branch
            and allowed_branch not in allowed_branches
            and allowed_branch not in (
                "Head Office",
                "Testing Branch"
            )
        ):
            allowed_branches.append(allowed_branch)


    # Get logged-in user's Employee branch
    user_branch = ""

    employee = frappe.db.get_value(
        "Employee",
        {
            "user_id": frappe.session.user,
            "status": "Active"
        },
        [
            "branch"
        ],
        as_dict=True
    )

    if employee and employee.get("branch"):
        user_branch = employee.get("branch")


    # If there is exactly one allowed branch, use it as default
    if not user_branch and len(allowed_branches) == 1:
        user_branch = allowed_branches[0]


    # User with no Branch User Permission is treated as Head Office
    is_head_office = 1

    if allowed_branches:
        is_head_office = 0


    # ============================================================
    # DISCOUNT APPROVAL REQUESTS
    # Return complete L1 / L2 / L3 / L4 chain for one invoice
    # ============================================================

    discount_requests = []

    invoice_name = str(
        frappe.form_dict.get("invoice_name")
        or ""
    ).strip()

    if invoice_name:

        invoice_exists = frappe.db.exists(
            "Sales Invoice",
            invoice_name
        )

        if invoice_exists:

            discount_requests = frappe.get_all(
                "Discount Approval Request",
                filters={
                    "linked_invoice": invoice_name
                },
                fields=[
                    "name",
                    "linked_invoice",
                    "selected_approver",
                    "requested_by",
                    "bill_total",
                    "requested_discount_pct",
                    "requested_final_amount",
                    "approval_level",
                    "status",
                    "approved_discount_pct",
                    "approved_final_amount",
                    "approved_by",
                    "approved_at",
                    "rejection_reason",
                    "reason",
                    "branch",
                    "creation",
                    "modified"
                ],
                order_by="creation asc",
                limit_page_length=0
            )

    # ============================================================
    # FINAL RESPONSE
    # ============================================================

    latest_invoice_print_format = "Consultaion Patient Sales Invoice"
    try:
        latest_print_formats = frappe.get_all(
            "Print Format",
            filters={"doc_type": "Sales Invoice", "print_format_for": "DocType", "disabled": 0},
            fields=["name"],
            order_by="creation desc, name desc",
            limit_page_length=1
        )
        if latest_print_formats:
            latest_invoice_print_format = latest_print_formats[0].get("name") or latest_invoice_print_format
    except Exception:
        pass

    frappe.response["message"] = {
        "user": frappe.session.user,
        "user_branch": user_branch,
        "allowed_branches": allowed_branches,
        "is_head_office": is_head_office,
        "branches": branches,
        "therapies": therapies,
        "templates": templates,
        "practitioners": practitioners,
        "modes": modes,
        "approvers": approvers,
        "offers": offers,
        "comp_items": complimentary_items,
        "discount_requests": discount_requests,
        "latest_invoice_print_format": latest_invoice_print_format
    }
