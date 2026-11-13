"""The module policy shared by portal navigation and embedded page requests."""
import json
from pathlib import Path

import frappe


def access_settings():
    # Apply the policy even when the user cannot edit the settings document.
    if frappe.db.exists("DocType", "Portal Access Settings"):
        try:
            value = json.loads(frappe.get_doc("Portal Access Settings").get("access_config") or "null")
            return value if isinstance(value, dict) else None
        except (ValueError, TypeError):
            pass
    return None


def allowed_modules(user, roles, portal_role, settings):
    if not user or user == "Guest":
        return []
    policy = json.loads((Path(__file__).parent / "portal_pages/access.json").read_text())
    key = "IT" if user == "Administrator" or "System Manager" in roles else next(
        (key for key, label in policy["labels"].items() if portal_role in (key, label)), ""
    )
    config = (settings or {}).get(key)
    allowed = []
    for group in policy["menu"]:
        for item in group["items"]:
            module = item["id"]
            if module == "home":
                visible = True
            elif isinstance(config, dict):
                show, hide, groups = (config.get(field) for field in ("show", "hide", "groups"))
                visible = (
                    True if isinstance(show, list) and module in show else
                    False if isinstance(hide, list) and module in hide else
                    groups == "ALL" or isinstance(groups, list) and group["label"] in groups
                )
            else:
                visible = key in ("IT", "MD") or group["label"] in policy["group_roles"].get(key, [])
            if visible:
                allowed.append(module)
    allowed.extend(module for module, entry in policy["children"].items() if entry["parent"] in allowed)
    return allowed


def allowed_tabs(user, roles, portal_role, settings, module):
    if module not in allowed_modules(user, roles, portal_role, settings):
        return []
    policy = json.loads((Path(__file__).parent / "portal_pages/access.json").read_text())
    key = "IT" if user == "Administrator" or "System Manager" in roles else next(
        (key for key,label in policy["labels"].items() if portal_role in (key,label)), "")
    config = (settings or {}).get(key) or {}
    tab_config = config.get("tab_access") if isinstance(config, dict) else None
    rules = tab_config.get(module, {}) if isinstance(tab_config, dict) else {}
    rules = rules if isinstance(rules, dict) else {}
    entries = {entry['id']:entry for entry in policy.get('tabs', {}).get(module, [])}
    def permitted(tab, seen=()):
        entry = entries.get(tab)
        if not entry or tab in seen or rules.get(tab) is False:
            return False
        return not entry.get('parent') or permitted(entry['parent'], (*seen,tab))
    return [tab for tab in entries if permitted(tab)]


def require_module(module, tab=None):
    user = frappe.get_doc("User", frappe.session.user)
    roles, settings = frappe.get_roles(user.name), access_settings()
    allowed = allowed_modules(user.name, roles, user.get("custom_portal_role") or "", settings)
    if module not in allowed:
        raise frappe.PermissionError("This module is not enabled for your portal role.")
    if tab is not None:
        tabs = allowed_tabs(user.name, roles, user.get("custom_portal_role") or "", settings, module)
        required = [tab] if isinstance(tab, str) else tab
        if not any(value in tabs for value in required):
            raise frappe.PermissionError("This tab is not enabled for your portal role.")
    return allowed
