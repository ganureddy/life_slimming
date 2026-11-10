import unittest
from unittest.mock import Mock, patch
import frappe
from life_slimming.api import cc_invoices as api


class InvoiceViewerTests(unittest.TestCase):
    def setUp(self):
        frappe.local.flags=frappe._dict(in_test=True)
        self.addCleanup(frappe.destroy)
        self.fake=Mock()
        self.fake.throw.side_effect=frappe.ValidationError
        self.fake.DoesNotExistError=frappe.DoesNotExistError
        for ctx in (patch.object(api,'frappe',self.fake),patch.object(api,'require_module')):
            ctx.start();self.addCleanup(ctx.stop)
        self.fake.get_meta.side_effect=lambda dt: Mock(has_field=lambda field: True)
        self.fake.db.sql.side_effect=[[],[{'total':0,'outstanding_count':0}],[]]

    def test_all_endpoints_require_cc_access(self):
        api.require_module.side_effect=frappe.PermissionError
        for func,args in ((api.list_invoices,{}),(api.filters,{}),(api.invoice,{'name':'INV1'})):
            with self.assertRaises(frappe.PermissionError):func(**args)
        self.fake.db.sql.assert_not_called()
        self.fake.get_doc.assert_not_called()

    def test_mobile_filter_normalizes_and_searches_all_recorded_numbers(self):
        api.list_invoices(mobile='+91 (98765) 43210')
        sql,params=self.fake.db.sql.call_args_list[0].args
        self.assertEqual(params['mobile'],'%9876543210%')
        for col in ('p.`mobile`','i.`contact_mobile`','c.`mobile_no`'):
            self.assertIn('REGEXP_REPLACE(COALESCE('+col,sql)
        self.assertNotIn('98765',sql)

    def test_general_search_accepts_mobile_and_client_details(self):
        api.list_invoices(query='98765 43210')
        sql,params=self.fake.db.sql.call_args_list[0].args
        self.assertEqual(params['query_mobile'],'%9876543210%')
        self.assertIn('i.customer_name LIKE',sql)
        self.assertIn('i.name LIKE',sql)
        self.assertIn('i.`patient` LIKE',sql)

    def test_filters_apply_before_pagination_and_to_summary(self):
        api.list_invoices(branch='Branch A',status='Paid',source='Call Center',from_date='2026-11-01',to_date='2026-11-10',start=40)
        calls=self.fake.db.sql.call_args_list
        self.assertEqual(len(calls),3)
        for call in calls:
            sql,params=call.args
            self.assertIn('i.`branch` = %(branch)s',sql)
            self.assertIn('i.status = %(status)s',sql)
            self.assertIn(' = %(source)s',sql)
            self.assertEqual(params['source'],'Call Center')
            self.assertEqual(str(params['until']),'2026-11-11')
        self.assertIn('LIMIT 41 OFFSET %(start)s',calls[0].args[0])
        self.assertEqual(calls[0].args[1]['start'],40)
        self.assertIn('i.docstatus != 2 GROUP BY i.currency',calls[2].args[0])

    def test_exact_page_boundary_and_currency_totals(self):
        self.fake.db.sql.side_effect=[[{'name':str(i)} for i in range(41)],[{'total':75,'outstanding_count':12}],
                                     [{'currency':'INR','billed':500,'outstanding':50},{'currency':'USD','billed':20,'outstanding':10}]]
        result=api.list_invoices()
        self.assertEqual(len(result['rows']),40)
        self.assertTrue(result['more'])
        self.assertEqual(result['total'],75)
        self.assertEqual(len(result['amounts']),2)
        self.assertEqual(result['outstanding_count'],12)

    def test_invalid_dates_mobile_and_offset_fail_before_read(self):
        for args in ({'from_date':'2026-11-10','to_date':'2026-11-01'},{'mobile':'abc'},{'mobile':'123'},{'start':'bad'}):
            with self.assertRaises(frappe.ValidationError):api.list_invoices(**args)
        self.fake.db.sql.assert_not_called()

    def test_optional_columns_are_not_queried_when_absent(self):
        self.fake.get_meta.side_effect=lambda dt: Mock(has_field=lambda field: field in {'patient','customer','mobile','source'})
        schema=api._schema()
        self.assertNotIn('i.`therapy_plan_reference_id`',schema['joins'])
        self.assertNotIn('i.`custom_therapy_plan`',schema['joins'])
        self.assertNotIn('p.`custom_lead`',schema['joins'])
        self.assertNotIn('c.`mobile_no`',str(schema))
        self.assertEqual(schema['branch'],"''")

    def test_source_priority_is_invoice_then_plan_then_client_then_lead(self):
        schema=api._schema()
        source=schema['source']
        self.assertLess(source.index('i.`source`'),source.index('t.`media`'))
        self.assertLess(source.index('t.`media`'),source.index('p.`custom_media`'))
        self.assertLess(source.index('p.`custom_media`'),source.index('l.`source`'))
        self.assertIn('AS source_from',','.join(schema['fields']))

    def test_detail_returns_safe_items_without_cost_or_mutations(self):
        self.fake.db.sql.side_effect=[[{'name':'INV1','source':'Call Center'}]]
        doc=Mock();doc.get.side_effect=lambda key: [{'name':'ITEM1','item_name':'Consultation','qty':1,'rate':100,'amount':100,'custom_net_profit':99}] if key=='items' else None
        self.fake.get_doc.return_value=doc
        result=api.invoice('INV1')
        self.assertEqual(result['source'],'Call Center')
        self.assertEqual(result['items'][0]['item_name'],'Consultation')
        self.assertNotIn('custom_net_profit',result['items'][0])
        doc.save.assert_not_called()
        self.fake.db.set_value.assert_not_called()

    def test_missing_invoice_reports_not_found(self):
        self.fake.db.sql.side_effect=[[]]
        with self.assertRaises(frappe.ValidationError):api.invoice('MISSING')
        self.fake.get_doc.assert_not_called()


if __name__=='__main__':unittest.main()
