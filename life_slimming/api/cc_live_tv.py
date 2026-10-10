"""Read-only CC TV snapshot, with the same owner scope as the CC lead queue.

Leads are counted by creation date. Bookings and visits are counted by the
lead's scheduled appointment date (one current appointment per lead).
"""
import frappe
from frappe.utils import now_datetime, get_system_timezone
from life_slimming.portal_access import require_module


@frappe.whitelist()
def snapshot():
    user = frappe.session.user
    if not user or user == 'Guest':
        raise frappe.AuthenticationError('Sign in to view CC TV.')
    require_module('leads')
    roles = set(frappe.get_roles(user))
    managers = {'System Manager', 'Sales Manager', 'Call Center Export'}
    if user != 'Administrator' and not roles.intersection(managers | {'Sales User', 'Branch Sales Invoice'}):
        raise frappe.PermissionError('CC access is required.')
    scoped = user != 'Administrator' and not roles.intersection(managers)
    now = now_datetime()
    month = str(now.date().replace(day=1))
    fields = ['name', 'lead_name', 'lead_owner', 'creation', 'modified',
              'branch', 'lead_assign_to_branch', 'source', 'enquired_for',
              'custom_appointment_date_and_time', 'custom_appointment_status',
              'custom_visit_status', 'status']
    meta = frappe.get_meta('Lead')
    fields = [field for field in fields if field in {'name', 'creation', 'modified'} or meta.has_field(field)]
    if 'custom_appointment_date_and_time' not in fields:
        raise frappe.ValidationError('CC appointment fields are not installed.')
    # Deliberately not paginated: never silently truncate the leaderboard.
    rows = frappe.get_all('Lead', fields=fields,
        filters={'lead_owner': user} if scoped else {},
        or_filters=[['creation', '>=', month], ['modified', '>=', month],
                    ['custom_appointment_date_and_time', '>=', month]],
        order_by='creation asc, name asc', limit_page_length=0)
    owners = sorted({row.lead_owner for row in rows if row.get('lead_owner')})
    agents = {owner: frappe.get_cached_value('User', owner, 'full_name') or owner for owner in owners}
    agent_images = {owner: frappe.get_cached_value('User', owner, 'user_image') or '' for owner in owners}
    return dict(rows=rows, agents=agents, agent_images=agent_images, today=str(now.date()),
                timestamp=str(now), timezone=get_system_timezone(), restricted_to_owner=bool(scoped))
