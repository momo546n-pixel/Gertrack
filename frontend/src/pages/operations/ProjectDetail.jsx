import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import api from '../../api/axios';
import toast from 'react-hot-toast';
import { Modal, Button, Badge } from '../../design-system';

const STATUS_MAP = {
  brouillon: { tone: 'muted',   label: 'Brouillon' },
  en_cours:  { tone: 'accent',  label: 'En cours'  },
  suspendu:  { tone: 'warning', label: 'Suspendu'  },
  termine:   { tone: 'success', label: 'Terminé'   },
  annule:    { tone: 'danger',  label: 'Annulé'    },
};

const WEATHER_TONE   = { ok: 'success', risque: 'warning', critique: 'danger' };
const WEATHER_LABELS = { ok: 'OK', risque: 'Risque', critique: 'Critique' };

const EF_TASK = {
  name: '', sub_activity: '', description: '', comment: '', unit: '',
  total_quantity: '', weight: '', planned_start: '', planned_end: '', order: 0,
};

// ─── Icône alerte ─────────────────────────────────────────────────────────────
const AlertIco = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
    stroke="var(--danger)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
    <line x1="12" y1="9" x2="12" y2="13"/>
    <line x1="12" y1="17" x2="12.01" y2="17"/>
  </svg>
);

export default function ProjectDetail() {
  const { id }      = useParams();
  const navigate    = useNavigate();
  const { user }    = useAuth();

  const [project,  setProject]  = useState(null);
  const [tasks,    setTasks]    = useState([]);
  const [reports,  setReports]  = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [showTask, setShowTask] = useState(false);
  const [editTask, setEditTask] = useState(null);
  const [taskForm, setTaskForm] = useState(EF_TASK);
  const [saving,   setSaving]   = useState(false);
  const [tab,      setTab]      = useState('tasks');

  // Droits
  const canManageTasks   = user?.is_project_manager;
  const canManageReports = user?.is_project_manager;
  const canChangeStatus  = user?.is_dg;
  const hasAccess        = user?.is_dg || user?.is_ops_chief || user?.is_project_manager;

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [p, t, r] = await Promise.all([
        api.get(`/operations/projects/${id}/`),
        api.get(`/operations/projects/${id}/tasks/`),
        api.get(`/operations/projects/${id}/reports/`),
      ]);
      setProject(p.data);
      setTasks(t.data.results || t.data);
      setReports(r.data.results || r.data);
    } catch {
      toast.error('Erreur de chargement ou accès non autorisé');
      navigate('/operations');
    } finally { setLoading(false); }
  }, [id, navigate]);

  useEffect(() => {
    if (!hasAccess) {
      toast.error('Accès non autorisé');
      navigate('/dashboard');
      return;
    }
    fetchAll();
  }, [hasAccess, navigate, fetchAll]);

  const openCreateTask = () => { setEditTask(null); setTaskForm(EF_TASK); setShowTask(true); };
  const openEditTask   = (t) => {
    setEditTask(t);
    setTaskForm({
      name: t.name, sub_activity: t.sub_activity || '',
      description: t.description || '', comment: t.comment || '',
      unit: t.unit || '', total_quantity: t.total_quantity,
      weight: t.weight, planned_start: t.planned_start || '',
      planned_end: t.planned_end || '', order: t.order || 0,
    });
    setShowTask(true);
  };

  const handleSaveTask = async (e) => {
    e.preventDefault(); setSaving(true);
    try {
      const payload = {
        ...taskForm,
        sub_activity:   taskForm.sub_activity || '',
        comment:        taskForm.comment || '',
        total_quantity: Number(taskForm.total_quantity),
        weight:         Number(taskForm.weight),
        order:          Number(taskForm.order) || 0,
        project:        Number(id),
        planned_start:  taskForm.planned_start || null,
        planned_end:    taskForm.planned_end   || null,
      };
      if (editTask) {
        await api.put(`/operations/tasks/${editTask.id}/`, payload);
        toast.success('Tâche modifiée');
      } else {
        await api.post('/operations/tasks/', payload);
        toast.success('Tâche ajoutée');
      }
      setShowTask(false); fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.weight?.[0] || err.response?.data?.detail || 'Erreur');
    } finally { setSaving(false); }
  };

  const handleDeleteTask = async (task) => {
    if (!window.confirm(`Supprimer la tâche "${task.name}" ?`)) return;
    try {
      await api.delete(`/operations/tasks/${task.id}/`);
      toast.success('Tâche supprimée');
      fetchAll();
    } catch (err) { toast.error(err.response?.data?.detail || 'Erreur'); }
  };

  const handleUpdateStatus = async (status) => {
    try {
      await api.patch(`/operations/projects/${id}/`, { status });
      toast.success('Statut mis à jour');
      fetchAll();
    } catch { toast.error('Erreur'); }
  };

  const handleUnblockBudget = async () => {
    try {
      await api.post(`/operations/projects/${id}/unblock-budget/`);
      toast.success('Budget débloqué');
      fetchAll();
    } catch (err) { toast.error(err.response?.data?.detail || 'Erreur'); }
  };

  const handleDownloadPdf = async (report) => {
    try {
      const res  = await api.get(`/operations/reports/${report.id}/pdf/`, { responseType: 'blob' });
      const url  = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href     = url;
      link.download = `Rapport_${project.code}_S${report.week_number}_${report.year}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
      toast.success('PDF téléchargé');
    } catch { toast.error('Erreur lors de la génération du PDF'); }
  };

  if (!hasAccess) return null;
  if (loading)    return <div style={S.loading}>Chargement...</div>;
  if (!project)   return null;

  const st          = STATUS_MAP[project.status] || STATUS_MAP.brouillon;
  const totalWeight = tasks.reduce((s, t) => s + Number(t.weight), 0);
  const progress    = project.global_progress || 0;

  // Budget
  const hasBudget      = project.budget !== null && project.budget !== undefined;
  const budgetPct      = project.budget_pourcentage || 0;
  const budgetDepasse  = project.budget_depasse || false;
  const budgetColor    = budgetDepasse ? 'var(--danger)' : budgetPct > 80 ? 'var(--warning)' : 'var(--success-light)';

  const fmtAmount = (v) =>
    v !== null && v !== undefined
      ? `${parseFloat(v).toLocaleString('fr-FR')} FCFA`
      : '–';

  return (
    <div style={S.page}>

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div style={S.header}>
        <Button variant="secondary" size="sm" style={{ marginTop: '2px' }} onClick={() => navigate('/operations')}>← Retour</Button>
        <div style={S.headerMain}>
          <div style={S.topRow}>
            <span style={S.projCode}>{project.code}</span>
            <Badge tone={st.tone}>{st.label}</Badge>
            {project.validated_by_dg
              ? <Badge tone="success">Validé</Badge>
              : <Badge tone="warning">En attente de validation</Badge>
            }
            {budgetDepasse && (
              <Badge tone="danger"><AlertIco /> BUDGET DÉPASSÉ</Badge>
            )}
            {project.is_budget_blocked && (
              <Badge tone="danger"><AlertIco /> BUDGET BLOQUÉ</Badge>
            )}
          </div>
          <h1 style={S.title}>{project.name}</h1>
          {project.client && (
            <p style={S.subtitle}>
              {project.client}{project.location ? ` — ${project.location}` : ''}
            </p>
          )}
        </div>
        <div style={S.headerActions}>
          {canChangeStatus && (
            <select style={S.statusSelect} value={project.status}
              onChange={e => handleUpdateStatus(e.target.value)}>
              <option value="brouillon">Brouillon</option>
              <option value="en_cours">En cours</option>
              <option value="suspendu">Suspendu</option>
              <option value="termine">Terminé</option>
              <option value="annule">Annulé</option>
            </select>
          )}
          {canManageReports && (
            <Button variant="primary" onClick={() => navigate(`/operations/${id}/report`)}>
              + Rapport hebdomadaire
            </Button>
          )}
        </div>
      </div>

      {/* ── Avancement global ────────────────────────────────────────────── */}
      <div style={S.progressCard}>
        <div style={S.progressInfo}>
          <div>
            <div style={S.progressLabel}>Avancement global du projet</div>
            <div style={S.progressValue}>{progress}%</div>
          </div>
          <div style={S.progressMeta}>
            {project.start_date && (
              <div style={S.metaItem}>
                <span style={S.metaLabel}>Démarrage</span>
                <span style={S.metaValue}>{new Date(project.start_date).toLocaleDateString('fr-FR')}</span>
              </div>
            )}
            {project.planned_end_date && (
              <div style={S.metaItem}>
                <span style={S.metaLabel}>Fin prévue</span>
                <span style={S.metaValue}>{new Date(project.planned_end_date).toLocaleDateString('fr-FR')}</span>
              </div>
            )}
            {project.project_manager_name && (
              <div style={S.metaItem}>
                <span style={S.metaLabel}>Chef de projet</span>
                <span style={S.metaValue}>{project.project_manager_name}</span>
              </div>
            )}
            {hasBudget && (
              <div style={S.metaItem}>
                <span style={S.metaLabel}>Budget alloué</span>
                <span style={{ ...S.metaValue, color: 'var(--accent-light)', fontWeight: '700' }}>
                  {fmtAmount(project.budget)}
                </span>
              </div>
            )}
          </div>
        </div>
        <div style={S.bigProgressBar}>
          <div style={{
            ...S.bigProgressFill,
            width: `${progress}%`,
            background: progress >= 80 ? 'var(--success-light)' : progress >= 50 ? 'var(--accent)' : 'var(--warning)',
          }} />
        </div>
        <div style={S.progressFooter}>
          <span style={{ color: 'var(--text-disabled)', fontSize: '0.75rem' }}>
            Poids total : <strong style={{ color: totalWeight === 100 ? 'var(--success-light)' : 'var(--warning)' }}>{totalWeight}%</strong>
            {totalWeight !== 100 && (
              <span style={{ color: 'var(--warning)', marginLeft: '0.5rem' }}>doit être égal à 100%</span>
            )}
          </span>
          <span style={{ color: 'var(--text-disabled)', fontSize: '0.75rem' }}>{tasks.length} tâche(s)</span>
        </div>
      </div>

      {/* ── Bloc Budget ──────────────────────────────────────────────────── */}
      {hasBudget && (
        <div style={{
          background: budgetDepasse ? 'var(--danger-bg)' : 'var(--bg-surface)',
          border: `1px solid ${budgetDepasse ? 'var(--danger)' : 'var(--border-default)'}`,
          borderRadius: '10px',
          padding: '1.25rem',
          marginBottom: '1.25rem',
        }}>
          {/* En-tête budget */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
              Budget du Projet
            </span>
            {budgetDepasse && (
              <Badge tone="danger"><AlertIco /> DÉPASSEMENT BUDGÉTAIRE</Badge>
            )}
          </div>

          {/* 3 stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '1rem' }}>
            {[
              { lbl: 'Budget Alloué',   val: project.budget,          color: 'var(--accent-light)' },
              { lbl: 'Budget Consommé', val: project.budget_consomme, color: 'var(--warning)' },
              { lbl: 'Budget Restant',  val: project.budget_restant,  color: budgetDepasse ? 'var(--danger)' : 'var(--success-light)' },
            ].map(b => (
              <div key={b.lbl} style={{
                background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)',
                borderRadius: '8px', padding: '0.875rem', textAlign: 'center',
              }}>
                <div style={{ fontSize: '1.1rem', fontWeight: '800', color: b.color, letterSpacing: '-0.5px' }}>
                  {fmtAmount(b.val)}
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-disabled)', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.5px', marginTop: '4px' }}>
                  {b.lbl}
                </div>
              </div>
            ))}
          </div>

          {/* Barre de progression budget */}
          <div style={{ marginBottom: '0.375rem' }}>
            <div style={{ background: 'var(--border-default)', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${Math.min(budgetPct, 100)}%`,
                background: budgetColor,
                borderRadius: '4px',
                transition: 'width 0.5s ease',
              }} />
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-disabled)' }}>0%</span>
            <span style={{ fontSize: '0.72rem', color: budgetColor, fontWeight: '700' }}>
              {budgetPct}% consommé
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-disabled)' }}>100%</span>
          </div>

          {/* Message dépassement */}
          {budgetDepasse && (
            <div style={{
              marginTop: '0.875rem', padding: '0.625rem 0.875rem',
              background: 'var(--danger-bg)', border: '1px solid var(--danger)',
              borderRadius: '6px', fontSize: '0.8rem', color: 'var(--danger)',
              display: 'flex', alignItems: 'center', gap: '8px',
            }}>
              <AlertIco />
              Le budget alloué est dépassé de{' '}
              <strong>{fmtAmount(Math.abs(project.budget_restant))}</strong>.
              Merci de consulter le DG pour régularisation.
            </div>
          )}

          {/* Blocage automatique du budget (Évolution 6) */}
          {project.is_budget_blocked && (
            <div style={{
              marginTop: '0.875rem', padding: '0.625rem 0.875rem',
              background: 'var(--danger-bg)', border: '1px solid var(--danger)',
              borderRadius: '6px', fontSize: '0.8rem', color: 'var(--danger)',
              display: 'flex', alignItems: 'flex-start', gap: '8px', flexWrap: 'wrap',
            }}>
              <AlertIco />
              <div style={{ flex: 1, minWidth: '200px' }}>
                <strong>Budget bloqué automatiquement</strong> — plus aucune nouvelle
                demande ne peut être liée à ce projet.
                {project.budget_block_reason && (
                  <div style={{ marginTop: '2px', opacity: 0.9 }}>{project.budget_block_reason}</div>
                )}
              </div>
              {user?.is_dg && (
                <Button variant="danger" size="sm" onClick={handleUnblockBudget}>
                  Débloquer
                </Button>
              )}
            </div>
          )}

          {/* Demandes liées — lien rapide */}
          <div style={{ marginTop: '0.875rem', textAlign: 'right' }}>
            <button
              onClick={() => navigate('/requests')}
              style={{
                background: 'none', border: 'none', color: 'var(--accent-light)',
                cursor: 'pointer', fontSize: '0.75rem', fontWeight: '600',
              }}>
              Voir les demandes liées →
            </button>
          </div>
        </div>
      )}

      {/* ── Tabs ─────────────────────────────────────────────────────────── */}
      <div style={S.tabs}>
        {[
          { key: 'tasks',   label: 'Tâches & Activités' },
          { key: 'reports', label: `Rapports hebdomadaires (${reports.length})` },
        ].map(t => (
          <button key={t.key}
            style={{ ...S.tab, ...(tab === t.key ? S.tabActive : {}) }}
            onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab: Tâches ──────────────────────────────────────────────────── */}
      {tab === 'tasks' && (
        <div>
          {canManageTasks && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.75rem' }}>
              <Button variant="primary" onClick={openCreateTask}>+ Ajouter une tâche</Button>
            </div>
          )}
          <div style={S.tableBox}>
            <table style={S.table}>
              <thead>
                <tr style={S.thead}>
                  {[
                    '#', 'Tâche', 'Unité', 'Qté totale', 'Qté réalisée',
                    'Avancement', 'Poids %', 'Contribution',
                    ...(canManageTasks ? [''] : []),
                  ].map(h => (
                    <th key={h} style={S.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tasks.length === 0 ? (
                  <tr>
                    <td colSpan={canManageTasks ? 9 : 8} style={S.empty}>
                      {canManageTasks
                        ? 'Aucune tâche — ajoutez des activités pour commencer'
                        : 'Aucune tâche enregistrée'}
                    </td>
                  </tr>
                ) : tasks.map((t, i) => (
                  <tr key={t.id} style={{ ...S.tr, background: i % 2 ? 'var(--bg-surface-alt)' : 'transparent' }}>
                    <td style={{ ...S.td, color: 'var(--text-disabled)', fontSize: '0.75rem' }}>{t.order || i + 1}</td>
                    <td style={S.td}>
                      <div style={{ fontWeight: '600', color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>{t.name}</div>
                      {t.sub_activity && (
                        <div style={{ fontSize: '0.72rem', color: 'var(--accent-light)', marginTop: '2px' }}>{t.sub_activity}</div>
                      )}
                    </td>
                    <td style={{ ...S.td, color: 'var(--text-muted)' }}>{t.unit || '—'}</td>
                    <td style={{ ...S.td, textAlign: 'right', fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>
                      {Number(t.total_quantity).toLocaleString('fr-FR')}
                    </td>
                    <td style={{ ...S.td, textAlign: 'right', fontFamily: 'monospace', color: 'var(--text-primary)', fontWeight: '600' }}>
                      {Number(t.realized_quantity).toLocaleString('fr-FR')}
                    </td>
                    <td style={{ ...S.td, minWidth: '120px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{ flex: 1, height: '4px', background: 'var(--border-default)', borderRadius: '2px', overflow: 'hidden' }}>
                          <div style={{
                            height: '100%', borderRadius: '2px',
                            width: `${t.task_progress}%`,
                            background: t.task_progress >= 80 ? 'var(--success-light)' : t.task_progress >= 50 ? 'var(--accent)' : 'var(--warning)',
                          }} />
                        </div>
                        <span style={{ fontSize: '0.72rem', fontFamily: 'monospace', color: 'var(--text-muted)', minWidth: '36px' }}>
                          {t.task_progress}%
                        </span>
                      </div>
                    </td>
                    <td style={{ ...S.td, textAlign: 'center', fontFamily: 'monospace', color: 'var(--accent-light)' }}>
                      {t.weight}%
                    </td>
                    <td style={{ ...S.td, textAlign: 'center', fontFamily: 'monospace', color: 'var(--info)' }}>
                      {t.weighted_progress}%
                    </td>
                    {canManageTasks && (
                      <td style={S.td}>
                        <div style={{ display: 'flex', gap: '0.375rem' }}>
                          <button style={S.actBtn} onClick={() => openEditTask(t)}>Modifier</button>
                          <button style={{ ...S.actBtn, color: 'var(--danger)' }} onClick={() => handleDeleteTask(t)}>Supprimer</button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
              {tasks.length > 0 && (
                <tfoot>
                  <tr style={{ background: 'var(--bg-surface-sunken)' }}>
                    <td colSpan={6} style={{ ...S.td, fontWeight: '700', color: 'var(--text-disabled)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Avancement global calculé
                    </td>
                    <td style={{ ...S.td, textAlign: 'center', fontFamily: 'monospace', color: 'var(--accent-light)', fontWeight: '700' }}>
                      {totalWeight}%
                    </td>
                    <td style={{ ...S.td, textAlign: 'center', fontFamily: 'monospace', color: 'var(--success-light)', fontWeight: '700', fontSize: '1rem' }}>
                      {progress}%
                    </td>
                    {canManageTasks && <td style={S.td}></td>}
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </div>
      )}

      {/* ── Tab: Rapports ─────────────────────────────────────────────────── */}
      {tab === 'reports' && (
        <div>
          {reports.length === 0 ? (
            <div style={{ ...S.empty, background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px' }}>
              {canManageReports
                ? 'Aucun rapport — cliquez sur "+ Rapport hebdomadaire" pour en créer un'
                : 'Aucun rapport hebdomadaire enregistré'}
            </div>
          ) : (
            <div style={S.reportList}>
              {reports.map(r => {
                const gap = r.progress_gap || 0;
                return (
                  <div key={r.id} style={S.reportCard}>
                    <div style={S.reportLeft}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.3rem' }}>
                        <span style={S.weekLabel}>Semaine {r.week_number} / {r.year}</span>
                        <Badge tone={WEATHER_TONE[r.weather] || 'muted'}>{WEATHER_LABELS[r.weather] || r.weather}</Badge>
                      </div>
                      <div style={S.reportDate}>{new Date(r.report_date).toLocaleDateString('fr-FR')}</div>
                      {r.summary && <div style={S.reportSummary}>{r.summary}</div>}
                      {r.decision_expected && (
                        <div style={S.decisionBox}>
                          <span style={S.decisionLabel}>Décision attendue</span>
                          <span style={S.decisionText}>{r.decision_expected}</span>
                        </div>
                      )}
                    </div>
                    <div style={S.reportRight}>
                      <div style={S.reportStat}>
                        <span style={S.reportStatLabel}>Réalisé</span>
                        <span style={{ ...S.reportStatValue, color: 'var(--accent-light)' }}>{r.global_progress_snapshot}%</span>
                      </div>
                      <div style={S.reportStat}>
                        <span style={S.reportStatLabel}>Prévu</span>
                        <span style={S.reportStatValue}>{r.planned_progress}%</span>
                      </div>
                      <div style={S.reportStat}>
                        <span style={S.reportStatLabel}>Écart %</span>
                        <span style={{ ...S.reportStatValue, color: gap >= 0 ? 'var(--success-light)' : 'var(--danger)' }}>
                          {gap >= 0 ? '+' : ''}{gap}%
                        </span>
                      </div>
                      <div style={S.reportStat}>
                        <span style={S.reportStatLabel}>Écart délai</span>
                        <span style={{ ...S.reportStatValue, color: r.delay_gap_days >= 0 ? 'var(--success-light)' : 'var(--danger)' }}>
                          {r.delay_gap_days >= 0 ? '+' : ''}{r.delay_gap_days} j
                        </span>
                      </div>
                      <Button variant="info" size="sm" onClick={() => handleDownloadPdf(r)}>PDF</Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Modal Tâche ───────────────────────────────────────────────────── */}
      {canManageTasks && (
        <Modal
          open={showTask}
          onClose={() => setShowTask(false)}
          title={editTask ? `Modifier — ${editTask.name}` : 'Nouvelle Tâche'}
          maxWidth="620px"
          footer={(
            <>
              <Button variant="secondary" type="button" onClick={() => setShowTask(false)}>Annuler</Button>
              <Button variant="primary" type="submit" form="task-form" disabled={saving}>
                {saving ? 'Enregistrement...' : editTask ? 'Modifier la tâche' : 'Ajouter la tâche'}
              </Button>
            </>
          )}
        >
          <form id="task-form" onSubmit={handleSaveTask}>
            <div style={S.grid2}>
              <div style={{ gridColumn: '1/-1' }}>
                <F label="Nom de la tâche *">
                  <input style={S.input} value={taskForm.name} required
                    onChange={e => setTaskForm({ ...taskForm, name: e.target.value })} />
                </F>
              </div>
              <div style={{ gridColumn: '1/-1' }}>
                <F label="Sous-activité / Tronçon">
                  <input style={S.input} placeholder="ex: PK0–PK10"
                    value={taskForm.sub_activity}
                    onChange={e => setTaskForm({ ...taskForm, sub_activity: e.target.value })} />
                </F>
              </div>
              <div style={{ gridColumn: '1/-1' }}>
                <F label="Description">
                  <textarea style={{ ...S.input, height: '55px', resize: 'vertical' }}
                    value={taskForm.description}
                    onChange={e => setTaskForm({ ...taskForm, description: e.target.value })} />
                </F>
              </div>
              <F label="Unité (m², ml, U...)">
                <input style={S.input} placeholder="ex: m², ml, U, kg"
                  value={taskForm.unit}
                  onChange={e => setTaskForm({ ...taskForm, unit: e.target.value })} />
              </F>
              <F label="Ordre d'affichage">
                <input style={S.input} type="number" min="0"
                  value={taskForm.order}
                  onChange={e => setTaskForm({ ...taskForm, order: e.target.value })} />
              </F>
              <F label="Quantité totale *">
                <input style={S.input} type="number" min="0" step="0.01" required
                  value={taskForm.total_quantity}
                  onChange={e => setTaskForm({ ...taskForm, total_quantity: e.target.value })} />
              </F>
              <F label="Poids dans le projet (%) *">
                <input style={S.input} type="number" min="0" max="100" step="0.01" required
                  placeholder="ex: 15.5"
                  value={taskForm.weight}
                  onChange={e => setTaskForm({ ...taskForm, weight: e.target.value })} />
                <span style={{ fontSize: '0.72rem', color: 'var(--text-disabled)', marginTop: '3px' }}>
                  Poids actuel total : {totalWeight.toFixed(1)}%
                  {taskForm.weight && ` → sera : ${(totalWeight + (editTask ? 0 : Number(taskForm.weight))).toFixed(1)}%`}
                </span>
              </F>
              <F label="Début planifié">
                <input style={S.input} type="date"
                  value={taskForm.planned_start}
                  onChange={e => setTaskForm({ ...taskForm, planned_start: e.target.value })} />
              </F>
              <F label="Fin planifiée">
                <input style={S.input} type="date"
                  value={taskForm.planned_end}
                  onChange={e => setTaskForm({ ...taskForm, planned_end: e.target.value })} />
              </F>
              <div style={{ gridColumn: '1/-1' }}>
                <F label="Commentaire">
                  <textarea style={{ ...S.input, height: '50px', resize: 'vertical' }}
                    placeholder="Commentaire général sur la tâche..."
                    value={taskForm.comment}
                    onChange={e => setTaskForm({ ...taskForm, comment: e.target.value })} />
                </F>
              </div>
            </div>
          </form>
        </Modal>
      )}

    </div>
  );
}

// ─── Composant Field ──────────────────────────────────────────────────────────
const F = ({ label, children }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginBottom: '0.875rem' }}>
    <label style={{ fontSize: '0.72rem', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
      {label}
    </label>
    {children}
  </div>
);

// ─── Styles ───────────────────────────────────────────────────────────────────
const S = {
  page:           { padding: '2rem 2.5rem', color: 'var(--text-secondary)' },
  loading:        { display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: 'var(--text-disabled)' },
  header:         { display: 'flex', alignItems: 'flex-start', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' },
  headerMain:     { flex: 1, minWidth: 0 },
  topRow:         { display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.35rem', flexWrap: 'wrap' },
  projCode:       { fontFamily: 'monospace', fontSize: '0.875rem', color: 'var(--accent-light)', fontWeight: '600' },
  title:          { fontSize: '1.4rem', fontWeight: '700', color: 'var(--text-primary)', letterSpacing: '-0.4px', margin: '0 0 0.2rem' },
  subtitle:       { fontSize: '0.82rem', color: 'var(--text-disabled)', margin: 0 },
  headerActions:  { display: 'flex', gap: '0.625rem', alignItems: 'center', flexShrink: 0 },
  statusSelect:   { padding: '0.5rem 0.875rem', background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '7px', fontSize: '0.83rem', color: 'var(--text-secondary)', outline: 'none', cursor: 'pointer' },

  progressCard:   { background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px', padding: '1.25rem', marginBottom: '1.25rem' },
  progressInfo:   { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' },
  progressLabel:  { fontSize: '0.7rem', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.3rem' },
  progressValue:  { fontSize: '2.5rem', fontWeight: '700', color: 'var(--accent-light)', letterSpacing: '-1px', lineHeight: 1 },
  progressMeta:   { display: 'flex', gap: '1.5rem', flexWrap: 'wrap' },
  metaItem:       { display: 'flex', flexDirection: 'column', gap: '0.15rem' },
  metaLabel:      { fontSize: '0.65rem', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '0.5px' },
  metaValue:      { fontSize: '0.83rem', color: 'var(--text-tertiary)', fontWeight: '500' },
  bigProgressBar: { height: '8px', background: 'var(--border-default)', borderRadius: '4px', overflow: 'hidden', marginBottom: '0.75rem' },
  bigProgressFill:{ height: '100%', borderRadius: '4px', transition: 'width 0.6s ease' },
  progressFooter: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },

  tabs:           { display: 'flex', gap: '0.25rem', marginBottom: '1rem', borderBottom: '1px solid var(--border-default)' },
  tab:            { padding: '0.6rem 1rem', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '0.85rem', fontWeight: '500', color: 'var(--text-disabled)', borderBottom: '2px solid transparent', marginBottom: '-1px' },
  tabActive:      { color: 'var(--accent-light)', borderBottomColor: 'var(--accent)', fontWeight: '600' },

  tableBox:       { background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px', overflow: 'auto' },
  table:          { width: '100%', borderCollapse: 'collapse', minWidth: '900px' },
  thead:          { background: 'var(--bg-surface-sunken)' },
  th:             { padding: '0.625rem 0.875rem', textAlign: 'left', fontSize: '0.68rem', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '0.6px', whiteSpace: 'nowrap' },
  tr:             { transition: 'background 0.1s' },
  td:             { padding: '0.7rem 0.875rem', fontSize: '0.83rem', borderBottom: '1px solid var(--border-faint)', color: 'var(--text-tertiary)', verticalAlign: 'middle' },
  empty:          { padding: '3rem', textAlign: 'center', color: 'var(--text-disabled)', fontSize: '0.875rem' },
  actBtn:         { background: 'none', border: 'none', color: 'var(--accent-light)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: '600', padding: '0.2rem 0.4rem', borderRadius: '4px' },

  reportList:       { display: 'flex', flexDirection: 'column', gap: '0.5rem' },
  reportCard:       { background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px', padding: '1rem 1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' },
  reportLeft:       { flex: 1 },
  weekLabel:        { fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--accent-light)', fontWeight: '600' },
  reportDate:       { fontSize: '0.75rem', color: 'var(--text-disabled)', marginTop: '0.2rem', marginBottom: '0.4rem' },
  reportSummary:    { fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.5 },
  decisionBox:      { marginTop: '0.625rem', padding: '0.5rem 0.75rem', background: 'var(--bg-surface-sunken)', border: '1px solid var(--border-default)', borderRadius: '6px', display: 'flex', flexDirection: 'column', gap: '0.2rem' },
  decisionLabel:    { fontSize: '0.65rem', fontWeight: '700', color: 'var(--info)', textTransform: 'uppercase', letterSpacing: '0.5px' },
  decisionText:     { fontSize: '0.78rem', color: 'var(--text-tertiary)' },
  reportRight:      { display: 'flex', gap: '1.25rem', flexShrink: 0, flexWrap: 'wrap', alignItems: 'center' },
  reportStat:       { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.2rem' },
  reportStatLabel:  { fontSize: '0.65rem', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '0.5px' },
  reportStatValue:  { fontSize: '1.1rem', fontWeight: '700', fontFamily: 'monospace', color: 'var(--text-tertiary)' },

  grid2:      { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 1rem' },
  input:      { padding: '0.65rem 0.875rem', background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '7px', fontSize: '0.875rem', outline: 'none', color: 'var(--text-secondary)', width: '100%', boxSizing: 'border-box' },
};
