"""Write tracking: every committed write by the request's user sets their stamp."""
import unittest
from unittest.mock import MagicMock, patch

import frappe

from life_slimming import cache
from life_slimming.tests.cache_fakes import FakeCache, FakeClock, FakeDB


class WriteTrackingTest(unittest.TestCase):
	def setUp(self):
		frappe.local.conf = frappe._dict({cache.CONFIG_KEY: {"enabled": 1}})
		frappe.local.flags = frappe._dict()
		frappe.local.session = frappe._dict(user="agent@x")
		self.clock = FakeClock()
		self.fake = FakeCache(self.clock)
		self.db = FakeDB(self.clock)
		self.patches = [
			patch.object(frappe, "cache", self.fake),
			patch.object(frappe, "db", self.db),
			patch.object(cache, "_now", self.clock),
			patch.object(frappe, "log_error", MagicMock()),
		]
		for p in self.patches:
			p.start()

	def tearDown(self):
		for p in reversed(self.patches):
			p.stop()
		frappe.destroy()

	def stamp(self):
		self.fake.new_request()
		return cache.stamp("agent@x")

	def test_commit_without_writes_does_not_mark(self):
		cache.arm_write_tracking()
		self.db.commit()
		self.assertEqual(self.stamp(), 0.0)

	def test_commit_with_writes_marks_after_commit(self):
		cache.arm_write_tracking()
		before_commit_time = self.clock.now
		self.db.write()
		self.db.commit()  # the fake clock moves one second at the COMMIT statement
		self.assertEqual(self.stamp(), before_commit_time + 1)

	def test_two_commits_in_one_request_both_mark(self):
		cache.arm_write_tracking()
		self.db.write()
		self.db.commit()
		first = self.stamp()
		self.clock.advance(5)
		self.db.write()
		self.db.commit()
		self.assertEqual(self.stamp(), first + 6)

	def test_rollback_then_write_commit_marks(self):
		cache.arm_write_tracking()
		self.db.write()
		self.db.rollback()
		self.assertEqual(self.stamp(), 0.0)
		self.db.write()
		self.db.commit()
		self.assertEqual(self.stamp(), self.clock.now)

	def test_two_rollbacks_then_write_commit_marks(self):
		cache.arm_write_tracking()
		self.db.rollback()
		self.db.rollback()
		self.db.write()
		self.db.commit()
		self.assertEqual(self.stamp(), self.clock.now)

	def test_never_adds_to_running_queue(self):
		cache.arm_write_tracking()
		self.db.commit()
		self.db.write()
		self.db.rollback()
		self.db.rollback()
		self.db.commit()
		self.db.write()
		self.db.commit()
		self.db.commit()
		self.assertEqual(self.stamp(), self.clock.now - 1)
		# Exactly one pending tracker per queue: the chain re-arms without piling up.
		self.assertEqual(len(self.db.before_commit), 1)
		self.assertEqual(len(self.db.before_rollback), 1)
		self.assertEqual(len(self.db.after_commit), 0)
		self.assertEqual(len(self.db.after_rollback), 0)

	def test_disabled_or_guest_does_not_arm(self):
		frappe.local.conf[cache.CONFIG_KEY] = {"enabled": 0}
		cache.arm_write_tracking()
		frappe.local.conf[cache.CONFIG_KEY] = {"enabled": 1}
		frappe.local.session = frappe._dict(user="Guest")
		cache.arm_write_tracking()
		for queue in (self.db.before_commit, self.db.after_commit, self.db.before_rollback, self.db.after_rollback):
			self.assertEqual(len(queue), 0, queue.name)
		self.db.write()
		self.db.commit()
		cache.mark_write("Guest")
		frappe.local.conf[cache.CONFIG_KEY] = {"enabled": 0}
		cache.mark_write("agent@x")
		self.assertEqual(self.fake.store, {})


if __name__ == "__main__":
	unittest.main()
