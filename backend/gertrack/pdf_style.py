"""
Palette et helpers ReportLab partagés par tous les documents PDF de GerTrack
(bon de commande, rapport hebdomadaire, export du Centre d'audit).

Style noir et blanc professionnel — pas de bannière de couleur ni d'accent
bleu/marine : uniquement noir, blancs et gris, avec du gras/des cadres pour
la hiérarchie visuelle, à l'image des documents administratifs GERTECH réels
(cf. modèle GES.PAA.FE.17 fourni comme référence). Centralisé ici (comme
gertrack/business_rules.py pour les règles métier) pour que les 3 générateurs
de PDF ne dupliquent plus chacun leur propre palette.

Ce module ne doit jamais importer de modèle Django, pour rester importable
depuis n'importe quelle app sans risque d'import circulaire.
"""
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import Table, TableStyle, Paragraph, Image
import os

# ── Palette ──────────────────────────────────────────────────────────────────
BLACK       = colors.black
WHITE       = colors.white
GREY_DARK   = colors.HexColor('#333333')
GREY_MID    = colors.HexColor('#666666')
GREY_TEXT   = colors.HexColor('#4D4D4D')
GREY_LIGHT  = colors.HexColor('#F0F0F0')
GREY_HEADER = colors.HexColor('#D9D9D9')
BORDER      = colors.HexColor('#999999')
BORDER_LIGHT= colors.HexColor('#CCCCCC')

# Chemin du logo GerTrack (frontend/public/logo.png) — réutilisé tel quel,
# aucune copie dupliquée du fichier dans le backend.
LOGO_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'frontend', 'public', 'logo.png'
))


def styles():
    """Styles de paragraphe communs — noir/gris uniquement."""
    return {
        'company':  ParagraphStyle('company', fontName='Helvetica-Bold', fontSize=10.5, textColor=BLACK),
        'company_s':ParagraphStyle('company_s', fontName='Helvetica', fontSize=7.5, textColor=GREY_TEXT),
        'doc_title':ParagraphStyle('doc_title', fontName='Helvetica-Bold', fontSize=15, textColor=BLACK, alignment=TA_CENTER),
        'doc_code': ParagraphStyle('doc_code', fontName='Helvetica', fontSize=7, textColor=GREY_TEXT, alignment=TA_RIGHT),
        'section':  ParagraphStyle('section', fontName='Helvetica-Bold', fontSize=8, textColor=BLACK, spaceAfter=3, letterSpacing=0.5),
        'body':     ParagraphStyle('body', fontName='Helvetica', fontSize=8.5, textColor=BLACK, leading=12),
        'body_bold':ParagraphStyle('body_bold', fontName='Helvetica-Bold', fontSize=8.5, textColor=BLACK, leading=12),
        'small':    ParagraphStyle('small', fontName='Helvetica', fontSize=7, textColor=GREY_TEXT),
        'small_c':  ParagraphStyle('small_c', fontName='Helvetica', fontSize=7, textColor=GREY_TEXT, alignment=TA_CENTER),
        'total':    ParagraphStyle('total', fontName='Helvetica-Bold', fontSize=10.5, textColor=BLACK, alignment=TA_RIGHT),
        'footer':   ParagraphStyle('footer', fontName='Helvetica', fontSize=7, textColor=GREY_MID, alignment=TA_CENTER),
        'th':       ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=7.5, textColor=BLACK, alignment=TA_CENTER),
        'th_left':  ParagraphStyle('th_left', fontName='Helvetica-Bold', fontSize=7.5, textColor=BLACK),
    }


def cols(content_width, *fractions):
    """Répartit `content_width` selon des fractions qui doivent sommer à 1.0
    — garantit que chaque tableau d'une même page fait EXACTEMENT la même
    largeur totale que les autres (sinon leurs bordures verticales ne
    s'alignent pas d'une section à l'autre, voir l'audit visuel du modèle
    GES.PAA.FE.17). La dernière colonne absorbe l'arrondi flottant pour que
    la somme soit rigoureusement égale à content_width, jamais approximative."""
    assert abs(sum(fractions) - 1.0) < 1e-6, f'les fractions doivent sommer à 1.0 (reçu {sum(fractions)})'
    widths = [round(content_width * f, 2) for f in fractions[:-1]]
    widths.append(content_width - sum(widths))
    return widths


def company_header(content_width, doc_code=None, doc_rev='00', page_label='Page 1 / 1'):
    """Bandeau d'en-tête commun : logo + identité GERTECH à gauche,
    code document/révision/page à droite — reproduit la forme des documents
    administratifs GERTECH réels (voir modèle GES.PAA.FE.17).

    `content_width` doit être la même largeur totale que celle utilisée pour
    tous les autres tableaux de la page (voir `cols()`), afin que la ligne
    sous l'en-tête s'aligne avec les bordures des tableaux qui suivent.

    `doc_code` est un numéro d'enregistrement qualité réel (ex. GES.PAA.FE.17)
    — ne jamais en inventer un pour un document qui n'en a pas (ex. les
    exports système comme le Centre d'audit) : laisser `doc_code=None` dans
    ce cas, seuls Rév/Page restent affichés."""
    S = styles()
    left_col_w, right_col_w = cols(content_width, 0.76, 0.24)

    left_cell = []
    if os.path.exists(LOGO_PATH):
        left_cell.append(Image(LOGO_PATH, width=14*mm, height=14*mm))
    left = Table([[
        left_cell[0] if left_cell else Paragraph('', S['company']),
        [
            Paragraph('GERTECH ENERGIES ET SERVICES SAS', S['company']),
            Paragraph('Hann Mariste, Lot Z/22 — Dakar, Sénégal', S['company_s']),
            Paragraph('+221 33 832 84 30  |  contact@gertech-e-services.com', S['company_s']),
        ],
    ]], colWidths=cols(left_col_w, 16*mm / left_col_w, 1 - 16*mm / left_col_w))
    left.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))

    right = []
    if doc_code:
        right.append(Paragraph(doc_code, S['doc_code']))
    right += [
        Paragraph(f'Rév : {doc_rev}', S['doc_code']),
        Paragraph(page_label, S['doc_code']),
    ]

    tbl = Table([[left, right]], colWidths=[left_col_w, right_col_w])
    tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, BLACK),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
    ]))
    return tbl


def section_title(text):
    S = styles()
    return Paragraph(f'<b>{text.upper()}</b>', S['section'])


def grid_table_style(header_rows=1, zebra=True):
    """TableStyle standard pour un tableau de données : en-tête gris foncé
    fond clair, grille noire fine, alternance de fond en gris très clair."""
    cmds = [
        ('BACKGROUND',   (0, 0), (-1, header_rows - 1), GREY_HEADER),
        ('FONTNAME',     (0, 0), (-1, header_rows - 1), 'Helvetica-Bold'),
        ('TEXTCOLOR',    (0, 0), (-1, header_rows - 1), BLACK),
        ('GRID',         (0, 0), (-1, -1), 0.5, BLACK),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',   (0, 0), (-1, -1), 2.5*mm),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 2.5*mm),
        ('LEFTPADDING',  (0, 0), (-1, -1), 2*mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2*mm),
    ]
    if zebra:
        cmds.append(('ROWBACKGROUNDS', (0, header_rows), (-1, -1), [WHITE, GREY_LIGHT]))
    return cmds
