"""Parse an Excel lead upload for review without inserting any records."""
import base64
from io import BytesIO
from zipfile import ZipFile, BadZipFile
import frappe
from life_slimming.api._runtime import script_endpoint
from life_slimming.portal_access import require_module


def parse_workbook(content):
    from openpyxl import load_workbook
    try:
        raw = base64.b64decode(content, validate=True)
        if len(raw) > 2_000_000:
            raise ValueError('Choose an Excel file smaller than 2 MB.')
        with ZipFile(BytesIO(raw)) as archive:
            if sum(info.file_size for info in archive.infolist()) > 20_000_000:
                raise ValueError('The expanded workbook is too large.')
        workbook = load_workbook(BytesIO(raw), read_only=True, data_only=True)
        try:
            iterator = workbook.active.iter_rows(values_only=True)
            headers = [str(v or '').strip().lower() for v in next(iterator, ())]
            if not {'name', 'mobile', 'source', 'branch'}.issubset(headers):
                raise ValueError('Excel needs name, mobile, source and branch columns.')
            rows = []
            for number, values in enumerate(iterator, 2):
                if not any(v is not None for v in values):
                    continue
                row = {'row': number}
                for key, value in zip(headers, values):
                    if key:
                        row[key] = str(int(value) if isinstance(value, float) and value.is_integer() else value or '').strip()
                rows.append(row)
                if len(rows) > 500:
                    raise ValueError('Upload up to 500 leads at a time.')
            return rows
        finally:
            workbook.close()
    except (BadZipFile, KeyError) as exc:
        raise ValueError('Choose a valid .xlsx workbook.') from exc


@script_endpoint(allow_guest=False)
def preview(content=None, **kwargs):
    require_module('leads')
    from life_slimming.api.cc_core import run
    if not run(action='perm')['can_move']:
        frappe.throw('Lead distribution requires manager access.', frappe.PermissionError)
    if not isinstance(content, str) or len(content) > 2_700_000:
        frappe.throw('Choose an Excel file smaller than 2 MB.')
    try:
        return {'rows': parse_workbook(content)}
    except (ValueError, TypeError) as exc:
        frappe.throw(str(exc))
