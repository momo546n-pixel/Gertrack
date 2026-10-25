import { useState, useEffect } from 'react';
import api from '../api/axios';
import toast from 'react-hot-toast';
import { Modal, Button } from '../design-system';

const EF = { name:'', contact_person:'', phone:'', email:'', address:'', city:'', notes:'' };

export default function Suppliers() {
  const user      = JSON.parse(localStorage.getItem('user') || '{}');
  const canManage = user.role === 'dg' || user.is_dg === true || user.role === 'stock';
  const [suppliers, setSuppliers] = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [search,    setSearch]    = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editing,   setEditing]   = useState(null);
  const [form,      setForm]      = useState(EF);
  const [saving,    setSaving]    = useState(false);

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    setLoading(true);
    try { const r = await api.get('/suppliers/'); setSuppliers(r.data.results || r.data); }
    catch { toast.error('Erreur de chargement'); }
    finally { setLoading(false); }
  };

  const filtered = suppliers.filter(s =>
    !search ||
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.city?.toLowerCase().includes(search.toLowerCase()) ||
    s.email?.toLowerCase().includes(search.toLowerCase())
  );

  const openCreate = () => { setEditing(null); setForm(EF); setShowModal(true); };
  const openEdit   = (s) => {
    setEditing(s);
    setForm({ name:s.name, contact_person:s.contact_person, phone:s.phone, email:s.email, address:s.address, city:s.city, notes:s.notes });
    setShowModal(true);
  };

  const handleSave = async (e) => {
    e.preventDefault(); setSaving(true);
    try {
      editing ? await api.put(`/suppliers/${editing.id}/`, form) : await api.post('/suppliers/', form);
      toast.success(editing ? 'Fournisseur modifié' : 'Fournisseur ajouté');
      setShowModal(false); fetchAll();
    } catch (err) { toast.error(err.response?.data?.email?.[0] || 'Erreur'); }
    finally { setSaving(false); }
  };

  const handleDelete = async (s) => {
    if (!window.confirm(`Désactiver "${s.name}" ?`)) return;
    try { await api.delete(`/suppliers/${s.id}/`); toast.success('Désactivé'); fetchAll(); }
    catch { toast.error('Erreur'); }
  };

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div>
          <h1 style={S.title}>Fournisseurs</h1>
          <p style={S.sub}>{suppliers.length} fournisseur(s) actif(s)</p>
        </div>
        {canManage && (
          <Button variant="primary" onClick={openCreate}>+ Nouveau Fournisseur</Button>
        )}
      </div>

      <input style={S.search}
        placeholder="Rechercher par nom, ville ou email..."
        value={search} onChange={e => setSearch(e.target.value)} />

      {loading ? <div style={S.loading}>Chargement...</div>
      : filtered.length === 0 ? <div style={S.empty}>Aucun fournisseur trouvé</div>
      : (
        <div style={S.grid}>
          {filtered.map(s => (
            <div key={s.id} style={S.card}>
              <div style={S.cardHead}>
                <div style={S.avatar}>{s.name.charAt(0).toUpperCase()}</div>
                <div style={{ flex:1, minWidth:0 }}>
                  <div style={S.cardName}>{s.name}</div>
                  {s.city && <div style={S.cardCity}>{s.city}</div>}
                </div>
                <div style={S.cmdBadge}>{s.total_orders || 0} cmd</div>
              </div>

              <div style={S.cardBody}>
                {[
                  { label:'Contact', value:s.contact_person },
                  { label:'Tél.',    value:s.phone          },
                  { label:'Email',   value:s.email, blue:true },
                  { label:'Adresse', value:s.address        },
                ].filter(r => r.value).map(row => (
                  <div key={row.label} style={S.infoRow}>
                    <span style={S.infoLabel}>{row.label}</span>
                    <span style={{ ...S.infoVal, ...(row.blue ? { color:'var(--accent-light)' } : {}) }}>{row.value}</span>
                  </div>
                ))}
                {s.notes && <div style={S.notes}>{s.notes}</div>}

                {/* Performance fournisseur (Phase F — §7) */}
                {s.taux_livraison_a_temps !== null && s.taux_livraison_a_temps !== undefined && (
                  <div style={S.perfBox}>
                    <div style={S.perfTitle}>Performance livraisons</div>
                    <div style={S.perfGrid}>
                      <div style={S.perfCell}>
                        <div style={{ ...S.perfVal, color: s.taux_livraison_a_temps >= 80 ? 'var(--success-light)' : s.taux_livraison_a_temps >= 50 ? 'var(--warning)' : 'var(--danger)' }}>
                          {s.taux_livraison_a_temps}%
                        </div>
                        <div style={S.perfLbl}>À temps</div>
                      </div>
                      <div style={S.perfCell}>
                        <div style={{ ...S.perfVal, color: s.delai_moyen_jours > 0 ? 'var(--warning)' : 'var(--accent-light)' }}>
                          {s.delai_moyen_jours > 0 ? `+${s.delai_moyen_jours}` : s.delai_moyen_jours}j
                        </div>
                        <div style={S.perfLbl}>Écart moyen</div>
                      </div>
                      <div style={S.perfCell}>
                        <div style={{ ...S.perfVal, color: s.commandes_en_retard_count > 0 ? 'var(--danger)' : 'var(--success-light)' }}>
                          {s.commandes_en_retard_count}
                        </div>
                        <div style={S.perfLbl}>En retard</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {canManage && (
                <div style={S.cardFoot}>
                  <button style={S.btnEdit}   onClick={() => openEdit(s)}>Modifier</button>
                  <button style={S.btnDelete} onClick={() => handleDelete(s)}>Désactiver</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <Modal
        open={showModal}
        onClose={() => setShowModal(false)}
        title={editing ? `Modifier — ${editing.name}` : 'Nouveau Fournisseur'}
        maxWidth="540px"
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setShowModal(false)}>Annuler</Button>
            <Button variant="primary" type="submit" form="supplier-form" disabled={saving}>
              {saving ? 'Enregistrement...' : editing ? 'Enregistrer' : 'Ajouter'}
            </Button>
          </>
        )}
      >
        <form id="supplier-form" onSubmit={handleSave}>
          <div style={S.grid2}>
            <div style={{ gridColumn:'1/-1' }}>
              <F label="Nom du fournisseur *">
                <input style={S.input} value={form.name}
                  onChange={e => setForm({...form, name:e.target.value})} required />
              </F>
            </div>
            <F label="Contact">
              <input style={S.input} value={form.contact_person}
                onChange={e => setForm({...form, contact_person:e.target.value})} />
            </F>
            <F label="Téléphone">
              <input style={S.input} value={form.phone}
                onChange={e => setForm({...form, phone:e.target.value})} />
            </F>
            <F label="Email">
              <input style={S.input} type="email" value={form.email}
                onChange={e => setForm({...form, email:e.target.value})} />
            </F>
            <F label="Ville">
              <input style={S.input} value={form.city}
                onChange={e => setForm({...form, city:e.target.value})} />
            </F>
            <div style={{ gridColumn:'1/-1' }}>
              <F label="Adresse">
                <input style={S.input} value={form.address}
                  onChange={e => setForm({...form, address:e.target.value})} />
              </F>
            </div>
            <div style={{ gridColumn:'1/-1' }}>
              <F label="Notes">
                <textarea style={{ ...S.input, height:'70px', resize:'vertical' }}
                  value={form.notes} onChange={e => setForm({...form, notes:e.target.value})} />
              </F>
            </div>
          </div>
        </form>
      </Modal>
    </div>
  );
}

const F = ({ label, children }) => (
  <div style={{ display:'flex', flexDirection:'column', gap:'0.4rem', marginBottom:'0.875rem' }}>
    <label style={{ fontSize:'0.7rem', fontWeight:'600', color:'var(--text-faint)', textTransform:'uppercase', letterSpacing:'1px' }}>{label}</label>
    {children}
  </div>
);

const S = {
  page:     { color:'var(--text-secondary)' },
  header:   { display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'1.5rem' },
  title:    { fontSize:'1.6rem', fontWeight:'700', color:'var(--text-primary)', margin:0, letterSpacing:'-0.4px' },
  sub:      { fontSize:'0.8rem', color:'var(--text-faint)', marginTop:'0.25rem' },
  search:   { width:'100%', padding:'0.65rem 0.875rem', background:'var(--bg-surface)', border:'1px solid var(--border-subtle)', borderRadius:'7px', fontSize:'0.875rem', color:'var(--text-secondary)', outline:'none', marginBottom:'1.25rem', boxSizing:'border-box' },
  loading:  { padding:'3rem', textAlign:'center', color:'var(--text-disabled)' },
  empty:    { padding:'3rem', textAlign:'center', color:'var(--text-disabled)' },
  grid:     { display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(300px, 1fr))', gap:'0.875rem' },
  card:     { background:'var(--bg-surface)', border:'1px solid var(--border-subtle)', borderRadius:'10px', overflow:'hidden' },
  cardHead: { display:'flex', gap:'0.875rem', alignItems:'center', padding:'1rem', borderBottom:'1px solid var(--border-faint)' },
  avatar:   { width:'42px', height:'42px', borderRadius:'10px', background:'var(--accent-gradient)', color:'white', display:'flex', alignItems:'center', justifyContent:'center', fontWeight:'800', fontSize:'1.1rem', flexShrink:0 },
  cardName: { fontWeight:'700', fontSize:'0.9rem', color:'var(--text-primary)' },
  cardCity: { fontSize:'0.75rem', color:'var(--text-disabled)', marginTop:'2px' },
  cmdBadge: { background:'var(--accent-bg)', color:'var(--accent-light)', fontSize:'0.7rem', fontWeight:'700', padding:'0.2rem 0.55rem', borderRadius:'4px', marginLeft:'auto', flexShrink:0 },
  cardBody: { padding:'0.75rem 1rem' },
  infoRow:  { display:'flex', gap:'0.75rem', fontSize:'0.78rem', color:'var(--text-faint)', padding:'0.3rem 0', borderBottom:'1px solid var(--border-faint)' },
  infoLabel:{ fontSize:'0.68rem', fontWeight:'700', color:'var(--border-default)', textTransform:'uppercase', letterSpacing:'0.4px', minWidth:'52px' },
  infoVal:  { color:'var(--text-muted)' },
  notes:    { marginTop:'0.5rem', fontSize:'0.75rem', color:'var(--text-disabled)', fontStyle:'italic', padding:'0.4rem 0.6rem', background:'var(--bg-surface-alt)', borderRadius:'5px' },
  perfBox:  { marginTop:'0.75rem', paddingTop:'0.75rem', borderTop:'1px solid var(--border-faint)' },
  perfTitle:{ fontSize:'0.65rem', fontWeight:'700', color:'var(--border-default)', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:'0.5rem' },
  perfGrid: { display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:'0.5rem' },
  perfCell: { textAlign:'center', background:'var(--bg-surface-alt)', borderRadius:'6px', padding:'0.5rem' },
  perfVal:  { fontSize:'0.95rem', fontWeight:'800' },
  perfLbl:  { fontSize:'0.6rem', color:'var(--text-disabled)', fontWeight:'600', textTransform:'uppercase', marginTop:'2px' },
  cardFoot: { display:'flex', gap:'0.5rem', padding:'0.625rem 1rem', borderTop:'1px solid var(--border-faint)' },
  btnEdit:  { flex:1, padding:'0.4rem', background:'var(--accent-bg)', color:'var(--accent-light)', border:'1px solid transparent', borderRadius:'6px', cursor:'pointer', fontSize:'0.78rem', fontWeight:'600' },
  btnDelete:{ flex:1, padding:'0.4rem', background:'var(--danger-bg)', color:'var(--danger)', border:'1px solid transparent', borderRadius:'6px', cursor:'pointer', fontSize:'0.78rem', fontWeight:'600' },
  grid2:    { display:'grid', gridTemplateColumns:'1fr 1fr', gap:'0 1rem' },
  input:    { width:'100%', padding:'0.65rem 0.875rem', background:'var(--bg-surface-alt)', border:'1px solid var(--border-subtle)', borderRadius:'7px', fontSize:'0.875rem', color:'var(--text-secondary)', outline:'none', boxSizing:'border-box' },
};
