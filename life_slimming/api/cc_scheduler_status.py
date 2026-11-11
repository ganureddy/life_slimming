"""Read-only scheduler diagnostics; never enable or execute a rule."""
import frappe
from frappe.utils import now_datetime,get_datetime
from life_slimming.api._runtime import script_endpoint


@script_endpoint(allow_guest=False)
def run(**kwargs):
    from life_slimming.api.cc_core import run as core
    if not core(action='perm')['can_move']:
        frappe.throw('Lead distribution access is required.',frappe.PermissionError)
    jobs=frappe.get_all('Scheduled Job Type',filters={'method':'life_slimming.cc_autoshuffle.run'},fields=['name','last_execution','stopped'],limit_page_length=10)
    rules=frappe.get_all('LIFE CC Assign Rule',filters={'enabled':1,'rule_type':['in',['Time-over New Lead','Time-over Follow-up','Hot Lead Overdue','Visited Not Booked','Absent Agent']]},fields=['name','test_mode','last_run','last_moved'],limit_page_length=200)
    last=max((get_datetime(j.last_execution) for j in jobs if j.last_execution),default=None)
    paused=bool(frappe.conf.get('pause_scheduler') or frappe.conf.get('maintenance_mode'))
    return {'jobs':jobs,'rules':rules,'paused':paused,'last_execution':str(last) if last else '',
            'stale':not last or (now_datetime()-last).total_seconds()>900,'checked_at':str(now_datetime()),
            'legacy_active':bool(frappe.db.exists('Server Script',{'name':'life_cc_autoshuffle','disabled':0}))}
