"""Read-only unit checks. Run with bench env Python; no site initialization required."""
import importlib
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import frappe
from life_slimming.api._runtime import script_endpoint
from life_slimming.api.auth import login_context
from life_slimming.api.server_scripts.portal_is_system_manager import run as roles_api
from life_slimming.api.server_scripts.get_client_transfer_web_details import run as patient_api


class PortalMigrationTest(unittest.TestCase):
    def setUp(self):
        frappe.local.flags = frappe._dict(in_test=True)
        frappe.local.session = frappe._dict(user='test@example.test', data=frappe._dict())
        frappe.local.form_dict = frappe._dict(original='kept')
        frappe.local.response = frappe._dict()

    def tearDown(self):
        frappe.destroy()

    def test_all_native_modules_are_registered_without_executing_bodies(self):
        catalog = json.loads((Path(__file__).parents[1] / 'api/catalog.json').read_text())
        self.assertEqual(catalog['count'], 141)
        methods = set()
        for item in catalog['endpoints']:
            fn = importlib.import_module(item['method'].rsplit('.', 1)[0]).run
            self.assertIn(fn, frappe.whitelisted)
            self.assertEqual(fn in frappe.guest_methods, item['allow_guest'])
            self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[fn], ['POST'])
            methods.add(item['method'])
        self.assertEqual(len(methods), 141)
        self.assertEqual(sum(item['allow_guest'] for item in catalog['endpoints']), 2)

    def test_request_arguments_are_restored_after_exception(self):
        previous = frappe.local.form_dict
        @script_endpoint()
        def fails(**kwargs):
            self.assertEqual(frappe.form_dict['branch'], 'TEST')
            self.assertEqual(frappe.form_dict['original'], 'kept')
            raise ValueError('expected')
        with self.assertRaises(ValueError):
            fails(branch='TEST')
        self.assertIs(frappe.local.form_dict, previous)

    def test_guest_cannot_call_authenticated_api_even_directly(self):
        frappe.local.session.user = 'Guest'
        with self.assertRaises(frappe.PermissionError):
            roles_api()

    def test_role_api_uses_current_user_not_supplied_user(self):
        with patch('frappe.get_roles', return_value=['Employee']) as get_roles:
            roles_api(user='Administrator')
        get_roles.assert_called_once_with('test@example.test')
        self.assertEqual(frappe.response['message']['is_sys_mgr'], 0)
        self.assertEqual(frappe.response['message']['user'], 'test@example.test')

    def test_patient_permission_denial_happens_before_source_reads(self):
        patient = Mock()
        patient.check_permission.side_effect = frappe.PermissionError
        with patch('frappe.get_doc', return_value=patient) as get_doc:
            with self.assertRaises(frappe.PermissionError):
                patient_api(patient='PAT-TEST')
        get_doc.assert_called_once_with('Patient', 'PAT-TEST')
        patient.check_permission.assert_called_once_with('read')

    def test_native_function_only_script_invokes_exported_function(self):
        from life_slimming.api.server_scripts.get_package_details import run
        with patch('frappe.call', return_value={'packages': []}) as call:
            self.assertEqual(run(client='PAT-TEST'), {'packages': []})
        self.assertEqual(call.call_args.args[0].__name__, 'get_client_packages')
        self.assertEqual(call.call_args.kwargs['client'], 'PAT-TEST')

    def test_callback_rejects_bad_token_without_record_creation(self):
        from life_slimming.api.server_scripts.life_convox_call_popup import run
        settings = Mock()
        settings.get.return_value = True
        settings.get_password.return_value = 'test-token'
        frappe.local.request = Mock(headers={'X-ConVox-Token': 'invalid'})
        with patch('frappe.get_doc', return_value=settings) as get_doc:
            run()
        get_doc.assert_called_once_with('System Settings')
        self.assertEqual(frappe.response['http_status_code'], 401)

    def test_login_context_preserves_site_password_and_otp_configuration(self):
        with patch('frappe.get_system_settings', side_effect=lambda key: {'two_factor_method':'SMS', 'disable_user_pass_login':'0'}[key]), patch('life_slimming.api.auth.get_csrf_token', return_value='csrf'):
            context = login_context()
        self.assertTrue(context['password_login_enabled'])
        self.assertTrue(context['authenticated'])
        self.assertEqual(context['challenge_seconds'], 300)
        frappe.local.session.user = 'Guest'
        with patch('frappe.get_system_settings', side_effect=lambda key: {'two_factor_method':'OTP App', 'disable_user_pass_login':'1'}[key]), patch('life_slimming.api.auth.get_csrf_token', return_value='csrf'):
            context = login_context()
        self.assertFalse(context['password_login_enabled'])
        self.assertFalse(context['authenticated'])
        self.assertEqual(context['challenge_seconds'], 180)


if __name__ == '__main__':
    unittest.main()
