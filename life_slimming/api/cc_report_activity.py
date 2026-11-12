"""Owner-scoped ConVox/mobile activity for the CC visit report."""
import json
from datetime import timedelta
import frappe
from frappe.utils import getdate, date_diff, get_datetime
from life_slimming.api._runtime import script_endpoint
from life_slimming.portal_access import require_module


def aggregate(events, updates, gap_minutes=15):
    groups = {}
    for event in events:
        owner = event['agent']
        row = groups.setdefault(owner, dict(agent=owner, convox=0, mobile=0, answered=0, talk=0, updates=0, idle_minutes=0, longest_gap=0, updated_no_call=0, talked_no_update=0, dispositions={}, events=[]))
        row[event['channel']] += 1
        row['answered'] += int(event['answered'])
        row['talk'] += event['talk']
        disposition = event.get('disposition') or event.get('status') or 'Not set'
        row['dispositions'][disposition] = row['dispositions'].get(disposition, 0) + 1
        row['events'].append(event)
    for update in updates:
        owner = update['agent']
        row = groups.setdefault(owner, dict(agent=owner, convox=0, mobile=0, answered=0, talk=0, updates=0, idle_minutes=0, longest_gap=0, updated_no_call=0, talked_no_update=0, dispositions={}, events=[]))
        row['updates'] += 1
        row['events'].append(update)
    for row in groups.values():
        row['events'].sort(key=lambda e: str(e['at']))
        call_keys = {(str(e['at'])[:10], e.get('lead')) for e in row['events'] if e['channel'] != 'update' and e.get('lead')}
        update_keys = {(str(e['at'])[:10], e.get('lead')) for e in row['events'] if e['channel'] == 'update' and e.get('lead')}
        talk_keys = {(str(e['at'])[:10], e.get('lead')) for e in row['events'] if e['channel'] != 'update' and e['talk'] >= 60 and e.get('lead')}
        row['updated_no_call'] = len(update_keys - call_keys)
        row['talked_no_update'] = len(talk_keys - update_keys)
        previous_end = None
        previous_day = None
        for event in row['events']:
            stamp = get_datetime(event['at'])
            if previous_end is not None and stamp.date() == previous_day:
                gap = (stamp - previous_end).total_seconds() / 60
                if gap >= gap_minutes:
                    row['idle_minutes'] += round(gap)
                    row['longest_gap'] = max(row['longest_gap'], round(gap))
            event_end = stamp + timedelta(seconds=event.get('talk', 0))
            previous_end = max(previous_end, event_end) if previous_end is not None and stamp.date() == previous_day else event_end
            previous_day = stamp.date()
    return sorted(groups.values(), key=lambda r: -(r['convox'] + r['mobile']))


def appointment_counts(appointments):
    result = {}
    for lead in appointments:
        row = result.setdefault(lead.get('lead_owner'), {'appointments': 0, 'walkins': 0, 'booked': 0})
        row['appointments'] += 1
        status = str(lead.get('custom_appointment_status') or lead.get('custom_visit_status') or '').lower().strip()
        status = ' '.join(status.replace('–', ' ').replace('—', ' ').replace('-', ' ').replace('&', ' ').split())
        if status.startswith('visited') or status in ('walked in booked', 'walked in: not booked'):
            row['walkins'] += 1
        if status in ('visited booked', 'walked in booked'):
            row['booked'] += 1
    return result


@script_endpoint(allow_guest=False)
def run(from_date=None, to_date=None, agents=None, gap=15, channel=None, **kwargs):
    require_module('ccvisit', tab=('convox',) if channel=='convox' else ('agent360','standalone'))
    start, end = getdate(from_date), getdate(to_date)
    if start > end or date_diff(end, start) > 92:
        frappe.throw('Choose an activity range of up to 93 days.')
    user = frappe.session.user
    manager = user == 'Administrator' or bool(set(frappe.get_roles()).intersection({'System Manager', 'Sales Manager', 'Call Center Export', 'CC Manager', 'COO'}))
    requested = json.loads(agents or '[]') if isinstance(agents, str) else agents or []
    if not isinstance(requested, list):
        frappe.throw('Choose a list of agents.')
    users = frappe.get_all('User', filters={} if manager else {'enabled': 1, 'name': user},
        fields=['name', 'full_name', 'custom_convox_agent_id'], limit_page_length=10000)
    allowed = {u.name: u for u in users if not requested or u.name in requested}
    dialer_map = {str(u.custom_convox_agent_id): u.name for u in allowed.values() if u.custom_convox_agent_id}
    events, warnings = [], []
    capped = False
    period = ['between', [str(start) + ' 00:00:00', str(end) + ' 23:59:59']]
    if dialer_map and frappe.db.exists('DocType', 'ConVox Call Event'):
        calls = frappe.get_all('ConVox Call Event', filters={'agent_id': ['in', list(dialer_map)], 'received_on': period, 'event_type': 'Call Status'},
            fields=['name','agent_id','call_reference','crm_lead','received_on','call_status','call_duration','disposition'], order_by='received_on asc', limit_page_length=30001)
        capped = len(calls) > 30000
        unique = {}
        for row in calls[:30000]:
            unique[(row.agent_id, row.call_reference or row.name)] = row
        for row in unique.values():
            answered = str(row.call_status or '').upper() in ('ANSWERED','CONNECTED')
            events.append(dict(agent=dialer_map[str(row.agent_id)], channel='convox', lead=row.crm_lead or '', at=str(row.received_on), status=row.call_status, disposition=row.disposition, answered=answered, talk=max(0, int(row.call_duration or 0)) if answered else 0))
    elif not dialer_map:
        warnings.append('No ConVox agent mapping is configured for the selected users.')
    if allowed and frappe.db.exists('DocType', 'LIFE Mobile Call Log'):
        calls = frappe.get_all('LIFE Mobile Call Log', filters={'agent': ['in', list(allowed)], 'started_on': period},
            fields=['name','agent','lead','started_on','call_status','talk_seconds','connected','disposition'], order_by='started_on asc', limit_page_length=30001)
        capped = capped or len(calls) > 30000
        for row in calls[:30000]:
            answered = str(row.call_status or '').lower() == 'answered' or row.connected == 'Connected'
            events.append(dict(agent=row.agent, channel='mobile', lead=row.lead or '', at=str(row.started_on), status=row.call_status, disposition=row.disposition, answered=answered, talk=max(0,int(row.talk_seconds or 0)) if answered else 0))
    updates = []
    timeline_available = date_diff(end, start) <= 6
    if timeline_available and allowed:
        versions = frappe.get_all('Version', filters={'ref_doctype':'Lead', 'owner':['in',list(allowed)], 'creation':period, 'data':['like','%custom_cc_sub_status%']},
            fields=['name','owner','docname','creation','data'], order_by='creation asc', limit_page_length=30001)
        capped = capped or len(versions) > 30000
        for version in versions[:30000]:
            try:
                changed = json.loads(version.data or '{}').get('changed', [])
            except (ValueError, TypeError):
                continue
            if any(item[0] == 'custom_cc_sub_status' for item in changed):
                updates.append(dict(agent=version.owner, channel='update', lead=version.docname, at=str(version.creation), status='Lead outcome updated', talk=0))
    if channel == "convox":
        events = [e for e in events if e["channel"] == "convox"]
        updates = []
    rows = aggregate(events, updates, max(1, min(120, int(gap))))
    # ERP outcomes belong to the activity tab as well, including agents who
    # have appointments but no calls in the period. Keep this read bounded.
    if channel != 'convox' and allowed:
        fields = ['lead_owner', 'custom_appointment_status']
        if frappe.get_meta('Lead').has_field('custom_visit_status'):
            fields.append('custom_visit_status')
        appointments = frappe.get_all('Lead', filters={'lead_owner': ['in', list(allowed)], 'custom_appointment_date_and_time': period},
            fields=fields, order_by='name asc', limit_page_length=10001)
        capped = capped or len(appointments) > 10000
        by_owner = {row['agent']: row for row in rows}
        for owner, counts in appointment_counts(appointments[:10000]).items():
            if owner not in by_owner:
                by_owner[owner] = dict(agent=owner, convox=0, mobile=0, answered=0, talk=0, updates=0,
                    idle_minutes=0, longest_gap=0, updated_no_call=0, talked_no_update=0, dispositions={}, events=[])
                rows.append(by_owner[owner])
            by_owner[owner].update(counts)
    appointment_leads = sorted({event.get('lead') for event in events if event.get('lead') and any(word in str(event.get('disposition') or '').lower() for word in ('appointment', 'appt', 'walk-in', 'walkin'))})
    appointment_state = {}
    for offset in range(0, len(appointment_leads), 500):
        lead_filters = {'name':['in',appointment_leads[offset:offset+500]], **({} if manager else {'lead_owner':user})}
        for lead in frappe.get_all('Lead', filters=lead_filters, fields=['name','custom_appointment_date_and_time','custom_cc_sub_status'], limit_page_length=500):
            appointment_state[lead.name] = bool(lead.custom_appointment_date_and_time or lead.custom_cc_sub_status == 'Appointment Booked')
    for row in rows:
        for key in ('appointments', 'walkins', 'booked'):
            row.setdefault(key, 0)
        row['appointment_without_booking'] = len({event.get('lead') for event in row['events'] if event.get('lead') in appointment_state and not appointment_state[event['lead']] and any(word in str(event.get('disposition') or '').lower() for word in ('appointment', 'appt', 'walk-in', 'walkin'))})
        row['name'] = allowed[row['agent']].full_name or row['agent']
        if not timeline_available:
            for key in ('idle_minutes','longest_gap','updated_no_call','talked_no_update'):
                row[key] = None
        # Timeline details are bounded and only available for ranges up to seven days.
        row['timeline_truncated'] = timeline_available and len(row['events']) > 1000
        row['events'] = row['events'][:1000] if timeline_available else []
    return dict(rows=rows, manager=manager, capped=capped, warnings=warnings, timeline_available=timeline_available, from_date=str(start), to_date=str(end))


@script_endpoint(allow_guest=False)
def changes(from_date=None, to_date=None, **kwargs):
    """Small change marker; refreshing the visible report remains an explicit action."""
    require_module('ccvisit')
    user = frappe.session.user
    manager = user == 'Administrator' or bool(set(frappe.get_roles()).intersection({'System Manager', 'Sales Manager', 'Call Center Export', 'CC Manager', 'COO'}))
    start, end = getdate(from_date), getdate(to_date)
    if start > end or date_diff(end, start) > 366:
        frappe.throw('Choose a valid report range of up to 367 days.')
    filters = {'custom_appointment_date_and_time':['between',[str(start)+' 00:00:00',str(end)+' 23:59:59']]}
    if not manager:
        filters['lead_owner'] = user
    result = frappe.get_all('Lead', filters=filters, fields=['max(modified) as last_modified','count(name) as count'])
    row = result[0] if result else {}
    return {'token': str(row.get('last_modified') or '') + '|' + str(row.get('count') or 0)}
