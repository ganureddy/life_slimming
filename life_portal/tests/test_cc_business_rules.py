import json
import unittest
from unittest.mock import patch,Mock
from datetime import datetime
import frappe
from life_slimming import cc_business_rules as rules
from life_portal.tests import test_cc_core as core_tests


class PaymentEvidenceTests(unittest.TestCase):
    def test_verified_number_matches_are_included(self):
        def query(dt,**kwargs):
            if dt=='Patient':return []
            return [frappe._dict(lead='L1',matched_patient='P1')]
        with patch.object(frappe,'get_all',side_effect=query):
            self.assertEqual(rules.linked_patients(['L1']),{'P1':'L1'})

    def test_payment_submission_orders_same_day_credit(self):
        def query(dt,**kwargs):
            if dt=='Patient':return [frappe._dict(name='P1',custom_lead='L1')]
            if dt=='LIFE CC Lead Track':return []
            if dt=='Sales Invoice':return [frappe._dict(name='I1',patient='P1',posting_date='2026-11-11',grand_total=100,outstanding_amount=0)]
            if dt=='Payment Entry Reference':return [frappe._dict(parent='PE1',reference_name='I1',allocated_amount=100)]
            if dt=='Payment Entry':return [frappe._dict(name='PE1',posting_date='2026-11-11')]
            if dt=='Version':
                name='PE1' if kwargs['filters']['ref_doctype']=='Payment Entry' else 'I1'
                return [frappe._dict(docname=name,creation='2026-11-11 10:30:00',data=json.dumps({'changed':[['docstatus',0,1]]}))]
            return []
        with patch.object(frappe,'get_all',side_effect=query):evidence=rules.paid_evidence(['L1'])
        events=[frappe._dict(lead='L1',agent='A',event_time='2026-11-11 10:00:00'),frappe._dict(lead='L1',agent='B',event_time='2026-11-11 11:00:00')]
        self.assertEqual(rules.credit_for_events(events,evidence,lambda u:u),{'L1':'A'})
        self.assertFalse(evidence['L1']['credit_provisional'])

    def test_booked_is_required_and_paid_owner_changes_are_rejected(self):
        lead=frappe._dict(name='L1',status='Lead',custom_cc_stage='UNTOUCHED')
        self.assertFalse(rules.booked(lead))
        def throw(message):raise frappe.ValidationError(message)
        with patch.object(rules,'paid_evidence',return_value={'L1':{'paid':100,'has_bill':True}}),patch.object(frappe,'throw',side_effect=throw):
            with self.assertRaises(frappe.ValidationError):rules.validate_lead_update(lead,{'lead_owner':'new'})
            with self.assertRaises(frappe.ValidationError):rules.validate_lead_update(lead,{'custom_cc_sub_status':'No Response'})

    def test_permission_editors_are_only_verified_accounts(self):
        self.assertEqual(rules.PERMISSION_EDITORS,{'bhuvan@lifescc.com','narendhar@lifescc.com'})
        self.assertNotIn('Administrator',rules.PERMISSION_EDITORS)


class PaidLeadRegressionTests(core_tests.JourneyTests):
    def test_paid_lead_without_booking_never_downgrades_on_failed_call(self):
        self.doc.status='Lead';self.doc.custom_cc_stage='UNTOUCHED';self.doc.custom_cc_sub_status='Lead';self.doc.custom_appointment_status='Not Booked'
        with patch('life_slimming.api.cc_core.paid_evidence',return_value={'LEAD1':{'paid':100,'has_bill':True,'joined_on':'2026-11-11','paid_at':'2026-11-11 10:00:00'}}):
            from life_slimming.api.cc_core import run
            run(action='attempt',lead='LEAD1',reason='No Response',expected_modified='v1')
        self.assertEqual(self.doc.status,'Lead')
        self.assertEqual(self.doc.custom_cc_stage,'UNTOUCHED')

    def test_generic_system_manager_cannot_edit_permission_list(self):
        self.doc.lead_owner='agent@example.test'
        def records(dt,**kwargs):
            return [frappe._dict(role='System Manager')] if dt=='Has Role' else []
        with patch.object(frappe,'get_all',side_effect=records),patch.object(frappe,'get_roles',return_value=['System Manager']):
            from life_slimming.api.cc_core import run
            with self.assertRaises(frappe.ValidationError):run(action='rule_save',rule=json.dumps({'rule_name':'Movers','rule_type':'Permissions','allowed_users':['someone']}))

    def test_md_portal_role_can_move_but_cannot_edit_permission_list(self):
        from life_slimming.api.cc_core import run
        def value(dt,name,field,*args,**kwargs):
            return 'MD' if dt=='User' and field=='custom_portal_role' else None
        with patch.object(frappe.db,'get_value',side_effect=value):
            permission=run(action='perm')
        self.assertTrue(permission['can_move'])
        self.assertFalse(permission['can_edit_perm'])
