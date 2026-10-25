import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import api from '../../api/axios';
import toast from 'react-hot-toast';
import { Modal, Button, Badge } from '../../design-system';

const STATUS_MAP = {
  brouillon: { tone: 'muted',   label: 'Brouillon' },
  en_cours:  { tone: 'accent',  label: 'En cours'  },
  suspendu:  { tone: 'warning', label: 'Suspendu'  },
  termine:   { tone: 'success', label: 'Terminé'   },
  annule:    { tone: 'danger',  label: 'Annulé'    },
};

const EF = {
  code: '', name: '', description: '', client: '',
  location: '', contract_date: '', start_date: '',
  planned_end_date: '', budget: '', project_manager: '',
};

export default function Projects() {
  const { user }       = useAuth();
  const navigate       = useNavigate();
  const [projects,     setProjects]     = useState([]);
  const [chefProjects, setChefProjects] = useState([]);
  const [loading,      setLoading]      = useState(true);
  const [showModal,    setShowModal]    = useState(false);
  const [editing,      setEditing]      = useState(null);
  const [form,         setForm]         = useState(EF);
  const [saving,       setSaving]       = useState(false);
  const [search,       setSearch]       = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  const canCreate   = user?.is_ops_chief;
  const canEdit     = user?.is_ops_chief;
  const canDelete   = user?.is_ops_chief;
  const canValidate = user?.is_dg;

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const p = await api.get('/operations/projects/');
      setProjects(p.data.results || p.data);
      try {
        const u = await api.get('/operations/projects/users/');
        setChefProjects(u.data || []);
      } catch { setChefProjects([]); }
    } catch {
      toast.error('Erreur de chargement des projets');
      setProjects([]);
    } finally { setLoading(false); }
  };

  const filtered = projects.filter(p => {
    const matchSearch = !search ||
      p.code?.toLowerCase().includes(search.toLowerCase()) ||
      p.name?.toLowerCase().includes(search.toLowerCase()) ||
      p.client?.toLowerCase().includes(search.toLowerCase());
    const matchStatus = !filterStatus || p.status === filterStatus;
    return matchSearch && matchStatus;
  });

  const stats = {
    total:    projects.length,
    en_cours: projects.filter(p => p.status === 'en_cours').length,
    termine:  projects.filter(p => p.status === 'termine').length,
    suspendu: projects.filter(p => p.status === 'suspendu').length,
  };

  const openCreate = () => { setEditing(null); setForm(EF); setShowModal(true); };
  const openEdit   = (p) => {
    setEditing(p);
    setForm({
      code: p.code, name: p.name, description: p.description || '',
      client: p.client || '', location: p.location || '',
      contract_date: p.contract_date || '', start_date: p.start_date || '',
      planned_end_date: p.planned_end_date || '',
      budget: p.budget || '',
      project_manager: p.project_manager || '',
    });
    setShowModal(true);
  };

  const handleSave = async (e) => {
    e.preventDefault(); setSaving(true);
    try {
      const payload = {
        code:             form.code,
        name:             form.name,
        description:      form.description || '',
        client:           form.client || '',
        location:         form.location || '',
        budget:           form.budget ? Number(form.budget) : null,
        contract_date:    form.contract_date    || null,
        start_date:       form.start_date       || null,
        planned_end_date: form.planned_end_date || null,
        project_manager:  form.project_manager  || null,
      };
      if (editing) {
        await api.put(`/operations/projects/${editing.id}/`, payload);
        toast.success('Projet modifié');
      } else {
        await api.post('/operations/projects/', payload);
        toast.success('Projet créé — en attente de validation');
      }
      setShowModal(false); fetchAll();
    } catch (err) {
      const d = err.response?.data;
      toast.error(d?.code?.[0] || d?.name?.[0] || d?.detail || 'Erreur');
    } finally { setSaving(false); }
  };

  const handleValidate = async (project) => {
    if (!window.confirm(`Valider le projet ${project.code} ?`)) return;
    try {
      await api.post(`/operations/projects/${project.id}/validate/`);
      toast.success('Projet validé');
      fetchAll();
    } catch (err) { toast.error(err.response?.data?.detail || 'Erreur'); }
  };

  const handleDelete = async (project) => {
    if (!window.confirm(`Supprimer définitivement "${project.code} — ${project.name}" ?`)) return;
    try {
      await api.delete(`/operations/projects/${project.id}/`);
      toast.success('Projet supprimé');
      fetchAll();
    } catch (err) { toast.error(err.response?.data?.detail || 'Erreur'); }
  };

  return (
    <div style={S.page}>

      {/* Header */}
      <div style={S.header}>
        <div>
          <h1 style={S.title}>{user?.is_project_manager ? 'Mes Projets' : 'Opérations & Projets'}</h1>
          <p style={S.subtitle}>{projects.length} projet(s) enregistré(s)</p>
        </div>
        {canCreate && (
          <Button variant="primary" onClick={openCreate}>+ Nouveau Projet</Button>
        )}
      </div>

      {/* KPIs */}
      <div style={S.kpiRow}>
        {[
          { label: 'Total',     value: stats.total,    color: 'var(--accent-light)'  },
          { label: 'En cours',  value: stats.en_cours, color: 'var(--accent-light)'  },
          { label: 'Terminés',  value: stats.termine,  color: 'var(--success-light)' },
          { label: 'Suspendus', value: stats.suspendu, color: 'var(--warning)'       },
        ].map(k => (
          <div key={k.label} style={S.kpi}>
            <span style={{ ...S.kpiVal, color: k.color }}>{k.value}</span>
            <span style={S.kpiLbl}>{k.label}</span>
          </div>
        ))}
      </div>

      {/* Filtres */}
      <div style={S.filterRow}>
        <input style={S.search}
          placeholder="Rechercher par code, nom ou client..."
          value={search} onChange={e => setSearch(e.target.value)} />
        <div style={S.filterBtns}>
          {[
            { v: '',          label: 'Tous'      },
            { v: 'brouillon', label: 'Brouillon' },
            { v: 'en_cours',  label: 'En cours'  },
            { v: 'suspendu',  label: 'Suspendu'  },
            { v: 'termine',   label: 'Terminé'   },
          ].map(f => (
            <button key={f.v}
              style={{ ...S.filterBtn, ...(filterStatus === f.v ? S.filterBtnActive : {}) }}
              onClick={() => setFilterStatus(f.v)}>
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Liste */}
      {loading ? <div style={S.loading}>Chargement...</div>
      : filtered.length === 0 ? (
        <div style={S.empty}>
          {user?.is_project_manager
            ? 'Aucun projet ne vous a été attribué pour le moment'
            : 'Aucun projet trouvé'}
        </div>
      ) : (
        <div style={S.projectList}>
          {filtered.map(project => {
            const st       = STATUS_MAP[project.status] || STATUS_MAP.brouillon;
            const progress = project.global_progress || 0;
            return (
              <div key={project.id} style={S.projectCard}>
                <div style={S.cardLeft}>
                  <div style={S.cardTopRow}>
                    <span style={S.projCode}>{project.code}</span>
                    <Badge tone={st.tone}>{st.label}</Badge>
                    {project.validated_by_dg
                      ? <Badge tone="success">Validé</Badge>
                      : <Badge tone="warning">En attente de validation</Badge>
                    }
                  </div>
                  <div style={S.projName}>{project.name}</div>
                  <div style={S.projMeta}>
                    {project.client && <span>{project.client}</span>}
                    {project.location && <><span style={S.sep}>·</span><span>{project.location}</span></>}
                    {project.project_manager_name
                      ? <><span style={S.sep}>·</span><span>Chef : {project.project_manager_name}</span></>
                      : <><span style={S.sep}>·</span><span style={{ color: 'var(--warning)' }}>Aucun chef de projet</span></>
                    }
                    {project.planned_end_date && (
                      <><span style={S.sep}>·</span>
                      <span>Fin prévue : {new Date(project.planned_end_date).toLocaleDateString('fr-FR')}</span></>
                    )}
                  </div>
                  <div style={S.progressArea}>
                    <div style={S.progressBar}>
                      <div style={{
                        ...S.progressFill,
                        width: `${progress}%`,
                        background: progress >= 80 ? 'var(--success-light)' : progress >= 50 ? 'var(--accent)' : 'var(--warning)',
                      }} />
                    </div>
                    <span style={S.progressText}>{progress}%</span>
                  </div>
                </div>

                <div style={S.cardRight}>
                  <Button variant="secondary" size="sm" onClick={() => navigate(`/operations/${project.id}`)}>
                    Ouvrir
                  </Button>
                  {canEdit && (
                    <Button variant="secondary" size="sm" onClick={() => openEdit(project)}>Modifier</Button>
                  )}
                  {canValidate && !project.validated_by_dg && (
                    <Button variant="success" size="sm" onClick={() => handleValidate(project)}>
                      Valider
                    </Button>
                  )}
                  {canDelete && (
                    <Button variant="danger" size="sm" onClick={() => handleDelete(project)}>Supprimer</Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal */}
      <Modal
        open={showModal}
        onClose={() => setShowModal(false)}
        title={editing ? `Modifier — ${editing.code}` : 'Nouveau Projet'}
        maxWidth="680px"
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setShowModal(false)}>Annuler</Button>
            <Button variant="primary" type="submit" form="project-form" disabled={saving}>
              {saving ? 'Enregistrement...' : editing ? 'Enregistrer les modifications' : 'Créer le projet'}
            </Button>
          </>
        )}
      >
        <form id="project-form" onSubmit={handleSave}>

          {!editing && (
            <div style={S.infoBanner}>
              Ce projet sera créé en statut "Brouillon" et devra être validé par le Directeur Général avant d'être actif.
            </div>
          )}

          <div style={S.sectionLabel}>Identification</div>
          <div style={S.grid2}>
            <F label="Code projet *">
              <input style={S.input} placeholder="ex: PRJ-2026-001"
                value={form.code}
                onChange={e => setForm({...form, code: e.target.value})}
                required disabled={!!editing} />
            </F>
            <F label="Nom du projet *">
              <input style={S.input} placeholder="Intitulé du projet"
                value={form.name}
                onChange={e => setForm({...form, name: e.target.value})} required />
            </F>
            <F label="Client">
              <input style={S.input} value={form.client}
                onChange={e => setForm({...form, client: e.target.value})} />
            </F>
            <F label="Localisation">
              <input style={S.input} value={form.location}
                onChange={e => setForm({...form, location: e.target.value})} />
            </F>
            <div style={{ gridColumn: '1/-1' }}>
              <F label="Description">
                <textarea style={{ ...S.input, height: '70px', resize: 'vertical' }}
                  value={form.description}
                  onChange={e => setForm({...form, description: e.target.value})} />
              </F>
            </div>
          </div>

          <div style={{ ...S.sectionLabel, marginTop: '0.5rem' }}>Attribution</div>
          <div style={S.grid2}>
            <F label="Chef de projet *">
              <select style={{ ...S.input, cursor: 'pointer' }} value={form.project_manager}
                onChange={e => setForm({...form, project_manager: e.target.value})} required>
                <option value="">Sélectionner un chef de projet</option>
                {chefProjects.map(u => (
                  <option key={u.id} value={u.id}>{u.full_name}</option>
                ))}
              </select>
              {chefProjects.length === 0 && (
                <span style={{ fontSize: '0.72rem', color: 'var(--warning)', marginTop: '4px' }}>
                  Aucun compte "Chef de Projet" disponible.
                </span>
              )}
            </F>
            <F label="Budget (FCFA)">
              <input style={S.input} type="number" min="0" value={form.budget}
                onChange={e => setForm({...form, budget: e.target.value})} />
            </F>
          </div>

          <div style={{ ...S.sectionLabel, marginTop: '0.5rem' }}>Dates</div>
          <div style={S.grid3}>
            <F label="Date de contrat">
              <input style={S.input} type="date" value={form.contract_date}
                onChange={e => setForm({...form, contract_date: e.target.value})} />
            </F>
            <F label="Date de démarrage">
              <input style={S.input} type="date" value={form.start_date}
                onChange={e => setForm({...form, start_date: e.target.value})} />
            </F>
            <F label="Date de fin prévue">
              <input style={S.input} type="date" value={form.planned_end_date}
                onChange={e => setForm({...form, planned_end_date: e.target.value})} />
            </F>
          </div>
        </form>
      </Modal>
    </div>
  );
}

const F = ({ label, children }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginBottom: '0.875rem' }}>
    <label style={{ fontSize: '0.72rem', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</label>
    {children}
  </div>
);

const S = {
  page:         { padding: '2rem 2.5rem', color: 'var(--text-secondary)' },
  header:       { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' },
  title:        { fontSize: '1.5rem', fontWeight: '700', color: 'var(--text-primary)', letterSpacing: '-0.4px', margin: 0 },
  subtitle:     { fontSize: '0.8rem', color: 'var(--text-disabled)', marginTop: '0.2rem' },
  kpiRow:       { display: 'flex', gap: '1px', marginBottom: '1.25rem', background: 'var(--border-default)', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-default)' },
  kpi:          { flex: 1, padding: '0.875rem 1.25rem', background: 'var(--bg-surface)', display: 'flex', flexDirection: 'column', gap: '0.25rem' },
  kpiVal:       { fontSize: '1.6rem', fontWeight: '700', letterSpacing: '-0.5px', lineHeight: 1 },
  kpiLbl:       { fontSize: '0.65rem', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '0.5px' },
  filterRow:    { display: 'flex', gap: '0.75rem', marginBottom: '1.25rem', alignItems: 'center', flexWrap: 'wrap' },
  search:       { flex: 1, padding: '0.65rem 0.875rem', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '7px', fontSize: '0.875rem', outline: 'none', color: 'var(--text-secondary)' },
  filterBtns:   { display: 'flex', gap: '0.375rem' },
  filterBtn:    { padding: '0.4rem 0.875rem', border: '1px solid var(--border-default)', borderRadius: '6px', background: 'transparent', cursor: 'pointer', fontSize: '0.78rem', color: 'var(--text-disabled)', fontWeight: '500' },
  filterBtnActive: { background: 'var(--accent-bg)', color: 'var(--accent-light)', borderColor: 'var(--accent)' },
  loading:      { padding: '3rem', textAlign: 'center', color: 'var(--text-disabled)' },
  empty:        { padding: '3rem', textAlign: 'center', color: 'var(--text-disabled)', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px' },
  projectList:  { display: 'flex', flexDirection: 'column', gap: '0.625rem' },
  projectCard:  { background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px', padding: '1.1rem 1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' },
  cardLeft:     { flex: 1, minWidth: 0 },
  cardTopRow:   { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem', flexWrap: 'wrap' },
  projCode:     { fontFamily: "'DM Mono', monospace", fontSize: '0.85rem', color: 'var(--accent-light)', fontWeight: '600' },
  projName:     { fontSize: '0.95rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '0.3rem' },
  projMeta:     { display: 'flex', gap: '0.4rem', fontSize: '0.78rem', color: 'var(--text-disabled)', flexWrap: 'wrap', alignItems: 'center', marginBottom: '0.75rem' },
  sep:          { color: 'var(--border-default)' },
  progressArea: { display: 'flex', alignItems: 'center', gap: '0.75rem', maxWidth: '400px' },
  progressBar:  { flex: 1, height: '5px', background: 'var(--border-default)', borderRadius: '3px', overflow: 'hidden' },
  progressFill: { height: '100%', borderRadius: '3px', transition: 'width 0.4s ease' },
  progressText: { fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-muted)', fontFamily: "'DM Mono', monospace", minWidth: '38px', textAlign: 'right' },
  cardRight:    { display: 'flex', gap: '0.5rem', flexShrink: 0, flexWrap: 'wrap' },
  infoBanner:   { background: 'var(--warning-bg)', border: '1px solid var(--warning)', borderRadius: '8px', padding: '0.75rem 1rem', fontSize: '0.8rem', color: 'var(--warning)', marginBottom: '1.25rem' },
  sectionLabel: { fontSize: '0.7rem', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '0.875rem' },
  grid2:        { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 1rem' },
  grid3:        { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0 1rem' },
  input:        { padding: '0.65rem 0.875rem', background: 'var(--bg-surface-alt)', border: '1px solid var(--border-default)', borderRadius: '7px', fontSize: '0.875rem', outline: 'none', color: 'var(--text-secondary)', width: '100%', boxSizing: 'border-box' },
};
