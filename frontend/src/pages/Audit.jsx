import { useState, useEffect, useCallback, useRef } from 'react';
import api from '../api/axios';
import toast from 'react-hot-toast';
import { Button, Badge } from '../design-system';

// ─────────────────────────────────────────────────────────────────────────────
// Centre d'audit (Évolution 8) — historique complet, filtres serveur,
// export CSV/PDF. Réutilise l'endpoint /accounts/audit-center/, scopé par
// rôle côté backend (le DG voit tout, les autres voient leur périmètre) —
// cette page ne fait ni filtrage ni scoping côté client, uniquement de
// l'affichage. N'affecte jamais /accounts/audit-logs/ (toujours utilisé
// tel quel ailleurs si besoin).
// ─────────────────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

const DOT_COLOR = {
  accent:     'var(--accent-light)',
  success:    'var(--success-light)',
  danger:     'var(--danger)',
  info:       'var(--info)',
  muted:      'var(--text-muted)',
  warningAlt: 'var(--warning-alt)',
};

const ACTION_MAP = {
  CREATE:   { tone: 'success',    label: 'Création'            },
  UPDATE:   { tone: 'accent',     label: 'Modification'        },
  DELETE:   { tone: 'danger',     label: 'Suppression'         },
  VALIDATE: { tone: 'success',    label: 'Validation'          },
  REFUSE:   { tone: 'danger',     label: 'Refus'               },
  EXECUTE:  { tone: 'info',       label: 'Exécution financière'},
  LOGIN:    { tone: 'info',       label: 'Connexion'           },
  LOGOUT:   { tone: 'muted',      label: 'Déconnexion'         },
  DENIED:   { tone: 'warningAlt', label: 'Tentative refusée'   },
};

const MODEL_LABELS = {
  Product: 'Produit', Supplier: 'Fournisseur', StockMovement: 'Stock',
  PurchaseOrder: 'Commande', Document: 'Document', User: 'Utilisateur',
  Project: 'Projet', Task: 'Tâche', WeeklyReport: 'Rapport',
  Warehouse: 'Magasin', AdminRequest: 'Demande administrative',
  UnifiedRequest: 'Demande', RALBudget: 'Budget RAL',
};

const FIELD_LABELS = {
  budget: 'Budget', project_manager: 'Chef de projet',
  manager: 'Gérant du magasin', manager_username: 'Identifiant du gérant',
  is_urgent: 'Priorité (urgent)', montant_annuel: 'Budget annuel RAL',
};

const Ico = ({ d, size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);
const D = {
  download: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4 M7 10l5 5 5-5 M12 15V3',
  refresh:  'M23 4v6h-6 M1 20v-6h6 M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15',
};

const todayStr = () => new Date().toISOString().slice(0, 10);
const daysAgoStr = (n) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
};
const monthStartStr = () => {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10);
};

const fmtValue = (v) => {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'object') {
    const val = Object.values(v)[0];
    if (val === null || val === undefined) return '—';
    if (typeof val === 'number') return val.toLocaleString('fr-FR');
    if (typeof val === 'boolean') return val ? 'Oui' : 'Non';
    return String(val);
  }
  return String(v);
};

export default function Audit() {
  const [logs,    setLogs]    = useState([]);
  const [count,   setCount]   = useState(0);
  const [page,    setPage]    = useState(1);
  const [loading, setLoading] = useState(true);

  const [search,      setSearch]      = useState('');
  const [filterAction, setFilterAction] = useState('');
  const [filterModel,  setFilterModel]  = useState('');
  const [datePreset,   setDatePreset]   = useState('');
  const [dateFrom,      setDateFrom]      = useState('');
  const [dateTo,        setDateTo]        = useState('');

  const debounceRef = useRef(null);

  const buildParams = useCallback((withPage = true) => {
    const params = {};
    if (search)       params.search = search;
    if (filterAction) params.action = filterAction;
    if (filterModel)  params.model_name = filterModel;
    if (dateFrom)     params.date_from = dateFrom;
    if (dateTo)       params.date_to = dateTo;
    if (withPage)      params.page = page;
    return params;
  }, [search, filterAction, filterModel, dateFrom, dateTo, page]);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/accounts/audit-center/', { params: buildParams(true) });
      const data = res.data;
      setLogs(data.results ?? data ?? []);
      setCount(data.count ?? (Array.isArray(data) ? data.length : 0));
    } catch {
      toast.error("Erreur de chargement de l'historique");
      setLogs([]);
      setCount(0);
    } finally { setLoading(false); }
  }, [buildParams]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  // Recherche texte débouncée (300ms) — les autres filtres déclenchent un
  // rafraîchissement immédiat via leur propre onChange.
  const onSearchChange = (value) => {
    setSearch(value);
    setPage(1);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchLogs(), 300);
  };

  const applyDatePreset = (preset) => {
    setDatePreset(preset);
    setPage(1);
    if (preset === 'today')      { setDateFrom(todayStr()); setDateTo(todayStr()); }
    else if (preset === 'week')  { setDateFrom(daysAgoStr(7)); setDateTo(todayStr()); }
    else if (preset === 'month') { setDateFrom(monthStartStr()); setDateTo(todayStr()); }
    else if (preset === '')      { setDateFrom(''); setDateTo(''); }
    // 'custom' : laisse dateFrom/dateTo tels quels, contrôlés par les inputs
  };

  const downloadExport = async (kind) => {
    try {
      const res = await api.get(`/accounts/audit-center/export-${kind}/`, {
        params: buildParams(false), responseType: 'blob',
      });
      const mime = kind === 'csv' ? 'text/csv' : 'application/pdf';
      const url  = window.URL.createObjectURL(new Blob([res.data], { type: mime }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `audit.${kind === 'csv' ? 'csv' : 'pdf'}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch { toast.error(`Impossible de générer l'export ${kind.toUpperCase()}.`); }
  };

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div>
          <h1 style={S.title}>Centre d'audit</h1>
          <p style={S.sub}>Historique complet — {count} événement(s)</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Button variant="secondary" size="sm" onClick={() => downloadExport('csv')}>
            <Ico d={D.download} /> CSV
          </Button>
          <Button variant="secondary" size="sm" onClick={() => downloadExport('pdf')}>
            <Ico d={D.download} /> PDF
          </Button>
          <Button variant="secondary" size="sm" onClick={fetchLogs}>
            <Ico d={D.refresh} />
          </Button>
        </div>
      </div>

      {/* Filtres — tous envoyés au serveur, jamais appliqués côté client */}
      <div style={S.filterRow}>
        <input style={S.search}
          placeholder="Rechercher (utilisateur, description...)"
          value={search} onChange={e => onSearchChange(e.target.value)} />
        <select style={{ ...S.select, cursor: 'pointer' }} value={filterAction}
          onChange={e => { setFilterAction(e.target.value); setPage(1); }}>
          <option value="">Toutes les actions</option>
          {Object.entries(ACTION_MAP).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        <select style={{ ...S.select, cursor: 'pointer' }} value={filterModel}
          onChange={e => { setFilterModel(e.target.value); setPage(1); }}>
          <option value="">Tous les modules</option>
          {Object.entries(MODEL_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select style={{ ...S.select, cursor: 'pointer' }} value={datePreset}
          onChange={e => applyDatePreset(e.target.value)}>
          <option value="">Toute période</option>
          <option value="today">Aujourd'hui</option>
          <option value="week">Cette semaine</option>
          <option value="month">Ce mois</option>
          <option value="custom">Personnalisé</option>
        </select>
      </div>

      {datePreset === 'custom' && (
        <div style={{ ...S.filterRow, marginTop: '-0.3rem' }}>
          <label style={S.dateLbl}>Du
            <input type="date" style={S.dateInput} value={dateFrom}
              onChange={e => { setDateFrom(e.target.value); setPage(1); }} />
          </label>
          <label style={S.dateLbl}>Au
            <input type="date" style={S.dateInput} value={dateTo}
              onChange={e => { setDateTo(e.target.value); setPage(1); }} />
          </label>
          <Button variant="secondary" size="sm" onClick={fetchLogs}>Appliquer</Button>
        </div>
      )}

      {loading ? <div style={S.loading}>Chargement...</div>
      : logs.length === 0 ? <div style={S.empty}>Aucun événement trouvé</div>
      : (
        <div style={S.timeline}>
          {logs.map((log, i) => {
            const action = ACTION_MAP[log.action] || { tone: 'muted', label: log.action };
            const model  = MODEL_LABELS[log.model_name] || log.model_name;
            const date   = new Date(log.created_at);
            return (
              <div key={log.id} style={S.logItem}>
                <div style={S.timelineCol}>
                  <div style={{ ...S.dot, background: DOT_COLOR[action.tone] || DOT_COLOR.muted }} />
                  {i < logs.length - 1 && <div style={S.line} />}
                </div>
                <div style={S.logCard}>
                  <div style={S.logTop}>
                    <div style={S.logLeft}>
                      <Badge tone={action.tone}>{action.label}</Badge>
                      <span style={S.modelBadge}>
                        {model}{log.object_id && <span style={{ color: 'var(--text-disabled)', fontFamily: 'monospace' }}> #{log.object_id}</span>}
                      </span>
                    </div>
                    <div style={S.logRight}>
                      <span style={S.logUser}>{log.user_name}</span>
                      <span style={S.logDate}>
                        {date.toLocaleDateString('fr-FR')} à {date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                  <div style={S.logDesc}>{log.description}</div>
                  {log.field_name && (
                    <div style={S.changeRow}>
                      <span style={S.changeLbl}>{FIELD_LABELS[log.field_name] || log.field_name}</span>
                      <span style={S.changeOld}>{fmtValue(log.old_value)}</span>
                      <Ico d="M5 12h14M12 5l7 7-7 7" size={11} />
                      <span style={S.changeNew}>{fmtValue(log.new_value)}</span>
                    </div>
                  )}
                  {log.ip_address && <div style={S.logIp}>IP : {log.ip_address}</div>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {totalPages > 1 && (
        <div style={S.pagination}>
          <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
            ← Précédent
          </Button>
          <span style={S.pageInfo}>Page {page} / {totalPages}</span>
          <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
            Suivant →
          </Button>
        </div>
      )}
    </div>
  );
}

const S = {
  page:        { color: 'var(--text-secondary)' },
  header:      { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' },
  title:       { fontSize: '1.6rem', fontWeight: '700', color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.4px' },
  sub:         { fontSize: '0.8rem', color: 'var(--text-disabled)', marginTop: '0.25rem' },
  filterRow:   { display: 'flex', gap: '0.75rem', marginBottom: '0.625rem', flexWrap: 'wrap' },
  search:      { flex: 2, minWidth: '200px', padding: '0.65rem 0.875rem', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '7px', fontSize: '0.875rem', color: 'var(--text-secondary)', outline: 'none' },
  select:      { flex: 1, minWidth: '150px', padding: '0.65rem 0.875rem', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '7px', fontSize: '0.83rem', color: 'var(--text-secondary)', outline: 'none' },
  dateLbl:     { display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.78rem', color: 'var(--text-disabled)' },
  dateInput:   { padding: '0.5rem 0.7rem', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '7px', fontSize: '0.8rem', color: 'var(--text-secondary)', outline: 'none' },
  loading:     { padding: '3rem', textAlign: 'center', color: 'var(--text-disabled)' },
  empty:       { padding: '3rem', textAlign: 'center', color: 'var(--text-disabled)', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px' },
  timeline:    { display: 'flex', flexDirection: 'column' },
  logItem:     { display: 'flex', gap: '0.875rem', alignItems: 'flex-start' },
  timelineCol: { display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '0.875rem', width: '14px', flexShrink: 0 },
  dot:         { width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0 },
  line:        { width: '1px', flex: 1, background: 'var(--border-default)', minHeight: '16px', marginTop: '4px' },
  logCard:     { flex: 1, background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '8px', padding: '0.875rem 1rem', marginBottom: '0.375rem' },
  logTop:      { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem', flexWrap: 'wrap', gap: '0.4rem' },
  logLeft:     { display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' },
  logRight:    { display: 'flex', gap: '0.875rem', alignItems: 'center', flexWrap: 'wrap' },
  modelBadge:  { background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', padding: '0.15rem 0.55rem', borderRadius: '4px', fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: '600' },
  logUser:     { fontSize: '0.75rem', color: 'var(--accent-light)', fontWeight: '600' },
  logDate:     { fontSize: '0.72rem', color: 'var(--text-disabled)', fontFamily: 'monospace' },
  logDesc:     { fontSize: '0.83rem', color: 'var(--text-faint)', lineHeight: 1.6 },
  logIp:       { fontSize: '0.68rem', color: 'var(--text-disabled)', fontFamily: 'monospace', marginTop: '0.25rem' },
  changeRow:   { display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.45rem', padding: '0.4rem 0.6rem', background: 'var(--bg-surface-alt)', borderRadius: '6px', fontSize: '0.76rem' },
  changeLbl:   { color: 'var(--text-disabled)', fontWeight: '700', textTransform: 'uppercase', fontSize: '0.65rem', letterSpacing: '.03em', marginRight: '0.25rem' },
  changeOld:   { color: 'var(--danger)', fontFamily: 'monospace', textDecoration: 'line-through', opacity: 0.8 },
  changeNew:   { color: 'var(--success)', fontFamily: 'monospace', fontWeight: '700' },
  pagination:  { display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem', marginTop: '1.25rem' },
  pageInfo:    { fontSize: '0.8rem', color: 'var(--text-disabled)' },
};
