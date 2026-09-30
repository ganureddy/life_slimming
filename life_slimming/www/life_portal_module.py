"""Authenticated, local copies of the ERP portal's embedded pages."""

from functools import lru_cache

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote, urlencode

import frappe
from bs4 import BeautifulSoup
from frappe.sessions import get_csrf_token
from life_slimming.portal_access import require_module
from life_slimming.portal_chrome import prepare_chrome

no_cache = 1
sitemap = 0


def adapt_source(code, name):
    # These two pages declare a global lexical `$` DOM helper, shadowing jQuery
    # inside Frappe itself. Rename their helper, including inline event handlers.
    if name in {"accounts-command-center", "contols-command"}:
        code = code.replace("const $=id=>document.getElementById(id);",
                            "const portalElementById=id=>document.getElementById(id);")
        code = re.sub(r"(?<![\w.$])\$\s*\(", "portalElementById(", code)
    if name == "accounts-command-center":
        # The current source omits its old clock element but still updates it.
        code = code.replace('portalElementById("clk").textContent=',
                            'if (portalElementById("clk")) portalElementById("clk").textContent=')
    return code


@lru_cache(maxsize=64)
def prepared_source(path, modified_ns):
    """Cache only static page markup; file timestamps invalidate edited sources."""
    source = json.loads(Path(path).read_text())
    soup = BeautifulSoup(adapt_source(source["html"], source["name"]), "html.parser")
    scripts = []
    for script in soup.find_all("script"):
        scripts.append(str(script))
        script.decompose()
    for tag in soup.find_all(["html", "head", "body"]):
        tag.unwrap()
    for tag in soup.find_all("title"):
        tag.decompose()
    prepare_chrome(soup, source["name"])
    return source, str(soup), "\n".join(scripts)


def get_context(context):
    if frappe.session.user == "Guest":
        target = frappe.request.full_path.rstrip("?")
        frappe.local.flags.redirect_location = "/life_portal/login?redirect-to=" + quote(target, safe="")
        raise frappe.Redirect(http_status_code=302)

    root = Path(frappe.get_app_path("life_slimming"))
    manifest = json.loads((root / "portal_pages" / "manifest.json").read_text())
    module = frappe.form_dict.get("module", "")
    entry = manifest.get(module)
    if not entry or not entry.get("source"):
        raise frappe.DoesNotExistError("Portal page not found")
    allowed = require_module(module)
    if frappe.form_dict.get("embed") != "1":
        query = urlencode({key: value for key, value in frappe.form_dict.items() if key not in {"module", "embed"}})
        frappe.local.flags.redirect_location = "/life_portal/" + quote(module, safe="") + ("?" + query if query else "")
        raise frappe.Redirect(http_status_code=302)
    source_path = root / "portal_pages" / (entry["source"] + ".json")
    source, module_html, module_scripts = prepared_source(str(source_path), source_path.stat().st_mtime_ns)
    catalog = json.loads((root / "api" / "catalog.json").read_text())
    counts = Counter(item["legacy_method"] for item in catalog["endpoints"])
    # Do not silently choose between two APIs that share a legacy method name.
    methods = {item["legacy_method"]: item["method"] for item in catalog["endpoints"]
               if counts[item["legacy_method"]] == 1}
    routes = {}
    for key, item in manifest.items():
        if item.get("source") and key in allowed:
            routes.setdefault("/" + item["route"], key)
    routes["/" + entry["route"]] = module

    # These are reviewed, checked-in application sources, not user-supplied HTML.
    # Keep script order while loading the local Frappe runtime before page code.
    context.update({
        "no_cache": 1,
        "title": source["title"],
        "module_html": module_html,
        "module_css": source["css"],
        "module_scripts": module_scripts,
        "module_javascript": source["javascript"],
        "module_config": {
            "module": module, "methods": methods, "routes": routes,
            "cc_asset_version": hashlib.sha256(
                (root / "public/js/convox_cc_bridge.js").read_bytes() +
                (root / "public/js/cc_notifications.js").read_bytes()
            ).hexdigest()[:16] if module == "leads" else "",
            "csrf_token": get_csrf_token(),
            "user": frappe.session.user,
            "roles": frappe.get_roles(),
            "optional_read_access": {
                doctype: bool(frappe.has_permission(doctype, "read"))
                for doctype in ("Employee", "Attendance", "Duplicate Lead")
            } if module == "leads" else {},
        },
    })
