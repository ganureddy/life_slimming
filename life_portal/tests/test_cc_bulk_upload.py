import base64
from io import BytesIO
import unittest
from openpyxl import Workbook
from life_slimming.api.cc_bulk_upload import parse_workbook


class WorkbookTests(unittest.TestCase):
    def workbook(self, rows):
        workbook = Workbook()
        for row in rows:
            workbook.active.append(row)
        output = BytesIO()
        workbook.save(output)
        workbook.close()
        return base64.b64encode(output.getvalue()).decode()

    def test_excel_preview_keeps_phone_text_and_numeric_values(self):
        rows = parse_workbook(self.workbook([
            ['name', 'mobile', 'source', 'branch'],
            ['A', '0123456789', 'Website', 'Ho CC'],
            ['B', 9876543210, 'Website', 'Ho CC']]))
        self.assertEqual(rows[0]['mobile'], '0123456789')
        self.assertEqual(rows[1]['mobile'], '9876543210')
        self.assertEqual(rows[1]['row'], 3)

    def test_missing_columns_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'source and branch'):
            parse_workbook(self.workbook([['name','mobile']]))

    def test_more_than_500_rows_are_rejected(self):
        with self.assertRaisesRegex(ValueError, '500'):
            parse_workbook(self.workbook([['name','mobile','source','branch']]+[['A','0123456789','Website','Ho CC']]*501))


class PreflightTests(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch,Mock
        import frappe
        self.frappe=frappe
        def records(dt,**kwargs):
            if dt=='Branch':return [frappe._dict(name='Ho CC')]
            if dt=='Lead Source':return [frappe._dict(name='Website')]
            return []
        def throw(message):raise frappe.ValidationError(message)
        for context in [patch.object(frappe,'get_doc',return_value={'agent_config':[{'agent':'agent@test'}]}),patch.object(frappe,'get_all',side_effect=records),patch.object(frappe,'db',Mock(sql=Mock(return_value=[]))),patch.object(frappe,'throw',side_effect=throw)]:
            context.start();self.addCleanup(context.stop)

    def test_every_row_is_checked_and_duplicates_are_skipped_before_creation(self):
        from life_slimming.api.cc_bulk_upload import check_rows
        rows=[{'name':'A','mobile':'9876543210','branch':'ho cc','source':'website'},{'name':'B','mobile':'+919876543210','branch':'Ho CC','source':'Website'},{'name':'','mobile':'12','branch':'Unknown','source':'Website'}]
        result=check_rows(rows)
        self.assertEqual((result['ready'],result['skipped'],result['invalid']),(1,1,1))
        self.assertEqual(result['rows'][0]['branch'],'Ho CC')
        self.assertGreaterEqual(len(result['rows'][2]['errors']),3)

    def test_file_owner_and_selected_agents_must_be_configured(self):
        from life_slimming.api.cc_bulk_upload import check_rows
        row={'name':'A','mobile':'9876543210','branch':'Ho CC','source':'Website','agent':'not-configured'}
        self.assertEqual(check_rows([row],mode='file')['invalid'],1)
        with self.assertRaises(self.frappe.ValidationError):check_rows([row],mode='split',to_agents=['not-configured'])
