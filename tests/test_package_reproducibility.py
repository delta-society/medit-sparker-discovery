"""Identical approved bytes must produce the same ZIP across host metadata."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('reproducible_package', ROOT / 'scripts/build-package.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class PackageReproducibilityTests(unittest.TestCase):
    def test_archive_ignores_host_defaults_and_input_metadata(self):
        inputs = [*('plugin/' + name for name in builder.PLUGIN_FILES),
                  *('examples/' + name for name in builder.EXAMPLE_FILES), 'docs/plugin-guide.md']
        with tempfile.TemporaryDirectory(prefix='package 한글 ') as directory:
            root = Path(directory)
            for label, timestamp, mode in [('first', 946684800, 0o600), ('second', 1893456000, 0o644)]:
                for name in inputs:
                    target = root / label / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes((ROOT / name).read_bytes())
                    os.utime(target, (timestamp, timestamp))
                    target.chmod(mode)
            first, second = root / 'first.zip', root / 'second.zip'
            with contextlib.redirect_stdout(io.StringIO()):
                builder.build(root / 'first', first)
                class WindowsDefaults(zipfile.ZipInfo):
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, **kwargs)
                        self.create_system = 0
                        self.external_attr = 0x20
                # Exercise a different constructor platform default even on Linux;
                # the builder must explicitly normalize both values.
                with patch.object(builder.zipfile, 'ZipInfo', WindowsDefaults):
                    builder.build(root / 'second', second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(len(archive.infolist()), len(inputs))
                for entry in archive.infolist():
                    self.assertEqual(entry.date_time, (1980, 1, 1, 0, 0, 0))
                    self.assertEqual(entry.create_system, 3)
                    self.assertEqual(entry.external_attr, 0o100644 << 16)
                    self.assertEqual(entry.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(archive.read('.claude-plugin/plugin.json'),
                                 (ROOT / 'plugin/.claude-plugin/plugin.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
