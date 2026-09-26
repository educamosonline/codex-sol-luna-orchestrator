import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/sol-luna-orchestrator/scripts/workflow.py'


class WorkflowTests(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True)

    def test_routing_escalates_to_sol_and_respects_capacity(self):
        cases = [
            (['--cross-module'], 'sol', 0),
            (['--ambiguity', 'medium'], 'sol', 0),
            (['--risk', 'high'], 'sol', 0),
            (['--available-workers', '0'], 'direct', 0),
            (['--parallel-scopes', '3', '--ownership-disjoint', '--available-workers', '1'], 'luna_single', 1),
            (['--parallel-scopes', '9', '--ownership-disjoint', '--available-workers', '3'], 'luna_wave', 3),
            (['--parallel-scopes', '9', '--ownership-disjoint'], 'luna_wave', 7),
        ]
        for args, lane, workers in cases:
            with self.subTest(args=args):
                result = self.cli('route', *args)
                self.assertEqual(result.returncode, 0, result.stderr)
                value = json.loads(result.stdout)
                self.assertEqual((value['lane'], value['max_workers']), (lane, workers))
        self.assertNotEqual(self.cli('route', '--available-workers', '-1').returncode, 0)

    def test_packet_receipt_round_trip_and_stale_evidence_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run'
            commands = [
                ('init', run, '--goal', 'Verify package', '--acceptance', 'Evidence accepted', '--candidate-digest', 'git:abc123'),
                ('packet', run, '--id', 'check', '--agent', 'luna_tester', '--role', 'tester',
                 '--objective', 'Verify one artifact', '--done-when', 'Artifact verified',
                 '--validation', 'python check.py'),
                ('receipt', run, '--packet-id', 'check', '--status', 'PASS', '--summary', 'Verified',
                 '--command', 'python check.py::0', '--evidence', 'test-report:report.txt',
                 '--candidate-digest', 'git:abc123', '--next-action', 'Sol acceptance'),
                ('validate', run),
            ]
            for args in commands:
                result = self.cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(self.cli('summary', run).stdout)
            self.assertEqual(summary['counts']['PASS'], 1)
            result = self.cli('receipt', run, '--packet-id', 'check', '--status', 'PASS',
                              '--summary', 'Stale', '--command', 'python check.py::0',
                              '--evidence', 'test-report:report.txt', '--candidate-digest', 'git:old',
                              '--next-action', 'Sol acceptance')
            # A receipt can be created, but cannot pass integrated validation for another candidate.
            if result.returncode == 0:
                result = self.cli('validate', run)
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
