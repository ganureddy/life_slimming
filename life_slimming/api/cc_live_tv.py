"""Read-only CC TV snapshot, with the same owner scope as the CC lead queue.

Leads are counted by creation date. Bookings and visits are counted by the
lead's scheduled appointment date (one current appointment per lead).
"""
from datetime import timedelta

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
    month_start = now.date().replace(day=6)
    if now.day < 6:
        month_start = (month_start.replace(day=1) - timedelta(days=1)).replace(day=6)
    month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=6)
    week_start = now.date() - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)
    since = str(min(month_start, week_start))
    fields = ['name', 'lead_name', 'lead_owner', 'creation', 'modified',
              'branch', 'lead_assign_to_branch', 'source', 'enquired_for',
              'custom_appointment_date_and_time', 'custom_appointment_status',
              'custom_visit_status', 'status', 'custom_call_count', 'custom_last_call_time']
    meta = frappe.get_meta('Lead')
    fields = [field for field in fields if field in {'name', 'creation', 'modified'} or meta.has_field(field)]
    if 'custom_appointment_date_and_time' not in fields:
        raise frappe.ValidationError('CC appointment fields are not installed.')
    # Deliberately not paginated: never silently truncate the leaderboard.
    rows = frappe.get_all('Lead', fields=fields,
        filters={'lead_owner': user} if scoped else {},
        or_filters=[['creation', '>=', since], ['modified', '>=', since],
                    ['custom_appointment_date_and_time', '>=', since]],
        order_by='creation asc, name asc', limit_page_length=0)
    owners = sorted({row.lead_owner for row in rows if row.get('lead_owner')})
    # Read enabled state on every poll so disabling a user takes effect immediately.
    users = frappe.get_all('User', filters={'name': ['in', owners], 'enabled': 1},
        fields=['name', 'full_name', 'user_image'], limit_page_length=0) if owners else []
    agents = {user.name: user.full_name or user.name for user in users}
    agent_images = {user.name: user.user_image or '' for user in users}
    return dict(rows=rows, agents=agents, agent_images=agent_images, today=str(now.date()),
                month_start=str(month_start), month_end=str(month_end),
                week_start=str(week_start), week_end=str(week_end),
                timestamp=str(now), timezone=get_system_timezone(), restricted_to_owner=bool(scoped))
