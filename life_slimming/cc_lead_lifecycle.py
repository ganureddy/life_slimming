"""Website chat intake and untouched-lead rotation."""
import frappe
from frappe.utils import now_datetime, get_datetime, add_days, cint


def contacted(doc):
    return bool(doc.get('custom_cc_first_touched_at') or doc.get('custom_last_call_time')
                or cint(doc.get('custom_call_count')) or doc.get('custom_convox_last_call_time')
                or cint(doc.get('custom_convox_call_count')))


def before_save(doc, method=None):
    old = doc.get_doc_before_save()
    has_tracking = doc.meta.has_field('custom_cc_rotation_at')
    if has_tracking and (not old or old.get('lead_owner') != doc.get('lead_owner')):
        doc.custom_cc_rotation_at = now_datetime()
    if has_tracking and old and any(doc.get(field) != old.get(field) for field in
                   ('custom_last_call_time', 'custom_call_count', 'custom_cc_sub_status')):
        doc.custom_cc_chat_returned = 0
    marker = '[NEW WEBSITE CHAT ENQUIRY '
    chat_changed = bool(doc.get('custom_chat_script')) and (not old or old.get('custom_chat_script') != doc.get('custom_chat_script'))
    repeat_received = str(doc.get('custom_remarks') or '').count(marker) > str(old.get('custom_remarks') or '' if old else '').count(marker)
    if not chat_changed and not repeat_received:
        return
    previous_stage = (old.get('custom_cc_stage') if old else None) or doc.get('custom_cc_stage')
    previous_status = str((old or doc).get('status') or '').strip().lower()
    appointment = str((old or doc).get('custom_appointment_status') or '').strip().lower()
    protected = previous_stage in ('FOLLOW-UP', 'SUCCESS', 'LOST', 'INVALID') or previous_status in {
        'followup', 'appointment booked', 'converted', 'do not contact', 'existing client', 'dnd'
    } or appointment in ('booked', 'visited booked')
    if protected and old:
        doc.lead_owner = old.get('lead_owner')
        doc.custom_cc_stage = previous_stage
        if has_tracking:
            doc.custom_cc_rotation_at = old.get('custom_cc_rotation_at')
            doc.custom_cc_chat_returned = int(previous_stage == 'FOLLOW-UP' or previous_status == 'followup')
        return
    if doc.get('custom_cc_stage') in ('SUCCESS', 'LOST', 'INVALID') or doc.get('custom_cc_sub_status') == 'Do Not Contact':
        return
    if doc.get('custom_cc_stage') == 'FOLLOW-UP':
        if has_tracking:
            doc.custom_cc_chat_returned = 1
    elif not contacted(doc):
        doc.custom_cc_stage = 'UNTOUCHED'
        doc.custom_cc_sub_status = ''
        doc.status = 'Lead'


def rotate_untouched():
    """Rotate after 15 days per owner; never use modified as a timer."""
    if not frappe.get_meta('Lead').has_field('custom_cc_rotation_at'):
        return
    if not frappe.db.exists('DocType', 'Lead Assignment Settings'):
        return
    settings = frappe.get_single('Lead Assignment Settings')
    configs = settings.get('agent_config') or []
    cutoff = add_days(now_datetime(), -15)
    names = frappe.get_all('Lead', filters={'custom_cc_stage': 'UNTOUCHED'}, pluck='name')
    for name in names:
        frappe.db.sql('SELECT name FROM `tabLead` WHERE name=%s FOR UPDATE', name)
        doc = frappe.get_doc('Lead', name)
        if not doc.get('custom_chat_script') or contacted(doc) or doc.get('custom_cc_stage') != 'UNTOUCHED':
            continue
        if get_datetime(doc.get('custom_cc_rotation_at') or doc.creation) > get_datetime(cutoff):
            continue
        eligible = []
        for config in configs:
            agent = config.get('agent')
            sources = [s.strip().lower() for s in (config.get('custom_lead_sources') or '').split(',') if s.strip()]
            if not agent or agent == doc.lead_owner or not cint(config.get('custom_auto_assign_enabled')) or cint(config.get('custom_temporarily_stopped')):
                continue
            if sources and (doc.get('source') or '').lower() not in sources:
                continue
            if cint(settings.get('custom_require_source_mapping')) and not sources:
                continue
            if not frappe.db.get_value('User', agent, 'enabled') or not frappe.db.exists('Employee', {'user_id': agent, 'status': 'Active', 'designation': 'Business Executive'}):
                continue
            if cint(settings.get('custom_require_open_checkin')):
                emp = frappe.db.get_value('Employee', {'user_id': agent, 'status': 'Active'}, 'name')
                last = frappe.get_all('Employee Checkin', filters={'employee': emp}, fields=['log_type'], order_by='time desc', limit_page_length=1)
                if not last or last[0].log_type != 'IN':
                    continue
            count = frappe.db.count('Lead', {'lead_owner': agent, 'custom_cc_rotation_at': ['>=', str(now_datetime().date())]})
            if cint(config.get('max_per_day')) and count >= cint(config.get('max_per_day')):
                continue
            eligible.append((count, agent))
        if eligible:
            previous = doc.lead_owner
            doc.lead_owner = min(eligible)[1]
            doc.custom_cc_rotation_at = now_datetime()
            doc.save(ignore_permissions=True)
            doc.add_comment('Info', f'Automatically reassigned after 15 untouched days: {previous} → {doc.lead_owner}')


def install_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({'Lead': [
        dict(fieldname='custom_cc_rotation_at', label='CC last assigned at', fieldtype='Datetime', read_only=1, no_copy=1),
        dict(fieldname='custom_cc_chat_returned', label='New Lead to the Same Agent', fieldtype='Check', read_only=1, no_copy=1),
    ]}, update=True)
