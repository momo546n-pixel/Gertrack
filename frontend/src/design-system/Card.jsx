export function Card({ children, hoverable = false, style, className = '', ...props }) {
  return (
    <div
      className={`ds-card ${className}`}
      data-hoverable={hoverable}
      style={{
        background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)', overflow: 'hidden', ...style,
      }}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, action, style }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
      padding: '1rem 1.1rem 0.75rem', borderBottom: '1px solid var(--border-faint)', ...style,
    }}>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.15rem' }}>{title}</div>
        {subtitle && <div style={{ fontSize: '0.72rem', color: 'var(--text-faint)' }}>{subtitle}</div>}
      </div>
      {action}
    </div>
  );
}

export function CardBody({ children, style }) {
  return <div style={{ padding: '0.875rem 1.1rem', ...style }}>{children}</div>;
}
