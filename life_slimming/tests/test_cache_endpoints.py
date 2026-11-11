"""Endpoint wiring for the read cache: scopes, keys, and what must stay live."""
import unittest
from datetime import datetime
from unittest.mock import patch

import frappe

from life_slimming.api import cc_live_tv


class CCLiveTVCacheTest(unittest.TestCase):
	def setUp(self):
		frappe.local.conf = frappe._dict()
		frappe.local.flags = frappe._dict()
		frappe.local.session = frappe._dict(user="agent@x")

	def tearDown(self):
		frappe.destroy()

	def test_tv_key_scopes_managers_to_all_and_agents_to_self(self):
		dates = ("2026-11-11", "2026-11-06", "2026-11-09")
		self.assertEqual(
			cc_live_tv._tv_cache_key("agent@x", True, *dates),
			("cc_live_tv", "agent@x", {"today": "2026-11-11", "month_start": "2026-11-06", "week_start": "2026-11-09"}),
		)
		namespace, scope, args = cc_live_tv._tv_cache_key("manager@x", False, *dates)
		self.assertEqual((namespace, scope), ("cc_live_tv", "all"))
		self.assertEqual(args, cc_live_tv._tv_cache_key("other-manager@x", False, *dates)[2])

	def test_tv_snapshot_runs_permission_checks_before_cache(self):
		with (
			patch.object(cc_live_tv, "require_module", side_effect=frappe.PermissionError),
			patch("life_slimming.cache.cached_read") as cached_read,
		):
			with self.assertRaises(frappe.PermissionError):
				cc_live_tv.snapshot()
		cached_read.assert_not_called()

		with (
			patch.object(cc_live_tv, "require_module"),
			patch.object(frappe, "get_roles", return_value=["Employee"]),
			patch("life_slimming.cache.cached_read") as cached_read,
		):
			with self.assertRaises(frappe.PermissionError):
				cc_live_tv.snapshot()
		cached_read.assert_not_called()

	def test_tv_snapshot_returns_cached_read_result_for_scope(self):
		with (
			patch.object(cc_live_tv, "require_module"),
			patch.object(cc_live_tv, "now_datetime", return_value=datetime(2026, 11, 11, 10, 0)),
			patch.object(frappe, "get_roles", return_value=["Sales User"]),
			patch("life_slimming.cache.cached_read", return_value={"rows": ["cached"]}) as cached_read,
		):
			self.assertEqual(cc_live_tv.snapshot(), {"rows": ["cached"]})
		namespace, scope, args, compute = cached_read.call_args.args
		self.assertEqual((namespace, scope), ("cc_live_tv", "agent@x"))
		self.assertEqual(args, {"today": "2026-11-11", "month_start": "2026-11-06", "week_start": "2026-11-09"})
		self.assertTrue(callable(compute))

		with (
			patch.object(cc_live_tv, "require_module"),
			patch.object(cc_live_tv, "now_datetime", return_value=datetime(2026, 11, 11, 10, 0)),
			patch.object(frappe, "get_roles", return_value=["Sales Manager"]),
			patch("life_slimming.cache.cached_read", return_value={}) as cached_read,
		):
			cc_live_tv.snapshot()
		self.assertEqual(cached_read.call_args.args[1], "all")


if __name__ == "__main__":
	unittest.main()
