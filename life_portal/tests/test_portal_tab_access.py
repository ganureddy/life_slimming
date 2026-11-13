import unittest
from unittest.mock import Mock,patch
import frappe
from life_slimming import portal_access as api
class PortalTabAccessTests(unittest.TestCase):
    def test_existing_config_inherits_tabs(self):
        self.assertIn('marketing',api.allowed_tabs('user',[],'CC',None,'ccvisit'))
    def test_tab_deny_and_subtab_parent(self):
        config={'CC':{'groups':'ALL','tab_access':{'ccvisit':{'marketing':False,'agents':False,'convox':True,'standalone':True}}}}
        tabs=api.allowed_tabs('user',[],'CC',config,'ccvisit')
        self.assertNotIn('marketing',tabs);self.assertNotIn('convox',tabs);self.assertIn('standalone',tabs)
    def test_parent_module_denial_wins_over_tab_grant(self):
        config={'CC':{'groups':'ALL','hide':['ccvisit'],'tab_access':{'ccvisit':{'marketing':True}}}}
        self.assertEqual(api.allowed_tabs('user',[],'CC',config,'ccvisit'),[])
    def test_endpoint_guard_rejects_denied_tab(self):
        frappe.local.session=frappe._dict(user='user')
        try:
            config={'CC':{'groups':'ALL','tab_access':{'ccvisit':{'marketing':False}}}}
            with patch.object(frappe,'get_doc',return_value=frappe._dict(name='user',custom_portal_role='CC')),patch.object(frappe,'get_roles',return_value=[]),patch.object(api,'access_settings',return_value=config):
                with self.assertRaises(frappe.PermissionError):api.require_module('ccvisit',tab='marketing')
                self.assertIn('ccvisit',api.require_module('ccvisit',tab='standalone'))
        finally:frappe.destroy()
