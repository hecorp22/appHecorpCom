"""
PDF de cotización con membrete "Aleaciones y Maquinados".
Paleta: azules cálidos / turquesa / metálicos cálidos.
"""
from io import BytesIO
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)


# ---------- Paleta ----------
TURQUOISE_DEEP = colors.HexColor("#0A6E7A")
TURQUOISE      = colors.HexColor("#13A4B5")
TURQUOISE_SOFT = colors.HexColor("#B8E4E8")
BRASS          = colors.HexColor("#B98B3A")
BRASS_SOFT     = colors.HexColor("#E3C492")
CHARCOAL       = colors.HexColor("#1E2A34")
INK            = colors.HexColor("#0F1A22")
PAPER          = colors.HexColor("#FDFBF6")
MUTED          = colors.HexColor("#6B7A85")


# ---------- Logo SVG-like dibujado con canvas ----------
def _draw_logo(c: canvas.Canvas, x: float, y: float, size: float = 20):
    """Logo: engranaje estilizado + 'AyM' — aleaciones y maquinados."""
    r = size / 2
    cx, cy = x + r, y + r

    # anillo exterior (brass)
    c.setStrokeColor(BRASS)
    c.setLineWidth(1.4)
    c.circle(cx, cy, r, stroke=1, fill=0)

    # dientes del engranaje
    import math
    c.setFillColor(TURQUOISE_DEEP)
    for i in range(8):
        ang = i * (360 / 8)
        rad = math.radians(ang)
        tx = cx + (r + 2) * math.cos(rad) - 1.2
        ty = cy + (r + 2) * math.sin(rad) - 1.2
        c.rect(tx, ty, 2.4, 2.4, stroke=0, fill=1)

    # interior: círculo turquesa
    c.setFillColor(TURQUOISE)
    c.circle(cx, cy, r - 3, stroke=0, fill=1)

    # monograma AyM
    c.setFillColor(PAPER)
    c.setFont("Helvetica-Bold", size * 0.42)
    c.drawCentredString(cx, cy - size * 0.14, "AyM")


# ---------- Marca de agua (para borradores / rechazadas) ----------
def _draw_watermark(c: canvas.Canvas, text: str, color=None):
    w, h = letter
    c.saveState()
    c.translate(w / 2, h / 2)
    c.rotate(30)
    c.setFont("Helvetica-Bold", 110)
    col = color or colors.Color(0.72, 0.55, 0.23, alpha=0.12)  # brass muy tenue
    c.setFillColor(col)
    c.drawCentredString(0, 0, text)
    c.restoreState()


# ---------- Header / footer en cada página ----------
def _header_footer(canvas_obj, doc, company_info, status: str | None = None):
    c = canvas_obj
    c.saveState()

    w, h = letter

    # Marca de agua según estatus (antes del contenido, para quedar detrás)
    status_l = (status or "").lower()
    if status_l == "borrador":
        _draw_watermark(c, "BORRADOR")
    elif status_l == "rechazada":
        _draw_watermark(c, "RECHAZADA", colors.Color(0.85, 0.25, 0.25, alpha=0.10))
    # Barra superior turquesa con degradado faux (dos rectángulos apilados)
    c.setFillColor(TURQUOISE_DEEP)
    c.rect(0, h - 28 * mm, w, 28 * mm, stroke=0, fill=1)
    c.setFillColor(TURQUOISE)
    c.rect(0, h - 18 * mm, w, 6 * mm, stroke=0, fill=1)

    # Banda metálica (brass)
    c.setFillColor(BRASS)
    c.rect(0, h - 30 * mm, w, 2 * mm, stroke=0, fill=1)

    # Logo
    _draw_logo(c, 18 * mm, h - 22 * mm, size=14 * mm)

    # Nombre empresa
    c.setFillColor(PAPER)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40 * mm, h - 14 * mm, "ALEACIONES Y MAQUINADOS")
    c.setFont("Helvetica", 8.5)
    c.setFillColor(TURQUOISE_SOFT)
    c.drawString(40 * mm, h - 19 * mm, "Bujes · Hules · Portachumaceras · Flechas · Maquinados de precisión")

    # Info en esquina superior derecha
    c.setFillColor(PAPER)
    c.setFont("Helvetica", 8)
    right_x = w - 18 * mm
    lines = [
        company_info.get("tagline", "Ingeniería en aleaciones"),
        company_info.get("phone",   "Tel: +52 272 000 0000"),
        company_info.get("email",   "ventas@aleacionesymaquinados.mx"),
    ]
    for i, ln in enumerate(lines):
        c.drawRightString(right_x, h - 11 * mm - (i * 4 * mm), ln)

    # Footer
    c.setStrokeColor(BRASS_SOFT)
    c.setLineWidth(0.6)
    c.line(18 * mm, 18 * mm, w - 18 * mm, 18 * mm)

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.5)
    footer_domain = company_info.get("domain", "aleacionesymaquinados.mx")
    c.drawString(18 * mm, 12 * mm, f"Aleaciones y Maquinados · Orizaba, Ver. · {footer_domain}")
    c.drawRightString(w - 18 * mm, 12 * mm, f"Página {doc.page}")

    c.restoreState()


# ---------- Estilos de texto ----------
def _styles():
    ss = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=ss["Heading1"],
                             textColor=TURQUOISE_DEEP, fontName="Helvetica-Bold",
                             fontSize=18, spaceAfter=2),
        "sub": ParagraphStyle("sub", parent=ss["BodyText"],
                              textColor=BRASS, fontName="Helvetica-Bold",
                              fontSize=9, spaceAfter=6),
        "label": ParagraphStyle("label", parent=ss["BodyText"],
                                textColor=MUTED, fontSize=7.5,
                                fontName="Helvetica-Bold"),
        "value": ParagraphStyle("value", parent=ss["BodyText"],
                                textColor=INK, fontSize=10,
                                fontName="Helvetica"),
        "p": ParagraphStyle("p", parent=ss["BodyText"],
                            textColor=INK, fontSize=9.5, leading=13),
        "notes": ParagraphStyle("notes", parent=ss["BodyText"],
                                textColor=MUTED, fontSize=8.5, leading=12),
    }


def _fmt_money(x, currency="MXN"):
    q = Decimal(x or 0).quantize(Decimal("0.01"))
    return f"${q:,.2f} {currency}"


# ---------- Render principal ----------
def build_quotation_pdf(q, company_info: dict | None = None) -> bytes:
    company_info = company_info or {}

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=40 * mm, bottomMargin=22 * mm,
        title=f"Cotización {q.quote_code}",
        author="Aleaciones y Maquinados",
    )
    s = _styles()
    story = []

    # --- Encabezado cotización ---
    story.append(Paragraph(f"COTIZACIÓN {q.quote_code}", s["h1"]))
    story.append(Paragraph(
        f"Emitida: {q.created_at.strftime('%d/%m/%Y')}"
        + (f" · Vigencia hasta: {q.valid_until.strftime('%d/%m/%Y')}" if q.valid_until else ""),
        s["sub"]
    ))
    story.append(Spacer(1, 4 * mm))

    # --- Datos del cliente ---
    info_rows = [
        [Paragraph("EMPRESA",    s["label"]), Paragraph(q.company or "—",      s["value"]),
         Paragraph("ENCARGADO", s["label"]),  Paragraph(q.contact_name or "—", s["value"])],
        [Paragraph("CORREO",     s["label"]), Paragraph(q.email or "—",        s["value"]),
         Paragraph("TELÉFONO",  s["label"]),  Paragraph(q.phone or "—",        s["value"])],
        [Paragraph("ASUNTO",     s["label"]), Paragraph(q.subject or "—",      s["value"]),
         Paragraph("ESTATUS",   s["label"]),  Paragraph(q.status.upper(),      s["value"])],
    ]
    info_tbl = Table(info_rows, colWidths=[22*mm, 60*mm, 22*mm, 60*mm])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAPER),
        ("BOX",        (0, 0), (-1, -1), 0.6, TURQUOISE_SOFT),
        ("LINEBELOW",  (0, 0), (-1, -2), 0.3, TURQUOISE_SOFT),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 6 * mm))

    # --- Tabla de items ---
    header = ["#", "Producto / Pieza", "Cant.", "Modo", "P. Unit.", "Peso kg", "Importe"]
    data = [header]

    for idx, it in enumerate(q.items, 1):
        product_block = [
            Paragraph(f"<b>{it.product}</b>", s["value"]),
        ]
        desc_line = []
        if it.piece:
            desc_line.append(it.piece)
        if it.notes:
            desc_line.append(it.notes)
        if desc_line:
            product_block.append(Paragraph(" · ".join(desc_line), s["notes"]))

        mode_lbl = "por pieza" if it.price_mode == "pieza" else "por kg"
        weight = f"{Decimal(it.weight_kg):.3f}" if it.weight_kg else "—"

        data.append([
            str(idx),
            product_block,
            f"{Decimal(it.quantity):g}",
            mode_lbl,
            _fmt_money(it.unit_price, q.currency),
            weight,
            _fmt_money(it.line_total, q.currency),
        ])

    items_tbl = Table(
        data,
        colWidths=[8*mm, 70*mm, 16*mm, 18*mm, 26*mm, 16*mm, 28*mm],
        repeatRows=1,
    )
    items_tbl.setStyle(TableStyle([
        # header
        ("BACKGROUND",   (0, 0), (-1, 0), TURQUOISE_DEEP),
        ("TEXTCOLOR",    (0, 0), (-1, 0), PAPER),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 8.5),
        ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
        # body
        ("FONTSIZE",     (0, 1), (-1, -1), 9),
        ("TEXTCOLOR",    (0, 1), (-1, -1), INK),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",        (0, 1), (0, -1),  "CENTER"),
        ("ALIGN",        (2, 1), (2, -1),  "RIGHT"),
        ("ALIGN",        (4, 1), (4, -1),  "RIGHT"),
        ("ALIGN",        (5, 1), (5, -1),  "RIGHT"),
        ("ALIGN",        (6, 1), (6, -1),  "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PAPER, TURQUOISE_SOFT.clone(alpha=0.15) if False else colors.Color(0.95, 0.98, 0.98)]),
        ("LINEBELOW",    (0, 0), (-1, 0), 1, BRASS),
        ("BOX",          (0, 0), (-1, -1), 0.4, TURQUOISE_SOFT),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 6 * mm))

    # --- Totales ---
    iva_pct = f"{Decimal(q.iva_rate) * 100:.0f}%"
    totals_data = [
        ["Subtotal",        _fmt_money(q.subtotal,   q.currency)],
        [f"IVA ({iva_pct})", _fmt_money(q.iva_amount, q.currency)],
        ["TOTAL",           _fmt_money(q.total,      q.currency)],
    ]
    totals_tbl = Table(totals_data, colWidths=[40*mm, 38*mm], hAlign="RIGHT")
    totals_tbl.setStyle(TableStyle([
        ("FONTSIZE",     (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",    (0, 0), (-1, -2), INK),
        ("ALIGN",        (0, 0), (0, -1), "LEFT"),
        ("ALIGN",        (1, 0), (1, -1), "RIGHT"),
        ("LINEBELOW",    (0, 0), (-1, 1), 0.3, TURQUOISE_SOFT),
        # fila total
        ("BACKGROUND",   (0, 2), (-1, 2), TURQUOISE_DEEP),
        ("TEXTCOLOR",    (0, 2), (-1, 2), PAPER),
        ("FONTNAME",     (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 2), (-1, 2), 11.5),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(totals_tbl)
    story.append(Spacer(1, 8 * mm))

    # --- Notas ---
    if q.notes:
        story.append(Paragraph("<b>Notas:</b>", s["label"]))
        story.append(Paragraph(q.notes.replace("\n", "<br/>"), s["notes"]))
        story.append(Spacer(1, 4 * mm))

    # --- Condiciones ---
    story.append(Paragraph("<b>CONDICIONES</b>", s["label"]))
    conditions = (
        "• Precios en " + (q.currency or "MXN") + ", IVA desglosado. "
        "• Tiempo de entrega sujeto a confirmación al recibir orden de compra. "
        "• Forma de pago: a convenir. "
        "• Fletes y maniobras no incluidos salvo indicación expresa. "
        "• Cotización sujeta a disponibilidad de materia prima."
    )
    story.append(Paragraph(conditions, s["notes"]))

    # Build
    status = getattr(q, "status", None)

    def _on_page(c, d):
        _header_footer(c, d, company_info, status=status)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()
