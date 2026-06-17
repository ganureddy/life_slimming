import frappe
from datetime import datetime
from life_slimming.user_wise_roles import get_roles
from frappe import _

def check_purchase_order_validate(doc,method=None):
    # LIMIT_AMOUNT = 25,00,000
    # current_month = datetime.now().strftime('%m')
    # buying_setting_detail = frappe.db.sql('''Select field,value from `tabSingles` Where doctype='Buying Settings' and field IN('monthly_purchase_limit','role_allow')
    #                                       ''',as_dict=1)
    
    buying_setting_detail = frappe.get_doc("Buying Settings","Buying Settings")
    
    limit_amount = buying_setting_detail.monthly_purchase_limit
    role_allow = buying_setting_detail.role_allow
    
    currentMonth = datetime.now().month
    
    if limit_amount != 0.0 or role_allow != '':
        return
            
    raw_data = frappe.db.sql("""Select Sum(grand_total) as grand_total from `tabPurchase Order` Where Month(transaction_date)='{month}'
                            """.format(month = currentMonth),as_dict=True)
    
    if len(raw_data)>0:
        if float(raw_data[0]['grand_total']) >= limit_amount:
            roles = get_roles(user=None,with_standard=True)
            if role_allow not in roles:
                frappe.throw(f"Purchase Order Is Exceed of its Limit Amount")
            else:
                pass
    else:
        pass

