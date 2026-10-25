import { useState, useEffect, useCallback } from 'react';
import api from '../api/axios';
import MagasinierAccountFields from '../components/MagasinierAccountFields';
import { Modal, Button, Badge } from '../design-system';

// ─── Icons ────────────────────────────────────────────────────────────────────
const WarehouseIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
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
const UsersIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 00-3-3.87"/>
    <path d="M16 3.13a4 4 0 010 7.75"/>
  </svg>
);
const LocationIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/>
    <circle cx="12" cy="10" r="3"/>
  </svg>
);
const BoxIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
    <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
    <line x1="12" y1="22.08" x2="12" y2="12"/>
  </svg>
);
const ArrowUpIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
  </svg>
);
const ArrowDownIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/>
  </svg>
);
const AlertTriangleIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
    <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
  </svg>
);
const KeyIcon = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
  </svg>
);

// ─── Styles ───────────────────────────────────────────────────────────────────
const S = {
  page:         { padding: '28px', minHeight: '100vh', background: 'var(--bg-page)', color: 'var(--text-secondary)', fontFamily: 'var(--font-sans)' },
  header:       { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '28px' },
  title:        { display: 'flex', alignItems: 'center', gap: '10px', fontSize: '22px', fontWeight: '700', color: 'var(--text-primary)' },
  subtitle:     { fontSize: '13px', color: 'var(--text-disabled)', marginTop: '4px' },
  grid:         { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '20px' },
  card:         { background: 'var(--bg-surface)', borderRadius: '12px', border: '1px solid var(--border-default)', overflow: 'hidden', transition: 'box-shadow .2s' },
  cardHead:     { padding: '18px 20px', borderBottom: '1px solid var(--border-default)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' },
  cardBody:     { padding: '14px 20px' },
  cardFoot:     { padding: '12px 20px', borderTop: '1px solid var(--border-default)', display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'flex-end' },
  iconBox:      { width: '44px', height: '44px', borderRadius: '10px', background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-light)' },
  codeBadge:    { display: 'inline-block', fontSize: '11px', fontWeight: '700', color: 'var(--accent-light)', background: 'var(--accent-bg)', padding: '2px 8px', borderRadius: '4px', letterSpacing: '.05em', marginTop: '4px' },
  statRow:      { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid var(--border-faint)' },
  statLabel:    { fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' },
  statVal:      (color) => ({ fontSize: '13px', fontWeight: '700', color: color || 'var(--text-secondary)' }),
  alertBox:     { padding: '8px 12px', borderRadius: '6px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '10px', background: 'var(--danger-bg)', border: '1px solid var(--danger)', color: 'var(--danger)' },
  flash:        (type) => ({ padding: '12px 16px', borderRadius: '8px', fontSize: '13px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', ...(type === 'success' ? { background: 'var(--success-bg)', border: '1px solid var(--success)', color: 'var(--success)' } : { background: 'var(--danger-bg)', border: '1px solid var(--danger)', color: 'var(--danger)' }) }),
  label:        { display: 'block', fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: '6px' },
  input:        { width: '100%', padding: '10px 12px', background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '8px', color: 'var(--text-secondary)', fontSize: '14px', outline: 'none', boxSizing: 'border-box' },
  fGroup:       { marginBottom: '16px' },
  magRow:       { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', background: 'var(--bg-surface-alt)', borderRadius: '8px', marginBottom: '8px', gap: '10px', flexWrap: 'wrap' },
  empty:        { textAlign: 'center', padding: '60px 20px', color: 'var(--text-disabled)' },
  sTitle:       { fontSize: '11px', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '.05em', margin: '20px 0 12px', paddingBottom: '6px', borderBottom: '1px solid var(--border-default)' },
  stockSearch:  { width: '100%', marginBottom: '12px', padding: '9px 12px', background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '8px', color: 'var(--text-secondary)', fontSize: '13px', outline: 'none', boxSizing: 'border-box' },
  stockTable:   { width: '100%', borderCollapse: 'collapse', fontSize: '13px' },
  stockTh:      { padding: '8px 10px', background: 'var(--bg-surface-alt)', color: 'var(--text-disabled)', fontWeight: '700', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '.05em', textAlign: 'left', borderBottom: '1px solid var(--border-default)' },
  stockTd:      { padding: '9px 10px', borderBottom: '1px solid var(--border-faint)', verticalAlign: 'middle' },
  stockCode:    { fontFamily: 'monospace', fontSize: '12px', color: 'var(--accent-light)', background: 'var(--accent-bg)', padding: '2px 6px', borderRadius: '4px' },
  stockCatTag:  { background: 'var(--bg-surface-alt)', color: 'var(--text-faint)', padding: '2px 6px', borderRadius: '4px', fontSize: '11px' },
};

const STOCK_STATUS_TONE = { suffisant: 'success', critique: 'warningAlt', rupture: 'danger' };
const STOCK_STATUS_LABEL = { suffisant: 'Suffisant', critique: 'Critique', rupture: 'Rupture' };

// ─── Component ────────────────────────────────────────────────────────────────
const Warehouses = () => {
  const [warehouses,   setWarehouses]   = useState([]);
  const [loading,      setLoading]      = useState(true);
  const [statsCache,   setStatsCache]   = useState({});
  const [flash,        setFlash]        = useState({ type: '', msg: '' });
  const [showInactive, setShowInactive] = useState(false);

  // Modals
  const [showCreate,   setShowCreate]   = useState(false);
  const [showEdit,     setShowEdit]     = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [selected,     setSelected]     = useState(null);

  // Stock du magasin (lecture seule)
  const [showStock,      setShowStock]      = useState(false);
  const [stockWarehouse, setStockWarehouse] = useState(null);
  const [stockProducts,  setStockProducts]  = useState([]);
  const [stockLoading,   setStockLoading]   = useState(false);

  // Form (création/édition de magasin + compte du gérant)
  const emptyForm = {
    name: '', code: '', location: '', phone: '', email: '', is_active: true,
    mag_username: '', mag_first_name: '', mag_last_name: '', mag_email: '', mag_phone: '',
    mag_password: '', mag_password_confirm: '',
  };
  const [form, setForm] = useState(emptyForm);
  const [newPassword, setNewPassword] = useState('');

  // Demandes administratives (création/suppression de magasin)
  const [adminRequests, setAdminRequests] = useState([]);
  const [showApprove,   setShowApprove]   = useState(false);
  const [approveTarget, setApproveTarget] = useState(null);
  const [approvePassword, setApprovePassword] = useState('');
  const [approving,     setApproving]     = useState(false);

  // Permissions
  const user      = JSON.parse(localStorage.getItem('user') || '{}');
  const userRole  = user.role || '';
  const isDG      = userRole === 'dg' || user.is_dg === true;
  const isStock   = userRole === 'stock';
  const canManage = isDG || isStock;

  // ── fetch ──────────────────────────────────────────────────────────────────
  const notify = (type, msg) => {
    setFlash({ type, msg });
    setTimeout(() => setFlash({ type: '', msg: '' }), 4000);
  };

  const loadWarehouses = useCallback(async (inactive) => {
    try {
      setLoading(true);
      const res = await api.get(`/stock/warehouses/?is_active=${inactive ? 'false' : 'true'}`);
      const data = res.data.results ?? res.data;
      setWarehouses(Array.isArray(data) ? data : []);
    } catch {
      notify('error', 'Impossible de charger les magasins.');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAdminRequests = useCallback(async () => {
    try {
      const res = await api.get('/accounts/admin-requests/');
      const data = res.data.results ?? res.data ?? [];
      const filtered = (Array.isArray(data) ? data : []).filter(
        r => ['creation_magasin', 'suppression_magasin'].includes(r.request_type)
      );
      setAdminRequests(filtered);
    } catch { setAdminRequests([]); }
  }, []);

  const loadStats = useCallback(async (id) => {
    try {
      const res = await api.get(`/stock/warehouses/${id}/stats/`);
      setStatsCache(prev => ({ ...prev, [id]: res.data }));
    } catch { /* non bloquant */ }
  }, []);

  useEffect(() => { loadWarehouses(showInactive); }, [loadWarehouses, showInactive]);

  useEffect(() => {
    if (isDG || isStock) loadAdminRequests();
  }, [isDG, isStock, loadAdminRequests]);

  useEffect(() => {
    warehouses.forEach(w => { if (!statsCache[w.id]) loadStats(w.id); });
  }, [warehouses]); // eslint-disable-line

  // ── handlers ───────────────────────────────────────────────────────────────
  const resetForm = () => setForm(emptyForm);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (isDG && form.mag_password !== form.mag_password_confirm) {
      notify('error', 'Les mots de passe ne correspondent pas.');
      return;
    }
    try {
      if (isDG) {
        // Le DG crée le magasin ET son compte de connexion directement, en
        // une seule opération, sans passer par une demande.
        await api.post('/stock/warehouses/', {
          name: form.name, code: form.code, location: form.location,
          phone: form.phone, email: form.email,
          mag_username: form.mag_username, mag_first_name: form.mag_first_name,
          mag_last_name: form.mag_last_name, mag_email: form.mag_email,
          mag_phone: form.mag_phone, mag_password: form.mag_password,
        });
        notify('success', 'Magasin créé avec succès.');
      } else {
        // Le Responsable Achat et Logistique soumet une demande au DG ; l'identifiant est
        // défini ici, mais le mot de passe sera fixé par le DG à la validation.
        await api.post('/accounts/admin-requests/', {
          request_type: 'creation_magasin',
          payload: {
            name: form.name, code: form.code, location: form.location,
            phone: form.phone, email: form.email,
            username: form.mag_username,
            first_name: form.mag_first_name, last_name: form.mag_last_name,
            account_email: form.mag_email, account_phone: form.mag_phone,
          },
        });
        notify('success', 'Demande de création envoyée au DG pour validation.');
      }
      setShowCreate(false);
      resetForm();
      loadWarehouses(showInactive);
    } catch (err) {
      const d = err.response?.data || {};
      const payloadErr = d.payload;
      const magErr = d.mag_username || d.mag_password;
      const first = (v) => Array.isArray(v) ? v[0] : v;
      notify('error', first(payloadErr) || first(magErr) || d.detail || 'Erreur lors de la création.');
    }
  };

  const handleEdit = async (e) => {
    e.preventDefault();
    try {
      await api.put(`/stock/warehouses/${selected.id}/`, {
        name: form.name, code: form.code, location: form.location,
        phone: form.phone, email: form.email, is_active: form.is_active,
        mag_username: form.mag_username, mag_first_name: form.mag_first_name,
        mag_last_name: form.mag_last_name, mag_email: form.mag_email, mag_phone: form.mag_phone,
      });
      notify('success', 'Magasin modifié avec succès.');
      setShowEdit(false);
      resetForm();
      loadWarehouses(showInactive);
    } catch (err) {
      const d = err.response?.data || {};
      const magErr = d.mag_username;
      const first = (v) => Array.isArray(v) ? v[0] : v;
      notify('error', first(magErr) || d.detail || 'Erreur lors de la modification.');
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (newPassword.length < 6) { notify('error', 'Mot de passe de 6 caractères minimum requis.'); return; }
    try {
      await api.post(`/stock/warehouses/${selected.id}/reset-password/`, { password: newPassword });
      notify('success', 'Mot de passe réinitialisé.');
      setShowPassword(false);
      setNewPassword('');
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors de la réinitialisation.');
    }
  };

  const handleDeactivate = async (wh) => {
    if (!window.confirm(`Désactiver "${wh.name}" ?`)) return;
    try {
      await api.delete(`/stock/warehouses/${wh.id}/`);
      notify('success', 'Magasin désactivé.');
      loadWarehouses(showInactive);
    } catch { notify('error', 'Erreur lors de la désactivation.'); }
  };

  const handleReactivate = async (wh) => {
    try {
      await api.post(`/stock/warehouses/${wh.id}/reactivate/`);
      notify('success', 'Magasin réactivé.');
      loadWarehouses(showInactive);
    } catch { notify('error', 'Erreur lors de la réactivation.'); }
  };

  const handleProposeDeletion = async (wh) => {
    if (!window.confirm(`Proposer la suppression de "${wh.name}" au DG ?`)) return;
    try {
      await api.post('/accounts/admin-requests/', {
        request_type: 'suppression_magasin',
        payload: { warehouse_id: wh.id },
      });
      notify('success', 'Demande de suppression envoyée au DG.');
      loadAdminRequests();
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors de la demande.');
    }
  };

  const handleDeletePermanently = async (wh) => {
    const warning = wh.manager_name
      ? `Supprimer définitivement "${wh.name}" ET le compte magasinier "${wh.manager_name}" ? Cette action est irréversible.`
      : `Supprimer définitivement "${wh.name}" ? Cette action est irréversible.`;
    if (!window.confirm(warning)) return;
    try {
      await api.delete(`/stock/warehouses/${wh.id}/delete-permanently/`);
      notify('success', 'Magasin et compte magasinier supprimés définitivement.');
      loadWarehouses(showInactive);
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors de la suppression.');
    }
  };

  // ── Demandes administratives (DG) ─────────────────────────────────────────
  const openApprove = (req) => { setApproveTarget(req); setApprovePassword(''); setShowApprove(true); };

  const handleApprove = async () => {
    if (!approveTarget) return;
    if (approveTarget.request_type === 'creation_magasin' && approvePassword.length < 6) {
      notify('error', 'Mot de passe de 6 caractères minimum requis.');
      return;
    }
    try {
      setApproving(true);
      const body = approveTarget.request_type === 'creation_magasin' ? { password: approvePassword } : {};
      await api.post(`/accounts/admin-requests/${approveTarget.id}/approve/`, body);
      notify('success', 'Demande validée.');
      setShowApprove(false);
      loadAdminRequests();
      loadWarehouses(showInactive);
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors de la validation.');
    } finally { setApproving(false); }
  };

  const handleReject = async (req) => {
    const comment = window.prompt('Motif du refus (optionnel) :') || '';
    try {
      await api.post(`/accounts/admin-requests/${req.id}/reject/`, { comment });
      notify('success', 'Demande refusée.');
      loadAdminRequests();
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors du refus.');
    }
  };

  const openStock = async (wh) => {
    setStockWarehouse(wh);
    setStockProducts([]);
    setShowStock(true);
    setStockLoading(true);
    try {
      const res = await api.get(`/stock/warehouses/${wh.id}/current-stock/`);
      setStockProducts(res.data.products || []);
    } catch {
      notify('error', 'Impossible de charger le stock de ce magasin.');
    } finally {
      setStockLoading(false);
    }
  };

  const openEdit = (wh) => {
    setSelected(wh);
    setForm({
      ...emptyForm,
      name: wh.name, code: wh.code, location: wh.location || '', phone: wh.phone || '', email: wh.email || '',
      is_active: wh.is_active,
      mag_username: wh.manager_username || '', mag_first_name: wh.manager_first_name || '',
      mag_last_name: wh.manager_last_name || '', mag_phone: wh.manager_phone || '', mag_email: wh.manager_email || '',
    });
    setShowEdit(true);
  };

  const openPassword = (wh) => {
    setSelected(wh);
    setNewPassword('');
    setShowPassword(true);
  };

  // ── render ─────────────────────────────────────────────────────────────────
  if (loading) return (
    <div style={S.page}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px', color: 'var(--text-disabled)' }}>
        Chargement des magasins…
      </div>
    </div>
  );

  return (
    <div style={S.page}>

      {/* Header */}
      <div style={S.header}>
        <div>
          <div style={S.title}><WarehouseIcon size={22} /> Gestion des Magasins</div>
          <div style={S.subtitle}>{warehouses.length} magasin{warehouses.length !== 1 ? 's' : ''} {showInactive ? 'désactivé' : 'configuré'}{warehouses.length !== 1 ? 's' : ''}</div>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {isDG && (
            <Button variant="secondary" size="sm" onClick={() => setShowInactive(v => !v)}>
              {showInactive ? 'Voir les actifs' : 'Voir les désactivés'}
            </Button>
          )}
          {canManage && (
            <Button variant="primary" onClick={() => { resetForm(); setShowCreate(true); }}>
              <PlusIcon /> Nouveau Magasin
            </Button>
          )}
        </div>
      </div>

      {/* Flash */}
      {flash.msg && (
        <div style={S.flash(flash.type)}>
          <span>{flash.msg}</span>
          <button onClick={() => setFlash({ type: '', msg: '' })} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '18px', lineHeight: 1 }}>×</button>
        </div>
      )}

      {/* Demandes administratives (création/suppression de magasin) */}
      {(isDG || isStock) && adminRequests.length > 0 && (
        <div style={{ ...S.card, marginBottom: '20px' }}>
          <div style={S.cardHead}>
            <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
              Demandes de magasin {isDG ? '' : '(les miennes)'}
            </span>
          </div>
          <div style={{ padding: '8px 20px 16px' }}>
            {adminRequests.map(req => (
              <div key={req.id} style={S.magRow}>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)' }}>
                    {req.request_type_display} — <span style={{ fontFamily: 'monospace', color: 'var(--accent-light)' }}>{req.reference}</span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {req.payload?.name || req.payload?.warehouse_id ? `Magasin : ${req.payload?.name || `#${req.payload?.warehouse_id}`}` : ''}
                    {' · '}Par {req.requested_by_name} · {new Date(req.created_at).toLocaleDateString('fr-FR')}
                  </div>
                  {req.status !== 'en_attente' && (
                    <div style={{ fontSize: '11px', color: req.status === 'validee' ? 'var(--success-light)' : 'var(--danger)', marginTop: '2px', fontWeight: '600' }}>
                      {req.status_display}{req.review_comment ? ` — ${req.review_comment}` : ''}
                    </div>
                  )}
                </div>
                {isDG && req.status === 'en_attente' && (
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <Button variant="success" size="sm" onClick={() => openApprove(req)}>Valider</Button>
                    <Button variant="danger" size="sm" onClick={() => handleReject(req)}>Refuser</Button>
                  </div>
                )}
                {req.status === 'en_attente' && !isDG && (
                  <Badge tone="accent">En attente DG</Badge>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grid */}
      {warehouses.length === 0 ? (
        <div style={S.empty}>
          <div style={{ opacity: .35, display: 'flex', justifyContent: 'center', marginBottom: '16px' }}><WarehouseIcon size={52} /></div>
          <p style={{ fontSize: '15px', fontWeight: '600', marginBottom: '6px' }}>
            {showInactive ? 'Aucun magasin désactivé' : 'Aucun magasin configuré'}
          </p>
          <p style={{ fontSize: '13px' }}>
            {showInactive ? '' : canManage ? 'Cliquez sur "Nouveau Magasin" pour commencer.' : 'Aucun magasin n\'est associé à votre compte.'}
          </p>
        </div>
      ) : (
        <div style={S.grid}>
          {warehouses.map(wh => {
            const st = statsCache[wh.id] || {};
            return (
              <div key={wh.id} style={S.card}>
                {/* Card Header */}
                <div style={S.cardHead}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                      <span style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)' }}>{wh.name}</span>
                      <Badge tone={wh.is_active ? 'success' : 'danger'}>{wh.is_active ? 'Actif' : 'Inactif'}</Badge>
                    </div>
                    <span style={S.codeBadge}>{wh.code}</span>
                  </div>
                  <div style={S.iconBox}><WarehouseIcon size={22} /></div>
                </div>

                {/* Card Body */}
                <div style={S.cardBody}>
                  {wh.location && (
                    <div style={S.statRow}>
                      <span style={S.statLabel}><LocationIcon /> Localisation</span>
                      <span style={S.statVal()}>{wh.location}</span>
                    </div>
                  )}
                  {wh.manager_name && (
                    <div style={S.statRow}>
                      <span style={S.statLabel}><UsersIcon size={13} /> Titulaire</span>
                      <span style={S.statVal()}>{wh.manager_name}</span>
                    </div>
                  )}
                  {wh.phone && (
                    <div style={S.statRow}>
                      <span style={S.statLabel}>Téléphone</span>
                      <span style={S.statVal()}>{wh.phone}</span>
                    </div>
                  )}
                  {wh.email && (
                    <div style={S.statRow}>
                      <span style={S.statLabel}>Email</span>
                      <span style={S.statVal()}>{wh.email}</span>
                    </div>
                  )}
                  <div style={S.statRow}>
                    <span style={S.statLabel}><BoxIcon /> Produits distincts</span>
                    <span style={S.statVal()}>{st.total_products ?? '–'}</span>
                  </div>
                  <div style={S.statRow}>
                    <span style={S.statLabel}><ArrowUpIcon /> Entrées (30 j)</span>
                    <span style={S.statVal('var(--success-light)')}>{st.recent_entries ?? '–'}</span>
                  </div>
                  <div style={{ ...S.statRow, borderBottom: 'none' }}>
                    <span style={S.statLabel}><ArrowDownIcon /> Sorties (30 j)</span>
                    <span style={S.statVal('var(--warning)')}>{st.recent_exits ?? '–'}</span>
                  </div>
                  {st.low_stock_products > 0 && (
                    <div style={S.alertBox}>
                      <AlertTriangleIcon />
                      {st.low_stock_products} produit{st.low_stock_products > 1 ? 's' : ''} en stock faible
                    </div>
                  )}
                </div>

                {/* Card Footer */}
                {canManage && (
                  <div style={S.cardFoot}>
                    <Button variant="secondary" size="sm" onClick={() => openStock(wh)}>
                      <BoxIcon /> Voir le stock
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => openEdit(wh)}>
                      <EditIcon size={14} /> Modifier
                    </Button>
                    {isDG && wh.manager_username && (
                      <Button variant="secondary" size="sm" onClick={() => openPassword(wh)}>
                        <KeyIcon size={14} /> Mot de passe
                      </Button>
                    )}
                    {isDG && wh.is_active && (
                      <Button variant="warning" size="sm" onClick={() => handleDeactivate(wh)}>
                        Désactiver
                      </Button>
                    )}
                    {isDG && !wh.is_active && (
                      <Button variant="success" size="sm" onClick={() => handleReactivate(wh)}>
                        Réactiver
                      </Button>
                    )}
                    {isDG && (
                      <Button variant="danger" size="sm" onClick={() => handleDeletePermanently(wh)}
                        title="Supprimer définitivement le magasin et le compte magasinier">
                        <TrashIcon size={14} /> Supprimer
                      </Button>
                    )}
                    {isStock && wh.is_active && (
                      <Button variant="warning" size="sm" onClick={() => handleProposeDeletion(wh)}>
                        Proposer suppression
                      </Button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Modal Créer ──────────────────────────────────────────────────────── */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Nouveau Magasin"
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setShowCreate(false)}>Annuler</Button>
            <Button variant="primary" type="submit" form="warehouse-create-form">
              {isDG ? 'Créer le Magasin' : 'Soumettre la demande'}
            </Button>
          </>
        )}
      >
        <form id="warehouse-create-form" onSubmit={handleCreate}>
          {!isDG && (
            <div style={{ ...S.alertBox, background: 'var(--accent-bg)', border: '1px solid var(--border-default)', color: 'var(--accent-light)', marginTop: 0, marginBottom: '16px' }}>
              <AlertTriangleIcon /> Cette demande sera soumise au DG pour validation avant la création réelle du magasin.
            </div>
          )}

          <p style={S.sTitle}>Informations du magasin</p>
          <div style={S.fGroup}>
            <label style={S.label}>Nom *</label>
            <input style={S.input} type="text" placeholder="Ex : Magasin Dakar" value={form.name}
              onChange={e => setForm(p => ({ ...p, name: e.target.value }))} required />
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Code *</label>
            <input style={S.input} type="text" placeholder="Ex : MAG-DKR" value={form.code}
              onChange={e => setForm(p => ({ ...p, code: e.target.value.toUpperCase() }))} required />
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Localisation</label>
            <input style={S.input} type="text" placeholder="Ex : Zone Industrielle, Dakar" value={form.location}
              onChange={e => setForm(p => ({ ...p, location: e.target.value }))} />
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Téléphone</label>
            <input style={S.input} type="text" placeholder="Ex : +221 33 000 00 00" value={form.phone}
              onChange={e => setForm(p => ({ ...p, phone: e.target.value }))} />
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Email</label>
            <input style={S.input} type="email" placeholder="Ex : magasin@gertech.com" value={form.email}
              onChange={e => setForm(p => ({ ...p, email: e.target.value }))} />
          </div>

          <MagasinierAccountFields form={form} setForm={setForm} mode="create" showPassword={isDG} />
        </form>
      </Modal>

      {/* ── Modal Modifier ───────────────────────────────────────────────────── */}
      <Modal
        open={showEdit && !!selected}
        onClose={() => setShowEdit(false)}
        title={selected ? `Modifier — ${selected.name}` : 'Modifier'}
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setShowEdit(false)}>Annuler</Button>
            <Button variant="primary" type="submit" form="warehouse-edit-form">Enregistrer</Button>
          </>
        )}
      >
        <form id="warehouse-edit-form" onSubmit={handleEdit}>
          <p style={S.sTitle}>Informations du magasin</p>
          <div style={S.fGroup}>
            <label style={S.label}>Nom *</label>
            <input style={S.input} type="text" value={form.name}
              onChange={e => setForm(p => ({ ...p, name: e.target.value }))} required />
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Code *</label>
            <input style={S.input} type="text" value={form.code}
              onChange={e => setForm(p => ({ ...p, code: e.target.value.toUpperCase() }))} required />
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Localisation</label>
            <input style={S.input} type="text" value={form.location}
              onChange={e => setForm(p => ({ ...p, location: e.target.value }))} />
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
          {isDG && (
            <div style={S.fGroup}>
              <label style={S.label}>Statut</label>
              <select style={{ ...S.input, cursor: 'pointer' }} value={form.is_active ? 'active' : 'inactive'}
                onChange={e => setForm(p => ({ ...p, is_active: e.target.value === 'active' }))}>
                <option value="active">Actif</option>
                <option value="inactive">Inactif</option>
              </select>
            </div>
          )}

          {isDG && <MagasinierAccountFields form={form} setForm={setForm} mode="edit" />}
        </form>
      </Modal>

      {/* ── Modal Réinitialiser le mot de passe ──────────────────────────────── */}
      <Modal
        open={showPassword && !!selected}
        onClose={() => setShowPassword(false)}
        title={selected ? `Réinitialiser — ${selected.name}` : 'Réinitialiser'}
        maxWidth="420px"
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setShowPassword(false)}>Annuler</Button>
            <Button variant="primary" type="submit" form="warehouse-password-form">Réinitialiser</Button>
          </>
        )}
      >
        <form id="warehouse-password-form" onSubmit={handleResetPassword}>
          <div style={S.fGroup}>
            <label style={S.label}>Nouveau mot de passe *</label>
            <input style={S.input} type="text" placeholder="6 caractères minimum" value={newPassword}
              onChange={e => setNewPassword(e.target.value)} required />
          </div>
        </form>
      </Modal>

      {/* ── Modal Valider une demande de création de magasin ─────────────────── */}
      <Modal
        open={showApprove && !!approveTarget}
        onClose={() => setShowApprove(false)}
        title={approveTarget ? `Valider — ${approveTarget.reference}` : 'Valider'}
        footer={(
          <>
            <Button variant="secondary" onClick={() => setShowApprove(false)}>Annuler</Button>
            <Button variant="primary" onClick={handleApprove} disabled={approving}>
              {approving ? 'Validation…' : 'Confirmer la validation'}
            </Button>
          </>
        )}
      >
        {approveTarget && (approveTarget.request_type === 'creation_magasin' ? (
          <>
            <p style={{ fontSize: '13px', color: 'var(--text-tertiary)', marginTop: 0 }}>
              Le magasin <strong style={{ color: 'var(--text-primary)' }}>{approveTarget.payload?.name}</strong> et son compte
              de connexion <strong style={{ color: 'var(--text-primary)' }}>{approveTarget.payload?.username}</strong> seront créés
              avec le mot de passe défini ci-dessous.
            </p>
            <div style={S.fGroup}>
              <label style={S.label}>Mot de passe du compte *</label>
              <input style={S.input} type="text" placeholder="6 caractères minimum" value={approvePassword}
                onChange={e => setApprovePassword(e.target.value)} required />
            </div>
          </>
        ) : (
          <p style={{ fontSize: '13px', color: 'var(--text-tertiary)', marginTop: 0 }}>
            Confirmer la désactivation du magasin visé par cette demande ?
          </p>
        ))}
      </Modal>

      {/* ── Modal Stock du magasin ─────────────────────────────────────────────── */}
      <Modal
        open={showStock}
        onClose={() => setShowStock(false)}
        title={stockWarehouse ? `Stock — ${stockWarehouse.name}` : 'Stock'}
        maxWidth="700px"
        footer={<Button variant="secondary" onClick={() => setShowStock(false)}>Fermer</Button>}
      >
        {stockLoading ? (
          <p style={{ fontSize: '13px', color: 'var(--text-disabled)', textAlign: 'center', padding: '20px 0' }}>Chargement…</p>
        ) : stockProducts.length === 0 ? (
          <p style={{ fontSize: '13px', color: 'var(--text-disabled)', textAlign: 'center', padding: '20px 0' }}>
            Aucun mouvement de stock n'a encore été enregistré dans ce magasin.
          </p>
        ) : (
          <table style={S.stockTable}>
            <thead>
              <tr>
                {['Code', 'Désignation', 'Catégorie', 'Unité', 'Stock présent', 'Sécurité', 'Statut'].map((h, i) => (
                  <th key={h} style={{ ...S.stockTh, textAlign: i >= 4 && i <= 5 ? 'right' : 'left' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {stockProducts.map(p => (
                <tr key={p.product_id}>
                  <td style={S.stockTd}><span style={S.stockCode}>{p.code}</span></td>
                  <td style={S.stockTd}>{p.designation}</td>
                  <td style={S.stockTd}>{p.category_name ? <span style={S.stockCatTag}>{p.category_name}</span> : '–'}</td>
                  <td style={S.stockTd}>{p.unit}</td>
                  <td style={{ ...S.stockTd, textAlign: 'right', fontWeight: '700', color: 'var(--text-primary)', fontFamily: 'monospace' }}>
                    {Number(p.stock_actuel).toLocaleString('fr-FR')}
                  </td>
                  <td style={{ ...S.stockTd, textAlign: 'right', color: 'var(--text-faint)', fontFamily: 'monospace' }}>
                    {Number(p.stock_securite).toLocaleString('fr-FR')}
                  </td>
                  <td style={S.stockTd}><Badge tone={STOCK_STATUS_TONE[p.stock_status] || 'success'}>{STOCK_STATUS_LABEL[p.stock_status] || p.stock_status}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Modal>

    </div>
  );
};

export default Warehouses;
