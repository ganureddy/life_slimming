import frappe
import traceback,sys

def get_roles(user=None, with_standard=True):
    try:
        if not user:
            user = frappe.session.user
        if user == 'Guest':
            return ['Guest']
        def get():
            return [r[0] for r in frappe.db.sql("""select role from `tabUserRole`
                where parent=%s and role not in ('All', 'Guest')""", (user,))] + ['All', 'Guest']

        roles = frappe.cache().hget("roles", user, get)

        if not with_standard:
            roles = filter(lambda x: x not in ['All', 'Guest', 'Administrator'], roles)
            
        return roles
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        frappe.log_error("line No:{}\n{}".format(exc_tb.tb_lineno, traceback.format_exc()), "get_roles")