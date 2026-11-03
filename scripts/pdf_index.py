#!/usr/bin/env python3
"""Slowly 离线安全版：只读本地信件 PDF，产出本地 SQLite + JSONL + 单文件网页档案馆。

正文唯一来源是 PDF 文本层。笔友级状态（墙上封数 / 离别信 / 仍在通信）读的是每个文件夹里的
`.slowly-pal` 标记文件，邮票、附件与资料读取本地文件，图片内嵌到阅读页面。
本文件不使用网络、端口、浏览器自动化或系统脚本能力。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from local_media import build_media

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    sys.exit("缺少 pypdf，请先执行：python3 -m pip install pypdf")

ENV_ROOT = "SLOWLY_PDF_ROOT"
ENV_OUT = "SLOWLY_PDF_OUT"
CONFIG_FILE = "library_root.txt"
MARKER_FILE = ".slowly-pal"

# 解析规则版本：改了页眉/标记/附件的判读口径就要 +1，增量库会据此自动全量重算，
# 避免出现「规则修好了但老记录永远不再重解析」的静默失真。
PARSER_VERSION = "2026-11-03.manual1"

ICON_GLYPH = re.compile(r"[\ue000-\uf8ff]+")
CJK_GAP = re.compile(r"(?<=[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef])\s+")
RADICAL_BLOCK = re.compile(r"[⼀-⿕]")
# CJK 部首补充（U+2E80–U+2EFF）：PDF 字体 cmap 会把正文里的这些字抽成部首形而非汉字，
# NFKC 认不出其中大部分，只能按实测词表还原（本库 32 封、69 个字，全是这 17 个）。
RADICAL_SUPPLEMENT = str.maketrans({
    "⺟": "母", "⻄": "西", "⻅": "见", "⻆": "角", "⻋": "车", "⻑": "長", "⻓": "长",
    "⻔": "门", "⻘": "青", "⻚": "页", "⻛": "风", "⻜": "飞", "⻝": "食", "⻢": "马",
    "⻤": "鬼", "⻥": "鱼", "⻩": "黄",
})
# 页脚那一行「写信人 · 字数: N / 字元: M」是应用打印上去的，不是正文。
FOOTER_RE = re.compile(r"^.+?\s*[·•]\s*字数[:：]\s*\d+\s*/\s*字元[:：]\s*\d+\s*$")
NOT_A_PLACE = re.compile(r"[\d，。！？、；:：,.!?;:…~～「」『』【】（）()]")
FILE_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{4})-(?P<sender>.+?)"
    r"(?: \(\d+\))?(?P<read>（已读）)?$"
)
PDF_DATE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*(\d{1,2}):(\d{2})")
DUP_SUFFIX_RE = re.compile(r" \(\d+\)$")
READ_SUFFIX = "（已读）"
PUBLIC_BADGE = "公开信"
COLLECTION_HINT = ("合集", "书信集")
# --verify-data 的告警阈值：PDF 正文比当初网页导出的正文少这么多字才值得喊一声。
# 实测 302 封里，PDF 长于导出正文的多半是空白写法差异（正差最大 +142），
# 少字的只有 3 封超过 -60，所以取 60 而不是拿绝对值一刀切。
DRIFT_FLAG = 60

GAP_LABELS = {
    "no-marker": "无标记文件",
    "unchecked": "未检查",
    "complete": "已齐",
    "complete-farewell": "已发离别信",
    "missing": "缺 N 封",
    "extra": "本地多 N 封",
}

LETTER_COLUMNS = {
    "id": "TEXT PRIMARY KEY", "pal": "TEXT NOT NULL", "file": "TEXT NOT NULL", "path": "TEXT NOT NULL",
    "dt": "TEXT NOT NULL", "year": "INTEGER NOT NULL", "sender": "TEXT NOT NULL", "sender_raw": "TEXT NOT NULL",
    "direction": "TEXT NOT NULL", "country": "TEXT", "is_public": "INTEGER NOT NULL DEFAULT 0",
    "read_mark": "INTEGER NOT NULL DEFAULT 0", "chars": "INTEGER NOT NULL", "body": "TEXT NOT NULL",
    "pages": "INTEGER", "pdf_bytes": "INTEGER", "pdf_mtime": "REAL", "att_files": "INTEGER NOT NULL DEFAULT 0",
    "char_drift": "INTEGER", "extracted_at": "TEXT", "metadata_source": "TEXT",
}
PAL_COLUMNS = {
    "name": "TEXT PRIMARY KEY", "letters": "INTEGER", "incoming": "INTEGER", "outgoing": "INTEGER",
    "public_letters": "INTEGER", "first_dt": "TEXT", "last_dt": "TEXT",
    "wall_total": "INTEGER", "gap": "TEXT", "gap_count": "INTEGER", "farewell_sent": "INTEGER",
    "still_writing": "INTEGER", "marker_at": "TEXT", "stamp_files": "INTEGER", "attachments": "INTEGER",
}
META_COLUMNS = {"key": "TEXT PRIMARY KEY", "value": "TEXT"}
TABLES = {"letters": LETTER_COLUMNS, "pals": PAL_COLUMNS, "meta": META_COLUMNS}
# pals 汇总里的键名是给前端看的驼峰写法，入库按 PAL_COLUMNS 顺序取值
PAL_FIELDS = ["name", "letters", "in", "out", "public", "first", "last", "wallTotal", "gap",
              "gapCount", "farewellSent", "stillWriting", "markerAt", "stamps", "attachments"]


def values(row: dict, fields: list[str]) -> tuple:
    return tuple(int(bool(row[f])) if isinstance(row.get(f), bool) else row.get(f) for f in fields)


def tidy(text: str) -> str:
    """给人看的正文清洗：剥离图标字体、还原部首形汉字、收紧中文字距。不做全量兼容转换。"""
    out = ICON_GLYPH.sub("", text)
    out = RADICAL_BLOCK.sub(lambda m: unicodedata.normalize("NFKC", m.group()), out)
    out = out.translate(RADICAL_SUPPLEMENT)
    return CJK_GAP.sub("", out)


def normalize(text: str) -> str:
    """用于比对的强归一：全量兼容还原 + 剥离图标 + 部首形还原 + 去空白 + 小写。"""
    out = unicodedata.normalize("NFKC", text)
    out = ICON_GLYPH.sub("", out)
    out = re.sub(r"\s+", "", out.translate(RADICAL_SUPPLEMENT)).casefold()
    return out


def resolve_root(cli_root: str | None, script_dir: Path) -> Path:
    if cli_root:
        return Path(cli_root).expanduser().resolve()
    env = os.environ.get(ENV_ROOT)
    if env:
        return Path(env).expanduser().resolve()
    for cfg in (script_dir / "library_root.txt.local", script_dir / CONFIG_FILE):
        if cfg.exists():
            for line in cfg.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    return Path(line).expanduser().resolve()
    return Path.home() / "Desktop" / "笔友库"


def resolve_out(cli_out: str | None) -> Path:
    if cli_out:
        return Path(cli_out).expanduser().resolve()
    env = os.environ.get(ENV_OUT)
    if env:
        return Path(env).expanduser().resolve()
    cfg = Path(__file__).parent / "library_out.txt.local"
    if cfg.is_file() and cfg.read_text(encoding="utf-8").strip():
        return Path(cfg.read_text(encoding="utf-8").strip()).expanduser().resolve()
    return Path.home() / "Desktop" / "Slowly离线档案"


def is_collection(name: str) -> bool:
    return any(h in name for h in COLLECTION_HINT)


def harvest(root: Path) -> list[tuple[str, Path]]:
    letters: list[tuple[str, Path]] = []
    for pal_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        box = pal_dir / "来往信件"
        if not box.is_dir():
            box = pal_dir
        letters += [(pal_dir.name, p) for p in sorted(box.glob("*.pdf")) if not is_collection(p.name)]
    return letters


def parse_pdf(path: Path) -> tuple[str, int]:
    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    return text, len(reader.pages)


def _region_slot(lines: list[str], i: int, keyed: set[str]) -> tuple[str, int]:
    """日期行紧跟的那一行是否国家/地区：短、无标点、不是写信人别名才算。"""
    if (i < len(lines) and lines[i] != PUBLIC_BADGE and len(lines[i]) <= 12
            and not NOT_A_PLACE.search(lines[i]) and normalize(lines[i]) not in keyed):
        return lines[i], i + 1
    return "", i


def drop_repeated_headers(lines: list[str], keyed: set[str]) -> list[str]:
    """多页 PDF 每翻一页都重打一遍页眉（实测 52 封，全是 2 页以上）。

    只有「写信人一行 + 紧跟日期一行」这种成对出现才算页眉，单独一句提到自己名字不算。
    """
    kept: list[str] = []
    i = 0
    while i < len(lines):
        if (normalize(lines[i]) in keyed and i + 1 < len(lines)
                and PDF_DATE_RE.search(lines[i + 1]) and len(lines[i + 1]) <= 40):
            i += 2
            _, i = _region_slot(lines, i, keyed)
            if i < len(lines) and lines[i] == PUBLIC_BADGE:
                i += 1
            continue
        kept.append(lines[i])
        i += 1
    return kept


def split_header(raw: str, aliases: tuple[str, ...]) -> dict:
    """按固定顺序剥离页眉：写信人 → 日期 → 国家/地区 → 公开信角标。

    每一槽只在原位命中才消费一次，之后一律视为正文；页眉整块缺失也不做猜测，
    日期与写信人始终以文件名为准。正文里再出现成对页眉（翻页重复）由
    `drop_repeated_headers` 清掉，末尾的应用页脚（字数/字元）也不算正文。
    """
    lines = [ln for ln in (tidy(x).strip() for x in raw.splitlines()) if ln]
    keyed = {normalize(a) for a in aliases}
    country = ""
    is_public = False
    i = 0
    if i < len(lines) and normalize(lines[i]) in keyed:
        i += 1                                        # 写信人
    if i < len(lines) and PDF_DATE_RE.search(lines[i]) and len(lines[i]) <= 40:
        i += 1                                        # 日期
        country, i = _region_slot(lines, i, keyed)    # 国家/地区
    if i < len(lines) and lines[i] == PUBLIC_BADGE:
        is_public = True                              # 角标
        i += 1
    body = drop_repeated_headers(lines[i:], keyed)
    if body and FOOTER_RE.match(body[-1]):
        body = body[:-1]
    return {"country": country, "is_public": is_public, "body": "\n".join(body).strip()}


def read_marker(pal_dir: Path) -> dict:
    """笔友文件夹里的 .slowly-pal：网页版导出时就写在本地，这里只读不写。"""
    path = pal_dir / MARKER_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"_broken": True}
    return data if isinstance(data, dict) else {"_broken": True}


def gap_status(marker: dict, pdf_count: int) -> tuple[str, int | None]:
    """墙上封数（导出当时记下的）对比本地 PDF 数；离别信已发就不算缺口。"""
    if not marker:
        return ("no-marker", None)
    if marker.get("_broken"):
        return ("unchecked", None)
    wall = marker.get("wallTotal")
    if not isinstance(wall, int):
        return ("unchecked", None)
    gap = wall - pdf_count
    if gap == 0:
        return ("complete", 0)
    if gap > 0:
        farewell = marker.get("farewell") or {}
        unexported = farewell.get("unexported") if isinstance(farewell, dict) else None
        if marker.get("farewellSent") and unexported in (None, gap):
            return ("complete-farewell", gap)
        return ("missing", gap)
    return ("extra", -gap)


def gap_label(code: str, count: int | None) -> str:
    text = GAP_LABELS.get(code, code)
    return text.replace("N", str(count)) if count is not None else text


def stamp_files_of(pal_dir: Path) -> list[str]:
    box = pal_dir / "邮票"
    if not box.is_dir():
        return []
    return sorted(p.name for p in box.iterdir() if p.suffix.lower() in {".png", ".jpg", ".webp"})


def stamp_slug(name: str) -> str:
    """一枚邮票的图案标识：去扩展名、去重名带的 (2) 后缀。"""
    return DUP_SUFFIX_RE.sub("", Path(name).stem)


def attachments_of(pal_dir: Path) -> dict[str, int]:
    """.data/附件/<日期 时间-写信人>-图N.jpg 按信件名归堆（只数文件名，不读图）。"""
    box = pal_dir / ".data" / "附件"
    out: dict[str, int] = {}
    if not box.is_dir():
        return out
    for p in box.iterdir():
        if not p.is_file() or p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            continue
        key = p.stem.rsplit("-图", 1)[0]
        out[key] = out.get(key, 0) + 1
    return out


def attachment_count(atts: dict[str, int], file_stem: str) -> int:
    if file_stem in atts:
        return atts[file_stem]
    return atts.get(file_stem.removesuffix(READ_SUFFIX), 0)


def build_record(root: Path, pal: str, pdf: Path, att_files: int = 0) -> dict:
    match = FILE_RE.match(pdf.stem)
    raw, pages = parse_pdf(pdf)
    if match:
        metadata_source = "filename"
        date, hhmm, sender = match["date"], match["time"], match["sender"]
        dt = datetime.strptime(f"{date} {hhmm}", "%Y-%m-%d %H%M").strftime("%Y-%m-%d %H:%M")
    else:
        lines = [tidy(line).strip() for line in raw.splitlines() if tidy(line).strip()]
        # 手动打印常用 Slowly.pdf：仅认开头的写信人 + 下一行日期，不在正文中猜日期。
        date_match = PDF_DATE_RE.fullmatch(lines[1]) if len(lines) >= 2 else None
        if date_match and lines[0] and len(lines[0]) <= 80:
            metadata_source = "pdf-header"
            sender = lines[0]
            dt = datetime(*map(int, date_match.groups())).strftime("%Y-%m-%d %H:%M")
        else:
            metadata_source = "unknown"
            sender, dt = "", ""
    pal_name = re.sub(r"[（(][^）)]*[）)]$", "", pal).strip()
    head = (split_header(raw, (sender, pal, pal_name)) if metadata_source != "unknown"
            else {"body": tidy(raw).strip(), "country": "", "is_public": False})
    stat = pdf.stat()
    same_as_pal = normalize(sender) in {normalize(pal), normalize(pal_name)}
    return {
        "id": hashlib.sha1(f"{pal}/{pdf.name}".encode("utf-8")).hexdigest()[:12],
        "pal": pal,
        "file": pdf.name,
        "path": str(pdf.resolve()),
        "dt": dt,
        "year": int(dt[:4]) if dt else 0,
        "sender_raw": sender,
        "sender": tidy(sender).strip(),
        "direction": "unknown" if metadata_source == "unknown" else ("in" if same_as_pal else "out"),
        "metadata_source": metadata_source,
        "country": head["country"],
        "is_public": head["is_public"],
        "read_mark": bool(match and match["read"]),
        "chars": len(head["body"]),
        "body": head["body"],
        "pages": pages,
        "pdf_bytes": stat.st_size,
        "pdf_mtime": stat.st_mtime,
        "att_files": att_files,
        "char_drift": None,
    }


def squash(text: str) -> str:
    """去掉所有空白：PDF 文本层没有空行、段首缩进也被压平，比原文长度会把这种排版差异当成丢字。"""
    return re.sub(r"\s+", "", text)


def verify_bodies(root: Path, records: list[dict]) -> tuple[list[dict], int]:
    """可选对账：把 PDF 文本层正文和网页版当初存下的 `.data/<同名>.json` 正文比一比内容量。

    负差（PDF 少字）才是要紧的：可能导出时截断，也可能页眉判定吞掉了正文首行。
    只比压平空白后的长度，排版差异（空行、缩进）不算问题。只读，不改任何源文件。
    """
    report: list[dict] = []
    matched = 0
    for r in records:
        js = root / r["pal"] / ".data" / (r["file"][:-4] + ".json")
        if not js.is_file():
            continue
        try:
            data = json.loads(js.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        source = str(data.get("text") or "")
        if not source:
            continue
        matched += 1
        drift = len(squash(r["body"])) - len(squash(source))
        r["char_drift"] = drift
        if drift < -DRIFT_FLAG:
            report.append({"pal": r["pal"], "file": r["file"], "pdfChars": len(squash(r["body"])),
                           "dataChars": len(squash(source)), "drift": drift,
                           "charInfo": str(data.get("charInfo") or "")})
    report.sort(key=lambda x: x["drift"])
    return report, matched


def summarize(records: list[dict], extras: dict[str, dict] | None = None) -> list[dict]:
    extras = extras or {}
    pals: dict[str, dict] = {}
    for r in records:
        p = pals.setdefault(r["pal"], {
            "name": r["pal"], "letters": 0, "in": 0, "out": 0, "public": 0,
            "first": r["dt"], "last": r["dt"], "gap": "no-marker", "gapCount": None,
            "gapLabel": GAP_LABELS["no-marker"], "wallTotal": None, "farewellSent": False,
            "stillWriting": False, "markerAt": "", "stamps": 0, "stampSlugs": [],
            "attachments": 0,
        })
        p["letters"] += 1
        if r["direction"] in ("in", "out"):
            p[r["direction"]] += 1
        p["public"] += 1 if r["is_public"] else 0
        p["attachments"] += r.get("att_files") or 0
        p["first"] = min(p["first"], r["dt"])
        p["last"] = max(p["last"], r["dt"])
    for name, extra in extras.items():
        p = pals.setdefault(name, {
            "name": name, "letters": 0, "in": 0, "out": 0, "public": 0,
            "first": "", "last": "", "gap": "no-marker", "gapCount": None,
            "gapLabel": GAP_LABELS["no-marker"], "wallTotal": None, "farewellSent": False,
            "stillWriting": False, "markerAt": "", "stamps": 0, "stampSlugs": [], "attachments": 0,
        })
        for key in ("gap", "gapCount", "wallTotal", "farewellSent", "stillWriting", "markerAt"):
            p[key] = extra.get(key, p[key])
        p["gapLabel"] = extra.get("gapLabel", p["gapLabel"])
        p["stamps"] = extra.get("stamps", p["stamps"])
        p["stampSlugs"] = extra.get("stampSlugs", p["stampSlugs"])
        p["attachments"] = extra.get("attachments", p["attachments"])
    return [pals[k] for k in sorted(pals)]


def ensure_schema(con: sqlite3.Connection) -> list[str]:
    """建表 + 增量加列：老库不删，新增字段一律 ADD COLUMN 补齐。

    老表里已有数据时，SQLite 不允许直接加「无默认值的 NOT NULL」列，
    所以给这类补列按类型垫一个空默认值。
    """
    added: list[str] = []
    for table, cols in TABLES.items():
        con.execute("CREATE TABLE IF NOT EXISTS {}({})".format(
            table, ", ".join(f"{n} {d}" for n, d in cols.items())))
        have = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
        for name, decl in cols.items():
            if name not in have:
                upper = decl.upper()
                if "NOT NULL" in upper and "DEFAULT" not in upper:
                    default = "0" if ("INTEGER" in upper or "REAL" in upper) else "''"
                    decl = f"{decl} DEFAULT {default}"
                con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
                added.append(f"{table}.{name}")
    con.execute("CREATE INDEX IF NOT EXISTS idx_letters_pal ON letters(pal)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_letters_dt ON letters(dt)")
    return added


def load_records(out: Path) -> dict[str, dict]:
    """沿用现有库；读取失败时直接停止，避免用空库覆盖已有档案。"""
    db = out / "slowly_pdf.db"
    if not db.exists():
        return {}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        records = {}
        for row in con.execute("SELECT * FROM letters"):
            record = dict(row)
            record["is_public"] = bool(record["is_public"])
            record["read_mark"] = bool(record["read_mark"])
            record["att_files"] = record.get("att_files") or 0
            records[record["id"]] = record
        return records
    finally:
        con.close()


def stored_parser_version(out: Path) -> str:
    """库里记的解析规则版本；没有版本号的旧库算 legacy，必须全量重算一次。"""
    db = out / "slowly_pdf.db"
    if not db.exists():
        return PARSER_VERSION
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        row = con.execute("SELECT value FROM meta WHERE key='parser_version'").fetchone()
        return row[0] if row else "legacy"
    except sqlite3.Error:
        return "legacy"
    finally:
        con.close()


def write_db(out: Path, records: list[dict], pals: list[dict], meta: dict) -> None:
    con = sqlite3.connect(out / "slowly_pdf.db")
    try:
        con.execute("BEGIN IMMEDIATE")
        ensure_schema(con)
        cols = ", ".join(LETTER_COLUMNS)
        holders = ", ".join("?" * len(LETTER_COLUMNS))
        updates = ", ".join(f"{c}=excluded.{c}" for c in LETTER_COLUMNS if c != "id")
        con.executemany(
            f"INSERT INTO letters({cols}) VALUES({holders}) ON CONFLICT(id) DO UPDATE SET {updates}",
            [values(r, list(LETTER_COLUMNS)) for r in records],
        )
        con.execute("DELETE FROM pals")
        pal_cols = ", ".join(PAL_COLUMNS)
        pal_holders = ", ".join("?" * len(PAL_COLUMNS))
        con.executemany(
            f"INSERT INTO pals({pal_cols}) VALUES({pal_holders})",
            [values(p, PAL_FIELDS) for p in pals],
        )
        con.execute("DELETE FROM meta")
        con.executemany("INSERT INTO meta VALUES(?,?)", [(k, str(v)) for k, v in meta.items()])
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()


def write_html(out: Path, payload: dict, template: str) -> None:
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("/*__PAYLOAD__*/ null", blob)
    if "/*__PAYLOAD__*/" in html:
        raise SystemExit("模板占位符缺失，未写出 index.html")
    (out / "index.html").write_text(html, encoding="utf-8")


def pal_extras(root: Path, pdf_counts: dict[str, int]) -> dict[str, dict]:
    """每位笔友的本地状态：标记文件给的墙上封数、离别信/仍在通信、邮票与附件计数。"""
    extras: dict[str, dict] = {}
    for pal_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if not (pal_dir / "来往信件").is_dir() and not any(pal_dir.glob("*.pdf")):
            continue
        name = pal_dir.name
        marker = read_marker(pal_dir)
        code, count = gap_status(marker, pdf_counts.get(name, 0))
        stamps = stamp_files_of(pal_dir)
        atts = attachments_of(pal_dir)
        extras[name] = {
            "gap": code,
            "gapCount": count,
            "gapLabel": gap_label(code, count),
            "wallTotal": marker.get("wallTotal") if isinstance(marker.get("wallTotal"), int) else None,
            "farewellSent": bool(marker.get("farewellSent")),
            "stillWriting": bool(marker.get("stillWriting")),
            "markerAt": str(marker.get("checkedAt") or marker.get("lastExportAt") or ""),
            "stamps": len(stamps),
            "stampSlugs": [stamp_slug(s) for s in stamps],
            "attachments": sum(atts.values()),
        }
    return extras


def run_build(root: Path, out: Path, pal_filter: str | None = None, opts: dict | None = None) -> int:
    opts = opts or {}
    pdf_only = bool(opts.get("pdf_only"))
    verify = bool(opts.get("verify_data"))
    if not root.is_dir():
        print(f"资料目录不存在：{root}", file=sys.stderr)
        print("用 --root 指定，或改 scripts/library_root.txt / 环境变量 SLOWLY_PDF_ROOT。", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    files = harvest(root)
    counts: dict[str, int] = {}
    for pal, _ in files:
        counts[pal] = counts.get(pal, 0) + 1
    if pal_filter:
        files = [(p, f) for p, f in files if p == pal_filter]

    extras = {} if pdf_only else pal_extras(root, counts)
    atts_by_pal = {} if pdf_only else {
        pal: attachments_of(root / pal) for pal in {p for p, _ in files}
    }

    merged = load_records(out)
    if not files and not merged:
        print("没有找到信件 PDF。请选择包含笔友子文件夹的资料总目录。", file=sys.stderr)
        return 2
    stale_rules = stored_parser_version(out) != PARSER_VERSION
    full_mode = bool(opts.get("full")) or stale_rules
    built_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    changes: list[dict] = []
    added = updated = unchanged = 0
    errors: list[dict] = []
    for pal, pdf in files:
        try:
            key = hashlib.sha1(f"{pal}/{pdf.name}".encode("utf-8")).hexdigest()[:12]
            old = merged.get(key)
            att = attachment_count(atts_by_pal.get(pal, {}), pdf.stem)
            stat = pdf.stat()
            if (old and not full_mode and old["pdf_bytes"] == stat.st_size
                    and old["pdf_mtime"] == stat.st_mtime and old["path"] == str(pdf.resolve())
                    and (old.get("att_files") or 0) == att):
                unchanged += 1
                continue
            record = build_record(root, pal, pdf, att)
            record["extracted_at"] = built_at
            if old:
                record["char_drift"] = old.get("char_drift")
                updated += 1
            else:
                added += 1
            merged[key] = record
            changes.append(record)
        except Exception as exc:  # 一份坏 PDF 不掀翻整批
            errors.append({"pal": pal, "file": pdf.name, "error": f"{type(exc).__name__}: {exc}"})

    records = sorted(merged.values(), key=lambda r: (r["pal"], r["dt"], r["id"]))
    drift_report, drift_checked = ([], 0)
    if verify:
        drift_report, drift_checked = verify_bodies(root, records)
        changes = records
    pals = summarize(records, extras)
    stamp_rows = sum(p["stamps"] for p in pals)
    stamp_distinct = len({s for p in pals for s in p["stampSlugs"]})
    meta = {
        "built_at": built_at,
        "parser_version": PARSER_VERSION,
        "source_root": str(root),
        "source": "local PDF only",
        "network": "none",
        "letters": len(records),
        "pals": len(pals),
        "skipped_collections": sum(1 for p in root.glob("*/来往信件/*.pdf") if is_collection(p.name)),
        "failed": len(errors),
        "mode": "full" if full_mode else "incremental",
        "added": added,
        "updated": updated,
        "unchanged": unchanged,
        "retained": len(records) - added - updated - unchanged,
        "stamp_rows": stamp_rows,
        "stamp_distinct": stamp_distinct,
        "attachments": sum(p["attachments"] for p in pals),
        "markers_missing": sum(1 for p in pals if p["gap"] == "no-marker"),
        "gap_letters": sum(p["gapCount"] or 0 for p in pals if p["gap"] == "missing"),
        "farewell_sent": sum(1 for p in pals if p["farewellSent"]),
        "still_writing": sum(1 for p in pals if p["stillWriting"]),
        "gap_checked": sum(1 for p in pals if p["gap"] in ("complete", "complete-farewell", "missing", "extra")),
        "verify_checked": drift_checked,
        "verify_drift": len(drift_report),
        "unknown_metadata": sum(r.get("metadata_source") == "unknown" for r in records),
    }

    media = ({"images": {}, "stamps": [], "letters": {}, "pals": {}, "warnings": []}
             if pdf_only else build_media(root, records))
    write_db(out, changes, pals, meta)
    (out / "letters.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
    )
    (out / "build.json").write_text(
        json.dumps({"meta": meta, "pals": pals, "errors": errors, "verify": drift_report},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    (out / "media.json").write_text(json.dumps(media, ensure_ascii=False), encoding="utf-8")
    template = (Path(__file__).parent / "viewer.html").read_text(encoding="utf-8")
    write_html(out, {"meta": meta, "pals": pals, "letters": records, "media": media}, template)

    print(f"解析 : {'全量重算（解析规则版本变了）' if stale_rules and not opts.get('full') else ('全量重算' if full_mode else '增量')} "
          f"· 新增 {added} 封 · 更新 {updated} 封 · 未变化 {unchanged} 封 · 保留历史 {meta['retained']} 封")
    print(f"来源 : {root}  （只读本地文件，未产生任何网络请求）")
    print(f"笔友 : {len(pals)} 位 · 信件 : {len(records)} 封"
          f"（去信 {sum(1 for r in records if r['direction']=='out')} / 来信 {sum(1 for r in records if r['direction']=='in')}）")
    public = sum(1 for r in records if r["is_public"])
    print(f"标记 : 公开信 {public} 封 · 已读后缀 {sum(1 for r in records if r['read_mark'])} 封"
          f" · 合成册跳过 {meta['skipped_collections']} 本")
    if not pdf_only:
        gap_pals = [p for p in pals if p["gap"] in ("missing", "unchecked", "no-marker", "extra")]
        print(f"完整性 : 齐 {sum(1 for p in pals if p['gap'] in ('complete', 'complete-farewell'))} 位"
              f" · 缺信 {meta['gap_letters']} 封"
              f" · 待确认 {len(gap_pals)} 位（含无标记文件 {meta['markers_missing']} 位）"
              f" · 已发离别信 {meta['farewell_sent']} 位 · 仍在通信 {meta['still_writing']} 位")
        for p in gap_pals[:6]:
            print(f"           - {p['name']} : {p['gapLabel']}"
                  f"（本地 {p['letters']} 封" + (f"，墙上 {p['wallTotal']} 封）" if p["wallTotal"] else "）"))
        if len(gap_pals) > 6:
            print(f"           … 另有 {len(gap_pals) - 6} 位，见 build.json")
        print(f"邮票 : {stamp_rows} 枚记录 / {stamp_distinct} 种不同图案（同一图案被多位笔友用过会重复计）"
              f" · 附件 {meta['attachments']} 张")
    if verify:
        print(f"对账 : 比对 {drift_checked} 封 · PDF 比导出正文少逾 {DRIFT_FLAG} 字（不计空行缩进）的 {len(drift_report)} 封"
              "（真丢字才报，见 build.json.verify）")
        for d in drift_report[:6]:
            print(f"           - {d['pal']}/{d['file']} : PDF {d['pdfChars']} vs 导出 {d['dataChars']}（少 {-d['drift']} 字）")
    if errors:
        print(f"告警 : {len(errors)} 份解析失败（已有记录保留）")
        for e in errors[:10]:
            print(f"       - {e['pal']}/{e['file']} : {e['error']}")
    print(f"产出 : {out}/index.html · slowly_pdf.db · letters.jsonl · build.json")
    return 0


def run_query(out: Path, sql: str) -> int:
    db = out / "slowly_pdf.db"
    if not db.is_file():
        print(f"还没有数据库：{db}\n先跑一次构建。", file=sys.stderr)
        return 2
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        cur = con.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        if cols:
            print(" | ".join(cols))
        for row in rows:
            print(" | ".join(str(c) for c in row))
        print(f"-- {len(rows)} 行")
    finally:
        con.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="从本地信件 PDF 离线建库（不联网、不开浏览器）")
    ap.add_argument("--root", help="笔友库根目录，默认按 --root > SLOWLY_PDF_ROOT > library_root.txt > ~/Desktop/笔友库")
    ap.add_argument("--out", help="产出目录，默认 SLOWLY_PDF_OUT 或 ~/Desktop/Slowly离线档案")
    ap.add_argument("--pal", help="只追加或更新某一位笔友，保留库中其他记录")
    ap.add_argument("--sql", help="对已建好的库跑一条只读 SQL，不重新构建")
    ap.add_argument("--full", action="store_true", help="强制全量重解析所有 PDF")
    ap.add_argument("--pdf-only", action="store_true", help="严格只看 PDF：不读 .slowly-pal 标记、不数邮票与附件")
    ap.add_argument("--verify-data", action="store_true",
                    help="额外把 PDF 正文长度与 .data/*.json 的导出正文比一比，只报「PDF 少字」的信（只读）")
    args = ap.parse_args()

    out = resolve_out(args.out)
    if args.sql:
        return run_query(out, args.sql)
    opts = {"full": args.full, "pdf_only": args.pdf_only, "verify_data": args.verify_data}
    return run_build(resolve_root(args.root, Path(__file__).parent), out, args.pal, opts)


if __name__ == "__main__":
    raise SystemExit(main())
