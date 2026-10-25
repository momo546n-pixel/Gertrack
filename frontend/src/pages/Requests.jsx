import { useState, useEffect, useCallback } from 'react';
import api from '../api/axios';
import { Modal, Button, Badge } from '../design-system';

// ─── Config ───────────────────────────────────────────────────────────────────
const STATUS_CFG = {
  brouillon:          { label: 'Brouillon',                    tone: 'muted'     },
  en_attente_dop:     { label: 'En attente DOP',               tone: 'warning'   },
  en_attente_dg:      { label: 'En attente DG',                tone: 'accent'    },
  en_attente_dop_dg:  { label: 'En attente DOP ou DG (urgent)', tone: 'warningAlt'},
  validee:            { label: 'Validée',                       tone: 'success'   },
  refusee:            { label: 'Refusée',                       tone: 'danger'    },
  executee:           { label: 'Exécutée',                      tone: 'info'      },
};

const TYPE_CFG = {
  achat:      { label: 'Achat',      color: 'var(--warning-alt)' },
  entree:     { label: 'Entrée',     color: 'var(--success-light)' },
  sortie:     { label: 'Sortie',     color: 'var(--danger)' },
  ajustement: { label: 'Ajustement', color: 'var(--accent-light)' },
};

// ─── Icons ────────────────────────────────────────────────────────────────────
const Ico = ({ d, size = 16, color = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);

const D = {
  plus:    'M12 5v14M5 12h14',
  eye:     'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z M12 9a3 3 0 100 6 3 3 0 000-6z',
  send:    'M22 2L11 13 M22 2l-7 20-4-9-9-4 20-7z',
  check:   'M20 6L9 17l-5-5',
  x:       'M18 6L6 18M6 6l12 12',
  trash:   'M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6',
  doc:     'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z M14 2v6h6',
  refresh: 'M23 4v6h-6 M1 20v-6h6 M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15',
  alert:   'M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z M12 9v4 M12 17h.01',
  download:'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4 M7 10l5 5 5-5 M12 15V3',
};

// ─── Styles ───────────────────────────────────────────────────────────────────
const S = {
  page:        { padding: '28px', minHeight: '100vh', background: 'var(--bg-page)', color: 'var(--text-secondary)', fontFamily: 'var(--font-sans)' },
  header:      { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' },
  title:       { fontSize: '22px', fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' },
  subtitle:    { fontSize: '13px', color: 'var(--text-disabled)', marginTop: '4px' },
  statsRow:    { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px,1fr))', gap: '12px', marginBottom: '24px' },
  statCard:    { background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px', padding: '14px 16px' },
  statVal:     { fontSize: '26px', fontWeight: '800', color: 'var(--text-primary)', lineHeight: 1 },
  statLbl:     { fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '.04em' },
  toolbar:     { display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap', alignItems: 'center' },
  searchInput: { flex: 1, minWidth: '200px', padding: '8px 12px', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '8px', color: 'var(--text-secondary)', fontSize: '13px', outline: 'none' },
  select:      { padding: '8px 12px', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '8px', color: 'var(--text-secondary)', fontSize: '13px', outline: 'none', cursor: 'pointer' },
  table:       { width: '100%', borderCollapse: 'collapse', fontSize: '13px' },
  th:          { padding: '10px 14px', background: 'var(--bg-surface-alt)', color: 'var(--text-disabled)', fontWeight: '700', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '.05em', textAlign: 'left', borderBottom: '1px solid var(--border-default)' },
  td:          { padding: '12px 14px', borderBottom: '1px solid var(--border-faint)', verticalAlign: 'middle' },
  flash:       (t) => ({ padding: '12px 16px', borderRadius: '8px', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', ...(t === 'success' ? { background: 'var(--success-bg)', border: '1px solid var(--success)', color: 'var(--success)' } : { background: 'var(--danger-bg)', border: '1px solid var(--danger)', color: 'var(--danger)' }) }),
  fGroup:      { marginBottom: '16px' },
  label:       { display: 'block', fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: '6px' },
  input:       { width: '100%', padding: '9px 12px', background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '8px', color: 'var(--text-secondary)', fontSize: '13px', outline: 'none', boxSizing: 'border-box' },
  textarea:    { width: '100%', padding: '9px 12px', background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '8px', color: 'var(--text-secondary)', fontSize: '13px', outline: 'none', boxSizing: 'border-box', resize: 'vertical', minHeight: '70px' },
  row2:        { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' },
  itemBox:     { background: 'var(--bg-surface-alt)', borderRadius: '8px', padding: '10px 12px', border: '1px solid var(--border-default)', marginBottom: '8px' },
  itemRow:     { display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: '8px', alignItems: 'flex-end' },
  section:     { marginBottom: '20px' },
  sTitle:      { fontSize: '11px', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: '10px', paddingBottom: '6px', borderBottom: '1px solid var(--border-default)' },
  infoRow:     { display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-faint)', fontSize: '13px' },
  infoLbl:     { color: 'var(--text-muted)' },
  infoVal:     { color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' },
  empty:       { textAlign: 'center', padding: '60px', color: 'var(--text-disabled)' },
};

// ─── Composant Principal ──────────────────────────────────────────────────────
export default function Requests({ validationMode = false }) {
  const user      = JSON.parse(localStorage.getItem('user') || '{}');
  const role      = user.role || '';

  const isDG        = role === 'dg'    || user.is_dg === true;
  const isDOP       = role === 'chef_ops' || user.is_ops_chief === true;
  const isStock     = role === 'stock';
  const isMagasinier = role === 'magasinier';
  const canCreate   = ['stock', 'magasinier', 'chef_projet'].includes(role);

  // ── Types de demande autorisés par rôle ──────────────────────────────────────
  const ALLOWED_TYPES_BY_ROLE = {
    stock:       ['achat', 'entree', 'sortie', 'ajustement'],
    magasinier:  ['entree', 'sortie', 'ajustement'],
    chef_projet: ['entree', 'sortie'],
  };
  const allowedTypes  = ALLOWED_TYPES_BY_ROLE[role] || Object.keys(TYPE_CFG);
  const isPM          = role === 'chef_projet';

  // Demande d'achat urgente (Évolution 5) — réservée à Chef de Projet,
  // Magasinier et RAL, toujours liée à un projet ; le serveur reste seul
  // juge (voir UnifiedRequestViewSet._enforce_role_constraints), ceci ne
  // sert qu'à afficher/masquer la case à cocher correspondante.
  const isUrgentAllowed = ['stock', 'magasinier', 'chef_projet'].includes(role);

  // ── State ──────────────────────────────────────────────────────────────────
  const [requests,       setRequests]       = useState([]);
  const [loading,        setLoading]        = useState(true);
  const [flash,          setFlash]          = useState({ t: '', m: '' });
  const [search,         setSearch]         = useState('');
  const [typeFilter,     setTypeFilter]     = useState('');
  const [statusFilter,   setStatusFilter]   = useState(validationMode ? 'en_attente_dg' : '');
  const [urgentFilter,   setUrgentFilter]   = useState(''); // '' | 'urgent' | 'standard'

  // Modals
  const [showCreate,      setShowCreate]      = useState(false);
  const [showDetail,      setShowDetail]      = useState(false);
  const [showValidate,    setShowValidate]    = useState(false);
  const [detail,          setDetail]          = useState(null);
  const [validateAction,  setValidateAction]  = useState('');
  const [validateComment, setValidateComment] = useState('');
  const [validating,      setValidating]      = useState(false);

  // Circuit logistique (Phase F — §7/§8)
  const [logisticsDate, setLogisticsDate] = useState('');
  const [advancing,     setAdvancing]     = useState(false);

  // Données pour selects
  const [products,   setProducts]   = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [suppliers,  setSuppliers]  = useState([]);
  const [projects,   setProjects]   = useState([]);

  // Budget
  const [budgetInfo,    setBudgetInfo]    = useState(null);
  const [budgetLoading, setBudgetLoading] = useState(false);

  // Formulaire
  const emptyForm = {
    request_type: allowedTypes[0] || 'entree', validation_type: 'dg_only',
    warehouse: '', supplier: '', project: '',
    motif: '', notes: '', date_needed: '', is_urgent: false,
  };
  const [form,      setForm]      = useState(emptyForm);
  const [formItems, setFormItems] = useState([{ product: '', quantity: '', unit_price: '', notes: '' }]);
  const [creating,  setCreating]  = useState(false);

  // ── Stats ──────────────────────────────────────────────────────────────────
  const stats = {
    total:      requests.length,
    brouillon:  requests.filter(r => r.status === 'brouillon').length,
    en_attente: requests.filter(r => ['en_attente_dop', 'en_attente_dg', 'en_attente_dop_dg'].includes(r.status)).length,
    validee:    requests.filter(r => r.status === 'validee').length,
    executee:   requests.filter(r => r.status === 'executee').length,
    refusee:    requests.filter(r => r.status === 'refusee').length,
  };

  // ── Helpers ────────────────────────────────────────────────────────────────
  const notify = (t, m) => {
    setFlash({ t, m });
    setTimeout(() => setFlash({ t: '', m: '' }), 4000);
  };
  const formatDate   = (d) => d ? new Date(d).toLocaleDateString('fr-FR') : '–';
  const formatAmount = (a) => a ? `${parseFloat(a).toLocaleString('fr-FR')} FCFA` : '–';

  // ── Chargements ───────────────────────────────────────────────────────────
  const loadRequests = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/requests/');
      setRequests(res.data.results ?? res.data ?? []);
    } catch { notify('error', 'Impossible de charger les demandes.'); }
    finally { setLoading(false); }
  }, []);

  const loadMeta = useCallback(async () => {
  try {
    const [p, w, s, proj] = await Promise.all([
      api.get('/products/').catch(() => ({ data: [] })),
      api.get('/stock/warehouses/select-list/').catch(() => ({ data: [] })),
      api.get('/suppliers/').catch(() => ({ data: [] })),

      api.get('/operations/projects/select-list/').catch(() => ({ data: [] })),
    ]);
    setProducts(p.data.results    ?? p.data    ?? []);
    setWarehouses(w.data.results  ?? w.data    ?? []);
    setSuppliers(s.data.results   ?? s.data    ?? []);
    setProjects(proj.data.results ?? proj.data ?? []);
  } catch (err) {
    console.error('loadMeta error:', err);
  }
}, []);

  const loadProjectBudget = async (projectId) => {
    if (!projectId) { setBudgetInfo(null); return; }
    try {
      setBudgetLoading(true);
      const res = await api.get(`/requests/project-budget/?project_id=${projectId}`);
      setBudgetInfo(res.data);
    } catch { setBudgetInfo(null); }
    finally { setBudgetLoading(false); }
  };

  useEffect(() => { loadRequests(); loadMeta(); }, [loadRequests, loadMeta]);

  // ── Filtrage ──────────────────────────────────────────────────────────────
  const filtered = requests.filter(r => {
    const q = search.toLowerCase();
    const matchSearch = !q ||
      r.reference?.toLowerCase().includes(q) ||
      r.requested_by_name?.toLowerCase().includes(q) ||
      r.motif?.toLowerCase().includes(q);
    const matchType   = !typeFilter   || r.request_type === typeFilter;
    const matchStatus = !statusFilter || r.status        === statusFilter;
    const matchUrgent = !urgentFilter || (urgentFilter === 'urgent' ? r.is_urgent : !r.is_urgent);
    const matchScope  = !validationMode || ['magasinier', 'chef_projet'].includes(r.requested_by_role);
    return matchSearch && matchType && matchStatus && matchUrgent && matchScope;
  });

  // ── Items formulaire ──────────────────────────────────────────────────────
  const addItem    = () => setFormItems(p => [...p, { product: '', quantity: '', unit_price: '', notes: '' }]);
  const removeItem = (i) => setFormItems(p => p.filter((_, idx) => idx !== i));
  const setItem    = (i, field, val) => setFormItems(p => p.map((it, idx) => idx === i ? { ...it, [field]: val } : it));

  // ── Créer ─────────────────────────────────────────────────────────────────
  const handleCreate = async (e) => {
    e.preventDefault();
    if (isPM && !form.project) { notify('error', 'Un projet est obligatoire pour le chef de projet.'); return; }
    if (form.is_urgent && !form.project) { notify('error', "Un projet est obligatoire pour une demande d'achat urgente."); return; }
    const validItems = formItems.filter(it => it.product && it.quantity);
    if (validItems.length === 0) { notify('error', 'Ajoutez au moins un article.'); return; }
    const payload = {
      ...form,
      warehouse:   form.warehouse   || null,
      supplier:    form.supplier    || null,
      project:     form.project     || null,
      date_needed: form.date_needed || null,
      items: validItems.map(it => ({
        product:    parseInt(it.product),
        quantity:   parseFloat(it.quantity),
        unit_price: it.unit_price ? parseFloat(it.unit_price) : null,
        notes:      it.notes || '',
      })),
    };
    try {
      setCreating(true);
      await api.post('/requests/', payload);
      notify('success', 'Demande créée en brouillon.');
      setShowCreate(false);
      setForm(emptyForm);
      setFormItems([{ product: '', quantity: '', unit_price: '', notes: '' }]);
      setBudgetInfo(null);
      loadRequests();
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors de la création.');
    } finally { setCreating(false); }
  };

  // ── Soumettre ─────────────────────────────────────────────────────────────
  const handleSubmit = async (id) => {
    try {
      const res = await api.post(`/requests/${id}/submit/`);
      setDetail(res.data);
      loadRequests();
      notify('success', 'Demande soumise pour validation.');
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur.');
    }
  };

  // ── Validation ────────────────────────────────────────────────────────────
  const openValidate = (action) => { setValidateAction(action); setValidateComment(''); setShowValidate(true); };

  const handleValidate = async () => {
    if (!detail) return;
    try {
      setValidating(true);
      const res = await api.post(`/requests/${detail.id}/${validateAction}/`, { comment: validateComment });
      setDetail(res.data);
      setShowValidate(false);
      loadRequests();
      notify('success', validateAction.startsWith('reject') ? 'Refusé avec succès.' : 'Validé avec succès.');
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur.');
    } finally { setValidating(false); }
  };

  // ── Supprimer ─────────────────────────────────────────────────────────────
  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer ce brouillon ?')) return;
    try {
      await api.delete(`/requests/${id}/`);
      notify('success', 'Brouillon supprimé.');
      setShowDetail(false);
      loadRequests();
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur.');
    }
  };

  // ── PDF ───────────────────────────────────────────────────────────────────
  const downloadPDF = async (id, reference) => {
    try {
      const res  = await api.get(`/requests/${id}/pdf/`, { responseType: 'blob' });
      const url  = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href  = url;
      link.setAttribute('download', `${reference}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch { notify('error', 'Impossible de générer le PDF.'); }
  };

  // ── Détail ────────────────────────────────────────────────────────────────
  const openDetail = async (id) => {
    try {
      const res = await api.get(`/requests/${id}/`);
      setDetail(res.data);
      setLogisticsDate('');
      setShowDetail(true);
    } catch { notify('error', 'Impossible de charger la demande.'); }
  };

  // ── Circuit logistique (Phase F — §7/§8) ──────────────────────────────────
  const nextLogisticsStage = (req) => {
    const stages = req?.logistics_stages || [];
    if (stages.length === 0) return null;
    const currentIdx = req.logistics_status ? stages.findIndex(s => s.value === req.logistics_status) : -1;
    if (currentIdx >= stages.length - 1) return null;
    return stages[currentIdx + 1];
  };

  const canAdvanceLogistics = (req, nextStage) => {
    if (!nextStage) return false;
    const isSiteReception = req.request_type === 'sortie' && nextStage.value === 'reception_chantier';
    if (isSiteReception) {
      // Sans projet associé, il n'y a pas de Chef de Projet à qui déléguer
      // la confirmation — on retombe sur le demandeur (sinon la demande
      // reste bloquée à "En transit" indéfiniment).
      if (!req.project) return isDG || req.requested_by === user.id;
      return isDG || isPM;
    }
    // Le suivi logistique (commande envoyée, expédition, etc.) est géré par
    // l'auteur de la demande, pas par un rôle générique.
    return req.requested_by === user.id;
  };

  const handleAdvanceLogistics = async (stageValue) => {
    if (!detail) return;
    try {
      setAdvancing(true);
      const payload = { logistics_status: stageValue };
      if (logisticsDate) payload.date_livraison_prevue = logisticsDate;
      const res = await api.post(`/requests/${detail.id}/advance-logistics/`, payload);
      setDetail(res.data);
      setLogisticsDate('');
      loadRequests();
      notify('success', 'Circuit logistique mis à jour.');
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors de la mise à jour du circuit logistique.');
    } finally { setAdvancing(false); }
  };

  // ── Render helpers ────────────────────────────────────────────────────────
  // Pour l'étape finale ('en_attente_dg'), le libellé affiché dépend de qui
  // valide réellement : Responsable Achat et Logistique pour un magasinier/chef de projet,
  // DG sinon (voir finalStageLabel plus haut).
  const StatusBadge = ({ s, req }) => {
    const cfg = STATUS_CFG[s] || { label: s, tone: 'muted' };
    const label = s === 'en_attente_dg' && req ? `En attente ${finalStageLabel(req)}` : cfg.label;
    return <Badge tone={cfg.tone}>{label}</Badge>;
  };
  const TypeBadge = ({ t }) => {
    const cfg = TYPE_CFG[t] || { label: t, color: 'var(--text-muted)' };
    return <span style={{ fontSize: '12px', fontWeight: '700', color: cfg.color }}>{cfg.label}</span>;
  };

  // Étape finale ('en_attente_dg') : validée par le Responsable Achat et Logistique quand la
  // demande vient d'un magasinier ou d'un chef de projet, sinon par le DG.
  const finalStageIsStockRun = (req) => ['magasinier', 'chef_projet'].includes(req?.requested_by_role);
  const canValidateFinalStage = (req) => finalStageIsStockRun(req) ? isStock : isDG;
  const finalStageLabel = (req) => finalStageIsStockRun(req) ? 'RAL' : 'DG';
  const circuitLabel = (req) => {
    if (req?.validation_type === 'urgent_dop_ou_dg') return 'Urgent — DOP ou DG (le premier valide)';
    if (req?.validation_type === 'dop_then_dg') return `DOP puis ${finalStageLabel(req)}`;
    return finalStageLabel(req);
  };

  const ActionButtons = ({ req }) => {
    if (!req) return null;
    const isOwner = req.requested_by === user.id;
    return (
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {req.status === 'brouillon' && (isOwner || isDG || isStock) && (
          <Button variant="warning" size="sm" onClick={() => handleSubmit(req.id)}>
            <Ico d={D.send} size={13} /> Soumettre
          </Button>
        )}
        {req.status === 'en_attente_dop' && (isDOP || isStock) && (<>
          <Button variant="success" size="sm" onClick={() => openValidate('validate-dop')}>
            <Ico d={D.check} size={13} /> Valider
          </Button>
          <Button variant="danger" size="sm" onClick={() => openValidate('reject-dop')}>
            <Ico d={D.x} size={13} /> Refuser
          </Button>
        </>)}
        {/* Course urgente (Évolution 5) : ni RAL ni personne d'autre ne peut
            s'y substituer — strictement DOP ou DG, le premier qui agit
            décide seul (voir UnifiedRequestViewSet._is_real_dop/_is_real_dg). */}
        {req.status === 'en_attente_dop_dg' && (isDOP || isDG) && (<>
          <Button variant="success" size="sm" onClick={() => openValidate(isDOP ? 'validate-dop' : 'validate-dg')}>
            <Ico d={D.check} size={13} /> Valider
          </Button>
          <Button variant="danger" size="sm" onClick={() => openValidate(isDOP ? 'reject-dop' : 'reject-dg')}>
            <Ico d={D.x} size={13} /> Refuser
          </Button>
        </>)}
        {req.status === 'en_attente_dg' && canValidateFinalStage(req) && (<>
          <Button variant="success" size="sm" onClick={() => openValidate('validate-dg')}>
            <Ico d={D.check} size={13} /> Valider
          </Button>
          <Button variant="danger" size="sm" onClick={() => openValidate('reject-dg')}>
            <Ico d={D.x} size={13} /> Refuser
          </Button>
        </>)}
        {['validee', 'executee'].includes(req.status) && req.request_type === 'achat' && (
          <Button variant="info" size="sm" onClick={() => downloadPDF(req.id, req.reference)}>
            <Ico d={D.download} size={13} /> Télécharger PDF
          </Button>
        )}
        {req.status === 'brouillon' && (isOwner || isDG || isStock) && (
          <Button variant="danger" size="sm" onClick={() => handleDelete(req.id)}>
            <Ico d={D.trash} size={13} />
          </Button>
        )}
      </div>
    );
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div style={S.page}>

      {/* Header */}
      <div style={S.header}>
        <div>
          <div style={S.title}><Ico d={D.doc} size={22} /> {validationMode ? 'Demandes à valider' : 'Demandes'}</div>
          <div style={S.subtitle}>
            {validationMode
              ? 'Demandes de magasiniers et chefs de projet en attente de votre validation'
              : "Gestion unifiée des demandes d'achat et de stock"}
          </div>
        </div>
        {canCreate && !validationMode && (
          <Button variant="primary" onClick={() => setShowCreate(true)}>
            <Ico d={D.plus} size={15} /> Nouvelle Demande
          </Button>
        )}
      </div>

      {/* Flash */}
      {flash.m && (
        <div style={S.flash(flash.t)}>
          <span>{flash.m}</span>
          <button onClick={() => setFlash({ t: '', m: '' })}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '18px' }}>×</button>
        </div>
      )}

      {/* Stats */}
      <div style={S.statsRow}>
        {[
          { val: stats.total,      lbl: 'Total',      color: 'var(--accent-light)' },
          { val: stats.en_attente, lbl: 'En attente', color: 'var(--warning)' },
          { val: stats.brouillon,  lbl: 'Brouillons', color: 'var(--text-muted)' },
          { val: stats.validee,    lbl: 'Validées',   color: 'var(--success-light)' },
          { val: stats.executee,   lbl: 'Exécutées',  color: 'var(--info)' },
          { val: stats.refusee,    lbl: 'Refusées',   color: 'var(--danger)' },
        ].map(s => (
          <div key={s.lbl} style={S.statCard}>
            <div style={{ ...S.statVal, color: s.color }}>{s.val}</div>
            <div style={S.statLbl}>{s.lbl}</div>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div style={S.toolbar}>
        <input style={S.searchInput} placeholder="Rechercher par référence, demandeur, motif…"
          value={search} onChange={e => setSearch(e.target.value)} />
        <select style={S.select} value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
          <option value="">Tous types</option>
          {Object.entries(TYPE_CFG).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <select style={S.select} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">Tous statuts</option>
          {Object.entries(STATUS_CFG).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <select style={S.select} value={urgentFilter} onChange={e => setUrgentFilter(e.target.value)}>
          <option value="">Urgent / Standard</option>
          <option value="urgent">Urgentes uniquement</option>
          <option value="standard">Standards uniquement</option>
        </select>
        <Button variant="secondary" size="sm" onClick={loadRequests}>
          <Ico d={D.refresh} size={13} />
        </Button>
      </div>

      {/* Table */}
      {loading ? (
        <div style={S.empty}>Chargement…</div>
      ) : filtered.length === 0 ? (
        <div style={S.empty}>
          <div style={{ opacity: .3, marginBottom: '12px' }}><Ico d={D.doc} size={48} /></div>
          <p style={{ fontSize: '15px', fontWeight: '600' }}>Aucune demande trouvée</p>
        </div>
      ) : (
        <div style={{ background: 'var(--bg-surface)', borderRadius: '12px', border: '1px solid var(--border-default)', overflow: 'hidden' }}>
          <table style={S.table}>
            <thead>
              <tr>
                {['Référence', 'Type', 'Statut', 'Demandeur', 'Articles', 'Montant', 'Date', 'Actions'].map(h => (
                  <th key={h} style={S.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(r => (
                <tr key={r.id}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <td style={S.td}>
                    <span style={{ fontWeight: '700', color: 'var(--accent-light)', fontFamily: 'monospace', fontSize: '13px', cursor: 'pointer' }}
                      onClick={() => openDetail(r.id)}>
                      {r.reference}
                    </span>
                    {r.motif && (
                      <div style={{ fontSize: '11px', color: 'var(--text-disabled)', marginTop: '2px' }}>
                        {r.motif.slice(0, 40)}{r.motif.length > 40 ? '…' : ''}
                      </div>
                    )}
                  </td>
                  <td style={S.td}>
                    <TypeBadge t={r.request_type} />
                    {r.is_urgent && <span style={{ marginLeft: '6px' }}><Badge tone="warningAlt">Urgent</Badge></span>}
                  </td>
                  <td style={S.td}>
                    <StatusBadge s={r.status} req={r} />
                    {r.est_en_retard && (
                      <span style={{ marginLeft: '6px' }}><Badge tone="danger">Retard</Badge></span>
                    )}
                  </td>
                  <td style={{ ...S.td, color: 'var(--text-secondary)' }}>{r.requested_by_name || '–'}</td>
                  <td style={{ ...S.td, color: 'var(--text-tertiary)', textAlign: 'center' }}>{r.items_count}</td>
                  <td style={{ ...S.td, color: 'var(--text-tertiary)' }}>{r.total_amount ? formatAmount(r.total_amount) : '–'}</td>
                  <td style={{ ...S.td, color: 'var(--text-muted)', fontSize: '12px' }}>{formatDate(r.created_at)}</td>
                  <td style={S.td}>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <Button variant="secondary" size="sm" onClick={() => openDetail(r.id)}>
                        <Ico d={D.eye} size={13} />
                      </Button>
                      {['validee', 'executee'].includes(r.status) && r.request_type === 'achat' && (
                        <Button variant="info" size="sm" onClick={() => downloadPDF(r.id, r.reference)}>
                          <Ico d={D.download} size={13} />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Modal Créer ──────────────────────────────────────────────────────── */}
      <Modal
        open={showCreate}
        onClose={() => { setShowCreate(false); setBudgetInfo(null); }}
        title="Nouvelle Demande"
        maxWidth="820px"
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => { setShowCreate(false); setBudgetInfo(null); }}>
              Annuler
            </Button>
            <Button variant="primary" type="submit" form="request-create-form" disabled={creating}>
              {creating ? 'Création…' : 'Créer en Brouillon'}
            </Button>
          </>
        )}
      >
        <form id="request-create-form" onSubmit={handleCreate}>

          {/* Type + Circuit */}
          <div style={S.row2}>
            <div style={S.fGroup}>
              <label style={S.label}>Type de Demande *</label>
              {form.is_urgent ? (
                <div style={{ ...S.input, display: 'flex', alignItems: 'center', color: 'var(--text-tertiary)' }}>
                  Achat
                </div>
              ) : (
                <select style={{ ...S.input, cursor: 'pointer' }}
                  value={form.request_type}
                  onChange={e => setForm(p => ({ ...p, request_type: e.target.value }))}>
                  {Object.entries(TYPE_CFG).filter(([k]) => allowedTypes.includes(k)).map(([k, v]) => (
                    <option key={k} value={k}>{v.label}</option>
                  ))}
                </select>
              )}
            </div>
            {form.is_urgent || isMagasinier || isPM ? (
              <div style={S.fGroup}>
                <label style={S.label}>Circuit de Validation</label>
                <div style={{ ...S.input, display: 'flex', alignItems: 'center', color: 'var(--text-tertiary)' }}>
                  {form.is_urgent ? 'Urgent — DOP ou DG (le premier valide)' : isMagasinier ? 'Responsable Achat et Logistique' : 'DOP puis Responsable Achat et Logistique'}
                </div>
              </div>
            ) : (
              <div style={S.fGroup}>
                <label style={S.label}>Circuit de Validation *</label>
                <select style={{ ...S.input, cursor: 'pointer' }}
                  value={form.validation_type}
                  onChange={e => setForm(p => ({ ...p, validation_type: e.target.value }))}>
                  <option value="dg_only">DG uniquement</option>
                  <option value="dop_then_dg">DOP puis DG</option>
                </select>
              </div>
            )}
          </div>

          {/* Demande d'achat urgente (Évolution 5) */}
          {isUrgentAllowed && (
            <div style={{ ...S.fGroup, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input type="checkbox" id="is_urgent" checked={form.is_urgent}
                onChange={e => {
                  const checked = e.target.checked;
                  setForm(p => ({ ...p, is_urgent: checked, request_type: checked ? 'achat' : (allowedTypes[0] || 'entree') }));
                }} />
              <label htmlFor="is_urgent" style={{ fontSize: '13px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                Demande d'achat urgente — notifie immédiatement le DOP et le DG, le premier à statuer décide seul
              </label>
            </div>
          )}

          {/* Magasin / Fournisseur + Date */}
          <div style={S.row2}>
            {['entree', 'sortie', 'ajustement'].includes(form.request_type) && (
              <div style={S.fGroup}>
                <label style={S.label}>Magasin</label>
                <select style={{ ...S.input, cursor: 'pointer' }}
                  value={form.warehouse}
                  onChange={e => setForm(p => ({ ...p, warehouse: e.target.value }))}>
                  <option value="">— Sélectionner —</option>
                  {warehouses.map(w => (
                    <option key={w.id} value={w.id}>{w.name}</option>
                  ))}
                </select>
              </div>
            )}
            {form.request_type === 'achat' && (
              <div style={S.fGroup}>
                <label style={S.label}>Fournisseur</label>
                <select style={{ ...S.input, cursor: 'pointer' }}
                  value={form.supplier}
                  onChange={e => setForm(p => ({ ...p, supplier: e.target.value }))}>
                  <option value="">— Sélectionner —</option>
                  {suppliers.map(s => (
                    <option key={s.id} value={s.id}>{s.nom || s.name}</option>
                  ))}
                </select>
              </div>
            )}
            <div style={S.fGroup}>
              <label style={S.label}>Date souhaitée</label>
              <input type="date" style={S.input}
                value={form.date_needed}
                onChange={e => setForm(p => ({ ...p, date_needed: e.target.value }))} />
            </div>
          </div>

          {/* Projet + Budget */}
          <div style={S.fGroup}>
            <label style={S.label}>Projet associé{(isPM || form.is_urgent) ? ' *' : ''}</label>
            <select style={{ ...S.input, cursor: 'pointer' }}
              value={form.project || ''}
              required={isPM || form.is_urgent}
              onChange={e => {
                setForm(p => ({ ...p, project: e.target.value }));
                loadProjectBudget(e.target.value);
              }}>
              {!isPM && !form.is_urgent && <option value="">— Aucun projet —</option>}
              {(isPM || form.is_urgent) && !form.project && <option value="">— Sélectionner un projet —</option>}
              {projects.map(p => (
                <option key={p.id} value={p.id}>[{p.code}] {p.name}</option>
              ))}
            </select>
            {isPM && projects.length === 0 && (
              <div style={{ fontSize: '12px', color: 'var(--warning)', marginTop: '6px' }}>
                Aucun projet ne vous est actuellement affecté.
              </div>
            )}
          </div>

          {/* Bloc budget dynamique */}
          {budgetLoading && (
            <div style={{ fontSize: '12px', color: 'var(--text-disabled)', marginBottom: '12px' }}>
              Chargement du budget…
            </div>
          )}
          {form.project && budgetInfo && !budgetLoading && (
            <div style={{
              padding: '14px', borderRadius: '8px', marginBottom: '16px',
              background: budgetInfo.budget_depasse ? 'var(--danger-bg)' : 'var(--accent-bg)',
              border: `1px solid ${budgetInfo.budget_depasse ? 'var(--danger)' : 'var(--border-default)'}`,
            }}>
              {budgetInfo.budget_alloue !== null ? (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.04em' }}>
                      Budget — {budgetInfo.project_name}
                    </span>
                    {budgetInfo.budget_depasse && (
                      <span style={{ fontSize: '11px', fontWeight: '800', color: 'var(--danger)' }}>
                        DÉPASSEMENT
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '8px', marginBottom: '10px' }}>
                    {[
                      { lbl: 'Alloué',   val: budgetInfo.budget_alloue,   color: 'var(--accent-light)' },
                      { lbl: 'Consommé', val: budgetInfo.budget_consomme, color: 'var(--warning)' },
                      { lbl: 'Restant',  val: budgetInfo.budget_restant,  color: budgetInfo.budget_depasse ? 'var(--danger)' : 'var(--success-light)' },
                    ].map(b => (
                      <div key={b.lbl} style={{ textAlign: 'center', background: 'var(--bg-surface-alt)', borderRadius: '6px', padding: '8px' }}>
                        <div style={{ fontSize: '13px', fontWeight: '800', color: b.color }}>
                          {b.val !== null ? `${parseFloat(b.val).toLocaleString('fr-FR')} F` : '–'}
                        </div>
                        <div style={{ fontSize: '10px', color: 'var(--text-disabled)', fontWeight: '600', textTransform: 'uppercase', marginTop: '2px' }}>{b.lbl}</div>
                      </div>
                    ))}
                  </div>
                  {/* Barre */}
                  <div style={{ background: 'var(--border-default)', borderRadius: '4px', height: '6px', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.min(budgetInfo.budget_pourcentage, 100)}%`,
                      background: budgetInfo.budget_depasse ? 'var(--danger)'
                        : budgetInfo.budget_pourcentage > 80 ? 'var(--warning)' : 'var(--success-light)',
                      borderRadius: '4px',
                    }} />
                  </div>
                  <div style={{ textAlign: 'right', fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {budgetInfo.budget_pourcentage}% consommé
                  </div>
                  {budgetInfo.budget_depasse && (
                    <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--danger)', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Ico d={D.alert} size={14} color="var(--danger)" />
                      Cette demande dépasse le budget restant. Elle reste possible mais une alerte sera générée.
                    </div>
                  )}
                </>
              ) : (
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0 }}>
                  Aucun budget défini pour ce projet.
                </p>
              )}
            </div>
          )}

          {/* Motif */}
          <div style={S.fGroup}>
            <label style={S.label}>Motif *</label>
            <input style={S.input} type="text" required placeholder="Objet de la demande…"
              value={form.motif}
              onChange={e => setForm(p => ({ ...p, motif: e.target.value }))} />
          </div>

          {/* Articles */}
          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <span style={{ ...S.label, marginBottom: 0 }}>Articles *</span>
              <Button variant="secondary" size="sm" type="button" onClick={addItem}>
                <Ico d={D.plus} size={13} /> Ajouter
              </Button>
            </div>
            {formItems.map((it, i) => (
              <div key={i} style={S.itemBox}>
                <div style={S.itemRow}>
                  <div>
                    <label style={S.label}>Produit *</label>
                    <select style={{ ...S.input, cursor: 'pointer' }}
                      value={it.product}
                      onChange={e => setItem(i, 'product', e.target.value)} required>
                      <option value="">— Choisir —</option>
                      {products.map(p => (
                        <option key={p.id} value={p.id}>
                          [{p.code}] {p.designation} (Stock: {p.stock_actuel})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label style={S.label}>Quantité *</label>
                    <input type="number" min="0.01" step="0.01" style={S.input}
                      value={it.quantity}
                      onChange={e => setItem(i, 'quantity', e.target.value)} required />
                  </div>
                  {form.request_type === 'achat' && (
                    <div>
                      <label style={S.label}>Prix unit.</label>
                      <input type="number" min="0" step="0.01" style={S.input}
                        value={it.unit_price}
                        onChange={e => setItem(i, 'unit_price', e.target.value)} />
                    </div>
                  )}
                  <Button variant="danger" size="sm" type="button" style={{ alignSelf: 'flex-end' }}
                    onClick={() => removeItem(i)} disabled={formItems.length === 1}>
                    <Ico d={D.trash} size={13} />
                  </Button>
                </div>
              </div>
            ))}
          </div>

          {/* Notes */}
          <div style={S.fGroup}>
            <label style={S.label}>Notes internes</label>
            <textarea style={S.textarea} placeholder="Remarques complémentaires…"
              value={form.notes}
              onChange={e => setForm(p => ({ ...p, notes: e.target.value }))} />
          </div>

        </form>
      </Modal>

      {/* ── Modal Détail ─────────────────────────────────────────────────────── */}
      <Modal
        open={showDetail && !!detail}
        onClose={() => setShowDetail(false)}
        title={detail?.reference}
        maxWidth="820px"
        footer={<Button variant="secondary" onClick={() => setShowDetail(false)}>Fermer</Button>}
      >
        {detail && (
          <>
            {/* Infos générales */}
            <div style={S.section}>
              <div style={S.sTitle}>Informations générales</div>
              {[
                ['Statut',          <StatusBadge s={detail.status} req={detail} />],
                ['Type',            <>
                  <TypeBadge t={detail.request_type} />
                  {detail.is_urgent && <span style={{ marginLeft: '6px' }}><Badge tone="warningAlt">Urgent</Badge></span>}
                </>],
                ['Circuit',         circuitLabel(detail)],
                ['Demandeur',       detail.requested_by_name],
                ['Motif',           detail.motif || '–'],
                ['Magasin',         detail.warehouse_name  || '–'],
                ['Fournisseur',     detail.supplier_name   || '–'],
                ['Projet',          detail.project_name    || '–'],
                ['Date souhaitée',  detail.date_needed ? formatDate(detail.date_needed) : '–'],
                ['Créée le',        formatDate(detail.created_at)],
              ].map(([l, v]) => (
                <div key={l} style={S.infoRow}>
                  <span style={S.infoLbl}>{l}</span>
                  <span style={S.infoVal}>{v}</span>
                </div>
              ))}
            </div>

            {/* Articles */}
            <div style={S.section}>
              <div style={S.sTitle}>Articles ({detail.items?.length || 0})</div>
              <table style={{ ...S.table, fontSize: '12px' }}>
                <thead>
                  <tr>
                    {['Code', 'Désignation', 'Qté', 'Prix unit.', 'Total', 'Stock actuel'].map(h => (
                      <th key={h} style={{ ...S.th, padding: '8px 10px' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(detail.items || []).map(it => (
                    <tr key={it.id}>
                      <td style={{ ...S.td, padding: '8px 10px', fontFamily: 'monospace', color: 'var(--accent-light)' }}>{it.product_code}</td>
                      <td style={{ ...S.td, padding: '8px 10px' }}>{it.product_name}</td>
                      <td style={{ ...S.td, padding: '8px 10px', fontWeight: '700' }}>{it.quantity} {it.product_unit}</td>
                      <td style={{ ...S.td, padding: '8px 10px', color: 'var(--text-tertiary)' }}>{it.unit_price ? formatAmount(it.unit_price) : '–'}</td>
                      <td style={{ ...S.td, padding: '8px 10px', color: 'var(--warning)', fontWeight: '700' }}>{it.total_price ? formatAmount(it.total_price) : '–'}</td>
                      <td style={{ ...S.td, padding: '8px 10px', color: it.stock_actuel < 5 ? 'var(--danger)' : 'var(--success-light)' }}>{it.stock_actuel}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {detail.total_amount > 0 && (
                <div style={{ textAlign: 'right', marginTop: '10px', fontSize: '14px', fontWeight: '800', color: 'var(--warning)' }}>
                  Total : {formatAmount(detail.total_amount)}
                </div>
              )}
            </div>

            {/* Circuit logistique (achats/sorties exécutées) — pour un achat
                (Évolution 7), 'validee' ne suffit plus : le Responsable
                Financier doit d'abord exécuter la commande. */}
            {['achat', 'sortie'].includes(detail.request_type) && detail.status === 'executee' && (
              <div style={S.section}>
                <div style={S.sTitle}>
                  Circuit logistique
                  {detail.est_en_retard && (
                    <span style={{ marginLeft: '10px' }}><Badge tone="danger">En retard</Badge></span>
                  )}
                </div>

                {/* Timeline des étapes */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '14px' }}>
                  {(detail.logistics_stages || []).map(stage => {
                    const stages    = detail.logistics_stages;
                    const currentIdx = detail.logistics_status ? stages.findIndex(s => s.value === detail.logistics_status) : -1;
                    const stageIdx   = stages.findIndex(s => s.value === stage.value);
                    const done    = stageIdx < currentIdx;
                    const current = stageIdx === currentIdx;
                    return (
                      <span key={stage.value} style={{
                        padding: '4px 10px', borderRadius: '20px', fontSize: '11px', fontWeight: '700',
                        background: current ? 'var(--accent-bg)' : done ? 'var(--success-bg)' : 'var(--muted-bg)',
                        color:      current ? 'var(--accent-light)' : done ? 'var(--success-light)' : 'var(--text-muted)',
                        border: current ? '1px solid var(--border-default)' : '1px solid transparent',
                      }}>
                        {stage.label}
                      </span>
                    );
                  })}
                </div>

                <div style={S.infoRow}>
                  <span style={S.infoLbl}>Date de livraison prévue</span>
                  <span style={S.infoVal}>{detail.date_livraison_prevue ? formatDate(detail.date_livraison_prevue) : '–'}</span>
                </div>
                <div style={S.infoRow}>
                  <span style={S.infoLbl}>Date de livraison réelle</span>
                  <span style={S.infoVal}>{detail.date_livraison_reelle ? formatDate(detail.date_livraison_reelle) : '–'}</span>
                </div>
                {detail.reception_confirmed_by_name && (
                  <div style={S.infoRow}>
                    <span style={S.infoLbl}>Réception confirmée par</span>
                    <span style={S.infoVal}>{detail.reception_confirmed_by_name}</span>
                  </div>
                )}

                {(() => {
                  const next = nextLogisticsStage(detail);
                  if (!next) return null;
                  if (!canAdvanceLogistics(detail, next)) return null;
                  const isSiteReception = detail.request_type === 'sortie' && next.value === 'reception_chantier';
                  return (
                    <div style={{ marginTop: '12px', padding: '12px', background: 'var(--bg-surface-alt)', borderRadius: '8px', border: '1px solid var(--border-default)' }}>
                      <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                        <div style={{ flex: 1, minWidth: '160px' }}>
                          <label style={S.label}>Date prévue (optionnel)</label>
                          <input type="date" style={S.input} value={logisticsDate}
                            onChange={e => setLogisticsDate(e.target.value)} />
                        </div>
                        <Button variant={isSiteReception ? 'success' : 'info'} disabled={advancing}
                          onClick={() => handleAdvanceLogistics(next.value)}>
                          {advancing ? 'Mise à jour…' : isSiteReception ? 'Confirmer réception chantier' : `Avancer : ${next.label}`}
                        </Button>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}

            {/* Historique validation */}
            {(detail.dop_validated_by || detail.dg_validated_by) && (
              <div style={S.section}>
                <div style={S.sTitle}>Historique validation</div>
                {detail.dop_validated_by_name && (
                  <div style={{ background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '8px', padding: '10px 12px', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: '700', fontSize: '12px', color: 'var(--warning)' }}>Validation</span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{formatDate(detail.dop_validated_at)}</span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '4px' }}>Par : {detail.dop_validated_by_name}</div>
                    {detail.dop_comment && <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px', fontStyle: 'italic' }}>"{detail.dop_comment}"</div>}
                  </div>
                )}
                {detail.dg_validated_by_name && (
                  <div style={{ background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '8px', padding: '10px 12px', marginBottom: detail.financial_execution_by_name ? '8px' : 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: '700', fontSize: '12px', color: 'var(--success-light)' }}>Validation</span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{formatDate(detail.dg_validated_at)}</span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '4px' }}>Par : {detail.dg_validated_by_name}</div>
                    {detail.dg_comment && <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px', fontStyle: 'italic' }}>"{detail.dg_comment}"</div>}
                  </div>
                )}
                {detail.financial_execution_by_name && (
                  <div style={{ background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '8px', padding: '10px 12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: '700', fontSize: '12px', color: 'var(--info)' }}>Exécution financière</span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{formatDate(detail.financial_execution_at)}</span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '4px' }}>Par : {detail.financial_execution_by_name}</div>
                    {detail.financial_execution_notes && <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px', fontStyle: 'italic' }}>"{detail.financial_execution_notes}"</div>}
                  </div>
                )}
              </div>
            )}

            {/* Actions */}
            <div style={S.section}>
              <div style={S.sTitle}>Actions</div>
              <ActionButtons req={detail} />
            </div>
          </>
        )}
      </Modal>

      {/* ── Modal Validation ─────────────────────────────────────────────────── */}
      <Modal
        open={showValidate}
        onClose={() => setShowValidate(false)}
        title={validateAction.startsWith('reject') ? 'Refuser' : 'Valider'}
        maxWidth="440px"
        footer={(
          <>
            <Button variant="secondary" onClick={() => setShowValidate(false)}>Annuler</Button>
            <Button variant={validateAction.includes('reject') ? 'danger' : 'success'} disabled={validating} onClick={handleValidate}>
              {validating ? 'En cours…' : validateAction.includes('reject') ? 'Confirmer le refus' : 'Confirmer la validation'}
            </Button>
          </>
        )}
      >
        <div style={S.fGroup}>
          <label style={S.label}>Commentaire</label>
          <textarea style={S.textarea} placeholder="Commentaire optionnel…"
            value={validateComment}
            onChange={e => setValidateComment(e.target.value)} />
        </div>
        {validateAction.startsWith('reject') && (
          <div style={{ padding: '10px 14px', background: 'var(--danger-bg)', border: '1px solid var(--danger)', borderRadius: '8px', fontSize: '13px', color: 'var(--danger)' }}>
            Cette action refusera définitivement la demande.
          </div>
        )}
      </Modal>

    </div>
  );
}
