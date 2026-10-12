"""Appointment status authorization and stale-update protection."""
import unittest
from unittest.mock import Mock, patch
import frappe
from life_slimming.api import cc_appointment_status as api


class AppointmentStatusTests(unittest.TestCase):
    def setUp(self):
        frappe.local.session = frappe._dict(user='editor')
        frappe.local.flags = frappe._dict(in_test=True)

    def test_only_requested_roles_can_edit(self):
        for role in ['System Manager', 'Call Center Export']:
            with patch.object(frappe, 'get_roles', return_value=[role]):
                api.authorize()
        for role in ['Sales User', 'Sales Manager', 'Branch Sales Invoice']:
            with patch.object(frappe, 'get_roles', return_value=[role]):
                with self.assertRaises(frappe.PermissionError):
                    api.authorize()

    def test_guest_rejected(self):
        frappe.local.session.user = 'Guest'
        with self.assertRaises(frappe.PermissionError):
            api.authorize()

    def test_updates_only_status_and_saves_document(self):
        doc = Mock(name='LEAD1', modified='v1', custom_appointment_status='Booked')
        with patch.object(api, 'authorize'), patch.object(api, 'status_options', return_value=['Visited']), patch.object(frappe, 'get_doc', return_value=doc):
            api.update('LEAD1', 'Visited', 'v1')
        self.assertEqual(doc.custom_appointment_status, 'Visited')
        doc.save.assert_called_once_with(ignore_permissions=True)

    def test_invalid_stale_and_locked_changes_rejected(self):
        for status, modified, current in [('Invalid', 'v1', 'Booked'), ('Visited', 'old', 'Booked'), ('Visited', '', 'Booked'), ('Visited', 'v1', 'Visited Booked')]:
            doc = Mock(modified='v1', custom_appointment_status=current)
            with patch.object(api, 'authorize'), patch.object(api, 'status_options', return_value=['Visited']), patch.object(frappe, 'get_doc', return_value=doc):
                with self.assertRaises(frappe.ValidationError):
                    api.update('LEAD1', status, modified)
            doc.save.assert_not_called()
