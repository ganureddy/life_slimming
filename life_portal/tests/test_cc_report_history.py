import unittest
from unittest.mock import Mock,patch
import frappe
from life_slimming.api import cc_report_history as api


class HistoryTests(unittest.TestCase):
    def setUp(self):
        frappe.local.flags=frappe._dict(in_test=True)
        frappe.local.session=frappe._dict(user='agent@example.test')
        frappe.local.form_dict=frappe._dict()
        self.records=[];self.queries=[]
        def get_all(dt,**kwargs):
            self.queries.append((dt,kwargs))
            if dt=='User':return [frappe._dict(name='agent@example.test',full_name='Agent',custom_convox_agent_id='101')]
            return self.records
        def throw(message,exc=frappe.ValidationError):raise exc(message)
        for context in [patch.object(api,'require_module'),patch.object(frappe,'get_roles',return_value=['Sales User']),patch.object(frappe,'get_all',side_effect=get_all),patch.object(frappe,'db',Mock(exists=Mock(return_value=True))),patch.object(frappe,'get_meta',return_value=Mock(has_field=Mock(return_value=True))),patch.object(frappe,'throw',side_effect=throw)]:
            context.start();self.addCleanup(context.stop)
    def tearDown(self):frappe.destroy()

    def test_calls_are_owner_scoped_and_phone_masked(self):
        self.records=[frappe._dict(name='C1',agent='agent@example.test',started_on='2026-11-11 10:00:00',mobile_number='9876543210',lead='L1',talk_seconds=30)]
        result=api.history(kind='mobile',from_date='2026-11-11',to_date='2026-11-11')
        self.assertEqual(self.queries[-1][1]['filters']['agent'],['in',['agent@example.test']])
        self.assertEqual(result['rows'][0]['phone'],'••••3210')
        self.assertNotIn('mobile_number',result['rows'][0])
        self.assertNotIn('recording',self.queries[-1][1]['fields'])

    def test_requested_other_agent_does_not_query_calls(self):
        result=api.history(kind='convox',agents='["other@example.test"]',from_date='2026-11-11',to_date='2026-11-11')
        self.assertEqual(result['rows'],[])
        self.assertEqual([dt for dt,k in self.queries],['User'])

    def test_recording_access_cannot_bypass_call_owner(self):
        with self.assertRaises(frappe.PermissionError):api.recording(kind='convox',id='OTHER')
        self.assertEqual(self.queries[-1][1]['filters']['agent_id'],['in',['101']])

    def test_changed_values_are_masked_and_dates_preserved(self):
        self.assertEqual(api.masked('9876543210'),'••••3210')
        self.assertEqual(api.masked('2026-11-11 10:00:00'),'2026-11-11 10:00:00')

    def test_recording_urls_preserve_private_files_and_normalize_pbx(self):
        self.assertEqual(api.safe_recording('/private/files/call.mp3','mobile'),'/private/files/call.mp3')
        self.assertEqual(api.safe_recording('http://192.168.0.193/call.wav','convox'),'https://lifeslimming.deepijatel.in/call.wav')
        self.assertEqual(api.safe_recording('https://example.test/call.mp3','convox'),'')
        self.assertEqual(api.safe_recording('javascript:alert(1)','mobile'),'')
