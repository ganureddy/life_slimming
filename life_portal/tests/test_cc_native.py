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
        with patch.object(frappe, 'get_all', side_effect=[roles, [{'name':'LEAD-1'}], []]) as query:
            leads.run.__wrapped__()
        return query.call_args_list[1], frappe.response['message']

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

    def test_agent_search_can_find_other_owners(self):
        for args in ({'query': 'Other client'}, {'phone': '9876543210'},
                     {'query': 'LEAD-1', 'detail': 1}):
            with self.subTest(args=args):
                frappe.local.form_dict = frappe._dict(args)
                query, response = self.read_leads(['Sales User'])
                self.assertFalse(any(f[0] == 'lead_owner' for f in query.kwargs['filters']))
                self.assertFalse(response['scoped_to_owner'])
                self.assertEqual(response['rows'][0]['name'], 'LEAD-1')

    def test_page_size_clamped(self):
        query, _ = self.read_leads(['Sales User'], page_size=100000, start=-1)
        self.assertEqual(query.kwargs['limit_page_length'], 500)
        self.assertEqual(query.kwargs['limit_start'], 0)

    def test_essential_report_keeps_owner_scope_without_financial_reads(self):
        frappe.local.session.user = 'lifescc13@gmail.com'
        frappe.local.form_dict.update(view='appointments', agent_owner='other@example.test')
        with patch.object(frappe, 'get_meta', return_value=Mock(has_field=lambda field: True)), \
             patch.object(frappe, 'get_list', return_value=[]) as permission_query, \
             patch.object(frappe, 'get_all', side_effect=[[], [{'name':'LEAD-1'}], [], []]) as query:
            report.run.__wrapped__()
        self.assertEqual([c.args[0] for c in query.call_args_list], ['Has Role','Lead'])
        permission_query.assert_called_once()
        for call in query.call_args_list[1:]:
            self.assertEqual(call.kwargs['filters']['lead_owner'], 'lifescc13@gmail.com')
            self.assertIn('custom_visit_status', call.kwargs['fields'])
            self.assertEqual([f[0] for f in call.kwargs['or_filters']], ['custom_appointment_date_and_time', 'custom_posting_date', 'creation'])
        self.assertTrue(frappe.response['message']['restricted_to_owner'])
        self.assertEqual(frappe.response['message']['count'], 1)
        self.assertEqual(frappe.response['message']['financial_events'], [])

    def test_visit_report_recognizes_assigned_agent_without_email_pattern(self):
        self.db.exists.return_value = True
        frappe.local.form_dict.update(view='appointments', agent_owner='other@example.test')
        with patch.object(frappe, 'get_meta', return_value=Mock(has_field=lambda field: False)), \
             patch.object(frappe, 'get_list', return_value=[]), \
             patch.object(frappe, 'get_all', side_effect=[[], [], [], []]) as query:
            report.run.__wrapped__()
        for call in query.call_args_list[1:]:
            self.assertEqual(call.kwargs['filters']['lead_owner'], 'agent@example.test')
        self.assertTrue(frappe.response['message']['restricted_to_owner'])

    def test_visit_report_reads_every_page_and_deduplicates_cohorts(self):
        frappe.local.session.user = 'Administrator'
        frappe.local.form_dict.update(view='appointments')
        batch = [{'name': 'LEAD-' + str(i)} for i in range(500)]
        with patch.object(frappe, 'get_meta', return_value=Mock(has_field=lambda field: False)), \
             patch.object(frappe, 'get_all', side_effect=[batch, [{'name': 'LEAD-500'}],
                                                        [{'name': 'LEAD-0'}], []]) as query:
            report.run.__wrapped__()
        self.assertEqual([c.kwargs['limit_start'] for c in query.call_args_list], [0, 500])
        self.assertTrue(all(c.kwargs['limit_page_length'] == 500 for c in query.call_args_list))
        self.assertEqual(frappe.response['message']['count'], 501)

    def test_visit_report_respects_permissions_for_non_agent_readers(self):
        frappe.local.form_dict.update(view='appointments')
        with patch.object(frappe, 'get_meta', return_value=Mock(has_field=lambda field: False)), \
             patch.object(frappe, 'get_all', return_value=[]) as unrestricted, \
             patch.object(frappe, 'get_list', side_effect=[[], [{'name': 'LEAD-1'}], [], []]) as permitted:
            report.run.__wrapped__()
        self.assertEqual([c.args[0] for c in unrestricted.call_args_list], ['Has Role'])
        self.assertEqual([c.args[0] for c in permitted.call_args_list], ['Lead'] * 2)
        self.assertEqual(frappe.response['message']['count'], 1)

    def test_visit_report_permission_denial_stops_data_reads(self):
        frappe.local.form_dict.update(view='appointments')
        with patch.object(frappe, 'get_all', return_value=[]) as query, \
             patch.object(frappe, 'get_list', side_effect=frappe.PermissionError), \
             patch.object(frappe, 'get_meta') as meta:
            with self.assertRaises(frappe.PermissionError):
                report.run.__wrapped__()
        self.assertEqual([c.args[0] for c in query.call_args_list], ['Has Role'])
        meta.assert_not_called()

    def test_full_visit_report_still_returns_financial_contract(self):
        frappe.local.session.user = 'Administrator'
        frappe.local.form_dict.update(view='full')
        with patch.object(frappe, 'get_meta', return_value=Mock(has_field=lambda field: False)), \
             patch.object(frappe, 'get_all', return_value=[]) as query:
            report.run.__wrapped__()
        result = frappe.response['message']
        self.assertTrue(result['ok'])
        self.assertEqual(result['financial_events'], [])
        self.assertIn('cc_invoice_report_summary', result)
        self.assertIn('agent_report_summary', result)
        cohort_calls = [call for call in query.call_args_list if call.kwargs.get('or_filters')]
        self.assertEqual(len(cohort_calls), 1)

    def test_guest_rejected_before_any_reads(self):
        frappe.local.session.user = 'Guest'
        with patch.object(frappe, 'get_all') as query:
            with self.assertRaises(frappe.PermissionError): leads.run()
            with self.assertRaises(frappe.PermissionError): report.run()
            query.assert_not_called()

if __name__ == '__main__': unittest.main()
