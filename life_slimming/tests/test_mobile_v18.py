"""Native life_cc_mobile_v18: same actions as the DB script, guarded rollout."""
import importlib
import inspect
import re
import unittest
from unittest.mock import MagicMock, patch

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


class MobileV18CacheTest(unittest.TestCase):
	WRITE_ACTIONS = ("dial", "finish", "sync", "recording", "wa_log", "timing", "plan_save", "target_save", "number")

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

	def test_write_actions_never_cached(self):
		for action in self.WRITE_ACTIONS:
			self.assertIsNone(self.module._mobile_cache_key(action, "a@x", False, {}, "2026-11-11"), action)
		for action in EXPECTED_ACTIONS - set(self.module.CACHED_ACTIONS):
			self.assertIsNone(self.module._mobile_cache_key(action, "a@x", True, {}, "2026-11-11"), action)
		self.assertEqual(set(self.module.CACHED_ACTIONS), {"queue", "calls", "summary", "live", "team", "feed"})

	def test_read_action_key_scope_and_args(self):
		fd = {"from": "2026-11-01", "to": "2026-11-11", "team": "A", "x": 1}
		self.assertEqual(
			self.module._mobile_cache_key("summary", "a@x", True, fd, "2026-11-11"),
			(
				"mobile_v18.summary",
				"a@x|mgr=1",
				{"today": "2026-11-11", "agent": None, "from": "2026-11-01", "to": "2026-11-11", "team": "A"},
			),
		)
		self.assertEqual(self.module._mobile_cache_key("queue", "a@x", False, fd, "2026-11-11")[1:], ("a@x|mgr=0", {"today": "2026-11-11"}))
		self.assertEqual(self.module._mobile_cache_key("calls", "a@x", False, {"date": "2026-11-10"}, "2026-11-11")[2]["date"], "2026-11-10")

	def test_cached_action_sets_response_from_cache(self):
		frappe.local.conf[cache.CONFIG_KEY] = {"mobile_native": 1}
		with (
			patch.object(frappe, "get_all", return_value=[]),
			patch.object(frappe.utils, "today", return_value="2026-11-11"),
			patch("life_slimming.cache.cached_read", return_value={"ok": 1}) as cached_read,
		):
			self.module.run(action="queue")
		self.assertEqual(frappe.response["message"], {"ok": 1})
		namespace, scope, args, compute = cached_read.call_args.args
		self.assertEqual((namespace, scope, args), ("mobile_v18.queue", "agent@x|mgr=0", {"today": "2026-11-11"}))
		self.assertTrue(callable(compute))


class CompareMobileTest(unittest.TestCase):
	def setUp(self):
		frappe.local.conf = frappe._dict()
		frappe.local.flags = frappe._dict()
		frappe.local.session = frappe._dict(user="Administrator")
		frappe.local.form_dict = frappe._dict(cmd="original")
		frappe.local.response = frappe._dict()
		from life_slimming import cache_tools
		from life_slimming.api.server_scripts import life_cc_mobile_v18

		self.tools = cache_tools
		self.mobile = life_cc_mobile_v18
		self.db = MagicMock()
		self.users = []

		def set_user(user):
			self.users.append(user)
			frappe.local.session = frappe._dict(user=user)

		self.patches = [
			patch.object(frappe, "db", self.db),
			patch.object(frappe, "set_user", side_effect=set_user),
		]
		for p in self.patches:
			p.start()

	def tearDown(self):
		for p in reversed(self.patches):
			p.stop()
		frappe.destroy()

	def implementations(self, db_message, native_message):
		def db_script(name):
			self.assertEqual(name, "life_cc_mobile_v18")
			frappe.response["message"] = db_message() if callable(db_message) else db_message

		def native():
			# The native copy must run with the read cache off.
			self.assertFalse(cache.enabled(f"mobile_v18.{frappe.form_dict.action}"))
			frappe.response["message"] = native_message() if callable(native_message) else native_message

		return (
			patch.object(self.tools, "run_server_script", side_effect=db_script),
			patch.object(self.mobile, "_native", side_effect=native),
		)

	def test_refuses_non_read_actions(self):
		db_patch, native_patch = self.implementations({}, {})
		with db_patch as db_script, native_patch as native:
			with self.assertRaises(frappe.ValidationError):
				self.tools.compare_mobile("a@x", "queue,dial")
		db_script.assert_not_called()
		native.assert_not_called()
		self.assertEqual(self.users, [])

	def test_ignores_now_and_timestamp_fields(self):
		frappe.local.conf[cache.CONFIG_KEY] = {"enabled": 1}
		db_patch, native_patch = self.implementations(
			{"agent": "a@x", "now": "2026-11-11 10:00:00", "rows": [{"n": 1, "timestamp": 1}]},
			{"agent": "a@x", "now": "2026-11-11 10:00:01", "rows": [{"n": 1, "timestamp": 2}]},
		)
		with db_patch, native_patch:
			report = self.tools.compare_mobile(["a@x", "b@x"], ["queue", "summary"])
		self.assertEqual(report, {"a@x": {"queue": "match", "summary": "match"}, "b@x": {"queue": "match", "summary": "match"}})
		self.assertEqual(frappe.conf[cache.CONFIG_KEY], {"enabled": 1})

	def test_reports_mismatch_paths(self):
		db_patch, native_patch = self.implementations(
			{"rows": [{"n": 1}, {"n": 2}], "total": 2},
			{"rows": [{"n": 1}, {"n": 3}], "total": 3, "extra": True},
		)
		with db_patch, native_patch:
			result = self.tools.compare_mobile("a@x", "calls")["a@x"]["calls"]
		self.assertTrue(result.startswith("differs"), result)
		for path in ("rows[1].n", "total", "extra"):
			self.assertIn(path, result)

	def test_always_rolls_back_and_restores_user(self):
		def native_fails():
			raise RuntimeError("native broke")

		db_patch, native_patch = self.implementations({"ok": 1}, native_fails)
		with db_patch, native_patch:
			report = self.tools.compare_mobile("a@x", "feed")
		self.assertIn("native", report["a@x"]["feed"])
		self.assertIn("RuntimeError", report["a@x"]["feed"])
		self.assertTrue(self.db.rollback.called)
		self.assertEqual(frappe.session.user, "Administrator")
		self.assertEqual(frappe.form_dict, {"cmd": "original"})

	def test_compare_mobile_is_not_whitelisted(self):
		self.assertNotIn(self.tools.compare_mobile, frappe.whitelisted)


if __name__ == "__main__":
	unittest.main()
