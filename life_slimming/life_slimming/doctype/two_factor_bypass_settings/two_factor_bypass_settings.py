# Copyright (c) 2026, swathi and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from life_slimming.two_factor_bypass import clear_bypass_cache


class TwoFactorBypassSettings(Document):
	def validate(self):
		self.validate_duplicate_users()
		self.validate_administrator()

	def validate_duplicate_users(self):
		seen = {}
		for row in self.users:
			if not row.user:
				continue
			if row.user in seen:
				frappe.throw(
					_("{0} is listed twice, in row {1} and row {2}.").format(
						frappe.bold(row.user), seen[row.user], row.idx
					),
					title=_("Duplicate User"),
				)
			seen[row.user] = row.idx

	def validate_administrator(self):
		# Administrator never runs 2FA anyway (frappe.twofactor.two_factor_is_enabled_for_),
		# so listing it here only makes the list misleading.
		for row in self.users:
			if row.user == "Administrator":
				frappe.throw(
					_("Administrator is already exempt from Two Factor Authentication; remove row {0}.").format(
						row.idx
					)
				)

	def on_update(self):
		clear_bypass_cache()
