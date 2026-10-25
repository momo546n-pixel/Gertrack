import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';
import NotificationBell from './NotificationBell';
import GertechLogo from './GertechLogo';
import { ThemeToggle } from '../design-system';
import { sidebarConfigByRole } from '../config/sidebarConfig';

const Icon = ({ path, size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <path d={path} />
  </svg>
);

const ICONS = {
  dashboard:     'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z M9 22V12h6v10',
  operations:    'M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7',
  ops_dashboard: 'M3 3v18h18 M18 17V9 M13 17V5 M8 17v-3',
  purchases:     'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
  products:      'M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z',
  stock:         'M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4',
  suppliers:     'M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2 M9 11a4 4 0 100-8 4 4 0 000 8z M23 21v-2a4 4 0 00-3-3.87 M16 3.13a4 4 0 010 7.75',
  audit:         'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
  logout:        'M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1',
  chevronRight:  'M9 18l6-6-6-6',
  chevronLeft:   'M15 18l-6-6 6-6',
  requests: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2 M12 12h.01M12 16h.01',
  warehouses:    'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z M9 22V12h6v10',
  chefsprojet:   'M2 7h20v13a2 2 0 01-2 2H4a2 2 0 01-2-2z M8 21V5a2 2 0 012-2h4a2 2 0 012 2v16 M2 12h20',
  administration:'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
  menu:          'M3 12h18M3 6h18M3 18h18',
  validation:    'M22 11.08V12a10 10 0 11-5.93-9.14 M22 4L12 14.01l-3-3',
  circuit:       'M6 3v12a3 3 0 003 3h9 M9 3v12a3 3 0 003 3h3 M15 3h4v4 M15 3l5 5 M6 21a2 2 0 100-4 2 2 0 000 4z',
  budget:        'M12 1v22 M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6',
};

const MOBILE_BREAKPOINT = 860;
const TABLET_MAX_WIDTH  = 1180;

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate          = useNavigate();
  const { pathname }      = useLocation();
  const [expanded, setExpanded]     = useState(false);
  const [isMobile, setIsMobile]     = useState(window.innerWidth < MOBILE_BREAKPOINT);
  const [isTablet, setIsTablet]     = useState(window.innerWidth >= MOBILE_BREAKPOINT && window.innerWidth < TABLET_MAX_WIDTH);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onResize = () => {
      const w = window.innerWidth;
      const mobile = w < MOBILE_BREAKPOINT;
      setIsMobile(mobile);
      setIsTablet(!mobile && w < TABLET_MAX_WIDTH);
      if (!mobile) setMobileOpen(false);
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => { setMobileOpen(false); }, [pathname]);

  const sections = sidebarConfigByRole(user);

  const roleLabel = user?.is_dg              ? 'Directeur Général'
                  : user?.is_ops_chief       ? 'DOP'
                  : user?.is_project_manager ? 'Chef de Projet'
                  : user?.role === 'magasinier' ? 'Magasinier'
                  : (user?.is_financial_officer || user?.role === 'financier') ? 'Responsable Financier'
                  : 'RAL';

  const roleTitle = user?.is_ops_chief ? 'Directrice des Opérations'
                   : (!user?.is_dg && !user?.is_ops_chief && !user?.is_project_manager
                      && user?.role !== 'magasinier' && !user?.is_financial_officer && user?.role !== 'financier') ? 'Responsable Achat et Logistique'
                   : undefined;

  const handleLogout = () => {
    logout();
    toast.success('Déconnexion réussie');
    navigate('/login');
  };

  const isActive = (p) =>
    pathname === p || (p === '/operations' && pathname.startsWith('/operations/'));

  // Desktop : l'utilisateur choisit (expanded) ; Tablette : toujours compacte ;
  // Mobile : le tiroir est toujours "large" quand ouvert.
  const sidebarExpanded = isMobile ? true : isTablet ? false : expanded;
  const sidebarW = isMobile ? '240px' : isTablet ? '64px' : (expanded ? '224px' : '64px');

  return (
    <div style={S.shell}>
      <style>{`
        @keyframes layoutActiveBarIn { from { transform: translateY(-50%) scaleY(0.2); opacity: 0; } to { transform: translateY(-50%) scaleY(1); opacity: 1; } }
        .layout-navitem { transition: background 160ms ease, transform 120ms var(--ease-out); }
        .layout-navitem:hover { background: var(--bg-hover); }
        .layout-navitem:active { transform: scale(0.985); }
        .layout-activebar { animation: layoutActiveBarIn 200ms var(--ease-out) both; }
        .layout-iconbtn { transition: transform 140ms var(--ease-out), background 140ms ease, border-color 140ms ease, color 140ms ease; }
        .layout-iconbtn:active { transform: scale(0.92); }
        .layout-iconbtn:hover { border-color: var(--border-default); background: var(--bg-hover); color: var(--text-secondary); }
        .layout-backdrop { animation: dsFadeIn 200ms ease-out both; }
        @media (prefers-reduced-motion: reduce) {
          .layout-navitem, .layout-activebar, .layout-iconbtn, .layout-backdrop { animation: none !important; transition: none !important; }
        }
      `}</style>

      {/* ── Barre supérieure ─────────────────────────────────────────── */}
      <header style={S.topBar}>
        <div style={S.topLeft}>
          {isMobile && (
            <button className="layout-iconbtn" style={S.hamburgerBtn} onClick={() => setMobileOpen(o => !o)} title="Menu">
              <Icon path={ICONS.menu} size={19} />
            </button>
          )}
          <GertechLogo size={34} textSize="1.05rem" />
        </div>
        <div style={S.topRight}>
          <ThemeToggle />
          <NotificationBell />
          <div style={S.userPill}>
            <div style={S.userAvatar}>
              {(user?.full_name || user?.username || 'U').charAt(0).toUpperCase()}
            </div>
            {!isMobile && (
              <div style={S.userInfo}>
                <span style={S.userName}>{user?.full_name || user?.username}</span>
                <span style={S.userRole} title={roleTitle}>{roleLabel}</span>
              </div>
            )}
          </div>
          <button className="layout-iconbtn" onClick={handleLogout} style={S.logoutBtn} title="Déconnexion">
            <Icon path={ICONS.logout} size={16} />
          </button>
        </div>
      </header>

      <div style={S.body}>

        {/* ── Backdrop mobile ──────────────────────────────────────────── */}
        {isMobile && mobileOpen && (
          <div className="layout-backdrop" style={S.backdrop} onClick={() => setMobileOpen(false)} />
        )}

        {/* ── Sidebar ──────────────────────────────────────────────────── */}
        <aside style={isMobile ? {
          ...S.sidebar, ...S.sidebarMobile, width: sidebarW,
          transform: mobileOpen ? 'translateX(0)' : 'translateX(-100%)',
        } : { ...S.sidebar, width: sidebarW }}>

          <div style={S.navList}>
            {sections.map((group, gi) => (
              <div key={group.section} style={{ ...S.navGroup, ...(gi === 0 ? S.navGroupFirst : {}) }}>
                {sidebarExpanded ? (
                  <div style={S.sectionLabel}>{group.section}</div>
                ) : gi > 0 ? (
                  <div style={S.sectionDivider} />
                ) : null}
                {group.items.map(item => {
                  const active = isActive(item.path);
                  return (
                    <div
                      key={item.path}
                      className="layout-navitem"
                      style={{ ...S.navItem, ...(active ? S.navItemActive : {}) }}
                      onClick={() => navigate(item.path)}
                      title={!sidebarExpanded ? item.label : ''}
                    >
                      {active && <div className="layout-activebar" style={S.activeBar} />}
                      <div style={{ ...S.navIcon, ...(active ? S.navIconActive : {}) }}>
                        <Icon path={ICONS[item.icon]} size={19} />
                      </div>
                      {sidebarExpanded && (
                        <span style={{ ...S.navLabel, ...(active ? S.navLabelActive : {}) }}>
                          {item.label}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>

          {!isMobile && !isTablet && (
            <button
              className="layout-iconbtn"
              style={S.toggleBtn}
              onClick={() => setExpanded(e => !e)}
              title={expanded ? 'Réduire' : 'Étendre'}
            >
              <Icon path={expanded ? ICONS.chevronLeft : ICONS.chevronRight} size={16} />
              {expanded && <span style={S.toggleLabel}>Réduire</span>}
            </button>
          )}
        </aside>

        {/* ── Contenu ───────────────────────────────────────────────── */}
        <main style={{ ...S.main, ...(isMobile ? S.mainMobile : {}) }}>{children}</main>
      </div>
    </div>
  );
}

const S = {
  shell:         { display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-page)', overflow: 'hidden' },
  topBar:        { height: '56px', background: 'var(--bg-surface-alt)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 1.5rem', flexShrink: 0, zIndex: 100 },
  topLeft:       { display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: 0 },
  hamburgerBtn:  { background: 'none', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '0.4rem', cursor: 'pointer', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  topRight:      { display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 },
  userPill:      { display: 'flex', alignItems: 'center', gap: '0.625rem' },
  userAvatar:    { width: '32px', height: '32px', borderRadius: '50%', background: 'var(--accent-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '700', fontSize: '0.85rem', color: '#fff', flexShrink: 0 },
  userInfo:      { display: 'flex', flexDirection: 'column' },
  userName:      { fontSize: '0.82rem', fontWeight: '600', color: 'var(--text-secondary)', lineHeight: 1.2 },
  userRole:      { fontSize: '0.68rem', color: 'var(--text-muted)', lineHeight: 1.2 },
  logoutBtn:     { background: 'none', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '0.4rem', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  body:          { display: 'flex', flex: 1, overflow: 'hidden', position: 'relative' },
  backdrop:      { position: 'absolute', inset: 0, background: 'var(--bg-overlay)', zIndex: 150, backdropFilter: 'blur(1px)' },
  sidebar:       { background: 'var(--bg-surface-alt)', borderRight: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', flexShrink: 0, transition: 'width 250ms var(--ease-out)', overflow: 'hidden' },
  sidebarMobile: { position: 'absolute', top: 0, bottom: 0, left: 0, zIndex: 200, transition: 'transform 260ms var(--ease-in-out)', boxShadow: 'var(--shadow-lg)' },
  navList:       { flex: 1, display: 'flex', flexDirection: 'column', padding: '0.5rem 0', overflowY: 'auto' },
  navGroup:      { display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '14px' },
  navGroupFirst: { marginTop: 0 },
  sectionLabel:  { fontSize: '0.66rem', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '0.7px', padding: '0 0 6px 16px', whiteSpace: 'nowrap' },
  sectionDivider:{ height: '1px', background: 'var(--border-subtle)', margin: '0 12px 8px' },
  navItem:       { position: 'relative', display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.6rem 0', paddingLeft: '0', cursor: 'pointer', borderRadius: '0 8px 8px 0', marginRight: '8px', whiteSpace: 'nowrap' },
  navItemActive: { background: 'var(--accent-bg)' },
  activeBar:     { position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)', width: '3px', height: '60%', background: 'var(--accent)', borderRadius: '0 3px 3px 0', flexShrink: 0, transformOrigin: 'center' },
  navIcon:       { width: '60px', minWidth: '60px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-disabled)', transition: 'color 160ms ease', flexShrink: 0 },
  navIconActive: { color: 'var(--accent-light)' },
  navLabel:      { fontSize: '0.855rem', fontWeight: '500', color: 'var(--text-faint)', overflow: 'hidden', textOverflow: 'ellipsis', paddingRight: '0.75rem' },
  navLabelActive:{ color: 'var(--accent-light)', fontWeight: '600' },
  toggleBtn:     { display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'none', border: 'none', borderTop: '1px solid var(--border-subtle)', padding: '0.875rem 0', paddingLeft: '0', cursor: 'pointer', color: 'var(--text-disabled)', width: '100%', whiteSpace: 'nowrap' },
  toggleLabel:   { fontSize: '0.78rem', fontWeight: '500', color: 'var(--text-disabled)', paddingLeft: '0' },
  main:          { flex: 1, overflow: 'auto', padding: '1.75rem 2rem' },
  mainMobile:    { padding: '1.25rem 1rem' },
};
