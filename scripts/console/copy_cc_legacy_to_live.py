# Paste into Frappe System Console, Type = Python, with Commit enabled.
# Copies the live legacy Web Page document; no local snapshot is used.
source = frappe.get_doc("Web Page", "cc-new-dashboard-bhuvan-oct2")
target = frappe.get_doc("Web Page", "cc-new-dash")

if str(source.modified) != "2026-10-03 20:26:30.330893":
    frappe.throw("Legacy CC changed after comparison. Compare it again before copying.")
if str(target.modified) != "2026-10-02 13:24:59.105555":
    frappe.throw("LIVE CC changed after comparison. Compare it again before copying.")
if not source.main_section_html or not source.javascript or not source.css:
    frappe.throw("Legacy CC content is incomplete; nothing was copied.")

original_route = target.route
original_published = target.published
backup = frappe.get_doc({
    "doctype": "File",
    "file_name": "cc-new-dash-before-legacy-copy-" + frappe.utils.generate_hash(length=12) + ".json",
    "is_private": 1,
    "attached_to_doctype": "Web Page",
    "attached_to_name": target.name,
    "content": as_json(target.as_dict()),
}).insert()

fields = [
    "title", "content_type", "main_section", "main_section_md", "main_section_html",
    "javascript", "css", "context_script", "insert_style", "text_align",
    "full_width", "show_title", "show_sidebar", "website_sidebar",
    "header", "breadcrumbs", "dynamic_template", "dynamic_route",
    "meta_title", "meta_description", "meta_image", "enable_comments",
    "slideshow", "start_date", "end_date",
]
for field in fields:
    target.set(field, source.get(field))
target.route = original_route
target.published = original_published
target.save()

saved = frappe.get_doc("Web Page", target.name)
for field in fields:
    if saved.get(field) != source.get(field):
        frappe.throw("Copy verification failed for " + field)
if saved.route != original_route or saved.published != original_published:
    frappe.throw("LIVE route/publication verification failed.")

print("Verified: legacy CC rendering fields copied exactly to " + saved.name)
print("URL: /" + saved.route)
print("Private backup: " + backup.file_url)
print("The Web Page save clears its website cache. Hard-refresh the page.")
