"""No-follow-up report access, filtering and privacy contracts."""
import datetime
import json
from inspect import unwrap
import unittest
from unittest.mock import Mock, patch

import frappe
from life_slimming.api.server_scripts import life_cc_nofu_v1 as report


class NoFollowupTests(unittest.TestCase):
    def setUp(self):
        self.api = Mock()
        self.api.session.user = "agent@example.test"
        self.api.form_dict = {}
        self.api.response = {}
        self.api.get_all.return_value = []
        self.api.utils.now_datetime.return_value = datetime.datetime(2026, 11, 10, 12)
        self.api.utils.add_to_date.side_effect = lambda now, days: now + datetime.timedelta(days=days)
        self.api.db.sql.side_effect = [[{}], [], [], [[1]], [{
            "name": "LEAD-1", "lead_name": "Client", "mobile_no": "9876543210",
            "custom_call_count": 2, "custom_convox_call_count": 3,
            "lt": "2026-10-01 10:00:00", "lead_owner": "agent@example.test",
        }]]
        self.access = Mock()
        for context in [patch.object(report, "frappe", self.api), patch.object(report, "require_module", self.access)]:
            context.start()
            self.addCleanup(context.stop)

    def run_report(self, roles=None, **filters):
        self.api.get_all.return_value = roles or []
        self.api.form_dict = filters
        unwrap(report.run)()
        return self.api.response["message"]

    def test_denied_module_cannot_query_data(self):
        self.access.side_effect = frappe.PermissionError
        with self.assertRaises(frappe.PermissionError):
            self.run_report()
        self.api.db.sql.assert_not_called()

    def test_agent_cannot_request_other_owners_and_phone_is_masked(self):
        result = self.run_report(agents=json.dumps(["other@example.test"]), owner="other@example.test")
        self.access.assert_called_once_with("ccvisit")
        query, params = self.api.db.sql.call_args.args
        self.assertEqual(params["o"], ("agent@example.test",))
        self.assertIn("lower(lead_owner) in %(o)s", query)
        self.assertIn("lower(lead_owner) = %(w)s", query)
        self.assertEqual(result["rows"][0]["ph4"], "3210")
        self.assertNotIn("9876543210", json.dumps(result))
        self.assertEqual(result["rows"][0]["calls"], 5)
        self.api.db.set_value.assert_not_called()

    def test_manager_filters_are_bound_parameters_and_paging_is_clamped(self):
        self.run_report(roles=["CC Manager"], agents=["Other@Example.test"],
                        statuses=["No Response", "(no status)"], start=-10, limit=9999)
        query, params = self.api.db.sql.call_args.args
        self.assertEqual(params["o"], ("other@example.test",))
        self.assertEqual(params["s"], ("No Response", ""))
        self.assertNotIn("No Response", query)
        self.assertIn("limit 500 offset 0", query)
        self.assertIn("'LOST','INVALID','SUCCESS'", query)

    def test_negative_limit_and_including_closed(self):
        self.run_report(limit=-50, closed=1)
        query = self.api.db.sql.call_args.args[0]
        self.assertIn("limit 1 offset 0", query)
        self.assertNotIn("'LOST','INVALID','SUCCESS'", query)


if __name__ == "__main__":
    unittest.main()
