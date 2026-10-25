import { useState, useEffect, useCallback, useMemo } from 'react';
import api from '../api/axios';
import { Modal, Button, Badge } from '../design-system';

// ─────────────────────────────────────────────────────────────────────────────
// Responsable Financier (Évolution 7) — interface volontairement minimale :
// Demandes à exécuter → Voir le PDF / Exécuter → Terminé (la demande
// disparaît immédiatement de la liste, le backend ne renvoie de toute façon
// plus que les achats 'validee' — voir UnifiedRequestViewSet.get_queryset).
// Aucune visibilité sur le circuit logistique, les réceptions, les retards,
// ni les autres types de demandes.
//
// Audit UX (Évolution 7 bis) : les demandes urgentes doivent être
// immédiatement identifiables (badge fort) et apparaître avant les demandes
// standards dans la liste — voir tri ci-dessous.
// ─────────────────────────────────────────────────────────────────────────────

const Ico = ({ d, size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);
const D = {
  eye:      'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z M12 9a3 3 0 100 6 3 3 0 000-6z',
  doc:      'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z M14 2v6h6',
  check:    'M20 6L9 17l-5-5',
  refresh:  'M23 4v6h-6 M1 20v-6h6 M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15',
  alert:    'M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z M12 9v4 M12 17h.01',
};

const fmtAmount = (a) => a ? `${parseFloat(a).toLocaleString('fr-FR')} FCFA` : '–';
const fmtDate   = (d) => d ? new Date(d).toLocaleDateString('fr-FR') : '–';

// Badge délibérément plus visible que le Badge générique de l'app (utilisé
// pour "Urgent" ailleurs) — le métier demande ici une couleur forte et une
// identification immédiate, cette liste étant la priorité de l'interface.
const UrgentBadge = () => (
  <span style={S.urgentBadge}>
    <Ico d={D.alert} size={11} /> URGENT
  </span>
);

export default function FinancialExecution() {
  const [requests, setRequests] = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [flash,    setFlash]    = useState({ t: '', m: '' });

  const [detail,     setDetail]     = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const [notes,      setNotes]      = useState('');
  const [executing,  setExecuting]  = useState(false);

  const notify = (t, m) => { setFlash({ t, m }); setTimeout(() => setFlash({ t: '', m: '' }), 4000); };

  // Le backend ne renvoie déjà que les achats validés en attente
  // d'exécution pour ce rôle (voir UnifiedRequestViewSet.get_queryset) —
  // aucun filtre supplémentaire nécessaire côté client.
  const loadRequests = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/requests/');
      setRequests(res.data.results ?? res.data ?? []);
    } catch { notify('error', 'Impossible de charger les demandes.'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadRequests(); }, [loadRequests]);

  // Urgentes en premier, puis les plus anciennes validées d'abord (file
  // d'attente FIFO au sein de chaque groupe) — Évolution 7 bis, §3.
  const sortedRequests = useMemo(() => {
    return [...requests].sort((a, b) => {
      if (!!a.is_urgent !== !!b.is_urgent) return a.is_urgent ? -1 : 1;
      return new Date(a.validated_at || a.created_at) - new Date(b.validated_at || b.created_at);
    });
  }, [requests]);

  const openDetail = async (id) => {
    try {
      const res = await api.get(`/requests/${id}/`);
      setDetail(res.data);
      setNotes('');
      setShowDetail(true);
    } catch { notify('error', 'Impossible de charger la demande.'); }
  };

  const viewPdf = async (id) => {
    // La fenêtre doit être ouverte de façon SYNCHRONE dans le gestionnaire de
    // clic (avant tout await) — sinon les navigateurs bloquent l'ouverture
    // comme un pop-up non sollicité, silencieusement, une fois le blob prêt.
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

  const handleExecute = async () => {
    if (!detail) return;
    try {
      setExecuting(true);
      await api.post(`/requests/${detail.id}/execute-financial/`, { notes });
      notify('success', `${detail.reference} exécutée.`);
      setShowDetail(false);
      loadRequests();
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors de l\'exécution.');
    } finally { setExecuting(false); }
  };

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div>
          <div style={S.title}><Ico d={D.doc} size={22} /> Demandes à exécuter</div>
          <div style={S.subtitle}>Achats validés en attente d'exécution financière</div>
        </div>
        <Button variant="secondary" size="sm" onClick={loadRequests}>
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
      ) : sortedRequests.length === 0 ? (
        <div style={S.empty}>
          <div style={{ opacity: .3, marginBottom: '12px' }}><Ico d={D.check} size={48} /></div>
          <p style={{ fontSize: '15px', fontWeight: '600' }}>Aucune demande en attente</p>
          <p style={{ fontSize: '13px' }}>Toutes les demandes d'achat validées ont été exécutées.</p>
        </div>
      ) : (
        <div style={{ background: 'var(--bg-surface)', borderRadius: '12px', border: '1px solid var(--border-default)', overflow: 'hidden' }}>
          <table style={S.table}>
            <thead>
              <tr>
                {['Référence', 'Projet', 'Demandeur', 'Fournisseur', 'Montant', 'Date de validation', 'Priorité', 'Actions'].map(h => (
                  <th key={h} style={S.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedRequests.map(r => (
                <tr key={r.id}
                  style={r.is_urgent ? S.urgentRow : undefined}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background = r.is_urgent ? 'var(--danger-bg)' : 'transparent'}>
                  <td style={S.td}>
                    <span style={{ fontWeight: '700', color: 'var(--accent-light)', fontFamily: 'monospace', fontSize: '13px' }}>
                      {r.reference}
                    </span>
                  </td>
                  <td style={{ ...S.td, color: 'var(--text-secondary)' }}>{r.project_name || '–'}</td>
                  <td style={{ ...S.td, color: 'var(--text-secondary)' }}>{r.requested_by_name || '–'}</td>
                  <td style={{ ...S.td, color: 'var(--text-tertiary)' }}>{r.supplier_name || '–'}</td>
                  <td style={{ ...S.td, color: 'var(--warning)', fontWeight: '700' }}>{fmtAmount(r.total_amount)}</td>
                  <td style={{ ...S.td, color: 'var(--text-muted)', fontSize: '12px' }}>{fmtDate(r.validated_at)}</td>
                  <td style={S.td}>
                    {r.is_urgent ? <UrgentBadge /> : <Badge tone="muted">Standard</Badge>}
                  </td>
                  <td style={S.td}>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <Button variant="info" size="sm" onClick={() => viewPdf(r.id)}>
                        <Ico d={D.doc} size={13} /> Voir le PDF
                      </Button>
                      <Button variant="success" size="sm" onClick={() => openDetail(r.id)}>
                        <Ico d={D.check} size={13} /> Exécuter
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Modal Détail / Exécution ─────────────────────────────────────── */}
      <Modal
        open={showDetail && !!detail}
        onClose={() => setShowDetail(false)}
        title={detail?.reference}
        maxWidth="560px"
        footer={(
          <>
            <Button variant="secondary" onClick={() => setShowDetail(false)}>Annuler</Button>
            <Button variant="success" disabled={executing} onClick={handleExecute}>
              {executing ? 'Exécution…' : (<><Ico d={D.check} size={14} /> Exécuter</>)}
            </Button>
          </>
        )}
      >
        {detail && (
          <>
            {detail.is_urgent && (
              <div style={{ marginBottom: '14px' }}><UrgentBadge /></div>
            )}
            <div style={S.section}>
              {[
                ['Demandeur',      detail.requested_by_name],
                ['Motif',          detail.motif || '–'],
                ['Projet',         detail.project_name || '–'],
                ['Fournisseur',    detail.supplier_name || '–'],
                ['Date souhaitée', detail.date_needed ? fmtDate(detail.date_needed) : '–'],
                ['Montant total',  fmtAmount(detail.total_amount)],
              ].map(([l, v]) => (
                <div key={l} style={S.infoRow}>
                  <span style={S.infoLbl}>{l}</span>
                  <span style={S.infoVal}>{v}</span>
                </div>
              ))}
            </div>

            <div style={{ marginBottom: '16px' }}>
              <Button variant="info" onClick={() => viewPdf(detail.id)} style={{ width: '100%' }}>
                <Ico d={D.doc} size={14} /> Consulter le bon de commande (PDF)
              </Button>
            </div>

            <div style={S.fGroup}>
              <label style={S.label}>Notes d'exécution (optionnel)</label>
              <textarea style={S.textarea} placeholder="Référence de paiement, remarques…"
                value={notes} onChange={e => setNotes(e.target.value)} />
            </div>
          </>
        )}
      </Modal>
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
  urgentRow: { background: 'var(--danger-bg)' },
  urgentBadge: {
    display: 'inline-flex', alignItems: 'center', gap: '4px',
    padding: '4px 10px', borderRadius: '6px', fontSize: '0.72rem', fontWeight: 800,
    letterSpacing: '.03em', color: '#fff', background: 'var(--danger)',
    textTransform: 'uppercase', whiteSpace: 'nowrap',
  },
  section:   { marginBottom: '16px' },
  infoRow:   { display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-faint)', fontSize: '13px' },
  infoLbl:   { color: 'var(--text-muted)' },
  infoVal:   { color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' },
  fGroup:    { marginBottom: '4px' },
  label:     { display: 'block', fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: '6px' },
  textarea:  { width: '100%', padding: '9px 12px', background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '8px', color: 'var(--text-secondary)', fontSize: '13px', outline: 'none', boxSizing: 'border-box', resize: 'vertical', minHeight: '70px' },
};
