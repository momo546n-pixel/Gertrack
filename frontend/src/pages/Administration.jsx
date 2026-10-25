import { useState, useEffect, useCallback } from 'react';
import api from '../api/axios';
import { Modal, Button, Badge } from '../design-system';

// ─── Icons ────────────────────────────────────────────────────────────────────
const ShieldIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  </svg>
);
const WarehouseIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
);
const UsersIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 00-3-3.87"/>
    <path d="M16 3.13a4 4 0 010 7.75"/>
  </svg>
);
const PlusIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
);
const EditIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
  </svg>
);
const TrashIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
    <path d="M10 11v6M14 11v6"/>
    <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/>
  </svg>
);
const KeyIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
  </svg>
);
const EyeIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
    <circle cx="12" cy="12" r="3"/>
  </svg>
);

// ─── Styles ───────────────────────────────────────────────────────────────────
const S = {
  page:         { padding: '28px', minHeight: '100vh', background: 'var(--bg-page)', color: 'var(--text-secondary)', fontFamily: 'var(--font-sans)' },
  header:       { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' },
  title:        { display: 'flex', alignItems: 'center', gap: '10px', fontSize: '22px', fontWeight: '700', color: 'var(--text-primary)' },
  subtitle:     { fontSize: '13px', color: 'var(--text-disabled)', marginTop: '4px' },
  tabs:         { display: 'flex', gap: '8px', marginBottom: '24px', borderBottom: '1px solid var(--border-default)' },
  tab:          (active) => ({ padding: '10px 18px', fontSize: '13px', fontWeight: '600', cursor: 'pointer', color: active ? 'var(--accent-light)' : 'var(--text-muted)', borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent', display: 'flex', alignItems: 'center', gap: '8px' }),
  grid:         { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '20px' },
  card:         { background: 'var(--bg-surface)', borderRadius: '12px', border: '1px solid var(--border-default)', overflow: 'hidden' },
  cardHead:     { padding: '18px 20px', borderBottom: '1px solid var(--border-default)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' },
  cardBody:     { padding: '14px 20px' },
  cardFoot:     { padding: '12px 20px', borderTop: '1px solid var(--border-default)', display: 'flex', gap: '8px', justifyContent: 'flex-end', flexWrap: 'wrap' },
  iconBox:      { width: '44px', height: '44px', borderRadius: '10px', background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-light)' },
  codeBadge:    { display: 'inline-block', fontSize: '11px', fontWeight: '700', color: 'var(--accent-light)', background: 'var(--accent-bg)', padding: '2px 8px', borderRadius: '4px', letterSpacing: '.05em', marginTop: '4px' },
  statRow:      { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid var(--border-faint)' },
  statLabel:    { fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' },
  statVal:      (color) => ({ fontSize: '13px', fontWeight: '700', color: color || 'var(--text-secondary)' }),
  flash:        (type) => ({ padding: '12px 16px', borderRadius: '8px', fontSize: '13px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', ...(type === 'success' ? { background: 'var(--success-bg)', border: '1px solid var(--success)', color: 'var(--success)' } : { background: 'var(--danger-bg)', border: '1px solid var(--danger)', color: 'var(--danger)' }) }),
  label:        { display: 'block', fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: '6px' },
  input:        { width: '100%', padding: '10px 12px', background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '8px', color: 'var(--text-secondary)', fontSize: '14px', outline: 'none', boxSizing: 'border-box' },
  fGroup:       { marginBottom: '16px' },
  empty:        { textAlign: 'center', padding: '60px 20px', color: 'var(--text-disabled)' },
  section:      { marginBottom: '22px' },
  sTitle:       { fontSize: '11px', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: '10px', paddingBottom: '6px', borderBottom: '1px solid var(--border-default)' },
  infoRow:      { display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-faint)', fontSize: '13px' },
  infoLbl:      { color: 'var(--text-muted)' },
  infoVal:      { color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' },
  miniTable:    { width: '100%', borderCollapse: 'collapse', fontSize: '12px' },
  miniTh:       { padding: '6px 8px', background: 'var(--bg-surface-alt)', color: 'var(--text-disabled)', fontWeight: '700', fontSize: '10px', textTransform: 'uppercase', textAlign: 'left', borderBottom: '1px solid var(--border-default)' },
  miniTd:       { padding: '7px 8px', borderBottom: '1px solid var(--border-faint)', color: 'var(--text-tertiary)' },
  emptySection: { fontSize: '12px', color: 'var(--text-disabled)', padding: '8px 0' },
};

const fmtDate     = (d) => d ? new Date(d).toLocaleDateString('fr-FR') : '–';
const fmtDateTime  = (d) => d ? new Date(d).toLocaleString('fr-FR') : 'Jamais';

// ─── Composant Principal ──────────────────────────────────────────────────────
const Administration = () => {
  const [tab,     setTab]     = useState('magasiniers'); // 'magasiniers' | 'chefsprojet'
  const [items,   setItems]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [flash,   setFlash]   = useState({ type: '', msg: '' });

  const [showCreate,   setShowCreate]   = useState(false);
  const [showEdit,     setShowEdit]     = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showDetail,   setShowDetail]   = useState(false);
  const [selected,     setSelected]     = useState(null);

  const emptyForm = { username: '', first_name: '', last_name: '', email: '', phone: '', password: '' };
  const [form, setForm] = useState(emptyForm);
  const [newPassword, setNewPassword] = useState('');

  // Fiche détaillée / historique d'activité
  const [detailTab,      setDetailTab]      = useState(''); // fixe le rôle de la fiche ouverte
  const [activity,       setActivity]       = useState(null);
  const [activityLoading,setActivityLoading]= useState(false);

  const endpoint = tab === 'magasiniers' ? '/accounts/magasiniers/' : '/accounts/project-managers/';

  const notify = (type, msg) => {
    setFlash({ type, msg });
    setTimeout(() => setFlash({ type: '', msg: '' }), 4000);
  };

  const loadItems = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get(endpoint);
      const data = res.data.results ?? res.data;
      setItems(Array.isArray(data) ? data : []);
    } catch {
      notify('error', 'Impossible de charger les comptes.');
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => { loadItems(); }, [loadItems]);

  const resetForm = () => setForm(emptyForm);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.post(endpoint, {
        username: form.username, first_name: form.first_name, last_name: form.last_name,
        email: form.email, phone: form.phone, password: form.password,
      });
      notify('success', 'Compte créé avec succès.');
      setShowCreate(false);
      resetForm();
      loadItems();
    } catch (err) {
      notify('error', err.response?.data?.password?.[0] || err.response?.data?.detail || 'Erreur lors de la création.');
    }
  };

  const handleEdit = async (e) => {
    e.preventDefault();
    try {
      await api.patch(`${endpoint}${selected.id}/`, {
        first_name: form.first_name, last_name: form.last_name,
        email: form.email, phone: form.phone,
        ...(tab === 'magasiniers' ? { username: form.username } : {}),
      });
      notify('success', 'Compte modifié avec succès.');
      setShowEdit(false);
      resetForm();
      loadItems();
    } catch (err) {
      notify('error', err.response?.data?.username?.[0] || err.response?.data?.detail || 'Erreur lors de la modification.');
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (newPassword.length < 6) { notify('error', 'Mot de passe de 6 caractères minimum requis.'); return; }
    try {
      await api.post(`${endpoint}${selected.id}/reset-password/`, { password: newPassword });
      notify('success', 'Mot de passe réinitialisé.');
      setShowPassword(false);
      setNewPassword('');
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors de la réinitialisation.');
    }
  };

  const handleDeactivate = async (item) => {
    if (!window.confirm(`Désactiver le compte de "${item.full_name}" ?`)) return;
    try {
      await api.post(`${endpoint}${item.id}/deactivate/`);
      notify('success', 'Compte désactivé.');
      loadItems();
    } catch { notify('error', 'Erreur lors de la désactivation.'); }
  };

  const handleReactivate = async (item) => {
    try {
      await api.post(`${endpoint}${item.id}/reactivate/`);
      notify('success', 'Compte réactivé.');
      loadItems();
    } catch { notify('error', 'Erreur lors de la réactivation.'); }
  };

  const handleDelete = async (item) => {
    if (!window.confirm(`Supprimer définitivement le compte de "${item.full_name}" ? Cette action est irréversible.`)) return;
    try {
      await api.delete(`${endpoint}${item.id}/`);
      notify('success', 'Compte supprimé définitivement.');
      loadItems();
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors de la suppression.');
    }
  };

  const openEdit = (item) => {
    setSelected(item);
    setForm({ ...emptyForm, username: item.username, first_name: item.first_name || '', last_name: item.last_name || '', email: item.email || '', phone: item.phone || '' });
    setShowEdit(true);
  };

  const openPassword = (item) => {
    setSelected(item);
    setNewPassword('');
    setShowPassword(true);
  };

  const openDetail = async (item) => {
    setSelected(item);
    setDetailTab(tab);
    setShowDetail(true);
    setActivity(null);
    setActivityLoading(true);
    try {
      const res = await api.get(`${endpoint}${item.id}/activity/`);
      setActivity(res.data);
    } catch {
      notify('error', "Impossible de charger l'historique d'activité.");
    } finally {
      setActivityLoading(false);
    }
  };

  const switchTab = (t) => {
    setTab(t);
    setItems([]);
    setLoading(true);
  };

  if (loading) return (
    <div style={S.page}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px', color: 'var(--text-disabled)' }}>
        Chargement…
      </div>
    </div>
  );

  return (
    <div style={S.page}>

      {/* Header */}
      <div style={S.header}>
        <div>
          <div style={S.title}><ShieldIcon size={22} /> Gestion des comptes</div>
          <div style={S.subtitle}>Comptes magasiniers et chefs de projet — accès, statut et historique d'activité</div>
        </div>
        {tab === 'chefsprojet' && (
          <Button variant="primary" onClick={() => { resetForm(); setShowCreate(true); }}>
            <PlusIcon /> Nouveau Chef de Projet
          </Button>
        )}
      </div>

      {/* Flash */}
      {flash.msg && (
        <div style={S.flash(flash.type)}>
          <span>{flash.msg}</span>
          <button onClick={() => setFlash({ type: '', msg: '' })} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '18px', lineHeight: 1 }}>×</button>
        </div>
      )}

      {/* Tabs */}
      <div style={S.tabs}>
        <div style={S.tab(tab === 'magasiniers')} onClick={() => switchTab('magasiniers')}>
          <WarehouseIcon size={16} /> Magasiniers
        </div>
        <div style={S.tab(tab === 'chefsprojet')} onClick={() => switchTab('chefsprojet')}>
          <UsersIcon size={16} /> Chefs de Projet
        </div>
      </div>

      {tab === 'magasiniers' && (
        <p style={{ fontSize: '12px', color: 'var(--text-disabled)', marginTop: '-12px', marginBottom: '20px' }}>
          Un compte magasinier se crée depuis le module <strong style={{ color: 'var(--text-muted)' }}>Magasins</strong>, pas ici — directement par le DG, ou via une demande que le DG valide.
        </p>
      )}

      {/* Grid */}
      {items.length === 0 ? (
        <div style={S.empty}>
          <div style={{ opacity: .35, display: 'flex', justifyContent: 'center', marginBottom: '16px' }}>
            {tab === 'magasiniers' ? <WarehouseIcon size={52} /> : <UsersIcon size={52} />}
          </div>
          <p style={{ fontSize: '15px', fontWeight: '600' }}>
            {tab === 'magasiniers' ? 'Aucun compte magasinier configuré' : 'Aucun chef de projet configuré'}
          </p>
        </div>
      ) : (
        <div style={S.grid}>
          {items.map(item => (
            <div key={item.id} style={S.card}>
              <div style={S.cardHead}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                    <span style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)' }}>{item.full_name}</span>
                    <Badge tone={item.is_active ? 'success' : 'danger'}>{item.is_active ? 'Actif' : 'Inactif'}</Badge>
                  </div>
                  <span style={S.codeBadge}>{item.username}</span>
                </div>
                <div style={S.iconBox}>
                  {tab === 'magasiniers' ? <WarehouseIcon size={22} /> : <UsersIcon size={22} />}
                </div>
              </div>

              <div style={S.cardBody}>
                {tab === 'magasiniers' && (
                  <div style={S.statRow}>
                    <span style={S.statLabel}>Magasin</span>
                    <span style={S.statVal()}>{item.warehouse_name ? `${item.warehouse_name} (${item.warehouse_code})` : '— Non assigné'}</span>
                  </div>
                )}
                {item.phone && (
                  <div style={S.statRow}>
                    <span style={S.statLabel}>Téléphone</span>
                    <span style={S.statVal()}>{item.phone}</span>
                  </div>
                )}
                {item.email && (
                  <div style={S.statRow}>
                    <span style={S.statLabel}>Email</span>
                    <span style={S.statVal()}>{item.email}</span>
                  </div>
                )}
                <div style={S.statRow}>
                  <span style={S.statLabel}>Créé le</span>
                  <span style={S.statVal()}>{fmtDate(item.date_joined)}</span>
                </div>
                <div style={{ ...S.statRow, borderBottom: 'none' }}>
                  <span style={S.statLabel}>Dernière connexion</span>
                  <span style={S.statVal()}>{fmtDateTime(item.last_login)}</span>
                </div>
              </div>

              <div style={S.cardFoot}>
                <Button variant="secondary" size="sm" onClick={() => openDetail(item)}>
                  <EyeIcon size={14} /> Voir la fiche
                </Button>
                <Button variant="secondary" size="sm" onClick={() => openEdit(item)}>
                  <EditIcon size={14} /> Modifier
                </Button>
                <Button variant="secondary" size="sm" onClick={() => openPassword(item)}>
                  <KeyIcon size={14} /> Mot de passe
                </Button>
                {item.is_active ? (
                  <Button variant="warning" size="sm" onClick={() => handleDeactivate(item)}>
                    Désactiver
                  </Button>
                ) : (
                  <Button variant="success" size="sm" onClick={() => handleReactivate(item)}>
                    Réactiver
                  </Button>
                )}
                <Button variant="danger" size="sm" onClick={() => handleDelete(item)}>
                  <TrashIcon size={14} /> Supprimer
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Modal Créer (Chefs de Projet uniquement — les comptes de magasin se
           créent depuis le module Magasins, jamais indépendamment) ─────────── */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Nouveau Chef de Projet"
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setShowCreate(false)}>Annuler</Button>
            <Button variant="primary" type="submit" form="admin-create-form">Créer le compte</Button>
          </>
        )}
      >
        <form id="admin-create-form" onSubmit={handleCreate}>
          <div style={S.fGroup}>
            <label style={S.label}>Identifiant *</label>
            <input style={S.input} type="text" value={form.username}
              onChange={e => setForm(p => ({ ...p, username: e.target.value }))} required />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={S.fGroup}>
              <label style={S.label}>Prénom</label>
              <input style={S.input} type="text" value={form.first_name}
                onChange={e => setForm(p => ({ ...p, first_name: e.target.value }))} />
            </div>
            <div style={S.fGroup}>
              <label style={S.label}>Nom</label>
              <input style={S.input} type="text" value={form.last_name}
                onChange={e => setForm(p => ({ ...p, last_name: e.target.value }))} />
            </div>
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Téléphone</label>
            <input style={S.input} type="text" value={form.phone}
              onChange={e => setForm(p => ({ ...p, phone: e.target.value }))} />
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Email</label>
            <input style={S.input} type="email" value={form.email}
              onChange={e => setForm(p => ({ ...p, email: e.target.value }))} />
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Mot de passe *</label>
            <input style={S.input} type="text" placeholder="6 caractères minimum" value={form.password}
              onChange={e => setForm(p => ({ ...p, password: e.target.value }))} required />
          </div>
        </form>
      </Modal>

      {/* ── Modal Modifier ───────────────────────────────────────────────────── */}
      <Modal
        open={showEdit && !!selected}
        onClose={() => setShowEdit(false)}
        title={selected ? `Modifier — ${selected.full_name}` : 'Modifier'}
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setShowEdit(false)}>Annuler</Button>
            <Button variant="primary" type="submit" form="admin-edit-form">Enregistrer</Button>
          </>
        )}
      >
        <form id="admin-edit-form" onSubmit={handleEdit}>
          <div style={S.fGroup}>
            <label style={S.label}>Identifiant{tab === 'magasiniers' ? ' *' : ''}</label>
            {tab === 'magasiniers' ? (
              <input style={S.input} type="text" value={form.username}
                onChange={e => setForm(p => ({ ...p, username: e.target.value }))} required />
            ) : (
              <input style={{ ...S.input, opacity: .6 }} type="text" value={form.username} disabled />
            )}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={S.fGroup}>
              <label style={S.label}>Prénom</label>
              <input style={S.input} type="text" value={form.first_name}
                onChange={e => setForm(p => ({ ...p, first_name: e.target.value }))} />
            </div>
            <div style={S.fGroup}>
              <label style={S.label}>Nom</label>
              <input style={S.input} type="text" value={form.last_name}
                onChange={e => setForm(p => ({ ...p, last_name: e.target.value }))} />
            </div>
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Téléphone</label>
            <input style={S.input} type="text" value={form.phone}
              onChange={e => setForm(p => ({ ...p, phone: e.target.value }))} />
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Email</label>
            <input style={S.input} type="email" value={form.email}
              onChange={e => setForm(p => ({ ...p, email: e.target.value }))} />
          </div>
        </form>
      </Modal>

      {/* ── Modal Réinitialiser mot de passe ─────────────────────────────────── */}
      <Modal
        open={showPassword && !!selected}
        onClose={() => setShowPassword(false)}
        title={selected ? `Réinitialiser — ${selected.full_name}` : 'Réinitialiser'}
        maxWidth="420px"
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setShowPassword(false)}>Annuler</Button>
            <Button variant="primary" type="submit" form="admin-password-form">Réinitialiser</Button>
          </>
        )}
      >
        <form id="admin-password-form" onSubmit={handleResetPassword}>
          <div style={S.fGroup}>
            <label style={S.label}>Nouveau mot de passe *</label>
            <input style={S.input} type="text" placeholder="6 caractères minimum" value={newPassword}
              onChange={e => setNewPassword(e.target.value)} required />
          </div>
        </form>
      </Modal>

      {/* ── Modal Fiche détaillée ─────────────────────────────────────────────── */}
      <Modal
        open={showDetail && !!selected}
        onClose={() => setShowDetail(false)}
        title={selected ? `Fiche — ${selected.full_name}` : 'Fiche'}
        maxWidth="760px"
        footer={<Button variant="secondary" onClick={() => setShowDetail(false)}>Fermer</Button>}
      >
        {selected && (
          <>
            <div style={{ marginTop: '-8px', marginBottom: '16px' }}>
              <Badge tone={selected.is_active ? 'success' : 'danger'}>{selected.is_active ? 'Actif' : 'Inactif'}</Badge>
            </div>

            {/* Informations générales */}
            <div style={S.section}>
              <div style={S.sTitle}>Informations générales</div>
              {[
                ['Identifiant',           selected.username],
                ['Rôle',                 detailTab === 'magasiniers' ? 'Magasinier' : 'Chef de Projet'],
                ...(detailTab === 'magasiniers' ? [['Magasin', selected.warehouse_name ? `${selected.warehouse_name} (${selected.warehouse_code})` : '— Non assigné']] : []),
                ['Téléphone',            selected.phone || '–'],
                ['Email',                selected.email || '–'],
                ['Créé le',              fmtDate(selected.date_joined)],
                ['Dernière connexion',   fmtDateTime(selected.last_login)],
              ].map(([l, v]) => (
                <div key={l} style={S.infoRow}>
                  <span style={S.infoLbl}>{l}</span>
                  <span style={S.infoVal}>{v}</span>
                </div>
              ))}
            </div>

            {activityLoading ? (
              <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-disabled)' }}>Chargement de l'historique…</div>
            ) : activity && detailTab === 'magasiniers' ? (
              <>
                <RequestSection title="Entrées"     items={activity.entrees} />
                <RequestSection title="Sorties"      items={activity.sorties} />
                <RequestSection title="Ajustements"  items={activity.ajustements} />
              </>
            ) : activity && detailTab === 'chefsprojet' ? (
              <>
                <div style={S.section}>
                  <div style={S.sTitle}>Projets ({activity.projets.length})</div>
                  {activity.projets.length === 0 ? <div style={S.emptySection}>Aucun projet.</div> : (
                    <table style={S.miniTable}>
                      <thead><tr>{['Code', 'Nom', 'Statut', 'Avancement', 'Budget consommé'].map(h => <th key={h} style={S.miniTh}>{h}</th>)}</tr></thead>
                      <tbody>
                        {activity.projets.map(p => (
                          <tr key={p.id}>
                            <td style={S.miniTd}>{p.code}</td>
                            <td style={S.miniTd}>{p.name}</td>
                            <td style={S.miniTd}>{p.status}</td>
                            <td style={S.miniTd}>{p.global_progress}%</td>
                            <td style={S.miniTd}>{p.budget ? `${Number(p.budget_consomme).toLocaleString('fr-FR')} F` : '–'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>

                <div style={S.section}>
                  <div style={S.sTitle}>Tâches récentes ({activity.taches_recentes.length})</div>
                  {activity.taches_recentes.length === 0 ? <div style={S.emptySection}>Aucune tâche.</div> : (
                    <table style={S.miniTable}>
                      <thead><tr>{['Projet', 'Tâche', 'Avancement', 'Mise à jour'].map(h => <th key={h} style={S.miniTh}>{h}</th>)}</tr></thead>
                      <tbody>
                        {activity.taches_recentes.map(t => (
                          <tr key={t.id}>
                            <td style={S.miniTd}>{t.project_code}</td>
                            <td style={S.miniTd}>{t.name}</td>
                            <td style={S.miniTd}>{t.task_progress}%</td>
                            <td style={S.miniTd}>{fmtDate(t.updated_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>

                <div style={S.section}>
                  <div style={S.sTitle}>Reportings hebdomadaires ({activity.reportings.length})</div>
                  {activity.reportings.length === 0 ? <div style={S.emptySection}>Aucun reporting.</div> : (
                    <table style={S.miniTable}>
                      <thead><tr>{['Projet', 'Semaine', 'Météo', 'Écart avancement', 'Commentaire'].map(h => <th key={h} style={S.miniTh}>{h}</th>)}</tr></thead>
                      <tbody>
                        {activity.reportings.map(r => (
                          <tr key={r.id}>
                            <td style={S.miniTd}>{r.project_code}</td>
                            <td style={S.miniTd}>S{r.week_number}/{r.year}</td>
                            <td style={S.miniTd}>{r.weather}</td>
                            <td style={S.miniTd}>{r.progress_gap}%</td>
                            <td style={S.miniTd}>{r.problems || r.summary || '–'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>

                <RequestSection title="Demandes" items={activity.demandes} />
              </>
            ) : null}
          </>
        )}
      </Modal>

    </div>
  );
};

// ─── Section réutilisable pour l'historique des demandes (entrées/sorties/ajustements) ─
const RequestSection = ({ title, items }) => (
  <div style={S.section}>
    <div style={S.sTitle}>{title} ({items.length})</div>
    {items.length === 0 ? <div style={S.emptySection}>Aucune demande.</div> : (
      <table style={S.miniTable}>
        <thead><tr>{['Référence', 'Statut', 'Articles', 'Montant', 'Date'].map(h => <th key={h} style={S.miniTh}>{h}</th>)}</tr></thead>
        <tbody>
          {items.map(it => (
            <tr key={it.id}>
              <td style={S.miniTd}>{it.reference}</td>
              <td style={S.miniTd}>{it.status_display}</td>
              <td style={S.miniTd}>{it.items_count}</td>
              <td style={S.miniTd}>{it.total_amount ? `${Number(it.total_amount).toLocaleString('fr-FR')} F` : '–'}</td>
              <td style={S.miniTd}>{fmtDate(it.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    )}
  </div>
);

export default Administration;
