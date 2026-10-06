"""Native read contracts: pagination, existing owner scope, no financial fan-out."""
import unittest
from unittest.mock import Mock, patch
import frappe
from life_slimming.api.server_scripts import cc_get_leads as leads
from life_slimming.api.server_scripts import life_cc_agent_marketing_data as report


class NativeReads(unittest.TestCase):
    def setUp(self):
        frappe.local.flags = frappe._dict(in_test=True)
        frappe.local.session = frappe._dict(user='agent@example.test')
        frappe.local.response = frappe._dict()
        frappe.local.form_dict = frappe._dict(from_date='2026-10-05', to_date='2026-10-05')
        self.db = Mock()
        self.db.count.return_value = 81
        self.db.exists.return_value = False
        for mock in [patch.object(frappe, 'db', self.db),
                     patch.object(leads, 'enrich_lead_appointments')]:
            mock.start(); self.addCleanup(mock.stop)

    def read_leads(self, roles, **args):
        frappe.local.form_dict.update(args)
        with patch.object(frappe, 'get_all', side_effect=[roles, [{'name':'LEAD-1'}]]) as query:
            leads.run.__wrapped__()
        return query.call_args, frappe.response['message']

    def test_agent_pagination_keeps_owner_filter(self):
        query, response = self.read_leads(['Sales User'], page_size=40, start=40)
        self.assertIn(['lead_owner', '=', 'agent@example.test'], query.kwargs['filters'])
        self.assertEqual(query.kwargs['limit_page_length'], 40)
        self.assertEqual(query.kwargs['limit_start'], 40)
        self.assertTrue(response['has_more'])
        self.assertFalse(response['truncated'])
        self.assertEqual(response['total'], 81)

    def test_legacy_and_manager_contract(self):
        query, response = self.read_leads(['Sales Manager'])
        self.assertEqual(query.kwargs['limit_page_length'], 5000)
        self.assertFalse(response['scoped_to_owner'])
        self.assertFalse(any(f[0] == 'lead_owner' for f in query.kwargs['filters']))

    def test_page_size_clamped(self):
        query, _ = self.read_leads(['Sales User'], page_size=100000, start=-1)
        self.assertEqual(query.kwargs['limit_page_length'], 100)
        self.assertEqual(query.kwargs['limit_start'], 0)

    def test_essential_report_uses_only_lead_and_role_queries(self):
        frappe.local.session.user = 'lifescc13@gmail.com'
        frappe.local.form_dict.update(view='appointments', agent_owner='other@example.test')
        with patch.object(frappe, 'get_meta', return_value=Mock(has_field=lambda field: True)), \
             patch.object(frappe, 'get_all', side_effect=[[], [{'name':'LEAD-1'}]]) as query:
            report.run.__wrapped__()
        self.assertEqual([c.args[0] for c in query.call_args_list], ['Has Role','Lead'])
        self.assertEqual(query.call_args.kwargs['filters']['lead_owner'], 'lifescc13@gmail.com')
        self.assertTrue(frappe.response['message']['restricted_to_owner'])
        self.assertTrue(frappe.response['message']['truncated'])
        self.assertIn('custom_visit_status', query.call_args.kwargs['fields'])

    def test_guest_rejected_before_any_reads(self):
        frappe.local.session.user = 'Guest'
        with patch.object(frappe, 'get_all') as query:
            with self.assertRaises(frappe.PermissionError): leads.run()
            with self.assertRaises(frappe.PermissionError): report.run()
            query.assert_not_called()

if __name__ == '__main__': unittest.main()
