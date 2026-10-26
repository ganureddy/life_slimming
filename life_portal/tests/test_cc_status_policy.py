"""Status bucketing can be checked without a running Frappe site."""
import ast
from pathlib import Path
import unittest


class StatusPolicyTests(unittest.TestCase):
    def test_report_ignores_retired_status_and_retains_confirmed_visit_evidence(self):
        path = Path(__file__).parents[2] / 'life_slimming/api/server_scripts/life_cc_agent_report_v2.py'
        tree = ast.parse(path.read_text())
        function = next(node for node in ast.walk(tree)
                        if isinstance(node, ast.FunctionDef) and node.name == 'appointment_bucket')
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
        bucket = namespace['appointment_bucket']
        for retired_status in ['Visited', 'Cancelled', 'Not Visited', '']:
            self.assertEqual(bucket('Booked', retired_status, '2026-10-26', '2026-10-26'), 'awaiting')
        self.assertEqual(bucket('Cancelled', '', '2026-10-26', '2026-10-26'), 'cancelled')
        self.assertEqual(bucket('Booked', '', '2026-10-25', '2026-10-26'), 'no_show')
        self.assertEqual(bucket('Booked', '', '2026-10-26', '2026-10-26', True), 'walkins')
