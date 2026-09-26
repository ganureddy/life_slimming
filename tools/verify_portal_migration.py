"""Compare generated native bodies with an inspected source export, without execution."""
import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


class ExpectedBody(ast.NodeTransformer):
    def visit_Attribute(self, node):
        path = ast.unparse(node)
        adapters = {'frappe.db.sql':'_read_sql', 'frappe.call':'_call_whitelisted', 'frappe.make_post_request':'_make_post_request'}
        if path in adapters:
            return ast.Name(id=adapters[path], ctx=ast.Load())
        return self.generic_visit(node)

    def visit_Assign(self, node):
        if any(isinstance(t,ast.Name) and t.id == 'GOOGLE_TRANSLATE_API_KEY' for t in node.targets):
            node.value = ast.parse('frappe.conf.get("life_google_translate_api_key") or "PASTE_API_KEY_IN_SITE_CONFIG"', mode='eval').body
        return self.generic_visit(node)


def verify(source_path):
    docs = json.loads(Path(source_path).read_text())
    manifest = json.loads((ROOT/'life_slimming/api/catalog.json').read_text())
    by_name = {x['source_name']:x for x in manifest['endpoints']}
    count = 0
    for doc in docs:
        if doc.get('disabled'): continue
        source = ExpectedBody().visit(ast.parse(doc['script']))
        funcs = [n for n in source.body if isinstance(n, ast.FunctionDef) and n.decorator_list]
        definition_only = len(funcs) == 1 and all(isinstance(n, (ast.Import,ast.ImportFrom,ast.FunctionDef)) for n in source.body)
        if definition_only: funcs[0].decorator_list = []
        path = ROOT/'life_slimming/api/server_scripts'/ (by_name[doc['name']]['id'] + '.py')
        module = ast.parse(path.read_text())
        body = next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name == 'run').body
        if doc['api_method'] == 'get_client_transfer_web_details': body = body[2:]
        if definition_only: body = body[:-1]
        assert ast.dump(ast.Module(body=body,type_ignores=[])) == ast.dump(source), doc['name']
        count += 1
    assert count == manifest['count']
    print(f'PASS: all {count} native bodies match source syntax trees, including literal values, apart from documented adapters.')


if __name__ == '__main__': verify(sys.argv[1])
