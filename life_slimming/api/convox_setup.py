"""Idempotent schema setup. No credentials, agent mappings or live calls are created."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def install():
    if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
        raise frappe.PermissionError
    def field(name, label, kind="Data", **extra):
        return dict(fieldname="custom_convox_" + name, label=label, fieldtype=kind, **extra)
    system = [
        field("section", "ConVox integration", "Section Break"),
        field("integration_enabled", "Enable ConVox", "Check", default="0"),
        field("widget_url", "ConVox widget URL", default="https://lifeslimming.deepijatel.in/ConVoxCCS/ExternalIndex"),
        field("api_url", "ConVox click-to-call URL", default="https://lifeslimming.deepijatel.in/ConVoxCCS/rest/api"),
        field("access_token", "ConVox access token", "Password"),
        field("auto_token_enabled", "Retrieve calling token automatically", "Check", default="0"),
        field("token_key", "ConVox token-generation key", "Password",
              description="Vendor PROD_ key used only with /ConVoxCCS/rest/secureToken. Never enter the callback token here."),
        field("default_dial_prefix", "ConVox default dial prefix"),
        field("sso_section", "ConVox encrypted SSO", "Section Break"),
        field("sso_enabled", "Enable ConVox SSO", "Check", default="0"),
        field("sso_secret", "ConVox deployment SSO secret", "Password"),
        field("sso_iv", "ConVox SSO IV", description="Vendor-provided IV; confirm its representation before enabling SSO."),
        field("sso_iv_mode", "Confirmed IV interpretation", "Select", options="\nbase64\nphp_literal_prefix"),
        field("callback_section", "ConVox call callbacks", "Section Break"),
        field("callbacks_enabled", "Enable ConVox callbacks", "Check", default="0"),
        field("callback_user", "ConVox OAuth service user", "Link", options="User",
              description="Restrict Bearer-authenticated callbacks to this dedicated service user."),
        field("callback_token", "Optional X-ConVox-Token", "Password",
              description="Alternative shared-header authentication; do not put this in the Authorization header."),
    ]
    users = [field("section", "ConVox agent mapping", "Section Break"),
        field("enabled", "Enable ConVox for this user", "Check", default="0"),
        field("agent_id", "ConVox agent ID"), field("sso_username", "ConVox mapped SSO email or username"),
        field("dial_prefix", "ConVox dial prefix override"), field("station", "ConVox station")]
    # Agent mappings must be administrator-managed, not editable through My Settings.
    for item in users:
        item["permlevel"] = 1
    create_custom_fields({"System Settings": system, "User": users}, update=True)
    fields = []
    def event_field(name, kind="Data", **extra):
        fields.append(dict(fieldname=name, label=name.replace("_", " ").title(), fieldtype=kind, **extra))
    event_field("event_type", "Select", options="Call Popup\nCall Status", reqd=1)
    for name in ["call_reference", "agent_id", "process_name", "mobile_number", "lead_id", "call_type",
                 "station", "disposition", "disposition_2", "disposition_3", "call_status", "call_mode",
                 "completed_by", "queue_name", "list_id", "did"]:
        event_field(name)
    for name in ["call_datetime", "received_on", "followup_time"]:
        event_field(name, "Datetime")
    for name in ["call_duration", "queue_duration", "ring_duration"]:
        event_field(name, "Int")
    event_field("recording_file_name", "Small Text")
    event_field("remarks", "Small Text")
    event_field("payload_json", "Long Text", hidden=1)
    if not frappe.db.exists("DocType", "ConVox Call Event"):
        frappe.get_doc(dict(doctype="DocType", name="ConVox Call Event", module="life_slimming", custom=1,
            autoname="hash", fields=fields, track_changes=0,
            permissions=[dict(role="System Manager", read=1, report=1, export=1)])).insert(ignore_permissions=True)
    else:
        # Preserve existing schema and records; add missing fields only.
        doc = frappe.get_doc("DocType", "ConVox Call Event")
        names = {f.fieldname for f in doc.fields}
        for item in fields:
            if item["fieldname"] not in names:
                doc.append("fields", item)
        doc.save(ignore_permissions=True)
    frappe.clear_cache()
    return {"installed": True, "message": "Configure System Settings and User agent mappings before enabling ConVox."}
