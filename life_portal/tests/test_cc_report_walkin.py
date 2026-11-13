import unittest
from unittest.mock import Mock, patch
import frappe
from life_slimming.api import cc_report_walkin as api

class WalkinReportAccessTests(unittest.TestCase):
    def setUp(self):
        frappe.local.flags=frappe._dict(in_test=True)
        frappe.local.session=frappe._dict(user='agent@example.test')
        frappe.local.form_dict=frappe._dict()
        frappe.local.response=frappe._dict()
        def throw(message,exc=frappe.ValidationError):raise exc(message)
        for context in [patch.object(frappe,'throw',side_effect=throw),patch.object(api,'require_module'),patch.object(frappe,'get_roles',return_value=['Sales User']),patch.object(frappe,'db',Mock(exists=Mock(return_value=True)))]:
            context.start();self.addCleanup(context.stop)
    def tearDown(self):frappe.destroy()
    def test_details_are_not_read_for_a_denied_lead(self):
        with patch.object(frappe,'get_list',return_value=[]),patch.object(api,'walkin_details') as details:
            with self.assertRaises(frappe.PermissionError):api.run(lead='OTHER')
            details.assert_not_called()
    def test_allowed_details_reuse_existing_server_script(self):
        def read(**kwargs):frappe.response['message']={'lead':kwargs['lead'],'images':[]}
        with patch.object(frappe,'get_list',return_value=[frappe._dict(name='OWN')]) as query,patch.object(api,'walkin_details',side_effect=read):
            result=api.run(lead='OWN')
        self.assertEqual(query.call_args.kwargs['filters'],{'name':'OWN','lead_owner':'agent@example.test'})
        self.assertEqual(result,{'lead':'OWN','images':[]})
