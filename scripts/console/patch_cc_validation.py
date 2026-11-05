"""Run in the target site's bench console; preview first, then apply=True.

Does not select or disable either duplicate API registration.
"""
import json
from pathlib import Path

import frappe


def patch_cc_validation(payload_path, apply=False):
    entries = json.loads(Path(payload_path).read_text())
    documents = []
    for entry in entries:
        doc = frappe.get_doc("Server Script", entry["name"])
        if doc.script == entry["script"]:
            continue
        if str(doc.modified) != entry["expected_modified"] or doc.script != entry["original_script"]:
            raise RuntimeError("Server Script changed; review again: " + entry["name"])
        compile(entry["script"], entry["name"], "exec")
        documents.append((doc, entry))
    names = [doc.name for doc, _ in documents]
    if not apply:
        return {"preview": names, "writes": 0}
    # Frappe commits this transaction only after both documents save successfully.
    try:
        for doc, entry in documents:
            doc.script = entry["script"]
            doc.save()
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise
    return {"updated": names}


def patch_mobile_call_page(payload_path, apply=False):
    entry = json.loads(Path(payload_path).read_text())
    doc = frappe.get_doc("Web Page", entry["name"])
    source = doc.javascript
    if all(change["new"] in source for change in entry["changes"]):
        return {"updated": [], "already_applied": True}
    if str(doc.modified) != entry["expected_modified"]:
        raise RuntimeError("Mobile page changed; review again before applying")
    for change in entry["changes"]:
        if source.count(change["old"]) != 1:
            raise RuntimeError("Mobile page no longer matches the reviewed source")
        source = source.replace(change["old"], change["new"], 1)
    if not apply:
        return {"preview": doc.name, "replacements": len(entry["changes"]), "writes": 0}
    try:
        doc.javascript = source
        doc.save()
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise
    return {"updated": [doc.name]}
