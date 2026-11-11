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


def check_rows(rows, mode='auto', to_agents=None, allow_dup=False):
    """Preflight uses the same normalized rows as insertion, without any writes."""
    import re
    if not isinstance(rows,list) or len(rows)>500:
        frappe.throw('Upload a list of up to 500 leads.')
    if mode not in ('auto','agent','split','rank','file'):
        frappe.throw('Choose an assignment mode.')
    selected=to_agents or []
    settings=frappe.get_doc('Lead Assignment Settings','Lead Assignment Settings')
    agents={r.get('agent') for r in settings.get('agent_config') or [] if r.get('agent')}
    branches={r.name.lower():r.name for r in frappe.get_all('Branch',fields=['name'],limit_page_length=0)}
    sources={r.name.lower():r.name for r in frappe.get_all('Lead Source',fields=['name'],limit_page_length=0)}
    if any(a not in agents for a in selected) or mode in ('agent','split','rank') and not selected:
        frappe.throw('Choose configured receiving agents.')
    phones=list({re.sub(r'\D','',str(r.get('mobile') or ''))[-10:] for r in rows if isinstance(r,dict)})
    phones=[number for number in phones if len(number)==10]
    existing={}
    if phones:
        matches=frappe.db.sql("""select name, right(regexp_replace(ifnull(mobile_no,''),'[^0-9]',''),10) as mobile, right(regexp_replace(ifnull(phone,''),'[^0-9]',''),10) as alternate
            from `tabLead` where right(regexp_replace(ifnull(mobile_no,''),'[^0-9]',''),10) in %(phones)s
            or right(regexp_replace(ifnull(phone,''),'[^0-9]',''),10) in %(phones)s""",{'phones':tuple(phones)},as_dict=True)
        for row in matches:
            existing[row.mobile]=row.name
            if row.alternate:
                existing[row.alternate]=row.name
    output=[];seen=set()
    for i,raw in enumerate(rows):
        if not isinstance(raw,dict):
            output.append({'row':i+2,'errors':['Expected a row object.'],'state':'invalid'});continue
        row={k:str(raw.get(k) or '').strip() for k in ('name','mobile','source','branch','alt','city','interest','notes','agent')}
        row['row']=raw.get('row',i+2)
        digits=re.sub(r'\D','',row['mobile'])
        row['mobile']=digits[-10:]
        errors=[]
        if not row['name']:errors.append('Name is required.')
        if len(digits) not in (10,12) or len(digits)==12 and not digits.startswith('91'):errors.append('Enter a ten-digit mobile or +91 number.')
        for key,master in [('source',sources),('branch',branches)]:
            value=master.get(row[key].lower())
            if not value:errors.append('Unknown '+key+'.')
            else:row[key]=value
        if row['alt'] and len(re.sub(r'\D','',row['alt'])) not in (10,12):errors.append('Alternate number is invalid.')
        if mode=='file' and row['agent'] not in agents:errors.append('Choose a configured agent in the agent column.')
        duplicate=existing.get(row['mobile']) or ('earlier upload row' if row['mobile'] in seen else '')
        row.update(errors=errors,duplicate=duplicate,state='invalid' if errors else 'skip' if duplicate and not allow_dup else 'ready')
        if not errors:seen.add(row['mobile'])
        output.append(row)
    return {'rows':output,'ready':sum(r['state']=='ready' for r in output),'invalid':sum(r['state']=='invalid' for r in output),'skipped':sum(r['state']=='skip' for r in output)}
