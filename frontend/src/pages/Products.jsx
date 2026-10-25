import { useState, useEffect } from 'react';
import api from '../api/axios';
import toast from 'react-hot-toast';
import { Modal, Button, Badge } from '../design-system';

const STATUS = {
  suffisant: { tone: 'success',    label: 'Suffisant' },
  critique:  { tone: 'warningAlt', label: 'Critique'  },
  rupture:   { tone: 'danger',     label: 'Rupture'   },
};

const EF = { code:'', designation:'', category:'', unit:'Unité', conditionnement:'', stock_actuel:0, stock_securite:0, description:'' };

export default function Products() {
  const user      = JSON.parse(localStorage.getItem('user') || '{}');
  const canManage = user.role === 'dg' || user.is_dg === true || user.role === 'stock';
  const [products,   setProducts]   = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [search,     setSearch]     = useState('');
  const [filterCat,  setFilterCat]  = useState('');
  const [modal,      setModal]      = useState(false);
  const [catModal,   setCatModal]   = useState(false);
  const [editing,    setEditing]    = useState(null);
  const [form,       setForm]       = useState(EF);
  const [saving,     setSaving]     = useState(false);
  const [newCat,     setNewCat]     = useState('');

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [p, c] = await Promise.all([
        api.get('/products/?active_only=true'),
        api.get('/products/categories/'),
      ]);
      setProducts(p.data.results || p.data);
      setCategories(c.data.results || c.data);
    } catch { toast.error('Erreur de chargement'); }
    finally { setLoading(false); }
  };

  const filtered = products.filter(p =>
    (!search || p.code.toLowerCase().includes(search.toLowerCase()) || p.designation.toLowerCase().includes(search.toLowerCase())) &&
    (!filterCat || String(p.category) === String(filterCat))
  );

  const stats = {
    total:    products.length,
    ok:       products.filter(p => p.stock_status === 'suffisant').length,
    critique: products.filter(p => p.stock_status === 'critique').length,
    rupture:  products.filter(p => p.stock_status === 'rupture').length,
  };

  const openCreate = () => { setEditing(null); setForm(EF); setModal(true); };
  const openEdit   = (p) => {
    setEditing(p);
    setForm({ code:p.code, designation:p.designation, category:p.category||'', unit:p.unit, conditionnement:p.conditionnement, stock_actuel:p.stock_actuel, stock_securite:p.stock_securite, description:p.description });
    setModal(true);
  };

  const handleSave = async (e) => {
    e.preventDefault(); setSaving(true);
    try {
      const pl = { ...form, category:form.category||null, stock_actuel:Number(form.stock_actuel), stock_securite:Number(form.stock_securite) };
      editing ? await api.put(`/products/${editing.id}/`, pl) : await api.post('/products/', pl);
      toast.success(editing ? 'Produit modifié' : 'Produit créé');
      setModal(false); fetchAll();
    } catch (err) { toast.error(err.response?.data?.code?.[0] || 'Erreur'); }
    finally { setSaving(false); }
  };

  const handleDelete = async (p) => {
    if (!window.confirm(`Désactiver ${p.code} ?`)) return;
    try { await api.delete(`/products/${p.id}/`); toast.success('Désactivé'); fetchAll(); }
    catch { toast.error('Erreur'); }
  };

  const handleAddCat = async (e) => {
    e.preventDefault();
    try { await api.post('/products/categories/', { name: newCat }); toast.success('Catégorie ajoutée'); setNewCat(''); setCatModal(false); fetchAll(); }
    catch { toast.error('Erreur'); }
  };

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div>
          <h1 style={S.title}>Produits</h1>
          <p style={S.sub}>{products.length} référence(s) active(s)</p>
        </div>
        {canManage && (
          <div style={S.hBtns}>
            <Button variant="secondary" onClick={() => setCatModal(true)}>+ Catégorie</Button>
            <Button variant="primary" onClick={openCreate}>+ Nouveau produit</Button>
          </div>
        )}
      </div>

      {/* KPIs */}
      <div style={S.kpiRow}>
        {[
          { label:'Total',     v:stats.total,    c:'var(--accent-light)' },
          { label:'Suffisant', v:stats.ok,       c:'var(--success)' },
          { label:'Critique',  v:stats.critique, c:'var(--warning-alt)' },
          { label:'Rupture',   v:stats.rupture,  c:'var(--danger)' },
        ].map(k => (
          <div key={k.label} style={S.kpi}>
            <span style={{ ...S.kpiVal, color:k.c }}>{k.v}</span>
            <span style={S.kpiLbl}>{k.label}</span>
          </div>
        ))}
      </div>

      {/* Filtres */}
      <div style={S.filterRow}>
        <input style={S.search} placeholder="Code ou désignation..."
          value={search} onChange={e => setSearch(e.target.value)} />
        <select style={S.select} value={filterCat} onChange={e => setFilterCat(e.target.value)}>
          <option value="">Toutes les catégories</option>
          {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>

      {/* Tableau */}
      <div style={S.tableBox}>
        <table style={S.table}>
          <thead>
            <tr style={S.thead}>
              {['Code','Désignation','Catégorie','Unité','Stock actuel','Sécurité','Statut',''].map(h => (
                <th key={h} style={S.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? <tr><td colSpan={8} style={S.empty}>Chargement...</td></tr>
            : filtered.length === 0 ? <tr><td colSpan={8} style={S.empty}>Aucun produit trouvé</td></tr>
            : filtered.map((p, i) => {
              const st = STATUS[p.stock_status] || STATUS.suffisant;
              return (
                <tr key={p.id} style={{ ...S.tr, background: i%2 ? 'var(--bg-surface-sunken)':'' }}>
                  <td style={S.td}><span style={S.code}>{p.code}</span></td>
                  <td style={S.td}>
                    <div style={S.desig}>{p.designation}</div>
                    {p.conditionnement && <div style={S.desigSub}>{p.conditionnement}</div>}
                  </td>
                  <td style={S.td}>{p.category_name ? <span style={S.catTag}>{p.category_name}</span> : <span style={S.dash}>—</span>}</td>
                  <td style={S.td}>{p.unit}</td>
                  <td style={{ ...S.td, textAlign:'right', fontWeight:'700', color:'var(--text-primary)', fontFamily:'monospace' }}>
                    {Number(p.stock_actuel).toLocaleString('fr-FR')}
                  </td>
                  <td style={{ ...S.td, textAlign:'right', color:'var(--text-faint)', fontFamily:'monospace' }}>
                    {Number(p.stock_securite).toLocaleString('fr-FR')}
                  </td>
                  <td style={S.td}>
                    <Badge tone={st.tone}>{st.label}</Badge>
                  </td>
                  <td style={S.td}>
                    {canManage && (
                    <div style={S.actions}>
                      <button style={S.actBtn} onClick={() => openEdit(p)}>Modifier</button>
                      <button style={{ ...S.actBtn, color:'var(--danger)' }} onClick={() => handleDelete(p)}>Désactiver</button>
                    </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Modal produit */}
      <Modal
        open={modal}
        onClose={() => setModal(false)}
        title={editing ? `Modifier — ${editing.code}` : 'Nouveau produit'}
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setModal(false)}>Annuler</Button>
            <Button variant="primary" type="submit" form="product-form" disabled={saving}>
              {saving ? 'Enregistrement...' : editing ? 'Enregistrer' : 'Créer le produit'}
            </Button>
          </>
        )}
      >
        <form id="product-form" onSubmit={handleSave}>
          <div style={S.grid2}>
            <F label="Code produit *">
              <input style={S.input} placeholder="ex: PF114"
                value={form.code} onChange={e => setForm({...form, code:e.target.value.toUpperCase()})}
                required disabled={!!editing} />
            </F>
            <F label="Unité *">
              <select style={S.input} value={form.unit} onChange={e => setForm({...form, unit:e.target.value})}>
                {['Unité','Boîte','Kg','Litre','Mètre','Lot','B/10','B/50','B/100'].map(u => <option key={u}>{u}</option>)}
              </select>
            </F>
            <div style={{ gridColumn:'1/-1' }}>
              <F label="Désignation *">
                <input style={S.input} value={form.designation}
                  onChange={e => setForm({...form, designation:e.target.value})} required />
              </F>
            </div>
            <F label="Catégorie">
              <select style={S.input} value={form.category} onChange={e => setForm({...form, category:e.target.value})}>
                <option value="">Sans catégorie</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </F>
            <F label="Conditionnement">
              <input style={S.input} placeholder="ex: Boîte de 10"
                value={form.conditionnement} onChange={e => setForm({...form, conditionnement:e.target.value})} />
            </F>
            <F label="Stock actuel">
              <input style={S.input} type="number" min="0"
                value={form.stock_actuel} onChange={e => setForm({...form, stock_actuel:e.target.value})} />
            </F>
            <F label="Stock de sécurité">
              <input style={S.input} type="number" min="0"
                value={form.stock_securite} onChange={e => setForm({...form, stock_securite:e.target.value})} />
            </F>
            <div style={{ gridColumn:'1/-1' }}>
              <F label="Description">
                <textarea style={{ ...S.input, height:'70px', resize:'vertical' }}
                  value={form.description} onChange={e => setForm({...form, description:e.target.value})} />
              </F>
            </div>
          </div>
        </form>
      </Modal>

      {/* Modal catégorie */}
      <Modal
        open={catModal}
        onClose={() => setCatModal(false)}
        title="Nouvelle catégorie"
        maxWidth="400px"
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setCatModal(false)}>Annuler</Button>
            <Button variant="primary" type="submit" form="category-form">Ajouter</Button>
          </>
        )}
      >
        <form id="category-form" onSubmit={handleAddCat}>
          <F label="Nom de la catégorie *">
            <input style={S.input} value={newCat}
              onChange={e => setNewCat(e.target.value)} required autoFocus />
          </F>
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
  page:       { color:'var(--text-secondary)' },
  header:     { display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'1.5rem' },
  title:      { fontSize:'1.6rem', fontWeight:'700', color:'var(--text-primary)', margin:0, letterSpacing:'-0.4px' },
  sub:        { fontSize:'0.8rem', color:'var(--text-faint)', marginTop:'0.25rem' },
  hBtns:      { display:'flex', gap:'0.625rem' },
  kpiRow:     { display:'flex', gap:'1px', marginBottom:'1.25rem', background:'var(--border-subtle)', borderRadius:'8px', overflow:'hidden' },
  kpi:        { flex:1, padding:'0.875rem 1.25rem', background:'var(--bg-surface)', display:'flex', flexDirection:'column', gap:'0.25rem' },
  kpiVal:     { fontSize:'1.6rem', fontWeight:'800', letterSpacing:'-1px', lineHeight:1 },
  kpiLbl:     { fontSize:'0.65rem', fontWeight:'700', color:'var(--text-faint)', textTransform:'uppercase', letterSpacing:'0.5px' },
  filterRow:  { display:'flex', gap:'0.75rem', marginBottom:'1rem' },
  search:     { flex:1, padding:'0.65rem 0.875rem', background:'var(--bg-surface)', border:'1px solid var(--border-subtle)', borderRadius:'7px', fontSize:'0.875rem', color:'var(--text-secondary)', outline:'none' },
  select:     { padding:'0.65rem 0.875rem', background:'var(--bg-surface)', border:'1px solid var(--border-subtle)', borderRadius:'7px', fontSize:'0.875rem', color:'var(--text-secondary)', outline:'none', minWidth:'200px' },
  tableBox:   { background:'var(--bg-surface)', border:'1px solid var(--border-subtle)', borderRadius:'10px', overflow:'hidden' },
  table:      { width:'100%', borderCollapse:'collapse' },
  thead:      { background:'var(--bg-surface-alt)' },
  th:         { padding:'0.625rem 1rem', fontSize:'0.68rem', fontWeight:'700', color:'var(--text-disabled)', textTransform:'uppercase', letterSpacing:'0.8px', textAlign:'left' },
  tr:         {},
  td:         { padding:'0.75rem 1rem', fontSize:'0.83rem', color:'var(--text-tertiary)', borderTop:'1px solid var(--border-faint)', verticalAlign:'middle' },
  code:       { fontFamily:'monospace', fontSize:'0.8rem', color:'var(--accent-light)', background:'var(--accent-bg)', padding:'0.15rem 0.5rem', borderRadius:'4px' },
  desig:      { fontWeight:'600', color:'var(--text-secondary)' },
  desigSub:   { fontSize:'0.72rem', color:'var(--text-disabled)', marginTop:'2px' },
  catTag:     { background:'var(--bg-surface-alt)', color:'var(--text-faint)', padding:'0.15rem 0.5rem', borderRadius:'4px', fontSize:'0.75rem' },
  dash:       { color:'var(--border-subtle)' },
  actions:    { display:'flex', gap:'0.5rem' },
  actBtn:     { background:'none', border:'none', color:'var(--accent)', cursor:'pointer', fontSize:'0.78rem', fontWeight:'600', padding:'0.2rem 0.4rem' },
  empty:      { padding:'3rem', textAlign:'center', color:'var(--text-disabled)', fontSize:'0.875rem' },
  grid2:      { display:'grid', gridTemplateColumns:'1fr 1fr', gap:'0 1rem' },
  input:      { width:'100%', padding:'0.65rem 0.875rem', background:'var(--bg-surface-alt)', border:'1px solid var(--border-subtle)', borderRadius:'7px', fontSize:'0.875rem', color:'var(--text-secondary)', outline:'none', boxSizing:'border-box' },
};
