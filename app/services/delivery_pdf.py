"""
PDF de ticket de entrega — usa reportlab.
Devuelve bytes; el router decide cómo entregarlo (download o guardar a disco).
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)

from app.models.delivery import Delivery


def _img_or_blank(path: str | None, w_mm=40, h_mm=30):
    if not path:
        return ""
    try:
        return Image(path, width=w_mm * mm, height=h_mm * mm)
    except Exception:
        return ""


def build_delivery_pdf(d: Delivery) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"Entrega {d.code}",
    )
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=18,
                        textColor=colors.HexColor("#0e7490"))
    label = ParagraphStyle("lbl", parent=ss["Normal"], fontSize=8,
                           textColor=colors.HexColor("#64748b"),
                           leading=10, spaceAfter=2)
    val = ParagraphStyle("val", parent=ss["Normal"], fontSize=10, leading=12)

    story = []
    story.append(Paragraph("HECORP · Ticket de entrega", h1))
    story.append(Paragraph(f"Folio <b>{d.code}</b> · "
                           f"emitido {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ss["Normal"]))
    story.append(Spacer(1, 8))

    cust = d.customer
    drv = d.driver

    # bloque cliente / chofer
    rows = [
        [Paragraph("CLIENTE", label), Paragraph("CHOFER", label)],
        [
            Paragraph(
                f"<b>{(cust.name if cust else '-')}</b><br/>"
                f"{cust.contact_name or ''}<br/>"
                f"{cust.address or ''}<br/>"
                f"{('Tel: ' + cust.phone) if cust and cust.phone else ''}", val
            ),
            Paragraph(
                f"<b>{(drv.name if drv else '-')}</b><br/>"
                f"{(drv.vehicle_type or '') if drv else ''} "
                f"{(drv.vehicle_plate or '') if drv else ''}<br/>"
                f"{('Tel: ' + drv.phone) if drv and drv.phone else ''}", val
            ),
        ],
    ]
    t = Table(rows, colWidths=[85 * mm, 85 * mm])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    # detalle entrega
    detail_rows = [
        ["Programada", (d.scheduled_at or "").strftime("%Y-%m-%d %H:%M") if d.scheduled_at else "-"],
        ["Llegada",   (d.arrived_at or "").strftime("%Y-%m-%d %H:%M") if d.arrived_at else "-"],
        ["Entregado", (d.delivered_at or "").strftime("%Y-%m-%d %H:%M") if d.delivered_at else "-"],
        ["Producto",   d.product_summary or "-"],
        ["Ticket #",   d.ticket_number or "-"],
        ["Monto",     f"{d.amount} {d.currency}" if d.amount is not None else "-"],
        ["Pago",       d.payment_status or "-"],
        ["Estado",     d.status.upper()],
    ]
    dt = Table(detail_rows, colWidths=[35 * mm, 135 * mm])
    dt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1),
            [colors.white, colors.HexColor("#f8fafc")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(dt)
    story.append(Spacer(1, 8))

    # mensaje + reporte
    if d.delivery_message:
        story.append(Paragraph("Mensaje al cliente", label))
        story.append(Paragraph(d.delivery_message, val))
        story.append(Spacer(1, 4))
    if d.delivery_report:
        story.append(Paragraph("Reporte de cierre", label))
        story.append(Paragraph(d.delivery_report, val))
        story.append(Spacer(1, 4))
    if d.issue_code:
        story.append(Paragraph(
            f"<b>Incidencia:</b> {d.issue_code} — {d.issue_detail or ''}", val))
        story.append(Spacer(1, 4))

    # foto + firma
    art_rows = [
        [Paragraph("FOTO DE ENTREGA", label), Paragraph("FIRMA", label)],
        [_img_or_blank(d.photo_url, 80, 55), _img_or_blank(d.signature_url, 80, 35)],
    ]
    art = Table(art_rows, colWidths=[85 * mm, 85 * mm])
    art.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("ALIGN", (0, 1), (-1, 1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(art)
    story.append(Spacer(1, 14))

    story.append(Paragraph(
        "Documento generado automáticamente por HECORP. "
        "Conserve este ticket como comprobante de entrega.",
        ParagraphStyle("foot", parent=ss["Normal"], fontSize=7,
                       textColor=colors.HexColor("#94a3b8"))
    ))

    doc.build(story)
    return buf.getvalue()
