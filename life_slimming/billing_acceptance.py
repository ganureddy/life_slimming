"""Read-only checks for native Billing against the configured Frappe site."""

import secrets

import frappe


def audit():
    from life_slimming.api.server_scripts.lifescc_billing_collections_report import run

    original_user = frappe.session.user
    original_response = frappe.local.response
    original_form = frappe.local.form_dict
    result = {"billed_match": False, "collections_match": False, "outstanding_match": False, "restricted_branch_check": "no eligible user", "unauthorized_branch_denied": "no eligible user"}
    try:
        # The report and independent ledger sums must agree for the same period.
        frappe.set_user("Administrator")
        frappe.local.response = frappe._dict()
        run(from_date="2026-09-06", to_date="2026-10-05", branch="")
        rows = frappe.local.response.get("message", {}).get("rows", [])
        actual = sum(float(row.get("billed_total") or 0) for row in rows)
        expected = frappe.db.sql(
            "SELECT COALESCE(SUM(base_grand_total),0) FROM `tabSales Invoice` "
            "WHERE docstatus=1 AND posting_date BETWEEN %s AND %s",
            ("2026-09-06", "2026-10-05"),
        )[0][0]
        result["billed_match"] = abs(actual - float(expected or 0)) < 0.01
        collected = sum(float(row.get("collected_total") or 0) for row in rows)
        expected_collected = frappe.db.sql(
            "SELECT COALESCE(SUM(per.allocated_amount),0) "
            "FROM `tabPayment Entry` pe JOIN `tabPayment Entry Reference` per "
            "ON per.parent=pe.name AND per.reference_doctype='Sales Invoice' "
            "JOIN `tabSales Invoice` si ON si.name=per.reference_name "
            "WHERE pe.docstatus=1 AND pe.payment_type='Receive' "
            "AND pe.posting_date BETWEEN %s AND %s",
            ("2026-09-06", "2026-10-05"),
        )[0][0]
        result["collections_match"] = abs(collected - float(expected_collected or 0)) < 0.01
        outstanding = sum(float(row.get("outstanding") or 0) for row in rows)
        expected_outstanding = frappe.db.sql(
            "SELECT COALESCE(SUM(outstanding_amount),0) FROM `tabSales Invoice` "
            "WHERE docstatus=1 AND posting_date BETWEEN %s AND %s",
            ("2026-09-06", "2026-10-05"),
        )[0][0]
        result["outstanding_match"] = abs(outstanding - float(expected_outstanding or 0)) < 0.01
        result["branch_rows"] = len(rows)

        permissions = frappe.get_all(
            "User Permission", filters={"allow": "Branch"},
            fields=["user", "for_value"], limit_page_length=0,
        )
        users = {}
        for permission in permissions:
            if permission.user and permission.for_value not in ("Head Office", "Testing Branch"):
                users.setdefault(permission.user, set()).add(permission.for_value)
        for user, allowed in users.items():
            if user == "Administrator" or not frappe.db.get_value("User", user, "enabled"):
                continue
            frappe.set_user(user)
            frappe.local.response = frappe._dict()
            run(from_date="2026-09-06", to_date="2026-10-05", branch="")
            user_rows = frappe.local.response.get("message", {}).get("rows", [])
            result["restricted_branch_check"] = all(
                row.get("branch") in allowed for row in user_rows
            )
            result["restricted_rows"] = len(user_rows)
            other_branch = next((row["branch"] for row in rows if row.get("branch") not in allowed), None)
            if other_branch:
                try:
                    run(from_date="2026-09-06", to_date="2026-10-05", branch=other_branch)
                    result["unauthorized_branch_denied"] = False
                except frappe.PermissionError:
                    result["unauthorized_branch_denied"] = True
            break
        return result
    finally:
        frappe.set_user(original_user)
        frappe.local.response = original_response
        frappe.local.form_dict = original_form


def otp_guard():
    """Confirm an unverified synthetic number is rejected before any insert."""
    from life_slimming.api.server_scripts.lifescc_billing_create_client import run

    original_response = frappe.local.response
    original_form = frappe.local.form_dict
    mobile = "9" + "".join(secrets.choice("0123456789") for _ in range(9))
    try:
        frappe.local.response = frappe._dict()
        run(
            patient_name="Acceptance Check", mobile=mobile, sex="Other",
            branch="Acceptance Check", consultation_employee="Acceptance Check",
            visited_for="Slimming", final_decision="Not-Booked",
            treatment_category="Slimming/Cryo", pd_form_number="Acceptance Check",
            pd_form_file="/private/files/acceptance-check.pdf",
        )
        return {"unverified_registration_denied": frappe.local.response.get("message", {}).get("error") == "Verify this mobile number before registering."}
    finally:
        frappe.local.response = original_response
        frappe.local.form_dict = original_form
