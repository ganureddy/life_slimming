from urllib.parse import quote

import frappe

no_cache = 1
sitemap = 0


def get_context(context):
    if frappe.session.user == "Guest" and frappe.request.path.rstrip("/") != "/life_portal/login":
        target = frappe.request.full_path.rstrip("?")
        frappe.local.flags.redirect_location = "/life_portal/login?redirect-to=" + quote(target, safe="")
        raise frappe.Redirect(http_status_code=302)
    context.no_cache = 1
