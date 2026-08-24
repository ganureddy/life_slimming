// Copyright (c) 2026, swathi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Two Factor Bypass Settings", {
	refresh(frm) {
		frappe.db.get_single_value("System Settings", "enable_two_factor_auth").then((enabled) => {
			if (!cint(enabled)) {
				frm.dashboard.set_headline(
					__("Two Factor Authentication is currently off in System Settings, so this list has no effect.")
				);
			}
		});
	},
});
