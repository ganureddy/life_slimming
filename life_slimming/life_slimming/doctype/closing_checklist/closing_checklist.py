# Copyright (c) 2023, swathi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import datetime


class ClosingChecklist(Document):
	def before_save(self):
		self.amount1 = (int(self.five_hundred)*int(self.count1)) if self.five_hundred and self.count1 else 0 
		self.amount2 = (int(self.two_hundred)*int(self.count2)) if self.two_hundred and self.count2 else 0 
		self.amount3 = (int(self.hundred)*int(self.count3)) if self.hundred and self.count3 else 0 
		self.amount4 = (int(self.fifty)*int(self.count4)) if self.fifty and self.count4 else 0 
		self.amount6 = (int(self.five_hundred1)*int(self.count6)) if self.five_hundred1 and self.count6 else 0 
		self.amount7 = (int(self.two_hundred1)*int(self.count7)) if self.two_hundred1 and self.count7 else 0 
		self.amount8 = (int(self.hundred1)*int(self.count8)) if self.hundred1 and self.count8 else 0 
		self.amount9 = (int(self.fifty)*int(self.count9)) if self.fifty and self.count9 else 0 
		self.amount10 = (int(self.twenty)*int(self.count10)) if self.twenty and self.count10 else 0 
		self.amount11 = (int(self.ten)*int(self.count11)) if self.ten and self.count11 else 0 
		self.total_amount = self.amount1 + self.amount2 +self.amount3+self.amount4+self.amount6+self.amount7+self.amount8+self.amount9+self.amount10+self.amount11+int(self.coins) if self.coins else 0
	
		
		today = datetime.datetime.now().strftime("%Y-%m-%d")
  
		total_therapy_sessions = frappe.db.get_list(
			"Therapy Session", filters={'start_date': today, 'docstatus': 1})
  
		print(total_therapy_sessions, '//////////////////')
  
		therapy_sessions_count = len(total_therapy_sessions)
		print(therapy_sessions_count, 'therapy sessions count')
		if therapy_sessions_count > 0:
			self.yes3 = 1
			self.yes4 = 1
		# if self.todays_total_sales != self.total_amount:
		# 	frappe.throw(
		# 		f"Your Today's total sales:{self.todays_total_sales} and total of sales cash denominations and petty cash denominations:{self.total_amount} are not match please check once")

@frappe.whitelist()
def today_total_amount():
	try:
		today = datetime.datetime.now().strftime("%Y-%m-%d")
		total_amoumt = frappe.db.sql("""Select SUM(paid_amount) as paid_amount  from `tabPayment Entry` Where posting_date = '{today}', mode_of_payment = "Cash" and
										payment_type = "Receive" """.format(today=today), as_dict=1)
		
		today_total_sales = total_amoumt[0]['paid_amount']
		
		return today_total_sales
	except Exception as e:
	 print(e)
	