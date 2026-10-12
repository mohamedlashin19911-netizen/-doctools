"""تحليل الفولدرات وفحص الملفات — كل شيء محلي على القرص، بدون إنترنت."""
import io
import os
import re
from collections import Counter

MAX_TREE = 5000          # حد عقد الشجرة
MAX_SCAN = 3000          # حد الملفات اللي بتتفحص بالعمق
MAX_FSIZE = 60 * 1024 * 1024  # أكبر حجم ملف بيتفحص

CATEGORY = {
    "صور": {"png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp", "ico", "heic", "heif",
             "svg", "avif", "raw", "psd", "cur", "qoi", "tga", "pcx", "ppm", "pgm", "dds"},
    "فيديوهات": {"mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "mpg", "mpeg", "3gp", "ts"},
    "صوتيات": {"mp3", "wav", "flac", "aac", "ogg", "m4a", "wma", "opus"},
    "مستندات": {"pdf", "docx", "doc", "odt", "rtf", "txt", "md", "html", "htm", "pptx", "ppt", "xls", "xlsx", "csv", "epub", "fb2"},
    "أرشيفات": {"zip", "7z", "rar", "tar", "gz", "bz2", "xz", "iso"},
    "برامج ونظام": {"exe", "msi", "bat", "cmd", "ps1", "vbs", "js", "jar", "dll", "sys", "ini", "conf", "sh", "py"},
}


def _category(ext: str) -> str:
    for name, exts in CATEGORY.items():
        if ext in exts:
            return name
    return "أخرى"


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _read_magic(path: str, size: int) -> bytes:
    n = min(size, MAX_FSIZE)
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except OSError:
        return b""


def real_type(data: bytes) -> str:
    """النوع الحقيقي من المحتوى (magic bytes)، راجع امتداد تقريبي أو ''."""
    if not data:
        return ""
    if data[:2] == b"MZ":
        return "exe"
    if data[:4] == b"\x7fELF":
        return "elf"
    if data[:4] == b"%PDF":
        return "pdf"
    if data[:5] == b"{\\rtf" or data[:6] == b"{\\\\rtf1":
        return "rtf"
    if data[:4] == b"\xd0\xcf\x11\xe0":
        return "doc-ole"
    if data[:3] == b"7z\xbc":
        return "7z"
    if data[:4] == b"\x82\x1f\x27":
        return "rar"
    if data[:6] in (b"Rar!\x1a\x07",):
        return "rar"
    if data[:2] == b"PK":
        try:
            import zipfile
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = set(z.namelist())
                if "mimetype" in names and z.read("mimetype").startswith(b"application/epub"):
                    return "epub"
                if any(n.startswith("word/") for n in names):
                    return "docx"
                if any(n.startswith("PPT/") or any(n.startswith("ppt/") for n in names) for n in names):
                    return "pptx"
                if any(n.startswith("xl/") for n in names):
                    return "xlsx"
            return "zip"
        except Exception:
            return "zip"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:2] == b"BM":
        return "bmp"
    if data[:4] == b"RIFF" and data[8:12] in (b"WEBP", b"AVI "):
        return "webp" if data[8:12] == b"WEBP" else "avi"
    if data[:4] == b"OggS":
        return "ogg"
    if data[:4] == b"fLaC":
        return "flac"
    if data[:3] == b"ID3" or data[:2] == b"\xff\xfb":
        return "mp3"
    if data[:5] == b"<html" or data[:6].lower() == b"<!html":
        return "html"
    if data[:4] == b"ftyp" or (data[4:8] == b"ftyp" and len(data) > 12):
        return "mp4"
    if data[:1] == b"#!":
        return "script"
    try:
        text = data[:4096].decode("utf-8")
        ctrl = sum(1 for ch in text if ord(ch) < 9 or 13 < ord(ch) < 32)
        if text and ctrl / len(text) < 0.02:
            return "text"
    except UnicodeDecodeError:
        pass
    return ""


NAME_TRICKS = [
    (re.compile(r"\.(pdf|doc|docx|xls|jpg|png|txt|zip)\s*\.(exe|scr|pif|bat|cmd|vbs|js|msi)\s*$", re.I),
     "امتداد مزدوج مخادع (بيتنكر إنه مستند لكنه برنامج تنفيذي)"),
    (re.compile(r"[^\x00-\x7f].*\.(exe|scr|bat|cmd|vbs)\s*$"),
     "اسم بيختصر Unicode عشان يخفي نوعه التنفيذي"),
    (re.compile(r"\.(exe|scr|pif|bat|cmd|vbs)\s+$"),
     "اسم بيه مسافة بعد الامتداد التنفيذي (محاولة إخفاء)"),
]

SAFE_EXTS = {"pdf", "docx", "xlsx", "pptx", "odt", "rtf", "txt", "md", "html", "htm", "csv",
             "png", "jpg", "jpeg", "gif", "bmp", "webp", "svg", "ico", "heic", "mp3", "mp4"}
EXEC_TYPES = {"exe", "elf", "script"}


def _ext_of(name: str) -> str:
    low = name.lower()
    for multi in ("tar.gz", "tar.bz2", "tar.xz"):
        if low.endswith(multi):
            return multi
    return low.rsplit(".", 1)[-1].lower() if "." in os.path.basename(name) else ""


def inspect_bytes(name: str, data: bytes) -> str:
    """يرجع وصف للمشاكل من الاسم + أول المحتوى، أو '' لو سليم."""
    probs = []
    base = os.path.basename(name)
    ext = _ext_of(name)
    for rx, msg in NAME_TRICKS:
        if rx.search(base):
            probs.append(msg)
    rt = real_type(data)
    if rt in ("exe", "elf") and ext not in ("exe", "msi", "dll", "sys"):
        origin = "برنامج تنفيذي" if rt == "exe" else "برنامج لينكس"
        if ext:
            probs.append(f"بيتنكر إنه .{ext} وأصله {origin} (احتمال ملف خبيث)")
        else:
            probs.append(f"ملف بدون امتداد وأصله {origin}")
    elif rt == "zip" and ext and ext not in ("zip", "docx", "xlsx", "pptx", "epub", "apk", "jar", "odt", "cbz", "vsix", "tgz"):
        probs.append(f"أصله أرشيف ZIP، ومش متوقع كشكل .{ext}")
    elif rt == "script" and ext not in ("sh", "py", "js", "bat", "ps1", "rb"):
        probs.append(f"أصله سكربت وأنتداده الظاهر .{ext or 'بدون'}")
    elif ext in SAFE_EXTS and rt == "":
        probs.append(f"امتحاده .{ext} بس محتواه مش بيتعرف عليه — ملف تالف أو غير متوقع")
    return "؛ ".join(probs)


def inspect_file(path: str, size: int) -> str:
    return inspect_bytes(path, _read_magic(path, size))


ARCHIVE_EXTS = {"zip", "7z", "tar", "tar.gz", "tgz", "tar.bz2", "tar.xz"}
MAX_ARC_SIZE = 300 * 1024 * 1024
MAX_ARC_MEMBERS = 2000


def archive_scan(name: str, data: bytes, depth: int = 1) -> dict:
    """يفحص جوه أرشيف: كل عضو بنوعه الحقيقي، والأرشيفات الداخلية بعمق طبقة."""
    from . import archive as A
    src = _ext_of(name)
    members = A.read_archive(data, src)
    exts = Counter()
    issues = []
    nested = 0
    for mname, mdata in members[:MAX_ARC_MEMBERS]:
        exts[_ext_of(mname) or "(بدون)"] += 1
        msg = inspect_bytes(mname, mdata[:65536])
        if msg:
            issues.append({"path": f"{name} ! {mname}", "msg": msg, "size_h": _human(len(mdata))})
        if depth > 0 and _ext_of(mname) in ARCHIVE_EXTS and len(mdata) < MAX_ARC_SIZE:
            try:
                sub = archive_scan(f"{name} ! {mname}", mdata, depth - 1)
                issues.extend(sub["issues"])
                for e, c in sub["exts"]:
                    exts[e] += c
                nested += 1
            except Exception:
                pass
    return {"members": len(members), "exts": exts.most_common(20),
            "issues": issues, "nested": nested}


def analyze(path: str, deep: bool = True) -> dict:
    if not os.path.isdir(path):
        raise ValueError("المسار مش مجلد — اتأكد إنك كاتب مسار فولدر صحيح")
    path = os.path.abspath(path)
    tree_nodes = [0]
    ext_counter = Counter()
    ext_size = Counter()
    cat_counter = Counter()
    dirs = files = 0
    issues = []
    archives = []
    scanned = [0]
    max_depth_seen = 0

    def build(node_path, depth):
        nonlocal dirs, files, max_depth_seen
        max_depth_seen = max(max_depth_seen, depth)
        children = []
        try:
            entries = sorted(os.scandir(node_path), key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))
        except (OSError, PermissionError):
            return {"name": os.path.basename(node_path) or node_path, "dir": True, "blocked": True, "children": []}
        for e in entries:
            if tree_nodes[0] >= MAX_TREE:
                break
            if e.is_dir(follow_symlinks=False):
                dirs += 1
                tree_nodes[0] += 1
                children.append(build(e.path, depth + 1))
            else:
                files += 1
                try:
                    size = e.stat(follow_symlinks=False).st_size
                except OSError:
                    size = 0
                ext = e.name.rsplit(".", 1)[-1].lower() if "." in e.name else "(بدون)"
                ext_counter[ext] += 1
                ext_size[ext] += size
                cat_counter[_category(ext)] += 1
                node = {"name": e.name, "dir": False, "size": size, "size_h": _human(size), "ext": ext}
                children.append(node)
                if deep and files <= MAX_SCAN and scanned[0] < MAX_SCAN:
                    msg = inspect_file(e.path, size)
                    scanned[0] += 1
                    if msg:
                        rel = os.path.relpath(e.path, path)
                        issues.append({"path": rel, "msg": msg, "size_h": _human(size)})
                    if _ext_of(e.name) in ARCHIVE_EXTS and size <= MAX_ARC_SIZE and len(archives) < 100:
                        try:
                            with open(e.path, "rb") as fh:
                                adata = fh.read(size)
                            rel = os.path.relpath(e.path, path)
                            sub = archive_scan(rel, adata)
                            sub["path"] = rel
                            sub["size_h"] = _human(size)
                            archives.append(sub)
                            issues.extend(sub["issues"])
                        except Exception:
                            pass
        return {"name": os.path.basename(node_path) or node_path, "dir": True, "children": children}

    tree = build(path, 0)
    total_size = sum(ext_size.values())
    return {
        "path": path,
        "tree": tree,
        "stats": {
            "dirs": dirs, "files": files,
            "total_size_h": _human(total_size),
            "max_depth": max_depth_seen,
            "scanned": scanned[0] if deep else 0,
            "truncated": files > MAX_TREE or tree_nodes[0] >= MAX_TREE,
        },
        "exts": [{"ext": e, "count": c, "size_h": _human(ext_size[e])} for e, c in ext_counter.most_common(40)],
        "cats": [{"cat": k, "count": v} for k, v in cat_counter.most_common()],
        "archives": [{"path": a["path"], "members": a["members"], "size_h": a["size_h"],
                      "nested": a["nested"], "bad": len(a["issues"]),
                      "exts": a["exts"][:10]} for a in archives],
        "issues": issues,
    }
