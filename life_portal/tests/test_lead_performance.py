"""Migration coverage without connecting to a site or creating indexes."""
import unittest
from unittest.mock import Mock, patch

import frappe
from life_slimming import lead_performance as migration


class LeadPerformanceIndexes(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.db.table_exists.return_value = True
        self.db.get_table_columns.side_effect = lambda dt: {
            field for fields in migration.INDEXES[dt] for field in fields}
        self.existing = {dt: [] for dt in migration.INDEXES}
        self.db.sql.side_effect = lambda sql, **kw: self.existing[sql.split('`tab')[1].split('`')[0]]

        def add(dt, fields, index_name):
            for position, field in enumerate(fields, 1):
                self.existing[dt].append(frappe._dict(Key_name=index_name, Seq_in_index=position,
                                                       Column_name=field, Sub_part=None))
        self.db.add_index.side_effect = add
        patcher = patch.object(frappe, 'db', self.db)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_adds_indexes_once_and_keeps_names_within_database_limit(self):
        added = migration.execute()
        self.assertEqual(len(added), sum(map(len, migration.INDEXES.values())))
        self.assertTrue(all(len(call.kwargs['index_name']) <= 64 for call in self.db.add_index.call_args_list))
        self.db.add_index.reset_mock()
        self.assertEqual(migration.execute(), [])
        self.db.add_index.assert_not_called()

    def test_existing_left_prefix_index_covers_requested_fields(self):
        self.existing['Lead'] = [frappe._dict(Key_name='existing', Seq_in_index=n,
            Column_name=field, Sub_part=None) for n, field in enumerate(
                ('lead_owner', 'creation', 'name'), 1)]
        added = migration.execute()
        self.assertNotIn(('Lead', ('lead_owner', 'creation')), added)

    def test_prefix_only_text_index_does_not_count_as_full_coverage(self):
        self.existing['Lead'] = [frappe._dict(Key_name='prefix', Seq_in_index=1,
            Column_name='custom_cc_sub_status', Sub_part=5)]
        self.assertIn(('Lead', ('custom_cc_sub_status',)), migration.execute())

    def test_optional_tables_and_fields_can_be_absent(self):
        self.db.table_exists.side_effect = lambda dt: dt == 'Lead'
        self.db.get_table_columns.side_effect = lambda dt: ['name', 'lead_owner', 'creation']
        self.assertEqual(migration.execute(), [('Lead', ('lead_owner', 'creation'))])


if __name__ == '__main__':
    unittest.main()
