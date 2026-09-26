"""Shared request binding for native ERP API modules; no dynamic script execution."""
from functools import wraps

import frappe
from frappe.rate_limiter import rate_limit


def script_endpoint(*, allow_guest=False, rate_count=None, rate_seconds=86400):
    def decorate(function):
        @wraps(function)
        def handler(**kwargs):
            if not allow_guest and frappe.session.user == "Guest":
                raise frappe.PermissionError
            previous = frappe.local.form_dict
            frappe.local.form_dict = frappe._dict(previous or {})
            frappe.local.form_dict.update(kwargs)
            try:
                return function(**kwargs)
            finally:
                frappe.local.form_dict = previous

        if rate_count:
            handler = rate_limit(limit=rate_count, seconds=rate_seconds)(handler)
        return frappe.whitelist(allow_guest=allow_guest, methods=["POST"])(handler)
    return decorate
