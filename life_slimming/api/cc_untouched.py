"""Compact, owner-scoped untouched lead report."""
import re
import frappe
from frappe.utils import getdate,date_diff
from life_slimming.api._runtime import script_endpoint
from life_slimming.portal_access import require_module


@script_endpoint(allow_guest=False)
def run(from_date=None,to_date=None,start=0,**kwargs):
    require_module('ccvisit')
    first,last=getdate(from_date),getdate(to_date)
    if first>last or date_diff(last,first)>366:
        frappe.throw('Choose a range of up to 367 days.')
    manager=frappe.session.user=='Administrator' or bool(set(frappe.get_roles()).intersection({'System Manager','Call Center Export','Sales Manager','CC Manager','MD','COO'}))
    filters={'custom_cc_stage':'UNTOUCHED','creation':['between',[str(first)+' 00:00:00',str(last)+' 23:59:59']]}
    if not manager:filters['lead_owner']=frappe.session.user
    rows=frappe.get_all('Lead',filters=filters,fields=['name','lead_name','lead_owner','mobile_no','creation'],order_by='creation desc, name desc',limit_start=max(0,int(start)),limit_page_length=50)
    users={u.name:u.full_name for u in frappe.get_all('User',filters={'name':['in',list({r.lead_owner for r in rows if r.lead_owner}) or ['-']]},fields=['name','full_name'],limit_page_length=50)}
    return {'rows':[{'name':r.name,'lead_name':r.lead_name,'agent_name':users.get(r.lead_owner,r.lead_owner),'phone':'••••'+re.sub(r'\D','',str(r.mobile_no or ''))[-4:],'creation':str(r.creation)} for r in rows], 'total':frappe.db.count('Lead',filters)}
