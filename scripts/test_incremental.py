"""用临时 PDF 验证增量行为，不读取真实信件库。"""
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfWriter
import pdf_index as archive


class IncrementalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "source"
        self.out = Path(self.tmp.name) / "archive"
        self.root.mkdir()

    def pdf(self, pal, day=1, pages=1):
        path = self.root / pal / "来往信件" / f"2026-01-{day:02d} 1200-{pal}.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        writer = PdfWriter()
        for _ in range(pages):
            writer.add_blank_page(width=100, height=100)
        writer.write(path)
        return path

    def build(self, pal=None):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(archive.run_build(self.root, self.out, pal), 0)
        report = json.loads((self.out / "build.json").read_text())
        records = archive.load_records(self.out)
        exported = [json.loads(line) for line in (self.out / "letters.jsonl").read_text().splitlines()]
        self.assertEqual({r["id"]: r for r in exported}, records)
        html = (self.out / "index.html").read_text()
        payload = next(line for line in html.splitlines() if line.startswith("const DATA = "))
        data = json.loads(payload[len("const DATA = "):-1].replace("<\\/", "</"))
        self.assertEqual(data["letters"], exported)
        return report["meta"], records

    def test_append_skip_update_and_retain(self):
        first = self.pdf("Alice")
        source_bytes = first.read_bytes()
        meta, records = self.build()
        self.assertEqual(meta["added"], 1)
        inode = (self.out / "slowly_pdf.db").stat().st_ino
        with patch.object(archive, "parse_pdf", side_effect=AssertionError("unchanged PDF parsed")):
            meta, records = self.build()
        self.assertEqual(meta["unchanged"], 1)
        self.pdf("Bob")
        meta, records = self.build("Bob")
        self.assertEqual((meta["added"], meta["retained"], len(records)), (1, 1, 2))
        self.assertEqual(first.read_bytes(), source_bytes)
        self.pdf("Alice", pages=2)
        meta, records = self.build()
        self.assertEqual(meta["updated"], 1)
        self.assertEqual(next(r for r in records.values() if r["pal"] == "Alice")["pages"], 2)
        first.unlink()
        meta, records = self.build()
        self.assertEqual((len(records), meta["retained"]), (2, 1))
        self.assertEqual((self.out / "slowly_pdf.db").stat().st_ino, inode)

    def test_bad_pdf_keeps_old_record(self):
        path = self.pdf("Alice")
        _, before = self.build()
        path.write_bytes(b"%PDF-broken")
        meta, after = self.build()
        self.assertEqual(meta["failed"], 1)
        self.assertEqual(before, after)

    def test_bad_database_stops_without_overwrite(self):
        self.pdf("Alice")
        self.build()
        db = self.out / "slowly_pdf.db"
        db.write_bytes(b"broken database")
        old_html = (self.out / "index.html").read_bytes()
        with self.assertRaises(sqlite3.DatabaseError):
            self.build()
        self.assertEqual(db.read_bytes(), b"broken database")
        self.assertEqual((self.out / "index.html").read_bytes(), old_html)

    def test_failed_transaction_restores_old_records_and_summary(self):
        self.pdf("Alice")
        meta, before = self.build()
        changed = dict(next(iter(before.values())), body="changed")
        pals = archive.summarize(list(before.values()))
        with self.assertRaises(sqlite3.IntegrityError):
            archive.write_db(self.out, [changed], pals + pals, meta)
        self.assertEqual(archive.load_records(self.out), before)
        with sqlite3.connect(self.out / "slowly_pdf.db") as con:
            self.assertEqual(con.execute("SELECT count(*) FROM pals").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
