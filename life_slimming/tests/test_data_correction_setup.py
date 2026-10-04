"""The installer adds missing fields but preserves local rule schema choices."""
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import frappe
from life_slimming.api import data_correction_setup as setup

ROOT = Path(__file__).parents[1]


class DataCorrectionSetupTest(unittest.TestCase):
    def test_existing_schema_is_not_saved(self):
        definitions = json.loads((ROOT / 'data_correction/doctypes.json').read_text())
        docs = {}
        for definition in definitions:
            doc = MagicMock()
            doc.fields = [frappe._dict(field) for field in definition['fields']]
            docs[definition['name']] = doc
        with patch.object(frappe, 'get_app_path', return_value=str(ROOT)), \
                patch.object(frappe, 'db', MagicMock()) as db, \
                patch.object(frappe, 'get_doc', side_effect=lambda dt, name: docs[name]):
            db.exists.return_value = True
            setup.execute()
        for doc in docs.values():
            doc.save.assert_not_called()
            doc.append.assert_not_called()

    def test_child_schemas_are_created_before_parent(self):
        inserted = []
        def get_doc(definition):
            doc = MagicMock()
            doc.insert.side_effect = lambda **kw: inserted.append(definition)
            return doc
        with patch.object(frappe, 'get_app_path', return_value=str(ROOT)), \
                patch.object(frappe, 'db', MagicMock()) as db, \
                patch.object(frappe, 'get_doc', side_effect=get_doc):
            db.exists.return_value = False
            setup.execute()
        seen = set()
        for definition in inserted:
            for field in definition['fields']:
                if field['fieldtype'] == 'Table':
                    self.assertIn(field['options'], seen)
            seen.add(definition['name'])
        self.assertEqual(len(inserted), 4)
