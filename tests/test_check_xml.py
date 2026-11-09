"""Exercise the same command used by CI with valid and invalid XML fixtures."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).resolve().parents[1] / "scripts" / "check_xml.py"


class CheckXMLTests(unittest.TestCase):
    def run_checker(self, *paths):
        return subprocess.run(
            [sys.executable, str(CHECKER), *map(str, paths)],
            capture_output=True, text=True, timeout=10,
        )

    def test_valid_namespaced_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, content in {
                "config.xml": '<config><title>Books &amp; articles</title></config>',
                "style sheet.xsl": '<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0"/>',
                "pipeline.xpl": '<p:declare-step xmlns:p="http://www.w3.org/ns/xproc" version="1.0"/>',
            }.items():
                path = Path(directory) / name
                path.write_text(content, encoding="utf-8")
                paths.append(path)
            result = self.run_checker(*paths)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "Checked 3 XML files")

    def test_malformed_sources_fail(self):
        for content in (
            '<config><title>Unclosed title</config>',
            '<xsl:stylesheet version="2.0"/>',  # unbound namespace prefix
            '<p:declare-step xmlns:p="http://www.w3.org/ns/xproc"',
        ):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "invalid.xml"
                path.write_text(content, encoding="utf-8")
                result = self.run_checker(path)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(str(path), result.stderr)

    def test_missing_file_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_checker(Path(directory) / "missing.xml")
            self.assertEqual(result.returncode, 1, result.stderr)


if __name__ == "__main__":
    unittest.main()
