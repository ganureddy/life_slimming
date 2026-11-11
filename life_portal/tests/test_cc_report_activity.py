import unittest
from unittest.mock import Mock, patch
import frappe
from life_slimming.api import cc_report_activity as api


class ActivityAggregationTests(unittest.TestCase):
    def event(self, at, lead, talk=0, channel='convox'):
        return dict(agent='a', channel=channel, lead=lead, at=at, answered=talk>0, talk=talk, status='Answered')

    def test_idle_time_starts_at_call_end_and_does_not_span_days(self):
        rows=api.aggregate([self.event('2026-11-11 10:00:00','L1',600),self.event('2026-11-11 10:30:00','L2'),self.event('2026-11-12 10:00:00','L3')],[],15)
        self.assertEqual(rows[0]['idle_minutes'],20)
        self.assertEqual(rows[0]['longest_gap'],20)
        self.assertEqual(rows[0]['talked_no_update'],1)

    def test_mismatches_are_distinct_leads_per_day(self):
        calls=[self.event('2026-11-11 10:00:00','L1',120),self.event('2026-11-11 10:30:00','L1',120,'mobile')]
        updates=[dict(agent='a',channel='update',at='2026-11-11 10:10:00',lead='L2',talk=0),dict(agent='a',channel='update',at='2026-11-11 10:11:00',lead='L2',talk=0)]
        row=api.aggregate(calls,updates)[0]
        self.assertEqual(row['convox'],1)
        self.assertEqual(row['mobile'],1)
        self.assertEqual(row['updated_no_call'],1)
        self.assertEqual(row['talked_no_update'],1)


class ActivityAccessTests(unittest.TestCase):
    def setUp(self):
        frappe.local.flags=frappe._dict(in_test=True)
        frappe.local.session=frappe._dict(user='agent@example.test')
        frappe.local.form_dict=frappe._dict()
        self.queries=[]
        def get_all(doctype, **kwargs):
            self.queries.append((doctype,kwargs))
            if doctype=='User':
                return [frappe._dict(name='agent@example.test',full_name='Agent',custom_convox_agent_id='101')]
            return []
        for context in [patch.object(api,'require_module'),patch.object(frappe,'get_roles',return_value=['Sales User']),patch.object(frappe,'get_all',side_effect=get_all),patch.object(frappe,'db',Mock(exists=Mock(return_value=True)))]:
            context.start();self.addCleanup(context.stop)

    def tearDown(self):
        frappe.destroy()

    def test_agent_cannot_request_another_agents_activity(self):
        result=api.run(from_date='2026-11-11',to_date='2026-11-11',agents='["other@example.test"]')
        self.assertEqual(result['rows'],[])
        self.assertEqual(self.queries[0][1]['filters']['name'],'agent@example.test')
        self.assertFalse(any(dt in ('ConVox Call Event','LIFE Mobile Call Log') for dt,args in self.queries))

    def test_agent_queries_are_scoped_to_own_user_and_dialer_id(self):
        api.run(from_date='2026-11-11',to_date='2026-11-11')
        convox=next(args for dt,args in self.queries if dt=='ConVox Call Event')
        mobile=next(args for dt,args in self.queries if dt=='LIFE Mobile Call Log')
        self.assertEqual(convox['filters']['agent_id'],['in',['101']])
        self.assertEqual(mobile['filters']['agent'],['in',['agent@example.test']])


class ConsultantAttributionTests(unittest.TestCase):
    def test_only_authorized_invoice_plans_are_looked_up(self):
        from life_slimming.api.cc_report_finance import enrich_consultants
        rows=[{'invoice':'I1','therapy_plan':'P1'},{'invoice':'I2','therapy_plan':''}]
        with patch.object(frappe,'db',Mock(exists=Mock(return_value=True))), patch.object(frappe,'get_meta',return_value=Mock(has_field=Mock(return_value=True))), patch.object(frappe,'get_all',return_value=[frappe._dict(name='P1',consultant_name='EMP1',custom_employee_name='Consultant One')]) as query:
            enrich_consultants(rows)
        self.assertEqual(query.call_args.kwargs['filters'],{'name':['in',['P1']]})
        self.assertEqual(rows[0]['consultant_name'],'Consultant One')
        self.assertNotIn('consultant_name',rows[1])
