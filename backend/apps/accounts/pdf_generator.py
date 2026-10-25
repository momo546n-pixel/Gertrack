import io
from django.utils import timezone
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from gertrack.pdf_style import BLACK, GREY_TEXT, styles, company_header, grid_table_style, cols


def generate_audit_pdf(entries, title="Centre d'audit — Export", filters_label=''):
    """Export PDF (noir et blanc, professionnel) d'une liste d'AuditLog déjà
    filtrée/scopée par l'appelant (voir apps.accounts.views.
    _audit_center_queryset) — ce module ne fait que la mise en page, aucune
    logique de permission ou de filtre ici."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        topMargin=12*mm, bottomMargin=12*mm, leftMargin=12*mm, rightMargin=12*mm,
    )
    S = styles()
    content_w = landscape(A4)[0] - 24*mm

    # Pas de code d'enregistrement qualité ici : le Centre d'audit est un
    # export système GerTrack, pas un document GERTECH officiel enregistré
    # (contrairement au bon de commande GES.PAA.FE.17) — voir company_header.
    elements = [company_header(content_w, doc_code=None, page_label='Page 1 / 1')]
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(title.upper(), ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=14, textColor=BLACK, alignment=TA_CENTER, spaceAfter=3)))
    sub = f"Généré le {timezone.now():%d/%m/%Y à %H:%M}" + (f' — {filters_label}' if filters_label else '')
    elements.append(Paragraph(sub, ParagraphStyle('sub', fontName='Helvetica', fontSize=8.5, textColor=GREY_TEXT, alignment=TA_CENTER)))
    elements.append(Spacer(1, 5*mm))

    head_style = S['th']
    cell_style = ParagraphStyle('cell', fontName='Helvetica', fontSize=8, textColor=BLACK, leading=10)

    rows = [[
        Paragraph('Date', head_style), Paragraph('Utilisateur', head_style),
        Paragraph('Action', head_style), Paragraph('Objet', head_style),
        Paragraph('Description', head_style),
    ]]
    for e in entries:
        rows.append([
            Paragraph(e.created_at.strftime('%d/%m/%Y %H:%M'), cell_style),
            Paragraph(e.user.get_full_name() or e.user.username if e.user else '—', cell_style),
            Paragraph(e.get_action_display(), cell_style),
            Paragraph(f"{e.model_name} #{e.object_id}" if e.object_id else e.model_name, cell_style),
            Paragraph(e.description or '', cell_style),
        ])

    # Proportions d'origine (28/40/32/45/125 sur 270mm), ré-appliquées à
    # content_w pour que ce tableau s'aligne exactement avec l'en-tête.
    _fracs = [28, 40, 32, 45, 125]
    table = Table(rows, colWidths=cols(content_w, *[v / sum(_fracs) for v in _fracs]), repeatRows=1)
    table.setStyle(TableStyle(grid_table_style(header_rows=1) + [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer
