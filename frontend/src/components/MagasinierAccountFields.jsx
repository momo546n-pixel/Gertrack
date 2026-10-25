// Bloc de champs "compte du magasin" partagé — une seule source de vérité
// pour les sections "Informations du gérant" / "Informations de connexion"
// utilisées par Warehouses.jsx (création et modification).
const S = {
  label:   { display: 'block', fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: '6px' },
  input:   { width: '100%', padding: '10px 12px', backgroundColor: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '8px', color: 'var(--text-secondary)', fontSize: '14px', outline: 'none', boxSizing: 'border-box' },
  fGroup:  { marginBottom: '16px' },
  sTitle:  { fontSize: '11px', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '.05em', margin: '20px 0 12px', paddingBottom: '6px', borderBottom: '1px solid var(--border-default)' },
};

// mode 'create' : Informations du gérant + Informations de connexion
//                 (identifiant, + mot de passe/confirmation si showPassword)
// mode 'edit'   : Informations du gérant + identifiant seul (le mot de passe
//                 se modifie séparément, via l'action dédiée "Mot de passe")
//
// showPassword : true quand le DG crée directement (il fixe le mot de passe
// tout de suite) ; false quand le Responsable Achat et Logistique soumet une demande — le
// mot de passe sera défini par le DG au moment de la validation, jamais par
// l'auteur de la demande.
const MagasinierAccountFields = ({ form, setForm, mode = 'create', showPassword = true }) => {
  const passwordsMismatch = mode === 'create' && showPassword
    && form.mag_password && form.mag_password_confirm
    && form.mag_password !== form.mag_password_confirm;

  return (
    <>
      <p style={S.sTitle}>Informations du gérant</p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <div style={S.fGroup}>
          <label style={S.label}>Nom *</label>
          <input style={S.input} type="text" value={form.mag_last_name}
            onChange={e => setForm(p => ({ ...p, mag_last_name: e.target.value }))} required />
        </div>
        <div style={S.fGroup}>
          <label style={S.label}>Prénom *</label>
          <input style={S.input} type="text" value={form.mag_first_name}
            onChange={e => setForm(p => ({ ...p, mag_first_name: e.target.value }))} required />
        </div>
      </div>
      <div style={S.fGroup}>
        <label style={S.label}>Téléphone</label>
        <input style={S.input} type="text" value={form.mag_phone}
          onChange={e => setForm(p => ({ ...p, mag_phone: e.target.value }))} />
      </div>
      <div style={S.fGroup}>
        <label style={S.label}>Email</label>
        <input style={S.input} type="email" value={form.mag_email}
          onChange={e => setForm(p => ({ ...p, mag_email: e.target.value }))} />
      </div>

      <p style={S.sTitle}>Informations de connexion</p>
      <div style={S.fGroup}>
        <label style={S.label}>Identifiant *</label>
        <input style={S.input} type="text" placeholder="Ex : mag.dakar" value={form.mag_username}
          onChange={e => setForm(p => ({ ...p, mag_username: e.target.value }))} required />
      </div>
      {mode === 'create' && showPassword && (
        <>
          <div style={S.fGroup}>
            <label style={S.label}>Mot de passe *</label>
            <input style={S.input} type="text" placeholder="6 caractères minimum" value={form.mag_password}
              onChange={e => setForm(p => ({ ...p, mag_password: e.target.value }))} required />
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Confirmation du mot de passe *</label>
            <input style={S.input} type="text" placeholder="Retapez le mot de passe" value={form.mag_password_confirm}
              onChange={e => setForm(p => ({ ...p, mag_password_confirm: e.target.value }))} required />
            {passwordsMismatch && (
              <p style={{ fontSize: '11px', color: 'var(--danger)', marginTop: '6px' }}>Les mots de passe ne correspondent pas.</p>
            )}
          </div>
        </>
      )}
      {mode === 'create' && !showPassword && (
        <p style={{ fontSize: '11px', color: 'var(--text-disabled)' }}>
          Le mot de passe du compte sera défini par le DG au moment de la validation.
        </p>
      )}
    </>
  );
};

export default MagasinierAccountFields;
