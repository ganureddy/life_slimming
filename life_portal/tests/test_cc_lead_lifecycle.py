import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import frappe
from life_slimming import cc_lead_lifecycle as lifecycle


class Lead(frappe._dict):
    def get_doc_before_save(self):
        return self.get('_old')


class ChatLifecycleTests(unittest.TestCase):
    def setUp(self):
        clock=patch.object(lifecycle, "now_datetime", return_value=datetime(2026, 11, 10, 12))
        clock.start()
        self.addCleanup(clock.stop)

    def lead(self, **values):
        return Lead(meta=Mock(), lead_owner='agent-a', creation=datetime(2026, 1, 1),
                    custom_chat_script='new chat', **values)

    def test_chat_without_contact_is_untouched(self):
        doc = self.lead(custom_cc_stage='', status='Open')
        lifecycle.before_save(doc)
        self.assertEqual(doc.custom_cc_stage, 'UNTOUCHED')
        self.assertEqual(doc.status, 'Lead')

    def test_chat_preserves_followup_agent_and_marks_return(self):
        doc = self.lead(custom_cc_stage='FOLLOW-UP', _old=frappe._dict(
            lead_owner='original-agent', custom_chat_script='previous chat'))
        lifecycle.before_save(doc)
        self.assertEqual(doc.lead_owner, 'original-agent')
        self.assertEqual(doc.custom_cc_chat_returned, 1)
        self.assertEqual(doc.custom_cc_stage, 'FOLLOW-UP')

    def test_chat_does_not_reset_contacted_or_protected_lead(self):
        for values in ({'custom_cc_stage': 'SUCCESS'}, {'custom_cc_stage': 'INVALID'},
                       {'custom_cc_stage': 'LOST'}, {'custom_cc_stage': '', 'custom_call_count': 1}):
            doc = self.lead(**values)
            lifecycle.before_save(doc)
            self.assertEqual(doc.custom_cc_stage, values['custom_cc_stage'])

    def test_repeat_marker_without_transcript_retains_followup_agent(self):
        old=frappe._dict(lead_owner='original-agent',custom_cc_stage='FOLLOW-UP',custom_chat_script='new chat',custom_remarks='')
        doc=self.lead(custom_cc_stage='FOLLOW-UP',custom_remarks='[NEW WEBSITE CHAT ENQUIRY 2026-11-10]',_old=old)
        lifecycle.before_save(doc)
        self.assertEqual(doc.lead_owner,'original-agent')
        self.assertEqual(doc.custom_cc_stage,'FOLLOW-UP')

    def test_protected_repeat_keeps_owner_without_new_custom_fields(self):
        for stage,status,appointment in [('SUCCESS','Converted','Visited Booked'),('FOLLOW-UP','Open',''),('LOST','Do Not Contact','')]:
            old=frappe._dict(lead_owner='original-agent',custom_cc_stage=stage,status=status,custom_appointment_status=appointment)
            doc=self.lead(custom_cc_stage=stage,status=status,_old=old)
            doc.meta.has_field.return_value=False
            lifecycle.before_save(doc)
            self.assertEqual(doc.lead_owner,'original-agent')
            self.assertEqual(doc.custom_cc_stage,stage)

    def rotate(self, doc, configs=None):
        doc.save=Mock();doc.add_comment=Mock()
        settings=frappe._dict(agent_config=configs if configs is not None else [frappe._dict(agent='agent-b',custom_auto_assign_enabled=1)])
        db=Mock();db.get_value.return_value=1;db.exists.return_value=True;db.count.return_value=0
        with patch.object(frappe,'db',db), patch.object(frappe,'get_meta',return_value=Mock()), \
             patch.object(frappe,'get_single',return_value=settings), \
             patch.object(frappe,'get_all',return_value=['LEAD-1']), \
             patch.object(frappe,'get_doc',return_value=doc):
            lifecycle.rotate_untouched()
        return doc

    def test_old_untouched_chat_rotates_to_different_agent(self):
        doc=self.rotate(self.lead(custom_cc_stage='UNTOUCHED'))
        self.assertEqual(doc.lead_owner,'agent-b')
        doc.save.assert_called_once()
        self.assertIsNotNone(doc.custom_cc_rotation_at)

    def test_no_eligible_different_agent_leaves_lead_untouched(self):
        for configs in ([], [frappe._dict(agent='agent-a',custom_auto_assign_enabled=1)],
                        [frappe._dict(agent='agent-b',custom_auto_assign_enabled=0)]):
            doc=self.rotate(self.lead(custom_cc_stage='UNTOUCHED'),configs)
            self.assertEqual(doc.lead_owner,'agent-a')
            doc.save.assert_not_called()

    def test_rotation_uses_assignment_age_and_skips_contacted(self):
        for values in ({'custom_cc_rotation_at': datetime(2026, 11, 8)},
                       {'custom_call_count': 1}, {'custom_last_call_time': '2026-01-02'}):
            doc=self.rotate(self.lead(custom_cc_stage='UNTOUCHED', **values))
            self.assertEqual(doc.lead_owner,'agent-a')
            doc.save.assert_not_called()


if __name__ == '__main__':
    unittest.main()
