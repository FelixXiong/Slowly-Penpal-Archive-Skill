"""合成图片与 PDF 的图文阅读回归验证。"""
import base64
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfWriter
import local_media
import pdf_index

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=")


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "library"
        self.folder = self.root / "Example"
        self.out = Path(self.tmp.name) / "out"
        self.base = "2026-01-01 1200-Example"
        self.put("邮票/test.png", PNG)
        self.put(".data/附件/" + self.base + "-图1.png", PNG)
        self.put("个人资料/头像.png", PNG)
        self.put("个人资料/profile.json", json.dumps({"bio": "<script>bad</script>", "country": "示例地区"}).encode())
        path = self.folder / "来往信件" / (self.base + ".pdf")
        path.parent.mkdir(parents=True)
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.write(path)
        self.put("来往信件/Example 书信合集.pdf", path.read_bytes())

    def put(self, relative, data):
        path = self.folder / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def build(self, opts=None):
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()):
            pdf_index.run_build(self.root, self.out, opts=opts)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        return json.loads((self.out / "media.json").read_text())

    def test_images_profile_links_and_incremental_sidecar(self):
        media = self.build()
        self.assertEqual(len(media["stamps"]), 1)
        self.assertEqual(media["stamps"][0]["letters"], [])
        record = next(iter(media["letters"].values()))
        self.assertEqual(len(record["photos"]), 1)
        self.assertTrue(record["pdf"].startswith("file:///"))
        self.assertEqual(len(media["images"]), 1)  # 相同图片按内容去重
        self.assertEqual(media["pals"]["Example"]["profile"]["bio"], "<script>bad</script>")
        self.assertEqual(len(media["pals"]["Example"]["links"]), 1)
        self.put(".data/" + self.base + ".json", json.dumps({"stampFile": "邮票/test.png", "stampName": "示例邮票", "photoFiles": [".data/附件/" + self.base + "-图1.png"]}).encode())
        media = self.build()
        self.assertEqual(len(media["stamps"][0]["letters"]), 1)
        self.assertEqual(media["stamps"][0]["name"], "示例邮票")
        self.assertEqual(len(next(iter(media["letters"].values()))["photos"]), 1)
        self.assertNotIn("<script>bad</script>", (self.out / "index.html").read_text())

    def test_missing_or_broken_metadata_and_pdf_only(self):
        self.put(".data/" + self.base + ".json", b"not json")
        media = self.build()
        self.assertIsNone(next(iter(media["letters"].values()))["stamp"])
        media = self.build({"pdf_only": True})
        self.assertEqual(media["images"], {})
        self.assertEqual(media["pals"], {})

    def test_paths_outside_pal_folder_are_not_read(self):
        outside = Path(self.tmp.name) / "secret.png"
        outside.write_bytes(PNG)
        self.assertIsNone(local_media.local_file(self.folder, str(outside)))
        self.assertIsNone(local_media.local_file(self.folder, "../../secret.png"))
        link = self.folder / "邮票" / "outside.png"
        try:
            link.symlink_to(outside)
        except OSError:
            return  # 部分 Windows 环境不允许创建符号链接
        self.assertIsNone(local_media.local_file(self.folder, "邮票/outside.png"))
        self.assertEqual(len(self.build()["stamps"]), 1)


if __name__ == "__main__":
    unittest.main()
