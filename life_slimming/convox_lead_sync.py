"""Link ConVox events and synchronize explicit dispositions to portal leads."""
import hashlib

import frappe


def reference_key(agent, reference):
    return "convox-lead:" + hashlib.sha256(f"{agent}:{reference}".encode()).hexdigest()


def resolve_lead(event):
    from life_slimming.api.convox import normalize_phone

    try:
        number = normalize_phone(event.get("mobile_number"))
    except frappe.ValidationError:
        return None
    users = frappe.get_all("User", filters={"enabled": 1, "custom_convox_enabled": 1,
        "custom_convox_agent_id": event.get("agent_id")}, pluck="name", limit_page_length=2)
    if len(users) != 1:
        return None
    # Vendor lead_id belongs to the dialler; never treat it as a trusted CRM ID.
    # Exact phone + owner matching also prevents ambiguous numbers changing a lead.
    rows = frappe.db.sql("""SELECT name FROM `tabLead` WHERE lead_owner = %(owner)s AND
        (REGEXP_REPLACE(COALESCE(mobile_no, ''), '[[:space:]()+.-]', '') IN %(numbers)s
         OR REGEXP_REPLACE(COALESCE(phone, ''), '[[:space:]()+.-]', '') IN %(numbers)s)
        LIMIT 2""", {"owner": users[0], "numbers": (number, "91" + number, "0" + number)}, as_dict=True)
    mapped = frappe.cache.get_value(reference_key(event.get("agent_id"), event.get("call_reference")))
    if mapped:
        # Reference was recorded by the authorized click-to-call endpoint. Still
        # verify the number before linking, including manager-initiated calls.
        lead = frappe.db.get_value("Lead", mapped, ["mobile_no", "phone"], as_dict=True)
        if lead:
            for value in (lead.mobile_no, lead.phone):
                try:
                    if normalize_phone(value) == number:
                        return mapped
                except frappe.ValidationError:
                    pass
    if len(rows) == 1:
        return rows[0].name
    if rows:
        return None
    # Global caller lookup also supports calls to another agent's lead, but
    # never chooses arbitrarily when the same phone belongs to several leads.
    rows = frappe.db.sql("""SELECT name FROM `tabLead` WHERE
        REGEXP_REPLACE(COALESCE(mobile_no, ''), '[[:space:]()+.-]', '') IN %(numbers)s
        OR REGEXP_REPLACE(COALESCE(phone, ''), '[[:space:]()+.-]', '') IN %(numbers)s
        LIMIT 2""", {"numbers": (number, "91" + number, "0" + number)}, as_dict=True)
    return rows[0].name if len(rows) == 1 else None


SUMMARY_FIELDS = {
    "custom_convox_last_event": "name",
    "custom_convox_call_reference": "call_reference",
    "custom_convox_call_status": "call_status",
    "custom_convox_disposition": "disposition",
    "custom_convox_disposition_2": "disposition_2",
    "custom_convox_disposition_3": "disposition_3",
    "custom_convox_last_call_time": "call_datetime",
    "custom_convox_call_duration": "call_duration",
    "custom_convox_recording": "recording_file_name",
    "custom_convox_remarks": "remarks",
}


def disposition_values(event, meta):
    """Map vendor labels only to installed Lead select options."""
    import re
    from html import unescape

    def key(value):
        return re.sub(r"[^a-z0-9]", "", unescape(str(value or "")).lower())

    groups = {
        "FOLLOW-UP": {
            "No Response": "Not Response", "Not Reachable": "Not Reachable",
            "Switch OFF": "Switch OFF", "Call Disconnected": "Call Disconnected",
            "Callback: Scheduled": "Call Back", "Price Negotiation": "Followup",
            "Get Back": "Get Back", "Very Positive": "Interested",
            "Call & Confirm": "Followup", "Out Station": "Followup",
            "Walked In: Not Booked": "Consultation Done",
            "Appointment no response": "Appointment no response",
        },
        "SUCCESS": {"Appointment Booked": "Appointment Booked",
                    "Existing Client": "Existing client", "Walked In & Booked": "Converted"},
        "LOST": {"Not interested": "Not interested", "Other clinic": "Other clinic",
                 "Joined Competition": "Not interested", "Do Not Contact": "Do Not Contact"},
        "INVALID": {"Invalid Number": "Wrong number", "Wrong number": "Wrong number",
                    "Not in Service": "Not in Service", "Job enquiry": "Job enquiry",
                    "Franchise Lead": "Franchise Lead", "Junk/Wrong Call": "Not Enquired",
                    "Not Enquired": "Not Enquired", "TNA": "TNA", "NID": "NID"},
    }
    mapping = {key(sub): (stage, sub, status) for stage, entries in groups.items()
               for sub, status in entries.items()}
    aliases = {"NR": "No Response", "No Answer": "No Response",
               "CNA--Ringing/No Answer": "No Response", "CNA--NO Answer": "No Response",
               "Callback": "Callback: Scheduled", "Call Back": "Callback: Scheduled",
               "DNC": "Do Not Contact"}
    for alias, target in aliases.items():
        mapping[key(alias)] = mapping[key(target)]
    for field in ("disposition_3", "disposition_2", "disposition"):
        match = mapping.get(key(event.get(field)))
        if not match:
            continue
        stage, sub, status = match
        result = {}
        for fieldname, value in (("custom_cc_stage", stage), ("custom_cc_sub_status", sub), ("status", status)):
            field = meta.get_field(fieldname)
            options = {key(option): option.strip() for option in (field.options or "").splitlines() if option.strip()} if field else {}
            if key(value) not in options:
                break
            result[fieldname] = options[key(value)]
        else:
            return result
    return {}


def sync_disposition(event, lead, meta):
    values = disposition_values(event, meta)
    if not values:
        return
    fields = list(values) + ["custom_appointment_status", "custom_convox_last_event",
                            "custom_convox_disposition", "custom_convox_disposition_2", "custom_convox_disposition_3"]
    current = frappe.db.get_value("Lead", lead, fields, as_dict=True)
    if not current:
        return
    # A repeated callback (e.g. recording delivery) must not undo a later manual edit.
    if current.get("custom_convox_last_event") == event.get("name") and all(
        (current.get("custom_convox_" + field) or "") == (event.get(field) or "")
        for field in ("disposition", "disposition_2", "disposition_3")
    ):
        return
    protected = current.get("custom_appointment_status") == "Visited Booked" or current.get("custom_cc_sub_status") in {
        "Walked In & Booked", "Do Not Contact", "Existing Client", "Not interested", "Invalid Number",
        "Wrong number", "Not in Service", "Other clinic", "Joined Competition", "Job enquiry",
        "Franchise Lead", "Junk/Wrong Call", "Not Enquired", "TNA", "NID"}
    if protected:
        users = frappe.get_all("User", filters={"enabled": 1, "custom_convox_enabled": 1,
            "custom_convox_agent_id": event.get("agent_id")}, pluck="name", limit_page_length=2)
        if len(users) != 1 or "Call Center Export" not in frappe.get_roles(users[0]):
            return
    if any(current.get(field) != value for field, value in values.items()):
        # Status edits invalidate stale portal forms, unlike telephony-only summaries.
        frappe.db.set_value("Lead", lead, values)


def sync_event(doc, method=None):
    """Runs in the same transaction as the event; retries never increment counts."""
    if not frappe.get_meta("ConVox Call Event").has_field("crm_lead"):
        return  # Install fields through migrate/setup before enabling summaries.
    lead = resolve_lead(doc)
    if not lead:
        return
    # A database row lock serializes callbacks even across different call refs.
    frappe.db.sql("SELECT name FROM `tabLead` WHERE name=%s FOR UPDATE", lead)
    doc.db_set("crm_lead", lead, update_modified=False)
    rows = frappe.db.sql("""SELECT name, call_reference, call_status, disposition,
        disposition_2, disposition_3, call_datetime, call_duration, recording_file_name, remarks
        FROM `tabConVox Call Event` WHERE crm_lead=%s AND event_type='Call Status'
        ORDER BY call_datetime DESC, received_on DESC, name DESC LIMIT 1""", lead, as_dict=True)
    if not rows:
        return
    meta = frappe.get_meta("Lead")
    if rows[0].get("name") == doc.get("name"):
        sync_disposition(doc, lead, meta)
    values = {field: rows[0].get(source) for field, source in SUMMARY_FIELDS.items() if meta.has_field(field)}
    if meta.has_field("custom_convox_call_count"):
        count = frappe.db.sql("""SELECT COUNT(DISTINCT COALESCE(NULLIF(call_reference, ''), name))
            FROM `tabConVox Call Event` WHERE crm_lead=%s AND event_type='Call Status'""", lead)[0][0]
        values["custom_convox_call_count"] = count
    if values:
        # Telephony summaries must not invalidate an in-progress counsellor form.
        frappe.db.set_value("Lead", lead, values, update_modified=False)


def install_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    if not frappe.db.exists("DocType", "ConVox Call Event"):
        return
    fields = [dict(fieldname="custom_convox_summary", label="Latest ConVox call", fieldtype="Section Break")]
    kinds = {"custom_convox_last_event": ("Link", "ConVox Call Event"),
             "custom_convox_last_call_time": ("Data", None),
             "custom_convox_call_duration": ("Data", None),
             "custom_convox_recording": ("Small Text", None),
             "custom_convox_remarks": ("Small Text", None)}
    for name in SUMMARY_FIELDS:
        kind, options = kinds.get(name, ("Data", None))
        fields.append(dict(fieldname=name, label=name.removeprefix("custom_convox_").replace("_", " ").title(),
                           fieldtype=kind, options=options, read_only=1, no_copy=1))
    fields.append(dict(fieldname="custom_convox_call_count", label="ConVox completed call events", fieldtype="Int", read_only=1, no_copy=1))
    create_custom_fields({"Lead": fields, "ConVox Call Event": [dict(fieldname="crm_lead", label="CRM Lead",
        fieldtype="Link", options="Lead", read_only=1, no_copy=1, in_list_view=1)]}, update=True)
