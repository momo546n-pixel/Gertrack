export default function IconButton({ children, title, size = 34, style, ...props }) {
  return (
    <button
      className="ds-icon-btn"
      title={title}
      aria-label={title}
      style={{
        width: size, height: size, flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'transparent', border: '1px solid var(--border-default)',
        borderRadius: 'var(--radius-md)', color: 'var(--text-tertiary)', cursor: 'pointer',
        ...style,
      }}
      {...props}
    >
      {children}
    </button>
  );
}
