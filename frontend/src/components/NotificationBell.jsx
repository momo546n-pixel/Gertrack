import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';

// ─── Icons ────────────────────────────────────────────────────────────────────
const BellIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
    <path d="M13.73 21a2 2 0 01-3.46 0"/>
  </svg>
);
const CheckAllIcon = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 12l5 5L22 4"/><path d="M7 12l5 5"/>
  </svg>
);
const TrashIcon = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6l-1 14H6L5 6M10 11v6M14 11v6M9 6V4h6v2"/>
  </svg>
);
const XIcon = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

// ─── Config par type ──────────────────────────────────────────────────────────
const TYPE_CFG = {
  demande_creee:    { color: 'var(--accent-light)', dot: 'var(--accent)', bg: 'var(--accent-bg)' },
  demande_soumise:  { color: 'var(--warning)', dot: 'var(--warning)', bg: 'var(--warning-bg)' },
  demande_validee:  { color: 'var(--success-light)', dot: 'var(--success-light)', bg: 'var(--success-bg)' },
  demande_refusee:  { color: 'var(--danger)', dot: 'var(--danger)', bg: 'var(--danger-bg)' },
  demande_executee: { color: 'var(--info)', dot: 'var(--info)', bg: 'var(--info-bg)' },
  stock_faible:     { color: 'var(--warning-alt)', dot: 'var(--warning-alt)', bg: 'var(--warning-alt-bg)' },
  stock_rupture:    { color: 'var(--danger)', dot: 'var(--danger)', bg: 'var(--danger-bg)' },
  entree_validee:   { color: 'var(--success-light)', dot: 'var(--success-light)', bg: 'var(--success-bg)' },
  sortie_validee:   { color: 'var(--success-light)', dot: 'var(--success-light)', bg: 'var(--success-bg)' },
  retard_projet:    { color: 'var(--danger)', dot: 'var(--danger)', bg: 'var(--danger-bg)' },
  budget_depasse:   { color: 'var(--warning-alt)', dot: 'var(--warning-alt)', bg: 'var(--warning-alt-bg)' },
  echeance_proche:  { color: 'var(--warning)', dot: 'var(--warning)', bg: 'var(--warning-bg)' },
  commande_arrivee:   { color: 'var(--success-light)', dot: 'var(--success-light)', bg: 'var(--success-bg)' },
  commande_en_retard: { color: 'var(--danger)', dot: 'var(--danger)', bg: 'var(--danger-bg)' },
  livraison_chantier: { color: 'var(--info)', dot: 'var(--info)', bg: 'var(--info-bg)' },
};
const DEFAULT_CFG = { color: 'var(--accent-light)', dot: 'var(--accent)', bg: 'var(--accent-bg)' };

export default function NotificationBell() {
  const navigate           = useNavigate();
  const [open,      setOpen]      = useState(false);
  const [notifs,    setNotifs]    = useState([]);
  const [count,     setCount]     = useState(0);
  const [loading,   setLoading]   = useState(false);
  const [animate,   setAnimate]   = useState(false);
  const dropRef                    = useRef(null);
  const prevCount                  = useRef(0);

  // ── Chargement ────────────────────────────────────────────────────────────
  const loadCount = useCallback(async () => {
    try {
      const res = await api.get('/notifications/unread-count/');
      const newCount = res.data.count || 0;
      if (newCount > prevCount.current) {
        setAnimate(true);
        setTimeout(() => setAnimate(false), 1000);
      }
      prevCount.current = newCount;
      setCount(newCount);
    } catch { /* non bloquant */ }
  }, []);

  const loadNotifs = useCallback(async () => {
  try {
    setLoading(true);
    
    const res = await api.get('/notifications/');
    setNotifs(res.data.results ?? res.data ?? []);
  } catch { /* non bloquant */ }
  finally { setLoading(false); }
}, []);

  // Polling toutes les 30 secondes — filet de sécurité si le WebSocket
  // temps réel ci-dessous est indisponible ou se déconnecte.
  useEffect(() => {
    loadCount();
    const interval = setInterval(loadCount, 30000);
    return () => clearInterval(interval);
  }, [loadCount]);

  // ── Temps réel (WebSocket — Phase G §9) ───────────────────────────────────
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const wsUrl = `ws://${window.location.hostname}:8000/ws/notifications/?token=${token}`;
    let socket;
    let reconnectTimer;

    const connect = () => {
      socket = new WebSocket(wsUrl);

      socket.onmessage = (event) => {
        try {
          const notif = JSON.parse(event.data);
          setNotifs(prev => [notif, ...prev]);
          setCount(c => c + 1);
          prevCount.current += 1;
          setAnimate(true);
          setTimeout(() => setAnimate(false), 1000);
        } catch { /* message non exploitable, ignoré */ }
      };

      socket.onclose = (event) => {
        // Fermeture volontaire (4001 = token invalide) : ne pas boucler.
        if (event.code === 4001) return;
        reconnectTimer = setTimeout(connect, 5000);
      };

      socket.onerror = () => socket.close();
    };

    connect();
    return () => {
      clearTimeout(reconnectTimer);
      if (socket) { socket.onclose = null; socket.close(); }
    };
  }, []);

  // Fermer en cliquant dehors
  useEffect(() => {
    const handler = (e) => {
      if (dropRef.current && !dropRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleOpen = () => {
    setOpen(o => !o);
    if (!open) loadNotifs();
  };

  // ── Actions ───────────────────────────────────────────────────────────────
  const markRead = async (id) => {
    try {
      await api.post(`/notifications/${id}/read/`);
      setNotifs(p => p.map(n => n.id === id ? { ...n, is_read: true } : n));
      setCount(c => Math.max(0, c - 1));
    } catch { /* non bloquant */ }
  };

  const markAllRead = async () => {
    try {
      await api.post('/notifications/read-all/');
      setNotifs(p => p.map(n => ({ ...n, is_read: true })));
      setCount(0);
    } catch { /* non bloquant */ }
  };

  const clearRead = async () => {
    try {
      await api.delete('/notifications/clear-read/');
      setNotifs(p => p.filter(n => !n.is_read));
    } catch { /* non bloquant */ }
  };

  const handleNotifClick = async (notif) => {
    if (!notif.is_read) await markRead(notif.id);
    if (notif.link) {
      navigate(notif.link);
      setOpen(false);
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  const unread = notifs.filter(n => !n.is_read).length;

  return (
    <div ref={dropRef} style={{ position: 'relative' }}>

      {/* Bouton cloche */}
      <button
        onClick={handleOpen}
        style={{
          position: 'relative',
          background: open ? 'var(--accent-bg)' : 'none',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '6px 8px',
          cursor: 'pointer',
          color: count > 0 ? 'var(--accent-light)' : 'var(--text-muted)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'background 160ms ease, color 160ms ease',
          animation: animate ? 'bellShake .5s ease' : 'none',
        }}
        title="Notifications"
      >
        <BellIcon size={18} />
        {count > 0 && (
          <span style={{
            position: 'absolute', top: '-6px', right: '-6px',
            background: 'var(--danger)', color: '#fff',
            borderRadius: '50%', width: '18px', height: '18px',
            fontSize: '10px', fontWeight: '800',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            border: '2px solid var(--bg-surface-alt)',
          }}>
            {count > 99 ? '99+' : count}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div style={{
          position: 'absolute', top: '42px', right: 0,
          width: '360px', maxHeight: '520px',
          background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-lg)',
          display: 'flex', flexDirection: 'column',
          zIndex: 999, overflow: 'hidden',
          fontFamily: 'var(--font-sans)',
        }}
        className="ds-modal-panel"
        >

          {/* Header dropdown */}
          <div style={{
            padding: '14px 16px', borderBottom: '1px solid var(--border-default)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <span style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>
                Notifications
              </span>
              {unread > 0 && (
                <span style={{
                  marginLeft: '8px', fontSize: '11px', fontWeight: '700',
                  color: 'var(--accent-light)', background: 'var(--accent-bg)',
                  padding: '2px 8px', borderRadius: '20px',
                }}>
                  {unread} non lue{unread > 1 ? 's' : ''}
                </span>
              )}
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              {unread > 0 && (
                <button onClick={markAllRead} title="Tout marquer comme lu"
                  style={{ background: 'none', border: '1px solid var(--border-default)', borderRadius: '6px', padding: '4px 8px', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
                  <CheckAllIcon /> Tout lire
                </button>
              )}
              <button onClick={clearRead} title="Supprimer les lues"
                style={{ background: 'none', border: '1px solid var(--border-default)', borderRadius: '6px', padding: '4px 8px', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
                <TrashIcon />
              </button>
              <button onClick={() => setOpen(false)} title="Fermer" aria-label="Fermer"
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}>
                <XIcon size={16} />
              </button>
            </div>
          </div>

          {/* Liste des notifications */}
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {loading ? (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                Chargement…
              </div>
            ) : notifs.length === 0 ? (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <div style={{ opacity: .4, marginBottom: '8px', display: 'flex', justifyContent: 'center' }}>
                  <BellIcon size={36} />
                </div>
                <p style={{ fontSize: '13px', fontWeight: '600' }}>Aucune notification</p>
              </div>
            ) : (
              notifs.map(notif => {
                const cfg = TYPE_CFG[notif.notif_type] || DEFAULT_CFG;
                return (
                  <div
                    key={notif.id}
                    onClick={() => handleNotifClick(notif)}
                    style={{
                      padding: '12px 16px',
                      borderBottom: '1px solid var(--border-faint)',
                      background: notif.is_read ? 'transparent' : 'var(--accent-bg)',
                      cursor: 'pointer',
                      display: 'flex', gap: '12px', alignItems: 'flex-start',
                      transition: 'background .15s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
                    onMouseLeave={e => e.currentTarget.style.background = notif.is_read ? 'transparent' : 'var(--accent-bg)'}
                  >
                    {/* Point coloré */}
                    <div style={{
                      width: '8px', height: '8px', borderRadius: '50%',
                      background: notif.is_read ? 'var(--border-default)' : cfg.dot,
                      flexShrink: 0, marginTop: '5px',
                    }} />

                    {/* Contenu */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                        <span style={{
                          fontSize: '13px', fontWeight: notif.is_read ? '500' : '700',
                          color: notif.is_read ? 'var(--text-tertiary)' : 'var(--text-primary)',
                          lineHeight: 1.3,
                        }}>
                          {notif.title}
                        </span>
                        <span style={{ fontSize: '10px', color: 'var(--text-disabled)', flexShrink: 0, marginTop: '2px' }}>
                          {notif.time_ago}
                        </span>
                      </div>
                      <p style={{
                        fontSize: '12px', color: 'var(--text-muted)',
                        margin: '3px 0 0', lineHeight: 1.4,
                        overflow: 'hidden', textOverflow: 'ellipsis',
                        display: '-webkit-box', WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                      }}>
                        {notif.message}
                      </p>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '5px' }}>
                        <span style={{
                          fontSize: '10px', fontWeight: '700', color: cfg.color,
                          background: cfg.bg,
                          padding: '1px 7px', borderRadius: '20px',
                          textTransform: 'uppercase', letterSpacing: '.03em',
                        }}>
                          {notif.category_display}
                        </span>
                        {!notif.is_read && (
                          <button
                            onClick={e => { e.stopPropagation(); markRead(notif.id); }}
                            style={{
                              background: 'none', border: 'none', cursor: 'pointer',
                              fontSize: '10px', color: 'var(--text-disabled)', padding: 0,
                            }}
                          >
                            Marquer comme lu
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div style={{
            padding: '10px 16px', borderTop: '1px solid var(--border-default)',
            textAlign: 'center', fontSize: '12px', color: 'var(--text-disabled)',
          }}>
            {notifs.length} notification{notifs.length !== 1 ? 's' : ''} au total
          </div>
        </div>
      )}

      {/* Animation cloche */}
      <style>{`
        @keyframes bellShake {
          0%, 100% { transform: rotate(0deg); }
          20%       { transform: rotate(-15deg); }
          40%       { transform: rotate(15deg); }
          60%       { transform: rotate(-10deg); }
          80%       { transform: rotate(10deg); }
        }
      `}</style>
    </div>
  );
}