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
