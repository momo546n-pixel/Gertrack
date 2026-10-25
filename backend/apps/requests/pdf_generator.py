import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from gertrack.pdf_style import (
    BLACK, GREY_HEADER, BORDER,
    styles, company_header, section_title, grid_table_style, cols,
)

# ─────────────────────────────────────────────────────────────────────────────
# BON DE COMMANDE (type = achat) — style noir et blanc professionnel,
# reproduisant la structure du modèle GERTECH réel (GES.PAA.FE.17) : en-tête
# société/document, bloc "Affaire suivie par" / "À l'attention de", Projet/
# Objet, tableau des livrables, totaux, observations, adresse de livraison,
# mention importante. Palette et helpers communs dans gertrack/pdf_style.py
# (plus de bannière bleu marine — voir aussi apps.operations.pdf_generator et
# apps.accounts.pdf_generator, même style).
# ─────────────────────────────────────────────────────────────────────────────

def _label_value_row(pairs, col_widths, S):
    """Ligne de labels au-dessus d'une ligne de valeurs (ex. Référence
    document / Référence commercial / Date), comme dans le modèle GERTECH."""
    header_row = [Paragraph(label, S['th_left']) for label, _ in pairs]
    value_row  = [Paragraph(value or '–', S['body']) for _, value in pairs]
    tbl = Table([header_row, value_row], colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ('BOX',          (0, 0), (-1, -1), 0.75, BLACK),
        ('INNERGRID',    (0, 0), (-1, -1), 0.5, BORDER),
        ('BACKGROUND',   (0, 0), (-1, 0), GREY_HEADER),
        ('LEFTPADDING',  (0, 0), (-1, -1), 2.5*mm),
        ('TOPPADDING',   (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 2*mm),
    ]))
    return tbl


def _contact_table(left_title, left_lines, right_title, right_lines, col_widths, S):
    """Bloc 'Affaire suivie par' / 'À l'attention de' — UNE table à 2 lignes
    (titres, puis contenu) et 2 colonnes, exactement comme le modèle GERTECH
    (2 rows x 2 cols, pas un bloc à cellule unique)."""
    left_content  = '<br/>'.join(left_lines)
    right_content = '<br/>'.join(right_lines)
    data = [
        [Paragraph(f'<b>{left_title}</b>', S['th_left']), Paragraph(f'<b>{right_title}</b>', S['th_left'])],
        [Paragraph(left_content, S['body']), Paragraph(right_content, S['body'])],
    ]
    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ('BOX',          (0, 0), (-1, -1), 0.75, BLACK),
        ('INNERGRID',    (0, 0), (-1, -1), 0.5, BORDER),
        ('LEFTPADDING',  (0, 0), (-1, -1), 3*mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3*mm),
        ('TOPPADDING',   (0, 0), (-1, -1), 1.5*mm),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 1.5*mm),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
    ]))
    return tbl


def _stacked_label_value_table(pairs, col_widths, S):
    """Table de paires label/valeur empilées verticalement (une paire par
    ligne) — ex. Projet / Objet dans le modèle GERTECH. À ne pas confondre
    avec `_label_value_row` (une ligne de labels au-dessus d'une ligne de
    valeurs) : ici chaque ligne est un couple [label, valeur] indépendant."""
    data = [[Paragraph(label, S['th_left']), Paragraph(value or '–', S['body'])] for label, value in pairs]
    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ('BOX',          (0, 0), (-1, -1), 0.75, BLACK),
        ('INNERGRID',    (0, 0), (-1, -1), 0.5, BORDER),
        ('BACKGROUND',   (0, 0), (0, -1), GREY_HEADER),
        ('LEFTPADDING',  (0, 0), (-1, -1), 2.5*mm),
        ('TOPPADDING',   (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 2*mm),
    ]))
    return tbl


def _items_table(items, date_prevue, w, S):
    """Tableau des livrables — N° / Désignation / Ut / Qté / Coût unitaire /
    Coût total / Date prévue, PUIS les lignes TOTAL / TVA % / MONTANT DE LA
    FACTURE en bas de la MÊME table (label fusionné sur les 5 premières
    colonnes, montant dans la colonne 6) — exactement la structure du
    modèle GERTECH (une seule table de 7 colonnes, pas un tableau de totaux
    séparé). `w` doit être la même largeur totale que les autres tableaux du
    document (voir cols()), pour que les bordures verticales s'alignent."""
    headers = ['N°', 'Désignation des livrables', 'Ut', 'Qté', 'Coût unitaire\nen FCFA', 'Coût total\nen FCFA', 'Date\nPrévue']
    # Proportions reprises du modèle GERTECH (8/62/12/14/26/26/22 sur 170mm),
    # ré-appliquées à la largeur réelle w pour rester alignées avec les
    # autres tableaux du document.
    col_w = cols(w, 8/170, 62/170, 12/170, 14/170, 26/170, 26/170, 22/170)

    data = [[Paragraph(h.replace('\n', '<br/>'), S['th']) for h in headers]]
    total_general = 0

    for i, item in enumerate(items, 1):
        qty        = float(item.quantity)
        unit_price = float(item.unit_price) if item.unit_price else None
        total      = qty * unit_price if unit_price else None
        if total:
            total_general += total

        desig = getattr(item.product, 'designation', '–')
        unit  = getattr(item.product, 'unit', '–')

        data.append([
            Paragraph(str(i), S['small_c']),
            Paragraph(desig, S['body']),
            Paragraph(unit, S['small_c']),
            Paragraph(f'{qty:g}', S['small_c']),
            Paragraph(f'{unit_price:,.0f}' if unit_price else '–', ParagraphStyle('r', parent=S['small_c'], alignment=TA_RIGHT)),
            Paragraph(f'{total:,.0f}' if total else '–', ParagraphStyle('r2', parent=S['small_c'], alignment=TA_RIGHT)),
            Paragraph(date_prevue, S['small_c']),
        ])

    n_item_rows = len(data)  # en-tête + lignes d'articles, avant les totaux

    totals_style = ParagraphStyle('tot', fontName='Helvetica-Bold', fontSize=8.5, textColor=BLACK)
    totals_style_r = ParagraphStyle('totr', parent=totals_style, alignment=TA_RIGHT)
    for label, amount in [
        ('TOTAL', f'{total_general:,.0f} F'),
        ('TVA %', '0,00'),
        ('MONTANT DE LA FACTURE', f'{total_general:,.0f} F'),
    ]:
        data.append([Paragraph(label, totals_style), '', '', '', '', Paragraph(amount, totals_style_r), ''])

    tbl = Table(data, colWidths=col_w, repeatRows=1)
    total_rows_start = n_item_rows
    style = grid_table_style(header_rows=1) + [
        ('ALIGN', (3, 1), (5, n_item_rows - 1), 'RIGHT'),
        # Lignes de totaux : label fusionné sur les 5 premières colonnes
        # (comme le modèle GERTECH), fond gris pour "MONTANT DE LA FACTURE".
        ('SPAN', (0, total_rows_start), (4, total_rows_start)),
        ('SPAN', (0, total_rows_start + 1), (4, total_rows_start + 1)),
        ('SPAN', (0, total_rows_start + 2), (4, total_rows_start + 2)),
        ('BACKGROUND', (0, total_rows_start + 2), (-1, total_rows_start + 2), GREY_HEADER),
        # Lignes plus denses que le style générique (voir grid_table_style) —
        # rapproche la hauteur de ligne de celle du modèle GERTECH, pour
        # qu'une commande de plusieurs articles tienne sur une seule page.
        ('TOPPADDING',    (0, 1), (-1, -1), 0.6*mm),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 0.6*mm),
    ]
    tbl.setStyle(TableStyle(style))
    return tbl, total_general


def _signature_block(left_label, left_name, right_label, right_name, w, S):
    def _sig_cell(label, name):
        return [
            Paragraph(f'<b>{label}</b>', S['small_c']),
            Spacer(1, 1*mm),
            HRFlowable(width='80%', thickness=0.5, color=BLACK),
            Spacer(1, 0.7*mm),
            Paragraph(name or 'Non signé', ParagraphStyle('sn', parent=S['body_bold'], alignment=TA_CENTER)),
        ]
    tbl = Table([[_sig_cell(left_label, left_name), _sig_cell(right_label, right_name)]], colWidths=cols(w, 0.5, 0.5))
    tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
        ('BOX',    (0, 0), (0, 0), 0.5, BORDER),
        ('BOX',    (1, 0), (1, 0), 0.5, BORDER),
        ('TOPPADDING',   (0, 0), (-1, -1), 1*mm),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 1*mm),
    ]))
    return tbl


def generate_bon_commande(request_obj):
    """Génère le bon de commande PDF (noir et blanc, professionnel) pour une
    demande d'achat validée. Retourne un objet BytesIO."""
    buffer = io.BytesIO()
    S = styles()
    w = A4[0] - 30*mm

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=6*mm, bottomMargin=6*mm,
        title=f'Bon de Commande {request_obj.reference}',
        author='GERTECH ENERGIES ET SERVICES SAS',
    )

    date_str = request_obj.dg_validated_at.strftime('%d/%m/%Y') if request_obj.dg_validated_at else datetime.now().strftime('%d/%m/%Y')

    def _build_main(extra_gap=0):
        """Construit le contenu principal (hors pied de page) — factorisé
        dans une fonction pour pouvoir être appelée deux fois avec des
        instances de Flowable FRAÎCHES : une passe de mesure (wrap()) et une
        passe réelle pour doc.build(). Réutiliser les MÊMES instances de
        Table entre les deux passes fausse les hauteurs mesurées — leur
        wrap() interne n'est pas idempotent d'un appel à l'autre.

        extra_gap (en points) est ajouté à CHAQUE espaceur inter-sections,
        afin de répartir l'espace restant de la page sur tout le document
        plutôt que de le concentrer en un seul grand blanc avant le pied de
        page — voir le calcul plus bas (« Remplir toute la page »)."""
        flowables = []
        gap_count = [0]

        def gap(base_mm):
            gap_count[0] += 1
            return Spacer(1, base_mm*mm + extra_gap)

        # ── En-tête société + document ──────────────────────────────────────
        flowables.append(company_header(w, 'GES.PAA.FE.17', doc_rev='00', page_label='Page 1 / 1'))
        flowables.append(gap(2))
        flowables.append(Paragraph('BON DE COMMANDE' + ('  —  URGENT' if request_obj.is_urgent else ''), S['doc_title']))
        flowables.append(gap(2.5))

        # ── Référence document / commercial / Date ───────────────────────────
        flowables.append(_label_value_row(
            [('Référence document', request_obj.reference),
             ('Référence commercial', '–'),
             ('Date', date_str)],
            col_widths=cols(w, 1/3, 1/3, 1/3), S=S,
        ))
        flowables.append(gap(2.5))

        # ── Affaire suivie par / À l'attention de ────────────────────────────
        dem = request_obj.requested_by
        dem_name = (dem.get_full_name() or dem.username) if dem else 'Compte supprimé'
        dem_role = dem.get_role_display() if dem and hasattr(dem, 'get_role_display') else '–'
        suivi_lines = [
            f'Prénom Nom : {dem_name}',
            f'Fonction : {dem_role}',
            f'Email : {getattr(dem, "email", "") or "–"}',
            f'Tel : {getattr(dem, "phone", "") or "–"}',
        ]

        supplier = request_obj.supplier
        if supplier:
            attn_lines = [
                f'Prestataire / Fournisseur : {supplier.name}',
                f'Adresse : {supplier.address or supplier.city or "–"}',
                f'Contact : {supplier.contact_person or "–"}',
                f'Email : {supplier.email or "–"}',
                f'Tel : {supplier.phone or "–"}',
            ]
        else:
            attn_lines = ['Prestataire / Fournisseur : Non spécifié']

        flowables.append(_contact_table(
            'Affaire suivie par : GERTECH ENERGIES ET SERVICES SAS', suivi_lines,
            'À l\'attention de :', attn_lines,
            col_widths=cols(w, 0.5, 0.5), S=S,
        ))
        flowables.append(gap(2.5))

        # ── Projet / Objet (2 lignes empilées, comme le modèle GERTECH) ──────
        flowables.append(_stacked_label_value_table(
            [('Projet', request_obj.project.name if request_obj.project else '–'),
             ('Objet', request_obj.motif or '–')],
            col_widths=cols(w, 0.25, 0.75), S=S,
        ))
        flowables.append(gap(2))

        # ── Tableau des livrables ─────────────────────────────────────────────
        items = list(request_obj.items.select_related('product').all())
        date_prevue = request_obj.date_needed.strftime('%d/%m/%Y') if request_obj.date_needed else '–'
        items_tbl, total_general = _items_table(items, date_prevue, w, S)
        flowables.append(items_tbl)
        flowables.append(gap(2))

        # ── Observations / Adresse de livraison / Date limite / Important ────
        # UNE table à 4 lignes empilées (1 colonne), comme le modèle GERTECH —
        # pas des paragraphes libres non encadrés.
        warehouse   = request_obj.warehouse
        livraison   = warehouse.location if (warehouse and warehouse.location) else 'Dakar, Sénégal'
        date_line   = request_obj.date_needed.strftime('%d/%m/%Y') if request_obj.date_needed else '–'
        obs_rows = [
            [Paragraph(
                f"<b>OBSERVATIONS :</b><br/>- Condition de paiement : {request_obj.notes or 'À définir'}"
                f"<br/>- Incoterm (2020) : –",
                S['body']
            )],
            [Paragraph(f"<b>ADRESSE DE LIVRAISON :</b> {livraison}", S['body'])],
            [Paragraph(f"<b>DATE LIMITE :</b> {date_line}", S['body'])],
            [Paragraph(
                "<b>IMPORTANT :</b> Merci de bien vouloir joindre à la facture l'original du bordereau de "
                "livraison, le PV de réception et l'original du bon de commande.",
                S['small']
            )],
        ]
        obs_tbl = Table(obs_rows, colWidths=[w])
        obs_tbl.setStyle(TableStyle([
            ('BOX',          (0, 0), (-1, -1), 0.75, BLACK),
            ('INNERGRID',    (0, 0), (-1, -1), 0.5, BORDER),
            ('LEFTPADDING',  (0, 0), (-1, -1), 3*mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3*mm),
            ('TOPPADDING',   (0, 0), (-1, -1), 1.5*mm),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 1.5*mm),
        ]))
        flowables.append(obs_tbl)
        flowables.append(gap(2))

        # ── Validation DOP (si applicable) ───────────────────────────────────
        if request_obj.dop_validated_by:
            dop_name = request_obj.dop_validated_by.get_full_name() or request_obj.dop_validated_by.username
            dop_date = request_obj.dop_validated_at.strftime('%d/%m/%Y') if request_obj.dop_validated_at else '–'
            flowables.append(Paragraph(f'Validé DOP par {dop_name} le {dop_date}', S['small']))
            if request_obj.dop_comment:
                flowables.append(Paragraph(f'Commentaire DOP : {request_obj.dop_comment}', S['small']))
            flowables.append(gap(2))

        # ── Signatures ────────────────────────────────────────────────────────
        flowables.append(section_title('Signatures'))
        flowables.append(gap(1))
        dg_name = ''
        if request_obj.dg_validated_by:
            dg_name = request_obj.dg_validated_by.get_full_name() or request_obj.dg_validated_by.username
        flowables.append(_signature_block(
            left_label='RESPONSABLE ACHAT ET LOGISTIQUE',
            left_name=(request_obj.requested_by.get_full_name() or request_obj.requested_by.username) if request_obj.requested_by else 'Compte supprimé',
            right_label='DIRECTEUR GÉNÉRAL',
            right_name=dg_name,
            w=w, S=S,
        ))
        return flowables, gap_count[0]

    def _build_footer():
        """Pied de page — une seule ligne, pour tenir sur une page. Même
        raison de factorisation que _build_main (instances fraîches)."""
        return [
            HRFlowable(width='100%', thickness=0.5, color=BORDER),
            Spacer(1, 1*mm),
            Paragraph(
                f'GERTECH ENERGIES ET SERVICES SAS · Document généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")} · '
                f'{request_obj.reference} · Généré automatiquement par GerTrack — toute modification manuelle invalide ce document.',
                S['footer']
            ),
        ]

    # ── Remplir toute la page ─────────────────────────────────────────────────
    # Un petit bon de commande (peu d'articles) ne doit pas laisser une
    # grande zone blanche en bas de page. On mesure (sur des instances
    # dédiées à la mesure, jamais réutilisées pour le rendu réel — voir
    # _build_main) la hauteur réellement consommée par le contenu, puis on
    # répartit l'espace restant sur CHAQUE espaceur inter-sections (via
    # extra_gap) plutôt que de le concentrer en un seul grand blanc juste
    # avant le pied de page — le document occupe ainsi visuellement toute la
    # page, sans jamais dépasser une seule page (si le contenu est déjà plus
    # grand que la page, extra_gap reste nul).
    # SimpleDocTemplate construit son unique Frame avec un padding interne
    # PAR DÉFAUT de 6pt en haut et en bas (en plus de topMargin/bottomMargin
    # eux-mêmes) — sans en tenir compte ici, l'espace calculé serait
    # légèrement trop grand et pousserait le pied de page sur une 2ᵉ page.
    default_frame_padding = 6 + 6  # points (haut + bas)
    usable_height = A4[1] - doc.topMargin - doc.bottomMargin - default_frame_padding

    # Une marge de sécurité est retranchée avant répartition : viser un
    # remplissage strictement égal à usable_height laisse une hauteur réelle
    # exactement à la limite de la frame, que les imprécisions flottantes de
    # ReportLab (arrondis internes de Table.wrap, etc.) peuvent faire déborder
    # sur une 2ᵉ page.
    safety_margin = 2*mm

    measuring_main, gap_count = _build_main(extra_gap=0)
    measuring_flowables = measuring_main + [Spacer(1, 2*mm)] + _build_footer()
    consumed = sum(f.wrap(w, usable_height)[1] for f in measuring_flowables)
    remaining = usable_height - consumed - safety_margin
    extra_gap = (remaining / gap_count) if (remaining > 0 and gap_count) else 0

    story, _ = _build_main(extra_gap=extra_gap)
    story.append(Spacer(1, 2*mm))
    story.extend(_build_footer())

    doc.build(story)
    buffer.seek(0)
    return buffer
