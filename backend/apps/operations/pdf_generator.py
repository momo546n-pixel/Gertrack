import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from gertrack.pdf_style import BLACK, WHITE, GREY_LIGHT, GREY_HEADER, BORDER, GREY_TEXT, company_header, cols

# ── Style noir et blanc professionnel (voir gertrack/pdf_style.py) ──────────
# Les indicateurs de risque (météo projet, écart planning) restent lisibles
# au premier coup d'œil sans couleur : gras + fond gris + libellé explicite,
# jamais de rouge/orange/vert.
WEATHER_LABELS = {'ok': 'OK — DANS LES DÉLAIS', 'risque': 'RISQUE', 'critique': 'CRITIQUE'}


def generate_weekly_synthesis_pdf(report):
    """
    Génère le rapport de synthèse hebdomadaire GERTECH (noir et blanc,
    professionnel), format A4 paysage, reproduisant la feuille
    Reporting_Synthese.
    """
    project = report.project
    buffer  = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        topMargin=12*mm,
        bottomMargin=12*mm,
        leftMargin=12*mm,
        rightMargin=12*mm,
        title=f'Rapport S{report.week_number}/{report.year} — {project.code}',
    )

    styles = getSampleStyleSheet()

    def sty(name='Normal', **kwargs):
        return ParagraphStyle(name, parent=styles['Normal'], **kwargs)

    content_w = landscape(A4)[0] - 24*mm
    elements  = []

    # ══════════════════════════════════════════════════════════════════════
    # 1. EN-TÊTE
    # ══════════════════════════════════════════════════════════════════════
    elements.append(company_header(content_w, 'GES.PAA.FE.17', doc_rev='00', page_label='Page 1 / 1'))
    elements.append(Spacer(1, 3*mm))

    doc_title = sty('DT', fontSize=14, fontName='Helvetica-Bold', textColor=BLACK, alignment=TA_CENTER)
    doc_sub   = sty('DS', fontSize=9, textColor=GREY_TEXT, alignment=TA_CENTER)
    elements.append(Paragraph('RAPPORT DE SYNTHÈSE HEBDOMADAIRE', doc_title))
    elements.append(Spacer(1, 1.5*mm))
    elements.append(Paragraph(
        f'Projet : <b>{project.code}</b> — {project.name} &nbsp;|&nbsp; '
        f'Semaine <b>{report.week_number}</b> / {report.year} &nbsp;|&nbsp; '
        f'Date : <b>{report.report_date.strftime("%d/%m/%Y")}</b>',
        doc_sub
    ))
    elements.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════════════════════════════════════
    # 2. TABLEAU DE SYNTHESE (Reporting_Synthese)
    # ══════════════════════════════════════════════════════════════════════
    pm_name = '—'
    if project.project_manager:
        pm_name = project.project_manager.get_full_name() or project.project_manager.username

    weather_label = WEATHER_LABELS.get(report.weather, report.weather)

    # Responsable de l'action principale
    main_responsible = '—'
    first_detail = report.task_details.filter(problem__gt='').select_related('action_responsible').first()
    if first_detail and first_detail.action_responsible:
        main_responsible = first_detail.action_responsible.get_full_name() or first_detail.action_responsible.username

    # Délai résolution
    main_deadline = '—'
    if first_detail and first_detail.resolution_deadline:
        main_deadline = first_detail.resolution_deadline.strftime('%d/%m/%Y')

    th_s  = sty('SH',  fontSize=7.5, fontName='Helvetica-Bold', textColor=BLACK, alignment=TA_CENTER)
    td_s  = sty('SD',  fontSize=8,   textColor=BLACK)
    td_sc = sty('SDC', fontSize=8,   textColor=BLACK, alignment=TA_CENTER)
    td_sm = sty('SDM', fontSize=7.5, textColor=BLACK)

    delay_sign  = '+' if report.delay_gap_days >= 0 else ''
    # Fond noir uniquement pour un statut réellement critique/à risque (le
    # champ `weather` renseigné par le chef de projet) — jamais dérivé d'un
    # autre indicateur, pour rester fidèle à ce que le rapport affirme.
    is_critical = report.weather in ('risque', 'critique')

    synth_header = [
        Paragraph('Projet',            th_s),
        Paragraph('Chef de Projet',    th_s),
        Paragraph('Semaine',           th_s),
        Paragraph('Statut',            th_s),
        Paragraph('Avancement (%)',    th_s),
        Paragraph('Ecart delai (j)',   th_s),
        Paragraph('Top Probleme',      th_s),
        Paragraph('Action',            th_s),
        Paragraph('Responsable',       th_s),
        Paragraph('Delai',             th_s),
        Paragraph('Decision attendue', th_s),
    ]

    synth_row = [
        Paragraph(project.code,                               td_sc),
        Paragraph(pm_name,                                    td_s),
        Paragraph(f'S{report.week_number}',                   td_sc),
        Paragraph(f'<b>{weather_label}</b>',                  sty('WL', fontSize=7.5, fontName='Helvetica-Bold', textColor=(WHITE if is_critical else BLACK), alignment=TA_CENTER)),
        Paragraph(f'{report.global_progress_snapshot}%',      sty('AV', fontSize=9, fontName='Helvetica-Bold', textColor=BLACK, alignment=TA_CENTER)),
        Paragraph(f'<b>{delay_sign}{report.delay_gap_days} j</b>', sty('DG', fontSize=8, fontName='Helvetica-Bold', textColor=BLACK, alignment=TA_CENTER)),
        Paragraph(report.problems or '—',                     td_sm),
        Paragraph(report.corrective_actions or '—',           td_sm),
        Paragraph(main_responsible,                           td_sc),
        Paragraph(main_deadline,                              td_sc),
        Paragraph(report.decision_expected or '—',            td_sm),
    ]

    # Proportions d'origine (22/28/14/26/20/18/40/40/24/20/42 sur 294mm),
    # ré-appliquées à content_w pour que ce tableau s'aligne exactement avec
    # les autres tableaux de la page (en-tête, résumé, détail par activité).
    _synth_fracs = [22, 28, 14, 26, 20, 18, 40, 40, 24, 20, 42]
    col_w_synth = cols(content_w, *[v / sum(_synth_fracs) for v in _synth_fracs])

    synth_data  = [synth_header, synth_row]
    synth_table = Table(synth_data, colWidths=col_w_synth, repeatRows=1)
    synth_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0),  (-1, 0),  GREY_HEADER),
        ('FONTNAME',      (0, 0),  (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0),  (-1, -1), 7.5),
        ('VALIGN',        (0, 0),  (-1, -1), 'MIDDLE'),
        ('ALIGN',         (0, 0),  (-1, 0),  'CENTER'),
        ('BOX',           (0, 0),  (-1, -1), 0.5, BORDER),
        ('INNERGRID',     (0, 0),  (-1, -1), 0.3, BORDER),
        ('ROWBACKGROUNDS',(0, 1),  (-1, -1), [GREY_LIGHT, WHITE]),
        # Statut : fond noir (au lieu d'une couleur) si le projet est en
        # risque/critique — reste lisible sans couleur. Doit être déclaré
        # APRÈS ROWBACKGROUNDS : ReportLab applique les commandes de
        # TableStyle dans l'ordre, la dernière l'emporte sur une même cellule.
        ('BACKGROUND',    (3, 1),  (3, 1),   BLACK if is_critical else GREY_LIGHT),
        ('TEXTCOLOR',     (3, 1),  (3, 1),   WHITE if is_critical else BLACK),
        ('TOPPADDING',    (0, 0),  (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0),  (-1, -1), 4),
        ('LEFTPADDING',   (0, 0),  (-1, -1), 3),
        ('RIGHTPADDING',  (0, 0),  (-1, -1), 3),
    ]))
    elements.append(synth_table)
    elements.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════════════════════════════════════
    # 3. RESUME / PLAN SEMAINE SUIVANTE
    # ══════════════════════════════════════════════════════════════════════
    sec_label = sty('SecLabel', fontSize=8, fontName='Helvetica-Bold', textColor=BLACK)
    sec_body  = sty('SecBody',  fontSize=8, textColor=BLACK)

    summary_data = [
        [Paragraph('Resume de la semaine', sec_label), Paragraph('Plan semaine suivante', sec_label)],
        [Paragraph(report.summary or '—', sec_body),   Paragraph(report.next_week_plan or '—', sec_body)],
    ]
    summary_table = Table(summary_data, colWidths=[content_w/2, content_w/2])
    summary_table.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 0.5, BORDER),
        ('INNERGRID',     (0, 0), (-1, -1), 0.5, BORDER),
        ('BACKGROUND',    (0, 0), (-1, 0),  GREY_HEADER),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════════════════════════════════════
    # 4. TABLEAU DETAIL PAR ACTIVITE (Avancement_XXX)
    # ══════════════════════════════════════════════════════════════════════
    sec_title = sty('SecTitle', fontSize=10, fontName='Helvetica-Bold', textColor=BLACK)
    elements.append(Paragraph('DETAIL PAR ACTIVITE', sec_title))
    elements.append(Spacer(1, 2*mm))

    th_d  = sty('DH',  fontSize=6.5, fontName='Helvetica-Bold', textColor=BLACK, alignment=TA_CENTER)
    td_d  = sty('DD',  fontSize=7,   textColor=BLACK)
    td_dc = sty('DDC', fontSize=7,   textColor=BLACK, alignment=TA_CENTER)
    cell  = sty('CEL', fontSize=6.5, textColor=BLACK)

    detail_header = [
        Paragraph('N°',                   th_d),
        Paragraph('Activite principale',   th_d),
        Paragraph('Sous-activite',         th_d),
        Paragraph('Unite',                 th_d),
        Paragraph('Qte totale',            th_d),
        Paragraph('Qte realisee',          th_d),
        Paragraph('Avanc. (%)',            th_d),
        Paragraph('Poids (%)',             th_d),
        Paragraph('Avanc. reel',           th_d),
        Paragraph('Prevu (%)',             th_d),
        Paragraph('Ecart (%)',             th_d),
        Paragraph('Probleme',              th_d),
        Paragraph('Action corrective',     th_d),
        Paragraph('Responsable',           th_d),
        Paragraph('Date resolution',       th_d),
    ]

    detail_rows = [detail_header]
    gap_styles  = []

    for idx, d in enumerate(
        report.task_details.select_related('task', 'action_responsible').order_by('task__order'),
        start=1
    ):
        task     = d.task
        resp_name= '—'
        if d.action_responsible:
            resp_name = d.action_responsible.get_full_name() or d.action_responsible.username
        deadline = d.resolution_deadline.strftime('%d/%m/%Y') if d.resolution_deadline else '—'

        avanc_reel = float(d.task_progress_snapshot) * float(task.weight) / 100
        gap_val    = d.task_gap

        row_idx = idx  # row index in table (1 = header)
        if gap_val < 0:
            gap_styles.append(('FONTNAME',  (10, row_idx), (10, row_idx), 'Helvetica-Bold'))

        detail_rows.append([
            Paragraph(str(task.order or idx), td_dc),
            Paragraph(task.name,                  td_d),
            Paragraph(task.sub_activity or '—',   td_d),
            Paragraph(task.unit or '—',            td_dc),
            Paragraph(f'{float(task.total_quantity):g}',    td_dc),
            Paragraph(f'{float(d.cumulative_quantity):g}',  td_dc),
            Paragraph(f'{d.task_progress_snapshot}%',       td_dc),
            Paragraph(f'{float(task.weight):g}%',           td_dc),
            Paragraph(f'{avanc_reel:.2f}%',                 td_dc),
            Paragraph(f'{d.planned_progress}%',             td_dc),
            Paragraph(f'{gap_val:+.1f}%',                   td_dc),
            Paragraph(d.problem or '—',            cell),
            Paragraph(d.corrective_action or '—',  cell),
            Paragraph(resp_name,                   td_dc),
            Paragraph(deadline,                    td_dc),
        ])

    # Proportions d'origine, ré-appliquées à content_w — même largeur totale
    # que les autres tableaux de la page (voir col_w_synth ci-dessus).
    _detail_fracs = [8, 28, 22, 12, 16, 16, 14, 13, 15, 13, 13, 30, 30, 20, 18]
    col_w_detail = cols(content_w, *[v / sum(_detail_fracs) for v in _detail_fracs])

    style_cmds_detail = [
        ('BACKGROUND',    (0, 0),  (-1, 0),  GREY_HEADER),
        ('FONTNAME',      (0, 0),  (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0),  (-1, -1), 6.5),
        ('VALIGN',        (0, 0),  (-1, -1), 'MIDDLE'),
        ('ALIGN',         (0, 0),  (-1, 0),  'CENTER'),
        ('BOX',           (0, 0),  (-1, -1), 0.5, BORDER),
        ('INNERGRID',     (0, 0),  (-1, -1), 0.25, BORDER),
        ('ROWBACKGROUNDS',(0, 1),  (-1, -1), [WHITE, GREY_LIGHT]),
        ('TOPPADDING',    (0, 0),  (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0),  (-1, -1), 3),
        ('LEFTPADDING',   (0, 0),  (-1, -1), 2),
        ('RIGHTPADDING',  (0, 0),  (-1, -1), 2),
    ] + gap_styles

    detail_table = Table(detail_rows, colWidths=col_w_detail, repeatRows=1)
    detail_table.setStyle(TableStyle(style_cmds_detail))
    elements.append(detail_table)
    elements.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════════════════════════════════════
    # 5. PIED DE PAGE
    # ══════════════════════════════════════════════════════════════════════
    footer = sty('Footer', fontSize=7, textColor=GREY_TEXT, alignment=TA_CENTER)
    elements.append(HRFlowable(width=content_w, thickness=0.5, color=BORDER))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(
        f'Document genere par GerTrack — '
        f'Rapport S{report.week_number}/{report.year} pour {project.code} — {project.name}',
        footer
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer
