"""Prepare static page fixtures for life_portal/tests/workspace.browser.cjs.

Run with the bench Python environment, then run the browser test against Vite
and an isolated Chrome debugging port. No ERP database or page scripts run.
"""
import json
from pathlib import Path

from life_slimming.www.life_portal_module import prepared_source


def main():
    root = Path(__file__).resolve().parents[1] / 'life_slimming'
    manifest = json.loads((root / 'portal_pages/manifest.json').read_text())
    loading = (root / 'public/js/portal_module_loading.js').read_text()
    css = (root / 'public/css/portal_module.css').read_text()
    fixtures = {}
    for module, entry in manifest.items():
        path = root / 'portal_pages' / (entry['source'] + '.json')
        source, markup, _ = prepared_source(str(path), path.stat().st_mtime_ns)
        fixtures[module] = (
            '<!doctype html><html data-portal-module="' + module + '"><head><style>'
            + source['css'] + '</style></head><body>' + markup + '<style>' + css
            + '</style><script>window.lifePortalModule=' + json.dumps({'module': module})
            + ';</script><script>' + loading + '</script><script>'
            + 'window.fixturePending=[fetch("/api/fixture/one"),fetch("/api/fixture/two")];'
            + '</script></body></html>'
        )
    Path('/tmp/life-workspace-fixtures.json').write_text(json.dumps(fixtures))
    print(f'Prepared {len(fixtures)} module fixtures')


if __name__ == '__main__':
    main()
