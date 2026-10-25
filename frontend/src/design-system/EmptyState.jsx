export default function EmptyState({ icon, title, message, action }) {
  return (
    <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-disabled)' }}>
      {icon && <div style={{ opacity: 0.4, display: 'flex', justifyContent: 'center', marginBottom: '16px' }}>{icon}</div>}
      {title && <p style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>{title}</p>}
      {message && <p style={{ fontSize: '13px' }}>{message}</p>}
      {action && <div style={{ marginTop: '16px' }}>{action}</div>}
    </div>
  );
}
