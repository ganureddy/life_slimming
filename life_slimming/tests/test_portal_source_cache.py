"""Static preparation caching must never cache session data or stale file edits."""
import json
import tempfile
import unittest
from pathlib import Path
from life_slimming.www.life_portal_module import prepared_source


class PortalSourceCacheTest(unittest.TestCase):
    def test_reuses_prepared_markup_and_invalidates_on_source_change(self):
        prepared_source.cache_clear()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.json'
            def save(html):
                path.write_text(json.dumps({'name': 'fixture', 'html': html}))
            save('<html><body><h1>First</h1><script>window.ready=1;</script></body></html>')
            first = prepared_source(str(path), 1)
            self.assertIs(prepared_source(str(path), 1), first)
            self.assertNotIn('<script', first[1])
            self.assertIn('window.ready=1', first[2])
            save('<h1>Updated</h1>')
            updated = prepared_source(str(path), 2)
            self.assertIn('Updated', updated[1])
            self.assertEqual(updated[2], '')
            self.assertEqual(prepared_source.cache_info().hits, 1)
        prepared_source.cache_clear()
