"""services/pdf_engine.py — SATU mesin cetak PDF berkop untuk semua dokumen bisnis
(invoice DP/pelunasan, kwitansi, konfirmasi pemesanan, SPJ) + pratinjau konfigurasi.

Kop/footer/watermark digambar tiap halaman dari `layout.brand`; tabel mengikuti `layout.table`;
kolom tanda tangan dari `layout.signatures`. Pratinjau memakai fungsi yang sama → tidak bohong.
"""
import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, LETTER, legal
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PAPER = {"A4": A4, "LETTER": LETTER, "LEGAL": legal}


def _hex(value, fallback="#0F6E56"):
    try:
        return colors.HexColor(value or fallback)
    except (ValueError, AttributeError):
        return colors.HexColor(fallback)


def rp(v) -> str:
    if v is None:
        return "-"
    return f"Rp {int(round(float(v))):,}".replace(",", ".")


def _esc(v) -> str:
    return str(v if v is not None else "-").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _reader(data):
    try:
        return ImageReader(io.BytesIO(data))
    except Exception:  # noqa: BLE001
        return None


class _Frame:
    def __init__(self, layout, logo):
        self.b = layout.get("brand") or {}
        self.logo = logo

    def __call__(self, canvas, doc):
        canvas.saveState()
        self._watermark(canvas, doc)
        self._header(canvas, doc)
        self._footer(canvas, doc)
        canvas.restoreState()

    def _header(self, canvas, doc):
        if (self.b.get("header_mode") or "system") == "none":
            return
        w, h = doc.pagesize
        left = float(self.b.get("margin_left_mm") or 18) * mm
        right = w - float(self.b.get("margin_right_mm") or 18) * mm
        top = h - 12 * mm
        x = left
        if self.logo:
            img = _reader(self.logo)
            if img:
                iw, ih = img.getSize()
                lh = 16 * mm
                lw = min(42 * mm, (lh * iw) / max(ih, 1))
                canvas.drawImage(img, left, top - lh + 2 * mm, width=lw, height=lh, preserveAspectRatio=True, anchor="sw", mask="auto")
                x = left + lw + 5 * mm
        canvas.setFillColor(_hex(self.b.get("text_color"), "#1C1C1E"))
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(x, top - 3 * mm, str(self.b.get("company_name") or "")[:60])
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6B6B73"))
        lines = [self.b.get("tagline"), self.b.get("address"),
                 " · ".join(t for t in [self.b.get("phone"), self.b.get("email"), self.b.get("website")] if t),
                 f"NPWP {self.b.get('npwp')}" if self.b.get("npwp") else None]
        y = top - 8 * mm
        for line in [ln for ln in lines if ln]:
            canvas.drawString(x, y, str(line)[:120])
            y -= 3.6 * mm
        canvas.setStrokeColor(_hex(self.b.get("accent_color")))
        canvas.setLineWidth(1.6)
        gy = min(y + 1.5 * mm, top - 9 * mm)
        canvas.line(left, gy, right, gy)

    def _footer(self, canvas, doc):
        if (self.b.get("footer_mode") or "system") == "none":
            return
        w, _ = doc.pagesize
        left = float(self.b.get("margin_left_mm") or 18) * mm
        right = w - float(self.b.get("margin_right_mm") or 18) * mm
        canvas.setStrokeColor(colors.HexColor("#E2E3E7"))
        canvas.setLineWidth(0.6)
        canvas.line(left, 15 * mm, right, 15 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#6B6B73"))
        teks = self.b.get("footer_text") or " · ".join(
            t for t in [self.b.get("company_name"), self.b.get("address"), self.b.get("phone"), self.b.get("website")] if t)
        canvas.drawString(left, 11 * mm, str(teks)[:150])
        if self.b.get("show_page_numbers", True):
            canvas.drawRightString(right, 11 * mm, f"Halaman {canvas.getPageNumber()}")

    def _watermark(self, canvas, doc):
        teks = (self.b.get("watermark_text") or "").strip()
        if not teks:
            return
        w, h = doc.pagesize
        alpha = max(0, min(int(self.b.get("watermark_opacity") or 8), 60)) / 100.0
        canvas.saveState()
        canvas.setFillAlpha(alpha)
        canvas.setFillColor(_hex(self.b.get("accent_color")))
        canvas.setFont("Helvetica-Bold", 64)
        canvas.translate(w / 2, h / 2)
        canvas.rotate(38)
        canvas.drawCentredString(0, 0, teks[:28])
        canvas.restoreState()


def _styles(layout):
    b = layout.get("brand") or {}
    s = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=s["Title"], fontSize=17, spaceAfter=0, alignment=TA_RIGHT, textColor=_hex(b.get("text_color"), "#1C1C1E")),
        "num": ParagraphStyle("n", parent=s["Normal"], fontSize=9.5, alignment=TA_RIGHT, textColor=colors.HexColor("#6B6B73")),
        "body": ParagraphStyle("b", parent=s["Normal"], fontSize=9.5, leading=14),
        "small": ParagraphStyle("s", parent=s["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#6B6B73")),
        "label": ParagraphStyle("l", parent=s["Normal"], fontSize=7.5, textColor=colors.HexColor("#8E8E93")),
        "val": ParagraphStyle("v", parent=s["Normal"], fontSize=10, leading=13, textColor=colors.HexColor("#1C1C1E")),
        "right": ParagraphStyle("r", parent=s["Normal"], fontSize=9.5, alignment=TA_RIGHT),
        "sec": ParagraphStyle("sec", parent=s["Normal"], fontSize=10, spaceBefore=8, spaceAfter=3, textColor=_hex(b.get("accent_color")), fontName="Helvetica-Bold"),
        "big": ParagraphStyle("big", parent=s["Normal"], fontSize=13, leading=16, fontName="Helvetica-Bold", alignment=TA_RIGHT),
        "center": ParagraphStyle("c", parent=s["Normal"], fontSize=9, alignment=TA_CENTER),
    }


def _tcfg(layout):
    t = dict((layout or {}).get("table") or {})
    return {"grid": t.get("grid") or "horizontal", "show_header": t.get("show_header", True) is not False,
            "header_fill": t.get("header_fill", True) is not False, "zebra": t.get("zebra", True) is not False,
            "total_highlight": t.get("total_highlight", True) is not False,
            "font_size": float(t.get("font_size") or 9), "grid_color": t.get("grid_color") or "#E2E3E7"}


def _table_style(cfg, accent, *, has_header, has_total):
    style = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    warna = _hex(cfg["grid_color"], "#E2E3E7")
    if cfg["grid"] == "full":
        style.append(("GRID", (0, 0), (-1, -1), 0.3, warna))
    elif cfg["grid"] == "horizontal":
        style.append(("LINEBELOW", (0, 0), (-1, -2), 0.3, warna))
    if has_header and cfg["header_fill"]:
        style += [("BACKGROUND", (0, 0), (-1, 0), accent), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
    if cfg["zebra"]:
        style.append(("ROWBACKGROUNDS", (0, 1 if has_header else 0), (-1, -1), [colors.white, colors.HexColor("#F7F8FA")]))
    if has_total and cfg["total_highlight"]:
        style.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EEF7F3")))
    return style


def _meta_grid(pairs, st, width):
    """Kotak meta 2 kolom: [(label, value), ...]."""
    rows, cells = [], []
    for i in range(0, len(pairs), 2):
        chunk = pairs[i:i + 2]
        row = []
        for lbl, val in chunk:
            row.append([Paragraph(_esc(lbl).upper(), st["label"]), Paragraph(_esc(val), st["val"])])
        while len(row) < 2:
            row.append("")
        rows.append(row)
    t = Table(rows, colWidths=[width / 2] * 2)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    return t


def _items_table(items, totals, st, accent, cfg, width):
    header_style = ParagraphStyle("hh", parent=st["body"], fontSize=cfg["font_size"], textColor=colors.white if cfg["header_fill"] else colors.black, fontName="Helvetica-Bold")
    cell = ParagraphStyle("cc", parent=st["body"], fontSize=cfg["font_size"], leading=cfg["font_size"] + 4)
    cell_r = ParagraphStyle("cr", parent=cell, alignment=TA_RIGHT)
    data = []
    if cfg["show_header"]:
        data.append([Paragraph("Deskripsi", header_style), Paragraph("Qty", ParagraphStyle("hr", parent=header_style, alignment=TA_RIGHT)),
                     Paragraph("Harga", ParagraphStyle("hr2", parent=header_style, alignment=TA_RIGHT)),
                     Paragraph("Jumlah", ParagraphStyle("hr3", parent=header_style, alignment=TA_RIGHT))])
    for it in items:
        qty = it.get("qty") or 1
        data.append([Paragraph(_esc(it.get("label")), cell), Paragraph(str(qty), cell_r),
                     Paragraph(rp(it.get("unit_price", it.get("amount"))), cell_r), Paragraph(rp(it.get("amount")), cell_r)])
    t = Table(data, colWidths=[width * 0.52, width * 0.10, width * 0.19, width * 0.19], repeatRows=1 if cfg["show_header"] else 0)
    t.setStyle(TableStyle(_table_style(cfg, accent, has_header=cfg["show_header"], has_total=False)))
    flow = [t, Spacer(1, 6)]
    trows = []
    for lbl, val, bold in totals:
        s_l = ParagraphStyle("tl", parent=st["right"], fontName="Helvetica-Bold" if bold else "Helvetica", fontSize=10 if bold else 9.5)
        trows.append(["", Paragraph(_esc(lbl), s_l), Paragraph(rp(val), s_l)])
    tt = Table(trows, colWidths=[width * 0.45, width * 0.33, width * 0.22])
    tt_style = [("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if totals:
        tt_style.append(("LINEABOVE", (1, -1), (-1, -1), 0.8, _hex((cfg or {}).get("grid_color"), "#1C1C1E")))
        if cfg["total_highlight"]:
            tt_style.append(("BACKGROUND", (1, -1), (-1, -1), colors.HexColor("#EEF7F3")))
    tt.setStyle(TableStyle(tt_style))
    flow.append(tt)
    return flow


def _bank_block(banks, st, width):
    if not banks:
        return []
    rows = [[Paragraph("<b>Pembayaran dapat ditransfer ke:</b>", st["body"])]]
    for b in banks:
        rows.append([Paragraph(f"<b>{_esc(b.get('bank'))}</b> · {_esc(b.get('account_no'))} a.n. {_esc(b.get('account_name'))}"
                               + (f" <font color='#6B6B73'>({_esc(b.get('note'))})</font>" if b.get("note") else ""), st["body"])])
    t = Table(rows, colWidths=[width])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E3E7")), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8FA")),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return [t]


def _signature_block(layout, st, sigs, width, doc_date):
    if not sigs:
        return []
    o = layout.get("options") or {}
    flow = []
    if o.get("show_place_date", True):
        tempat = (o.get("place") or "").strip()
        flow.append(Paragraph(f"{tempat + ', ' if tempat else ''}{doc_date or ''}", st["right"]))
        flow.append(Spacer(1, 4))
    cells = []
    for i, s in enumerate(sigs):
        isi = [Paragraph(f"<b>{_esc(s.get('title'))}</b>", st["center"]), Spacer(1, 18 * mm)]
        if i == 0 and o.get("show_materai"):
            isi.append(Paragraph(_esc(o.get("materai_note") or "Bermeterai cukup"), ParagraphStyle("m", parent=st["small"], alignment=TA_CENTER)))
        isi.append(Paragraph(f"<u>{_esc(s.get('name') or '(...............................)')}</u>", st["center"]))
        if s.get("position"):
            isi.append(Paragraph(_esc(s["position"]), ParagraphStyle("p", parent=st["small"], alignment=TA_CENTER)))
        cells.append(isi)
    lebar = min(60 * mm, width / max(len(sigs), 1))
    t = Table([cells], colWidths=[lebar] * len(sigs), hAlign="RIGHT" if len(sigs) == 1 else "CENTER")
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    flow.append(t)
    return flow


def render_document(layout: dict, logo, *, title: str, doc_number: str, doc_date: str, meta_pairs: list,
                    intro: str = "", items=None, totals=None, banks=None, summary_pairs=None, closing: str = "",
                    terms=None, signatures=None, status_label: str = None, big_amount=None, big_label: str = None,
                    note: str = "") -> bytes:
    """Renderer generik: judul kanan, meta grid, naskah, tabel item + total, rekening, S&K, ttd."""
    st = _styles(layout)
    b = layout.get("brand") or {}
    o = layout.get("options") or {}
    accent = _hex(b.get("accent_color"))
    cfg = _tcfg(layout)
    buf = io.BytesIO()
    pagesize = PAPER.get(b.get("paper") or "A4", A4)
    doc = SimpleDocTemplate(buf, pagesize=pagesize, topMargin=float(b.get("margin_top_mm") or 34) * mm,
                            bottomMargin=float(b.get("margin_bottom_mm") or 24) * mm,
                            leftMargin=float(b.get("margin_left_mm") or 18) * mm,
                            rightMargin=float(b.get("margin_right_mm") or 18) * mm, title=doc_number or title)
    width = pagesize[0] - doc.leftMargin - doc.rightMargin
    flow = []
    head_right = []
    if o.get("show_title", True):
        head_right.append(Paragraph(_esc(title), st["title"]))
    if doc_number and o.get("show_doc_number", True):
        head_right.append(Paragraph(f"No. <b>{_esc(doc_number)}</b>", st["num"]))
    head_right.append(Paragraph(f"Tanggal: {_esc(doc_date)}", st["num"]))
    if status_label:
        head_right.append(Paragraph(f"<font color='{b.get('accent_color') or '#0F6E56'}'><b>{_esc(status_label)}</b></font>", st["num"]))
    left = []
    if big_amount is not None:
        left = [Paragraph(_esc(big_label or "Jumlah").upper(), st["label"]),
                Paragraph(f"<font color='{b.get('accent_color') or '#0F6E56'}'>{rp(big_amount)}</font>",
                          ParagraphStyle("ba", parent=st["big"], alignment=0, fontSize=16))]
    ht = Table([[left, head_right]], colWidths=[width * 0.5, width * 0.5])
    ht.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    flow += [ht, Spacer(1, 8)]
    if meta_pairs:
        flow += [_meta_grid(meta_pairs, st, width), Spacer(1, 4)]
    for line in (intro or "").split("\n"):
        flow.append(Paragraph(_esc(line), st["body"]) if line.strip() else Spacer(1, 4))
    if items is not None:
        flow.append(Paragraph("Rincian", st["sec"]))
        flow += _items_table(items, totals or [], st, accent, cfg, width)
    if summary_pairs:
        flow.append(Paragraph("Ringkasan pembayaran", st["sec"]))
        rows = [[Paragraph(_esc(k), st["body"]), Paragraph(rp(v) if isinstance(v, (int, float)) else _esc(v), st["right"])] for k, v in summary_pairs]
        t = Table(rows, colWidths=[width * 0.6, width * 0.4])
        t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#E2E3E7")), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        flow.append(t)
    if banks:
        flow.append(Spacer(1, 8))
        flow += _bank_block(banks, st, width)
    if closing:
        flow.append(Spacer(1, 8))
        for line in closing.split("\n"):
            flow.append(Paragraph(_esc(line), st["body"]) if line.strip() else Spacer(1, 4))
    if terms:
        flow.append(Paragraph("Syarat & ketentuan", st["sec"]))
        for i, c in enumerate([x for x in terms if x.strip()], 1):
            flow.append(Paragraph(f"{i}. {_esc(c)}", st["small"]))
    if note:
        flow += [Spacer(1, 6), Paragraph(_esc(note), st["small"])]
    flow.append(Spacer(1, 14))
    flow.append(KeepTogether(_signature_block(layout, st, signatures or [], width, doc_date)))
    if o.get("show_generated_note", True):
        flow += [Spacer(1, 10), Paragraph(f"Dokumen ini diterbitkan secara elektronik oleh sistem {_esc(b.get('company_name') or '')} dan sah tanpa tanda tangan basah.", st["small"])]
    frame = _Frame(layout, logo)
    doc.build(flow, onFirstPage=frame, onLaterPages=frame)
    return buf.getvalue()
