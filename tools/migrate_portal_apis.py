"""Convert an inspected ERP Server Script export to native, versioned Python APIs.

Usage: python tools/migrate_portal_apis.py /path/to/export.json
The export is an array with script/name/api_method/disabled/allow_guest/modified.
This does not import or execute the exported code, connect to ERP, or alter a DB.
"""
import ast
import collections
import hashlib
import json
import io
from pathlib import Path
import re
import sys
import tokenize

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'life_slimming/api/server_scripts'


def slug(value):
    return re.sub(r'[^a-z0-9]+', '_', value.lower()).strip('_')


def indent_source(source):
    # A plain indent would change every multiline SQL/HTML/string value.
    # Indent statements while retaining continuation lines inside string tokens.
    literal_lines = set()
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.STRING and token.start[0] < token.end[0]:
            literal_lines.update(range(token.start[0] + 1, token.end[0] + 1))
    return ''.join(
        line if number in literal_lines else ('    ' + line.rstrip() + '\n' if line.strip() else '\n')
        for number, line in enumerate(source.splitlines(keepends=True), 1)
    )


def convert(docs):
    active = [d for d in docs if not d.get('disabled')]
    counts = collections.Counter(slug(d.get('api_method') or d['name']) for d in active)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / '__init__.py').write_text('"""Native API modules migrated from the ERP Portal. See ../CATALOG.md."""\n')
    records = []
    for d in sorted(active, key=lambda d: d['name'].lower()):
        source = d['script'].replace('\r\n', '\n').rstrip() + '\n'
        tree = ast.parse(source, filename=d['name'])
        key = slug(d.get('api_method') or d['name'])
        if counts[key] > 1:
            key += '__' + hashlib.sha256(d['name'].encode()).hexdigest()[:8]
        notes = []
        if not d.get('api_method'):
            notes.append('Original API Method was blank; new local endpoint uses the script name.')
        if counts[slug(d.get('api_method') or d['name'])] > 1:
            notes.append('Duplicate original API method: use this explicit local endpoint; no ambiguous alias.')
        edits = []
        lines = source.splitlines(keepends=True)
        offsets = [0]
        for line in lines: offsets.append(offsets[-1] + len(line))
        def replace_node(node, value):
            # AST columns are UTF-8 byte offsets, while the source contains Unicode.
            start = offsets[node.lineno-1] + len(lines[node.lineno-1].encode()[:node.col_offset].decode())
            end = offsets[node.end_lineno-1] + len(lines[node.end_lineno-1].encode()[:node.end_col_offset].decode())
            edits.append((start, end, value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                path = ast.unparse(node)
                replacements = {
                    'frappe.db.sql': '_read_sql',
                    'frappe.call': '_call_whitelisted',
                    'frappe.make_post_request': '_make_post_request',
                }
                if path in replacements: replace_node(node, replacements[path])
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'GOOGLE_TRANSLATE_API_KEY' for t in node.targets):
                replace_node(node.value, 'frappe.conf.get("life_google_translate_api_key") or "PASTE_API_KEY_IN_SITE_CONFIG"')
                notes.append('Translation key is read from local site config: life_google_translate_api_key.')
        decorated = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.decorator_list]
        definition_only = len(decorated) == 1 and all(isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef)) for n in tree.body)
        if definition_only:
            for decorator in decorated[0].decorator_list:
                # Keep the source function but avoid registering a new nested whitelist on each request.
                start = offsets[decorator.lineno-1]
                end = offsets[decorator.end_lineno]
                edits.append((start, end, ''))
            notes.append('Function-only Server Script: the native entry now invokes ' + decorated[0].name + '.')
        for start, end, value in sorted(edits, reverse=True): source = source[:start] + value + source[end:]
        guest = bool(d.get('allow_guest'))
        prelude = ''
        if d.get('api_method') == 'get_client_transfer_web_details':
            guest = False
            prelude = 'patient = frappe.form_dict.get("patient")\nif patient:\n    frappe.get_doc("Patient", patient).check_permission("read")\n\n'
            notes.append('Patient-data endpoint now requires authentication and Patient read permission.')
        tail = ''
        if definition_only:
            tail = '\nreturn frappe.call(' + decorated[0].name + ', **dict(frappe.form_dict))\n'
        header = '"""' + d['name'].replace('"""', "'''") + '\n\nOriginal API: ' + str(d.get('api_method')) + '\nSource modified: ' + str(d.get('modified')) + '\nSee ../CATALOG.md for migration notes and validation limits.\n"""\n\n'
        header += 'import json\nimport re\n\nimport frappe\nfrom frappe.integrations.utils import make_post_request as _make_post_request\nfrom frappe.utils.safe_exec import read_sql as _read_sql\nfrom frappe.utils.safe_exec import call_whitelisted_function as _call_whitelisted\nfrom life_slimming.api._runtime import script_endpoint\n\n\n'
        header += '@script_endpoint(allow_guest=' + repr(guest)
        if d.get('enable_rate_limit'):
            header += ', rate_count=' + str(d.get('rate_limit_count') or 5) + ', rate_seconds=' + str(d.get('rate_limit_seconds') or 86400)
        header += ')\ndef run(**kwargs):\n'
        generated = header + indent_source(prelude + source + tail)
        compile(generated, str(OUTPUT / (key + '.py')), 'exec')
        (OUTPUT / (key + '.py')).write_text(generated)
        doctypes = set()
        params = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = ast.unparse(node.func)
                if name in {'frappe.get_doc','frappe.get_all','frappe.get_list','frappe.new_doc','frappe.get_meta','frappe.db.get_value','frappe.db.exists','frappe.db.count','frappe.db.get_all','frappe.db.get_list','frappe.db.set_value','frappe.db.get_single_value'} and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    doctypes.add(node.args[0].value)
                if name == 'frappe.form_dict.get' and node.args and isinstance(node.args[0],ast.Constant): params.add(str(node.args[0].value))
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                doctypes.update(re.findall(r'`tab([^`]+)`', node.value))
        records.append({
            'id':key, 'source_name':d['name'], 'legacy_method':d.get('api_method'),
            'method':'life_slimming.api.server_scripts.' + key + '.run',
            'source_modified':d.get('modified'), 'source_sha256':hashlib.sha256(d['script'].encode()).hexdigest(),
            'allow_guest':guest, 'source_allow_guest':bool(d.get('allow_guest')),
            'http_methods':['POST'], 'parameters':sorted(params), 'doctypes':sorted(doctypes), 'notes':notes,
        })
    manifest = {'source':'ERP Portal / Server Script', 'exported_on':'2026-09-19', 'count':len(records), 'endpoints':records}
    (OUTPUT.parent / 'catalog.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    frontend = ROOT / 'life_portal/src/api'
    frontend.mkdir(parents=True,exist_ok=True)
    (frontend / 'endpoints.json').write_text(json.dumps({r['id']:r['method'] for r in records},indent=2)+'\n')
    markdown = ['# ERP Portal API catalogue', '', '141 enabled Server Scripts migrated to native Python; disabled scripts are excluded.', '', 'Use **POST** `/api/method/<Python method>` with the Frappe session cookie and CSRF token.', 'The Vue client uses `dataApi(id, params)` from `src/api/index.js`.', '', 'Source conversion and import checks do not validate business results against production data.', 'Read `MIGRATION.md` for missing local schema and explicit behavior changes.', '', '| API ID / file | Original API method | Guest | Notes |', '|---|---|---|---|']
    for r in records:
        markdown.append('| ['+r['id']+'](server_scripts/'+r['id']+'.py) | `'+str(r['legacy_method'] or '(blank)')+'` | '+('Token callback' if r['allow_guest'] else 'No')+' | '+' '.join(r['notes'])+' |')
    (OUTPUT.parent / 'CATALOG.md').write_text('\n'.join(markdown)+'\n')
    print('Created',len(records),'native Python modules and central catalogue.')


if __name__ == '__main__':
    convert(json.loads(Path(sys.argv[1]).read_text()))
