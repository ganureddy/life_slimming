"""Run in the target site's bench console to protect existing agent ownership.

exec(open('apps/life_slimming/scripts/console/patch_website_repeat_v5_protection.py').read())
"""
import frappe

script = frappe.get_doc('Server Script', 'MD LEADS AUTO ASSIGN')
needle = '                protected = current_status in ("followup", "appointment booked")'
replacement = '''                # LIFE WEBSITE REPEAT OWNERSHIP PROTECTION V6
                current_stage = str(lead.custom_cc_stage or "").strip().upper()
                protected = current_status in (
                    "followup", "appointment booked", "converted", "do not contact",
                    "existing client", "dnd"
                ) or current_stage in ("FOLLOW-UP", "SUCCESS", "LOST", "INVALID")'''
if 'LIFE WEBSITE REPEAT OWNERSHIP PROTECTION V6' in script.script:
    print('Website repeat ownership protection already installed.')
else:
    if 'LIFE WEBSITE CHAT REPEAT ENQUIRY V5' not in script.script or script.script.count(needle) != 1:
        raise RuntimeError('The installed V5 script differs. Review it before applying this patch.')
    code = script.script.replace(needle, replacement, 1)
    code = code.replace('if appointment_state == "booked":', 'if appointment_state in ("booked", "visited booked"):')
    compile(code, '<website repeat ownership protection>', 'exec')
    script.script = code
    script.save()
    frappe.db.commit()
    print('Website repeat ownership protection installed. No Lead records were changed.')
