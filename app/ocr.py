"""تفريغ النص بالتصوير الضوئي — يستخدم محرك OCR المدمج في ويندوز، محلي بالكامل."""
import io
import os
import re
import subprocess
import tempfile

import pymupdf
from PIL import Image

PS1 = os.path.join(os.path.dirname(__file__), "ocr.ps1")
startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW


def _run_ocr(png: bytes, lang: str) -> tuple:
    """OCR لصورة PNG — يرجع (نص، لغة المحرك)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    out = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="wb")
    tmp.write(png); tmp.close(); out.close()
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", PS1,
             "-Path", tmp.name, "-OutFile", out.name, "-Lang", lang],
            capture_output=True, text=True, timeout=120,
            startupinfo=startupinfo)
        engine = ""
        for ln in (r.stdout or "").splitlines():
            if ln.startswith("ENGINE:"):
                engine = ln[7:].strip()
        if "NO_ENGINE" in (r.stdout or "") or r.returncode != 0:
            raise ValueError("محرك OCR غير متوفر على هذا الجهاز")
        with open(out.name, encoding="utf-8") as f:
            return f.read().strip(), engine
    finally:
        import gc
        gc.collect()
        for p in (tmp.name, out.name):
            try:
                os.unlink(p)
            except OSError:
                pass


def _to_png(data: bytes) -> bytes:
    img = Image.open(io.BytesIO(data))
    img.load()
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if img.width * img.height > 4_000_000:
        img = img.resize((2000, max(1, int(img.height * 2000 / img.width))))
    b = io.BytesIO(); img.save(b, "PNG")
    return b.getvalue()


def image_to_text(data: bytes, lang: str) -> tuple:
    return _run_ocr(_to_png(data), lang)


def pdf_to_text(data: bytes, lang: str, min_chars: int = 25) -> tuple:
    """PDF → نص: الطبقة النصية أولًا، والصفحات الممسوحة ضوئيًا تتعملها OCR."""
    doc = pymupdf.open(stream=data, filetype="pdf")
    parts, engine = [], ""
    for page in doc:
        text = page.get_text().strip()
        if len(text) >= min_chars:
            parts.append(text)
        else:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            b = io.BytesIO(); img.save(b, "PNG")
            t, engine = _run_ocr(b.getvalue(), lang)
            parts.append(t)
    doc.close()
    return "\n\n".join(parts).strip(), engine


def docx_to_text(data: bytes) -> tuple:
    import docx
    d = docx.Document(io.BytesIO(data))
    return "\n\n".join(p.text for p in d.paragraphs if p.text.strip()), "docx"


FORMAT_MODES = ("none", "simple", "paragraphs", "structured")


def format_text(text: str, mode: str) -> str:
    """مستويات التنسيق للنص المتفرَّغ."""
    if mode == "none" or not text:
        return text
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.splitlines()]
    lines = [l for l in lines if l]
    if mode == "simple":
        return "\n".join(lines)
    # فقرات: ادمج الأسطر المتتابعة، والفصل بإشارة ترقيم أو سطر قصير
    paras, cur = [], []
    for l in lines:
        cur.append(l)
        if re.search(r"[.!؟?؛\"]$", l) or len(l) < 40:
            paras.append(" ".join(cur)); cur = []
    if cur:
        paras.append(" ".join(cur))
    if mode == "paragraphs":
        return "\n\n".join(paras)
    # structured: أول سطر عنوان، والقوائم تتعرف على علاماتها
    import re as _re
    out = []
    for i, p in enumerate(paras):
        if i == 0 and len(p) < 70 and not _re.search(r"[.!؟?]$", p):
            out.append("# " + p)
        elif _re.match(r"^([-•*\u0645\u0628]\s+|\d+[.)]\s+)", p):
            out.append("- " + _re.sub(r"^([-•*\u0645\u0628]\s+|\d+[.)]\s+)", "", p))
        else:
            out.append(p)
    return "\n\n".join(out)
