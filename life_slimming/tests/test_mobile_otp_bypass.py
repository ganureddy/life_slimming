import hashlib
from datetime import datetime
import unittest
from unittest.mock import patch, MagicMock

import frappe
from life_slimming import mobile_otp_bypass as bypass


class MobileOtpBypassTest(unittest.TestCase):
    def setUp(self):
        clock = patch.object(bypass, 'now_datetime', return_value=datetime(2026, 11, 8))
        clock.start()
        self.addCleanup(clock.stop)
        self.item = dict(target='billing', purpose='billing', salt='salt',
                         hash=hashlib.sha256(b'salt|123456').hexdigest(),
                         exp='2099-01-01 00:00:00', used=0)

    def test_code_requires_correct_purpose_target_expiry_and_unused_state(self):
        data = {'codes': [self.item]}
        self.assertIs(bypass._matching_code(data, 'billing', 'billing', '123456'), self.item)
        for target, purpose, code in [('other', 'billing', '123456'),
                                      ('billing', 'login', '123456'),
                                      ('billing', 'billing', '654321')]:
            self.assertIsNone(bypass._matching_code(data, target, purpose, code))
        self.item['used'] = 1
        self.assertIsNone(bypass._matching_code(data, 'billing', 'billing', '123456'))
        self.item.update(used=0, exp='2000-01-01 00:00:00')
        self.assertIsNone(bypass._matching_code(data, 'billing', 'billing', '123456'))

    def test_login_code_is_consumed_and_cannot_be_replayed(self):
        self.item.update(target='staff@example.com', purpose='login')
        data = {'codes': [self.item]}
        with patch.object(frappe, 'get_roles', return_value=[]), \
                patch.object(bypass, '_read_store', return_value=('note', data)), \
                patch.object(frappe, 'db', MagicMock()) as db:
            self.assertTrue(bypass._redeem_login('staff@example.com', '123456'))
            self.assertFalse(bypass._redeem_login('staff@example.com', '123456'))
            db.commit.assert_called_once()
            self.assertEqual(self.item['used_by'], 'staff@example.com')

    def test_system_managers_cannot_use_login_codes(self):
        with patch.object(frappe, 'get_roles', return_value=['System Manager']), \
                patch.object(bypass, '_read_store') as read:
            self.assertFalse(bypass._redeem_login('manager@example.com', '123456'))
            read.assert_not_called()

    def test_billing_redemption_restores_request_and_sets_scoped_proof(self):
        from frappe.core.doctype.server_script import server_script_utils
        frappe.local.session = frappe._dict(user='branch@example.com')
        frappe.local.form_dict = frappe._dict(original='request')
        frappe.local.response = frappe._dict(original='response')
        saved_form, saved_response = frappe.local.form_dict, frappe.local.response
        script = MagicMock()
        def redeem():
            self.assertEqual(frappe.form_dict.action, 'redeem')
            self.assertEqual(frappe.form_dict.target, 'billing')
            frappe.local.response.message = {'ok': 1, 'purpose': 'billing'}
        script.execute_method.side_effect = redeem
        try:
            with patch.object(bypass, '_read_store', return_value=('note', {'codes': [self.item]})), \
                    patch.object(server_script_utils, 'get_server_script_map', return_value={'_api': {'life_mobile_bypass_v5': 'script'}}), \
                    patch.object(frappe, 'get_doc', return_value=script), \
                    patch.object(frappe, 'cache', MagicMock()) as cache:
                result = bypass.verify_billing_bypass.__wrapped__('+91 9876543210', '123456')
                self.assertTrue(result['verified'])
                cache.set_value.assert_called_once_with('client_otp_verified::branch@example.com::9876543210', 1, expires_in_sec=300)
                self.assertIs(frappe.local.form_dict, saved_form)
                self.assertIs(frappe.local.response, saved_response)
        finally:
            frappe.destroy()

    def test_login_hook_updates_auth_binding_and_falls_back_without_challenge(self):
        import frappe.auth as auth
        import frappe.twofactor as twofactor
        original = MagicMock(return_value=False)
        original._life_mobile_bypass = False
        frappe.local.form_dict = frappe._dict(otp='123456')
        try:
            with patch.object(twofactor, 'confirm_otp_token', original), \
                    patch.object(auth, 'confirm_otp_token', original), \
                    patch.object(bypass, '_redeem_login') as redeem:
                bypass.install()
                wrapped = twofactor.confirm_otp_token
                self.assertIs(auth.confirm_otp_token, wrapped)
                bypass.install()
                self.assertIs(twofactor.confirm_otp_token, wrapped)
                self.assertFalse(auth.confirm_otp_token(MagicMock(user='staff@example.com')))
                redeem.assert_not_called()
                original.assert_called_once()
        finally:
            frappe.destroy()

    def test_billing_never_grants_proof_for_wrong_purpose_response(self):
        from frappe.core.doctype.server_script import server_script_utils
        frappe.local.session = frappe._dict(user='branch@example.com')
        frappe.local.form_dict = frappe._dict()
        frappe.local.response = frappe._dict()
        script = MagicMock()
        def redeem():
            frappe.local.response.message = {'ok': 1, 'purpose': 'login'}
        script.execute_method.side_effect = redeem
        try:
            with patch.object(bypass, '_read_store', return_value=('note', {'codes': [self.item]})), \
                    patch.object(server_script_utils, 'get_server_script_map', return_value={'_api': {'life_mobile_bypass_v5': 'script'}}), \
                    patch.object(frappe, 'get_doc', return_value=script), \
                    patch.object(frappe, 'throw', side_effect=frappe.ValidationError), \
                    patch.object(frappe, 'cache', MagicMock()) as cache:
                with self.assertRaises(frappe.ValidationError):
                    bypass.verify_billing_bypass.__wrapped__('9876543210', '123456')
                cache.set_value.assert_not_called()
        finally:
            frappe.destroy()

    def test_login_hook_requires_challenge_bound_to_authenticated_user(self):
        import frappe.auth as auth
        import frappe.twofactor as twofactor
        original = MagicMock(return_value=False)
        original._life_mobile_bypass = False
        frappe.local.form_dict = frappe._dict(otp='123456', tmp_id='challenge')
        cache = MagicMock()
        cache.get.side_effect = [b'other@example.com', b'secret']
        try:
            with patch.object(twofactor, 'confirm_otp_token', original), \
                    patch.object(auth, 'confirm_otp_token', original), \
                    patch.object(frappe, 'cache', cache), \
                    patch.object(bypass, '_redeem_login', return_value=True) as redeem, \
                    patch.object(auth, 'get_login_attempt_tracker') as tracker:
                bypass.install()
                manager = MagicMock(user='staff@example.com')
                self.assertFalse(auth.confirm_otp_token(manager))
                redeem.assert_not_called()
                cache.get.side_effect = [b'staff@example.com', b'secret']
                self.assertTrue(auth.confirm_otp_token(manager))
                redeem.assert_called_once_with('staff@example.com', '123456')
                self.assertEqual(cache.delete.call_count, 4)
                tracker.return_value.add_success_attempt.assert_called_once()
        finally:
            frappe.destroy()
