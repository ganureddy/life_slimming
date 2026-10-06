import frappe


def pd_form_attachment_fields():
    try:
        meta = frappe.get_meta("PD Form")
        return [
            field.fieldname
            for field in meta.fields
            if field.fieldtype in ("Attach", "Attach Image")
        ]
    except Exception:
        return ["pd_form"]


def pd_form_child_urls(patient_name):
    urls = []
    fields = pd_form_attachment_fields()
    if not fields or not patient_name:
        return urls
    try:
        rows = frappe.get_all(
            "PD Form",
            filters={
                "parent": patient_name,
                "parenttype": "Patient",
                "parentfield": "custom_pd_form",
            },
            fields=["name"] + fields,
            order_by="idx asc",
            ignore_permissions=True,
            limit_page_length=0,
        )
    except Exception:
        return urls
    for row in rows:
        for field in fields:
            value = row.get(field)
            if value and value not in urls:
                urls.append(value)
    return urls


def pd_form_child_urls_by_patient(patient_names):
    result = {}
    fields = pd_form_attachment_fields()
    if not fields or not patient_names:
        return result
    try:
        rows = frappe.get_all(
            "PD Form",
            filters={
                "parent": ["in", patient_names],
                "parenttype": "Patient",
                "parentfield": "custom_pd_form",
            },
            fields=["parent", "name"] + fields,
            order_by="parent asc, idx asc",
            ignore_permissions=True,
            limit_page_length=0,
        )
    except Exception:
        return result
    for row in rows:
        patient_name = row.get("parent")
        urls = result.setdefault(patient_name, [])
        for field in fields:
            value = row.get(field)
            if value and value not in urls:
                urls.append(value)
    return result


def pd_form_file_urls(patient_name):
    urls = []
    if not patient_name:
        return urls
    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Patient", "attached_to_name": patient_name},
        fields=["file_url", "attached_to_field", "file_name", "thumbnail_url", "creation"],
        order_by="creation asc",
        ignore_permissions=True,
        limit_page_length=0,
    )
    for row in files:
        field = (row.get("attached_to_field") or "").lower()
        url = row.get("file_url") or ""
        if url and (not field or "pd_form" in field) and url not in urls:
            urls.append(url)
    return urls


def pd_form_urls(patient_name, patient_doc=None):
    urls = pd_form_child_urls(patient_name)
    if patient_doc:
        for row in patient_doc.get("custom_pd_form") or []:
            for field in pd_form_attachment_fields():
                value = row.get(field)
                if value and value not in urls:
                    urls.append(value)
    for url in pd_form_file_urls(patient_name):
        if url not in urls:
            urls.append(url)
    return urls
