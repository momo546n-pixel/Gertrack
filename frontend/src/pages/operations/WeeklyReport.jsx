import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../api/axios';
import toast from 'react-hot-toast';
import { Button } from '../../design-system';

function getWeekNumber(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
}

const F = ({ label, children }) => (
  <div style={{ display:'flex', flexDirection:'column', gap:'0.4rem', marginBottom:'0.875rem' }}>
    <label style={{ fontSize:'0.7rem', fontWeight:'600', color:'var(--text-disabled)', textTransform:'uppercase', letterSpacing:'1px' }}>{label}</label>
    {children}
  </div>
);

export default function WeeklyReport() {
  const { id }   = useParams();
  const navigate = useNavigate();
  const today    = new Date();
  const weekNum  = getWeekNumber(today);

  const [project,     setProject]     = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [saving,      setSaving]      = useState(false);
  const [taskDetails, setTaskDetails] = useState([]);

  const [form, setForm] = useState({
    week_number:        weekNum,
    year:               today.getFullYear(),
    report_date:        today.toISOString().split('T')[0],
    planned_progress:   0,
    delay_gap_days:     0,
    weather:            'ok',
    summary:            '',
    problems:           '',
    corrective_actions: '',
    decision_expected:  '',
    next_week_plan:     '',
  });

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [p, t] = await Promise.all([
        api.get(`/operations/projects/${id}/`),
        api.get(`/operations/projects/${id}/tasks/`),
      ]);
      setProject(p.data);
      const tasks = t.data.results || t.data;
      setTaskDetails(tasks.map(task => ({
        task:                   task.id,
        task_name:              task.name,
        task_sub_activity:      task.sub_activity || '',
        task_unit:              task.unit || '',
        task_total:             task.total_quantity,
        task_current:           task.realized_quantity,
        task_weight:            task.weight,
        task_progress:          task.task_progress,
        quantity_this_week:     0,
        cumulative_quantity:    task.realized_quantity,
        task_progress_snapshot: task.task_progress,
        planned_progress:       0,
        problem:                '',
        corrective_action:      '',
        resolution_deadline:    '',
      })));
    } catch { toast.error('Erreur'); navigate(`/operations/${id}`); }
    finally { setLoading(false); }
  }, [id, navigate]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const updateDetail = (idx, field, value) => {
    const updated = [...taskDetails];
    updated[idx] = { ...updated[idx], [field]: value };
    if (field === 'quantity_this_week') {
      const cumul = Number(updated[idx].task_current) + Number(value);
      const progress = updated[idx].task_total > 0
        ? Math.min((cumul / Number(updated[idx].task_total)) * 100, 100) : 0;
      updated[idx].cumulative_quantity    = cumul;
      updated[idx].task_progress_snapshot = Math.round(progress * 100) / 100;
    }
    setTaskDetails(updated);
  };

  const computedProgress = taskDetails.reduce((sum, d) =>
    sum + (d.task_progress_snapshot * Number(d.task_weight)) / 100, 0);

  const handleSubmit = async (e) => {
    e.preventDefault(); setSaving(true);
    try {
      await api.post(`/operations/projects/${id}/weekly-report/`, {
        week_number:              Number(form.week_number),
        year:                     Number(form.year),
        report_date:              form.report_date,
        planned_progress:         Number(form.planned_progress),
        delay_gap_days:           Number(form.delay_gap_days) || 0,
        global_progress_snapshot: Math.round(computedProgress * 100) / 100,
        weather:                  form.weather,
        summary:                  form.summary,
        problems:                 form.problems,
        corrective_actions:       form.corrective_actions,
        decision_expected:        form.decision_expected,
        next_week_plan:           form.next_week_plan,
        task_details: taskDetails.map(d => ({
          task:                    Number(d.task),
          quantity_this_week:      Number(d.quantity_this_week)    || 0,
          cumulative_quantity:     Number(d.cumulative_quantity)   || 0,
          task_progress_snapshot:  Number(d.task_progress_snapshot)|| 0,
          planned_progress:        Number(d.planned_progress)       || 0,
          problem:                 d.problem             || '',
          corrective_action:       d.corrective_action   || '',
          resolution_deadline:     d.resolution_deadline || null,
        })),
      });
      toast.success('Rapport enregistré');
      navigate(`/operations/${id}`);
    } catch (err) {
      const d = err.response?.data;
      if (d?.non_field_errors) toast.error(d.non_field_errors[0]);
      else toast.error("Erreur lors de l'enregistrement");
      console.error(err.response?.data);
    } finally { setSaving(false); }
  };

  if (loading) return <div style={S.loading}>Chargement...</div>;
  if (!project) return null;

  const gap = computedProgress - Number(form.planned_progress);

  const WEATHER_CONFIG = {
    ok:       { label:'OK — Dans les délais'         },
    risque:   { label:'Risque — Vigilance requise'   },
    critique: { label:'Critique — Action urgente'    },
  };

  return (
    <div style={S.page}>
      <div style={S.header}>
        <Button variant="secondary" size="sm" style={{ marginTop: '2px' }} onClick={() => navigate(`/operations/${id}`)}>← Retour</Button>
        <div>
          <h1 style={S.title}>Rapport hebdomadaire</h1>
          <p style={S.sub}>{project.code} — {project.name}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>

        {/* Infos du rapport */}
        <div style={S.section}>
          <div style={S.sectionTitle}>Informations du rapport</div>
          <div style={S.grid5}>
            <F label="Semaine *">
              <input style={S.input} type="number" min="1" max="53"
                value={form.week_number} onChange={e => setForm({...form, week_number:e.target.value})} required />
            </F>
            <F label="Année *">
              <input style={S.input} type="number"
                value={form.year} onChange={e => setForm({...form, year:e.target.value})} required />
            </F>
            <F label="Date *">
              <input style={S.input} type="date"
                value={form.report_date} onChange={e => setForm({...form, report_date:e.target.value})} required />
            </F>
            <F label="Avancement prévu (%)">
              <input style={S.input} type="number" min="0" max="100" step="0.1"
                value={form.planned_progress} onChange={e => setForm({...form, planned_progress:e.target.value})} />
            </F>
            <F label="Écart délai (j)">
              <input style={S.input} placeholder="-5 ou +3" type="number"
                value={form.delay_gap_days} onChange={e => setForm({...form, delay_gap_days:e.target.value})} />
            </F>
          </div>
        </div>

        {/* Avancement calculé */}
        <div style={S.progressCard}>
          <div style={S.progressRow}>
            <div style={S.progressStat}>
              <div style={S.progLabel}>Avancement réel calculé</div>
              <div style={{ ...S.progValue, color:'var(--accent-light)' }}>{computedProgress.toFixed(2)}%</div>
            </div>
            <div style={S.progressStat}>
              <div style={S.progLabel}>Avancement prévu</div>
              <div style={S.progValue}>{form.planned_progress}%</div>
            </div>
            <div style={S.progressStat}>
              <div style={S.progLabel}>Écart</div>
              <div style={{ ...S.progValue, color: gap >= 0 ? 'var(--success-light)' : 'var(--danger)' }}>
                {gap >= 0 ? '+':''}{gap.toFixed(2)}%
              </div>
            </div>
            <div style={S.progressStat}>
              <div style={S.progLabel}>Statut</div>
              <select style={{ ...S.input, maxWidth:'220px', padding:'0.5rem 0.875rem', cursor: 'pointer' }}
                value={form.weather} onChange={e => setForm({...form, weather:e.target.value})}>
                {Object.entries(WEATHER_CONFIG).map(([k, v]) => (
                  <option key={k} value={k}>{v.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div style={S.bigBar}>
            <div style={{ ...S.bigBarFill, width:`${Math.min(computedProgress,100)}%`,
              background: computedProgress >= 80 ? 'var(--success-light)' : computedProgress >= 50 ? 'var(--accent)' : 'var(--warning)' }} />
          </div>
        </div>

        {/* Tableau suivi des tâches */}
        <div style={S.section}>
          <div style={S.sectionTitle}>Suivi par tâche — Semaine {form.week_number}</div>
          <div style={{ overflow:'auto' }}>
            <table style={S.table}>
              <thead>
                <tr style={S.thead}>
                  {['Tâche','Unité','Qté totale','Qté S-1','Qté semaine','Qté cumulée',
                    'Avanc. réel %','Prévu %','Écart %','Problème','Action corrective','Délai résolution'].map(h => (
                    <th key={h} style={S.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {taskDetails.map((detail, idx) => {
                  const taskGap = detail.task_progress_snapshot - Number(detail.planned_progress);
                  return (
                    <tr key={detail.task} style={{ ...S.tr, background: idx%2 ? 'var(--bg-surface-alt)' : '' }}>
                      <td style={{ ...S.td, minWidth:'140px' }}>
                        <div style={{ fontWeight:'600', color:'var(--text-tertiary)', fontSize:'0.82rem' }}>{detail.task_name}</div>
                        {detail.task_sub_activity && <div style={{ fontSize:'0.7rem', color:'var(--accent-light)', marginTop:'2px' }}>{detail.task_sub_activity}</div>}
                      </td>
                      <td style={{ ...S.td, color:'var(--text-disabled)' }}>{detail.task_unit || '—'}</td>
                      <td style={{ ...S.td, textAlign:'right', fontFamily:'monospace', color:'var(--text-disabled)' }}>
                        {Number(detail.task_total).toLocaleString('fr-FR')}
                      </td>
                      <td style={{ ...S.td, textAlign:'right', fontFamily:'monospace', color:'var(--text-disabled)' }}>
                        {Number(detail.task_current).toLocaleString('fr-FR')}
                      </td>
                      <td style={{ ...S.td, minWidth:'100px' }}>
                        <input style={S.cellInput} type="number" min="0" step="0.01"
                          value={detail.quantity_this_week}
                          onChange={e => updateDetail(idx, 'quantity_this_week', e.target.value)} />
                      </td>
                      <td style={{ ...S.td, textAlign:'right', fontFamily:'monospace', color:'var(--text-primary)', fontWeight:'700' }}>
                        {Number(detail.cumulative_quantity).toLocaleString('fr-FR')}
                      </td>
                      <td style={{ ...S.td, textAlign:'center', fontFamily:'monospace', fontWeight:'700',
                        color: detail.task_progress_snapshot >= 80 ? 'var(--success-light)' : detail.task_progress_snapshot >= 50 ? 'var(--accent-light)' : 'var(--warning)' }}>
                        {detail.task_progress_snapshot}%
                      </td>
                      <td style={{ ...S.td, minWidth:'80px' }}>
                        <input style={{ ...S.cellInput, textAlign:'center' }} type="number" min="0" max="100" step="0.1"
                          value={detail.planned_progress}
                          onChange={e => updateDetail(idx, 'planned_progress', e.target.value)} />
                      </td>
                      <td style={{ ...S.td, textAlign:'center', fontFamily:'monospace', fontWeight:'700',
                        color: taskGap >= 0 ? 'var(--success-light)' : 'var(--danger)' }}>
                        {taskGap >= 0 ? '+':''}{taskGap.toFixed(1)}%
                      </td>
                      <td style={{ ...S.td, minWidth:'150px' }}>
                        <input style={S.cellInput} placeholder="Problème..."
                          value={detail.problem}
                          onChange={e => updateDetail(idx, 'problem', e.target.value)} />
                      </td>
                      <td style={{ ...S.td, minWidth:'150px' }}>
                        <input style={S.cellInput} placeholder="Action corrective..."
                          value={detail.corrective_action}
                          onChange={e => updateDetail(idx, 'corrective_action', e.target.value)} />
                      </td>
                      <td style={{ ...S.td, minWidth:'120px' }}>
                        <input style={S.cellInput} type="date"
                          value={detail.resolution_deadline}
                          onChange={e => updateDetail(idx, 'resolution_deadline', e.target.value)} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Commentaires */}
        <div style={S.section}>
          <div style={S.sectionTitle}>Commentaires & Décisions</div>
          <div style={S.grid2}>
            <F label="Résumé de la semaine">
              <textarea style={{ ...S.input, height:'90px', resize:'vertical' }}
                value={form.summary} onChange={e => setForm({...form, summary:e.target.value})} />
            </F>
            <F label="Plan semaine suivante">
              <textarea style={{ ...S.input, height:'90px', resize:'vertical' }}
                value={form.next_week_plan} onChange={e => setForm({...form, next_week_plan:e.target.value})} />
            </F>
            <F label="Top problème">
              <textarea style={{ ...S.input, height:'90px', resize:'vertical' }}
                value={form.problems} onChange={e => setForm({...form, problems:e.target.value})} />
            </F>
            <F label="Action corrective proposée">
              <textarea style={{ ...S.input, height:'90px', resize:'vertical' }}
                value={form.corrective_actions} onChange={e => setForm({...form, corrective_actions:e.target.value})} />
            </F>
            <div style={{ gridColumn:'1/-1' }}>
              <F label="Décision attendue">
                <textarea style={{ ...S.input, height:'70px', resize:'vertical' }}
                  placeholder="Quelle décision est nécessaire..."
                  value={form.decision_expected} onChange={e => setForm({...form, decision_expected:e.target.value})} />
              </F>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={S.footer}>
          <Button variant="secondary" type="button" onClick={() => navigate(`/operations/${id}`)}>Annuler</Button>
          <Button variant="primary" type="submit" disabled={saving}>
            {saving ? 'Enregistrement...' : 'Enregistrer le rapport'}
          </Button>
        </div>
      </form>
    </div>
  );
}

const S = {
  page:         { color:'var(--text-secondary)', maxWidth:'1600px' },
  loading:      { display:'flex', alignItems:'center', justifyContent:'center', height:'60vh', color:'var(--text-disabled)' },
  header:       { display:'flex', alignItems:'flex-start', gap:'1rem', marginBottom:'1.5rem' },
  title:        { fontSize:'1.5rem', fontWeight:'700', color:'var(--text-primary)', margin:'0 0 0.2rem', letterSpacing:'-0.4px' },
  sub:          { fontSize:'0.82rem', color:'var(--text-disabled)' },
  section:      { background:'var(--bg-surface)', border:'1px solid var(--border-default)', borderRadius:'10px', padding:'1.25rem', marginBottom:'1rem' },
  sectionTitle: { fontSize:'0.7rem', fontWeight:'700', color:'var(--text-disabled)', textTransform:'uppercase', letterSpacing:'1px', marginBottom:'1rem' },
  grid5:        { display:'grid', gridTemplateColumns:'repeat(5,1fr)', gap:'0 1rem' },
  grid2:        { display:'grid', gridTemplateColumns:'1fr 1fr', gap:'0 1rem' },
  progressCard: { background:'var(--bg-surface)', border:'1px solid var(--border-default)', borderRadius:'10px', padding:'1.25rem', marginBottom:'1rem' },
  progressRow:  { display:'flex', gap:'2rem', alignItems:'flex-end', marginBottom:'1rem', flexWrap:'wrap' },
  progressStat: { display:'flex', flexDirection:'column', gap:'0.3rem' },
  progLabel:    { fontSize:'0.68rem', fontWeight:'700', color:'var(--text-disabled)', textTransform:'uppercase', letterSpacing:'0.5px' },
  progValue:    { fontSize:'1.75rem', fontWeight:'800', letterSpacing:'-0.5px', lineHeight:1, color:'var(--text-tertiary)' },
  bigBar:       { height:'6px', background:'var(--border-default)', borderRadius:'3px', overflow:'hidden' },
  bigBarFill:   { height:'100%', borderRadius:'3px', transition:'width 0.3s ease' },
  table:        { width:'100%', borderCollapse:'collapse', minWidth:'1200px' },
  thead:        { background:'var(--bg-surface-sunken)' },
  th:           { padding:'0.5rem 0.625rem', textAlign:'left', fontSize:'0.65rem', fontWeight:'700', color:'var(--text-disabled)', textTransform:'uppercase', letterSpacing:'0.5px', whiteSpace:'nowrap', borderBottom:'1px solid var(--border-default)' },
  tr:           {},
  td:           { padding:'0.5rem 0.625rem', fontSize:'0.82rem', borderBottom:'1px solid var(--border-faint)', color:'var(--text-tertiary)', verticalAlign:'middle' },
  cellInput:    { width:'100%', padding:'0.4rem 0.5rem', background:'var(--bg-surface-alt)', border:'1px solid var(--border-default)', borderRadius:'5px', fontSize:'0.8rem', color:'var(--text-secondary)', boxSizing:'border-box', outline:'none' },
  input:        { padding:'0.65rem 0.875rem', background:'var(--bg-surface-alt)', border:'1px solid var(--border-default)', borderRadius:'7px', fontSize:'0.875rem', color:'var(--text-secondary)', width:'100%', boxSizing:'border-box', outline:'none' },
  footer:       { display:'flex', justifyContent:'flex-end', gap:'0.75rem', paddingTop:'0.5rem' },
};
