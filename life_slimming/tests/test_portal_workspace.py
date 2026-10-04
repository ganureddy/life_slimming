"""Shared workspace policy and page compatibility, without live business data."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import frappe
from bs4 import BeautifulSoup
from life_slimming.portal_access import allowed_modules
from life_slimming.portal_chrome import PAGE_CHROME
from life_slimming.www import life_portal_module as page

ROOT = Path(__file__).parents[1]


class WorkspacePolicyTest(unittest.TestCase):
    def test_guest_unknown_role_and_admin(self):
        self.assertEqual(allowed_modules('Guest', ['System Manager'], 'IT', None), [])
        self.assertEqual(allowed_modules('user', [], '', None), ['home'])
        self.assertIn('billing', allowed_modules('Administrator', [], '', None))
        self.assertIn('payroll', allowed_modules('user', ['System Manager'], '', None))

    def test_role_labels_aliases_and_child_pages(self):
        self.assertEqual(allowed_modules('u', [], 'COO', None), allowed_modules('u', [], 'C00', None))
        self.assertEqual(allowed_modules('u', [], 'BM', None), allowed_modules('u', [], 'Branch Manager', None))
        allowed = allowed_modules('u', [], 'HR', None)
        self.assertIn('employees', allowed)
        self.assertNotIn('billing', allowed)
        for module in ('p2p', 'c2c', 'b2b', 'clireg'):
            self.assertIn(module, allowed_modules('u', [], 'BM', None))

    def test_overrides_and_child_denial(self):
        settings = {'BM': {'groups': 'ALL', 'hide': ['billing', 'conversions'], 'show': ['billing']}}
        allowed = allowed_modules('u', [], 'BM', settings)
        self.assertIn('billing', allowed)  # Existing UI rule: explicit show wins.
        self.assertNotIn('conversions', allowed)
        self.assertNotIn('p2p', allowed)
        self.assertEqual(allowed_modules('u', [], 'BM', {'BM': {'groups': 'MAIN'}}), ['home'])

    def test_denied_module_never_prepares_source(self):
        frappe.local.session = frappe._dict(user='fixture')
        frappe.local.form_dict = frappe._dict(module='tasks', embed='1')
        try:
            with patch.object(frappe, 'get_app_path', return_value=str(ROOT)), patch.object(page, 'require_module', side_effect=frappe.PermissionError), patch.object(page, 'prepared_source') as prepare:
                with self.assertRaises(frappe.PermissionError):
                    page.get_context({})
                prepare.assert_not_called()
        finally:
            frappe.destroy()

    def test_direct_module_link_enters_workspace(self):
        frappe.local.session = frappe._dict(user='fixture')
        frappe.local.flags = frappe._dict()
        frappe.local.form_dict = frappe._dict(module='p2p', client='Fixture Client')
        try:
            with patch.object(frappe, 'get_app_path', return_value=str(ROOT)), patch.object(page, 'require_module'), patch.object(page, 'prepared_source') as prepare:
                with self.assertRaises(frappe.Redirect):
                    page.get_context({})
                prepare.assert_not_called()
                self.assertEqual(frappe.local.flags.redirect_location, '/life_portal/p2p?client=Fixture+Client')
        finally:
            frappe.destroy()


class WorkspaceChromeTest(unittest.TestCase):
    def test_every_source_reviewed_and_dom_hooks_preserved(self):
        manifest = json.loads((ROOT / 'portal_pages/manifest.json').read_text())
        for name in {entry['source'] for entry in manifest.values()}:
            with self.subTest(page=name):
                self.assertIn(name, PAGE_CHROME)
                path = ROOT / 'portal_pages' / (name + '.json')
                source, markup, _ = page.prepared_source(str(path), path.stat().st_mtime_ns)
                before = BeautifulSoup(source['html'], 'html.parser')
                after = BeautifulSoup(markup, 'html.parser')
                for tag in before(['script', 'style']):
                    tag.decompose()
                for node in before.select('[id]'):
                    self.assertIsNotNone(after.find(id=node['id']), node['id'])
                for tag in after.select('[data-portal-chrome]'):
                    self.assertIn('inert', tag.attrs)
                    self.assertIn('hidden', tag.attrs)
                    self.assertIn('display: none !important', tag.get('style', ''))
                # Form controls and buttons survive the page transformation.
                for selector in ('input', 'select', 'button'):
                    self.assertEqual(len(before.select(selector)), len(after.select(selector)))
                self.assertNotIn('DISABLED HEADER', markup)
