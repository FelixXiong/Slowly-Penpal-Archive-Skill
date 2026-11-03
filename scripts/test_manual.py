import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfWriter
import pdf_index as archive


class ManualImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "input"
        self.pal = "Example（未读）"
        self.pdf = self.root / self.pal / "Slowly2.pdf"
        self.pdf.parent.mkdir(parents=True)
        writer = PdfWriter(); writer.add_blank_page(width=100, height=100); writer.write(self.pdf)

    def test_direct_pdf_and_header_metadata(self):
        self.assertEqual(archive.harvest(self.root), [(self.pal, self.pdf)])
        with patch.object(archive, "parse_pdf", return_value=("Example\n2024 年 11 月 19 日 04:17\n台湾\n正文", 1)):
            record = archive.build_record(self.root, self.pal, self.pdf)
        self.assertEqual(record["dt"], "2024-11-19 04:17")
        self.assertEqual(record["direction"], "in")
        self.assertEqual(record["metadata_source"], "pdf-header")
        self.assertEqual(record["body"], "正文")

    def test_no_header_keeps_body_without_guessing(self):
        with patch.object(archive, "parse_pdf", return_value=("Hello, Example.\nThis is a letter without metadata.", 1)):
            record = archive.build_record(self.root, self.pal, self.pdf)
        self.assertEqual((record["year"], record["dt"], record["direction"]), (0, "", "unknown"))
        self.assertEqual(record["metadata_source"], "unknown")
        self.assertTrue(record["body"].startswith("Hello"))
        self.assertEqual(archive.summarize([record])[0]["letters"], 1)

    def test_local_root_config_and_explicit_overrides(self):
        script = Path(self.tmp.name)
        (script / "library_root.txt").write_text("/default-library")
        (script / "library_root.txt.local").write_text(str(self.root))
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(archive.resolve_root(None, script), self.root.resolve())
            self.assertEqual(archive.resolve_root("/explicit-library", script), Path("/explicit-library"))
        with patch.dict(os.environ, {"SLOWLY_PDF_ROOT": "/environment-library"}):
            self.assertEqual(archive.resolve_root(None, script), Path("/environment-library"))

    def test_empty_directory_returns_error(self):
        empty = Path(self.tmp.name) / "empty"; empty.mkdir()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(archive.run_build(empty, Path(self.tmp.name) / "out"), 2)


if __name__ == "__main__":
    unittest.main()
