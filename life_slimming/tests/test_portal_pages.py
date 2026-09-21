"""Page-source checks without database access or business API execution."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import frappe
from bs4 import BeautifulSoup
from life_slimming.www import life_portal_module as page

ROOT = Path(__file__).parents[1]


class PortalPagesTest(unittest.TestCase):
    def setUp(self):
        frappe.local.session = frappe._dict(user="test@example.test")
        frappe.local.flags = frappe._dict()
        frappe.local.form_dict = frappe._dict(module="tasks")
        frappe.local.request = frappe._dict(full_path="/life_portal_module?module=tasks")
        self.manifest = json.loads((ROOT / "portal_pages/manifest.json").read_text())

    def tearDown(self):
        frappe.destroy()

    def context(self):
        result = {}
        with patch.object(frappe, "get_app_path", return_value=str(ROOT)), patch.object(page, "get_csrf_token", return_value="test-csrf"):
            page.get_context(result)
        return result

    def test_guest_redirects_before_reading_source(self):
        frappe.local.session.user = "Guest"
        with patch.object(page.Path, "read_text") as read:
            with self.assertRaises(frappe.Redirect):
                page.get_context({})
            read.assert_not_called()
        self.assertIn("redirect-to=%2Flife_portal_module%3Fmodule%3Dtasks", frappe.local.flags.redirect_location)

    def test_unknown_and_path_traversal_modules_rejected(self):
        for name in ["missing", "../../site_config", "../billing"]:
            frappe.local.form_dict.module = name
            with self.assertRaises(frappe.DoesNotExistError):
                self.context()

    def test_all_sources_load_with_runtime_before_extracted_scripts(self):
        for module, entry in self.manifest.items():
            with self.subTest(module=module):
                frappe.local.form_dict.module = module
                result = self.context()
                self.assertTrue(result["module_html"])
                self.assertFalse(BeautifulSoup(result["module_html"], "html.parser").find_all("script"))
                source = json.loads((ROOT / "portal_pages" / (entry["source"] + ".json")).read_text())
                self.assertEqual(result["module_javascript"], source["javascript"])
                self.assertEqual(result["module_css"], source["css"])
                self.assertEqual(result["no_cache"], 1)

    def test_session_and_unambiguous_api_mapping(self):
        config = self.context()["module_config"]
        self.assertEqual(config["user"], "test@example.test")
        self.assertEqual(config["csrf_token"], "test-csrf")
        self.assertNotIn("create_po_from_indent360", config["methods"])
        self.assertTrue(all(value.startswith("life_slimming.api.server_scripts.") for value in config["methods"].values()))

    def test_frontend_manifest_matches_backend(self):
        frontend = ROOT.parent / "life_portal/src/data/portalPages.json"
        self.assertEqual(json.loads(frontend.read_text()), self.manifest)

    def test_dom_helper_does_not_shadow_frappe_jquery(self):
        source = 'const $=id=>document.getElementById(id); $("field"); window.$.extend({});'
        adapted = page.adapt_source(source, "accounts-command-center")
        self.assertNotIn("const $=", adapted)
        self.assertIn('portalElementById("field")', adapted)
        self.assertIn("window.$.extend", adapted)
        self.assertEqual(page.adapt_source(source, "other-page"), source)


if __name__ == "__main__":
    unittest.main()
