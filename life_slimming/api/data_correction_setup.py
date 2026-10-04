"""Install missing Data Correction schemas without replacing site customizations."""
import json
from pathlib import Path

import frappe


def execute():
    path = Path(frappe.get_app_path("life_slimming")) / "data_correction/doctypes.json"
    for definition in json.loads(path.read_text()):
        name = definition["name"]
        if not frappe.db.exists("DocType", name):
            frappe.get_doc(definition).insert(ignore_permissions=True)
            continue
        doc = frappe.get_doc("DocType", name)
        existing = {field.fieldname for field in doc.fields}
        missing = [field for field in definition["fields"] if field["fieldname"] not in existing]
        if missing:
            for field in missing:
                doc.append("fields", field)
            doc.save(ignore_permissions=True)
