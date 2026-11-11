"""Endpoint wiring for the read cache: scopes, keys, and what must stay live."""
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

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


class CCGetLeadsCacheTest(unittest.TestCase):
	def setUp(self):
		frappe.local.conf = frappe._dict()
		frappe.local.flags = frappe._dict()
		frappe.local.session = frappe._dict(user="agent@x")
		frappe.local.form_dict = frappe._dict()
		frappe.local.response = frappe._dict()
		from life_slimming.api.server_scripts import cc_get_leads

		self.module = cc_get_leads

	def tearDown(self):
		frappe.destroy()

	def plan(self, can_view_all=False, user="agent@x", **fd):
		return self.module._cache_plan(frappe._dict(fd), user, can_view_all)

	def test_leads_detail_bypasses_cache(self):
		self.assertIsNone(self.plan(query="CRM-LEAD-2026-1", detail=1))

	def test_leads_search_and_phone_share_search_scope(self):
		self.assertEqual(
			self.plan(query=" Ravi ", start="20"),
			("cc_get_leads", "search", {"mode": "query", "query": "Ravi", "start": "20"}),
		)
		self.assertEqual(self.plan(query="Ravi"), self.plan(query="Ravi", can_view_all=True, user="manager@x"))
		self.assertEqual(
			self.plan(phone="+91 93901-70043"),
			("cc_get_leads", "search", {"mode": "phone", "digits": "9390170043"}),
		)
		# query wins over phone, exactly like the endpoint's own branch order.
		self.assertEqual(self.plan(query="Ravi", phone="9390170043")[2]["mode"], "query")

	def test_leads_range_scope_all_for_managers_self_for_agents(self):
		fd = {"from_date": "2026-11-01", "to_date": "2026-11-11"}
		self.assertEqual(self.plan(**fd)[:2], ("cc_get_leads", "agent@x"))
		self.assertEqual(self.plan(can_view_all=True, user="manager@x", **fd)[:2], ("cc_get_leads", "all"))
		self.assertEqual(self.plan(**fd)[2]["date_mode"], "created")

	def test_leads_range_args_distinguish_pagination_and_filters(self):
		base = {"from_date": "2026-11-01", "to_date": "2026-11-11", "date_mode": "followup"}
		legacy = self.plan(**base)[2]
		paged = self.plan(page_size="40", **base)[2]
		self.assertFalse(legacy["paginated"])
		self.assertTrue(paged["paginated"])
		variants = [
			legacy,
			paged,
			self.plan(page_size="40", start="40", **base)[2],
			self.plan(page_size="40", branch="Hyderabad", **base)[2],
			self.plan(page_size="40", stage="FOLLOW-UP", **base)[2],
			self.plan(**{**base, "date_mode": "appointment"})[2],
			self.plan(**{**base, "to_date": "2026-11-12"})[2],
		]
		self.assertEqual(len({repr(sorted(v.items())) for v in variants}), len(variants))
		self.assertEqual(set(paged), {"mode", "from_date", "to_date", "date_mode", "page_size", "start", "branch", "stage", "paginated"})

	def test_contact_manager_applied_after_cache(self):
		def get_all(doctype, *args, **kwargs):
			return ["Sales User"] if doctype == "Has Role" else []

		meta = frappe._dict(has_field=lambda fieldname: False)
		with (
			patch.object(frappe, "get_all", side_effect=get_all),
			patch.object(frappe, "get_meta", return_value=meta),
			patch.object(frappe, "db", MagicMock(**{"exists.return_value": False, "count.return_value": 0})),
			patch("life_slimming.cache.cached_read", return_value={"rows": [], "contact_manager": True}) as cached_read,
		):
			self.module.run(from_date="2026-11-01", to_date="2026-11-11")
		self.assertEqual(cached_read.call_args.args[:2], ("cc_get_leads", "agent@x"))
		self.assertIs(frappe.response["message"]["contact_manager"], False)


if __name__ == "__main__":
	unittest.main()
