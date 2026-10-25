import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';
import { Button, ThemeToggle } from '../design-system';

/* ── Illustration pylône électrique + graphique ─────────────────────────── */
const TowerIllustration = () => (
  <svg viewBox="0 0 420 290" fill="none" xmlns="http://www.w3.org/2000/svg"
    style={{ width: '100%', maxWidth: '400px', opacity: 0.9 }}>

    {/* Lignes de grille */}
    {[40, 80, 120, 160, 200, 240].map(y => (
      <line key={y} x1="20" y1={y} x2="400" y2={y}
        stroke="var(--border-default)" strokeWidth="0.5" strokeDasharray="6 6" />
    ))}

    {/* Barres */}
    {[
      { x:28,  h:55  },
      { x:73,  h:90  },
      { x:118, h:70  },
      { x:163, h:115 },
      { x:208, h:95  },
      { x:253, h:135 },
      { x:298, h:118 },
      { x:343, h:160 },
    ].map((b, i) => (
      <rect key={i} x={b.x} y={260 - b.h} width="34" height={b.h} rx="3"
        fill={i % 3 === 1 ? 'var(--accent)' : 'var(--accent-hover)'} opacity="0.75" />
    ))}

    {/* Ligne de tendance */}
    <polyline
      points="45,205 90,172 135,185 180,148 225,158 270,122 315,132 360,98"
      stroke="var(--accent-light)" strokeWidth="2.5" fill="none"
      strokeLinecap="round" strokeLinejoin="round"
    />
    {[[45,205],[90,172],[135,185],[180,148],[225,158],[270,122],[315,132],[360,98]].map(([x,y],i)=>(
      <circle key={i} cx={x} cy={y} r="4.5" fill="var(--accent-hover)" stroke="var(--accent-light)" strokeWidth="2.5"/>
    ))}

    {/* Pylône */}
    <g transform="translate(175, 8)" opacity="0.3" stroke="var(--accent-light)" strokeWidth="1.8">
      {/* Mât */}
      <line x1="35" y1="0"   x2="35" y2="140"/>
      {/* Base */}
      <line x1="35" y1="140" x2="0"  y2="215"/>
      <line x1="35" y1="140" x2="70" y2="215"/>
      <line x1="10" y1="185" x2="60" y2="185"/>
      {/* Bras */}
      <line x1="5"  y1="55"  x2="65" y2="55"/>
      <line x1="12" y1="90"  x2="58" y2="90"/>
      <line x1="18" y1="120" x2="52" y2="120"/>
      {/* Entretoises */}
      <line x1="20" y1="140" x2="35" y2="55"/>
      <line x1="50" y1="140" x2="35" y2="55"/>
      <line x1="15" y1="185" x2="35" y2="120"/>
      <line x1="55" y1="185" x2="35" y2="120"/>
      {/* Câbles */}
      <path d="M5,55  Q-30,70 -65,65" fill="none"/>
      <path d="M65,55 Q100,70 135,65" fill="none"/>
      <path d="M12,90 Q-20,105 -50,100" fill="none"/>
      <path d="M58,90 Q90,105 120,100" fill="none"/>
    </g>

    {/* Flèche horizontale */}
    <line x1="20" y1="275" x2="385" y2="275" stroke="var(--border-default)" strokeWidth="1.5"/>
    <polygon points="390,275 378,269 378,281" fill="var(--border-default)"/>
  </svg>
);

/* ─────────────────────────────────────────────────────────────────────────── */

export default function Login() {
  const [form,    setForm]    = useState({ username: '', password: '' });
  const [loading, setLoading] = useState(false);
  const { login }   = useAuth();
  const navigate    = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const user = await login(form.username, form.password);
      toast.success(`Bienvenue, ${user.full_name || user.username}`);
      navigate('/dashboard');
    } catch {
      toast.error('Identifiants incorrects');
    } finally { setLoading(false); }
  };

  return (
    <div style={S.page}>

      {/* ── Panneau gauche ────────────────────────────────────────────── */}
      <div style={S.left}>

        {/* Logo */}
        <div style={S.logo}>
          {/* Placez votre logo dans public/logo.png */}
          <img
            src="/logo.png"
            alt="Gertech"
            style={S.logoImg}
            onError={e => { e.target.style.display = 'none'; }}
          />
          <span style={S.logoText}>
            GER<span style={S.logoAccent}>TRACK</span>
          </span>
        </div>

        {/* Titre */}
        <div style={S.heroArea}>
          <h1 style={S.heroTitle}>
            Gestion industrielle<br />centralisée
          </h1>
          <p style={S.heroDesc}>
            Plateforme intégrée de suivi des stocks, des achats<br />
            et de validation hiérarchique pour votre entreprise.
          </p>
        </div>

        {/* Illustration */}
        <div style={S.illustration}>
          <TowerIllustration />
        </div>
      </div>

      {/* ── Panneau droit ─────────────────────────────────────────────── */}
      <div style={S.right}>
        <div style={S.themeToggleWrap}><ThemeToggle /></div>
        <div style={S.formCard}>

          <div style={S.formHead}>
            <h2 style={S.formTitle}>Connexion</h2>
            <p style={S.formSub}>Accédez à votre espace de travail</p>
          </div>

          <form onSubmit={handleSubmit} style={S.form}>
            <div style={S.fieldGroup}>
              <label style={S.label}>NOM D'UTILISATEUR</label>
              <input
                style={S.input}
                type="text"
                value={form.username}
                onChange={e => setForm({...form, username: e.target.value})}
                placeholder="admin"
                required
                autoFocus
              />
            </div>

            <div style={S.fieldGroup}>
              <label style={S.label}>MOT DE PASSE</label>
              <input
                style={S.input}
                type="password"
                value={form.password}
                onChange={e => setForm({...form, password: e.target.value})}
                placeholder="••••••••"
                required
              />
            </div>

            <Button variant="primary" type="submit" disabled={loading} style={S.btn}>
              {loading ? 'Connexion...' : 'Se connecter'}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}

const S = {
  page:        { display:'flex', height:'100vh', background:'var(--bg-page)', overflow:'hidden' },

  /* Left */
  left:        { flex:'0 0 58%', background:'linear-gradient(145deg, var(--bg-page) 0%, var(--bg-surface-alt) 60%, var(--bg-surface) 100%)', display:'flex', flexDirection:'column', padding:'2.5rem 3rem', position:'relative', overflow:'hidden' },
  logo:        { display:'flex', alignItems:'center', gap:'0.75rem', marginBottom:'auto' },
  logoImg:     { width:'44px', height:'44px', borderRadius:'50%', objectFit:'cover' },
  logoText:    { fontSize:'1.25rem', fontWeight:'300', color:'var(--text-primary)', letterSpacing:'3px', textTransform:'uppercase' },
  logoAccent:  { fontWeight:'700', color:'var(--accent-light)' },
  heroArea:    { marginTop:'4rem', marginBottom:'2rem' },
  heroTitle:   { fontSize:'2.5rem', fontWeight:'700', color:'var(--text-primary)', lineHeight:'1.25', letterSpacing:'-0.5px', marginBottom:'1.25rem' },
  heroDesc:    { fontSize:'0.9rem', color:'var(--text-tertiary)', lineHeight:'1.75' },
  illustration:{ marginTop:'auto', display:'flex', justifyContent:'center', paddingBottom:'1rem' },

  /* Right */
  right:       { flex:'0 0 42%', display:'flex', alignItems:'center', justifyContent:'center', background:'var(--bg-surface)', padding:'2rem', position:'relative' },
  themeToggleWrap: { position:'absolute', top:'1.5rem', right:'1.5rem' },
  formCard:    { width:'100%', maxWidth:'380px' },
  formHead:    { marginBottom:'2.5rem' },
  formTitle:   { fontSize:'2.25rem', fontWeight:'700', color:'var(--text-primary)', letterSpacing:'-0.5px', marginBottom:'0.4rem' },
  formSub:     { fontSize:'0.875rem', color:'var(--text-tertiary)' },

  form:        { display:'flex', flexDirection:'column', gap:'1.25rem', marginBottom:'2rem' },
  fieldGroup:  { display:'flex', flexDirection:'column', gap:'0.5rem' },
  label:       { fontSize:'0.7rem', fontWeight:'600', color:'var(--text-muted)', letterSpacing:'1.5px' },
  input:       {
    background:'var(--bg-surface-alt)',
    border:'1px solid var(--border-default)',
    borderRadius:'8px',
    padding:'0.8rem 1rem',
    fontSize:'0.9rem',
    color:'var(--text-primary)',
    transition:'border-color 0.2s',
    width:'100%',
    boxSizing:'border-box',
    outline:'none',
  },
  btn:         { width:'100%', padding:'0.9rem', fontSize:'0.95rem', marginTop:'0.5rem', boxShadow:'0 4px 20px rgba(37,99,235,0.35)' },

};
