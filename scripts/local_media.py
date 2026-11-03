"""只读本地图片与旁车资料，生成可内嵌的图文索引。"""
import base64
import hashlib
import json
from pathlib import Path
import re

IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp", ".gif": "image/gif"}


def file_uri(path):
    # 自行编码本地文件链接，避免部分 Python 版本的 as_uri 隐式加载网络模块。
    raw = path.resolve().as_posix()
    if not raw.startswith("/"):
        raw = "/" + raw
    safe = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~/:"
    return "file://" + "".join(chr(b) if b in safe else f"%{b:02X}" for b in raw.encode("utf-8"))


def local_file(folder, relative):
    if not isinstance(relative, str) or not relative:
        return None
    root = folder.resolve()
    path = (root / relative).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


def read_object(path):
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (OSError, ValueError):
        return {}


def build_media(root, records):
    root = root.resolve()
    result = {"images": {}, "stamps": [], "letters": {}, "pals": {}, "warnings": []}
    stamps = {}
    cache = {}

    def image(path):
        if not path or path.suffix.lower() not in IMAGE_TYPES:
            return None
        if path in cache:
            return cache[path]
        try:
            content = path.read_bytes()
            key = hashlib.sha256(content).hexdigest()
            result["images"][key] = "data:" + IMAGE_TYPES[path.suffix.lower()] + ";base64," + base64.b64encode(content).decode("ascii")
            cache[path] = key
            return key
        except OSError:
            result["warnings"].append(f"图片不可读：{path.name}")
            return None

    # 无 JSON 也能浏览已有邮票；没有可靠关联就保持未关联。
    names = {r["pal"] for r in records}
    names.update(p.name for p in root.iterdir() if p.is_dir() and (p / "来往信件").is_dir())
    for name in sorted(names):
        folder = root / name
        if not folder.resolve().is_relative_to(root):
            continue
        box = folder / "邮票"
        for path in sorted(box.iterdir()) if box.is_dir() else []:
            safe = local_file(folder, str(path.relative_to(folder)))
            key = image(safe)
            if key:
                sid = name + "/" + path.name
                stamps[sid] = {"id": sid, "pal": name, "name": path.stem, "image": key, "letters": []}
        profile_path = local_file(folder, "个人资料/profile.json")
        profile = read_object(profile_path) if profile_path else {}
        # 只展示资料字段，忽略资料里的任何远端图片或链接。
        profile = {key: profile[key] for key in ("country", "gender", "interests", "bio", "facts", "deactivated") if key in profile}
        links = []
        for rel, label in [(f"来往信件/{name} 书信合集.pdf", "书信合集 PDF"),
                           (f"来往信件/{name} 书信合集.docx", "书信合集 Word"),
                           ("个人资料/个人资料.docx", "个人资料 Word")]:
            path = local_file(folder, rel)
            if path:
                links.append({"label": label, "url": file_uri(path)})
        result["pals"][name] = {"profile": profile, "avatar": image(local_file(folder, "个人资料/头像.png")), "links": links}

    for record in records:
        folder = root / record["pal"]
        if not folder.resolve().is_relative_to(root) or folder.resolve() == root:
            continue
        base = Path(record["file"]).stem
        variants = list(dict.fromkeys([base, base.removesuffix("（已读）")]))
        rec = {}
        for stem in variants:
            path = local_file(folder, ".data/" + stem + ".json")
            if path:
                rec = read_object(path)
                break
        entry = {"stamp": None, "photos": [], "pdf": None}
        pdf = local_file(folder, "来往信件/" + record["file"])
        if not pdf:
            pdf = local_file(folder, record["file"])
        if pdf:
            entry["pdf"] = file_uri(pdf)
        stamp = local_file(folder, rec.get("stampFile"))
        if stamp and image(stamp):
            sid = record["pal"] + "/" + stamp.relative_to(folder.resolve()).as_posix()
            # 邮票目录的键保持一致。
            if stamp.parent.name == "邮票":
                sid = record["pal"] + "/" + stamp.name
            stamps.setdefault(sid, {"id": sid, "pal": record["pal"], "name": stamp.stem,
                                     "image": image(stamp), "letters": []})
            if isinstance(rec.get("stampName"), str) and rec["stampName"]:
                stamps[sid]["name"] = rec["stampName"]
            stamps[sid]["letters"].append(record["id"])
            entry["stamp"] = sid
        photos = rec.get("photoFiles")
        paths = [local_file(folder, rel) for rel in photos] if isinstance(photos, list) else []
        box = folder / ".data" / "附件"
        if box.is_dir():
            for path in sorted(box.iterdir()):
                if any(re.fullmatch(re.escape(stem) + r"-图\d+", path.stem) for stem in variants):
                    paths.append(local_file(folder, str(path.relative_to(folder))))
        seen = set()
        for path in paths:
            if path and path not in seen:
                seen.add(path)
                key = image(path)
                if key:
                    entry["photos"].append(key)
        result["letters"][record["id"]] = entry
    result["stamps"] = list(stamps.values())
    return result
