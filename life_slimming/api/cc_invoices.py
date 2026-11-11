"""Read-only invoice search for the call-centre workspace."""
import re

import frappe
from frappe.utils import getdate, add_days
from life_slimming.portal_access import require_module

PAGE_SIZE = 40
STATUSES = ('Draft', 'Paid', 'Partly Paid', 'Unpaid', 'Overdue', 'Cancelled', 'Return', 'Credit Note Issued')


def _schema():
    metas = {key: frappe.get_meta(dt) for key, dt in (
        ('i', 'Sales Invoice'), ('p', 'Patient'), ('t', 'Therapy Plan'),
        ('l', 'Lead'), ('c', 'Customer'))}

    def col(alias, field):
        return f'{alias}.`{field}`' if metas[alias].has_field(field) or field == 'name' else "''"

    def first(*values):
        return 'COALESCE(' + ','.join(f"NULLIF(TRIM({value}), '')" for value in values) + ", '')"

    joins = ' FROM `tabSales Invoice` i'
    joins += ' LEFT JOIN `tabPatient` p ON p.name = ' + col('i', 'patient')
    joins += ' LEFT JOIN `tabCustomer` c ON c.name = ' + col('i', 'customer')
    joins += ' LEFT JOIN `tabTherapy Plan` t ON t.name = ' + first(col('i', 'therapy_plan_reference_id'), col('i', 'custom_therapy_plan'))
    joins += ' LEFT JOIN `tabLead` l ON l.name = ' + col('p', 'custom_lead')
    invoice_source, plan_source, client_source, lead_source = (
        col('i', 'source'), col('t', 'media'), col('p', 'custom_media'), col('l', 'source'))
    source = first(invoice_source, plan_source, client_source, lead_source)
    mobiles = [col('p', 'mobile'), col('i', 'contact_mobile'), col('c', 'mobile_no')]
    mobile = first(*mobiles)
    provenance = 'CASE ' + ' '.join(
        f"WHEN COALESCE(TRIM({value}), '') != '' THEN '{label}'"
        for value, label in ((invoice_source, 'Invoice'), (plan_source, 'Therapy plan'),
                             (client_source, 'Client profile'), (lead_source, 'Original lead'))
    ) + " ELSE 'Not recorded' END"
    fields = ['i.name', 'i.customer_name', 'i.posting_date', 'i.status', 'i.grand_total',
              'i.outstanding_amount', 'i.currency', 'i.docstatus',
              col('i', 'patient') + ' AS patient', col('i', 'branch') + ' AS branch',
              mobile + ' AS mobile', source + ' AS source', provenance + ' AS source_from',
              lead_source + ' AS lead_source']
    return {'joins': joins, 'fields': fields, 'source': source, 'mobiles': mobiles,
            'branch': col('i', 'branch'), 'patient': col('i', 'patient')}


def _conditions(schema, query='', mobile='', branch='', status='', source='', from_date='', to_date=''):
    parts, params = ['1=1'], {}
    if from_date and to_date and getdate(from_date) > getdate(to_date):
        frappe.throw('Start date must be on or before end date.')
    if from_date:
        parts.append('i.posting_date >= %(from_date)s')
        params['from_date'] = getdate(from_date)
    if to_date:
        parts.append('i.posting_date < %(until)s')
        params['until'] = add_days(getdate(to_date), 1)
    for key, column, value in [('branch', schema['branch'], branch), ('source', schema['source'], source), ('status', 'i.status', status)]:
        if value:
            parts.append(column + ' = %(' + key + ')s')
            params[key] = str(value).strip()
    def phone_matches(param):
        return '(' + ' OR '.join(
            "REGEXP_REPLACE(COALESCE(" + column + ", ''), '[^0-9]', '') LIKE %(" + param + ')s'
            for column in schema['mobiles']) + ')'
    if mobile:
        digits = re.sub(r'\D', '', str(mobile))
        if len(digits) < 4:
            frappe.throw('Enter at least four digits for mobile search.')
        parts.append(phone_matches('mobile'))
        params['mobile'] = '%' + (digits[-10:] if len(digits) > 10 else digits) + '%'
    term = str(query or '').strip()
    if term:
        params['query'] = '%' + term.replace('%', '').replace('_', '') + '%'
        searches = [column + ' LIKE %(query)s' for column in ('i.name', 'i.customer_name', schema['patient'])]
        if re.fullmatch(r'[+\d\s().-]+', term) and len(re.sub(r'\D', '', term)) >= 4:
            digits = re.sub(r'\D', '', term)
            params['query_mobile'] = '%' + digits[-10:] + '%'
            searches.append(phone_matches('query_mobile'))
        parts.append('(' + ' OR '.join(searches) + ')')
    return ' WHERE ' + ' AND '.join(parts), params


@frappe.whitelist()
def filters():
    require_module('leads')
    return {
        'branches': frappe.get_all('Branch', pluck='name', order_by='name asc', limit_page_length=0),
        'sources': frappe.get_all('Lead Source', pluck='name', order_by='name asc', limit_page_length=0),
        'statuses': list(STATUSES),
    }


@frappe.whitelist()
def list_invoices(query='', mobile='', branch='', status='', source='', from_date='', to_date='', start=0):
    require_module('leads')
    schema = _schema()
    where, params = _conditions(schema, query, mobile, branch, status, source, from_date, to_date)
    try:
        offset = max(0, int(start))
    except (TypeError, ValueError):
        frappe.throw('Invalid invoice page.')
    params['start'] = offset
    base = schema['joins'] + where
    records = frappe.db.sql('SELECT ' + ','.join(schema['fields']) + base +
        ' ORDER BY i.posting_date DESC, i.name DESC LIMIT 41 OFFSET %(start)s', params, as_dict=True)
    counts = frappe.db.sql('SELECT COUNT(*) AS total, '
        'SUM(CASE WHEN i.docstatus != 2 AND i.outstanding_amount > 0 THEN 1 ELSE 0 END) AS outstanding_count' + base,
        params, as_dict=True)[0]
    amounts = frappe.db.sql('SELECT i.currency, SUM(i.grand_total) AS billed, '
        'SUM(i.outstanding_amount) AS outstanding' + base +
        ' AND i.docstatus != 2 GROUP BY i.currency ORDER BY i.currency', params, as_dict=True)
    return {'rows': records[:PAGE_SIZE], 'more': len(records) > PAGE_SIZE, 'start': offset,
            'total': int(counts.get('total') or 0), 'outstanding_count': int(counts.get('outstanding_count') or 0),
            'amounts': amounts}


@frappe.whitelist()
def invoice(name):
    require_module('leads')
    schema = _schema()
    rows = frappe.db.sql('SELECT ' + ','.join(schema['fields']) + schema['joins'] +
                         ' WHERE i.name = %(name)s', {'name': name}, as_dict=True)
    if not rows:
        frappe.throw('Invoice not found.', frappe.DoesNotExistError)
    result = dict(rows[0])
    doc = frappe.get_doc('Sales Invoice', name)
    for field in ('due_date', 'net_total', 'total_taxes_and_charges', 'discount_amount', 'rounded_total', 'is_return'):
        result[field] = doc.get(field)
    result['items'] = [{key: item.get(key) for key in
                        ('name', 'item_code', 'item_name', 'qty', 'uom', 'rate', 'amount')} for item in doc.get('items') or []]
    return result
