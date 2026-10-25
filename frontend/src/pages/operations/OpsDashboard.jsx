import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api/axios';
import toast from 'react-hot-toast';
import { Button, Badge } from '../../design-system';

const TONE = {
  muted:   { c: 'var(--text-muted)',    bg: 'var(--muted-bg)' },
  accent:  { c: 'var(--accent-light)',  bg: 'var(--accent-bg)' },
  warning: { c: 'var(--warning)',       bg: 'var(--warning-bg)' },
  success: { c: 'var(--success-light)', bg: 'var(--success-bg)' },
  danger:  { c: 'var(--danger)',        bg: 'var(--danger-bg)' },
};

const STATUS_MAP = {
  brouillon: { tone: 'muted',   label: 'Brouillon' },
  en_cours:  { tone: 'accent',  label: 'En cours'  },
  suspendu:  { tone: 'warning', label: 'Suspendu'  },
  termine:   { tone: 'success', label: 'Terminé'   },
  annule:    { tone: 'danger',  label: 'Annulé'    },
};

const WEATHER_TONE   = { ok: 'success', risque: 'warning', critique: 'danger' };
const WEATHER_LABELS = { ok: 'OK', risque: 'Risque', critique: 'Critique' };

export default function OpsDashboard() {
  const navigate      = useNavigate();
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await api.get('/operations/projects/dashboard/');
      setData(res.data);
    } catch { toast.error('Erreur de chargement'); }
    finally { setLoading(false); }
  };

  if (loading) return <div style={S.loading}>Chargement...</div>;
  if (!data) return null;

  const { projects, alerts, summary } = data;

  return (
    <div style={S.page}>

      <div style={S.header}>
        <div>
          <h1 style={S.title}>Suivi des Projets</h1>
          <p style={S.sub}>Vue consolidée — {summary.total} projet(s) actif(s)</p>
        </div>
        <Button variant="primary" onClick={() => navigate('/operations')}>
          Tous les projets
        </Button>
      </div>

      {/* KPIs */}
      <div style={S.kpiRow}>
        {[
          { label: 'Total projets',   value: summary.total,       tone: 'accent'  },
          { label: 'Dans les délais', value: summary.on_schedule, tone: 'success' },
          { label: 'En retard',       value: summary.delayed,     tone: 'warning' },
          { label: 'Critiques',       value: summary.critical,    tone: 'danger'  },
          { label: 'À risque',        value: summary.risk,        tone: 'warning' },
        ].map(k => (
          <div key={k.label} style={S.kpi}>
            <span style={{ ...S.kpiVal, color: TONE[k.tone].c }}>{k.value}</span>
            <span style={S.kpiLbl}>{k.label}</span>
          </div>
        ))}
      </div>

      {/* Alertes */}
      {alerts.length > 0 && (
        <div style={S.alertBanner}>
          <div style={S.alertHead}>
            <span style={S.alertTitle}>Projets nécessitant attention</span>
            <span style={S.alertCount}>{alerts.length}</span>
          </div>
          <div style={S.alertList}>
            {alerts.map(p => (
              <div key={p.id} style={S.alertItem} onClick={() => navigate(`/operations/${p.id}`)}>
                <div style={S.alertLeft}>
                  <span style={S.alertCode}>{p.code}</span>
                  <span style={S.alertName}>{p.name}</span>
                  {p.last_report?.decision_expected && (
                    <span style={S.alertDecision}>Décision : {p.last_report.decision_expected}</span>
                  )}
                </div>
                <div style={S.alertRight}>
                  <Badge tone={WEATHER_TONE[p.last_report.weather]}>{WEATHER_LABELS[p.last_report.weather]}</Badge>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.82rem', fontWeight: '700', color: p.last_report.progress_gap >= 0 ? 'var(--success-light)' : 'var(--danger)' }}>
                    {p.last_report.progress_gap >= 0 ? '+' : ''}{p.last_report.progress_gap}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Liste projets */}
      <div style={S.sectionTitle}>Tous les projets</div>
      <div style={S.projectList}>
        {projects.length === 0 ? (
          <div style={S.empty}>Aucun projet actif</div>
        ) : projects.map(p => {
          const st = STATUS_MAP[p.status] || STATUS_MAP.brouillon;
          return (
            <div key={p.id} style={S.projectCard} onClick={() => navigate(`/operations/${p.id}`)}>
              <div style={S.cardLeft}>
                <div style={S.cardTopRow}>
                  <span style={S.projCode}>{p.code}</span>
                  <Badge tone={st.tone}>{st.label}</Badge>
                  {p.last_report && (
                    <Badge tone={WEATHER_TONE[p.last_report.weather]}>{WEATHER_LABELS[p.last_report.weather]}</Badge>
                  )}
                </div>
                <div style={S.projName}>{p.name}</div>
                <div style={S.projMeta}>
                  {p.client && <span>{p.client}</span>}
                  {p.project_manager_name && <><span style={S.sep}>·</span><span>Chef : {p.project_manager_name}</span></>}
                  {p.planned_end_date && <><span style={S.sep}>·</span><span>Fin : {new Date(p.planned_end_date).toLocaleDateString('fr-FR')}</span></>}
                  {p.last_report && <><span style={S.sep}>·</span><span>Rapport : S{p.last_report.week_number}/{p.last_report.year}</span></>}
                </div>
                <div style={S.progressArea}>
                  <div style={S.progressBar}>
                    <div style={{ ...S.progressFill, width: `${p.global_progress}%`, background: p.global_progress >= 80 ? 'var(--success-light)' : p.global_progress >= 50 ? 'var(--accent)' : 'var(--warning)' }} />
                  </div>
                  <span style={S.progressText}>{p.global_progress}%</span>
                </div>
              </div>
              {p.last_report && (
                <div style={S.cardRight}>
                  <div style={S.statBox}>
                    <span style={S.statLabel}>Écart</span>
                    <span style={{ ...S.statValue, color: p.last_report.progress_gap >= 0 ? 'var(--success-light)' : 'var(--danger)' }}>
                      {p.last_report.progress_gap >= 0 ? '+' : ''}{p.last_report.progress_gap}%
                    </span>
                  </div>
                  <div style={S.statBox}>
                    <span style={S.statLabel}>Délai</span>
                    <span style={{ ...S.statValue, color: p.last_report.delay_gap_days >= 0 ? 'var(--success-light)' : 'var(--danger)' }}>
                      {p.last_report.delay_gap_days >= 0 ? '+' : ''}{p.last_report.delay_gap_days}j
                    </span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const S = {
  page:        { color: 'var(--text-secondary)' },
  loading:     { display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-disabled)' },
  header:      { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' },
  title:       { fontSize: '1.6rem', fontWeight: '700', color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.4px' },
  sub:         { fontSize: '0.8rem', color: 'var(--text-disabled)', marginTop: '0.25rem' },
  kpiRow:      { display: 'flex', gap: '1px', marginBottom: '1.25rem', background: 'var(--border-default)', borderRadius: '8px', overflow: 'hidden' },
  kpi:         { flex: 1, padding: '0.875rem 1.25rem', background: 'var(--bg-surface)', display: 'flex', flexDirection: 'column', gap: '0.25rem' },
  kpiVal:      { fontSize: '1.6rem', fontWeight: '800', letterSpacing: '-1px', lineHeight: 1 },
  kpiLbl:      { fontSize: '0.65rem', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '0.5px' },
  alertBanner: { background: 'var(--danger-bg)', border: '1px solid var(--danger)', borderRadius: '10px', padding: '1rem 1.25rem', marginBottom: '1.5rem' },
  alertHead:   { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' },
  alertTitle:  { fontSize: '0.85rem', fontWeight: '700', color: 'var(--danger)' },
  alertCount:  { background: 'var(--danger)', color: '#fff', borderRadius: '50%', width: '22px', height: '22px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: '700' },
  alertList:   { display: 'flex', flexDirection: 'column', gap: '0.5rem' },
  alertItem:   { display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-surface)', borderRadius: '8px', padding: '0.75rem 1rem', cursor: 'pointer', gap: '1rem', border: '1px solid var(--border-default)' },
  alertLeft:   { display: 'flex', flexDirection: 'column', gap: '0.15rem', flex: 1, minWidth: 0 },
  alertCode:   { fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--accent-light)', fontWeight: '600' },
  alertName:   { fontSize: '0.85rem', color: 'var(--text-tertiary)', fontWeight: '500' },
  alertDecision:{ fontSize: '0.72rem', color: 'var(--info)' },
  alertRight:  { display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 },
  sectionTitle:{ fontSize: '0.7rem', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '0.75rem' },
  projectList: { display: 'flex', flexDirection: 'column', gap: '0.625rem' },
  empty:       { padding: '3rem', textAlign: 'center', color: 'var(--text-disabled)', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px' },
  projectCard: { background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px', padding: '1.1rem 1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', cursor: 'pointer' },
  cardLeft:    { flex: 1, minWidth: 0 },
  cardTopRow:  { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem', flexWrap: 'wrap' },
  projCode:    { fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--accent-light)', fontWeight: '600' },
  projName:    { fontSize: '0.95rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '0.3rem' },
  projMeta:    { display: 'flex', gap: '0.4rem', fontSize: '0.78rem', color: 'var(--text-disabled)', flexWrap: 'wrap', alignItems: 'center', marginBottom: '0.75rem' },
  sep:         { color: 'var(--border-default)' },
  progressArea:{ display: 'flex', alignItems: 'center', gap: '0.75rem', maxWidth: '400px' },
  progressBar: { flex: 1, height: '5px', background: 'var(--border-default)', borderRadius: '3px', overflow: 'hidden' },
  progressFill:{ height: '100%', borderRadius: '3px', transition: 'width 0.4s ease' },
  progressText:{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-disabled)', fontFamily: 'monospace', minWidth: '38px', textAlign: 'right' },
  cardRight:   { display: 'flex', gap: '1rem', flexShrink: 0 },
  statBox:     { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.2rem' },
  statLabel:   { fontSize: '0.65rem', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '0.5px' },
  statValue:   { fontSize: '1.1rem', fontWeight: '700', fontFamily: 'monospace' },
};
