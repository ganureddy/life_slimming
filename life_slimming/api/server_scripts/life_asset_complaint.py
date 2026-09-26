"""Asset Master Complaint  Resolver Mail

Original API: life_asset_complaint
Source modified: 2026-08-12 15:53:39.623399
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
    # ERPNext Server Script
    # Script Type: API
    # API Method: life_asset_complaint
    # Allow Guest: No
    #
    # One permission-aware endpoint for the dashboard complaint form.
    # - action=directory returns active System Users and only A K Shrikant as resolver.
    # - action=create creates the Issue with the logged-in user's normal Create permission,
    #   assigns A K Shrikant, and emails the resolver plus every selected CC user.
    # No ignore_permissions flag is used.

    user = frappe.session.user
    action = frappe.form_dict.get("action") or "directory"

    if not user or user == "Guest":
        frappe.response["message"] = {"ok": False, "message": "Please log in to use Asset Complaints."}
    else:
        system_users = frappe.get_all(
            "User",
            filters={"enabled": 1, "user_type": "System User"},
            fields=["name", "full_name"],
            order_by="full_name asc",
            limit_page_length=2000
        )

        resolver = None
        for system_user in system_users:
            resolver_text = ((system_user.get("full_name") or "") + " " + (system_user.get("name") or "")).lower()
            resolver_key = resolver_text.replace(".", " ").replace("-", " ").replace("_", " ")
            while "  " in resolver_key:
                resolver_key = resolver_key.replace("  ", " ")
            if "a k shrikant" in resolver_key.strip() or "a k srikanth" in resolver_key.strip():
                resolver = system_user
                break

        if action == "directory":
            frappe.response["message"] = {
                "ok": True,
                "resolver": resolver,
                "users": system_users
            }
        elif action == "create":
            branch = (frappe.form_dict.get("branch") or "").strip()
            category = (frappe.form_dict.get("category") or "").strip()
            specific_issue = (frappe.form_dict.get("specific_issue") or "").strip()
            priority = (frappe.form_dict.get("priority") or "Medium").strip()
            details = (frappe.form_dict.get("details") or "").strip()
            asset = (frappe.form_dict.get("asset") or "").strip()
            requested_resolver = (frappe.form_dict.get("resolver") or "").strip()
            cc_text = (frappe.form_dict.get("cc_to") or "").strip()

            cc_users = []
            for cc_value in cc_text.split(","):
                cc_email = cc_value.strip()
                if cc_email and cc_email not in cc_users:
                    cc_users.append(cc_email)

            active_user_ids = []
            for system_user in system_users:
                if system_user.get("name"):
                    active_user_ids.append(system_user.get("name"))

            if not resolver:
                frappe.response["message"] = {
                    "ok": False,
                    "message": "Active System User A K Srikanth was not found. Confirm that the User is enabled and its Full Name is A K Srikanth."
                }
            elif requested_resolver and requested_resolver != resolver.get("name"):
                frappe.response["message"] = {"ok": False, "message": "Only A K Srikanth can be selected as resolver."}
            elif not branch or not category or not specific_issue or not details or not asset:
                frappe.response["message"] = {
                    "ok": False,
                    "message": "Branch, category, specific issue, Asset and issue details are required."
                }
            else:
                valid_cc_users = []
                for cc_email in cc_users:
                    if cc_email in active_user_ids and cc_email != resolver.get("name"):
                        valid_cc_users.append(cc_email)

                readable = (
                    "Branch: " + branch + "\n"
                    "Category: " + category + "\n"
                    "Issue: " + specific_issue + "\n"
                    "Asset: " + asset + "\n"
                    "Tag To: " + resolver.get("name") + "\n"
                    "CC To: " + ", ".join(valid_cc_users) + "\n"
                    "Details: " + details
                )
                issue = frappe.get_doc({
                    "doctype": "Issue",
                    "naming_series": "ISS-.YYYY.-",
                    "subject": specific_issue,
                    "raised_by": user,
                    "status": "Open",
                    "priority": priority,
                    "email_cc": ", ".join(valid_cc_users),
                    "description": readable
                })

                # Normal insert enforces the logged-in user's Create permission.
                issue.insert()

                # Store the selected resolver in the standard assignment column.
                resolver_id = resolver.get("name").replace("\\", "\\\\").replace('"', '\\"')
                issue.db_set("_assign", '["' + resolver_id + '"]', update_modified=False)

                recipients = [resolver.get("name")]
                for cc_email in valid_cc_users:
                    if cc_email not in recipients:
                        recipients.append(cc_email)

                dashboard_link = frappe.utils.get_url("/asset-master?open=complaints&issue=" + issue.name)
                frappe.sendmail(
                    recipients=recipients,
                    subject="Asset Complaint Raised · " + issue.name + " · " + specific_issue,
                    message=(
                        "<p>A LIFE Asset Complaint has been raised.</p>"
                        "<p><b>Complaint:</b> " + issue.name + "<br>"
                        "<b>Branch:</b> " + branch + "<br>"
                        "<b>Category:</b> " + category + "<br>"
                        "<b>Asset:</b> " + asset + "<br>"
                        "<b>Priority:</b> " + priority + "</p>"
                        "<p>" + details + "</p>"
                        "<p><a href='" + dashboard_link + "' style='background:#1e5b35;color:#fff;padding:10px 16px;text-decoration:none;border-radius:5px'>Open Complaints Dashboard</a></p>"
                    ),
                    reference_doctype="Issue",
                    reference_name=issue.name,
                    now=True
                )

                frappe.response["message"] = {
                    "ok": True,
                    "doc": {"name": issue.name, "status": issue.status},
                    "resolver": resolver.get("name"),
                    "emailed_to": recipients
                }
        else:
            frappe.response["message"] = {"ok": False, "message": "Unsupported complaint action."}
