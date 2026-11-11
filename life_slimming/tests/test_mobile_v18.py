"""Native life_cc_mobile_v18: same actions as the DB script, guarded rollout."""
import importlib
import inspect
import re
import unittest
from unittest.mock import patch

import frappe

from life_slimming import cache

EXPECTED_ACTIONS = {
	"queue", "dial", "finish", "sync", "recording", "calls", "summary", "appver", "me", "agents",
	"number", "wa_log", "timing", "live", "team", "plans", "plan_save", "plan_leads", "targets",
	"target_save", "feed",
}


class MobileV18MigrationTest(unittest.TestCase):
	def setUp(self):
		frappe.local.conf = frappe._dict()
		frappe.local.flags = frappe._dict()
		frappe.local.session = frappe._dict(user="agent@x")
		frappe.local.form_dict = frappe._dict()
		frappe.local.response = frappe._dict()
		from life_slimming.api.server_scripts import life_cc_mobile_v18

		self.module = life_cc_mobile_v18

	def tearDown(self):
		frappe.destroy()

	def test_actions_match_source(self):
		source = inspect.getsource(self.module._native)
		literals = set(re.findall(r'action == "([a-z_]+)"', source))
		self.assertEqual(literals, EXPECTED_ACTIONS)
		self.assertEqual(set(self.module.ACTIONS), EXPECTED_ACTIONS)

	def test_falls_back_to_db_script_when_native_off(self):
		with (
			patch.object(self.module, "run_server_script", return_value=None) as run_server_script,
			patch.object(self.module, "_native") as native,
		):
			self.module.run(action="queue")
		run_server_script.assert_called_once_with("life_cc_mobile_v18")
		native.assert_not_called()

	def test_native_when_switch_on(self):
		frappe.local.conf[cache.CONFIG_KEY] = {"mobile_native": 1}
		with (
			patch.object(self.module, "run_server_script") as run_server_script,
			patch.object(self.module, "_native") as native,
		):
			self.module.run(action="queue")
		native.assert_called_once_with()
		run_server_script.assert_not_called()

	def test_hooks_override_points_to_native_run(self):
		from life_slimming import hooks

		target = hooks.override_whitelisted_methods["life_cc_mobile_v18"]
		self.assertEqual(target, "life_slimming.api.server_scripts.life_cc_mobile_v18.run")
		module_path, attribute = target.rsplit(".", 1)
		self.assertIs(getattr(importlib.import_module(module_path), attribute), self.module.run)
		self.assertIn(self.module.run, frappe.whitelisted)
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[self.module.run], ["POST"])


if __name__ == "__main__":
	unittest.main()
