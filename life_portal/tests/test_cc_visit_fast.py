"""Visit loading must not fetch creation cohorts or financial records."""
import unittest
from unittest.mock import Mock, patch
from life_slimming.api import cc_visit_fast as api


class FastVisitTests(unittest.TestCase):
    def setUp(self):
        self.query=Mock(return_value=[])
        self.permissions=Mock(return_value=[])
        for context in [patch.object(api.frappe,'get_all',self.query),patch.object(api.frappe,'get_list',self.permissions),patch.object(api.frappe,'get_meta',return_value=Mock(has_field=Mock(return_value=False)))]:
            context.start();self.addCleanup(context.stop)

    def test_appointment_read_uses_only_scheduled_dates_and_small_payload(self):
        result=api.read_appointments('2026-11-01','2026-11-11','agent@example.test',False,True)
        self.query.assert_called_once()
        kwargs=self.query.call_args.kwargs
        self.assertNotIn('or_filters',kwargs)
        self.assertNotIn('custom_remarks',kwargs['fields'])
        self.assertNotIn('creation',kwargs['filters'])
        self.assertEqual(kwargs['filters']['lead_owner'],'agent@example.test')
        self.assertEqual(kwargs['limit_page_length'],10001)
        self.assertFalse(result['truncated'])

    def test_non_agent_reader_keeps_permission_aware_query(self):
        api.read_appointments('2026-11-01','2026-11-11','',False,False)
        self.permissions.assert_called_once()
        self.query.assert_not_called()

    def test_calendar_is_one_grouped_query_without_phone_or_client(self):
        self.query.return_value=[{'day':'2026-11-11','count':250,'custom_appointment_status':'Visited Booked'}]
        result=api.read_appointments('2026-11-06','2026-12-05','',True,False,calendar=True)
        kwargs=self.query.call_args.kwargs
        self.assertIn('count(name) as count',kwargs['fields'])
        self.assertIn('group_by',kwargs)
        self.assertNotIn('mobile_no',kwargs['fields'])
        self.assertEqual(result['days'][0]['count'],250)

    def test_large_ranges_are_bounded_and_marked_partial(self):
        self.query.return_value=[{'name':str(i)} for i in range(10001)]
        result=api.read_appointments('2026-11-01','2026-11-11','',True,False)
        self.assertEqual(len(result['rows']),10000)
        self.assertTrue(result['truncated'])
        self.assertTrue(result['total_is_lower_bound'])
