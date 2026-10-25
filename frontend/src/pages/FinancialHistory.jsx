import { useState, useEffect, useCallback } from 'react';
import api from '../api/axios';
import { Button, Badge } from '../design-system';

// ─────────────────────────────────────────────────────────────────────────────
// Responsable Financier (Évolution 7 bis — audit UX) — historique en lecture
// seule de ses propres exécutions financières. Réutilise le même endpoint
// que le KPI du Dashboard (/requests/financial-history/, voir
// UnifiedRequestViewSet.financial_history) — le backend ne renvoie déjà que
// les achats exécutés PAR cet utilisateur, aucun filtre supplémentaire
// nécessaire côté client.
// ─────────────────────────────────────────────────────────────────────────────

const Ico = ({ d, size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);
const D = {
  doc:      'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z M14 2v6h6',
  check:    'M20 6L9 17l-5-5',
  refresh:  'M23 4v6h-6 M1 20v-6h6 M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15',
  alert:    'M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z M12 9v4 M12 17h.01',
};

const fmtAmount = (a) => a ? `${parseFloat(a).toLocaleString('fr-FR')} FCFA` : '–';
const fmtDate   = (d) => d ? new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '–';

// Même badge "fort" que FinancialExecution.jsx pour le même concept (achat
// urgent) — les deux pages doivent rester visuellement cohérentes.
const UrgentBadge = () => (
  <span style={S.urgentBadge}>
    <Ico d={D.alert} size={11} /> URGENT
  </span>
);

export default function FinancialHistory() {
  const [requests, setRequests] = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [flash,    setFlash]    = useState({ t: '', m: '' });

  const notify = (t, m) => { setFlash({ t, m }); setTimeout(() => setFlash({ t: '', m: '' }), 4000); };

  const loadHistory = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/requests/financial-history/');
      setRequests(res.data.results ?? res.data ?? []);
    } catch { notify('error', "Impossible de charger l'historique."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  const viewPdf = async (id) => {
    // Ouverture synchrone (avant tout await) — voir FinancialExecution.jsx.
    const win = window.open('', '_blank');
    try {
      const res = await api.get(`/requests/${id}/pdf-preview/`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      if (win) win.location.href = url;
    } catch {
      if (win) win.close();
      notify('error', 'Impossible d\'afficher le bon de commande.');
    }
  };

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div>
          <div style={S.title}><Ico d={D.check} size={22} /> Historique des exécutions</div>
          <div style={S.subtitle}>Achats que vous avez exécutés financièrement</div>
        </div>
        <Button variant="secondary" size="sm" onClick={loadHistory}>
          <Ico d={D.refresh} size={13} />
        </Button>
      </div>

      {flash.m && (
        <div style={S.flash(flash.t)}>
          <span>{flash.m}</span>
          <button onClick={() => setFlash({ t: '', m: '' })}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '18px' }}>×</button>
        </div>
      )}

      {loading ? (
        <div style={S.empty}>Chargement…</div>
      ) : requests.length === 0 ? (
        <div style={S.empty}>
          <p style={{ fontSize: '15px', fontWeight: '600' }}>Aucune exécution pour l'instant</p>
          <p style={{ fontSize: '13px' }}>Les demandes que vous exécutez apparaîtront ici.</p>
        </div>
      ) : (
        <div style={{ background: 'var(--bg-surface)', borderRadius: '12px', border: '1px solid var(--border-default)', overflow: 'hidden' }}>
          <table style={S.table}>
            <thead>
              <tr>
                {['Référence', 'Projet', 'Demandeur', 'Fournisseur', 'Montant', 'Priorité', 'Date d\'exécution', 'Actions'].map(h => (
                  <th key={h} style={S.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {requests.map(r => (
                <tr key={r.id}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <td style={S.td}>
                    <span style={{ fontWeight: '700', color: 'var(--accent-light)', fontFamily: 'monospace', fontSize: '13px' }}>
                      {r.reference}
                    </span>
                  </td>
                  <td style={{ ...S.td, color: 'var(--text-secondary)' }}>{r.project_name || '–'}</td>
                  <td style={{ ...S.td, color: 'var(--text-secondary)' }}>{r.requested_by_name || '–'}</td>
                  <td style={{ ...S.td, color: 'var(--text-tertiary)' }}>{r.supplier_name || '–'}</td>
                  <td style={{ ...S.td, color: 'var(--warning)', fontWeight: '700' }}>{fmtAmount(r.total_amount)}</td>
                  <td style={S.td}>
                    {r.is_urgent ? <UrgentBadge /> : <Badge tone="muted">Standard</Badge>}
                  </td>
                  <td style={{ ...S.td, color: 'var(--text-muted)', fontSize: '12px' }}>{fmtDate(r.financial_execution_at)}</td>
                  <td style={S.td}>
                    <Button variant="info" size="sm" onClick={() => viewPdf(r.id)}>
                      <Ico d={D.doc} size={13} /> Voir le PDF
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const S = {
  page:      { padding: '28px', minHeight: '100vh', background: 'var(--bg-page)', color: 'var(--text-secondary)', fontFamily: 'var(--font-sans)' },
  header:    { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' },
  title:     { fontSize: '22px', fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' },
  subtitle:  { fontSize: '13px', color: 'var(--text-disabled)', marginTop: '4px' },
  flash:     (t) => ({ padding: '12px 16px', borderRadius: '8px', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', ...(t === 'success' ? { background: 'var(--success-bg)', border: '1px solid var(--success)', color: 'var(--success)' } : { background: 'var(--danger-bg)', border: '1px solid var(--danger)', color: 'var(--danger)' }) }),
  empty:     { textAlign: 'center', padding: '60px', color: 'var(--text-disabled)' },
  table:     { width: '100%', borderCollapse: 'collapse', fontSize: '13px' },
  th:        { padding: '10px 14px', background: 'var(--bg-surface-alt)', color: 'var(--text-disabled)', fontWeight: '700', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '.05em', textAlign: 'left', borderBottom: '1px solid var(--border-default)' },
  td:        { padding: '12px 14px', borderBottom: '1px solid var(--border-faint)', verticalAlign: 'middle' },
  urgentBadge: {
    display: 'inline-flex', alignItems: 'center', gap: '4px',
    padding: '4px 10px', borderRadius: '6px', fontSize: '0.72rem', fontWeight: 800,
    letterSpacing: '.03em', color: '#fff', background: 'var(--danger)',
    textTransform: 'uppercase', whiteSpace: 'nowrap',
  },
};
