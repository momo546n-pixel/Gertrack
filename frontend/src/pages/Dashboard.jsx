import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import { PieChart, Pie, Cell, Tooltip } from 'recharts';

// ─── Tons sémantiques (jetons de design) ───────────────────────────────────────
const TONE = {
  accent:     { c: 'var(--accent-light)', bg: 'var(--accent-bg)' },
  success:    { c: 'var(--success)',      bg: 'var(--success-bg)' },
  danger:     { c: 'var(--danger)',       bg: 'var(--danger-bg)' },
  warning:    { c: 'var(--warning)',      bg: 'var(--warning-bg)' },
  warningAlt: { c: 'var(--warning-alt)',  bg: 'var(--warning-alt-bg)' },
  info:       { c: 'var(--info)',         bg: 'var(--info-bg)' },
  muted:      { c: 'var(--text-muted)',   bg: 'var(--muted-bg)' },
};

// ─── Config statuts ───────────────────────────────────────────────────────────
const STATUS_STYLE = {
  brouillon:         { tone: 'muted',      label: 'Brouillon'                    },
  en_attente_dop:    { tone: 'warning',    label: 'En attente DOP'               },
  en_attente_dg:     { tone: 'warningAlt', label: 'En attente DG'                },
  en_attente_dop_dg: { tone: 'warningAlt', label: 'En attente DOP ou DG (urgent)'},
  validee:           { tone: 'success',    label: 'Validée'                       },
  refusee:           { tone: 'danger',     label: 'Refusée'                       },
  executee:          { tone: 'info',       label: 'Exécutée'                      },
};

// L'étape finale ('en_attente_dg') est validée par le Responsable Achat et Logistique quand
// la demande vient d'un magasinier ou d'un chef de projet, sinon par le DG.
const statusLabel = (o) => {
  if (o.status === 'en_attente_dg' && ['magasinier', 'chef_projet'].includes(o.requested_by_role)) {
    return 'En attente RAL';
  }
  return (STATUS_STYLE[o.status] || STATUS_STYLE.brouillon).label;
};

const ACTION_TONE = {
  CREATE: 'success', UPDATE: 'accent', DELETE: 'danger',
  VALIDATE: 'success', REFUSE: 'danger', LOGIN: 'info', LOGOUT: 'muted',
};
const ACTION_LABELS = {
  CREATE: 'Création', UPDATE: 'Modification', DELETE: 'Suppression',
  VALIDATE: 'Validation', REFUSE: 'Refus', LOGIN: 'Connexion', LOGOUT: 'Déconnexion',
};

// ─── Mini composants ──────────────────────────────────────────────────────────
const Ico = ({ d, size = 16, color = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);

const D = {
  arrow_right: 'M5 12h14M12 5l7 7-7 7',
  alert:       'M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z M12 9v4 M12 17h.01',
  check:       'M20 6L9 17l-5-5',
  clock:       'M12 22a10 10 0 100-20 10 10 0 000 20z M12 6v6l4 2',
  box:         'M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z',
  doc:         'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z M14 2v6h6',
  users:       'M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2 M9 11a4 4 0 100-8 4 4 0 000 8z',
  trending:    'M23 6l-9.5 9.5-5-5L1 18 M17 6h6v6',
  warehouse:   'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z M9 22V12h6v10',
  plus:        'M12 5v14M5 12h14',
};

// ─── Donut avec total au centre ────────────────────────────────────────────────
const Donut = ({ data, size = 108 }) => {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) {
    return (
      <div style={{ width: size, height: size, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-disabled)' }}>—</span>
      </div>
    );
  }
  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      {/* Taille fixe passée directement (au lieu de ResponsiveContainer) :
          le conteneur a déjà des dimensions en pixels connues à l'avance,
          ce qui évite l'avertissement recharts "width(-1) height(-1)" émis
          le temps que son ResizeObserver interne mesure le parent. */}
      <PieChart width={size} height={size}>
        <Pie
          data={data} dataKey="value" nameKey="label"
          innerRadius={size * 0.34} outerRadius={size * 0.5}
          paddingAngle={data.filter(d => d.value > 0).length > 1 ? 3 : 0}
          strokeWidth={0} animationDuration={650} animationEasing="ease-out"
          isAnimationActive
        >
          {data.map((d, i) => <Cell key={i} fill={d.color} />)}
        </Pie>
        <Tooltip
          contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '8px', fontSize: '12px', padding: '6px 10px' }}
          itemStyle={{ color: 'var(--text-secondary)' }}
          labelStyle={{ display: 'none' }}
          formatter={(value, name) => [value, name]}
        />
      </PieChart>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', pointerEvents: 'none',
      }}>
        <span style={{ fontSize: '1.2rem', fontWeight: '800', color: 'var(--text-primary)', lineHeight: 1 }}>{total}</span>
        <span style={{ fontSize: '0.55rem', color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '.5px', marginTop: '2px' }}>Total</span>
      </div>
    </div>
  );
};

// ─── Légende à côté d'un donut ──────────────────────────────────────────────────
const DonutLegend = ({ data }) => (
  <div style={{ flex: 1, minWidth: 0 }}>
    {data.map(d => (
      <div key={d.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '7px', minWidth: 0 }}>
          <div style={{ width: '7px', height: '7px', borderRadius: '50%', background: d.color, flexShrink: 0 }} />
          <span style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.label}</span>
        </div>
        <span style={{ fontFamily: "'DM Mono', monospace", fontWeight: '700', color: d.color, fontSize: '0.82rem', flexShrink: 0, marginLeft: '8px' }}>{d.value}</span>
      </div>
    ))}
  </div>
);

// ─── Barres horizontales simples (projets par statut) ──────────────────────────
const StatusBars = ({ data }) => {
  const max = Math.max(...data.map(d => d.value), 1);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {data.map((d, i) => (
        <div key={d.label}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
            <span style={{ color: 'var(--text-tertiary)' }}>{d.label}</span>
            <span style={{ color: d.color, fontWeight: '700', fontFamily: "'DM Mono', monospace" }}>{d.value}</span>
          </div>
          <div style={{ height: '6px', background: 'var(--bg-page)', borderRadius: '4px', overflow: 'hidden' }}>
            <div className="dash-bar-fill" style={{
              height: '100%', background: d.color, borderRadius: '4px',
              width: `${(d.value / max) * 100}%`, animationDelay: `${i * 60}ms`,
            }} />
          </div>
        </div>
      ))}
    </div>
  );
};

// ─── Carte quel raccourci ───────────────────────────────────────────────────────
const ShortcutRow = ({ shortcuts, navigate }) => (
  <div style={S.shortcutRow}>
    {shortcuts.map(s => (
      <button key={s.label} className="dash-shortcut" style={S.shortcutBtn} onClick={() => navigate(s.path)}>
        <Ico d={s.icon} size={15} color={TONE[s.tone]?.c || TONE.accent.c} />
        {s.label}
      </button>
    ))}
  </div>
);

// ─── Squelette de chargement ────────────────────────────────────────────────────
const Skeleton = () => (
  <div style={S.page}>
    <div style={{ width: '160px', height: '14px', borderRadius: '4px', marginBottom: '10px' }} className="ds-skeleton" />
    <div style={{ width: '220px', height: '28px', borderRadius: '6px', marginBottom: '24px' }} className="ds-skeleton" />
    <div style={S.kpiRow}>
      {[0, 1, 2, 3].map(i => (
        <div key={i} className="ds-skeleton" style={{ height: '112px', borderRadius: '10px' }} />
      ))}
    </div>
    <div style={S.mainGrid}>
      <div className="ds-skeleton" style={{ height: '220px', borderRadius: '10px' }} />
      <div className="ds-skeleton" style={{ height: '220px', borderRadius: '10px' }} />
    </div>
  </div>
);

export default function Dashboard() {
  const { user }              = useAuth();
  const navigate              = useNavigate();
  const [data,    setData]    = useState(null);
  const [logs,    setLogs]    = useState([]);
  const [loading, setLoading] = useState(true);

  const isDG          = user?.is_dg  || user?.role === 'dg';
  const isDOP         = user?.is_ops_chief || user?.role === 'chef_ops';
  const isPM          = user?.is_project_manager || user?.role === 'chef_projet';
  const isMagasinier  = user?.role === 'magasinier';
  const isFinancial   = user?.is_financial_officer || user?.role === 'financier';
  const isStock       = user?.is_stock_manager || user?.role === 'stock';
  const isOpsOrPm     = isDOP || isPM;

  useEffect(() => {
    // Empêche les setState (et l'appel audit-logs, déclenché après les
    // premiers appels) de se déclencher si l'utilisateur se déconnecte ou
    // change de page pendant que la chaîne de requêtes est encore en vol —
    // sinon la dernière requête part sans token valide (401 côté serveur).
    let cancelled = false;
    fetchData(() => cancelled);
    return () => { cancelled = true; };
  }, []); // eslint-disable-line

  const fetchData = async (isCancelled) => {
    try {
      // Le Responsable Financier ne gère ni stock ni produits ni projets —
      // il utilise ses propres endpoints dédiés (financial-dashboard /
      // financial-history) plutôt que les appels génériques ci-dessous,
      // qui renverraient des données hors de son périmètre métier.
      if (isFinancial) {
        const [fdRes, fhRes] = await Promise.all([
          api.get('/requests/financial-dashboard/').catch(() => ({ data: {} })),
          api.get('/requests/financial-history/').catch(() => ({ data: [] })),
        ]);
        if (isCancelled()) return;
        const history = fhRes.data.results ?? fhRes.data ?? [];
        setData({ financial: fdRes.data, financialHistory: history.slice(0, 6) });
        return;
      }

      const calls = [
        api.get('/products/stats/').catch(() => ({ data: {} })),
        api.get('/requests/pending-count/').catch(() => ({ data: {} })),
        api.get('/stock/movements/alertes/').catch(() => ({ data: { results: [] } })),
        api.get('/requests/?ordering=-created_at').catch(() => ({ data: [] })),
        api.get('/operations/projects/stats/').catch(() => ({ data: {} })),
        api.get('/requests/stats/').catch(() => ({ data: {} })),
        isMagasinier ? api.get('/stock/warehouses/').catch(() => ({ data: [] })) : Promise.resolve({ data: [] }),
      ];

      const [pRes, pcRes, aRes, rListRes, opRes, rStatsRes, whRes] = await Promise.all(calls);
      if (isCancelled()) return;

      const allRequests = rListRes.data.results ?? rListRes.data ?? [];
      const warehouses  = whRes.data.results ?? whRes.data ?? [];

      setData({
        products:      pRes.data,
        pendingCount:  pcRes.data?.pending || 0,
        alerts:        aRes.data.results?.slice(0, 6) || [],
        orders:        allRequests.slice(0, 6),
        operations:    opRes.data,
        requestStats:  rStatsRes.data,
        warehouse:     warehouses[0] || null,
      });

      if (isDG) {
        const logRes = await api.get('/accounts/audit-logs/').catch(() => ({ data: [] }));
        if (isCancelled()) return;
        setLogs((logRes.data.results || logRes.data).slice(0, 6));
      }
    } catch (err) { console.error(err); }
    finally { if (!isCancelled()) setLoading(false); }
  };

  if (loading || !data) return <Skeleton />;

  const today    = new Date();
  const todayStr = today.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  const todayFmt = todayStr.charAt(0).toUpperCase() + todayStr.slice(1);
  const fmtNum   = (n) => Number(n || 0).toLocaleString('fr-FR');

  // ── Données dérivées pour les graphiques ─────────────────────────────────────
  const requestDonutData = [
    { label: 'En attente DOP', value: data.requestStats?.en_attente_dop    || 0, color: TONE[STATUS_STYLE.en_attente_dop.tone].c },
    { label: 'En attente DG',  value: data.requestStats?.en_attente_dg     || 0, color: TONE[STATUS_STYLE.en_attente_dg.tone].c },
    { label: 'Urgentes (DOP ou DG)', value: data.requestStats?.en_attente_dop_dg || 0, color: TONE[STATUS_STYLE.en_attente_dop_dg.tone].c },
    { label: 'Validées',       value: data.requestStats?.validee            || 0, color: TONE[STATUS_STYLE.validee.tone].c },
    { label: 'Exécutées',      value: data.requestStats?.executee           || 0, color: TONE[STATUS_STYLE.executee.tone].c },
    { label: 'Refusées',       value: data.requestStats?.refusee            || 0, color: TONE[STATUS_STYLE.refusee.tone].c },
  ].filter(d => d.value > 0);

  const stockDonutData = [
    { label: 'Suffisant', value: data.products?.stock_ok || 0, color: TONE.success.c },
    { label: 'Critique',  value: data.products?.stock_critique  || 0, color: TONE.warningAlt.c },
    { label: 'Rupture',   value: data.products?.stock_rupture   || 0, color: TONE.danger.c },
  ].filter(d => d.value > 0);

  const projectBarData = [
    { label: 'En cours',  value: data.operations?.en_cours  || 0, color: TONE.accent.c },
    { label: 'Suspendus', value: data.operations?.suspendu  || 0, color: TONE.warningAlt.c },
    { label: 'Terminés',  value: data.operations?.termine   || 0, color: TONE.success.c },
    { label: 'Brouillons',value: data.operations?.brouillon || 0, color: TONE.muted.c },
  ];

  // ── KPIs selon rôle ───────────────────────────────────────────────────────
  const kpis = isDG ? [
    { label: 'En attente DG',  value: data.pendingCount,                    tone: 'warningAlt', sub: 'à valider maintenant',   path: '/requests',             icon: D.clock    },
    { label: 'Projets actifs', value: data.operations?.en_cours || 0,       tone: 'accent',     sub: 'en cours d\'exécution',  path: '/operations-dashboard', icon: D.trending },
    { label: 'Total demandes', value: data.requestStats?.total || 0,        tone: 'info',       sub: 'toutes catégories',       path: '/requests',             icon: D.doc      },
    { label: 'Alertes stock',  value: data.products?.stock_critique || 0,   tone: 'danger',     sub: 'produits critiques',      path: '/products',             icon: D.alert    },
  ] : isDOP ? [
    { label: 'En attente DOP', value: data.pendingCount,                    tone: 'warning',    sub: 'à valider',               path: '/requests',             icon: D.clock    },
    { label: 'Projets actifs', value: data.operations?.en_cours || 0,       tone: 'accent',     sub: 'en cours',                path: '/operations-dashboard', icon: D.trending },
    { label: 'Demandes total', value: data.requestStats?.total || 0,        tone: 'info',       sub: 'toutes',                  path: '/requests',             icon: D.doc      },
    { label: 'Suspendus',      value: data.operations?.suspendu || 0,       tone: 'warningAlt', sub: 'projets en pause',        path: '/operations',           icon: D.clock    },
  ] : isPM ? [
    { label: 'Mes projets',    value: data.operations?.total || 0,          tone: 'accent',     sub: 'tous statuts',            path: '/operations',           icon: D.trending },
    { label: 'En cours',       value: data.operations?.en_cours || 0,       tone: 'success',    sub: 'actifs',                  path: '/operations',           icon: D.check    },
    { label: 'Mes demandes',   value: data.requestStats?.total || 0,        tone: 'info',       sub: 'toutes',                  path: '/requests',             icon: D.doc      },
    { label: 'Suspendus',      value: data.operations?.suspendu || 0,       tone: 'warningAlt', sub: 'en pause',                path: '/operations',           icon: D.clock    },
  ] : isMagasinier ? [
    { label: 'Mon magasin',    value: data.warehouse ? 1 : 0,                tone: 'accent',     sub: data.warehouse?.name || 'Non assigné', path: null, icon: D.warehouse, isText: !!data.warehouse },
    { label: 'Mes demandes',   value: data.requestStats?.total || 0,        tone: 'info',       sub: 'toutes catégories',       path: '/requests',             icon: D.doc      },
    { label: 'En attente',     value: (data.requestStats?.en_attente_dop||0) + (data.requestStats?.en_attente_dg||0) + (data.requestStats?.en_attente_dop_dg||0), tone: 'warning', sub: 'en cours de validation', path: '/requests', icon: D.clock },
    { label: 'Exécutées',      value: data.requestStats?.executee || 0,     tone: 'success',    sub: 'demandes traitées',       path: '/requests',             icon: D.check    },
  ] : isFinancial ? [
    { label: 'À exécuter',              value: data.financial?.to_execute_count || 0,          tone: 'success', sub: 'achats validés en attente',  path: '/financial-execution', icon: D.check    },
    { label: 'Valeur à exécuter',        value: data.financial?.to_execute_total_value || 0,    tone: 'accent',  sub: 'montant total (F CFA)',      path: '/financial-execution', icon: D.trending, isCurrency: true },
    { label: 'Demandes urgentes',        value: data.financial?.urgent_count || 0,              tone: 'danger',  sub: 'priorité immédiate',          path: '/financial-execution', icon: D.alert    },
    { label: 'Exécutées aujourd\'hui',   value: data.financial?.executed_today_count || 0,      tone: 'info',    sub: 'commandes du jour',           path: '/financial-history',   icon: D.clock    },
    { label: 'Exécutées ce mois',        value: data.financial?.executed_this_month_count || 0, tone: 'muted',   sub: 'total du mois en cours',      path: '/financial-history',   icon: D.doc      },
  ] : [
    { label: 'En attente',     value: data.pendingCount,                    tone: 'warningAlt', sub: 'à valider maintenant',    path: '/validations',          icon: D.clock    },
    { label: 'Stock critique', value: data.products?.stock_critique || 0,   tone: 'warningAlt', sub: 'sous seuil de sécurité',  path: '/products',             icon: D.alert    },
    { label: 'Ruptures',       value: data.products?.stock_rupture || 0,    tone: 'danger',     sub: 'stock à zéro',            path: '/products',             icon: D.alert    },
    { label: 'Mes demandes',   value: data.requestStats?.total || 0,        tone: 'success',    sub: 'toutes catégories',       path: '/requests',             icon: D.doc      },
  ];

  // ── Raccourcis selon rôle ─────────────────────────────────────────────────
  const shortcuts = isDG ? [
    { label: 'Demandes à valider', path: '/requests', icon: D.clock, tone: 'warningAlt' },
    { label: 'Nouveau magasin',    path: '/warehouses', icon: D.plus, tone: 'accent' },
    { label: 'Administration',     path: '/administration', icon: D.users, tone: 'info' },
  ] : isDOP ? [
    { label: 'Demandes à valider', path: '/requests', icon: D.clock, tone: 'warning' },
    { label: 'Nouveau projet',     path: '/operations', icon: D.plus, tone: 'accent' },
    { label: 'Chefs de projet',    path: '/project-managers', icon: D.users, tone: 'info' },
  ] : isPM ? [
    { label: 'Nouvelle demande', path: '/requests', icon: D.plus, tone: 'accent' },
    { label: 'Mes projets',      path: '/operations', icon: D.trending, tone: 'success' },
  ] : isMagasinier ? [
    { label: 'Nouvelle demande', path: '/requests', icon: D.plus, tone: 'accent' },
    { label: 'Mon stock',       path: '/my-stock', icon: D.box, tone: 'info' },
  ] : isFinancial ? [
    { label: 'Demandes à exécuter',    path: '/financial-execution', icon: D.check, tone: 'success' },
    { label: 'Historique des exécutions', path: '/financial-history', icon: D.doc, tone: 'info' },
  ] : [
    { label: 'Demandes à valider', path: '/validations', icon: D.clock, tone: 'warningAlt' },
    { label: 'Nouvelle demande',   path: '/requests', icon: D.plus, tone: 'accent' },
    { label: 'Produits',           path: '/products', icon: D.box, tone: 'warningAlt' },
    { label: 'Fournisseurs',       path: '/suppliers', icon: D.users, tone: 'info' },
  ];

  const roleLabel = isDG ? 'Directeur Général' : isDOP ? 'DOP' : isPM ? 'Chef de Projet' : isMagasinier ? 'Magasinier' : isFinancial ? 'Responsable Financier' : 'RAL';
  const roleTitle  = isDOP ? 'Directrice des Opérations' : isStock ? 'Responsable Achat et Logistique' : undefined;
  const roleTone  = isDG ? 'warningAlt' : isDOP ? 'accent' : isPM ? 'info' : isMagasinier ? 'success' : isFinancial ? 'info' : 'success';

  return (
    <div style={S.page}>
      <style>{`
        @keyframes dashFadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes dashBarGrow { from { width: 0 !important; } }
        .dash-kpi, .dash-card { animation: dashFadeUp 320ms var(--ease-out) backwards; }
        .dash-bar-fill { animation: dashBarGrow 500ms var(--ease-out) backwards; }
        .dash-kpi { transition: transform 160ms var(--ease-out), border-color 160ms ease; }
        .dash-kpi:hover { transform: translateY(-2px); border-color: var(--border-default); }
        .dash-kpi:active { transform: scale(0.98); }
        .dash-shortcut { transition: transform 140ms var(--ease-out), background 140ms ease, border-color 140ms ease; }
        .dash-shortcut:hover { border-color: var(--border-default); background: var(--bg-surface-alt); }
        .dash-shortcut:active { transform: scale(0.96); }
        .dash-link:hover { opacity: .8; }
        @media (prefers-reduced-motion: reduce) {
          .dash-kpi, .dash-card, .dash-bar-fill { animation: none !important; }
        }
      `}</style>

      {/* ── En-tête ──────────────────────────────────────────────────────── */}
      <div style={S.pageHeader}>
        <div style={S.eyebrow}>{todayFmt}</div>
        <h1 style={S.pageTitle}>Dashboard</h1>
        <p style={S.pageSub}>
          Bonjour, <strong style={{ color: 'var(--text-secondary)' }}>{user?.full_name || user?.username}</strong>
          <span style={S.rolePill(TONE[roleTone].c, TONE[roleTone].bg)} title={roleTitle}>{roleLabel}</span>
        </p>
      </div>

      {/* ── Raccourcis ───────────────────────────────────────────────────── */}
      <ShortcutRow shortcuts={shortcuts} navigate={navigate} />

      {/* ── KPIs ─────────────────────────────────────────────────────────── */}
      <div style={S.kpiRow}>
        {kpis.map((k, i) => {
          const tone = TONE[k.tone];
          return (
            <div key={k.label} className="dash-kpi" style={{ ...S.kpiCard, cursor: k.path ? 'pointer' : 'default', animationDelay: `${i * 50}ms` }} onClick={() => k.path && navigate(k.path)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div style={{ ...S.kpiDot, background: tone.bg }}>
                  <Ico d={k.icon} size={16} color={tone.c} />
                </div>
                {k.path && <Ico d={D.arrow_right} size={14} color="var(--border-default)" />}
              </div>
              {k.isText ? (
                <div style={{ ...S.kpiValue, fontSize: '1.15rem', color: tone.c }}>{data.warehouse?.code}</div>
              ) : k.isCurrency ? (
                <div style={{ ...S.kpiValue, fontSize: '1.4rem', color: tone.c }}>{fmtNum(k.value)} F</div>
              ) : (
                <div style={{ ...S.kpiValue, color: tone.c }}>{fmtNum(k.value)}</div>
              )}
              <div style={S.kpiLabel}>{k.label}</div>
              <div style={S.kpiSub}>{k.sub}</div>
            </div>
          );
        })}
      </div>

      {/* ── Contenu selon rôle ───────────────────────────────────────────── */}
      {isFinancial ? (
        /* ── Vue Responsable Financier ───────────────────────────────────────
           Aucune donnée de stock/produits/magasins/circuit logistique — hors
           périmètre métier (audit UX Évolution 7). Seul l'historique de ses
           propres exécutions est affiché ici, en complément des KPIs. */
        <div style={S.mainGrid}>
          <div className="dash-card" style={{ ...S.card, animationDelay: '80ms' }}>
            <div style={S.cardHead}>
              <div>
                <div style={S.cardTitle}>Historique récent de mes exécutions</div>
                <div style={S.cardSub}>{data.financialHistory.length} exécution(s) récente(s)</div>
              </div>
              <button style={S.linkBtn} className="dash-link" onClick={() => navigate('/financial-history')}>Voir tout →</button>
            </div>
            <div style={S.cardBody}>
              {data.financialHistory.length === 0 ? (
                <div style={S.emptyText}>Aucune exécution pour l'instant</div>
              ) : data.financialHistory.map(o => (
                <div key={o.id} style={S.orderRow} onClick={() => navigate('/financial-history')}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={S.orderRef}>{o.reference}</div>
                    <div style={S.orderSup}>{o.project_name || 'Sans projet'} — {o.requested_by_name || '–'}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    {o.total_amount > 0 && <span style={S.orderAmount}>{fmtNum(o.total_amount)} F</span>}
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)', fontFamily: 'monospace', flexShrink: 0 }}>
                      {o.financial_execution_at ? new Date(o.financial_execution_at).toLocaleDateString('fr-FR') : '–'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : isMagasinier ? (
        /* ── Vue Magasinier ───────────────────────────────────────────────── */
        <div style={S.mainGrid}>
          <div className="dash-card" style={{ ...S.card, animationDelay: '80ms' }}>
            <div style={S.cardHead}>
              <div>
                <div style={S.cardTitle}>Mes demandes récentes</div>
                <div style={S.cardSub}>{data.orders.length} demande(s)</div>
              </div>
              <button style={S.linkBtn} className="dash-link" onClick={() => navigate('/requests')}>Voir tout →</button>
            </div>
            <div style={S.cardBody}>
              {data.orders.length === 0 ? (
                <div style={S.emptyText}>Aucune demande pour l'instant</div>
              ) : data.orders.map(o => {
                const st = STATUS_STYLE[o.status] || STATUS_STYLE.brouillon;
                return (
                  <div key={o.id} style={S.orderRow} onClick={() => navigate('/requests')}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={S.orderRef}>{o.reference}</div>
                      <div style={S.orderSup}>{o.request_type_display}</div>
                    </div>
                    <span style={{ ...S.statusBadge, background: TONE[st.tone].bg, color: TONE[st.tone].c }}>{statusLabel(o)}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="dash-card" style={{ ...S.card, animationDelay: '130ms' }}>
            <div style={S.cardHead}>
              <div>
                <div style={S.cardTitle}>Répartition de mes demandes</div>
                <div style={S.cardSub}>Par statut</div>
              </div>
            </div>
            <div style={{ ...S.cardBody, display: 'flex', alignItems: 'center', gap: '18px' }}>
              <Donut data={requestDonutData} />
              <DonutLegend data={requestDonutData.length ? requestDonutData : [{ label: 'Aucune donnée', value: 0, color: 'var(--border-default)' }]} />
            </div>
          </div>
        </div>
      ) : isOpsOrPm ? (
        /* ── Vue Opérations / Chef de Projet ─────────────────────────────── */
        <div style={S.mainGrid}>
          <div style={S.col}>
            <div className="dash-card" style={{ ...S.card, animationDelay: '80ms' }}>
              <div style={S.cardHead}>
                <div>
                  <div style={S.cardTitle}>Projets par statut</div>
                  <div style={S.cardSub}>Suivi des opérations</div>
                </div>
                <button style={S.linkBtn} className="dash-link" onClick={() => navigate('/operations-dashboard')}>
                  Tableau de bord →
                </button>
              </div>
              <div style={S.cardBody}>
                <StatusBars data={projectBarData} />
              </div>
            </div>

            {/* Demandes récentes */}
            <div className="dash-card" style={{ ...S.card, animationDelay: '130ms' }}>
              <div style={S.cardHead}>
                <div>
                  <div style={S.cardTitle}>Demandes récentes</div>
                  <div style={S.cardSub}>{data.orders.length} demande(s)</div>
                </div>
                <button style={S.linkBtn} className="dash-link" onClick={() => navigate('/requests')}>Voir tout →</button>
              </div>
              <div style={S.cardBody}>
                {data.orders.length === 0 ? (
                  <div style={S.emptyText}>Aucune demande</div>
                ) : data.orders.map(o => {
                  const st = STATUS_STYLE[o.status] || STATUS_STYLE.brouillon;
                  return (
                    <div key={o.id} style={S.orderRow} onClick={() => navigate('/requests')}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={S.orderRef}>{o.reference}</div>
                        <div style={S.orderSup}>{o.request_type_display} — {o.requested_by_name || '–'}</div>
                      </div>
                      <span style={{ ...S.statusBadge, background: TONE[st.tone].bg, color: TONE[st.tone].c }}>{statusLabel(o)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div style={S.col}>
            {/* Stats demandes — donut */}
            <div className="dash-card" style={{ ...S.card, animationDelay: '100ms' }}>
              <div style={S.cardHead}>
                <div>
                  <div style={S.cardTitle}>Statut des demandes</div>
                  <div style={S.cardSub}>{data.requestStats?.total || 0} au total</div>
                </div>
                <button style={S.linkBtn} className="dash-link" onClick={() => navigate('/requests')}>Voir tout →</button>
              </div>
              <div style={{ ...S.cardBody, display: 'flex', alignItems: 'center', gap: '18px' }}>
                <Donut data={requestDonutData} />
                <DonutLegend data={requestDonutData.length ? requestDonutData : [{ label: 'Aucune donnée', value: 0, color: 'var(--border-default)' }]} />
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* ── Vue DG / Responsable Achat et Logistique ──────────────────────────────────── */
        <div style={S.mainGrid}>
          <div style={S.col}>

            {/* Alertes Stock */}
            <div className="dash-card" style={{ ...S.card, animationDelay: '80ms' }}>
              <div style={S.cardHead}>
                <div>
                  <div style={{ ...S.cardTitle, color: 'var(--warning-alt)' }}>Alertes Stock</div>
                  <div style={S.cardSub}>{data.alerts.length} produit(s) sous seuil</div>
                </div>
                <button style={S.linkBtn} className="dash-link" onClick={() => navigate('/products')}>Voir tout →</button>
              </div>
              <div style={S.cardBody}>
                {data.alerts.length === 0 ? (
                  <div style={S.allGood}>
                    <div style={S.allGoodDot} />
                    <span style={{ color: 'var(--success)', fontWeight: '600', fontSize: '0.875rem' }}>
                      Tous les stocks sont suffisants
                    </span>
                  </div>
                ) : data.alerts.map(p => (
                  <div key={p.id} style={S.alertRow}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span style={S.alertCode}>{p.code}</span>
                      <span style={S.alertName}>{p.designation}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                      <span style={S.alertStock}>{p.stock_actuel}/{p.stock_securite}</span>
                      <span style={{
                        ...S.alertBadge,
                        background: p.stock_status === 'rupture' ? 'var(--danger-bg)' : 'var(--warning-alt-bg)',
                        color:      p.stock_status === 'rupture' ? 'var(--danger)' : 'var(--warning-alt)',
                      }}>
                        {p.stock_status === 'rupture' ? 'Rupture' : 'Critique'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Demandes récentes */}
            <div className="dash-card" style={{ ...S.card, animationDelay: '130ms' }}>
              <div style={S.cardHead}>
                <div>
                  <div style={S.cardTitle}>{(isDG || isStock) ? 'Demandes à valider' : 'Demandes récentes'}</div>
                  <div style={S.cardSub}>{data.orders.length} demande(s)</div>
                </div>
                <button style={S.linkBtn} className="dash-link" onClick={() => navigate(isStock ? '/validations' : '/requests')}>Voir tout →</button>
              </div>
              <div style={S.cardBody}>
                {data.orders.length === 0 ? (
                  <div style={S.emptyText}>Aucune demande</div>
                ) : data.orders.map(o => {
                  const st = STATUS_STYLE[o.status] || STATUS_STYLE.brouillon;
                  return (
                    <div key={o.id} style={S.orderRow} onClick={() => navigate(isStock ? '/validations' : '/requests')}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={S.orderRef}>{o.reference}</div>
                        <div style={S.orderSup}>{o.request_type_display} — {o.requested_by_name || '–'}</div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        {o.total_amount > 0 && (
                          <span style={S.orderAmount}>{fmtNum(o.total_amount)} F</span>
                        )}
                        <span style={{ ...S.statusBadge, background: TONE[st.tone].bg, color: TONE[st.tone].c }}>{statusLabel(o)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div style={S.col}>

            {/* État des stocks — donut */}
            <div className="dash-card" style={{ ...S.card, animationDelay: '100ms' }}>
              <div style={S.cardHead}>
                <div>
                  <div style={S.cardTitle}>État des Stocks</div>
                  <div style={S.cardSub}>{data.products?.total_produits || 0} produit(s) référencé(s)</div>
                </div>
                <button style={S.linkBtn} className="dash-link" onClick={() => navigate('/products')}>Voir tout →</button>
              </div>
              <div style={{ ...S.cardBody, display: 'flex', alignItems: 'center', gap: '18px' }}>
                <Donut data={stockDonutData} />
                <DonutLegend data={stockDonutData.length ? stockDonutData : [{ label: 'Aucun produit', value: 0, color: 'var(--border-default)' }]} />
              </div>
            </div>

            {/* Stats demandes (Responsable Achat et Logistique) ou Traçabilité (DG) */}
            <div className="dash-card" style={{ ...S.card, animationDelay: '150ms' }}>
              <div style={S.cardHead}>
                <div>
                  <div style={S.cardTitle}>{(isDG || isStock) ? 'Statistiques Demandes' : 'Mes Demandes'}</div>
                  <div style={S.cardSub}>{data.requestStats?.total || 0} au total</div>
                </div>
                <button style={S.linkBtn} className="dash-link" onClick={() => navigate('/requests')}>Voir tout →</button>
              </div>
              <div style={{ ...S.cardBody, display: 'flex', alignItems: 'center', gap: '18px' }}>
                <Donut data={requestDonutData} />
                <DonutLegend data={requestDonutData.length ? requestDonutData : [{ label: 'Aucune donnée', value: 0, color: 'var(--border-default)' }]} />
              </div>
            </div>

            {/* Traçabilité — DG uniquement */}
            {isDG && logs.length > 0 && (
              <div className="dash-card" style={{ ...S.card, animationDelay: '200ms' }}>
                <div style={S.cardHead}>
                  <div>
                    <div style={S.cardTitle}>Traçabilité</div>
                    <div style={S.cardSub}>Dernières actions système</div>
                  </div>
                  <button style={S.linkBtn} className="dash-link" onClick={() => navigate('/audit')}>Voir tout →</button>
                </div>
                <div style={S.cardBody}>
                  {logs.map(log => (
                    <div key={log.id} style={S.traceRow}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', flex: 1, minWidth: 0 }}>
                        <div style={{ width: '7px', height: '7px', borderRadius: '50%', background: TONE[ACTION_TONE[log.action]]?.c || TONE.muted.c, flexShrink: 0 }} />
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{log.description}</div>
                          <div style={{ fontSize: '0.68rem', color: 'var(--text-disabled)', marginTop: '1px' }}>
                            {ACTION_LABELS[log.action] || log.action}
                          </div>
                        </div>
                      </div>
                      <span style={{ fontSize: '0.68rem', color: 'var(--text-disabled)', fontFamily: 'monospace', flexShrink: 0, marginLeft: '0.5rem' }}>
                        {new Date(log.created_at).toLocaleDateString('fr-FR')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Helper style ─────────────────────────────────────────────────────────────
const S = {
  page:        { color: 'var(--text-secondary)', fontFamily: 'var(--font-sans)' },
  pageHeader:  { marginBottom: '1.25rem' },
  eyebrow:     { fontSize: '0.72rem', fontWeight: '600', color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '1.5px', marginBottom: '0.375rem' },
  pageTitle:   { fontSize: '1.75rem', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-0.5px', margin: 0 },
  pageSub:     { fontSize: '0.83rem', color: 'var(--text-faint)', marginTop: '0.25rem', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' },
  rolePill:    (c, bg) => ({ fontSize: '0.7rem', fontWeight: '700', color: c, background: bg, padding: '2px 10px', borderRadius: '20px', border: '1px solid transparent' }),

  shortcutRow: { display: 'flex', gap: '0.625rem', marginBottom: '1.25rem', flexWrap: 'wrap' },
  shortcutBtn: { display: 'flex', alignItems: 'center', gap: '7px', padding: '0.55rem 0.9rem', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '9px', color: 'var(--text-secondary)', fontSize: '0.8rem', fontWeight: '600', cursor: 'pointer' },

  kpiRow:      { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '0.875rem', marginBottom: '1.25rem' },
  kpiCard:     { background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '1.1rem 1.25rem', cursor: 'pointer' },
  kpiDot:      { width: '32px', height: '32px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  kpiValue:    { fontSize: '2.25rem', fontWeight: '800', letterSpacing: '-1.5px', lineHeight: 1, marginBottom: '0.2rem', marginTop: '0.5rem' },
  kpiLabel:    { fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '0.15rem' },
  kpiSub:      { fontSize: '0.7rem', color: 'var(--text-faint)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },

  mainGrid:    { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '0.875rem', alignItems: 'start' },
  col:         { display: 'flex', flexDirection: 'column', gap: '0.875rem', minWidth: 0 },

  card:        { background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '10px', overflow: 'hidden' },
  cardHead:    { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '1rem 1.1rem 0.75rem', borderBottom: '1px solid var(--border-faint)' },
  cardTitle:   { fontSize: '0.9rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '0.15rem' },
  cardSub:     { fontSize: '0.72rem', color: 'var(--text-faint)' },
  cardBody:    { padding: '0.875rem 1.1rem' },
  linkBtn:     { background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: '600', flexShrink: 0, transition: 'opacity 140ms ease' },

  alertRow:    { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', padding: '0.5rem 0', borderBottom: '1px solid var(--border-faint)' },
  alertCode:   { fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--accent-light)', marginRight: '0.5rem' },
  alertName:   { fontSize: '0.78rem', color: 'var(--text-tertiary)' },
  alertStock:  { fontSize: '0.7rem', fontFamily: 'monospace', color: 'var(--text-disabled)' },
  alertBadge:  { padding: '0.15rem 0.55rem', borderRadius: '4px', fontSize: '0.7rem', fontWeight: '700', flexShrink: 0 },
  allGood:     { display: 'flex', alignItems: 'center', gap: '0.625rem', padding: '1rem 0' },
  allGoodDot:  { width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)', flexShrink: 0 },

  orderRow:    { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', padding: '0.55rem 0', borderBottom: '1px solid var(--border-faint)', cursor: 'pointer' },
  orderRef:    { fontFamily: 'monospace', fontSize: '0.78rem', color: 'var(--accent-light)', fontWeight: '600' },
  orderSup:    { fontSize: '0.72rem', color: 'var(--text-disabled)', marginTop: '1px' },
  orderAmount: { fontSize: '0.78rem', fontFamily: 'monospace', color: 'var(--text-secondary)', fontWeight: '600', flexShrink: 0 },
  statusBadge: { padding: '0.15rem 0.55rem', borderRadius: '4px', fontSize: '0.7rem', fontWeight: '700', flexShrink: 0 },

  traceRow:    { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--border-faint)' },
  emptyText:   { color: 'var(--text-disabled)', fontSize: '0.82rem', textAlign: 'center', padding: '1.25rem 0' },
};
