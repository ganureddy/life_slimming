"""No site writes or calls: callback linking, summaries and search access."""
import unittest
from unittest.mock import Mock, patch

import frappe
from life_slimming import convox_lead_sync as sync
from life_slimming.api import convox


class LeadSyncTest(unittest.TestCase):
    def setUp(self):
        frappe.local.flags = frappe._dict(in_test=True)
        frappe.local.session = frappe._dict(user='agent@example.test')
        self.db = Mock()
        self.db.sql.return_value = [frappe._dict(name='LEAD-1')]
        self.cache = Mock()
        self.cache.get_value.return_value = None
        self.event = frappe._dict(agent_id='AGENT1', call_reference='REF-1', mobile_number='+91 98765 43210', lead_id='VENDOR-1')
        for patcher in [patch.object(frappe, 'db', self.db), patch.object(frappe, 'cache', self.cache),
                        patch.object(frappe, 'get_all', return_value=['agent@example.test'])]:
            patcher.start(); self.addCleanup(patcher.stop)

    def tearDown(self):
        frappe.destroy()

    def test_exact_phone_and_agent_owner_not_vendor_lead_id(self):
        self.assertEqual(sync.resolve_lead(self.event), 'LEAD-1')
        query, args = self.db.sql.call_args.args
        self.assertIn('lead_owner', query)
        self.assertIn('COALESCE(phone', query)
        self.assertEqual(args['numbers'], ('9876543210', '919876543210', '09876543210'))
        self.assertNotIn('VENDOR-1', str(args))

    def test_ambiguous_or_unmapped_calls_do_not_update_arbitrary_lead(self):
        self.db.sql.return_value = [frappe._dict(name='LEAD-1'), frappe._dict(name='LEAD-2')]
        self.assertIsNone(sync.resolve_lead(self.event))
        with patch.object(frappe, 'get_all', return_value=[]):
            self.assertIsNone(sync.resolve_lead(self.event))

    def test_known_dial_reference_checks_phone_and_supports_manager_calls(self):
        self.cache.get_value.return_value = 'LEAD-MANAGER-DIAL'
        self.db.get_value.return_value = frappe._dict(mobile_no='9876543210', phone='')
        self.assertEqual(sync.resolve_lead(self.event), 'LEAD-MANAGER-DIAL')
        self.db.get_value.return_value = frappe._dict(mobile_no='9123456789', phone='')
        self.assertEqual(sync.resolve_lead(self.event), 'LEAD-1')

    def test_unanswered_event_updates_summary_without_changing_sales_status(self):
        doc = Mock()
        latest = frappe._dict(name='EVENT-1', call_reference='REF-1', call_status='NO ANSWER',
            disposition='No Response', call_datetime='2026-10-12 14:00:00', call_duration=0)
        meta = Mock(); meta.has_field.return_value = True
        with patch.object(sync, 'resolve_lead', return_value='LEAD-1'), patch.object(frappe, 'get_meta', return_value=meta):
            for _ in range(2):
                self.db.sql.side_effect = [[], [latest], [(1,)]]
                sync.sync_event(doc)
                values = self.db.set_value.call_args.args[2]
                self.assertEqual(values['custom_convox_call_count'], 1)
                self.assertEqual(values['custom_convox_call_status'], 'NO ANSWER')
                self.assertEqual(values['custom_convox_call_duration'], 0)
                self.assertNotIn('status', values)
                self.assertNotIn('custom_cc_sub_status', values)
                self.assertFalse(self.db.set_value.call_args.kwargs['update_modified'])
        doc.db_set.assert_called_with('crm_lead', 'LEAD-1', update_modified=False)
        self.assertIn('ORDER BY call_datetime DESC', self.db.sql.call_args_list[-2].args[0])

    def test_missing_schema_or_ambiguous_match_does_not_write(self):
        meta = Mock(); meta.has_field.return_value = False
        with patch.object(frappe, 'get_meta', return_value=meta):
            sync.sync_event(Mock())
        meta.has_field.return_value = True
        with patch.object(frappe, 'get_meta', return_value=meta), patch.object(sync, 'resolve_lead', return_value=None):
            sync.sync_event(Mock())
        self.db.set_value.assert_not_called()

    def test_crm_search_is_scoped_for_agents_and_allows_manager_scope(self):
        with patch.object(convox, '_identity'), patch.object(frappe, 'get_roles', return_value=['Sales User']):
            self.assertEqual(convox.find_leads('9876543210')['rows'][0].name, 'LEAD-1')
            self.assertEqual(self.db.sql.call_args.args[1]['owner'], 'agent@example.test')
            with self.assertRaises(frappe.ValidationError):
                convox.find_leads('+449876543210')
        with patch.object(convox, '_identity'), patch.object(frappe, 'get_roles', return_value=['System Manager']):
            convox.find_leads('9876543210')
            self.assertNotIn('owner', self.db.sql.call_args.args[1])


if __name__ == '__main__':
    unittest.main()
