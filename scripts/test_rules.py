"""解析规则级测试：全部用合成数据或临时目录，不读真实信件库。"""
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pdf_index as a


class TidyTests(unittest.TestCase):
    def test_radical_forms_restored(self):
        self.assertEqual(a.tidy("⽇⽉"), "日月")          # 康熙部首区 U+2F00 起，NFKC 能还原
        self.assertEqual(a.tidy("⻅⺟⻝⻢"), "见母食马")      # 部首补充区，NFKC 认不出，靠词表
        self.assertEqual(a.tidy("你好 世界"), "你好世界")    # 中文字距收紧
        self.assertEqual(a.tidy("你好\ue000\ue001图"), "你好图")  # 图标私用区剥离

    def test_small_caps_survive(self):
        # 正文不做全量 NFKC：小型大写字母笔友 ID（ᴅᴇᴍᴜʀᴇ）必须原样保留
        self.assertEqual(a.tidy("ᴅᴇᴍᴜʀᴇ"), "ᴅᴇᴍᴜʀᴇ")
        # Python 的 NFKC 本来就不拆音标小型大写，比对口径也不吃掉它
        self.assertEqual(a.normalize("ᴅᴇᴍᴜʀᴇ"), "ᴅᴇᴍᴜʀᴇ")


class HeaderTests(unittest.TestCase):
    def test_full_block(self):
        head = a.split_header("Felix\n2025 年1 月29 日10:00\n台湾\n公开信\n你好呀\n第二行",
                              ("Felix", "小小熊"))
        self.assertEqual(head["country"], "台湾")
        self.assertTrue(head["is_public"])
        self.assertTrue(head["body"].startswith("你好呀"))

    def test_badge_without_date_line(self):
        # 早期导出的 PDF 页眉没有日期行，角标也要认出来
        head = a.split_header("Felix\n公开信\n你好", ("Felix", "小小熊"))
        self.assertTrue(head["is_public"])
        self.assertEqual(head["body"], "你好")

    def test_mention_is_not_badge(self):
        # 正文里提到「公开信」是笔友的回信内容，不能标
        head = a.split_header("Felix\n2025 年1 月29 日10:00\n台湾\n看到了你的公开信，很高兴",
                              ("Felix", "小小熊"))
        self.assertFalse(head["is_public"])
        self.assertIn("看到了你的公开信", head["body"])

    def test_region_slot_guards(self):
        # 紧跟日期、短、无标点 → 国家/地区
        head = a.split_header("Felix\n2025 年1 月29 日10:00\n新加坡\n正文",
                              ("Felix", "小小熊"))
        self.assertEqual(head["country"], "新加坡")
        # 带标点、超长、或与写信人同名的一律不当地区
        for line in ("ttnhatle ：", "这一行长得已经完全不像地区名字了", "Felix"):
            head = a.split_header(f"Felix\n2025 年1 月29 日10:00\n{line}\n正文",
                                  ("Felix", "小小熊"))
            self.assertEqual(head["country"], "", line)
            self.assertIn(line, head["body"])

    def test_repeated_page_header_removed(self):
        raw = ("Felix\n2025 年1 月29 日10:00\n中国\n第一页从这里开始内容足够长不会被判成地区\n"
               "Felix\n2025 年1 月29 日10:00\n中国\n第二页从这里开始内容足够长不会被判成地区")
        head = a.split_header(raw, ("Felix", "小小熊"))
        self.assertIn("第一页", head["body"])
        self.assertIn("第二页", head["body"])
        self.assertNotIn("2025 年1 月29 日10:00", head["body"])

    def test_repeated_header_needs_alias_and_date(self):
        # 单独一句提到写信人名字、后面不是日期行 → 是正文，不能丢
        raw = "Felix\n2025 年1 月29 日10:00\n中国\nFelix 说得对，这一句要留在正文里"
        head = a.split_header(raw, ("Felix", "小小熊"))
        self.assertIn("Felix 说得对", head["body"])

    def test_footer_stripped(self):
        raw = ("Felix\n2025 年1 月29 日10:00\n中国\n正文第一行\n"
               "故事熊Felix · 字数: 524 / 字元: 646")
        head = a.split_header(raw, ("Felix", "小小熊"))
        self.assertNotIn("字元", head["body"])
        self.assertEqual(head["body"], "正文第一行")


class MarkerTests(unittest.TestCase):
    def test_gap_status(self):
        self.assertEqual(a.gap_status({}, 3), ("no-marker", None))
        self.assertEqual(a.gap_status({"_broken": True}, 3), ("unchecked", None))
        self.assertEqual(a.gap_status({"wallTotal": "x"}, 3), ("unchecked", None))
        self.assertEqual(a.gap_status({"wallTotal": 3}, 3), ("complete", 0))
        self.assertEqual(a.gap_status({"wallTotal": 5}, 3), ("missing", 2))
        self.assertEqual(a.gap_status({"wallTotal": 5, "farewellSent": True}, 3),
                         ("complete-farewell", 2))
        self.assertEqual(a.gap_status({"wallTotal": 5, "farewellSent": True,
                                       "farewell": {"unexported": 2}}, 3),
                         ("complete-farewell", 2))
        self.assertEqual(a.gap_status({"wallTotal": 5, "farewellSent": True,
                                       "farewell": {"unexported": 1}}, 3),
                         ("missing", 2))
        self.assertEqual(a.gap_status({"wallTotal": 1}, 3), ("extra", 2))

    def test_gap_label(self):
        self.assertEqual(a.gap_label("missing", 2), "缺 2 封")
        self.assertEqual(a.gap_label("complete", 0), "已齐")
        self.assertEqual(a.gap_label("no-marker", None), "无标记文件")


class AttachmentTests(unittest.TestCase):
    def test_attachment_count(self):
        atts = {"2025-01-01 1200-Felix": 3}
        self.assertEqual(a.attachment_count(atts, "2025-01-01 1200-Felix"), 3)
        self.assertEqual(a.attachment_count(atts, "2025-01-01 1200-Felix（已读）"), 3)
        self.assertEqual(a.attachment_count(atts, "2025-01-01 1200-其他"), 0)

    def test_attachments_of(self):
        with tempfile.TemporaryDirectory() as tmp:
            pal = Path(tmp)
            box = pal / ".data" / "附件"
            box.mkdir(parents=True)
            for name in ("2025-01-01 1200-Felix-图1.jpg", "2025-01-01 1200-Felix-图2.jpg",
                         "2025-01-01 1200-Bob-图1.png"):
                (box / name).write_bytes(b"x")
            (box / "notes.txt").write_text("不是附件")
            self.assertEqual(a.attachments_of(pal),
                             {"2025-01-01 1200-Felix": 2, "2025-01-01 1200-Bob": 1})

    def test_stamp_slug(self):
        self.assertEqual(a.stamp_slug("rose (2).png"), "rose")
        self.assertEqual(a.stamp_slug("rose.png"), "rose")


class FilenameTests(unittest.TestCase):
    def test_file_re(self):
        m = a.FILE_RE.match("2025-01-30 0421-故事熊Felix（已读）")
        self.assertEqual((m["date"], m["time"], m["sender"], m["read"]),
                         ("2025-01-30", "0421", "故事熊Felix", "（已读）"))
        m = a.FILE_RE.match("2025-01-30 0421-故事熊Felix (2)")
        self.assertEqual(m["sender"], "故事熊Felix")
        self.assertIsNone(a.FILE_RE.match("20250130-没有时间"))
        self.assertIsNone(a.FILE_RE.match("grimgirl 书信合集"))


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)

    def test_parser_version_missing_db(self):
        self.assertEqual(a.stored_parser_version(self.out), a.PARSER_VERSION)

    def test_legacy_db_reports_legacy(self):
        con = sqlite3.connect(self.out / "slowly_pdf.db")
        con.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)")
        con.execute("INSERT INTO meta VALUES('built_at','2025-01-01')")
        con.commit()
        con.close()
        self.assertEqual(a.stored_parser_version(self.out), "legacy")

    def test_broken_db_reports_legacy(self):
        (self.out / "slowly_pdf.db").write_bytes(b"not a database")
        self.assertEqual(a.stored_parser_version(self.out), "legacy")

    def test_ensure_schema_migrates_old_db(self):
        con = sqlite3.connect(self.out / "slowly_pdf.db")
        # 模拟老版本：letters 缺 att_files / char_drift，pals 缺标记字段
        con.execute("CREATE TABLE letters(id TEXT PRIMARY KEY, pal TEXT)")
        con.execute("CREATE TABLE pals(name TEXT PRIMARY KEY)")
        con.execute("INSERT INTO letters VALUES('abc','老朋友')")
        con.commit()
        added = a.ensure_schema(con)
        con.close()
        cols = {r[1] for r in sqlite3.connect(self.out / "slowly_pdf.db")
                .execute("PRAGMA table_info(letters)")}
        self.assertIn("att_files", cols)
        self.assertIn("char_drift", cols)
        self.assertIn("letters.att_files", added)
        rows = list(sqlite3.connect(self.out / "slowly_pdf.db")
                    .execute("SELECT id, pal, att_files, char_drift FROM letters"))
        self.assertEqual(rows, [("abc", "老朋友", 0, None)])   # 老数据一行不删，缺省补 0

    def test_values_bool_coercion(self):
        row = {"name": "x", "farewellSent": True, "stillWriting": False, "letters": 3}
        out = a.values(row, ["name", "farewellSent", "stillWriting", "letters"])
        self.assertEqual(out, ("x", 1, 0, 3))

    def test_parser_version_change_triggers_full_reparse(self):
        import contextlib
        import io
        import json
        import sqlite3 as sq
        import unittest.mock as mock
        from pypdf import PdfWriter
        root = Path(self.tmp.name) / "src"
        (root / "阿熊" / "来往信件").mkdir(parents=True)
        path = root / "阿熊" / "来往信件" / "2026-01-01 1200-阿熊.pdf"
        w = PdfWriter()
        w.add_blank_page(width=100, height=100)
        w.write(path)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(a.run_build(root, self.out, None), 0)
        con = sq.connect(self.out / "slowly_pdf.db")
        con.execute("UPDATE meta SET value='旧版本' WHERE key='parser_version'")
        con.commit()
        con.close()
        calls = {"n": 0}
        real = a.parse_pdf

        def counting(p):
            calls["n"] += 1
            return real(p)

        with contextlib.redirect_stdout(io.StringIO()):
            with mock.patch.object(a, "parse_pdf", side_effect=counting):
                self.assertEqual(a.run_build(root, self.out, None), 0)
        self.assertEqual(calls["n"], 1)   # 规则版本变了就必须重解析，不能因为 size/mtime 没变而跳过
        meta = json.loads((self.out / "build.json").read_text())["meta"]
        self.assertEqual(meta["mode"], "full")
        self.assertEqual(meta["parser_version"], a.PARSER_VERSION)


if __name__ == "__main__":
    unittest.main()
