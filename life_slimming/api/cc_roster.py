"""CC roster: existing HR shift assignments, scoped exclusively to Ho CC."""
from datetime import date, timedelta
import calendar

import frappe
from frappe.utils import getdate, nowdate
from life_slimming.portal_access import require_module

BRANCH = 'Ho CC'


def authorize():
    if not frappe.session.user or frappe.session.user == 'Guest':
        raise frappe.AuthenticationError('Sign in to view the CC roster.')
    require_module('leads')


def period_for(anchor, view):
    if view not in ('week', 'month'):
        raise frappe.ValidationError('Choose week or month.')
    day = getdate(anchor or nowdate())
    if view == 'week':
        start = day - timedelta(days=day.weekday())
        end = start + timedelta(days=6)
    else:
        start = day.replace(day=1)
        end = day.replace(day=calendar.monthrange(day.year, day.month)[1])
    return start, end


def can_edit():
    return bool({'Call Center Export', 'System Manager'}.intersection(frappe.get_roles()))


def assignments(employees, start, end):
    if not employees:
        return []
    return frappe.get_all('Shift Assignment', filters={
        'employee': ['in', employees], 'docstatus': 1, 'status': 'Active',
        'start_date': ['<=', str(end)],
    }, or_filters=[['end_date', '>=', str(start)], ['end_date', 'is', 'not set']],
        fields=['name', 'employee', 'shift_type', 'start_date', 'end_date', 'modified'],
        order_by='start_date asc, name asc', limit_page_length=0)


def build_days(employees, shifts, attendance, leaves, start, end):
    days = [(start + timedelta(days=n)).isoformat() for n in range((end-start).days + 1)]
    result = {e['name']: {d: {'shifts': [], 'attendance': '', 'leave': False} for d in days} for e in employees}
    for shift in shifts:
        row = result.get(shift['employee'], {})
        first, last = getdate(shift['start_date']), getdate(shift['end_date']) if shift.get('end_date') else end
        for day in days:
            if first <= getdate(day) <= last:
                row[day]['shifts'].append(dict(
                    name=shift['name'], shift_type=shift['shift_type'], modified=str(shift['modified']),
                    single_day=bool(shift.get('end_date') and first == last)))
    for record in attendance:
        cell = result.get(record['employee'], {}).get(str(record['attendance_date']))
        if cell is not None:
            cell['attendance'] = record['status']
    for record in leaves:
        row = result.get(record['employee'], {})
        for day in days:
            if getdate(record['from_date']) <= getdate(day) <= getdate(record['to_date']):
                row[day]['leave'] = True
    return days, result


@frappe.whitelist(methods=['POST'])
def calendar_view(anchor=None, view='week'):
    authorize()
    start, end = period_for(anchor, view)
    employees = frappe.get_all('Employee', filters={'branch': BRANCH, 'status': 'Active'},
        fields=['name', 'employee_name', 'designation', 'department'],
        order_by='department asc, employee_name asc', limit_page_length=0)
    ids = [e.name for e in employees]
    shifts = assignments(ids, start, end)
    attendance, leaves = [], []
    attendance_available = bool(frappe.db.exists('DocType', 'Attendance'))
    if ids and attendance_available:
        attendance = frappe.get_all('Attendance', filters={'employee': ['in', ids], 'docstatus': 1,
            'attendance_date': ['between', [str(start), str(end)]]},
            fields=['employee', 'attendance_date', 'status'], limit_page_length=0)
    if ids and frappe.db.exists('DocType', 'Leave Application'):
        leaves = frappe.get_all('Leave Application', filters={'employee': ['in', ids], 'docstatus': 1,
            'status': 'Approved', 'from_date': ['<=', str(end)], 'to_date': ['>=', str(start)]},
            fields=['employee', 'from_date', 'to_date'], limit_page_length=0)
    days, cells = build_days(employees, shifts, attendance, leaves, start, end)
    return dict(branch=BRANCH, today=nowdate(), view=view, start=str(start), end=str(end),
        employees=employees, days=days, cells=cells, can_edit=can_edit(),
        attendance_available=attendance_available,
        shift_types=frappe.get_all('Shift Type', pluck='name', order_by='name asc', limit_page_length=0))


@frappe.whitelist(methods=['POST'])
def save_shift(employee, day, shift_type='', assignment='', expected_modified=''):
    authorize()
    if not can_edit():
        raise frappe.PermissionError('Only Call Center Export and System Manager can change CC roster shifts.')
    target = getdate(day)
    if not day or str(target) != day:
        raise frappe.ValidationError('Choose a valid roster date.')
    # Serialize changes from this roster for the same employee.
    frappe.db.sql('SELECT name FROM tabEmployee WHERE name=%s FOR UPDATE', (employee,))
    emp = frappe.get_doc('Employee', employee)
    if emp.branch != BRANCH or emp.status != 'Active':
        raise frappe.PermissionError('Only active Ho CC employees can be scheduled here.')
    current = assignments([employee], target, target)
    if len(current) > 1:
        raise frappe.ValidationError('Overlapping shifts exist. Resolve them in HR before changing this day.')
    old = current[0] if current else None
    if (old['name'] if old else '') != (assignment or '') or (old and str(old['modified']) != expected_modified):
        raise frappe.TimestampMismatchError('This roster changed elsewhere. Refresh and try again.')
    if old and (not old.get('end_date') or getdate(old['start_date']) != target or getdate(old['end_date']) != target):
        raise frappe.ValidationError('This shift covers multiple days. Change its date range in HR.')
    if shift_type and not frappe.db.exists('Shift Type', shift_type):
        raise frappe.ValidationError('Choose an existing shift type.')
    if old and old['shift_type'] == shift_type:
        return {'ok': 1, 'name': old['name']}
    # The explicit role check above grants access only to this Ho CC operation;
    # keep HR validation and lifecycle hooks without granting general HR access.
    if old:
        doc = frappe.get_doc('Shift Assignment', old['name'])
        doc.flags.ignore_permissions = True
        doc.cancel()
    if not shift_type:
        return {'ok': 1, 'name': ''}
    doc = frappe.get_doc(dict(doctype='Shift Assignment', employee=employee, company=emp.company,
        shift_type=shift_type, start_date=str(target), end_date=str(target), status='Active'))
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    doc.submit()
    return {'ok': 1, 'name': doc.name}
