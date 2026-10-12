"""بناء المستندات من_blocks المحرر — export إلى PDF/DOCX/PNG/HTML/MD/TXT."""
import io
import re
import base64
from html import escape, unescape

import pymupdf
from PIL import Image

from .convert import _story_pdf, _norm_image, pdf_to


def _blocks_html(blocks: list) -> str:
    out = []
    for b in blocks:
        if b.get("type") == "image":
            raw = b.get("data", "")
            if "," in raw[:60]:
                header, raw = raw.split(",", 1)
                ext = "png"
                m = re.search(r"image/(\w+)", header)
                if m:
                    ext = {"jpeg": "jpg", "svg+xml": "png"}.get(m.group(1), m.group(1))
            else:
                ext = "png"
            out.append(f'<div style="text-align:center"><img src="data:image/{ext};base64,{raw}"></div>')
        else:
            html = b.get("html", "")
            html = re.sub(r"<img[^>]*>", "", html)
            if not html.strip() or html.strip() in ("<br>", "<div><br></div>"):
                continue
            out.append(f'<div dir=auto style="unicode-bidi:plaintext">{html}</div>')
    return "".join(out)


def _html_to_plain(html: str) -> str:
    html = re.sub(r"<(h[1-6])[^>]*>", r"\n[\1] ", html)
    html = re.sub(r"</h[1-6]>", "\n", html)
    html = re.sub(r"<(p|div|li|br|tr)[^>]*>", "\n", html)
    text = unescape(re.sub(r"<[^>]+>", "", html))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def build(fmt: str, blocks: list, name: str) -> tuple:
    """يرجع (bytes, ext, mime-safe) أو ('zip', pages)"""
    if fmt == "pdf":
        return _story_pdf(_blocks_html(blocks)), "pdf"
    if fmt in ("png", "jpg"):
        pdf = _story_pdf(_blocks_html(blocks))
        kind, data_or_files, ext = pdf_to(pdf, fmt, name)
        if kind == "zip":
            pages = [d for _, d in data_or_files]
            imgs = [Image.open(io.BytesIO(p)) for p in pages]
            total = io.BytesIO()
            if len(imgs) == 1:
                imgs[0].save(total, "JPEG" if fmt == "jpg" else "PNG")
                return total.getvalue(), fmt
            w = max(i.width for i in imgs)
            h = sum(i.height for i in imgs)
            canvas = Image.new("RGB", (w, h), "white")
            y = 0
            for i in imgs:
                canvas.paste(i.resize((w, round(i.height * w / i.width))), (0, y))
                y += round(i.height * w / i.width)
            canvas.save(total, "JPEG" if fmt == "jpg" else "PNG")
            return total.getvalue(), fmt
        return data_or_files, ext
    if fmt == "html":
        html = ("<!doctype html><html dir=auto><head><meta charset=utf-8>"
                f"<title>{escape(name)}</title>"
                "<style>body{font-family:Segoe UI,sans-serif;max-width:800px;margin:2rem auto;"
                "line-height:1.8}img{max-width:100%}</style></head><body>"
                + _blocks_html(blocks) + "</body></html>")
        return html.encode("utf-8"), "html"
    if fmt == "txt":
        return _html_to_plain(_blocks_html(blocks)).encode("utf-8"), "txt"
    if fmt == "md":
        import markdown2  # تحويل بسيط عبر تنسيق الـ html الموجود
        html = _blocks_html(blocks)
        md = markdown2.markdown(html, extras=["cuddled-lists"]) if False else _html_to_md(html)
        return md.encode("utf-8"), "md"
    if fmt == "docx":
        import docx
        from docx.shared import Inches
        d = docx.Document()
        for b in blocks:
            if b.get("type") == "image":
                raw = b.get("data", "")
                if "," in raw[:60]:
                    raw = raw.split(",", 1)[1]
                try:
                    img = Image.open(io.BytesIO(base64.b64decode(raw)))
                    out = io.BytesIO()
                    img.save(out, "PNG")
                    out.seek(0)
                    d.add_picture(out, width=Inches(6))
                except Exception:
                    pass
            else:
                _append_docx_html(d, b.get("html", ""))
        buf = io.BytesIO()
        d.save(buf)
        return buf.getvalue(), "docx"
    if fmt == "pptx":
        from .pptxgen import build_pptx
        sections = []
        cur = None
        for b in blocks:
            if b.get("type") == "image":
                raw = b.get("data", "")
                if "," in raw[:60]:
                    raw = raw.split(",", 1)[1]
                try:
                    img_bytes = base64.b64decode(raw)
                except Exception:
                    continue
                if cur is None:
                    cur = {"title": "", "bullets": [], "images": []}
                    sections.append(cur)
                cur["images"].append(img_bytes)
                continue
            html = b.get("html", "")
            hm = re.match(r"\s*<h([12])[^>]*>(.*?)</h\1>", html, re.IGNORECASE | re.DOTALL)
            if hm:
                cur = {"title": _html_to_plain(hm.group(2)), "bullets": [], "images": []}
                sections.append(cur)
                continue
            text = _html_to_plain(html)
            if not text:
                continue
            if cur is None:
                lines = text.splitlines()
                cur = {"title": lines[0] if lines else "", "bullets": lines[1:], "images": []}
                sections.append(cur)
            else:
                cur["bullets"] += [l for l in text.splitlines() if l.strip()]
        if not sections:
            raise ValueError("لا يوجد محتوى للتحويل إلى PowerPoint")
        return build_pptx(sections), "pptx"
    raise ValueError(f"صيغة غير مدعومة للحفظ: {fmt}")


def _html_to_md(html: str) -> str:
    text = _html_to_plain(html)
    text = re.sub(r"\n\[h([1-6])\] ", lambda m: "\n" + "#" * int(m.group(1)) + " ", text)
    text = re.sub(r"^\[(h\d)\] ", r"\1", text)
    return text


def _append_docx_html(d, html: str):
    import docx
    chunks = re.split(r"<(?:h[1-6]|p|div|li)[^>]*>", html)
    tags = re.findall(r"<(h[1-6]|p|div|li)[^>]*>", html)
    for tag, chunk in zip(tags, chunks[1:]):
        clean = unescape(re.sub(r"<[^>]+>", "", chunk)).strip()
        if not clean:
            continue
        if tag.startswith("h"):
            d.add_heading(clean, int(tag[1]))
        else:
            d.add_paragraph(clean)
