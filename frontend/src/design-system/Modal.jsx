import { useEffect, useRef } from 'react';

export default function Modal({ open, onClose, title, children, footer, maxWidth = '480px' }) {
  const panelRef = useRef(null);
  // onClose est souvent une lambda inline (nouvelle référence à chaque rendu du
  // parent) — on la lit via une ref pour ne pas la mettre dans les deps de
  // l'effet ci-dessous, sinon il se redéclenche à chaque frappe dans un champ
  // du formulaire et vole le focus de l'input vers le panneau.
  const onCloseRef = useRef(onClose);
  useEffect(() => { onCloseRef.current = onClose; });

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e) => { if (e.key === 'Escape') onCloseRef.current?.(); };
    document.addEventListener('keydown', onKeyDown);
    // Focus le panneau à l'ouverture pour que Échap/Tab fonctionnent tout de suite.
    panelRef.current?.focus();
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="ds-modal-overlay"
      onClick={e => e.target === e.currentTarget && onClose?.()}
      style={{
        position: 'fixed', inset: 0, background: 'var(--bg-overlay)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 1000, padding: '20px',
      }}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="ds-modal-panel"
        style={{
          background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)',
          border: '1px solid var(--border-subtle)', boxShadow: 'var(--shadow-lg)',
          width: '100%', maxWidth, maxHeight: '90vh', overflowY: 'auto', outline: 'none',
        }}
      >
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '20px 24px', borderBottom: '1px solid var(--border-subtle)',
        }}>
          <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)' }}>{title}</span>
          <button
            onClick={onClose}
            title="Fermer"
            aria-label="Fermer"
            className="ds-icon-btn"
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', borderRadius: 'var(--radius-sm)', width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          >
            ✕
          </button>
        </div>
        <div style={{ padding: '20px 24px' }}>{children}</div>
        {footer && (
          <div style={{
            padding: '16px 24px', borderTop: '1px solid var(--border-subtle)',
            display: 'flex', justifyContent: 'flex-end', gap: '12px',
          }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
