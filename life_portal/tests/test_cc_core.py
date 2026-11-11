"""Lead journey reads must respect ownership; failed calls preserve outcomes."""
import unittest
from unittest.mock import Mock, patch
from datetime import datetime
import frappe
from life_slimming.api import cc_core as api


class Document(frappe._dict):
    def save(self, **kwargs):
        self.modified = 'v2'

    def set(self, key, value):
        self[key] = value

    def is_new(self):
        return False


class JourneyTests(unittest.TestCase):
    def setUp(self):
        frappe.local.flags = frappe._dict(in_test=True)
        frappe.local.session = frappe._dict(user='agent@example.test')
        frappe.local.form_dict = frappe._dict()
        self.doc = Document(name='LEAD1', lead_owner='agent@example.test', modified='v1',
            custom_cc_stage='SUCCESS', custom_cc_sub_status='Appointment Booked', status='Appointment Booked',
            custom_appointment_status='Booked', custom_call_count=2)
        self.track = Document(unreachable_streak=0)
        self.queries = []
        def get_all(dt, **kwargs):
            self.queries.append((dt, kwargs))
            if dt == 'Has Role':
                return [frappe._dict(role='Sales User')]
            return []
        def throw(message, exc=frappe.ValidationError):
            raise exc(message)
        for context in [patch.object(api, 'require_module'), patch.object(frappe.utils, 'now_datetime', return_value=datetime(2026,11,11,10)), patch.object(frappe, 'get_all', side_effect=get_all),
                        patch.object(frappe, 'get_roles', return_value=['Sales User']),
                        patch.object(frappe, 'get_doc', return_value=self.doc),
                        patch.object(frappe, 'new_doc', return_value=self.track),
                        patch.object(frappe, 'throw', side_effect=throw),
                        patch.object(frappe, 'db', Mock(exists=Mock(return_value=False)))]:
            context.start()
            self.addCleanup(context.stop)

    def tearDown(self):
        frappe.destroy()

    def test_summary_rejects_another_agents_lead(self):
        self.doc.lead_owner = 'other@example.test'
        with self.assertRaises(frappe.ValidationError):
            api.run(action='summary', leads='["LEAD1"]')
        self.assertFalse(any(dt == 'Lead' for dt, _ in self.queries))

    def test_agent_cannot_distribute(self):
        with self.assertRaises(frappe.PermissionError):
            api.run(action='dist_move', leads='["LEAD1"]', to_agents='["other@example.test"]')

    def test_report_is_owner_scoped(self):
        api.run(action='report', owners='["other@example.test"]', from_date='2026-11-01', to_date='2026-11-11')
        lead_query = next(args for dt, args in self.queries if dt == 'Lead')
        self.assertEqual(lead_query['filters']['lead_owner'], ['in', ['agent@example.test']])
        move_query = next(args for dt, args in self.queries if dt == 'CC Lead Activity Log')
        self.assertIn('lead', move_query['filters'])

    def test_failed_call_keeps_booked_outcome_and_schedules_retry(self):
        result = api.run(action='attempt', lead='LEAD1', reason='No Response', expected_modified='v1')
        self.assertTrue(result['ok'])
        self.assertEqual(self.doc.status, 'Appointment Booked')
        self.assertEqual(self.doc.custom_cc_stage, 'SUCCESS')
        self.assertEqual(self.doc.custom_cc_sub_status, 'Appointment Booked')
        self.assertEqual(self.doc.custom_call_count, 3)
        self.assertTrue(self.doc.custom_next_followup_date)
        self.assertEqual(self.track.unreachable_streak, 1)

    def test_stale_attempt_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            api.run(action='attempt', lead='LEAD1', reason='No Response', expected_modified='old')
        self.assertEqual(self.doc.custom_call_count, 2)

    def test_connected_save_updates_lead_and_tracking_in_one_request(self):
        with patch('life_slimming.api.server_scripts.cc_update_lead.run', return_value={'ok': 1, 'modified': 'v2'}) as save:
            result = api.run(action='save_connected', lead='LEAD1', values='{}', expected_modified='v1', next_action='Call back')
        save.assert_called_once()
        self.assertTrue(result['ok'])
        self.assertEqual(result['modified'], 'v2')
        self.assertEqual(self.track.last_call_result, 'Connected')
        self.assertEqual(self.track.unreachable_streak, 0)

    def test_conflicted_connected_save_does_not_change_tracking(self):
        with patch('life_slimming.api.server_scripts.cc_update_lead.run', return_value={'ok': 0, 'conflict': 1}):
            result = api.run(action='save_connected', lead='LEAD1', values='{}', expected_modified='old')
        self.assertEqual(result['conflict'], 1)
        self.assertIsNone(self.track.last_call_result)
