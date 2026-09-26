"""ConVox unit tests; mocked storage/HTTP only. Run with the bench Python."""
import base64
from datetime import datetime
from contextlib import nullcontext
import hashlib
import json
import subprocess
import unittest
from unittest.mock import Mock, patch

import frappe
from life_slimming.api import convox


class Cache:
    def __init__(self): self.values = {}
    def get_value(self, key): return self.values.get(key)
    def set_value(self, key, value, **kwargs): self.values[key] = value
    def lock(self, *args, **kwargs): return nullcontext()


class ConvoxTest(unittest.TestCase):
    def setUp(self):
        frappe.local.flags = frappe._dict(in_test=True)
        frappe.local.session = frappe._dict(user='agent@example.test')
        frappe.local.form_dict = frappe._dict()
        frappe.local.response = frappe._dict()
        frappe.local.request = Mock(headers={})
        self.settings = frappe._dict(custom_convox_integration_enabled=1, custom_convox_default_dial_prefix='11')
        self.user = frappe._dict(name='agent@example.test', custom_convox_enabled=1, custom_convox_agent_id='AGENT1')
        self.lead = frappe._dict(name='LEAD-TEST', lead_owner='agent@example.test', mobile_no='+91 98765 43210')
        self.cache = Cache()
        clock=patch.object(convox,'now_datetime',return_value=datetime(2026,9,21,12,30))
        clock.start();self.addCleanup(clock.stop)

    def tearDown(self): frappe.destroy()

    def test_unreadable_secret_does_not_add_response_messages(self):
        frappe.local.message_log = []
        settings = Mock()
        def unreadable(*args, **kwargs):
            try:
                frappe.throw('Encryption key is invalid')
            except frappe.ValidationError:
                return None
        settings.get_password.side_effect = unreadable
        self.assertEqual(convox._secret(settings, 'custom_convox_callback_token'), '')
        self.assertEqual(frappe.local.message_log, [])
        self.assertFalse(frappe.flags.mute_messages)

    def test_encryption_matches_independent_openssl_for_both_iv_modes(self):
        secret, username = 'test-only-key-not-a-production-secret', 'agent@example.test'
        iv_value = base64.b64encode(b'1234567890123456').decode()
        for mode, iv in [('base64', b'1234567890123456'), ('php_literal_prefix', iv_value.encode()[:16])]:
            expected = subprocess.run(['openssl', 'enc', '-aes-256-cbc', '-K', hashlib.sha256(secret.encode()).hexdigest(), '-iv', iv.hex()], input=username.encode(), capture_output=True, check=True).stdout
            self.assertEqual(convox.encrypt_username(username, secret, iv_value, mode), base64.b64encode(expected).decode())
        with self.assertRaises(ValueError): convox.encrypt_username(username, secret, iv_value, '')
        with self.assertRaises(ValueError): convox.encrypt_username(username, secret, 'YmFk', 'base64')

    def test_widget_url_is_encoded_no_store_and_uses_current_identity(self):
        self.settings.update(custom_convox_sso_enabled=1, custom_convox_sso_iv='MTIzNDU2Nzg5MDEyMzQ1Ng==', custom_convox_sso_iv_mode='base64')
        with patch.object(convox, '_require_enabled', return_value=(self.user, self.settings)), patch.object(convox, '_secret', return_value='fixture-secret'):
            response = convox.widget_session()
        body = json.loads(response.get_data())['message']
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertTrue(body['url'].startswith(convox.ORIGIN+'/ConVoxCCS/ExternalIndex?ExternalUserName='))
        self.assertNotIn('agent@example.test', body['url'])
        self.assertNotIn('fixture-secret', response.get_data(as_text=True))

    def test_vendor_identity_is_user_specific_and_encoded_once(self):
        from urllib.parse import parse_qs, urlsplit
        self.settings.custom_convox_sso_enabled = 1
        self.user.custom_convox_sso_encrypted_identity = '********'
        value = base64.b64encode(bytes(range(240, 256))).decode()
        with patch.object(convox, '_require_enabled', return_value=(self.user, self.settings)), patch.object(convox, '_secret', return_value=value) as secret, patch.object(convox, 'encrypt_username') as encrypt:
            body = json.loads(convox.widget_session().get_data())['message']
        self.assertEqual(parse_qs(urlsplit(body['url']).query)['ExternalUserName'], [value])
        self.assertEqual(body['mode'], 'sso')
        secret.assert_called_once_with(self.user, 'custom_convox_sso_encrypted_identity')
        encrypt.assert_not_called()
        other = frappe._dict(name='other@example.test')
        self.assertEqual(convox._vendor_sso_value(other), '')

    def test_vendor_identity_rejects_urls_and_invalid_blocks(self):
        self.user.custom_convox_sso_encrypted_identity = '********'
        for value in ['https://example.test/login', 'abcd%3D', base64.b64encode(b'short').decode(), '']:
            with patch.object(convox, '_secret', return_value=value):
                with self.assertRaises(frappe.ValidationError):
                    convox._vendor_sso_value(self.user)

    def test_manual_login_never_needs_a_secret(self):
        with patch.object(convox, '_require_enabled', return_value=(self.user, self.settings)), patch.object(convox, '_secret') as secret:
            body = json.loads(convox.widget_session().get_data())['message']
        self.assertEqual(body, {'url': convox.WIDGET_URL, 'mode': 'manual'})
        secret.assert_not_called()

    def test_guest_is_denied(self):
        frappe.local.session.user='Guest'
        with self.assertRaises(frappe.AuthenticationError): convox.config()

    def test_manual_signin_bypasses_sso_without_changing_settings(self):
        self.settings.custom_convox_sso_enabled = 1
        with patch.object(convox, '_require_enabled', return_value=(self.user, self.settings)), patch.object(convox, '_secret') as secret:
            body = json.loads(convox.widget_session(manual='1').get_data())['message']
        self.assertEqual(body, {'url': convox.WIDGET_URL, 'mode': 'manual'})
        self.assertEqual(self.settings.custom_convox_sso_enabled, 1)
        secret.assert_not_called()

    def test_target_preview_prefers_mobile_and_never_sends_a_call(self):
        self.lead.phone = '9123456789'
        with patch.object(convox, '_require_enabled', return_value=(self.user, self.settings)), patch.object(convox, '_lead', return_value=self.lead), patch.object(convox.requests, 'post') as post:
            result = convox.call_target('LEAD-TEST')
        self.assertEqual(result, {'lead_id': 'LEAD-TEST', 'phone_number': '9876543210'})
        post.assert_not_called()

    def test_target_preview_checks_lead_ownership(self):
        self.lead.lead_owner = 'other@example.test'
        with patch.object(convox, '_require_enabled', return_value=(self.user, self.settings)), patch('frappe.get_doc', return_value=self.lead), patch('frappe.get_roles', return_value=['Sales User']):
            with self.assertRaises(frappe.PermissionError): convox.call_target('LEAD-TEST')

    def test_missing_mobile_never_falls_back_to_another_phone(self):
        self.lead.mobile_no = ''
        self.lead.phone = '9123456789'
        self.lead.custom_mobile_number = '9876543210'
        with patch.object(convox, '_require_enabled', return_value=(self.user, self.settings)), patch.object(convox, '_lead', return_value=self.lead), patch.object(convox, '_secret', return_value='fixture-token'), patch.object(convox.requests, 'post') as post:
            with self.assertRaises(frappe.ValidationError): convox.click_to_call('LEAD-TEST', 'a'*32)
        post.assert_not_called()

    def test_config_explains_missing_setup_without_returning_secrets(self):
        self.settings.custom_convox_integration_enabled = 0
        self.settings.custom_convox_default_dial_prefix = ''
        self.user.custom_convox_enabled = 0
        self.user.custom_convox_agent_id = ''
        with patch.object(convox, '_identity', return_value=(self.user, self.settings)), patch.object(convox, '_secret', return_value=''), patch('frappe.get_roles', return_value=['System Manager']):
            result = convox.config()
        self.assertFalse(result['enabled'])
        self.assertFalse(result['click_to_call_ready'])
        self.assertEqual(len(result['setup_issues']), 5)
        self.assertTrue(result['can_manage'])
        self.assertEqual(result['user_settings_url'], '/app/user/agent%40example.test')

    def test_config_requires_unique_agent_and_valid_enabled_sso(self):
        db = Mock(); db.count.return_value = 2
        with patch.object(convox, '_identity', return_value=(self.user, self.settings)), patch.object(convox, '_secret', return_value='fixture-secret'), patch('frappe.get_roles', return_value=['Sales User']), patch.object(frappe, 'db', db):
            result = convox.config()
            self.assertFalse(result['click_to_call_ready'])
            db.count.return_value = 1
            self.settings.custom_convox_sso_enabled = 1
            result = convox.config()
            self.assertFalse(result['click_to_call_ready'])
            self.assertFalse(result['sso_ready'])
            self.assertIn('SSO secret', ' '.join(result['setup_issues']))
            self.settings.custom_convox_sso_enabled = 0
            result = convox.config()
            self.assertTrue(result['click_to_call_ready'])
            self.assertEqual(result['setup_issues'], [])
            self.assertNotIn('fixture-secret', json.dumps(result))

    def test_other_agents_lead_is_denied_before_call(self):
        self.lead.lead_owner='other@example.test'
        with patch.object(convox, '_require_enabled', return_value=(self.user,self.settings)), patch('frappe.get_doc', return_value=self.lead), patch('frappe.get_roles', return_value=['Sales User']), patch.object(convox.requests,'post') as post:
            with self.assertRaises(frappe.PermissionError): convox.click_to_call('LEAD-TEST','a'*32)
        post.assert_not_called()

    def test_normalization_rejects_foreign_or_malformed_numbers(self):
        self.assertEqual(convox.normalize_phone('+91 98765 43210'), '9876543210')
        self.assertEqual(convox.normalize_phone('09876543210'), '9876543210')
        for bad in ['+44 1234567890', '123456789012345', 'call9876543210', '123']:
            with self.assertRaises(frappe.ValidationError): convox.normalize_phone(bad)

    def test_call_payload_and_idempotency(self):
        self.lead.phone = '9123456789'
        response=Mock();response.json.return_value={'STATUS':'CL000'}
        with patch.object(convox,'_require_enabled',return_value=(self.user,self.settings)), patch.object(convox,'_lead',return_value=self.lead), patch.object(convox,'_secret',return_value='fixture-access-token'), patch.object(frappe,'cache',self.cache), patch.object(convox.requests,'post',return_value=response) as post:
            one=convox.click_to_call('LEAD-TEST','a'*32)
            two=convox.click_to_call('LEAD-TEST','a'*32)
            busy=convox.click_to_call('LEAD-TEST','b'*32)
        self.assertEqual(one,two); self.assertTrue(one['success']);self.assertEqual(busy['status'],'BUSY')
        post.assert_called_once()
        args=post.call_args.kwargs
        self.assertEqual(args['json']['phone_number'],'9876543210')
        self.assertEqual(args['json']['userid'],'AGENT1')
        self.assertRegex(args['json']['refno'],r'^[A-Za-z0-9_]{6,20}$')
        self.assertFalse(args['allow_redirects']);self.assertEqual(args['headers']['Access-Token'],'fixture-access-token')
        self.assertNotIn('fixture-access-token',json.dumps(one))

    def test_timeout_is_not_retried_and_does_not_leak_exception(self):
        with patch.object(convox,'_require_enabled',return_value=(self.user,self.settings)), patch.object(convox,'_lead',return_value=self.lead), patch.object(convox,'_secret',return_value='fixture-token'), patch.object(frappe,'cache',self.cache), patch.object(convox.requests,'post',side_effect=convox.requests.Timeout('secret-upstream-error')) as post:
            answer=convox.click_to_call('LEAD-TEST','a'*32)
            again=convox.click_to_call('LEAD-TEST','a'*32)
        self.assertEqual(answer,again);self.assertEqual(answer['status'],'UNKNOWN');post.assert_called_once()
        self.assertNotIn('secret-upstream-error',json.dumps(answer))

    def test_auto_token_is_used_for_call_and_duplicate_does_not_fetch_again(self):
        self.settings.custom_convox_auto_token_enabled = 1
        token_response = Mock(); token_response.json.return_value = {'STATUS': 'SUCCESS', 'REFRESH_TOKEN': 'fixture-calling-token', 'EXPIRES_AT': '2026-09-22 12:34:58'}
        call_response = Mock(); call_response.json.return_value = {'STATUS': 'CL000'}
        with patch.object(convox, '_require_enabled', return_value=(self.user, self.settings)), patch.object(convox, '_lead', return_value=self.lead), patch.object(convox, '_secret', return_value='fixture-generation-key'), patch.object(frappe, 'cache', self.cache), patch.object(convox.requests, 'post', side_effect=[token_response, call_response]) as post:
            result = convox.click_to_call('LEAD-TEST', 'a'*32)
            self.assertEqual(convox.click_to_call('LEAD-TEST', 'a'*32), result)
        self.assertTrue(result['success'])
        self.assertEqual(post.call_count, 2)
        first, second = post.call_args_list
        self.assertEqual(first.args[0], convox.ORIGIN + '/ConVoxCCS/rest/secureToken')
        self.assertEqual(first.kwargs['headers']['Access-Token'], 'fixture-generation-key')
        self.assertNotIn('json', first.kwargs)
        self.assertFalse(first.kwargs['allow_redirects'])
        self.assertEqual(second.kwargs['headers']['Access-Token'], 'fixture-calling-token')
        self.assertNotIn('fixture-calling-token', json.dumps(result))

    def test_auto_token_failure_never_sends_a_call_or_reserves_an_unknown_dial(self):
        self.settings.custom_convox_auto_token_enabled = 1
        with patch.object(convox, '_require_enabled', return_value=(self.user, self.settings)), patch.object(convox, '_lead', return_value=self.lead), patch.object(convox, '_secret', return_value='fixture-generation-key'), patch.object(frappe, 'cache', self.cache), patch.object(convox.requests, 'post', side_effect=convox.requests.Timeout('secret-server-detail')) as post:
            result = convox.click_to_call('LEAD-TEST', 'a'*32)
        self.assertEqual(result['status'], 'TOKEN_ERROR')
        self.assertIn('No call was sent', result['message'])
        self.assertEqual(self.cache.values, {})
        post.assert_called_once()
        self.assertNotIn('secret-server-detail', json.dumps(result))

    def test_auto_token_rejects_invalid_payloads(self):
        self.settings.custom_convox_auto_token_enabled = 1
        for data in [[], {'STATUS': 'GE004'}, {'STATUS': 'SUCCESS', 'REFRESH_TOKEN': ''}, {'STATUS': 'SUCCESS', 'REFRESH_TOKEN': 'bad\r\nheader'}]:
            response = Mock(); response.json.return_value = data
            with patch.object(convox, '_secret', return_value='fixture-key'), patch.object(convox.requests, 'post', return_value=response):
                with self.assertRaises(frappe.ValidationError): convox._access_token(self.settings)

    def test_destination_cannot_be_private_ip_or_arbitrary_url(self):
        for url in ['http://192.168.0.193/ConVoxCCS/rest/api','https://attacker.test/ConVoxCCS/rest/api',convox.API_URL+'?token=secret',convox.ORIGIN+'/ConVoxCCS/ExternalIndex']:
            with self.assertRaises(frappe.ValidationError):convox._url(url,'/ConVoxCCS/rest/api')

    def test_callback_rejects_missing_token_before_any_storage(self):
        self.settings.custom_convox_callbacks_enabled=1
        with patch('frappe.get_doc',return_value=self.settings),patch.object(convox,'_secret',return_value='fixture-token'),patch('frappe.new_doc') as new:
            answer=convox.receive_callback('Call Popup',{})
        self.assertEqual(frappe.response.http_status_code,401);new.assert_not_called()
        self.assertEqual(answer['status'],'error')

    def test_callback_validation_and_agent_mapping(self):
        self.settings.custom_convox_callbacks_enabled=1
        frappe.local.request.headers={'X-ConVox-Token':'fixture-token'}
        with patch('frappe.get_doc',return_value=self.settings),patch.object(convox,'_secret',return_value='fixture-token'),patch('frappe.new_doc') as new:
            convox.receive_callback('Call Popup',{'agent_id':'AGENT1'})
        self.assertEqual(frappe.response.http_status_code,400);new.assert_not_called()

    def test_authenticated_callback_is_idempotent(self):
        self.settings.custom_convox_callbacks_enabled=1
        frappe.local.request.headers={'X-ConVox-Token':'fixture-token'}
        data=dict(agent_id='AGENT1',call_hit_reference_number='REF12345',mobile_number='9876543210',process_name='Test',lead_id='REMOTE-1',entry_date='2026-09-21 12:00:00',call_type='incoming',station='1001')
        event=Mock();event.get.return_value=None
        db=Mock();db.count.return_value=1;db.exists.side_effect=lambda dt,*a:dt=='DocType'
        with patch('frappe.get_doc',return_value=self.settings),patch('frappe.new_doc',return_value=event),patch.object(frappe,'db',db),patch.object(frappe,'cache',self.cache),patch.object(convox,'_secret',return_value='fixture-token'):
            first=convox.receive_callback('Call Popup',data)
        event.insert.assert_called_once_with(ignore_permissions=True, set_name=first["event_id"])
        event.get.return_value=json.dumps(data,sort_keys=True)
        db.exists.return_value=True;db.exists.side_effect=None
        with patch('frappe.get_doc',side_effect=[self.settings,event]),patch.object(frappe,'db',db),patch.object(frappe,'cache',self.cache),patch.object(convox,'_secret',return_value='fixture-token'):
            second=convox.receive_callback('Call Popup',data)
        self.assertEqual(first['event_id'],second['event_id']);event.save.assert_not_called()

    def test_poll_and_history_always_scope_agent(self):
        self.settings.custom_convox_callbacks_enabled=1
        db=Mock();db.exists.return_value=True;db.sql.return_value=[]
        with patch.object(convox,'_require_enabled',return_value=(self.user,self.settings)),patch.object(frappe,'db',db),patch('frappe.get_all',return_value=[]) as all_rows:
            convox.poll('2026-09-21 10:00:00')
            convox.history(call_reference='other-reference')
        self.assertEqual(db.sql.call_args.args[1]['agent'],'AGENT1')
        self.assertEqual(all_rows.call_args.kwargs['filters']['agent_id'],'AGENT1')

    def test_status_callback_preserves_vendor_fields_with_oauth_service_identity(self):
        self.settings.update(custom_convox_callbacks_enabled=1, custom_convox_callback_user='service@example.test')
        frappe.local.session.user = 'service@example.test'
        frappe.local.request.headers = {'Authorization': 'Bearer fixture-oauth-token'}
        data = dict(CALL_REFERENCE_ID='REF12345', MOBILE_NO='9876543210', PROCESS_NAME='Test',
                    CALL_DATE='2026-09-21T12:00:00', USER_ID='AGENT1', CALL_STATUS='Completed',
                    DISPOSITION='Interested', disposition2='Callback Later', disposition3='Evening',
                    remarks='Call after 6', CALL_MODE='CALLPATCH', CALL_HOUR='12', CALL_MINUTE='00',
                    CALL_DURATION='180', COMPLETED_BY='agent', QUEUE_NAME='TestQueue', QUEUE_DURATION='25',
                    RING_DURATION='10', FOLLOWUP_TIME='', STATION='1001', LIST_ID='LIST1', LEAD_ID='REMOTE1',
                    DID='1800123456', RECORDING_FILE_NAME='https://recordings.example.test/call.wav')
        event = Mock(); event.get.return_value = None
        db = Mock(); db.count.return_value = 1; db.exists.side_effect = lambda dt, *a: dt == 'DocType'
        with patch('frappe.get_doc', return_value=self.settings), patch('frappe.new_doc', return_value=event), patch.object(frappe, 'db', db), patch.object(frappe, 'cache', self.cache), patch.object(convox, '_secret', return_value=''):
            result = convox.receive_callback('Call Status', data)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(event.agent_id, 'AGENT1')
        self.assertEqual(event.call_status, 'Completed')
        self.assertEqual(event.call_duration, 180)
        self.assertEqual(event.queue_duration, 25)
        self.assertEqual(event.disposition_2, 'Callback Later')
        self.assertEqual(event.recording_file_name, data['RECORDING_FILE_NAME'])
        self.assertEqual(json.loads(event.payload_json)['CALL_HOUR'], '12')

    def test_bearer_callback_cannot_use_another_authenticated_user(self):
        self.settings.update(custom_convox_callbacks_enabled=1, custom_convox_callback_user='service@example.test')
        frappe.local.request.headers = {'Authorization': 'Bearer fixture-oauth-token'}
        with patch('frappe.get_doc', return_value=self.settings), patch.object(convox, '_secret', return_value=''), patch('frappe.new_doc') as new:
            result = convox.receive_callback('Call Status', {})
        self.assertEqual(result['status'], 'error')
        self.assertEqual(frappe.response.http_status_code, 401)
        new.assert_not_called()

if __name__=='__main__':unittest.main()
