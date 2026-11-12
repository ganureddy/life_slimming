"""Metadata-safe campaign fields for the report's already-authorized Lead cohort."""
import re
import frappe


def read_campaign_details(rows):
    names = sorted({row.get('campaign_name') for row in rows if row.get('campaign_name')})
    if not names or not frappe.db.exists('DocType', 'Campaign'):
        return {}
    meta = frappe.get_meta('Campaign')
    def pick(preferred, pattern, types=None):
        if preferred and meta.has_field(preferred):
            return preferred
        return next((field.fieldname for field in meta.fields
            if re.search(pattern, (field.fieldname or '')+' '+(field.label or ''), re.I)
            and (not types or field.fieldtype in types)), '')
    mapping = {
        'title': pick('campaign_name', r'title|campaign name'),
        'from_date': pick('start_date', r'start.*date'),
        'to_date': pick('end_date', r'end.*date'),
        'status': pick('status', r'status'),
        'agency': pick('', r'agency|vendor|marketing partner'),
        'category': pick('', r'category|treatment'),
        'platform': pick('', r'platform|media channel|ad channel'),
        'spend': pick('', r'ad.*spend|spent.*amount|spend.*amount|media.*cost|campaign.*cost', ['Currency', 'Float', 'Int']),
    }
    fields = ['name', *sorted({field for field in mapping.values() if field})]
    output = {}
    try:
        for start in range(0, len(names), 400):
            for row in frappe.get_list('Campaign', filters={'name': ['in', names[start:start+400]]}, fields=fields, limit_page_length=400):
                output[row.name] = {'name': row.name, **{key: row.get(field) for key,field in mapping.items() if field}}
    except frappe.PermissionError:
        # Legacy get_list also omits campaigns this login is not allowed to read.
        return {}
    return output
