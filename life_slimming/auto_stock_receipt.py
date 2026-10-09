# LIFE: 24-hour automatic branch stock receipt
# Install in apps/life_slimming/life_slimming/auto_stock_receipt.py
# bench --site portal.lifescc.com execute life_slimming.auto_stock_receipt.install

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.model.workflow import apply_workflow, get_transitions

METHOD = "life_slimming.auto_stock_receipt.run"
PENDING = "Pending Receipt (Sub WH)"
ADJUSTMENT = "LIFE Stock Receipt Adjustment Request"
MARKER = "LIFE_AUTO_STOCK_RECEIPT_24H_V1"


def run():
    """Scheduler entry point. Each transfer commits independently."""
    previous_user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        cutoff = add_to_date(now_datetime(), hours=-24)
        names = frappe.get_all(
            "Stock Entry",
            filters={"docstatus": 0, "purpose": "Material Transfer",
                     "workflow_state": PENDING,
                     "custom_stock_release_date": ["<=", cutoff]},
            pluck="name", order_by="custom_stock_release_date asc, name asc",
            limit_page_length=0,
        )
        for name in names:
            try:
                _receive(name)
                frappe.db.commit()
            except Exception:
                frappe.db.rollback()
                frappe.log_error(frappe.get_traceback(), "Auto stock receipt: " + name)
    finally:
        frappe.set_user(previous_user)


def _receive(name):
    # Lock the original document; reload and recheck after acquiring the lock.
    frappe.db.sql("select name from `tabStock Entry` where name=%s for update", (name,))
    doc = frappe.get_doc("Stock Entry", name)
    released = doc.get("custom_stock_release_date")
    if (doc.docstatus != 0 or doc.get("workflow_state") != PENDING
            or doc.purpose != "Material Transfer" or not released
            or doc.get("custom_received_date") or doc.get("custom_received_by")
            or doc.get("custom_auto_received")):
        return
    if now_datetime() < add_to_date(get_datetime(released), hours=24):
        return
    # Any non-cancelled discrepancy request needs human review, even if rejected.
    if frappe.db.exists("DocType", ADJUSTMENT) and frappe.db.exists(
        ADJUSTMENT, {"stock_entry": name, "docstatus": ["!=", 2]}
    ):
        return
    if not doc.items or not all(row.s_warehouse and row.t_warehouse for row in doc.items):
        frappe.throw("Source or target warehouse is missing; auto receipt skipped.")
    if any(float(row.get("custom_received_qty") or 0) != 0 for row in doc.items):
        # A saved partial receipt must not silently become a full receipt.
        return
    workflows = frappe.get_all("Workflow", filters={"document_type": "Stock Entry", "is_active": 1}, pluck="name")
    if len(workflows) != 1:
        frappe.throw("Exactly one active Stock Entry workflow is required.")
    workflow = frappe.get_doc("Workflow", workflows[0])
    submitted_states = {row.state for row in workflow.states if int(row.doc_status) == 1}
    transitions = get_transitions(doc, workflow)
    actions = [row for row in transitions if row.next_state in submitted_states]
    if not actions:
        frappe.throw("No permitted workflow action submits this receipt.")
    preferred = [row for row in actions if any(word in row.action.lower() for word in ("receive", "receipt", "confirm", "approve"))]
    action = (preferred or actions)[0].action
    stamp = now_datetime()
    note = "Auto-received after 24 hours. Full released quantity assumed received; no branch confirmation."
    for row in doc.items:
        row.custom_received_qty = row.qty
    doc.custom_auto_received = 1
    doc.custom_auto_received_on = stamp
    doc.custom_received_date = stamp
    # Do not attribute an automatic receipt to a branch employee.
    doc.custom_branch_receipt_remarks = "\n".join(filter(None, [doc.get("custom_branch_receipt_remarks"), note]))
    doc.save(ignore_permissions=True)
    apply_workflow(doc, action)
    doc.reload()
    if doc.docstatus != 1:
        frappe.throw("Receipt workflow did not submit the Stock Entry.")
    requests = {row.material_request for row in doc.items if row.material_request}
    for request_name in requests:
        meta = frappe.get_meta("Material Request")
        values = {}
        for field in ("custom_stock_request_status", "transfer_status"):
            if meta.has_field(field):
                values[field] = "Completed"
        if values:
            frappe.db.set_value("Material Request", request_name, values)
    doc.add_comment("Info", note + " Posted at " + str(stamp))


ALERT_JS = r'''
function lifeAutoReceiptAlert24h() {
    var box = document.getElementById('life-auto-receipt-alert');
    if (!box) {
        box = document.createElement('div');
        box.id = 'life-auto-receipt-alert';
        box.style.cssText = 'position:fixed;bottom:18px;left:18px;right:18px;z-index:950;background:#fff7ed;border:2px solid #d97706;border-radius:10px;padding:12px 16px;color:#92400e;box-shadow:0 4px 18px #0002;font-size:14px';
        document.body.appendChild(box);
    }
    var rows = state.currentView === 'branch' && Array.isArray(state.branchReceivingRows) ? state.branchReceivingRows : [];
    var pending = rows.filter(function(row) {
        return Number(row.docstatus) === 0 && row.custom_stock_release_date && !row.custom_received_date;
    });
    box.style.display = pending.length ? 'block' : 'none';
    if (!pending.length) return;
    var messages = pending.map(function(row) {
        // Frappe timestamps use the site's timezone (India); avoid browser timezone drift.
        var raw = String(row.custom_stock_release_date).replace(' ', 'T');
        if (!/[zZ]$|[+-]\d\d:\d\d$/.test(raw)) raw += '+05:30';
        var deadline = Date.parse(raw) + 24 * 60 * 60 * 1000;
        var remaining = deadline - Date.now();
        var label = remaining > 0 ? Math.ceil(remaining / 3600000) + ' hour(s) remaining' : '24 hours elapsed; awaiting automatic posting or adjustment review';
        return escapeHtml(row.name) + ': ' + label;
    });
    box.innerHTML = '<strong>Pending stock receipt (' + pending.length + ')</strong> — Confirm receipt or report missing/damaged items in Branch Stock-Receipt before 24 hours.<br>' + messages.slice(0,4).join('<br>') + (messages.length > 4 ? '<br>More pending receipts: ' + (messages.length-4) : '');
}
setInterval(lifeAutoReceiptAlert24h, 60000);
'''


def install():
    """Idempotent install; does not post stock immediately."""
    frappe.only_for("System Manager")
    page = frappe.get_doc("Web Page", "stock-dashboard")
    js = page.javascript or ""
    anchor = "function renderBranchReceivingTable(){"
    if MARKER not in js and js.count(anchor) != 1:
        frappe.throw("Stock dashboard receipt function does not match. Nothing changed.")
    required = ["custom_stock_release_date", "custom_received_date", "custom_received_by", "custom_branch_receipt_remarks"]
    for field in required:
        if not frappe.get_meta("Stock Entry").has_field(field):
            frappe.throw("Required field missing: Stock Entry." + field)
    if not frappe.get_meta("Stock Entry Detail").has_field("custom_received_qty"):
        frappe.throw("Required field missing: Stock Entry Detail.custom_received_qty")
    create_custom_fields({"Stock Entry": [
        {"fieldname": "custom_auto_received", "label": "Auto-received after 24 hours", "fieldtype": "Check", "read_only": 1, "insert_after": "custom_received_date"},
        {"fieldname": "custom_auto_received_on", "label": "Auto-received On", "fieldtype": "Datetime", "read_only": 1, "insert_after": "custom_auto_received"},
    ]})
    if MARKER not in js:
        page.javascript = js.replace(anchor, "// " + MARKER + "\n" + ALERT_JS + "\n" + anchor + "\nlifeAutoReceiptAlert24h();", 1)
        page.save()
    name = frappe.db.get_value("Scheduled Job Type", {"method": METHOD}, "name")
    job = frappe.get_doc("Scheduled Job Type", name) if name else frappe.new_doc("Scheduled Job Type")
    job.method = METHOD
    job.frequency = "Cron"
    job.cron_format = "*/5 * * * *"
    job.stopped = 0
    job.save(ignore_permissions=True)
    frappe.db.commit()
    return "Installed: branch alerts and 24-hour auto receipt. Existing overdue pending receipts qualify. Scheduler must be enabled."
