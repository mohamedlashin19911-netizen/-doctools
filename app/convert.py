"""تحويل الصيغات — كل العمليات محلية على الجهاز، بدون رفع أي بيانات."""
import io
import re
import csv as csvmod
import zipfile
from html import escape, unescape

import pymupdf
from PIL import Image

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass

if not hasattr(pymupdf.Rect, "get_area"):
    pymupdf.Rect.get_area = lambda self: abs(self.width * self.height)

try:
    from pdf2docx import Converter
except Exception:
    Converter = None

try:
    import markdown as _md
except Exception:
    _md = None

IMAGE_SAVE = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "gif", "ico", "heic", "heif",
              "avif", "ppm", "tga", "pcx", "jp2", "dds", "sgi", "im", "xbm", "eps"}
IMAGE_READONLY = {"cur", "qoi", "xpm", "icns", "psd", "wmf", "mpo", "dib", "pgm", "pbm", "j2k"}
IMAGE_EXTS = IMAGE_SAVE | IMAGE_READONLY
TABLE_EXTS = {"xlsx", "csv", "xls", "tsv"}
TEXT_LIKE = {"txt", "md", "html", "rtf", "json", "xml", "log", "odt",
             "yaml", "yml", "toml", "ini", "cfg", "conf", "tex", "rst", "srt", "vtt"}
ARCHIVE_EXTS = {"zip", "7z", "tar", "tar.gz", "tgz"}
PAGED_EXTS = {"xps", "fb2", "cbz", "epub"}

_IMG_TARGETS = ["pdf", "pptx", "png", "jpg", "jpeg", "webp", "bmp", "tiff", "gif", "ico",
                "avif", "ppm", "tga", "pcx", "jp2", "dds", "sgi", "im", "eps"]
_DOC_TARGETS = ["pdf", "docx", "pptx", "txt", "md", "html", "png", "jpg"]

TARGETS = {
    "pdf": _DOC_TARGETS,
    "docx": _DOC_TARGETS,
    "pptx": _DOC_TARGETS,
    "odt": _DOC_TARGETS,
    "xlsx": ["csv", "tsv", "xls", "html", "md", "txt", "pdf", "png"],
    "csv": ["xlsx", "xls", "tsv", "html", "md", "txt", "pdf", "png"],
    "tsv": ["xlsx", "xls", "csv", "html", "md", "txt", "pdf", "png"],
    "xls": ["xlsx", "csv", "tsv", "html", "md", "txt", "pdf"],
    "txt": ["pdf", "docx", "pptx", "html", "md", "png"],
    "md": ["pdf", "docx", "pptx", "html", "txt", "png"],
    "html": ["pdf", "docx", "pptx", "txt", "md", "png"],
    "rtf": ["pdf", "docx", "pptx", "html", "txt", "md"],
    "json": ["pdf", "docx", "txt", "html", "md", "yaml", "csv"],
    "xml": ["pdf", "docx", "txt", "html", "md"],
    "yaml": ["pdf", "txt", "html", "md", "json"],
    "yml": ["pdf", "txt", "html", "md", "json"],
    "toml": ["pdf", "txt", "html", "json"],
    "ini": ["pdf", "txt", "html"],
    "cfg": ["pdf", "txt", "html"],
    "conf": ["pdf", "txt", "html"],
    "tex": ["pdf", "txt", "html", "md"],
    "rst": ["pdf", "txt", "html", "md"],
    "srt": ["pdf", "txt", "html", "vtt"],
    "vtt": ["pdf", "txt", "html", "srt"],
    "log": ["pdf", "txt", "html"],
    "svg": ["pdf", "png", "jpg", "webp", "bmp", "tiff"],
    "xps": ["pdf", "txt", "png"],
    "fb2": ["pdf", "txt", "html"],
    "cbz": ["pdf", "png"],
    "epub": ["pdf", "txt", "html"],
    **{e: _IMG_TARGETS for e in IMAGE_EXTS - {"eps"}},
    **{e: ["extract", "pdf", "docx", "txt", "png", "jpg", "zip", "7z", "tar", "tar.gz"]
       for e in ARCHIVE_EXTS},
}

MIME = {
    "pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp",
    "tiff": "image/tiff", "gif": "image/gif", "bmp": "image/bmp", "ico": "image/x-icon",
    "heic": "image/heic", "heif": "image/heif", "svg": "image/svg+xml",
    "txt": "text/plain; charset=utf-8", "md": "text/markdown; charset=utf-8",
    "log": "text/plain; charset=utf-8", "rtf": "text/rtf",
    "html": "text/html; charset=utf-8", "csv": "text/csv; charset=utf-8",
    "json": "application/json", "xml": "application/xml",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel", "odt": "application/vnd.oasis.opendocument.text",
    "zip": "application/zip", "7z": "application/x-7z-compressed",
    "tar": "application/x-tar", "tar.gz": "application/gzip", "tgz": "application/gzip",
}


def detect_ext(filename: str) -> str:
    low = filename.lower()
    for multi in ("tar.gz", "tar.bz2", "tar.xz"):
        if low.endswith("." + multi):
            return multi
    return low.rsplit(".", 1)[-1].strip() if "." in filename else ""


_PIL_FORMAT_EXT = {
    "JPEG": "jpg", "PNG": "png", "GIF": "gif", "WEBP": "webp", "BMP": "bmp",
    "TIFF": "tiff", "ICO": "ico", "CUR": "cur", "PSD": "psd", "PCX": "pcx",
    "TGA": "tga", "PPM": "ppm", "PBM": "pbm", "PGM": "pgm", "SGI": "sgi",
    "JPEG2000": "jp2", "DDS": "dds", "XBM": "xbm", "XPM": "xpm", "MPO": "mpo",
    "DIB": "dib", "ICNS": "icns", "QOI": "qoi", "WMF": "wmf", "MPEG": "mpeg",
    "BLP": "blp", "FTEX": "ftex", "GBR": "gbr", "IPTC": "iptc", "PIXAR": "pxr",
    "SPIDER": "spo", "MCAS": "mcas", "WMV": "wmv",
}


def sniff(data: bytes, ext: str) -> str:
    """يكشف النوع الحقيقي للمحتوى، ويصلح الامتداد الخاطئ أو المفقود."""
    if ext in TARGETS:
        return ext
    if data[:4] == b"%PDF":
        return "pdf"
    if data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = z.namelist()
                if any(n == "mimetype" and z.read(n).startswith(b"application/epub") for n in names):
                    return "epub"
                if any(n.startswith("word/") for n in names):
                    return "docx"
                if any(n.startswith("ppt/") for n in names):
                    return "pptx"
                if any(n.startswith("xl/") for n in names):
                    return "xlsx"
                return "zip"
        except Exception:
            pass
    if data[:5] == b"{\\rtf" or data[:6] == b"{\\\\rtf1":
        return "rtf"
    if data[:4] == b"\xd0\xcf\x11\xe0":
        try:
            import xlrd
            xlrd.open_workbook(file_contents=data[:2_000_000] if len(data) > 2_000_000 else data)
            return "xls"
        except Exception:
            return ext or "ole"
    if data[:3] in (b"7z\xbc", b"\x52\x61\x72") or data[:8] == b"\x82\x1f\x27\x02\x01\x00\x00\x00":
        return "7z" if data[:3] == b"7z\xbc" else ext
    if b"<?xml" in data[:200]:
        return "xml"
    try:
        fmt = Image.open(io.BytesIO(data)).format
        if fmt:
            return _PIL_FORMAT_EXT.get(fmt.upper(), ext)
    except Exception:
        pass
    try:
        sample = data[:4096]
        text = sample.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = sample.decode("cp1256")
        except UnicodeDecodeError:
            return ext
    ctrl = sum(1 for ch in text if ord(ch) < 9 or 13 < ord(ch) < 32)
    if text and ctrl / len(text) < 0.02:
        return "txt"
    return ext


def _norm_image(data: bytes, dst: str) -> bytes:
    img = Image.open(io.BytesIO(data))
    fmt = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP",
           "bmp": "BMP", "tiff": "TIFF", "gif": "GIF", "ico": "ICO",
           "heic": "HEIF", "heif": "HEIF", "avif": "AVIF", "ppm": "PPM",
           "tga": "TGA", "pcx": "PCX", "jp2": "JPEG2000", "j2k": "JPEG2000",
           "dds": "DDS", "sgi": "SGI", "im": "IM", "xbm": "XBM", "eps": "EPS"}[dst]
    if dst in ("jpg", "jpeg") and img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    if dst == "xbm":
        img = img.convert("1")
    if dst == "ico":
        img = img.resize((min(img.width, 256), min(img.height, 256)))
    buf = io.BytesIO()
    try:
        img.save(buf, fmt)
    except ValueError as e:
        raise ValueError(f"لا يمكن الحفظ بصيغة {dst.upper()} ({e})")
    return buf.getvalue()


def _open_pdf(data: bytes) -> pymupdf.Document:
    doc = pymupdf.open(stream=data, filetype="pdf")
    if doc.needs_pass:
        raise ValueError("الملف محمي بكلمة مرور")
    return doc


def _story_pdf(html: str, landscape: bool = False) -> bytes:
    from .pdfrender import render_html_to_pdf
    return render_html_to_pdf(html, landscape)


def _pdf_to_images(doc: pymupdf.Document, dst: str, dpi: int = 150):
    pages = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        buf = io.BytesIO()
        img.save(buf, "JPEG" if dst in ("jpg", "jpeg") else "PNG")
        pages.append(buf.getvalue())
    return pages


def pdf_to(data: bytes, dst: str, stem: str):
    doc = _open_pdf(data)
    if dst in IMAGE_EXTS:
        pages = _pdf_to_images(doc, dst if dst in ("jpg", "jpeg", "png") else "png")
        doc.close()
        files = [(f"{stem}-{i + 1}.{dst}", b) for i, b in enumerate(pages)]
        return ("zip", files) if len(files) > 1 else ("file", files[0][1], dst)
    if dst in ("txt", "md"):
        text = "\n\n".join(p.get_text() for p in doc).strip()
        doc.close()
        return ("file", text.encode("utf-8"), dst)
    if dst == "html":
        body = "".join(p.get_text("xhtml") for p in doc)
        doc.close()
        html = f'<div dir="auto">{body}</div>'
        return ("file", html.encode("utf-8"), dst)
    if dst == "docx":
        if Converter is None:
            paras = [p.get_text() for p in doc if p.get_text().strip()]
            doc.close()
            return ("file", _text_to_docx("\n\n".join(paras)), "docx")
        import tempfile, os
        tmp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp_docx = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        tmp_pdf.write(data); tmp_pdf.close(); tmp_docx.close()
        try:
            c = Converter(tmp_pdf.name)
            c.convert(tmp_docx.name)
            c.close()
            with open(tmp_docx.name, "rb") as f:
                return ("file", f.read(), "docx")
        finally:
            import gc
            gc.collect()
            for p in (tmp_pdf.name, tmp_docx.name):
                try:
                    os.unlink(p)
                except OSError:
                    pass
    if dst == "pptx":
        from .pptxgen import build_pptx
        secs = []
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=96)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            b = io.BytesIO(); img.save(b, "PNG")
            lines = [l for l in page.get_text().splitlines() if l.strip()]
            secs.append({"title": lines[0][:80] if lines else f"صفحة {i + 1}",
                         "bullets": lines[1:11], "images": [b.getvalue()]})
        doc.close()
        return ("file", build_pptx(secs), "pptx")
    doc.close()
    raise ValueError(f"هدف غير مدعوم لـ PDF: {dst}")


def _strip_inline(html: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", html)).strip()


def _text_to_docx(text: str) -> bytes:
    import docx
    d = docx.Document()
    for para in text.split("\n"):
        d.add_heading(para, 1) if re.match(r"^#{1,3}\s", para) else d.add_paragraph(
            para.lstrip("#- "))
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def docx_to(data: bytes, dst: str, stem: str):
    import docx
    d = docx.Document(io.BytesIO(data))
    parts = []
    for p in d.paragraphs:
        if not p.text.strip():
            continue
        style = (p.style.name or "").lower()
        prefix = ""
        if style.startswith(("heading", "title", "عنوان")):
            lvl = re.search(r"(\d)", style)
            prefix = "#" * int(lvl.group(1) if lvl else 1) + " "
        parts.append(prefix + p.text)
    for t in d.tables:
        rows = [["c.text" if False else (cell.text or "").strip() for cell in r.cells] for r in t.rows]
        parts.append(rows_to_md(rows))
    text = "\n\n".join(parts)
    if dst in ("txt", "md"):
        return ("file", text.encode("utf-8"), dst)
    html = "<div dir=auto>" + "".join(f"<p>{escape(p)}</p>" for p in text.split("\n\n")) + "</div>"
    if dst == "html":
        return ("file", html.encode("utf-8"), dst)
    if dst == "pdf":
        return ("file", _story_pdf(html), "pdf")
    if dst == "pptx":
        from .pptxgen import build_pptx, sections_from_text
        return ("file", build_pptx(sections_from_text(text)), "pptx")
    if dst in IMAGE_EXTS:
        return pdf_to(_story_pdf(html), dst, stem)
    raise ValueError(f"هدف غير مدعوم لـ Word: {dst}")


def images_to_pdf(images: list) -> bytes:
    doc = pymupdf.open()
    for data in images:
        try:
            norm = _norm_image(data, "png") if Image.open(io.BytesIO(data)).format not in ("PNG", "JPEG") else data
        except Exception:
            norm = data
        p = pymupdf.open(stream=norm, filetype="png")
        pg = p[0]
        rect = pg.rect
        out = doc.new_page(width=rect.width, height=rect.height)
        out.insert_image(rect, stream=norm)
        p.close()
    data = doc.tobytes()
    doc.close()
    return data


def _read_xlsx(data: bytes):
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    ws = wb.active
    rows = [[("" if c is None else str(c)) for c in r] for r in ws.iter_rows(values_only=True)]
    wb.close()
    return rows


def _read_csv(data: bytes):
    for enc in ("utf-8-sig", "cp1256", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    sample = text[:2000]
    delim = max([",", ";", "\t", "|"], key=lambda d: sample.count(d))
    return [list(r) for r in csvmod.reader(io.StringIO(text), delimiter=delim)]


def rows_to_md(rows):
    rows = [r for r in rows if any(c for c in r)]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(c.replace("|", "\\|") for c in rows[0]) + " |",
           "|" + "---|" * width]
    out += ["| " + " | ".join(c.replace("|", "\\|") for c in r) + " |" for r in rows[1:]]
    return "\n".join(out)


def rows_to_html(rows):
    body = "".join("<tr>" + "".join(f"<t{'h' if i == 0 else 'd'}>{escape(str(c))}</t{'h' if i == 0 else 'd'}>"
                                    for c in r) + "</tr>" for i, r in enumerate(rows))
    return f'<table dir="rtl">{body}</table>'


def _read_xls(data: bytes):
    import xlrd
    wb = xlrd.open_workbook(file_contents=data)
    ws = wb.sheet_by_index(0)
    return [[str(ws.cell_value(r, c)) for c in range(ws.ncols)] for r in range(ws.nrows)]


def table_to(data: bytes, src: str, dst: str, stem: str):
    if src == "xlsx":
        rows = _read_xlsx(data)
    elif src == "xls":
        rows = _read_xls(data)
    else:
        rows = _read_csv(data)
    if dst == "csv":
        buf = io.StringIO()
        csvmod.writer(buf).writerows(rows)
        return ("file", buf.getvalue().encode("utf-8-sig"), "csv")
    if dst == "tsv":
        buf = io.StringIO()
        csvmod.writer(buf, delimiter="\t").writerows(rows)
        return ("file", buf.getvalue().encode("utf-8-sig"), "tsv")
    if dst == "xlsx":
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active
        for r in rows:
            ws.append(r)
        buf = io.BytesIO(); wb.save(buf)
        return ("file", buf.getvalue(), "xlsx")
    if dst == "xls":
        import xlwt
        wb = xlwt.Workbook(encoding="utf-8")
        ws = wb.add_sheet("Sheet1")
        for i, r in enumerate(rows):
            for j, c in enumerate(r):
                ws.write(i, j, c)
        buf = io.BytesIO(); wb.save(buf)
        return ("file", buf.getvalue(), "xls")
    if dst == "txt":
        return ("file", rows_to_md(rows).encode("utf-8"), "txt")
    if dst == "md":
        return ("file", rows_to_md(rows).encode("utf-8"), "md")
    html = rows_to_html(rows)
    if dst == "html":
        return ("file", html.encode("utf-8"), "html")
    if dst == "pdf":
        return ("file", _story_pdf(html, landscape=True), "pdf")
    if dst in IMAGE_EXTS:
        return pdf_to(_story_pdf(html, landscape=True), dst, stem)
    raise ValueError(f"هدف غير مدعوم: {dst}")


def _odt_text(data: bytes) -> str:
    import zipfile
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("content.xml").decode("utf-8", "replace")
    xml = re.sub(r"<text:line-break[^>]*/>", "\n", xml)
    xml = re.sub(r"</text:(p|h)>", "\n\n", xml)
    return unescape(re.sub(r"<[^>]+>", "", xml)).strip()


def _source_to_text(data: bytes, src: str) -> str:
    text = data.decode("utf-8", errors="replace")
    if src == "rtf":
        from striprtf.striprtf import rtf_to_text
        return rtf_to_text(text)
    if src == "odt":
        return _odt_text(data)
    if src == "json":
        import json as _json
        try:
            return _json.dumps(_json.loads(text), indent=2, ensure_ascii=False)
        except Exception:
            return text
    if src == "xml":
        from xml.dom import minidom
        try:
            return minidom.parseString(data).toprettyxml(indent="  ")
        except Exception:
            return text
    return text


def text_to(data: bytes, src: str, dst: str, stem: str):
    text = _source_to_text(data, src)
    if src == "html":
        html = text
    elif src == "md" and _md:
        html = _md.markdown(text, extensions=["tables"])
    elif src == "md":
        html = "<div dir=auto>" + "".join(
            f"<h{int(m.group(1))}>{escape(m.group(2))}</h{int(m.group(1))}>" if (m := re.match(r"^(#{1,3}) (.+)", l))
            else f"<p>{escape(l)}</p>"
            for l in text.splitlines() if l.strip()) + "</div>"
    else:
        html = "<div dir=auto>" + "".join(f"<p>{escape(l)}</p>" for l in text.splitlines()) + "</div>"
    if dst == "html":
        return ("file", html.encode("utf-8"), dst)
    if dst == "pdf":
        return ("file", _story_pdf(html), "pdf")
    if dst == "pptx":
        from .pptxgen import build_pptx, sections_from_text
        if src == "html":
            plain = unescape(re.sub(r"</(p|h\d|li|div|tr)>", "\n", html))
            plain = re.sub(r"^#+\s", "", plain)
            text = plain
        return ("file", build_pptx(sections_from_text(text)), "pptx")
    if dst == "docx":
        plain = _strip_inline(re.sub(r"</(p|h\d|li|div|tr)>", "\n", html))
        return ("file", _text_to_docx(plain), "docx")
    if dst in ("txt", "md"):
        plain = unescape(re.sub(r"<[^>]+>", "\n", html))
        plain = re.sub(r"\n{3,}", "\n\n", plain).strip()
        return ("file", plain.encode("utf-8"), dst)
    if dst in IMAGE_EXTS:
        return pdf_to(_story_pdf(html), dst, stem)
    raise ValueError(f"هدف غير مدعوم: {dst}")


def svg_to(data: bytes, dst: str, stem: str):
    doc = pymupdf.open(stream=data, filetype="svg")
    if not doc.page_count:
        doc.close()
        raise ValueError("ملف SVG غير صالح")
    if dst == "pdf":
        pdf = doc.convert_to_pdf()
        doc.close()
        return ("file", pdf, "pdf")
    if dst in IMAGE_EXTS:
        pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        b = io.BytesIO(); img.save(b, "PNG")
        doc.close()
        return ("file", _norm_image(b.getvalue(), dst), dst)
    doc.close()
    raise ValueError(f"SVG يتحول لصور أو PDF فقط، وليس {dst}")


def pptx_to(data: bytes, dst: str, stem: str):
    from pptx import Presentation
    import base64 as b64m
    prs = Presentation(io.BytesIO(data))
    secs = []
    for slide in prs.slides:
        title, bullets, images = "", [], []
        for sh in slide.shapes:
            if sh.shape_type == 13:
                try:
                    images.append(sh.image.blob)
                except Exception:
                    pass
            elif sh.has_text_frame:
                for para in sh.text_frame.paragraphs:
                    t = "".join(r.text for r in para.runs).strip()
                    if not t:
                        continue
                    if not title:
                        title = t
                    else:
                        bullets.append(t)
        secs.append({"title": title, "bullets": bullets, "images": images})
    if dst in ("txt", "md"):
        out = []
        for s in secs:
            out.append(("# " if dst == "md" else "") + s["title"])
            out += [("- " if dst == "md" else "") + b for b in s["bullets"]]
            out.append("")
        return ("file", "\n".join(out).encode("utf-8"), dst)
    parts = []
    for i, s in enumerate(secs):
        if i:
            parts.append('<div style="pagebreak"></div>')
        if s["title"]:
            parts.append(f"<h2>{escape(s['title'])}</h2>")
        parts += [f"<p>{escape(b)}</p>" for b in s["bullets"]]
        for im in s["images"]:
            try:
                png = _norm_image(im, "png")
                parts.append(f'<div><img src="data:image/png;base64,{b64m.b64encode(png).decode()}"></div>')
            except Exception:
                pass
    html = "<div dir=auto>" + "".join(parts) + "</div>"
    if dst == "html":
        return ("file", html.encode("utf-8"), "html")
    if dst == "pdf":
        return ("file", _story_pdf(html), "pdf")
    if dst == "docx":
        plain = "\n".join(f"{s['title']}\n" + "\n".join(s["bullets"]) for s in secs)
        return ("file", _text_to_docx(plain), "docx")
    if dst in IMAGE_EXTS:
        return pdf_to(_story_pdf(html), dst, stem)
    raise ValueError(f"هدف غير مدعوم لـ PowerPoint: {dst}")


def paged_to(data: bytes, kind: str, dst: str, stem: str):
    """مصادر يفتحها MuPDF (epub/fb2/xps/cbz) → PDF/نص/صور."""
    doc = pymupdf.open(stream=data, filetype=kind)
    if doc.page_count == 0:
        doc.close()
        raise ValueError("الملف لا يحتوي على صفحات")
    if dst == "pdf":
        out = pymupdf.open()
        for p in doc:
            pix = p.get_pixmap(dpi=120)
            pg = out.new_page(width=p.rect.width, height=p.rect.height)
            pg.insert_image(pg.rect, stream=pix.tobytes("png"))
        b = out.tobytes(); out.close(); doc.close()
        return ("file", b, "pdf")
    if dst in ("txt", "md"):
        text = "\n\n".join(p.get_text() for p in doc).strip()
        doc.close()
        return ("file", text.encode("utf-8"), dst)
    if dst == "html":
        html = "".join(p.get_text("xhtml") for p in doc)
        doc.close()
        return ("file", html.encode("utf-8"), "html")
    if dst in IMAGE_EXTS:
        conv = [_norm_image(p.get_pixmap(dpi=150).tobytes("png"), dst) for p in doc]
        doc.close()
        files = [(f"{stem}-{i + 1}.{dst}", b) for i, b in enumerate(conv)]
        return ("zip", files) if len(files) > 1 else ("file", files[0][1], dst)
    doc.close()
    raise ValueError(f"هدف غير مدعوم لـ {kind.upper()}: {dst}")


def _data_convert(data: bytes, src: str, dst: str):
    """تحويل بين صيغ البيانات: json / yaml / toml / csv"""
    import json as _json
    text = data.decode("utf-8", errors="replace")
    obj = None
    if src in ("json",):
        obj = _json.loads(text)
    elif src in ("yaml", "yml"):
        import yaml
        obj = yaml.safe_load(text)
    elif src == "toml":
        import tomllib
        obj = tomllib.loads(text)
    if obj is None:
        raise ValueError("تعذّر قراءة الملف كبيانات منظمة")
    if dst == "json":
        return ("file", _json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8"), "json")
    if dst in ("yaml", "yml"):
        import yaml
        return ("file", yaml.safe_dump(obj, allow_unicode=True, sort_keys=False).encode("utf-8"), "yaml")
    if dst == "csv" and isinstance(obj, list) and obj and isinstance(obj[0], dict):
        buf = io.StringIO()
        w = csvmod.DictWriter(buf, fieldnames=list(obj[0].keys()))
        w.writeheader(); w.writerows(obj)
        return ("file", buf.getvalue().encode("utf-8-sig"), "csv")
    raise ValueError("تحول البيانات غير ممكن بين هاتين الصيغتين")


def _subtitle_convert(data: bytes, src: str, dst: str):
    text = data.decode("utf-8", errors="replace")
    if dst == "vtt":
        body = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", text)
        return ("file", f"WEBVTT\n\n{body}".encode("utf-8"), "vtt")
    body = re.sub(r"(\d{2}:\d{2}:\d{2})\.(\d{3})", r"\1,\2", text)
    body = re.sub(r"STYLE[^{]*\{[^}]*\}", "", body)
    body = body.replace("WEBVTT\n", "", 1)
    return ("file", body.strip().encode("utf-8"), "srt")


TEXT_ALIASES = {"docm": "docx", "dot": "docx", "dotx": "docx", "htm": "html",
                "xhtml": "html", "yml": "yaml", "tgz": "tar.gz", "j2k": "jp2",
                "jpeg": "jpg"}


def convert_one(data: bytes, src: str, dst: str, stem: str):
    """يرجع ('file', bytes, ext) أو ('zip', [(name, bytes), ...])"""
    src, dst = TEXT_ALIASES.get(src, src), TEXT_ALIASES.get(dst, dst)
    if src == dst:
        return ("file", data, dst)
    if dst == "vtt" and src == "srt" or dst == "srt" and src == "vtt":
        return _subtitle_convert(data, src, dst)
    if src in ("json", "yaml", "toml") and dst in ("json", "yaml", "csv"):
        return _data_convert(data, src, dst)
    if src == "odt":
        return text_to(data, "odt", dst, stem)
    if src == "pdf":
        return pdf_to(data, dst, stem)
    if src == "docx":
        return docx_to(data, dst, stem)
    if src in PAGED_EXTS:
        return paged_to(data, src, dst, stem)
    if src == "pptx":
        return pptx_to(data, dst, stem)
    if src == "svg":
        return svg_to(data, dst, stem)
    if src in IMAGE_EXTS:
        if src == "eps":
            raise ValueError("قراءة EPS تحتاج Ghostscript غير المتوفر — استخدم EPS كصيغة حفظ فقط")
        if dst == "pdf":
            return ("file", images_to_pdf([data]), "pdf")
        if dst in IMAGE_EXTS:
            return ("file", _norm_image(data, dst), dst)
        if dst == "pptx":
            from .pptxgen import build_pptx
            return ("file", build_pptx([{"title": stem, "bullets": [], "images": [data]}]), "pptx")
        raise ValueError("الصورة تتحول لصور أو PDF أو PowerPoint")
    if src in TABLE_EXTS:
        return table_to(data, src, dst, stem)
    if src in TEXT_LIKE:
        return text_to(data, src, dst, stem)
    raise ValueError(f"صيغة المصدر غير مدعومة: {src}")


def convert_many(files: list, dst: str):
    """files: [(stem, src, bytes)] — دمج الصور لـ PDF أو إرجاع ملف/zip"""
    if len(files) > 1 and all(s == "pdf" for _, s, _ in files) and dst == "pdf":
        out = pymupdf.open()
        for _, _, data in files:
            out.insert_pdf(_open_pdf(data))
        data = out.tobytes(); out.close()
        return ("file", data, "pdf")
    if len(files) > 1 and all(s in IMAGE_EXTS for _, s, _ in files) and dst == "pdf":
        return ("file", images_to_pdf([d for _, _, d in files]), "pdf")
    if len(files) > 1 and all(s in IMAGE_EXTS for _, s, _ in files) and dst == "pptx":
        from .pptxgen import build_pptx
        return ("file", build_pptx([{"title": stem, "bullets": [], "images": [d]}
                                    for stem, _, d in files]), "pptx")
    results = [convert_one(d, s, dst, stem) for stem, s, d in files]
    if len(results) == 1:
        return results[0]
    all_files = []
    for r in results:
        if r[0] == "file":
            stem = "out"
            all_files.append((f"{stem}.{r[2]}", r[1]))
        else:
            all_files.extend(r[1])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, (name, data) in enumerate(all_files):
            z.writestr(f"{i + 1}-{name}", data)
    return ("zip", [( "converted.zip", buf.getvalue())])
