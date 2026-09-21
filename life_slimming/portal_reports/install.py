"""Explicit, repeatable local installation of the original referral report."""

import json
from pathlib import Path

import frappe


def referral_report():
    source = json.loads(Path(__file__).with_name("referral_report_fixed.json").read_text())
    name = source["report_name"]
    if frappe.db.exists("Report", name):
        report = frappe.get_doc("Report", name)
        if report.query != source["query"]:
            frappe.throw("A different report already exists; refusing to overwrite it.")
        return {"name": name, "created": False}

    fields = (
        "report_name", "ref_doctype", "reference_report", "is_standard", "module",
        "report_type", "add_total_row", "disabled", "prepared_report",
        "add_translate_data", "timeout", "query", "report_script", "javascript", "json",
    )
    report = frappe.get_doc({"doctype": "Report", **{key: source.get(key) for key in fields}})
    for row in source["filters"]:
        report.append("filters", {key: row.get(key) for key in (
            "label", "fieldtype", "fieldname", "mandatory", "wildcard_filter", "options", "default",
        )})
    for row in source["roles"]:
        report.append("roles", {"role": row["role"]})
    report.insert()
    return {"name": name, "created": True}
