import { useState, useEffect, useCallback } from 'react';
import api from '../api/axios';
import { Modal, Button, Badge } from '../design-system';

// ─── Icons ────────────────────────────────────────────────────────────────────
const UsersIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 00-3-3.87"/>
    <path d="M16 3.13a4 4 0 010 7.75"/>
  </svg>
);
const PlusIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
);
const EditIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
  </svg>
);
const TrashIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
    <path d="M10 11v6M14 11v6"/>
    <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/>
  </svg>
);

// ─── Styles ───────────────────────────────────────────────────────────────────
const S = {
  page:         { padding: '28px', minHeight: '100vh', background: 'var(--bg-page)', color: 'var(--text-secondary)', fontFamily: 'var(--font-sans)' },
  header:       { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '28px' },
  title:        { display: 'flex', alignItems: 'center', gap: '10px', fontSize: '22px', fontWeight: '700', color: 'var(--text-primary)' },
  subtitle:     { fontSize: '13px', color: 'var(--text-disabled)', marginTop: '4px' },
  grid:         { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '20px' },
  card:         { background: 'var(--bg-surface)', borderRadius: '12px', border: '1px solid var(--border-default)', overflow: 'hidden' },
  cardHead:     { padding: '18px 20px', borderBottom: '1px solid var(--border-default)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' },
  cardBody:     { padding: '14px 20px' },
  cardFoot:     { padding: '12px 20px', borderTop: '1px solid var(--border-default)', display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'flex-end' },
  iconBox:      { width: '44px', height: '44px', borderRadius: '10px', background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-light)' },
  codeBadge:    { display: 'inline-block', fontSize: '11px', fontWeight: '700', color: 'var(--accent-light)', background: 'var(--accent-bg)', padding: '2px 8px', borderRadius: '4px', letterSpacing: '.05em', marginTop: '4px' },
  statRow:      { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid var(--border-faint)' },
  statLabel:    { fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' },
  statVal:      (color) => ({ fontSize: '13px', fontWeight: '700', color: color || 'var(--text-secondary)' }),
  alertBox:     { padding: '8px 12px', borderRadius: '6px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '10px', background: 'var(--danger-bg)', border: '1px solid var(--danger)', color: 'var(--danger)' },
  flash:        (type) => ({ padding: '12px 16px', borderRadius: '8px', fontSize: '13px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', ...(type === 'success' ? { background: 'var(--success-bg)', border: '1px solid var(--success)', color: 'var(--success)' } : { background: 'var(--danger-bg)', border: '1px solid var(--danger)', color: 'var(--danger)' }) }),
  label:        { display: 'block', fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: '6px' },
  input:        { width: '100%', padding: '10px 12px', background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '8px', color: 'var(--text-secondary)', fontSize: '14px', outline: 'none', boxSizing: 'border-box' },
  fGroup:       { marginBottom: '16px' },
  magRow:       { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', background: 'var(--bg-surface-alt)', borderRadius: '8px', marginBottom: '8px', gap: '10px', flexWrap: 'wrap' },
  empty:        { textAlign: 'center', padding: '60px 20px', color: 'var(--text-disabled)' },
};

const fmtDate = (d) => d ? new Date(d).toLocaleDateString('fr-FR') : '–';
const fmtDateTime = (d) => d ? new Date(d).toLocaleString('fr-FR') : 'Jamais';

const ProjectManagers = () => {
  const [pms,     setPms]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [flash,   setFlash]   = useState({ type: '', msg: '' });

  const [showCreate, setShowCreate] = useState(false);
  const [showEdit,   setShowEdit]   = useState(false);
  const [selected,   setSelected]   = useState(null);

  const emptyForm = { username: '', first_name: '', last_name: '', email: '', phone: '', password: '' };
  const [form, setForm] = useState(emptyForm);

  const [adminRequests, setAdminRequests] = useState([]);
  const [showApprove,   setShowApprove]   = useState(false);
  const [approveTarget, setApproveTarget] = useState(null);
  const [approvePassword, setApprovePassword] = useState('');
  const [approving, setApproving] = useState(false);

  const user      = JSON.parse(localStorage.getItem('user') || '{}');
  const userRole  = user.role || '';
  const isDG      = userRole === 'dg' || user.is_dg === true;
  const isDOP     = userRole === 'chef_ops' || user.is_ops_chief === true;
  const canManage = isDG || isDOP;

  const notify = (type, msg) => {
    setFlash({ type, msg });
    setTimeout(() => setFlash({ type: '', msg: '' }), 4000);
  };

  const loadPms = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/accounts/project-managers/');
      const data = res.data.results ?? res.data;
      setPms(Array.isArray(data) ? data : []);
    } catch {
      notify('error', 'Impossible de charger les chefs de projet.');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAdminRequests = useCallback(async () => {
    try {
      const res = await api.get('/accounts/admin-requests/');
      const data = res.data.results ?? res.data ?? [];
      const filtered = (Array.isArray(data) ? data : []).filter(
        r => ['creation_chef_projet', 'suppression_chef_projet'].includes(r.request_type)
      );
      setAdminRequests(filtered);
    } catch { setAdminRequests([]); }
  }, []);

  useEffect(() => { loadPms(); }, [loadPms]);
  useEffect(() => { if (isDG || isDOP) loadAdminRequests(); }, [isDG, isDOP, loadAdminRequests]);

  const resetForm = () => setForm(emptyForm);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      if (isDG) {
        await api.post('/accounts/project-managers/', {
          username: form.username, first_name: form.first_name, last_name: form.last_name,
          email: form.email, phone: form.phone, password: form.password,
        });
        notify('success', 'Compte chef de projet créé avec succès.');
      } else {
        await api.post('/accounts/admin-requests/', {
          request_type: 'creation_chef_projet',
          payload: {
            username: form.username, first_name: form.first_name, last_name: form.last_name,
            email: form.email, phone: form.phone,
          },
        });
        notify('success', 'Demande de création envoyée au DG pour validation.');
      }
      setShowCreate(false);
      resetForm();
      loadPms();
      loadAdminRequests();
    } catch (err) {
      const payloadErr = err.response?.data?.payload || err.response?.data?.password;
      notify('error', (Array.isArray(payloadErr) ? payloadErr[0] : payloadErr) || err.response?.data?.detail || 'Erreur lors de la création.');
    }
  };

  const handleEdit = async (e) => {
    e.preventDefault();
    try {
      await api.patch(`/accounts/project-managers/${selected.id}/`, {
        first_name: form.first_name, last_name: form.last_name,
        email: form.email, phone: form.phone,
        ...(form.password ? { password: form.password } : {}),
      });
      notify('success', 'Compte modifié avec succès.');
      setShowEdit(false);
      resetForm();
      loadPms();
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors de la modification.');
    }
  };

  const handleDeactivate = async (pm) => {
    if (!window.confirm(`Désactiver le compte de "${pm.full_name}" ?`)) return;
    try {
      await api.post(`/accounts/project-managers/${pm.id}/deactivate/`);
      notify('success', 'Compte désactivé.');
      loadPms();
    } catch { notify('error', 'Erreur lors de la désactivation.'); }
  };

  const handleReactivate = async (pm) => {
    try {
      await api.post(`/accounts/project-managers/${pm.id}/reactivate/`);
      notify('success', 'Compte réactivé.');
      loadPms();
    } catch { notify('error', 'Erreur lors de la réactivation.'); }
  };

  const handleDeletePermanently = async (pm) => {
    if (!window.confirm(`Supprimer définitivement le compte de "${pm.full_name}" ? Cette action est irréversible.`)) return;
    try {
      await api.delete(`/accounts/project-managers/${pm.id}/`);
      notify('success', 'Compte supprimé définitivement.');
      loadPms();
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors de la suppression.');
    }
  };

  const handleProposeDeletion = async (pm) => {
    if (!window.confirm(`Proposer la suppression du compte de "${pm.full_name}" au DG ?`)) return;
    try {
      await api.post('/accounts/admin-requests/', {
        request_type: 'suppression_chef_projet',
        payload: { user_id: pm.id },
      });
      notify('success', 'Demande de suppression envoyée au DG.');
      loadAdminRequests();
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors de la demande.');
    }
  };

  const openEdit = (pm) => {
    setSelected(pm);
    setForm({ ...emptyForm, username: pm.username, first_name: pm.first_name || '', last_name: pm.last_name || '', email: pm.email || '', phone: pm.phone || '' });
    setShowEdit(true);
  };

  const openApprove = (req) => { setApproveTarget(req); setApprovePassword(''); setShowApprove(true); };

  const handleApprove = async () => {
    if (!approveTarget) return;
    if (approveTarget.request_type === 'creation_chef_projet' && approvePassword.length < 6) {
      notify('error', 'Mot de passe de 6 caractères minimum requis.');
      return;
    }
    try {
      setApproving(true);
      const body = approveTarget.request_type === 'creation_chef_projet' ? { password: approvePassword } : {};
      await api.post(`/accounts/admin-requests/${approveTarget.id}/approve/`, body);
      notify('success', 'Demande validée.');
      setShowApprove(false);
      loadAdminRequests();
      loadPms();
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors de la validation.');
    } finally { setApproving(false); }
  };

  const handleReject = async (req) => {
    const comment = window.prompt('Motif du refus (optionnel) :') || '';
    try {
      await api.post(`/accounts/admin-requests/${req.id}/reject/`, { comment });
      notify('success', 'Demande refusée.');
      loadAdminRequests();
    } catch (err) {
      notify('error', err.response?.data?.detail || 'Erreur lors du refus.');
    }
  };

  if (loading) return (
    <div style={S.page}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px', color: 'var(--text-disabled)' }}>
        Chargement des chefs de projet…
      </div>
    </div>
  );

  return (
    <div style={S.page}>

      {/* Header */}
      <div style={S.header}>
        <div>
          <div style={S.title}><UsersIcon size={22} /> Chefs de Projet</div>
          <div style={S.subtitle}>{pms.length} compte{pms.length !== 1 ? 's' : ''} configuré{pms.length !== 1 ? 's' : ''}</div>
        </div>
        {canManage && (
          <Button variant="primary" onClick={() => { resetForm(); setShowCreate(true); }}>
            <PlusIcon /> Nouveau Chef de Projet
          </Button>
        )}
      </div>

      {/* Flash */}
      {flash.msg && (
        <div style={S.flash(flash.type)}>
          <span>{flash.msg}</span>
          <button onClick={() => setFlash({ type: '', msg: '' })} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '18px', lineHeight: 1 }}>×</button>
        </div>
      )}

      {/* Demandes administratives (création/suppression de compte) */}
      {(isDG || isDOP) && adminRequests.length > 0 && (
        <div style={{ ...S.card, marginBottom: '20px' }}>
          <div style={S.cardHead}>
            <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
              Demandes de compte {isDG ? '' : '(les miennes)'}
            </span>
          </div>
          <div style={{ padding: '8px 20px 16px' }}>
            {adminRequests.map(req => (
              <div key={req.id} style={S.magRow}>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)' }}>
                    {req.request_type_display} — <span style={{ fontFamily: 'monospace', color: 'var(--accent-light)' }}>{req.reference}</span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {req.payload?.username ? `Compte : ${req.payload.username}` : ''}
                    {' · '}Par {req.requested_by_name} · {fmtDate(req.created_at)}
                  </div>
                  {req.status !== 'en_attente' && (
                    <div style={{ fontSize: '11px', color: req.status === 'validee' ? 'var(--success-light)' : 'var(--danger)', marginTop: '2px', fontWeight: '600' }}>
                      {req.status_display}{req.review_comment ? ` — ${req.review_comment}` : ''}
                    </div>
                  )}
                </div>
                {isDG && req.status === 'en_attente' && (
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <Button variant="success" size="sm" onClick={() => openApprove(req)}>Valider</Button>
                    <Button variant="danger" size="sm" onClick={() => handleReject(req)}>Refuser</Button>
                  </div>
                )}
                {req.status === 'en_attente' && !isDG && (
                  <Badge tone="accent">En attente DG</Badge>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grid */}
      {pms.length === 0 ? (
        <div style={S.empty}>
          <div style={{ opacity: .35, display: 'flex', justifyContent: 'center', marginBottom: '16px' }}><UsersIcon size={52} /></div>
          <p style={{ fontSize: '15px', fontWeight: '600', marginBottom: '6px' }}>Aucun chef de projet configuré</p>
          <p style={{ fontSize: '13px' }}>
            {canManage ? 'Cliquez sur "Nouveau Chef de Projet" pour commencer.' : ''}
          </p>
        </div>
      ) : (
        <div style={S.grid}>
          {pms.map(pm => (
            <div key={pm.id} style={S.card}>
              <div style={S.cardHead}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                    <span style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)' }}>{pm.full_name}</span>
                    <Badge tone={pm.is_active ? 'success' : 'danger'}>{pm.is_active ? 'Actif' : 'Inactif'}</Badge>
                  </div>
                  <span style={S.codeBadge}>{pm.username}</span>
                </div>
                <div style={S.iconBox}><UsersIcon size={22} /></div>
              </div>

              <div style={S.cardBody}>
                {pm.phone && (
                  <div style={S.statRow}>
                    <span style={S.statLabel}>Téléphone</span>
                    <span style={S.statVal()}>{pm.phone}</span>
                  </div>
                )}
                {pm.email && (
                  <div style={S.statRow}>
                    <span style={S.statLabel}>Email</span>
                    <span style={S.statVal()}>{pm.email}</span>
                  </div>
                )}
                <div style={S.statRow}>
                  <span style={S.statLabel}>Créé le</span>
                  <span style={S.statVal()}>{fmtDate(pm.date_joined)}</span>
                </div>
                <div style={{ ...S.statRow, borderBottom: 'none' }}>
                  <span style={S.statLabel}>Dernière connexion</span>
                  <span style={S.statVal()}>{fmtDateTime(pm.last_login)}</span>
                </div>
              </div>

              {canManage && (
                <div style={S.cardFoot}>
                  <Button variant="secondary" size="sm" onClick={() => openEdit(pm)}>
                    <EditIcon size={14} /> Modifier
                  </Button>
                  {isDG && pm.is_active && (
                    <Button variant="warning" size="sm" onClick={() => handleDeactivate(pm)}>
                      Désactiver
                    </Button>
                  )}
                  {isDG && !pm.is_active && (
                    <Button variant="success" size="sm" onClick={() => handleReactivate(pm)}>
                      Réactiver
                    </Button>
                  )}
                  {isDG && (
                    <Button variant="danger" size="sm" onClick={() => handleDeletePermanently(pm)}
                      title="Supprimer définitivement le compte">
                      <TrashIcon size={14} /> Supprimer
                    </Button>
                  )}
                  {isDOP && pm.is_active && (
                    <Button variant="warning" size="sm" onClick={() => handleProposeDeletion(pm)}>
                      Proposer suppression
                    </Button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Modal Créer ──────────────────────────────────────────────────────── */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Nouveau Chef de Projet"
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setShowCreate(false)}>Annuler</Button>
            <Button variant="primary" type="submit" form="pm-create-form">
              {isDG ? 'Créer le compte' : 'Soumettre la demande'}
            </Button>
          </>
        )}
      >
        <form id="pm-create-form" onSubmit={handleCreate}>
          {!isDG && (
            <div style={{ ...S.alertBox, background: 'var(--accent-bg)', border: '1px solid var(--border-default)', color: 'var(--accent-light)', marginTop: 0, marginBottom: '16px' }}>
              Cette demande sera soumise au DG pour validation avant la création réelle du compte.
            </div>
          )}
          <div style={S.fGroup}>
            <label style={S.label}>Identifiant *</label>
            <input style={S.input} type="text" placeholder="Ex : a.diallo" value={form.username}
              onChange={e => setForm(p => ({ ...p, username: e.target.value }))} required />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={S.fGroup}>
              <label style={S.label}>Prénom</label>
              <input style={S.input} type="text" value={form.first_name}
                onChange={e => setForm(p => ({ ...p, first_name: e.target.value }))} />
            </div>
            <div style={S.fGroup}>
              <label style={S.label}>Nom</label>
              <input style={S.input} type="text" value={form.last_name}
                onChange={e => setForm(p => ({ ...p, last_name: e.target.value }))} />
            </div>
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Téléphone</label>
            <input style={S.input} type="text" value={form.phone}
              onChange={e => setForm(p => ({ ...p, phone: e.target.value }))} />
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Email</label>
            <input style={S.input} type="email" value={form.email}
              onChange={e => setForm(p => ({ ...p, email: e.target.value }))} />
          </div>
          {isDG && (
            <div style={S.fGroup}>
              <label style={S.label}>Mot de passe *</label>
              <input style={S.input} type="text" placeholder="6 caractères minimum" value={form.password}
                onChange={e => setForm(p => ({ ...p, password: e.target.value }))} required />
            </div>
          )}
          {!isDG && (
            <p style={{ fontSize: '11px', color: 'var(--text-disabled)' }}>
              Le mot de passe du compte sera défini par le DG au moment de la validation.
            </p>
          )}
        </form>
      </Modal>

      {/* ── Modal Modifier ───────────────────────────────────────────────────── */}
      <Modal
        open={showEdit && !!selected}
        onClose={() => setShowEdit(false)}
        title={selected ? `Modifier — ${selected.full_name}` : 'Modifier'}
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setShowEdit(false)}>Annuler</Button>
            <Button variant="primary" type="submit" form="pm-edit-form">Enregistrer</Button>
          </>
        )}
      >
        <form id="pm-edit-form" onSubmit={handleEdit}>
          <div style={S.fGroup}>
            <label style={S.label}>Identifiant</label>
            <input style={{ ...S.input, opacity: .6 }} type="text" value={form.username} disabled />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={S.fGroup}>
              <label style={S.label}>Prénom</label>
              <input style={S.input} type="text" value={form.first_name}
                onChange={e => setForm(p => ({ ...p, first_name: e.target.value }))} />
            </div>
            <div style={S.fGroup}>
              <label style={S.label}>Nom</label>
              <input style={S.input} type="text" value={form.last_name}
                onChange={e => setForm(p => ({ ...p, last_name: e.target.value }))} />
            </div>
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Téléphone</label>
            <input style={S.input} type="text" value={form.phone}
              onChange={e => setForm(p => ({ ...p, phone: e.target.value }))} />
          </div>
          <div style={S.fGroup}>
            <label style={S.label}>Email</label>
            <input style={S.input} type="email" value={form.email}
              onChange={e => setForm(p => ({ ...p, email: e.target.value }))} />
          </div>
          {isDG && (
            <div style={S.fGroup}>
              <label style={S.label}>Nouveau mot de passe</label>
              <input style={S.input} type="text" placeholder="Laisser vide pour ne pas changer" value={form.password}
                onChange={e => setForm(p => ({ ...p, password: e.target.value }))} />
            </div>
          )}
        </form>
      </Modal>

      {/* ── Modal Valider une demande de création de compte ──────────────────── */}
      <Modal
        open={showApprove && !!approveTarget}
        onClose={() => setShowApprove(false)}
        title={approveTarget ? `Valider — ${approveTarget.reference}` : 'Valider'}
        footer={(
          <>
            <Button variant="secondary" onClick={() => setShowApprove(false)}>Annuler</Button>
            <Button variant="primary" onClick={handleApprove} disabled={approving}>
              {approving ? 'Validation…' : 'Confirmer la validation'}
            </Button>
          </>
        )}
      >
        {approveTarget && (approveTarget.request_type === 'creation_chef_projet' ? (
          <>
            <p style={{ fontSize: '13px', color: 'var(--text-tertiary)', marginTop: 0 }}>
              Le compte <strong style={{ color: 'var(--text-primary)' }}>{approveTarget.payload?.username}</strong> sera créé
              avec le mot de passe défini ci-dessous.
            </p>
            <div style={S.fGroup}>
              <label style={S.label}>Mot de passe du compte *</label>
              <input style={S.input} type="text" placeholder="6 caractères minimum" value={approvePassword}
                onChange={e => setApprovePassword(e.target.value)} required />
            </div>
          </>
        ) : (
          <p style={{ fontSize: '13px', color: 'var(--text-tertiary)', marginTop: 0 }}>
            Confirmer la désactivation du compte visé par cette demande ?
          </p>
        ))}
      </Modal>

    </div>
  );
};

export default ProjectManagers;
