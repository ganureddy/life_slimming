"""Read cache: own writes are seen at once, other users' writes within ttl."""
import json
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import frappe

from life_slimming import cache
from life_slimming.tests.cache_fakes import FakeCache, FakeClock

DEFAULT_ROWS = object()


class ReadCacheTest(unittest.TestCase):
	def setUp(self):
		frappe.local.conf = frappe._dict()
		frappe.local.flags = frappe._dict()
		frappe.local.session = frappe._dict(user="agent@x")
		self.clock = FakeClock()
		self.fake = FakeCache(self.clock)
		self.patches = [
			patch.object(frappe, "cache", self.fake),
			patch.object(cache, "_now", self.clock),
			patch.object(frappe, "log_error", MagicMock()),
		]
		for p in self.patches:
			p.start()
		cache._error_logged = False
		self.calls = 0

	def tearDown(self):
		for p in reversed(self.patches):
			p.stop()
		frappe.destroy()

	def configure(self, **values):
		frappe.local.conf[cache.CONFIG_KEY] = {"enabled": 1, **values}

	def compute(self, value=DEFAULT_ROWS):
		def run():
			self.calls += 1
			return [{"lead": "L-1", "n": self.calls}] if value is DEFAULT_ROWS else value
		return run

	def read(self, compute=None, namespace="cc_live_tv", scope="all", args=None):
		self.fake.new_request()
		return cache.cached_read(namespace, scope, args or {"today": "2026-11-11"}, compute or self.compute())

	def set_stamp(self, user, when):
		self.fake.set_value(f"life_slimming:lw:{user}", when, expires_in_sec=120)

	def counters(self, namespace="cc_live_tv"):
		key = self.fake.make_key(f"life_slimming:rc:stats:{namespace}")
		return {k.decode(): int(v) for k, v in self.fake.hashes.get(key, {}).items()}

	def test_disabled_by_default_calls_compute_every_time(self):
		self.read()
		self.read()
		self.assertEqual(self.calls, 2)
		self.assertEqual(self.fake.store, {})
		self.assertEqual(self.fake.hashes, {})

	def test_hit_within_ttl_and_miss_after(self):
		self.configure()
		first = self.read()
		self.clock.advance(29)
		self.assertEqual(self.read(), first)
		self.assertEqual(self.calls, 1)
		self.clock.advance(2)
		self.read()
		self.assertEqual(self.calls, 2)
		self.assertEqual(self.counters()["hit"], 1)
		self.assertEqual(self.counters()["miss"], 2)

	def test_own_write_makes_entry_stale(self):
		self.configure()
		self.read()
		self.set_stamp("agent@x", self.clock.now + 1)
		self.clock.advance(1)
		self.read()
		self.assertEqual(self.calls, 2)
		self.assertEqual(self.counters()["stale_own_write"], 1)

	def test_other_users_write_does_not_invalidate(self):
		self.configure()
		self.read()
		self.set_stamp("other@x", self.clock.now + 1)
		self.clock.advance(1)
		self.read()
		self.assertEqual(self.calls, 1)

	def test_write_during_compute_invalidates(self):
		self.configure()

		def writes_while_computing():
			self.calls += 1
			self.set_stamp("agent@x", self.clock.now)
			return ["rows"]

		self.read(writes_while_computing)
		self.read(writes_while_computing)
		self.assertEqual(self.calls, 2)

	def test_equal_timestamps_are_stale(self):
		self.configure()
		self.read()
		self.set_stamp("agent@x", self.clock.now)
		self.read()
		self.assertEqual(self.calls, 2)

	def test_falsy_results_are_cached(self):
		self.configure()
		for index, value in enumerate([None, [], {}]):
			self.calls = 0
			args = {"case": index}
			self.assertEqual(self.read(self.compute(value), args=args), value)
			self.assertEqual(self.read(self.compute(value), args=args), value)
			self.assertEqual(self.calls, 1, f"recomputed falsy value {value!r}")

	def test_returned_values_are_independent_copies(self):
		self.configure()
		first = self.read(self.compute({"rows": [1], "contact_manager": False}))
		first["contact_manager"] = True
		first["rows"].append(2)
		second = self.read()
		self.assertEqual(second, {"rows": [1], "contact_manager": False})
		second["rows"].append(3)
		self.assertEqual(self.read(), {"rows": [1], "contact_manager": False})

	def test_args_hash_stable_and_distinct(self):
		self.configure()
		self.read(args={"b": 1, "a": date(2026, 11, 11)})
		self.read(args={"a": date(2026, 11, 11), "b": 1})
		self.read(args=frappe._dict(a=date(2026, 11, 11), b=1))
		self.assertEqual(self.calls, 1)
		self.read(args={"a": date(2026, 11, 12), "b": 1})
		self.assertEqual(self.calls, 2)

	def test_too_large_not_stored(self):
		self.configure(max_entry_bytes=10)
		result = self.read(self.compute(list(range(100))))
		self.assertEqual(result, list(range(100)))
		self.read(self.compute(list(range(100))))
		self.assertEqual(self.calls, 2)
		self.assertEqual(self.counters()["too_large"], 2)
		self.assertFalse(any(b"life_slimming:rc:cc_live_tv" in k for k in self.fake.store))

	def test_namespace_and_prefix_disable(self):
		self.configure(disabled=["mobile_v18"])
		self.assertFalse(cache.enabled("mobile_v18.queue"))
		self.assertFalse(cache.enabled("mobile_v18"))
		self.assertTrue(cache.enabled("cc_live_tv"))
		self.assertTrue(cache.enabled("mobile_v18x"))
		self.read(namespace="mobile_v18.queue")
		self.read(namespace="mobile_v18.queue")
		self.assertEqual(self.calls, 2)

	def test_settings_accepts_json_string_and_survives_garbage(self):
		frappe.local.conf[cache.CONFIG_KEY] = json.dumps({"enabled": 1, "ttl": 45})
		self.assertEqual(cache.settings().ttl, 45)
		self.assertTrue(cache.enabled("cc_live_tv"))
		for garbage in ['{"enabled": 1', "yes", 7, ["enabled"], {"enabled": 1, "ttl": "soon", "disabled": None}]:
			frappe.local.conf[cache.CONFIG_KEY] = garbage
			config = cache.settings()
			self.assertEqual(config.ttl, 30)
			self.assertEqual(config.max_entry_bytes, 1048576)
			self.assertEqual(config.disabled, [])
		frappe.local.conf[cache.CONFIG_KEY] = '{"enabled": 1'
		self.assertFalse(cache.enabled("cc_live_tv"))

	def test_redis_failure_falls_through(self):
		self.configure()
		self.fake.fail = True
		self.assertEqual(self.read(self.compute(["fresh"])), ["fresh"])
		self.assertEqual(self.read(self.compute(["fresh"])), ["fresh"])
		self.assertEqual(self.calls, 2)
		self.assertEqual(frappe.log_error.call_count, 1)

	def test_compute_exception_propagates_and_is_not_stored(self):
		self.configure()

		def boom():
			raise frappe.ValidationError("bad range")

		with self.assertRaises(frappe.ValidationError):
			self.read(boom)
		self.assertFalse(any(b"life_slimming:rc:cc_live_tv" in k for k in self.fake.store))
		self.read()
		self.assertEqual(self.calls, 1)

	def test_guest_bypasses_cache(self):
		self.configure()
		frappe.local.session = frappe._dict(user="Guest")
		self.read()
		self.read()
		self.assertEqual(self.calls, 2)
		self.assertEqual(self.fake.store, {})

	def test_stats_requires_system_manager_and_reports_counters(self):
		self.configure()
		self.read()
		self.read()
		with patch.object(frappe, "only_for", side_effect=frappe.PermissionError):
			with self.assertRaises(frappe.PermissionError):
				cache.stats()
		with patch.object(frappe, "only_for") as only_for:
			report = cache.stats()
		only_for.assert_called_once_with("System Manager")
		self.assertEqual(report["namespaces"]["cc_live_tv"]["hit"], 1)
		self.assertEqual(report["namespaces"]["cc_live_tv"]["miss"], 1)
		self.assertGreater(report["namespaces"]["cc_live_tv"]["stored_bytes"], 0)
		self.assertEqual(set(report["redis"]), {"used_memory", "evicted_keys", "keyspace_hits", "keyspace_misses"})


if __name__ == "__main__":
	unittest.main()
