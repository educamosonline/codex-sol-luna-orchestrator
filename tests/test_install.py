import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'scripts/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'codex'
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def test_preview_leaves_destination_absent(self):
        self.assertEqual(installer.install(self.home), 0)
        self.assertFalse(self.home.exists())

    def test_install_doctor_and_idempotence_preserve_unrelated_files(self):
        self.home.mkdir()
        config = self.home / 'config.toml'
        config.write_text('model = "other"\n[agents]\nenabled = true\n')
        unrelated = self.home / 'agents/other.toml'
        unrelated.parent.mkdir()
        unrelated.write_text('private config')
        self.assertEqual(installer.install(self.home, apply=True), 0)
        self.assertEqual(installer.doctor(self.home), 0)
        files = {p.relative_to(self.home): (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.home.rglob('*') if p.is_file()}
        self.assertEqual(installer.install(self.home, apply=True), 0)
        self.assertEqual(files, {p.relative_to(self.home): (p.read_bytes(), p.stat().st_mtime_ns)
                                for p in self.home.rglob('*') if p.is_file()})
        self.assertEqual(unrelated.read_text(), 'private config')
        self.assertIn('model = "other"', config.read_text())

    def test_conflict_requires_replace_and_backups_recover_original(self):
        target = self.home / 'agents/luna-worker.toml'
        target.parent.mkdir(parents=True)
        target.write_bytes(b'original custom agent\n')
        self.assertEqual(installer.install(self.home, apply=True), 2)
        self.assertFalse((self.home / 'skills').exists())
        self.assertEqual(target.read_bytes(), b'original custom agent\n')
        self.assertEqual(installer.install(self.home, apply=True, replace=True), 0)
        backups = list((self.home / 'backups').rglob('luna-worker.toml'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), b'original custom agent\n')
        self.assertEqual(installer.doctor(self.home), 0)

    def test_doctor_detects_tampering_missing_files_and_disabled_agents(self):
        self.assertEqual(installer.doctor(self.home), 1)
        installer.install(self.home, apply=True)
        target = self.home / 'agents/luna-worker.toml'
        target.write_text('changed')
        self.assertEqual(installer.doctor(self.home), 1)
        installer.install(self.home, apply=True, replace=True)
        (self.home / 'config.toml').write_text('[agents]\nenabled = false\n')
        self.assertEqual(installer.doctor(self.home), 1)

    def test_linked_destination_is_refused_without_outside_writes(self):
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        self.home.mkdir()
        try:
            (self.home / 'agents').symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f'Symlink creation unavailable: {exc}')
        with self.assertRaises(ValueError):
            installer.install(self.home, apply=True)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.home / 'skills').exists())


if __name__ == '__main__':
    unittest.main()
