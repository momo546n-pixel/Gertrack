const base = {
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
  fontFamily: 'var(--font-sans)', fontWeight: 600, cursor: 'pointer',
  border: '1px solid transparent', borderRadius: 'var(--radius-md)',
  transition: 'transform 140ms var(--ease-out), background 140ms ease, border-color 140ms ease, opacity 140ms ease',
  whiteSpace: 'nowrap',
};

const sizes = {
  sm: { padding: '0.4rem 0.75rem', fontSize: '0.78rem' },
  md: { padding: '0.6rem 1rem',    fontSize: '0.85rem' },
  lg: { padding: '0.75rem 1.25rem', fontSize: '0.9rem' },
};

const variants = {
  primary:   { background: 'var(--accent)', color: '#fff' },
  secondary: { background: 'transparent', color: 'var(--text-secondary)', borderColor: 'var(--border-default)' },
  ghost:     { background: 'transparent', color: 'var(--text-tertiary)' },
  danger:    { background: 'var(--danger-bg)', color: 'var(--danger)', borderColor: 'transparent' },
  success:   { background: 'var(--success-bg)', color: 'var(--success)', borderColor: 'transparent' },
  warning:   { background: 'var(--warning-bg)', color: 'var(--warning)', borderColor: 'transparent' },
  info:      { background: 'var(--accent-bg)', color: 'var(--accent-light)', borderColor: 'transparent' },
};

export default function Button({
  variant = 'primary', size = 'md', icon = null, disabled = false,
  style, children, className = '', ...props
}) {
  return (
    <button
      className={`ds-btn ${className}`}
      data-variant={variant}
      disabled={disabled}
      style={{
        ...base, ...sizes[size], ...variants[variant],
        opacity: disabled ? 0.55 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
        ...style,
      }}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
