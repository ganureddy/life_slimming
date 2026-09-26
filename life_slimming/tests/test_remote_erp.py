"""Gateway boundary tests; no network, records or real credentials used."""
import unittest
from unittest.mock import Mock, patch
import frappe
from life_slimming.api import remote_erp as api


class RemoteERPTest(unittest.TestCase):
    def setUp(self):
        frappe.local.flags = frappe._dict(in_test=True)
        frappe.local.session = frappe._dict(user='local@example.test', sid='local-session')
        frappe.local.request = None
        self.cache = Mock()
        self.cache.get_value.return_value = {'user': 'erp@example.test', 'cookies': {'sid': 'remote-session'}}
        self.cache_patch = patch.object(frappe, 'cache', self.cache)
        self.cache_patch.start()

    def tearDown(self):
        self.cache_patch.stop()
        frappe.destroy()

    def test_connections_are_bound_to_user_and_session(self):
        a = api._key()
        frappe.session.sid = 'another-session'
        self.assertNotEqual(a, api._key())
        frappe.session.user = 'another@example.test'
        self.assertNotEqual(a, api._key())
        self.assertNotIn('local-session', a)

    def test_guest_denied_before_network(self):
        frappe.session.user = 'Guest'
        with patch.object(frappe, 'throw', side_effect=frappe.AuthenticationError), patch.object(api, '_request') as request:
            with self.assertRaises(frappe.AuthenticationError): api.dashboard()
            request.assert_not_called()

    def test_no_connection_requests_signin(self):
        self.cache.get_value.return_value = None
        with patch.object(api, '_request') as request:
            self.assertTrue(api.dashboard()['authentication_required'])
            request.assert_not_called()

    def test_unauthorized_branch_does_not_call_dashboard(self):
        with patch.object(api, '_branches', return_value={'branches': ['Allowed']}), patch.object(api, '_request') as request, patch.object(frappe, 'throw', side_effect=frappe.PermissionError):
            with self.assertRaises(frappe.PermissionError): api.dashboard('Other', '2026-09-01', '2026-09-19')
            request.assert_not_called()

    def test_invalid_range_does_not_call_dashboard(self):
        with patch.object(api, '_branches', return_value={'branches': ['Allowed']}), patch.object(api, '_request') as request, patch.object(frappe, 'throw', side_effect=frappe.ValidationError):
            with self.assertRaises(frappe.ValidationError): api.dashboard('Allowed', '2026-09-20', '2026-09-19')
            request.assert_not_called()

    def test_branch_mismatch_is_not_rendered(self):
        with patch.object(api, '_branches', return_value={'branches': ['Allowed']}), patch.object(api, '_request', return_value=({'message': {'branch': 'Other'}}, {})):
            self.assertIn('error', api.dashboard('Allowed', '2026-09-01', '2026-09-19'))

    def test_success_forwards_dates_and_preserves_zero(self):
        payload = {'branch': 'Allowed', 'achieved': 0}
        with patch.object(api, '_branches', return_value={'branches': ['Allowed']}), patch.object(api, '_request', return_value=({'message': payload}, {})) as request:
            result = api.dashboard('Allowed', '2026-09-01', '2026-09-19')
            self.assertEqual(result['data'], payload)
            self.assertEqual(request.call_args.kwargs['args'], {'branch': 'Allowed', 'from_date': '2026-09-01', 'to_date': '2026-09-19'})
            self.assertNotIn('cookies', result)

    def test_login_keeps_only_cookies_and_verified_identity(self):
        with patch.object(api, '_request', side_effect=[({'message': 'Logged In'}, {'sid': 'remote-session'}), ({'message': 'erp@example.test'}, {})]):
            self.assertTrue(api.connect('erp@example.test', 'fake-password')['connected'])
        stored = self.cache.set_value.call_args.args[1]
        self.assertEqual(set(stored), {'cookies', 'user'})
        self.assertNotIn('fake-password', str(stored))

    def test_otp_uses_server_challenge_without_password(self):
        self.cache.get_value.return_value = {'tmp_id': 'challenge', 'cookies': {}}
        with patch.object(api, '_request', return_value=({'error': 'Incorrect code'}, {})) as request:
            self.assertIn('error', api.connect(otp='123456'))
            self.assertEqual(request.call_args.kwargs['args'], {'otp': '123456', 'tmp_id': 'challenge'})

    def test_transport_uses_fixed_origin_tls_and_no_redirects(self):
        client = Mock()
        client.cookies = api.requests.cookies.RequestsCookieJar()
        client.request.return_value = Mock(status_code=200, ok=True, json=lambda: {'message': []})
        with patch.object(api.requests, 'Session') as factory:
            factory.return_value.__enter__.return_value = client
            api._request('branch_command_center', state={'cookies': {'sid': 'test'}}, args={'branch': 'Allowed'})
        args, kwargs = client.request.call_args
        self.assertEqual(args, ('GET', 'https://portal.lifescc.com/api/method/branch_command_center'))
        self.assertFalse(kwargs['allow_redirects'])
        self.assertNotIn('verify', kwargs)  # requests verifies TLS by default
        self.assertEqual(kwargs['params'], {'branch': 'Allowed'})

if __name__ == '__main__': unittest.main()
