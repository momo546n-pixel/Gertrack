import { useState, useEffect, useCallback } from 'react';
import api from '../api/axios';
import { Modal, Button, Badge } from '../design-system';

const Ico = ({ d, size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);
const D = {
  edit: 'M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7 M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z',
  unlock: 'M8 11V7a4 4 0 118 0 M3 11h14v10H3z',
  alert: 'M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z M12 9v4 M12 17h.01',
};

const fmt = (n) => Number(n || 0).toLocaleString('fr-FR');

export default function RALBudget() {
  const user  = JSON.parse(localStorage.getItem('user') || '{}');
  const isDG  = user.role === 'dg' || user.is_dg === true;
  const year  = new Date().getFullYear();

  const [budget,  setBudget]  = useState(null);
  const [loading, setLoading] = useState(true);
  const [flash,   setFlash]   = useState({ t: '', m: '' });

  const [showForm, setShowForm] = useState(false);
  const [montant,  setMontant]  = useState('');
  const [saving,   setSaving]   = useState(false);

  const notify = (t, m) => { setFlash({ t, m }); setTimeout(() => setFlash({ t: '', m: '' }), 4000); };

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get(`/requests/ral-budget/?year=${year}`);
      const data = res.data.results ?? res.data ?? [];
      setBudget(data[0] || null);
    } catch { notify('error', 'Impossible de charger le budget.'); }
    finally { setLoading(false); }
  }, [year]);

  useEffect(() => { load(); }, [load]);

  const openForm = () => { setMontant(budget ? String(budget.montant_annuel) : ''); setShowForm(true); };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (budget) {
        await api.patch(`/requests/ral-budget/${budget.id}/`, { montant_annuel: montant });
        notify('success', 'Budget modifié.');
      } else {
        await api.post('/requests/ral-budget/', { year, montant_annuel: montant });
        notify('success', 'Budget créé.');
      }
      setShowForm(false);
      load();
    } catch (err) {
      const d = err.response?.data || {};
      const first = (v) => Array.isArray(v) ? v[0] : v;
      notify('error', first(d.montant_annuel) || first(d.year) || d.detail || 'Erreur lors de l\'enregistrement.');
    } finally { setSaving(false); }
  };

  const handleUnblock = async () => {
    try {
      await api.post(`/requests/ral-budget/${budget.id}/unblock/`);
      notify('success', 'Compte débloqué — le RAL peut créer de nouvelles demandes d\'achat.');
      load();
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur.');
    }
  };

  if (loading) return <div style={S.page}><div style={S.empty}>Chargement…</div></div>;

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div>
          <div style={S.title}>Budget Annuel {isDG ? 'du RAL' : ''}</div>
          <div style={S.subtitle}>
            {isDG
              ? "Budget d'achat du Responsable Achat et Logistique — visible uniquement par vous et le RAL"
              : "Votre budget d'achat annuel — modifiable uniquement par le DG"}
          </div>
        </div>
        {isDG && (
          <Button variant="primary" onClick={openForm}>
            <Ico d={D.edit} size={15} /> {budget ? 'Modifier le budget' : 'Créer le budget'}
          </Button>
        )}
      </div>

      {flash.m && (
        <div style={S.flash(flash.t)}>
          <span>{flash.m}</span>
          <button onClick={() => setFlash({ t: '', m: '' })}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '18px' }}>×</button>
        </div>
      )}

      {!budget ? (
        <div style={S.empty}>
          <p style={{ fontSize: '15px', fontWeight: '600' }}>Aucun budget défini pour {year}</p>
          <p style={{ fontSize: '13px' }}>
            {isDG ? 'Cliquez sur "Créer le budget" pour en définir un.' : 'Le DG n\'a pas encore défini de budget pour cette année.'}
          </p>
        </div>
      ) : (
        <>
          {budget.is_creation_blocked && (
            <div style={S.alertBox}>
              <Ico d={D.alert} size={16} />
              <div>
                <strong>Création de nouvelles demandes d'achat bloquée</strong>
                <div style={{ fontSize: '12px', marginTop: '2px' }}>
                  Le budget a atteint {budget.pourcentage_consomme}% de consommation
                  {isDG ? ' — augmentez le budget ou débloquez le compte ci-dessous.' : ' — contactez le DG.'}
                </div>
              </div>
              {isDG && (
                <Button variant="warning" size="sm" onClick={handleUnblock} style={{ marginLeft: 'auto' }}>
                  <Ico d={D.unlock} size={13} /> Débloquer le compte
                </Button>
              )}
            </div>
          )}

          <div style={S.kpiRow}>
            <div style={S.kpi}>
              <span style={{ ...S.kpiVal, color: 'var(--accent-light)' }}>{fmt(budget.montant_annuel)}</span>
              <span style={S.kpiLbl}>Budget annuel (FCFA)</span>
            </div>
            <div style={S.kpi}>
              <span style={{ ...S.kpiVal, color: 'var(--warning-alt)' }}>{fmt(budget.montant_consomme)}</span>
              <span style={S.kpiLbl}>Consommé (FCFA)</span>
            </div>
            <div style={S.kpi}>
              <span style={{ ...S.kpiVal, color: budget.montant_restant < 0 ? 'var(--danger)' : 'var(--success)' }}>{fmt(budget.montant_restant)}</span>
              <span style={S.kpiLbl}>Restant (FCFA)</span>
            </div>
            <div style={S.kpi}>
              <span style={{ ...S.kpiVal, color: budget.is_threshold_reached ? 'var(--danger)' : 'var(--success)' }}>{budget.pourcentage_consomme}%</span>
              <span style={S.kpiLbl}>Consommé</span>
            </div>
          </div>

          <div style={S.progressBox}>
            <div style={S.progressBar}>
              <div style={{
                ...S.progressFill,
                width: `${Math.min(budget.pourcentage_consomme, 100)}%`,
                background: budget.pourcentage_consomme >= budget.threshold_percent ? 'var(--danger)' : budget.pourcentage_consomme >= 60 ? 'var(--warning-alt)' : 'var(--success)',
              }} />
              <div style={{ ...S.thresholdMarker, left: `${budget.threshold_percent}%` }} title={`Seuil de blocage (${budget.threshold_percent}%)`} />
            </div>
            <div style={{ display: 'flex', gap: '8px', marginTop: '10px', flexWrap: 'wrap' }}>
              {budget.is_threshold_reached && <Badge tone="danger">Seuil {budget.threshold_percent}% atteint</Badge>}
              {budget.is_manually_unblocked && <Badge tone="warningAlt">Débloqué manuellement</Badge>}
              {!budget.is_creation_blocked && <Badge tone="success">Création autorisée</Badge>}
            </div>
          </div>
        </>
      )}

      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={budget ? `Modifier le budget ${year}` : `Créer le budget ${year}`}
        maxWidth="420px"
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Annuler</Button>
            <Button variant="primary" type="submit" form="budget-form" disabled={saving}>
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </Button>
          </>
        )}
      >
        <form id="budget-form" onSubmit={handleSave}>
          <div style={S.fGroup}>
            <label style={S.label}>Budget annuel (FCFA) *</label>
            <input style={S.input} type="number" min="0" step="0.01" required
              value={montant} onChange={e => setMontant(e.target.value)} />
          </div>
        </form>
      </Modal>
    </div>
  );
}

const S = {
  page:      { padding: '28px', minHeight: '100vh', background: 'var(--bg-page)', color: 'var(--text-secondary)', fontFamily: 'var(--font-sans)' },
  header:    { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', gap: '16px', flexWrap: 'wrap' },
  title:     { fontSize: '22px', fontWeight: '700', color: 'var(--text-primary)' },
  subtitle:  { fontSize: '13px', color: 'var(--text-disabled)', marginTop: '4px', maxWidth: '520px' },
  flash:     (t) => ({ padding: '12px 16px', borderRadius: '8px', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', ...(t === 'success' ? { background: 'var(--success-bg)', border: '1px solid var(--success)', color: 'var(--success)' } : { background: 'var(--danger-bg)', border: '1px solid var(--danger)', color: 'var(--danger)' }) }),
  empty:     { textAlign: 'center', padding: '60px', color: 'var(--text-disabled)' },
  alertBox:  { display: 'flex', alignItems: 'flex-start', gap: '10px', padding: '14px 16px', borderRadius: '10px', background: 'var(--danger-bg)', border: '1px solid var(--danger)', color: 'var(--danger)', marginBottom: '20px' },
  kpiRow:    { display: 'flex', gap: '1px', marginBottom: '20px', background: 'var(--border-subtle)', borderRadius: '10px', overflow: 'hidden', flexWrap: 'wrap' },
  kpi:       { flex: '1 1 160px', padding: '16px 20px', background: 'var(--bg-surface)', display: 'flex', flexDirection: 'column', gap: '4px' },
  kpiVal:    { fontSize: '22px', fontWeight: '800', letterSpacing: '-0.5px', lineHeight: 1 },
  kpiLbl:    { fontSize: '11px', fontWeight: '700', color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '0.5px' },
  progressBox: { background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px', padding: '18px 20px' },
  progressBar: { position: 'relative', height: '14px', background: 'var(--bg-surface-alt)', borderRadius: '7px', overflow: 'hidden' },
  progressFill:{ height: '100%', borderRadius: '7px', transition: 'width 300ms ease' },
  thresholdMarker: { position: 'absolute', top: 0, bottom: 0, width: '2px', background: 'var(--text-disabled)' },
  fGroup:    { marginBottom: '16px' },
  label:     { display: 'block', fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: '6px' },
  input:     { width: '100%', padding: '9px 12px', background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '8px', color: 'var(--text-secondary)', fontSize: '13px', outline: 'none', boxSizing: 'border-box' },
};
