"""Native replacement for the live ``life_item_master_control`` Server Script.

This preserves the live endpoint's init/save contract while keeping all writes
behind Stock Manager/System Manager authorization and strict field allowlists.
"""

import json

import frappe
from frappe.utils import now

from life_slimming.api._runtime import script_endpoint


SETTINGS_DOCTYPE = "LIFE Stock Request Settings"
HO_WAREHOUSE = "Stores - LSACPL"
THERAPY_TABLES = (
    "custom_consumed_items_details",
    "custom_supporting_materials",
    "custom_main_treatment_consumables",
)
ITEM_FIELDS = (
    "custom_main_category",
    "custom_stock_type",
    "custom_material_role",
    "item_group",
    "disabled",
    "safety_stock",
    "lead_time_days",
    "custom_issue_pack_to_branch",
    "custom_units_per_issue_pack",
)
STOCK_TYPES = ("", "Monthly (Gen) Stock", "Consumable (Spl) Stock", "Non Stock", "Equipment")
MATERIAL_ROLES = ("", "MAIN TREATMENT", "SUPPORTING")
REQUEST_USES = ("", "M", "C", "B")


def _json(value, default):
    if value in (None, ""):
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _can_edit():
    user = frappe.session.user
    return user == "Administrator" or bool(
        frappe.db.exists(
            "Has Role",
            {"parent": user, "parenttype": "User", "role": ["in", ["Stock Manager", "System Manager"]]},
        )
    )


def _user_name():
    return frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user


def _timestamp():
    return str(now())[:16].replace(" ", "T")


def _branches():
    rows = frappe.get_all(
        "Warehouse",
        filters=[["name", "like", "% Main Store - LSACPL"], ["disabled", "=", 0]],
        pluck="name",
        order_by="name asc",
    )
    return [name.replace(" Main Store - LSACPL", "").strip() for name in rows]


def _settings():
    meta = frappe.get_meta(SETTINGS_DOCTYPE)
    rules = frappe.db.get_single_value(SETTINGS_DOCTYPE, "item_request_rules") if meta.has_field("item_request_rules") else "{}"
    imr = frappe.db.get_single_value(SETTINGS_DOCTYPE, "item_master_rules") if meta.has_field("item_master_rules") else "{}"
    return {
        "rules": _json(rules, {}) or {},
        "imr": _json(imr, {}) or {},
    }


def _item_rows(codes=None):
    filters = [["is_stock_item", "=", 1], ["item_group", "not in", ["ASSETS", "Services"]]]
    if codes:
        filters = [["name", "in", codes]]
    return frappe.get_all(
        "Item",
        filters=filters,
        fields=["name", "item_name", "stock_uom", "allow_alternative_item", *ITEM_FIELDS],
        order_by="item_name asc",
        limit_page_length=0,
    )


def _usage(codes=None):
    filters = {"parenttype": "Therapy Type"}
    if codes:
        filters["item_name"] = ["in", codes]
    rows = frappe.get_all(
        "Consumed Items Details",
        filters=filters,
        fields=["name", "parent", "parentfield", "item_name", "required_quantity"],
        limit_page_length=0,
    )
    return [
        {"row": r.name, "tt": r.parent, "table": r.parentfield, "item": r.item_name, "qty": r.required_quantity or ""}
        for r in rows
        if r.parentfield in THERAPY_TABLES
    ]


def _alternatives(codes=None):
    filters = {"item_code": ["in", codes]} if codes else {}
    return [
        {"name": r.name, "item": r.item_code, "alt": r.alternative_item_code, "two_way": r.two_way or 0}
        for r in frappe.get_all(
            "Item Alternative",
            filters=filters,
            fields=["name", "item_code", "alternative_item_code", "two_way"],
            limit_page_length=0,
        )
    ]


def _number(value, label, integer=False):
    try:
        result = float(value if value not in (None, "") else 0)
    except (TypeError, ValueError):
        frappe.throw(f"{label} must be a number 0 or above")
    if result < 0:
        frappe.throw(f"{label} must be a number 0 or above")
    return int(result) if integer else result


def _save_fields(code, values, categories, groups):
    doc = frappe.get_doc("Item", code)
    changed = []
    for field, value in (values or {}).items():
        if field not in ITEM_FIELDS:
            continue
        if field == "custom_main_category" and value and value not in categories:
            frappe.throw(f"{code}: unknown category {value}")
        if field == "custom_stock_type" and (value or "") not in STOCK_TYPES:
            frappe.throw(f"{code}: unknown stock type {value}")
        if field == "custom_material_role" and (value or "") not in MATERIAL_ROLES:
            frappe.throw(f"{code}: unknown material role {value}")
        if field == "item_group" and value not in groups:
            frappe.throw(f"{code}: unknown item group {value}")
        if field in ("safety_stock", "custom_units_per_issue_pack"):
            value = _number(value, field)
        elif field == "lead_time_days":
            value = _number(value, "lead time", integer=True)
        elif field == "disabled":
            value = int(value in (1, "1", True, "true"))
        if str(doc.get(field) or "") != str(value or ""):
            doc.set(field, value)
            changed.append(field)
    if changed:
        doc.flags.ignore_permissions = True
        doc.save()
    return changed


def _save_alternatives(code, requested):
    wanted = []
    for alt in requested or []:
        alt = str(alt or "").strip()
        if alt and alt != code and alt not in wanted:
            if not frappe.db.exists("Item", alt):
                frappe.throw(f"{code}: alternative item not found: {alt}")
            wanted.append(alt)
    existing = {r.alternative_item_code: r.name for r in frappe.get_all(
        "Item Alternative", filters={"item_code": code}, fields=["name", "alternative_item_code"]
    )}
    for alt in wanted:
        if alt not in existing:
            doc = frappe.get_doc({"doctype": "Item Alternative", "item_code": code, "alternative_item_code": alt, "two_way": 1})
            doc.flags.ignore_permissions = True
            doc.insert()
    for alt, name in existing.items():
        if alt not in wanted:
            frappe.delete_doc("Item Alternative", name, ignore_permissions=True)
    flag = int(bool(wanted))
    if int(frappe.db.get_value("Item", code, "allow_alternative_item") or 0) != flag:
        frappe.db.set_value("Item", code, "allow_alternative_item", flag)


def _save_therapies(code, requested, valid_therapies):
    wanted = {}
    for row in requested or []:
        therapy = str(row.get("tt") or "").strip()
        table = str(row.get("table") or THERAPY_TABLES[0])
        if therapy not in valid_therapies:
            frappe.throw(f"{code}: therapy type not found: {therapy}")
        if table not in THERAPY_TABLES:
            frappe.throw(f"{code}: unknown table {table}")
        qty = _number(row.get("qty"), "per-session qty")
        if qty <= 0 or qty > 100000:
            frappe.throw(f"{code} in {therapy}: per-session qty must be above 0")
        wanted[(therapy, table)] = str(int(qty)) if qty.is_integer() else ("%.4f" % qty).rstrip("0").rstrip(".")
    touched = set(valid_therapies)
    for therapy in touched:
        doc = frappe.get_doc("Therapy Type", therapy)
        changed = False
        for table in THERAPY_TABLES:
            target = wanted.get((therapy, table))
            kept, found = [], False
            for row in doc.get(table) or []:
                if row.item_name != code:
                    kept.append(row)
                elif target and not found:
                    row.required_quantity = target
                    kept.append(row)
                    found = True
                else:
                    changed = True
            if target and not found:
                kept.append({"item_name": code, "required_quantity": target})
                changed = True
            doc.set(table, kept)
        if changed:
            doc.flags.ignore_permissions = True
            doc.save()


def _log(message):
    try:
        if not frappe.get_meta(SETTINGS_DOCTYPE).has_field("control_log"):
            return
        entries = _json(frappe.db.get_single_value(SETTINGS_DOCTYPE, "control_log"), [])
        entries = entries if isinstance(entries, list) else []
        entries.insert(0, {"at": _timestamp(), "by": _user_name(), "what": message})
        frappe.db.set_value(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE, "control_log", json.dumps(entries[:400]))
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Stock item control log")


def _init_response():
    settings = _settings()
    ho = {r.item_code: r.actual_qty for r in frappe.get_all(
        "Bin", filters={"warehouse": HO_WAREHOUSE}, fields=["item_code", "actual_qty"], limit_page_length=0
    )}
    therapies = frappe.get_all("Therapy Type", fields=["name", "disabled"], order_by="name asc", limit_page_length=0)
    meta = frappe.get_meta(SETTINGS_DOCTYPE)
    control_log = _json(
        frappe.db.get_single_value(SETTINGS_DOCTYPE, "control_log") if meta.has_field("control_log") else "[]",
        [],
    )
    return {
        "can_edit": _can_edit(), "items": _item_rows(), "usage": _usage(), "alts": _alternatives(),
        "rules": settings["rules"], "imr": settings["imr"],
        "categories": frappe.get_all("Therapy Main Category", pluck="name", order_by="name asc"),
        "groups": frappe.get_all("Item Group", pluck="name", order_by="name asc"),
        "stock_types": list(STOCK_TYPES[1:]), "roles": list(MATERIAL_ROLES[1:]),
        "branches": _branches(), "ho": ho,
        "therapies": [{"name": r.name, "disabled": r.disabled or 0} for r in therapies],
        "control_log": control_log if isinstance(control_log, list) else [],
    }


@script_endpoint(allow_guest=False)
def run(**kwargs):
    action = kwargs.get("action") or frappe.form_dict.get("action") or "init"
    if action == "init":
        return _init_response()
    if action not in ("save", "bulk"):
        frappe.throw("Unknown action")
    if not _can_edit():
        frappe.throw("Only Stock Manager or System Manager can change item settings.")
    settings_meta = frappe.get_meta(SETTINGS_DOCTYPE)
    missing = [field for field in ("item_request_rules", "item_master_rules") if not settings_meta.has_field(field)]
    if missing:
        frappe.throw("Stock Request Settings is not migrated. Missing fields: " + ", ".join(missing))
    payload = _json(kwargs.get("items") or frappe.form_dict.get("items"), None)
    if not isinstance(payload, list) or not payload:
        frappe.throw("Nothing to save.")
    if len(payload) > 500:
        frappe.throw("Save at most 500 items at a time.")

    branches = _branches()
    categories = set(frappe.get_all("Therapy Main Category", pluck="name"))
    groups = set(frappe.get_all("Item Group", pluck="name"))
    therapies = set(frappe.get_all("Therapy Type", pluck="name"))
    settings = _settings()
    rules, imr, saved_codes, notes = settings["rules"], settings["imr"], [], []
    for entry in payload:
        code = str(entry.get("item") or "").strip()
        if not code:
            continue
        if not frappe.db.exists("Item", code):
            frappe.throw(f"Item not found: {code}")
        changes = _save_fields(code, entry.get("fields"), categories, groups)
        if "alternatives" in entry:
            _save_alternatives(code, entry.get("alternatives"))
            changes.append("alternatives")
        if "therapies" in entry:
            _save_therapies(code, entry.get("therapies"), therapies)
            changes.append("therapies")
        if "req" in entry:
            request_use = str(entry.get("req") or "")
            if request_use not in REQUEST_USES:
                frappe.throw(f"{code}: unknown request use {request_use}")
            if request_use:
                item = frappe.db.get_value("Item", code, ["item_name", "stock_uom", "item_group"], as_dict=True)
                imr[code] = {"req": request_use, "nm": item.item_name, "uom": item.stock_uom, "grp": item.item_group, "by": _user_name(), "at": _timestamp()}
            else:
                imr.pop(code, None)
            changes.append("request use")
        if "blocked" in entry:
            blocked = entry.get("blocked")
            if blocked == "all":
                rules[code] = {"all": True, "by": _user_name(), "at": _timestamp()}
            elif isinstance(blocked, list) and blocked:
                unknown = sorted(set(blocked) - set(branches))
                if unknown:
                    frappe.throw(f"{code}: unknown branch {', '.join(unknown)}")
                rules[code] = {"branches": sorted(set(blocked)), "by": _user_name(), "at": _timestamp()}
            else:
                rules.pop(code, None)
            changes.append("branch access")
        saved_codes.append(code)
        if changes:
            notes.append(f"{code} ({'; '.join(changes)})")

    frappe.db.set_value(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE, "item_request_rules", json.dumps(rules))
    frappe.db.set_value(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE, "item_master_rules", json.dumps(imr))
    if notes:
        _log(f"Item master · {len(notes)} item(s): {' | '.join(notes)[:900]}")
    return {"saved": len(notes), "notes": notes, "items": _item_rows(saved_codes), "usage": _usage(saved_codes), "alts": _alternatives(saved_codes), "rules": rules, "imr": imr}
