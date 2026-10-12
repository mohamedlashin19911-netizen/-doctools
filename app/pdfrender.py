"""توليد PDF من HTML بسيط — fpdf2 + تشكيل عربي (muPDF Story معطل على هذه البيئة)."""
import io
import re
import base64
from html import unescape

import arabic_reshaper
import bidi
from fpdf import FPDF
from fpdf.enums import XPos, YPos

_FONT_CANDIDATES = [
    (r"C:/Windows/Fonts/tahoma.ttf", r"C:/Windows/Fonts/tahomabd.ttf"),
    (r"C:/Windows/Fonts/arial.ttf", r"C:/Windows/Fonts/arialbd.ttf"),
]
RTL_RE = re.compile(r"[\u0600-\u08ff\ufb50-\ufeff]")


def _is_rtl(text: str) -> bool:
    return bool(RTL_RE.search(text))


def _prep(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text).strip()
    text = unescape(text)
    if _is_rtl(text):
        text = bidi.get_display(arabic_reshaper.reshape(text))
    return text


def _tag_fontsize(tag: str) -> float:
    return {"h1": 21, "h2": 17, "h3": 14, "h4": 12.5, "h5": 11.5, "h6": 11,
            "p": 11.5, "li": 11.5, "td": 10.5, "th": 11}.get(tag, 11.5)


_BLOCK_RE = re.compile(
    r"<(h[1-6]|p|div|li|blockquote)([^>]*)>(.*?)</\1>",
    re.IGNORECASE | re.DOTALL)
_IMG_RE = re.compile(r"<img[^>]+src=[\"'](?:data:image/[^;]+;)?base64,([A-Za-z0-9+/=]+)[\"'][^>]*>",
                     re.IGNORECASE)
_TABLE_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.IGNORECASE | re.DOTALL)
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
_CELL_RE = re.compile(r"<t([hd])[^>]*>(.*?)</t\1>", re.IGNORECASE | re.DOTALL)


def _align(style: str, rtl: bool):
    s = (style or "").lower()
    if "center" in s:
        return "C"
    if "left" in s:
        return "L"
    if "right" in s:
        return "R"
    return "R" if rtl else "L"


def _add_image(pdf: FPDF, b64: str):
    try:
        raw = base64.b64decode(b64)
        from PIL import Image
        img = Image.open(io.BytesIO(raw))
        max_w = pdf.epw
        scale = min(max_w / img.width, 120 / img.height) if img.width else 1
        w = max(20, img.width * scale)
        x = pdf.l_margin + (pdf.epw - w) / 2
        pdf.image(io.BytesIO(raw), x=x, w=w)
        pdf.ln(4)
    except Exception:
        pass


def _render_table(pdf: FPDF, table_html: str):
    rows = _ROW_RE.findall(table_html)
    if not rows:
        return
    cols = max(len(_CELL_RE.findall(r)) for r in rows)
    col_w = pdf.epw / max(cols, 1)
    for i, row in enumerate(rows):
        cells = _CELL_RE.findall(row)
        texts = [_prep(c) for _, c in cells] + [""] * (cols - len(cells))
        heights = []
        for t in texts:
            pdf.set_font("main", "B" if i == 0 else "", _tag_fontsize("th" if i == 0 else "td"))
            h = pdf.multi_cell(col_w - 2, 5, t or " ", dry_run=True, output="HEIGHT")
            heights.append(h)
        row_h = max(heights)
        if pdf.get_y() + row_h > pdf.page_break_trigger:
            pdf.add_page()
        y0 = pdf.get_y()
        x0 = pdf.l_margin
        for j, t in enumerate(texts):
            is_head = i == 0
            pdf.set_font("main", "B" if is_head else "", _tag_fontsize("th" if is_head else "td"))
            pdf.set_xy(x0 + j * col_w, y0)
            rtl = bool(t and RTL_RE.search(t))
            pdf.multi_cell(col_w, 5, t or " ", border=1, max_line_height=5,
                           align="R" if rtl else "L",
                           new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_xy(x0, y0 + row_h)
    pdf.ln(3)


def render_html_to_pdf(html: str, landscape: bool = False, title: str = "") -> bytes:
    fmt = "landscape" if landscape else "portrait"
    pdf = FPDF(format="A4", orientation=fmt)
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    reg, bold = next((a, b) for a, b in _FONT_CANDIDATES if __import__("os").path.exists(a))
    pdf.add_font("main", "", reg)
    pdf.add_font("main", "B", bold)
    if title:
        pdf.set_font("main", "B", 24)
        t = _prep(title)
        pdf.cell(pdf.epw, 14, t, new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                 align="R" if _is_rtl(title) else "L")
        pdf.ln(2)

    # الجداول تُستخرج أولاً ثم تُدمج في موضعها عبر تقطيع النص
    pos = 0
    for m_tbl in _TABLE_RE.finditer(html):
        pos = _render_flow(pdf, html[pos:m_tbl.start()])
        _render_table(pdf, m_tbl.group(1))
    _render_flow(pdf, html[pos:])

    return bytes(pdf.output())


def _render_flow(pdf: FPDF, chunk: str) -> int:
    last = 0
    for m in _IMG_RE.finditer(chunk):
        _add_image(pdf, m.group(1))
    rest = _IMG_RE.sub("", chunk)
    blocks = list(_BLOCK_RE.finditer(rest))
    for m in blocks:
        tag, attrs, inner = m.group(1).lower(), m.group(2), m.group(3)
        if "pagebreak" in (attrs or "").lower():
            pdf.add_page()
            continue
        text = re.sub(r"<[^>]+>", "", inner).strip()
        if not text:
            continue
        text = unescape(text)
        rtl = _is_rtl(text)
        if rtl:
            text = bidi.get_display(arabic_reshaper.reshape(text))
        style = ""
        sm = re.search(r'style=["\']([^"\']*)', attrs, re.IGNORECASE)
        if sm:
            style = sm.group(1)
        size = _tag_fontsize(tag)
        pdf.set_font("main", "B" if tag in ("h1", "h2", "h3", "th") else "", size)
        if tag == "li":
            text = ("• " + text) if not rtl else (text + " •")
        x = XPos.LMARGIN
        pdf.multi_cell(pdf.epw, size * 0.55, text,
                       align=_align(style, rtl), new_x=x, new_y=YPos.NEXT)
        pdf.ln(1.5)
    return last
