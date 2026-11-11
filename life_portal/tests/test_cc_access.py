import unittest
from unittest.mock import Mock, patch
import frappe
from life_slimming.api import cc_access


class CCAccessTests(unittest.TestCase):
    def setUp(self):
        frappe.local.flags = frappe._dict(in_test=True)
        self.addCleanup(frappe.destroy)
        for name, value in [('require_module', Mock()), ('frappe', Mock())]:
            ctx=patch.object(cc_access,name,value)
            ctx.start();self.addCleanup(ctx.stop)
        cc_access.frappe.throw.side_effect=frappe.ValidationError
        cc_access.frappe.session.user="agent@example.test"

    def test_invoice_access_requires_cc_module(self):
        cc_access.require_module.side_effect=frappe.PermissionError
        with self.assertRaises(frappe.PermissionError):
            cc_access.invoices()
        cc_access.frappe.get_all.assert_not_called()

    def test_invoice_listing_is_read_only_and_paginated(self):
        cc_access.invoices(query='Alice',start=40)
        cc_access.require_module.assert_called_once_with('leads')
        args=cc_access.frappe.get_all.call_args.kwargs
        self.assertEqual(args['limit_start'],40)
        self.assertEqual(args['limit_page_length'],40)
        cc_access.frappe.db.set_value.assert_not_called()

    def test_recovery_rejects_non_junk_and_booked_clients(self):
        for sub, appointment in [('Do Not Contact',''), ('Invalid Number',''), ('Junk/Wrong Call','Visited Booked')]:
            doc=Mock();doc.get.side_effect=lambda key: {'custom_cc_sub_status':sub,'custom_appointment_status':appointment}.get(key)
            cc_access.frappe.get_doc.return_value=doc
            with self.assertRaises(frappe.ValidationError):
                cc_access.recover_junk('LEAD1')
            doc.save.assert_not_called()

    def test_junk_recovery_saves_and_audits(self):
        doc=Mock();doc.get.side_effect=lambda key: {'custom_cc_sub_status':'Junk/Wrong Call'}.get(key)
        cc_access.frappe.get_doc.return_value=doc
        cc_access.recover_junk('LEAD1')
        doc.update.assert_called_once_with({'status':'Lead','custom_cc_stage':'UNTOUCHED','custom_cc_sub_status':''})
        doc.save.assert_called_once_with(ignore_permissions=True)
        doc.add_comment.assert_called_once()

    def read_updates(self, roles=None, records=None, **args):
        cc_access.frappe.get_roles.return_value=roles or ['Sales User']
        cc_access.frappe.db.sql.return_value=records or []
        return cc_access.lead_updates('2026-11-01','2026-11-10',**args)

    def test_updates_scope_agents_to_owned_leads(self):
        result=self.read_updates()
        query,params=cc_access.frappe.db.sql.call_args.args
        self.assertIn('l.lead_owner = %(user)s',query)
        self.assertEqual(params['user'],'agent@example.test')
        self.assertEqual(str(params['until']),'2026-11-11')
        self.assertTrue(result['scoped_to_owner'])

    def test_updates_managers_see_team_history(self):
        result=self.read_updates(roles=['Sales Manager'])
        query,params=cc_access.frappe.db.sql.call_args.args
        self.assertNotIn('l.lead_owner = %(user)s',query)
        self.assertIn('ORDER BY v.creation DESC, v.name DESC',query)
        self.assertFalse(result['scoped_to_owner'])

    def test_updates_reject_reversed_range(self):
        with self.assertRaises(frappe.ValidationError):
            cc_access.lead_updates('2026-11-10','2026-11-01')
        cc_access.frappe.db.sql.assert_not_called()

    def test_updates_pagination_and_safe_fields(self):
        record={'lead':'LEAD1','data':'{"changed":[["status","Lead","Followup"],["mobile_no","123","456"]]}'}
        result=self.read_updates(records=[record]*51,start=50)
        self.assertEqual(len(result['rows']),50)
        self.assertTrue(result['more'])
        self.assertEqual(result['start'],50)
        self.assertEqual(result['rows'][0]['changes'],[{'field':'status','label':'Lead status','before':'Lead','after':'Followup'}])
        self.assertNotIn('data',result['rows'][0])

    def test_updates_handle_bad_history(self):
        result=self.read_updates(records=[{'data':value} for value in ('bad','[]','{"changed":null}','{"changed":[[[],0,1]]}')])
        self.assertTrue(all(row['changes']==[] for row in result['rows']))

    def test_updates_require_cc_access(self):
        cc_access.require_module.side_effect=frappe.PermissionError
        with self.assertRaises(frappe.PermissionError):
            cc_access.lead_updates('2026-11-01','2026-11-10')
        cc_access.frappe.db.sql.assert_not_called()


if __name__ == '__main__':
    unittest.main()
