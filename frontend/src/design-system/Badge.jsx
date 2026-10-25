const TONES = {
  accent:  { color: 'var(--accent-light)', bg: 'var(--accent-bg)' },
  success: { color: 'var(--success)',      bg: 'var(--success-bg)' },
  danger:  { color: 'var(--danger)',       bg: 'var(--danger-bg)' },
  warning: { color: 'var(--warning)',      bg: 'var(--warning-bg)' },
  warningAlt: { color: 'var(--warning-alt)', bg: 'var(--warning-alt-bg)' },
  info:    { color: 'var(--info)',         bg: 'var(--info-bg)' },
  muted:   { color: 'var(--text-muted)',   bg: 'var(--muted-bg)' },
};

export default function Badge({ tone = 'muted', children, style }) {
  const t = TONES[tone] || TONES.muted;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      padding: '3px 9px', borderRadius: '20px', fontSize: '0.7rem', fontWeight: 700,
      color: t.color, background: t.bg, whiteSpace: 'nowrap', ...style,
    }}>
      {children}
    </span>
  );
}
