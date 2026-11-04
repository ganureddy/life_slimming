"""No site writes or calls: callback linking, summaries and search access."""
import json
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
        self.version = Mock()
        self.make_version = Mock(return_value=self.version)
        self.event = frappe._dict(agent_id='AGENT1', call_reference='REF-1', mobile_number='+91 98765 43210', lead_id='VENDOR-1')
        for patcher in [patch.object(frappe, 'db', self.db), patch.object(frappe, 'cache', self.cache),
                        patch.object(frappe, 'get_all', return_value=['agent@example.test']),
                        patch.object(frappe, 'get_doc', self.make_version)]:
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

    def disposition_meta(self):
        options = {
            'status': 'Not Response\nCall Disconnected\nNot interested\nInterested\nCall Back\nAppointment Booked',
            'custom_cc_stage': 'FOLLOW-UP\nLOST\nSUCCESS',
            'custom_cc_sub_status': 'No Response\nCall Disconnected\nNot interested\nVery Positive\nCallback: Scheduled\nAppointment Booked',
        }
        meta = Mock()
        meta.get_field.side_effect = lambda name: frappe._dict(options=options[name])
        return meta

    def test_disposition_mapping_prioritizes_specific_vendor_disposition(self):
        meta = self.disposition_meta()
        values = sync.disposition_values(frappe._dict(disposition='CallDisconnected', disposition_2='Very Positive'), meta)
        self.assertEqual(values, {'status': 'Interested', 'custom_cc_stage': 'FOLLOW-UP', 'custom_cc_sub_status': 'Very Positive'})
        self.assertEqual(sync.disposition_values(frappe._dict(disposition='NR'), meta)['status'], 'Not Response')
        self.assertEqual(sync.disposition_values(frappe._dict(disposition='CNA--Ringing/No Answer'), meta)['custom_cc_sub_status'], 'No Response')
        for value in ['CONGESTION', 'ANSWERED', 'ANA--Normal Call Clearing', 'Hungup']:
            self.assertEqual(sync.disposition_values(frappe._dict(disposition=value), meta), {})

    def test_saved_disposition_updates_actual_lead_status(self):
        event = frappe._dict(name='EVENT-1', agent_id='AGENT1', disposition='Not Interested')
        self.db.get_value.return_value = frappe._dict(custom_cc_sub_status='Very Positive')
        sync.sync_disposition(event, 'LEAD-1', self.disposition_meta())
        self.db.set_value.assert_called_once_with('Lead', 'LEAD-1', {
            'status': 'Not interested', 'custom_cc_stage': 'LOST', 'custom_cc_sub_status': 'Not interested'})
        audit = self.make_version.call_args.args[0]
        self.assertEqual((audit['doctype'], audit['ref_doctype'], audit['docname']),
                         ('Version', 'Lead', 'LEAD-1'))
        self.assertEqual(audit['owner'], 'agent@example.test')
        data = json.loads(audit['data'])
        self.assertEqual(data['changed'], [
            ['custom_cc_stage', None, 'LOST'],
            ['custom_cc_sub_status', 'Very Positive', 'Not interested'],
            ['status', None, 'Not interested'],
        ])
        self.assertEqual(data['convox_event'], 'EVENT-1')
        self.assertEqual(data['source'], 'ConVox')
        self.version.insert.assert_called_once_with(ignore_permissions=True)

    def test_recording_retry_does_not_undo_manual_edit(self):
        event = frappe._dict(name='EVENT-1', disposition='NR')
        self.db.get_value.return_value = frappe._dict(custom_convox_last_event='EVENT-1', custom_convox_disposition='NR', custom_cc_sub_status='Very Positive')
        sync.sync_disposition(event, 'LEAD-1', self.disposition_meta())
        self.db.set_value.assert_not_called()
        self.make_version.assert_not_called()

    def test_repeated_disposition_creates_only_one_history_entry(self):
        event = frappe._dict(name='EVENT-1', agent_id='AGENT1', disposition='NR')
        current = frappe._dict(status='Call Back', custom_cc_stage='FOLLOW-UP',
                              custom_cc_sub_status='Callback: Scheduled')
        self.db.get_value.return_value = current
        self.db.set_value.side_effect = lambda doctype, name, values: current.update(values)
        sync.sync_disposition(event, 'LEAD-1', self.disposition_meta())
        sync.sync_disposition(event, 'LEAD-1', self.disposition_meta())
        self.db.set_value.assert_called_once()
        self.make_version.assert_called_once()
        self.assertEqual(json.loads(self.make_version.call_args.args[0]['data'])['changed'], [
            ['custom_cc_sub_status', 'Callback: Scheduled', 'No Response'],
            ['status', 'Call Back', 'Not Response'],
        ])

    def test_unrecognized_disposition_creates_no_lead_history(self):
        sync.sync_disposition(frappe._dict(disposition='CHANUNAVAIL'),
                              'LEAD-1', self.disposition_meta())
        self.db.set_value.assert_not_called()
        self.make_version.assert_not_called()

    def test_ambiguous_agent_creates_no_status_or_history_update(self):
        self.db.get_value.return_value = frappe._dict(status='Call Back')
        with patch.object(frappe, 'get_all', return_value=['one@example.test', 'two@example.test']):
            sync.sync_disposition(frappe._dict(agent_id='AGENT1', disposition='NR'),
                                  'LEAD-1', self.disposition_meta())
        self.db.set_value.assert_not_called()
        self.make_version.assert_not_called()

    def test_history_failure_propagates_so_callback_transaction_can_roll_back(self):
        self.db.get_value.return_value = frappe._dict(status='Call Back')
        self.version.insert.side_effect = RuntimeError('History insert failed')
        with self.assertRaisesRegex(RuntimeError, 'History insert failed'):
            sync.sync_disposition(frappe._dict(agent_id='AGENT1', disposition='NR'),
                                  'LEAD-1', self.disposition_meta())
        self.db.commit.assert_not_called()

    def test_locked_status_requires_call_center_export_agent(self):
        event = frappe._dict(name='EVENT-1', agent_id='AGENT1', disposition='Very Positive')
        self.db.get_value.return_value = frappe._dict(custom_cc_sub_status='Do Not Contact')
        with patch.object(frappe, 'get_roles', return_value=['Sales User']):
            sync.sync_disposition(event, 'LEAD-1', self.disposition_meta())
        self.db.set_value.assert_not_called()
        self.make_version.assert_not_called()
        with patch.object(frappe, 'get_roles', return_value=['Call Center Export']):
            sync.sync_disposition(event, 'LEAD-1', self.disposition_meta())
        self.assertEqual(self.db.set_value.call_args.args[2]['status'], 'Interested')

    def test_global_phone_fallback_requires_unique_lead(self):
        self.db.sql.side_effect = [[], [frappe._dict(name='OTHER-OWNER')]]
        self.assertEqual(sync.resolve_lead(self.event), 'OTHER-OWNER')
        self.db.sql.side_effect = [[], [frappe._dict(name='ONE'), frappe._dict(name='TWO')]]
        self.assertIsNone(sync.resolve_lead(self.event))

    def test_crm_search_is_global_for_authorized_agents_and_managers(self):
        with patch.object(convox, '_identity'), patch.object(frappe, 'get_roles', return_value=['Sales User']):
            self.assertEqual(convox.find_leads('9876543210')['rows'][0].name, 'LEAD-1')
            self.assertNotIn('owner', self.db.sql.call_args.args[1])
            with self.assertRaises(frappe.ValidationError):
                convox.find_leads('+449876543210')
        with patch.object(convox, '_identity'), patch.object(frappe, 'get_roles', return_value=['System Manager']):
            convox.find_leads('9876543210')
            self.assertNotIn('owner', self.db.sql.call_args.args[1])


if __name__ == '__main__':
    unittest.main()
