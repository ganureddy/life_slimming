import unittest
from unittest.mock import patch

import frappe
from life_slimming import session_policy


class SessionPolicyTest(unittest.TestCase):
    def setUp(self):
        frappe.local.conf = frappe._dict()
        frappe.local.flags = frappe._dict()
        frappe.local.session = frappe._dict(user="narendhar@lifescc.com")

    def tearDown(self):
        frappe.destroy()

    def test_only_selected_users_are_exempt(self):
        for user, expected in [("narendhar@lifescc.com", True), ("life@gmail.com", True),
                               ("other@example.com", False), ("Guest", False)]:
            frappe.session.user = user
            self.assertEqual(session_policy.idle_logout_exempt(), expected)

    def test_config_can_remove_defaults_and_never_exempt_guest(self):
        frappe.conf.life_idle_logout_exempt_users = []
        self.assertFalse(session_policy.idle_logout_exempt())
        frappe.conf.life_idle_logout_exempt_users = " Guest, OTHER@example.com "
        frappe.session.user = "Guest"
        self.assertFalse(session_policy.idle_logout_exempt())
        frappe.session.user = "other@example.com"
        self.assertTrue(session_policy.idle_logout_exempt())

    def test_heartbeat_interval_respects_short_session_expiry(self):
        with patch.object(session_policy, "get_expiry_in_seconds", return_value=90):
            self.assertEqual(session_policy.heartbeat(), {
                "idle_logout_exempt": True, "heartbeat_seconds": 30,
            })
