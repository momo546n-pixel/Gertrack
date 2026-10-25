export default function GertechLogo({ size = 36, showText = true, textSize = '1.1rem' }) {
  return (
    <div style={{ display:'flex', alignItems:'center', gap:'0.75rem' }}>
      <img
        src="/logo.png"
        alt="Gertech Énergies et Services"
        style={{
          width: `${size}px`,
          height: `${size}px`,
          borderRadius: '50%',
          objectFit: 'cover',
          flexShrink: 0,
        }}
        onError={e => {
          e.target.style.display = 'none';
        }}
      />
      {showText && (
        <span style={{
          fontSize: textSize,
          fontWeight: '300',
          color: 'var(--text-primary)',
          letterSpacing: '3px',
          textTransform: 'uppercase',
          userSelect: 'none',
          whiteSpace: 'nowrap',
        }}>
          GER<span style={{ fontWeight:'700', color:'var(--accent-light)' }}>TRACK</span>
        </span>
      )}
    </div>
  );
}