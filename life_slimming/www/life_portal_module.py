"""Authenticated, local copies of the ERP portal's embedded pages."""

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

import frappe
from bs4 import BeautifulSoup
from frappe.sessions import get_csrf_token

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
    source = json.loads((root / "portal_pages" / (entry["source"] + ".json")).read_text())
    catalog = json.loads((root / "api" / "catalog.json").read_text())
    counts = Counter(item["legacy_method"] for item in catalog["endpoints"])
    # Do not silently choose between two APIs that share a legacy method name.
    methods = {item["legacy_method"]: item["method"] for item in catalog["endpoints"]
               if counts[item["legacy_method"]] == 1}
    routes = {"/" + item["route"]: key for key, item in manifest.items() if item.get("source")}

    # These are reviewed, checked-in application sources, not user-supplied HTML.
    # Keep script order while loading the local Frappe runtime before page code.
    soup = BeautifulSoup(adapt_source(source["html"], source["name"]), "html.parser")
    scripts = []
    for script in soup.find_all("script"):
        scripts.append(str(script))
        script.decompose()
    for tag in soup.find_all(["html", "head", "body"]):
        tag.unwrap()
    for tag in soup.find_all("title"):
        tag.decompose()
    context.update({
        "no_cache": 1,
        "title": source["title"],
        "module_html": str(soup),
        "module_css": source["css"],
        "module_scripts": "\n".join(scripts),
        "module_javascript": source["javascript"],
        "module_config": {
            "methods": methods, "routes": routes,
            "csrf_token": get_csrf_token(),
            "user": frappe.session.user,
        },
    })
