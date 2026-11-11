"""Lazy, paged Agent 360 call history and recording access."""
import json
import re
from urllib.parse import urlsplit
import frappe
from frappe.utils import getdate, date_diff
from life_slimming.api._runtime import script_endpoint
from life_slimming.portal_access import require_module

MANAGERS = {'System Manager', 'Sales Manager', 'Call Center Export', 'CC Manager', 'COO'}
CHANGE_FIELDS = {'status','custom_cc_stage','custom_cc_sub_status','lead_owner','branch','lead_assign_to_branch',
                 'custom_appointment_status','custom_appointment_date_and_time','custom_next_followup_date',
                 'custom_conclusion_remark','source','first_name','lead_name','mobile_no','phone'}


def scope(agents=None):
    require_module('ccvisit')
    user = frappe.session.user
    manager = user == 'Administrator' or bool(MANAGERS.intersection(frappe.get_roles()))
    try:
        requested = json.loads(agents or '[]') if isinstance(agents, str) else agents or []
    except (ValueError, TypeError):
        frappe.throw('Choose a valid list of agents.')
    if not isinstance(requested, list):
        frappe.throw('Choose a valid list of agents.')
    users = frappe.get_all('User', filters={} if manager else {'name':user},
        fields=['name','full_name','custom_convox_agent_id'], limit_page_length=10000)
    return {u.name:u for u in users if not requested or u.name in requested}


def masked(value):
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?', str(value or '')):
        return str(value)
    return re.sub(r'(?<!\d)\+?\d[\d ()-]{8,}\d(?!\d)', lambda m:'••••'+re.sub(r'\D','',m[0])[-4:], str(value or ''))


def filters_for(kind, users):
    if kind == 'convox':
        ids = [u.custom_convox_agent_id for u in users.values() if u.custom_convox_agent_id]
        return {'agent_id':['in',ids or ['-']], 'event_type':'Call Status'}
    if kind == 'mobile':
        return {'agent':['in',list(users) or ['-']]}
    if kind == 'updates':
        return {'owner':['in',list(users) or ['-']], 'ref_doctype':'Lead'}
    frappe.throw('Choose CC History, ConVox History or Lead Updates.')


@script_endpoint(allow_guest=False)
def history(kind='mobile', from_date=None, to_date=None, agents=None, start=0, limit=30, query='', **kwargs):
    users = scope(agents)
    first,last = getdate(from_date),getdate(to_date)
    if first > last or date_diff(last,first) > 92:
        frappe.throw('Choose a history range of up to 93 days.')
    try:
        start,limit = max(0,int(start)),max(1,min(100,int(limit)))
    except (TypeError,ValueError):
        frappe.throw('Choose a valid history page.')
    definitions = {
        'convox':('ConVox Call Event','received_on',['name','agent_id','received_on','crm_lead','mobile_number','call_mode','call_status','call_duration','disposition','recording_available']),
        'mobile':('LIFE Mobile Call Log','started_on',['name','agent','started_on','lead','lead_name','mobile_number','direction','call_status','talk_seconds','disposition','recording_available']),
        'updates':('Version','creation',['name','owner','creation','docname','data']),
    }
    filters = filters_for(kind,users)
    doctype,stamp,fields = definitions[kind]
    filters[stamp] = ['between',[str(first)+' 00:00:00',str(last)+' 23:59:59']]
    if not users or not frappe.db.exists('DocType',doctype):
        return {'rows':[], 'has_more':False, 'start':start, 'limit':limit}
    # Older mobile installations may not have the optional direction/recording flag.
    meta = frappe.get_meta(doctype)
    fields = [f for f in fields if f in {'name','creation','owner'} or meta.has_field(f)]
    term = str(query or '').strip()[:100]
    search_fields = {'convox':['crm_lead','mobile_number','call_status','disposition','agent_id'],
                     'mobile':['lead','lead_name','mobile_number','call_status','disposition','agent'],
                     'updates':['docname','owner','data']}[kind]
    or_filters = {field:['like','%'+term.replace('%','\\%').replace('_','\\_')+'%'] for field in search_fields if field in fields} if term else None
    records = frappe.get_all(doctype, filters=filters, or_filters=or_filters, fields=fields,
        order_by=stamp+' desc, name desc', limit_start=start, limit_page_length=limit+1)
    dialers = {str(u.custom_convox_agent_id):u.name for u in users.values() if u.custom_convox_agent_id}
    rows=[]
    for item in records[:limit]:
        agent = dialers.get(str(item.get('agent_id'))) if kind == 'convox' else item.get('agent') if kind == 'mobile' else item.get('owner')
        if agent not in users:
            continue
        row={'id':item.name,'at':str(item.get(stamp) or ''),'agent':agent,'agent_name':users[agent].full_name or agent}
        if kind == 'updates':
            try:
                changed=json.loads(item.get('data') or '{}').get('changed',[])
            except (ValueError,TypeError):
                changed=[]
            row.update(lead=item.get('docname'), changes=[{'field':c[0],'before':masked(c[1]),'after':masked(c[2])} for c in changed[:200] if len(c)>=3 and c[0] in CHANGE_FIELDS])
        else:
            digits=re.sub(r'\D','',str(item.get('mobile_number') or ''))
            row.update(lead=item.get('crm_lead') or item.get('lead') or '',client=item.get('lead_name') or '',
                phone='••••'+digits[-4:] if digits else '', direction=item.get('call_mode') or item.get('direction') or '',
                status=item.get('call_status') or '', duration=item.get('call_duration') or item.get('talk_seconds') or 0,
                disposition=item.get('disposition') or '',recording_available=bool(item.get('recording_available')))
        rows.append(row)
    return {'rows':rows,'has_more':len(records)>limit,'start':start,'limit':limit}


def safe_recording(value, kind):
    value=str(value or '').strip()
    if not value:
        return ''
    if kind=='mobile' and value.startswith(('/private/files/','/files/')) and not any(c in value for c in ('\\','\r','\n')) and '..' not in value:
        return value
    parsed=urlsplit(value)
    if kind=='convox' and parsed.scheme in ('http','https') and parsed.hostname in ('192.168.0.193','lifeslimming.deepijatel.in') and not parsed.username and not parsed.password:
        return 'https://lifeslimming.deepijatel.in'+parsed.path+('?' + parsed.query if parsed.query else '')
    return ''


@script_endpoint(allow_guest=False)
def recording(kind=None, id=None, **kwargs):
    users=scope()
    if kind not in ('convox','mobile'):
        frappe.throw('Choose a call channel.')
    doctype='ConVox Call Event' if kind=='convox' else 'LIFE Mobile Call Log'
    filters=filters_for(kind,users)
    filters['name']=str(id or '')[:140]
    field='recording_file_name' if kind=='convox' else 'recording'
    records=frappe.get_all(doctype,filters=filters,fields=['name',field],limit_page_length=1)
    if not records:
        frappe.throw('This call is not available to your account.',frappe.PermissionError)
    return {'url':safe_recording(records[0].get(field),kind)}
