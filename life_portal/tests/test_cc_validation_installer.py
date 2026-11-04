"""Remote patch previews and stale-source guards without ERP writes."""
import json
from pathlib import Path
import runpy
import unittest
from unittest.mock import Mock, patch

import frappe

ROOT = Path(__file__).resolve().parents[2]
PAYLOAD = ROOT / 'docs/apk-calling/cc-validation-patches.json'
PAGE = ROOT / 'docs/apk-calling/mobile-page-patch.json'
INSTALLER = runpy.run_path(str(ROOT / 'scripts/console/patch_cc_validation.py'))


class ValidationInstallerTests(unittest.TestCase):
    def setUp(self):
        self.entries = json.loads(PAYLOAD.read_text())
        self.docs = {}
        for entry in self.entries:
            doc = Mock()
            doc.name = entry['name']
            doc.modified = entry['expected_modified']
            doc.script = entry['original_script']
            self.docs[doc.name] = doc
        self.db = Mock()
        for context in [patch.object(frappe, 'get_doc', side_effect=lambda dt, name: self.docs[name]),
                        patch.object(frappe, 'db', self.db)]:
            context.start()
            self.addCleanup(context.stop)

    def test_preview_compiles_both_scripts_without_writes(self):
        result = INSTALLER['patch_cc_validation'](PAYLOAD)
        self.assertEqual(set(result['preview']), set(self.docs))
        for doc in self.docs.values():
            doc.save.assert_not_called()
        self.db.commit.assert_not_called()

    def test_stale_second_script_aborts_before_any_save(self):
        self.docs[self.entries[1]['name']].script += '\n# edited elsewhere'
        with self.assertRaises(RuntimeError):
            INSTALLER['patch_cc_validation'](PAYLOAD, apply=True)
        for doc in self.docs.values():
            doc.save.assert_not_called()

    def test_apply_is_idempotent(self):
        INSTALLER['patch_cc_validation'](PAYLOAD, apply=True)
        result = INSTALLER['patch_cc_validation'](PAYLOAD, apply=True)
        self.assertEqual(result['updated'], [])
        for doc in self.docs.values():
            doc.save.assert_called_once()

    def test_save_failure_rolls_back(self):
        self.docs[self.entries[1]['name']].save.side_effect = RuntimeError('save failed')
        with self.assertRaises(RuntimeError):
            INSTALLER['patch_cc_validation'](PAYLOAD, apply=True)
        self.db.rollback.assert_called_once()
        self.db.commit.assert_not_called()

    def test_page_patch_refuses_changed_source(self):
        entry = json.loads(PAGE.read_text())
        doc = Mock()
        doc.name = entry['name']
        doc.modified = 'changed'
        doc.javascript = ''
        self.docs[doc.name] = doc
        with self.assertRaises(RuntimeError):
            INSTALLER['patch_mobile_call_page'](PAGE, apply=True)
        doc.save.assert_not_called()

    def test_page_preview_and_idempotent_apply(self):
        entry = json.loads(PAGE.read_text())
        doc = Mock()
        doc.name = entry['name']
        doc.modified = entry['expected_modified']
        doc.javascript = '\n'.join(change['old'] for change in entry['changes'])
        self.docs[doc.name] = doc
        self.assertEqual(INSTALLER['patch_mobile_call_page'](PAGE)['writes'], 0)
        doc.save.assert_not_called()
        INSTALLER['patch_mobile_call_page'](PAGE, apply=True)
        self.assertTrue(INSTALLER['patch_mobile_call_page'](PAGE, apply=True)['already_applied'])
        doc.save.assert_called_once()


if __name__ == '__main__':
    unittest.main()
