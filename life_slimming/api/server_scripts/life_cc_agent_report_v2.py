"""LIFE CC Agent Reports v2

Original API: life_cc_agent_report_v2
Source modified: 2026-10-05 02:06:25.176853
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
    def appointment_bucket(status, visit_status, appointment_day, today, has_visit=False):
        # A confirmed visit takes precedence over stale cancelled/no-show fields.
        if has_visit:
            return 'walkins'
        if status == 'Cancelled':
            return 'cancelled'
        if not appointment_day:
            return 'unclassified'
        if appointment_day < today:
            return 'no_show'
        return 'awaiting'


    def score_kpis(actuals, targets, weights, volumes, factor=1.0, cap=100.0,
                   deductions=0.0, sources=None):
        """Missing inputs are excluded, with remaining weights renormalized once."""
        effective = []
        provisional = False
        source_flags = sources or [True] * 7
        for i in range(7):
            target = targets[i]
            if target is not None and i in (0, 1, 4):
                target = target * factor
            weight = max(0, weights[i])
            reason = ''
            if actuals[i] is None or target is None or target <= 0 or not source_flags[i]:
                weight = 0
                reason = 'Missing target or source'
                provisional = True
            elif i in (2, 3):
                volume = volumes[i]
                if volume < 5:
                    weight = 0
                    reason = 'Fewer than 5 base events'
                elif volume < 10:
                    weight = weight / 2
                    reason = '5–9 base events: half weight'
            effective.append({'target': target, 'weight': weight, 'reason': reason})
        total = sum(item['weight'] for item in effective)
        points = 0
        for i in range(7):
            item = effective[i]
            item['actual'] = actuals[i]
            item['weight'] = item['weight'] * 100 / total if total else 0
            item['achievement'] = min(cap, max(0, actuals[i] / item['target'] * 100)) if item['weight'] else None
            item['points'] = item['achievement'] * item['weight'] / 100 if item['weight'] else 0
            points = points + item['points']
        incentive_score = max(0, points - min(10, max(0, deductions))) if total else None
        final_score = min(100, incentive_score) if incentive_score is not None else None
        band = None
        if final_score is not None:
            band = 'A' if final_score >= 90 else 'B' if final_score >= 75 else 'C' if final_score >= 60 else 'D'
        return {'score': final_score, 'incentive_score': incentive_score, 'band': band,
                'provisional': provisional or total == 0, 'kpis': effective,
                'deductions': min(10, max(0, deductions)), 'available_weight': total}


    def reconciliation(rows):
        totals = {'appointments': len(rows), 'walkins': 0, 'awaiting': 0,
                  'no_show': 0, 'cancelled': 0, 'unclassified': 0,
                  'booked': 0, 'not_booked': 0, 'pending': 0}
        for row in rows:
            totals[row['bucket']] = totals[row['bucket']] + 1
            if row['bucket'] == 'walkins':
                outcome = row.get('outcome') or 'pending'
                totals[outcome] = totals[outcome] + 1
        totals['appointment_gap'] = totals['appointments'] - sum(totals[k] for k in ['walkins', 'awaiting', 'no_show', 'cancelled'])
        totals['visit_gap'] = totals['walkins'] - totals['booked'] - totals['not_booked'] - totals['pending']
        return totals

    # All metrics and drilldowns originate from the same normalized records.
    user = frappe.session.user
    if not user or user == 'Guest':
        frappe.throw('Please log in to view Agent Reports.')
    roles = frappe.get_all('Has Role',filters={'parent':user,'parenttype':'User'},pluck='role')
    manager = user == 'Administrator' or any(r in roles for r in ['System Manager','COO','CC Manager'])
    can_settings = manager
    today = str(frappe.utils.today())
    month_start = frappe.utils.getdate(today).replace(day=6)
    if frappe.utils.getdate(today).day < 6:
        month_start = frappe.utils.add_months(month_start,-1)
    start = str(frappe.utils.getdate(frappe.form_dict.get('from_date') or month_start))
    end = str(frappe.utils.getdate(frappe.form_dict.get('to_date') or today))
    if start > end or frappe.utils.date_diff(end,start) > 366:
        frappe.throw('Choose a valid range of no more than 367 days.')
    installed = frappe.db.exists('DocType','CC Agent KPI Plan')
    action = str(frappe.form_dict.get('action') or 'report')
    if action == 'save_plan':
        if not can_settings or not frappe.form_dict.get('csrf_token') or frappe.form_dict.get('csrf_token') != frappe.session.csrf_token:
            frappe.throw('Manager access and POST are required.')
        payload = json.loads(frappe.form_dict.get('plan') or '{}')
        allowed = ['from_date','to_date','working_days','status','sla_minutes','achievement_cap','prorate_attendance','prorate_period','deductions_on','remarks']
        allowed = allowed + ['target_k'+str(i) for i in range(1,8)] + ['weight_k'+str(i) for i in range(1,8)]
        key = str(payload.get('from_date') or '')[:7]
        plan_doc = frappe.get_doc('CC Agent KPI Plan',key) if frappe.db.exists('CC Agent KPI Plan',key) else frappe.new_doc('CC Agent KPI Plan')
        for field in allowed:
            if field in payload:
                plan_doc.set(field,payload[field])
        plan_doc.business_month = key
        if 'targets' in payload:
            plan_doc.set('targets',[])
            for row in payload['targets']:
                clean = {'employee':row.get('employee'),'include_in_ranking':row.get('include_in_ranking',1),'remarks':row.get('remarks','')}
                for i in range(1,8):
                    clean['target_k'+str(i)] = row.get('target_k'+str(i),'')
                plan_doc.append('targets',clean)
        plan_doc.save(ignore_permissions=True)
        frappe.response['message'] = {'saved':plan_doc.name}
    else:
        employees = frappe.get_all('Employee',fields=['name','employee_name','user_id','designation','department','status','reports_to','date_of_joining','attendance_device_id','holiday_list'],limit_page_length=10000)
        own = [e for e in employees if e.user_id == user]
        own_ids = [e.name for e in own]
        cc = [e for e in employees if e.designation in ['Business Executive','Business Executive Team Leader','Business Excutive Team Lead'] or e.name in ['HR-EMP-00544','HR-EMP-00483','HR-EMP-00552']]
        permitted = cc if manager else [e for e in cc if e.name in own_ids or e.reports_to in own_ids]
        if not permitted and not manager:
            frappe.throw('Your ERP user is not linked to a permitted CC Employee. Ask your manager to verify the mapping.')
        requested = json.loads(frappe.form_dict.get('employees') or '[]')
        selected = [e for e in permitted if (e.name in requested if requested else e.status == 'Active')]
        selected_ids = [e.name for e in selected]
        selected_users = [e.user_id for e in selected if e.user_id]
        if not selected:
            frappe.throw('Choose at least one permitted Employee.')
        if action == 'metadata':
            frappe.response['message'] = {'employees':permitted,'selected':selected_ids,'can_settings':can_settings,'setup_required':not installed}
        elif not installed:
            frappe.response['message'] = {'setup_required':True,'can_settings':can_settings,'employees':permitted}
        else:
            basis = 'cohort' if frappe.form_dict.get('basis') == 'cohort' else 'activity'
            branches = json.loads(frappe.form_dict.get('branches') or '[]')
            lookback = str(frappe.utils.add_months(start,-6))
            upper = max(end,today)
            def fetch(dt,fields,filters=None,order='creation asc'):
                output = []
                offset = 0
                while True:
                    batch = frappe.get_all(dt,fields=fields,filters=filters or [],order_by=order,limit_start=offset,limit_page_length=2000)
                    output.extend(batch)
                    if len(batch) < 2000:
                        break
                    offset = offset + 2000
                    if offset >= 100000:
                        frappe.throw('This range is too large. Narrow the period; partial totals will not be shown.')
                return output
            user_employee = {}
            duplicate_users = []
            for employee in cc:
                if employee.user_id:
                    if employee.user_id in user_employee:
                        duplicate_users.append(employee.user_id)
                    else:
                        user_employee[employee.user_id] = employee.name
            for employee in cc:
                if employee.user_id and employee.status == 'Active':
                    user_employee[employee.user_id] = employee.name
            lead_fields=['name','creation','owner','lead_owner','lead_name','mobile_no','gender','age','source','category','enquired_for','branch','lead_assign_to_branch','custom_posting_date','custom_appointment_date_and_time','custom_appointment_status','custom_visit_status','custom_cc_sub_status','custom_last_call_time','custom_next_followup_date','custom_consulting_doctor','custom_cc_first_agent','custom_cc_first_assigned_at','custom_cc_first_touched_at','custom_cc_appointment_agent','custom_cc_original_appointment','custom_cc_reschedule_count']
            # Date bounds are applied after attribution so reassignment cannot move credit.
            collected_leads = {}
            for date_field in ['custom_appointment_date_and_time','custom_posting_date','creation']:
                scope_filters = {date_field:['>=',lookback],'lead_owner':['in',selected_users]}
                batch = fetch('Lead',lead_fields,scope_filters) if selected_users else []
                for row in batch:
                    collected_leads[row.name] = row
            for field in ['custom_cc_appointment_agent','custom_cc_first_agent']:
                for row in fetch('Lead',lead_fields,{field:['in',selected_ids]}):
                    collected_leads[row.name] = row
            authored_versions = fetch('Version',['docname'],{'ref_doctype':'Lead','owner':['in',selected_users],'creation':['>=',lookback],'data':['like','%custom_appointment_date_and_time%']}) if selected_users else []
            authored_ids = list(set(v.docname for v in authored_versions if v.docname not in collected_leads))
            if authored_ids:
                for row in fetch('Lead',lead_fields,{'name':['in',authored_ids]}):
                    collected_leads[row.name] = row
            leads = list(collected_leads.values())
            lead_map = {r.name:r for r in leads}
            relevant_leads = [l for l in leads if (str(l.custom_appointment_date_and_time or '')[:10] >= lookback or str(l.custom_posting_date or l.creation)[:10] >= lookback) and True]
            relevant_ids = [l.name for l in relevant_leads if l.custom_appointment_date_and_time]
            versions = fetch('Version',['docname','owner','creation','data'],{'ref_doctype':'Lead','docname':['in',relevant_ids],'data':['like','%custom_appointment_date_and_time%']}) if relevant_ids else []
            appointment_authors = {}
            first_owners = {}
            for version in versions:
                if version.docname not in lead_map:
                    continue
                changes = json.loads(version.data or '{}').get('changed') or []
                for change in changes:
                    if len(change) >= 3:
                        if change[0] == 'lead_owner' and version.docname not in first_owners:
                            first_owners[version.docname] = change[1] or change[2]
                        if change[0] == 'custom_appointment_date_and_time' and change[2] and not change[1] and version.docname not in appointment_authors:
                            appointment_authors[version.docname] = {'agent':user_employee.get(version.owner),'at':str(version.creation)}
            scoped = []
            for lead in leads:
                recorded = appointment_authors.get(lead.name) or {}
                lead['credit_agent'] = lead.custom_cc_appointment_agent or recorded.get('agent') or user_employee.get(lead.lead_owner)
                lead['credit_provisional'] = not (lead.custom_cc_appointment_agent or recorded.get('agent')) or lead.lead_owner in duplicate_users
                lead['receipt_agent'] = lead.custom_cc_first_agent or user_employee.get(first_owners.get(lead.name)) or user_employee.get(lead.lead_owner)
                lead['receipt_provisional'] = not (lead.custom_cc_first_agent or first_owners.get(lead.name))
                lead['received_day'] = str(lead.custom_cc_first_assigned_at or lead.custom_posting_date or lead.creation)[:10]
                lead['appointment_created'] = recorded.get('at') or ''
                lead['branch_key'] = lead.branch or lead.lead_assign_to_branch or 'Not assigned'
                if (lead['credit_agent'] in selected_ids or lead['receipt_agent'] in selected_ids or user_employee.get(lead.lead_owner) in selected_ids) and (not branches or lead['branch_key'] in branches):
                    scoped.append(lead)
            lead_ids = [r.name for r in scoped]
            assigned_pool = fetch('Lead',['name','lead_owner','lead_name','source','branch','lead_assign_to_branch','custom_cc_first_touched_at','custom_last_call_time','custom_next_followup_date','custom_posting_date','creation'],{'lead_owner':['in',selected_users]}) if selected_users else []
            patients = fetch('Patient',['name','custom_lead','patient_name','sex','custom_joining_date','custom_pd_form_number','branch_name','custom_branch'],{'custom_lead':['in',lead_ids]}) if lead_ids else []
            patient_ids = [p.name for p in patients]
            pd_rows = fetch('PD Form',['parent','pd_form'],{'parent':['in',patient_ids]}) if patient_ids else []
            pd_patients = set(p.parent for p in pd_rows if p.pd_form)
            patient_by_lead = {}
            for patient in patients:
                patient_by_lead.setdefault(patient.custom_lead,[]).append(patient)
            visits = fetch('Patient Appointment',['name','patient','appointment_date','status'],{'patient':['in',patient_ids],'status':['in',['Checked In','Checked Out','Closed']]}) if patient_ids else []
            visit_by_patient = {}
            for visit in visits:
                visit_by_patient.setdefault(visit.patient,[]).append(visit)
            invoices = fetch('Sales Invoice',['name','patient','posting_date','grand_total','net_total','paid_amount','change_amount','is_pos','is_return','return_against','custom_therapy_plan','therapy_plan_reference_id','outstanding_amount','write_off_amount'],{'patient':['in',patient_ids],'docstatus':1}) if patient_ids else []
            invoice_ids = [i.name for i in invoices]
            invoice_by_patient = {}
            invoice_by_name = {i.name:i for i in invoices}
            returns_by_invoice = {}
            for invoice in invoices:
                if invoice.is_return and invoice.return_against:
                    returns_by_invoice.setdefault(invoice.return_against,[]).append(invoice)
            for invoice in invoices:
                invoice_by_patient.setdefault(invoice.patient,[]).append(invoice)
            refs = fetch('Payment Entry Reference',['parent','reference_name','allocated_amount'],{'reference_doctype':'Sales Invoice','reference_name':['in',invoice_ids]}) if invoice_ids else []
            pe_ids = list(set(r.parent for r in refs))
            payments = fetch('Payment Entry',['name','posting_date','payment_type','docstatus'],{'name':['in',pe_ids],'docstatus':1}) if pe_ids else []
            payment_map = {p.name:p for p in payments}
            receipts = {}
            for ref in refs:
                payment = payment_map.get(ref.parent)
                if payment:
                    signed = float(ref.allocated_amount or 0) * (-1 if payment.payment_type == 'Pay' else 1)
                    receipts.setdefault(ref.reference_name,[]).append({'date':str(payment.posting_date),'amount':signed,'reference':payment.name})
            for invoice in invoices:
                if invoice.is_pos and float(invoice.paid_amount or 0):
                    receipts.setdefault(invoice.name,[]).append({'date':str(invoice.posting_date),'amount':float(invoice.paid_amount or 0)-float(invoice.change_amount or 0),'reference':invoice.name})
            items = fetch('Sales Invoice Item',['parent','item_name','item_group','net_amount','qty'],{'parent':['in',invoice_ids]}) if invoice_ids else []
            plan_ids = list(set((i.custom_therapy_plan or i.therapy_plan_reference_id) for i in invoices if i.custom_therapy_plan or i.therapy_plan_reference_id))
            therapy_details = fetch('Therapy Plan Detail',['parent','no_of_sessions'],{'parent':['in',plan_ids]}) if plan_ids else []
            sessions_by_plan = {}
            for detail in therapy_details:
                sessions_by_plan[detail.parent] = sessions_by_plan.get(detail.parent,0) + float(detail.no_of_sessions or 0)
            items_by_invoice = {}
            for item in items:
                items_by_invoice.setdefault(item.parent,[]).append(item)
            attendance = fetch('Attendance',['employee','attendance_date','status','in_time','out_time','late_entry'],{'employee':['in',selected_ids],'docstatus':1,'attendance_date':['between',[lookback,upper]]})
            checkins = fetch('Employee Checkin',['employee','time','log_type'],{'employee':['in',selected_ids],'time':['between',[lookback+' 00:00:00',upper+' 23:59:59']]})
            plans = fetch('CC Agent KPI Plan',['name','from_date','to_date','status'],{'from_date':['<=',end],'to_date':['>=',lookback]})
            plan_documents = [frappe.get_doc('CC Agent KPI Plan',p.name).as_dict() for p in plans]
            logs = fetch('CC Lead Activity Log',['name','lead','agent','event_time','action','connected','change_json'],{'agent':['in',selected_ids],'event_time':['between',[lookback+' 00:00:00',upper+' 23:59:59']]})
            followups = fetch('CC Followup Event',['name','lead','agent','due_at','closed_at','result'],{'agent':['in',selected_ids],'due_at':['between',[lookback+' 00:00:00',upper+' 23:59:59']]})
            normalized = []
            for lead in scoped:
                appointment_day = str(lead.custom_appointment_date_and_time or '')[:10]
                if not appointment_day:
                    continue
                linked = patient_by_lead.get(lead.name,[])
                visit_candidates = []
                for patient in linked:
                    for visit in visit_by_patient.get(patient.name,[]):
                        if str(visit.appointment_date) >= appointment_day:
                            visit_candidates.append({'date':str(visit.appointment_date),'source':'Checked-in appointment','patient':patient})
                    if (patient.custom_pd_form_number or patient.name in pd_patients) and patient.custom_joining_date and str(patient.custom_joining_date) >= appointment_day:
                        visit_candidates.append({'date':str(patient.custom_joining_date),'source':'PD form and patient joining date','patient':patient})
                visit_candidates = sorted(visit_candidates,key=lambda x:x['date'])
                evidence = visit_candidates[0] if visit_candidates else None
                legacy_visit = lead.custom_appointment_status in ['Visited','Visited Booked','Visited Not Booked']
                visit_date = evidence['date'] if evidence else appointment_day if legacy_visit else ''
                patient = evidence['patient'] if evidence else linked[0] if len(linked) == 1 else None
                row_invoices = [i for i in invoice_by_patient.get(patient.name,[]) if str(i.posting_date) == visit_date and not i.is_return] if patient else []
                row_invoice_names = [i.name for i in row_invoices]
                returns = [item for name in row_invoice_names for item in returns_by_invoice.get(name,[])]
                row_invoices = row_invoices + returns
                paid_all = sum(float(event['amount']) for i in row_invoices for event in receipts.get(i.name,[]) if event['date'] <= today)
                paid_period = sum(float(event['amount']) for i in row_invoices for event in receipts.get(i.name,[]) if start <= event['date'] <= end)
                gross = sum(float(i.grand_total or 0) for i in row_invoices)
                net = sum(float(i.net_total or 0) for i in row_invoices)
                booked = bool(visit_date and gross > 0 and paid_all > 0)
                outcome = 'booked' if booked else 'not_booked' if lead.custom_appointment_status == 'Visited Not Booked' else 'pending'
                bucket = appointment_bucket(lead.custom_appointment_status,lead.custom_visit_status,appointment_day,today,bool(visit_date))
                row_items = [item for i in row_invoices if not i.is_return for item in items_by_invoice.get(i.name,[])]
                row_items = sorted(row_items,key=lambda x:float(x.net_amount or 0),reverse=True)
                primary = row_items[0] if row_items else {}
                gender = (patient.sex if patient else None) or lead.gender or 'Not captured'
                gender = gender if gender in ['Male','Female'] else 'Not captured'
                # Expose only masked phone numbers; historical reassignment never expands client access.
                mobile = str(lead.mobile_no or '')
                masked = mobile[:3]+'xxx'+mobile[-4:] if len(mobile) >= 7 else ''
                private = not manager and lead.lead_owner != user and not any(e.reports_to in own_ids and e.user_id == lead.lead_owner for e in selected)
                normalized.append({'id':lead.name,'agent':lead['credit_agent'],'first_agent':lead['receipt_agent'],'received':lead['received_day'],'appointment':str(lead.custom_appointment_date_and_time),'appointment_created':lead['appointment_created'],'visit_date':visit_date,'visit_evidence':evidence['source'] if evidence else 'Legacy visited status — provisional' if legacy_visit else '', 'credit_provisional':lead['credit_provisional'],'receipt_provisional':lead['receipt_provisional'],'visit_provisional':bool(legacy_visit and not evidence),'branch':lead['branch_key'],'bucket':bucket,'outcome':outcome if bucket=='walkins' else '', 'client':'Restricted historical record' if private else lead.lead_name,'mobile':'' if private else masked,'gender':gender,'age':lead.age or None,'source':lead.source or 'Not captured','enquired':lead.enquired_for or lead.category or 'Not captured','consultant':lead.custom_consulting_doctor or '', 'pd':patient.custom_pd_form_number if patient else '', 'invoices':[] if private else [i.name for i in row_invoices],'gross':gross,'net':net,'paid':paid_period,'paid_all':paid_all,'balance':gross-paid_all,'erp_outstanding':sum(float(i.outstanding_amount or 0) for i in row_invoices),'treatment':primary.get('item_name') or 'Not captured','category':primary.get('item_group') or 'Not captured','quantity':sum(sessions_by_plan.get(plan,0) for plan in set(i.custom_therapy_plan or i.therapy_plan_reference_id for i in row_invoices)),'legacy_status':lead.custom_appointment_status or 'Not set','payment_events':[event for i in row_invoices for event in receipts.get(i.name,[])]})
            def in_range(value,a,b):
                return bool(value and a <= str(value)[:10] <= b)
            def aggregate(agent,a,b,current_basis):
                cohort_ids = set(l.name for l in scoped if l['receipt_agent']==agent and in_range(l['received_day'],a,b))
                rows = [r for r in normalized if r['agent']==agent and (r['id'] in cohort_ids if current_basis=='cohort' else in_range(r['appointment'],a,b))]
                partition = reconciliation(rows)
                visit_rows = [r for r in normalized if r['agent']==agent and r['bucket']=='walkins' and (r['id'] in cohort_ids if current_basis=='cohort' else in_range(r['visit_date'],a,b))]
                booked_rows = [r for r in visit_rows if r['outcome']=='booked']
                received = [l for l in scoped if l['receipt_agent']==agent and in_range(l['received_day'],a,b)]
                quality = [l for l in received if str(l.custom_cc_sub_status or '').lower() not in ['junk/wrong call','invalid number','wrong number','junk','duplicate']]
                connected_ids = list(set(l.lead for l in logs if l.agent==agent and l.connected and in_range(l.event_time,a,b)))
                assigned = [l for l in assigned_pool if user_employee.get(l.lead_owner)==agent and (not branches or (l.branch or l.lead_assign_to_branch or 'Not assigned') in branches)]
                touched = [l for l in logs if l.agent==agent and l.action in ['call','status change','appointment'] and in_range(l.event_time,a,b)]
                due = [f for f in followups if f.agent==agent and in_range(f.due_at,a,b) and f.result!='Rescheduled']
                done_time = [f for f in due if f.result=='Done on time']
                done_late = [f for f in due if f.result=='Done late']
                overdue = [f for f in due if f.result in ['Open','Missed'] and str(f.due_at) < str(frappe.utils.now())]
                att = [v for v in attendance if v.employee==agent and in_range(v.attendance_date,a,b)]
                present = sum(.5 if v.status=='Half Day' else 1 if v.status in ['Present','Work From Home'] else 0 for v in att)
                paid_rows = [r for r in normalized if r['agent']==agent and r['outcome']=='booked' and (current_basis!='cohort' or r['id'] in cohort_ids)]
                paid = sum(float(ev['amount']) for r in paid_rows for ev in r['payment_events'] if in_range(ev['date'],a,b))
                metrics={'agent':agent,'from_date':a,'to_date':b,'basis':current_basis,'leads':len(received),'quality':len(quality),'connected':len(connected_ids),'appointments':len(rows),'walkins':len(visit_rows),'booked':len(booked_rows),'not_booked':len([r for r in visit_rows if r['outcome']=='not_booked']),'pending':len([r for r in visit_rows if r['outcome']=='pending']),'awaiting':partition['awaiting'],'no_show':partition['no_show'],'cancelled':partition['cancelled'],'partition':partition,'gross':sum(r['gross'] for r in booked_rows),'net':sum(r['net'] for r in booked_rows),'paid':paid,'balance':sum(r['balance'] for r in booked_rows),'assigned':len(assigned),'never_touched':len([l for l in assigned if not l.custom_cc_first_touched_at and not l.custom_last_call_time]),'fresh_touched':len(set(l.lead for l in touched).intersection(set(l.name for l in received))),'old_touched':len(set(l.lead for l in touched).difference(set(l.name for l in received))),'updates':len(touched),'unique_updates':len(set(l.lead for l in touched)),'followup_due':len(due),'followup_on_time':len(done_time),'followup_late':len(done_late),'followup_overdue':len(overdue),'present_days':present,'attendance_days':len(att),'late_ins':len([v for v in att if v.late_entry]),'leave_days':len([v for v in att if v.status=='On Leave']),'ids':{'leads':[l.name for l in received],'quality':[l.name for l in quality],'connected':connected_ids,'appointments':[r['id'] for r in rows],'walkins':[r['id'] for r in visit_rows],'booked':[r['id'] for r in booked_rows],'not_booked':[r['id'] for r in visit_rows if r['outcome']=='not_booked'],'pending':[r['id'] for r in visit_rows if r['outcome']=='pending'],'awaiting':[r['id'] for r in rows if r['bucket']=='awaiting'],'no_show':[r['id'] for r in rows if r['bucket']=='no_show'],'cancelled':[r['id'] for r in rows if r['bucket']=='cancelled'],'assigned':[l.name for l in assigned],'never_touched':[l.name for l in assigned if not l.custom_cc_first_touched_at and not l.custom_last_call_time],'unique_updates':list(set(l.lead for l in touched)),'updates':['log:'+l.name for l in touched],'followup_due':['fu:'+f.name for f in due],'followup_on_time':['fu:'+f.name for f in done_time],'followup_late':['fu:'+f.name for f in done_late],'followup_overdue':['fu:'+f.name for f in overdue]},'provisional':any(r['credit_provisional'] or r['visit_provisional'] for r in rows) or any(l['receipt_provisional'] for l in received)}
                base = partition['walkins'] + partition['no_show']
                metrics['showup'] = 100*partition['walkins']/base if base else None
                metrics['conversion'] = 100*len(booked_rows)/len(visit_rows) if visit_rows else None
                responses = []
                for lead in received:
                    if lead.custom_cc_first_assigned_at and lead.custom_cc_first_touched_at:
                        minutes = frappe.utils.time_diff_in_seconds(lead.custom_cc_first_touched_at,lead.custom_cc_first_assigned_at)/60
                        responses.append(max(0,minutes))
                responses = sorted(responses)
                metrics['first_response_median'] = (responses[(len(responses)-1)//2]+responses[len(responses)//2])/2 if responses else None
                matching = [p for p in plan_documents if str(p['from_date']) <= a and str(p['to_date']) >= b and p['status'] in ['Active','Locked']]
                plan = matching[0] if matching else None
                overrides = [t for t in plan.get('targets',[]) if t.employee==agent] if plan else []
                override = overrides[0] if overrides else {}
                targets = []
                for i in range(1,8):
                    value = override.get('target_k'+str(i))
                    if value is None or str(value).strip()=='':
                        value = plan.get('target_k'+str(i)) if plan else None
                    targets.append(float(value) if value is not None and str(value).strip() else None)
                weights = [float(plan.get('weight_k'+str(i)) or 0) for i in range(1,8)] if plan else [30,20,10,10,10,10,10]
                sla = float(plan.get('sla_minutes') or 30) if plan else 30
                response_rate = 100*len([x for x in responses if x<=sla])/len(received) if received and all(l.custom_cc_first_assigned_at for l in received) else None
                followup_rate = 100*len(done_time)/len(due) if due else None
                factor = 1.0
                if plan:
                    if plan.get('prorate_attendance'):
                        factor = present/float(plan['working_days'])
                    elif plan.get('prorate_period'):
                        factor = min(1.0,max(0,frappe.utils.date_diff(min(b,today),max(a,str(plan['from_date'])))+1)/float(frappe.utils.date_diff(plan['to_date'],plan['from_date'])+1))
                capture = 100*len([r for r in booked_rows if r['gender']!='Not captured' and r['age'] and r['treatment']!='Not captured'])/len(booked_rows) if booked_rows else None
                deduction = min(10,max(0,int((90-capture+9.999)/10)*2)) if plan and plan.get('deductions_on') and capture is not None and capture<90 else 0
                scored = score_kpis([len(booked_rows),len(visit_rows),metrics['showup'],metrics['conversion'],paid,response_rate,followup_rate],targets,weights,[0,0,base,len(visit_rows),0,0,0],factor,float(plan.get('achievement_cap') or 100) if plan else 100,deduction)
                scored['provisional'] = scored['provisional'] or metrics['provisional']
                metrics['score'] = scored
                metrics['capture'] = capture
                metrics['plan'] = plan['name'] if plan else None
                metrics['included'] = agent != 'HR-EMP-00483' and bool(override.get('include_in_ranking',1))
                metrics['response_rate'] = response_rate
                metrics['followup_rate'] = followup_rate
                return metrics
            metrics = [aggregate(e.name,start,end,basis) for e in selected]
            snapshots = {'today':[aggregate(e.name,today,today,'activity') for e in selected],'yesterday':[aggregate(e.name,str(frappe.utils.add_days(today,-1)),str(frappe.utils.add_days(today,-1)),'activity') for e in selected]}
            history = []
            for offset in range(-5,1):
                a = str(frappe.utils.add_months(month_start,offset))
                b = min(today,str(frappe.utils.add_days(frappe.utils.add_months(a,1),-1)))
                if a<=b:
                    history_metrics = [aggregate(e.name,a,b,'activity') for e in selected]
                    for item in history_metrics:
                        item['ids'] = {}
                    history.append({'from_date':a,'to_date':b,'metrics':history_metrics})
            comparison = []
            compare = frappe.form_dict.get('compare')
            if compare in ['previous','last_month']:
                length = int(frappe.utils.date_diff(end,start))+1
                ca = str(frappe.utils.add_days(start,-length)) if compare=='previous' else str(frappe.utils.add_months(start,-1))
                cb = str(frappe.utils.add_days(start,-1)) if compare=='previous' else str(frappe.utils.add_months(end,-1))
                comparison = [aggregate(e.name,ca,cb,basis) for e in selected]
                for item in comparison:
                    item['ids'] = {}
            lead_details = [{'id':l.name,'agent':l['receipt_agent'],'received':l['received_day'],'client':l.lead_name if manager or l.lead_owner==user else 'Restricted historical record','mobile':'','source':l.source or 'Not captured','branch':l['branch_key'],'last_touch':str(l.custom_last_call_time or l.custom_cc_first_touched_at or ''),'next_followup':str(l.custom_next_followup_date or '')} for l in scoped]
            detail_ids = set(l['id'] for l in lead_details)
            for lead in assigned_pool:
                if lead.name not in detail_ids:
                    lead_details.append({'id':lead.name,'agent':user_employee.get(lead.lead_owner),'received':str(lead.custom_posting_date or lead.creation)[:10],'client':lead.lead_name,'mobile':'','source':lead.source or 'Not captured','branch':lead.branch or lead.lead_assign_to_branch or 'Not assigned','last_touch':str(lead.custom_last_call_time or lead.custom_cc_first_touched_at or ''),'next_followup':str(lead.custom_next_followup_date or '')})
            if not branches and basis == 'activity':
                for metric in snapshots['today']:
                    key = metric['agent']+'-'+today
                    values = {'metric_key':key,'employee':metric['agent'],'metric_date':today,'refreshed_at':frappe.utils.now(),'metrics_json':json.dumps(metric,default=str)}
                    if frappe.db.exists('CC Agent Daily Metric',key):
                        frappe.db.set_value('CC Agent Daily Metric',key,values,update_modified=False)
                    else:
                        values['doctype'] = 'CC Agent Daily Metric'
                        frappe.get_doc(values).insert(ignore_permissions=True,ignore_if_duplicate=True)
            all_branches = frappe.get_all('Branch',pluck='name',limit_page_length=1000)
            frappe.response['message'] = {'version':'2.0','generated_at':frappe.utils.now(),'can_settings':can_settings,'manager':manager,'employees':permitted,'selected':selected_ids,'branches':all_branches,'from_date':start,'to_date':end,'basis':basis,'metrics':metrics,'rows':normalized,'lead_details':lead_details,'snapshots':snapshots,'history':history,'comparison':comparison,'attendance':attendance,'checkins':checkins,'followups':followups,'logs':logs,'plans':plan_documents if can_settings else [],'health':{'missing_users':[e.employee_name for e in permitted if not e.user_id],'duplicate_users':duplicate_users,'provisional_credits':len([r for r in normalized if r['credit_provisional']]),'legacy_visit_evidence':len([r for r in normalized if r['visit_provisional']]),'note':'Activity dates differ by metric. Branch reconciliation uses one appointment population. Historical status-only visits and uncertain attribution remain provisional.'} if manager else None}
