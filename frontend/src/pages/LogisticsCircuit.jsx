import { useState, useEffect, useCallback } from 'react';
import api from '../api/axios';
import { Modal, Button, Badge } from '../design-system';

// ─── Icons ────────────────────────────────────────────────────────────────────
const Ico = ({ d, size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);
const D = {
  plus:   'M12 5v14M5 12h14',
  up:     'M18 15l-6-6-6 6',
  down:   'M6 9l6 6 6-6',
  edit:   'M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7 M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z',
  trash:  'M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6',
  flag:   'M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z M4 22V15',
  check:  'M20 6L9 17l-5-5',
};

const TYPE_TABS = [
  { value: 'achat',      label: 'Achat' },
  { value: 'entree',     label: 'Entrée Stock' },
  { value: 'sortie',     label: 'Sortie Stock' },
  { value: 'ajustement', label: 'Ajustement Stock' },
];

const emptyForm = { code: '', label: '', is_reception_stage: false, is_closing_stage: false };

export default function LogisticsCircuit() {
  const [activeType, setActiveType] = useState('achat');
  const [stages,     setStages]     = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [flash,      setFlash]      = useState({ t: '', m: '' });

  const [showForm, setShowForm] = useState(false);
  const [editing,  setEditing]  = useState(null);
  const [form,     setForm]     = useState(emptyForm);
  const [saving,   setSaving]   = useState(false);

  const notify = (t, m) => { setFlash({ t, m }); setTimeout(() => setFlash({ t: '', m: '' }), 4000); };

  const loadStages = useCallback(async (type) => {
    try {
      setLoading(true);
      const res = await api.get(`/requests/logistics-stages/?request_type=${type}`);
      const data = res.data.results ?? res.data ?? [];
      setStages(data.slice().sort((a, b) => a.order - b.order));
    } catch { notify('error', 'Impossible de charger le circuit logistique.'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadStages(activeType); }, [activeType, loadStages]);

  const openCreate = () => { setEditing(null); setForm(emptyForm); setShowForm(true); };
  const openEdit   = (stage) => {
    setEditing(stage);
    setForm({
      code: stage.code, label: stage.label,
      is_reception_stage: stage.is_reception_stage, is_closing_stage: stage.is_closing_stage,
    });
    setShowForm(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editing) {
        await api.patch(`/requests/logistics-stages/${editing.id}/`, {
          label: form.label,
          is_reception_stage: form.is_reception_stage,
          is_closing_stage: form.is_closing_stage,
        });
        notify('success', 'Étape modifiée.');
      } else {
        await api.post('/requests/logistics-stages/', {
          request_type: activeType, code: form.code, label: form.label,
          order: stages.length,
          is_reception_stage: form.is_reception_stage, is_closing_stage: form.is_closing_stage,
        });
        notify('success', 'Étape créée.');
      }
      setShowForm(false);
      loadStages(activeType);
    } catch (err) {
      const d = err.response?.data || {};
      const first = (v) => Array.isArray(v) ? v[0] : v;
      notify('error', first(d.code) || first(d.label) || d.detail || 'Erreur lors de l\'enregistrement.');
    } finally { setSaving(false); }
  };

  const handleToggleActive = async (stage) => {
    try {
      await api.patch(`/requests/logistics-stages/${stage.id}/`, { is_active: !stage.is_active });
      notify('success', stage.is_active ? 'Étape désactivée.' : 'Étape activée.');
      loadStages(activeType);
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur.');
    }
  };

  const handleDelete = async (stage) => {
    if (!window.confirm(`Supprimer définitivement l'étape "${stage.label}" ?`)) return;
    try {
      await api.delete(`/requests/logistics-stages/${stage.id}/`);
      notify('success', 'Étape supprimée.');
      loadStages(activeType);
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Impossible de supprimer cette étape.');
    }
  };

  const move = async (index, direction) => {
    const target = index + direction;
    if (target < 0 || target >= stages.length) return;
    const reordered = stages.slice();
    [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
    setStages(reordered);
    try {
      await api.post('/requests/logistics-stages/reorder/', {
        request_type: activeType, stage_ids: reordered.map(s => s.id),
      });
    } catch {
      notify('error', 'Impossible de réordonner le circuit.');
      loadStages(activeType);
    }
  };

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div>
          <div style={S.title}>Circuit Logistique</div>
          <div style={S.subtitle}>
            Étapes de suivi après validation d'une demande — réservé au Responsable Achat et Logistique
          </div>
        </div>
        <Button variant="primary" onClick={openCreate}>
          <Ico d={D.plus} size={15} /> Nouvelle étape
        </Button>
      </div>

      {flash.m && (
        <div style={S.flash(flash.t)}>
          <span>{flash.m}</span>
          <button onClick={() => setFlash({ t: '', m: '' })}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '18px' }}>×</button>
        </div>
      )}

      <div style={S.tabs}>
        {TYPE_TABS.map(t => (
          <button key={t.value} style={S.tab(t.value === activeType)} onClick={() => setActiveType(t.value)}>
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={S.empty}>Chargement…</div>
      ) : stages.length === 0 ? (
        <div style={S.empty}>
          <p style={{ fontSize: '15px', fontWeight: '600' }}>Aucune étape configurée pour ce type de demande</p>
          <p style={{ fontSize: '13px' }}>Cliquez sur "Nouvelle étape" pour construire le circuit.</p>
        </div>
      ) : (
        <div style={S.list}>
          {stages.map((s, i) => (
            <div key={s.id} style={{ ...S.row, opacity: s.is_active ? 1 : .5 }}>
              <div style={S.moveCol}>
                <button style={S.moveBtn} disabled={i === 0} onClick={() => move(i, -1)}><Ico d={D.up} size={14} /></button>
                <button style={S.moveBtn} disabled={i === stages.length - 1} onClick={() => move(i, 1)}><Ico d={D.down} size={14} /></button>
              </div>
              <div style={S.orderBadge}>{i + 1}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={S.rowLabel}>{s.label}</div>
                <div style={S.rowCode}>{s.code}</div>
              </div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {s.is_reception_stage && <Badge tone="info"><Ico d={D.flag} size={11} /> Réception</Badge>}
                {s.is_closing_stage && <Badge tone="success"><Ico d={D.check} size={11} /> Clôture</Badge>}
                {!s.is_active && <Badge tone="muted">Inactive</Badge>}
              </div>
              <div style={S.actions}>
                <Button variant="secondary" size="sm" onClick={() => openEdit(s)}><Ico d={D.edit} size={13} /></Button>
                <Button variant="secondary" size="sm" onClick={() => handleToggleActive(s)}>
                  {s.is_active ? 'Désactiver' : 'Activer'}
                </Button>
                <Button variant="danger" size="sm" onClick={() => handleDelete(s)}><Ico d={D.trash} size={13} /></Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Créer/Modifier */}
      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editing ? `Modifier — ${editing.label}` : 'Nouvelle étape'}
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Annuler</Button>
            <Button variant="primary" type="submit" form="stage-form" disabled={saving}>
              {saving ? 'Enregistrement…' : editing ? 'Enregistrer' : 'Créer'}
            </Button>
          </>
        )}
      >
        <form id="stage-form" onSubmit={handleSave}>
          <div style={S.fGroup}>
            <label style={S.label}>Libellé affiché *</label>
            <input style={S.input} value={form.label} required
              onChange={e => setForm(p => ({ ...p, label: e.target.value }))} />
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Code technique *</label>
            <input style={S.input} value={form.code} required disabled={!!editing}
              placeholder="ex: reception_magasin"
              onChange={e => setForm(p => ({ ...p, code: e.target.value.toLowerCase().replace(/\s+/g, '_') }))} />
            {editing && (
              <p style={S.hint}>Le code n'est modifiable qu'à la création, pour ne pas perturber les demandes déjà à cette étape.</p>
            )}
          </div>
          <label style={S.checkRow}>
            <input type="checkbox" checked={form.is_reception_stage}
              onChange={e => setForm(p => ({ ...p, is_reception_stage: e.target.checked }))} />
            Étape de réception (déclenche l'entrée en stock ou la confirmation chantier)
          </label>
          <label style={S.checkRow}>
            <input type="checkbox" checked={form.is_closing_stage}
              onChange={e => setForm(p => ({ ...p, is_closing_stage: e.target.checked }))} />
            Étape de clôture (fin du circuit)
          </label>
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
  tabs:      { display: 'flex', gap: '6px', marginBottom: '20px', flexWrap: 'wrap' },
  tab:       (active) => ({
    padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '600', cursor: 'pointer',
    border: `1px solid ${active ? 'var(--accent)' : 'var(--border-default)'}`,
    background: active ? 'var(--accent-bg)' : 'var(--bg-surface)',
    color: active ? 'var(--accent-light)' : 'var(--text-tertiary)',
  }),
  list:      { display: 'flex', flexDirection: 'column', gap: '8px' },
  row:       { display: 'flex', alignItems: 'center', gap: '14px', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px', padding: '12px 16px' },
  moveCol:   { display: 'flex', flexDirection: 'column', gap: '2px' },
  moveBtn:   { background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '5px', color: 'var(--text-tertiary)', cursor: 'pointer', padding: '2px' },
  orderBadge:{ width: '26px', height: '26px', borderRadius: '50%', background: 'var(--accent-bg)', color: 'var(--accent-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: '700', flexShrink: 0 },
  rowLabel:  { fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' },
  rowCode:   { fontSize: '11px', color: 'var(--text-disabled)', fontFamily: 'monospace', marginTop: '2px' },
  actions:   { display: 'flex', gap: '6px', flexShrink: 0 },
  empty:     { textAlign: 'center', padding: '60px', color: 'var(--text-disabled)' },
  fGroup:    { marginBottom: '16px' },
  label:     { display: 'block', fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: '6px' },
  input:     { width: '100%', padding: '9px 12px', background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '8px', color: 'var(--text-secondary)', fontSize: '13px', outline: 'none', boxSizing: 'border-box' },
  hint:      { fontSize: '11px', color: 'var(--text-disabled)', marginTop: '6px' },
  checkRow:  { display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-tertiary)', marginBottom: '12px', cursor: 'pointer' },
};
