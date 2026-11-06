"""Indexes for portal Lead reads; run after schema sync, never during requests."""
import frappe

# Put owner first for agent-scoped date cohorts; standalone dates serve managers.
INDEXES = {
    'Lead': [
        ('lead_owner', 'creation'),
        ('lead_owner', 'custom_appointment_date_and_time'),
        ('lead_owner', 'custom_next_followup_date'),
        ('custom_appointment_date_and_time',),
        ('custom_next_followup_date',),
        ('custom_cc_sub_status',),
    ],
    'ConVox Call Event': [
        ('agent_id', 'received_on', 'name'),
        ('received_on',),
        ('crm_lead', 'event_type', 'call_datetime'),
    ],
    'Version': [('ref_doctype', 'docname', 'creation')],
}


def execute():
    """Add missing indexes, allowing sites without optional custom fields."""
    added = []
    for doctype, definitions in INDEXES.items():
        if not frappe.db.table_exists(doctype):
            continue
        columns = set(frappe.db.get_table_columns(doctype))
        # Identifiers come only from the fixed table list above.
        existing = {}
        for row in frappe.db.sql(f'SHOW INDEX FROM `tab{doctype}`', as_dict=True):
            existing.setdefault(row.Key_name, {})[int(row.Seq_in_index)] = (
                row.Column_name if not row.Sub_part else None)
        covered = [tuple(parts[index] for index in sorted(parts)) for parts in existing.values()]
        for fields in definitions:
            if not set(fields).issubset(columns):
                continue
            if any(index[:len(fields)] == fields for index in covered):
                continue
            name = 'life_' + '_'.join(fields) + '_idx'
            # Stay within MariaDB's 64-character identifier limit.
            if len(name) > 64:
                import hashlib
                name = name[:51] + '_' + hashlib.sha256(name.encode()).hexdigest()[:12]
            frappe.db.add_index(doctype, list(fields), index_name=name)
            covered.append(fields)
            added.append((doctype, fields))
    return added
