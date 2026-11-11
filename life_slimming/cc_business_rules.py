"""Shared CC outcome, attribution and redistribution policy."""
import json
import frappe
from frappe.utils import get_datetime

PERMISSION_EDITORS = frozenset({'bhuvan@lifescc.com', 'narendhar@lifescc.com'})
DEFAULT_MOVERS = frozenset({'Administrator', 'bhuvan@lifescc.com', 'surya@lifescc.com'})
MOVER_ROLES = frozenset({'Call Center Export', 'System Manager', 'Team Lead', 'TL', 'MD'})


def booked(lead, counts=None):
    return bool((counts or {}).get('booked') or (counts or {}).get('visited') or
        lead.get('custom_appointment_status') in {'Booked','Visited','Visited Booked','Visited Not Booked','Not Visited'} or
        lead.get('custom_cc_sub_status') in {'Appointment Booked','Walked In & Booked','Walked In: Not Booked'} or
        lead.get('status') in {'Appointment Booked','Converted','Joined'})


def has_business_result(lead, paid=0, bill=False):
    return bool(paid or bill or booked(lead) or lead.get('custom_cc_stage') in {'SUCCESS','LOST','INVALID'} or
        lead.get('custom_cc_sub_status') not in {None,'','Lead','No Response','Not Response','Not Reachable','Switch OFF','TNA','Call Disconnected','Appointment no response','Busy','Not Lifted'})


def linked_patients(names):
    if not names:
        return {}
    mapping = {p.name:p.custom_lead for p in frappe.get_all('Patient', filters={'custom_lead':['in',names]}, fields=['name','custom_lead'], limit_page_length=0)}
    for row in frappe.get_all('LIFE CC Lead Track', filters={'lead':['in',names],'match_status':'Verified','matched_patient':['is','set']}, fields=['lead','matched_patient'], limit_page_length=0):
        mapping[row.matched_patient] = row.lead
    return mapping


def submission_times(doctype, names):
    """Use recorded submission events; do not treat posting dates as timestamps."""
    result = {}
    if not names:
        return result
    for row in frappe.get_all('Version', filters={'ref_doctype':doctype,'docname':['in',names],'data':['like','%docstatus%']}, fields=['docname','creation','data'], order_by='creation asc', limit_page_length=0):
        try:
            changes=json.loads(row.data or '{}').get('changed',[])
        except (ValueError,TypeError):
            continue
        if any(len(c)>=3 and c[0]=='docstatus' and str(c[2])=='1' for c in changes):
            result.setdefault(row.docname, str(row.creation))
    return result


def paid_evidence(names):
    p2l=linked_patients(names)
    if not p2l:
        return {}
    invoices=frappe.get_all('Sales Invoice', filters={'patient':['in',list(p2l)],'docstatus':1,'is_return':0}, fields=['name','patient','posting_date','grand_total','outstanding_amount','paid_amount'], limit_page_length=0)
    invoice_map={i.name:i for i in invoices}
    references=frappe.get_all('Payment Entry Reference', filters={'reference_doctype':'Sales Invoice','reference_name':['in',list(invoice_map) or ['-']],'docstatus':1}, fields=['parent','reference_name','allocated_amount'], limit_page_length=0)
    parents=list({r.parent for r in references if float(r.allocated_amount or 0)>0})
    payments={p.name:p for p in frappe.get_all('Payment Entry',filters={'name':['in',parents or ['-']],'docstatus':1,'payment_type':'Receive'},fields=['name','posting_date'],limit_page_length=0)} if parents else {}
    payment_times=submission_times('Payment Entry',list(payments))
    invoice_times=submission_times('Sales Invoice',list(invoice_map))
    first={}
    for ref in references:
        if ref.parent in payments and float(ref.allocated_amount or 0)>0:
            stamp=payment_times.get(ref.parent)
            if stamp:
                first[ref.reference_name]=min(first.get(ref.reference_name,stamp),stamp)
    out={}
    for invoice in invoices:
        name=p2l[invoice.patient]
        record=out.setdefault(name,{'paid':0,'has_bill':True,'joined_on':None,'paid_at':None,'credit_provisional':False})
        amount=max(0,float(invoice.grand_total or 0)-float(invoice.outstanding_amount or 0))
        if not amount:
            continue
        record['paid']+=amount
        # For directly-paid invoices, submission is the payment event. A later
        # collection must have its own recorded Payment Entry submission.
        has_payment=any(r.reference_name==invoice.name and r.parent in payments for r in references)
        candidates=[stamp for stamp in [first.get(invoice.name), invoice_times.get(invoice.name) if float(invoice.get('paid_amount') or 0)>0 else None] if stamp]
        exact=min(candidates) if candidates else None
        cutoff=exact or str(invoice.posting_date)+' 00:00:00'
        if not record['paid_at'] or get_datetime(cutoff)<get_datetime(record['paid_at']):
            record.update(paid_at=cutoff,joined_on=str(invoice.posting_date),credit_provisional=not bool(exact))
    return out


def credit_for_events(events, evidence, employee_of):
    result={}
    for event in sorted(events,key=lambda e:str(e.event_time)):
        record=evidence.get(event.lead) or {}
        if record.get('paid') and record.get('paid_at') and get_datetime(event.event_time)<=get_datetime(record['paid_at']):
            result[event.lead]=event.agent or employee_of(event.erp_user)
    return result


def validate_lead_update(lead, values):
    protected={'status','custom_cc_stage','custom_cc_sub_status','custom_appointment_date_and_time','custom_appointment_status','lead_owner'}
    changed={k for k in protected if k in values and str(values[k] or '')!=str(lead.get(k) or '')}
    if not changed:
        return
    evidence=paid_evidence([lead.name]).get(lead.name) or {}
    if evidence.get('paid') and ('lead_owner' in changed or booked(lead)):
        frappe.throw('Paid and joined clients are protected. Record feedback without changing the owner or business outcome.')
    if evidence.get('has_bill') and values.get('custom_cc_sub_status') in {'No Response','Not Response','Not Reachable','Switch OFF','TNA','Call Disconnected','Appointment no response'}:
        frappe.throw('A failed call cannot replace a lead with an existing bill. Save it as a call attempt.')
