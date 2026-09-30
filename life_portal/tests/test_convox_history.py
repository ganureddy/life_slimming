"""Call-history matching, access scope and pagination without live records."""
import unittest
from unittest.mock import Mock, patch
import frappe
from life_slimming.api import convox


class HistoryTest(unittest.TestCase):
    def setUp(self):
        frappe.local.flags = frappe._dict(in_test=True)
        self.user = frappe._dict(custom_convox_agent_id='AGENT1')
        self.lead = frappe._dict(name='LEAD-1', lead_name='Fixture', mobile_no='+91 98765-43210')
        self.db = Mock()
        self.db.exists.return_value = True
        self.db.sql.side_effect = [[frappe._dict(total_events=51, total_calls=26)], [frappe._dict(name='event-51', recording_file_name='https://192.168.0.193/calls/2026-09-29/out/fixture.WAV')]]
        meta = Mock()
        meta.has_field.side_effect = lambda field: field != 'recording_received_on'
        meta.get_field.side_effect = lambda field: frappe._dict(label=field)
        for patcher in [patch.object(convox, '_identity', return_value=(self.user, {})),
                        patch.object(convox, '_lead', return_value=self.lead),
                        patch.object(frappe, 'get_roles', return_value=['Sales User']),
                        patch.object(frappe, 'get_meta', return_value=meta), patch.object(frappe, 'db', self.db)]:
            patcher.start(); self.addCleanup(patcher.stop)

    def test_mobile_variants_agent_scope_and_full_history_page(self):
        result = convox.lead_history('LEAD-1', 50)
        query, args = self.db.sql.call_args.args
        self.assertEqual(args['numbers'], ('9876543210', '919876543210', '09876543210'))
        self.assertEqual(args['agent'], 'AGENT1')
        self.assertIn('agent_id = %(agent)s', query)
        self.assertNotIn('lead_id =', query)
        self.assertIn('OFFSET %(start)s', query)
        self.assertEqual(args['start'], 50)
        self.assertEqual(result['events'][0]['recording_file_name'], 'https://lifeslimming.deepijatel.in/calls/2026-09-29/out/fixture.WAV')
        self.assertEqual(result['total_calls'], 26)
        self.assertFalse(result['has_more'])
        self.assertIn('COUNT(DISTINCT', self.db.sql.call_args_list[0].args[0])
        self.assertNotIn('payload_json', query)
        self.assertNotIn('recording_received_on', query)
        self.assertIn('recording_file_name', query)

    def test_manager_sees_all_agents_for_authorized_mobile(self):
        with patch.object(frappe, 'get_roles', return_value=['System Manager']):
            result = convox.lead_history('LEAD-1')
        self.assertEqual(result['scope'], 'all_agents')
        self.assertNotIn('agent_id =', self.db.sql.call_args.args[0])

    def test_recording_host_replacement_preserves_path_and_other_hosts(self):
        path = '/calls/2026-09-29/out/9515400243_ConVoxProcess_Niharika___NA_Hyderabad_ConVoxProcess_20260929184903.WAV'
        self.assertEqual(convox.recording_url('https://192.168.0.193' + path), convox.ORIGIN + path)
        self.assertEqual(convox.recording_url('https://192.168.0.193.example.org' + path), 'https://192.168.0.193.example.org' + path)
        self.assertEqual(convox.recording_url('/files/call.wav'), '/files/call.wav')

    def test_denied_lead_never_queries_events(self):
        with patch.object(convox, '_lead', side_effect=frappe.PermissionError):
            with self.assertRaises(frappe.PermissionError): convox.lead_history('OTHER')
        self.db.sql.assert_not_called()

    def test_invalid_phone_and_page_never_query(self):
        for start in [-1, 'bad']:
            with self.assertRaises(frappe.ValidationError): convox.lead_history('LEAD-1', start)
        self.lead.mobile_no = '123'
        with self.assertRaises(frappe.ValidationError): convox.lead_history('LEAD-1')
        self.db.sql.assert_not_called()

    def test_unmapped_agent_cannot_read_history(self):
        self.user.custom_convox_agent_id = ''
        with self.assertRaises(frappe.PermissionError): convox.lead_history('LEAD-1')
        self.db.sql.assert_not_called()


if __name__ == '__main__': unittest.main()
