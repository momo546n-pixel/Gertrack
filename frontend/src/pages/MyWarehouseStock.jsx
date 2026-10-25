import { useState, useEffect } from 'react';
import api from '../api/axios';
import toast from 'react-hot-toast';
import { Badge } from '../design-system';

const STATUS = {
  suffisant: { tone: 'success',    label: 'Suffisant' },
  critique:  { tone: 'warningAlt', label: 'Critique'  },
  rupture:   { tone: 'danger',     label: 'Rupture'   },
};

export default function MyWarehouseStock() {
  const [warehouse, setWarehouse] = useState(null);
  const [products,  setProducts]  = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [search,    setSearch]    = useState('');

  useEffect(() => { fetchStock(); }, []);

  const fetchStock = async () => {
    setLoading(true);
    try {
      const whRes = await api.get('/stock/warehouses/select-list/');
      const list  = whRes.data.results ?? whRes.data ?? [];
      const mine  = list[0];
      if (!mine) { setWarehouse(null); setProducts([]); return; }
      const stockRes = await api.get(`/stock/warehouses/${mine.id}/current-stock/`);
      setWarehouse(stockRes.data.warehouse);
      setProducts(stockRes.data.products);
    } catch { toast.error('Erreur de chargement du stock'); }
    finally { setLoading(false); }
  };

  const filtered = products.filter(p =>
    !search ||
    p.code.toLowerCase().includes(search.toLowerCase()) ||
    p.designation.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total:    products.length,
    ok:       products.filter(p => p.stock_status === 'suffisant').length,
    critique: products.filter(p => p.stock_status === 'critique').length,
    rupture:  products.filter(p => p.stock_status === 'rupture').length,
  };

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div>
          <h1 style={S.title}>Mon Stock</h1>
          <p style={S.sub}>
            {warehouse ? `${warehouse.name} (${warehouse.code})` : loading ? 'Chargement…' : 'Aucun magasin assigné'}
          </p>
        </div>
      </div>

      {/* KPIs */}
      <div style={S.kpiRow}>
        {[
          { label: 'Références',  v: stats.total,    c: 'var(--accent-light)' },
          { label: 'Suffisant',   v: stats.ok,       c: 'var(--success)' },
          { label: 'Critique',    v: stats.critique, c: 'var(--warning-alt)' },
          { label: 'Rupture',     v: stats.rupture,  c: 'var(--danger)' },
        ].map(k => (
          <div key={k.label} style={S.kpi}>
            <span style={{ ...S.kpiVal, color: k.c }}>{k.v}</span>
            <span style={S.kpiLbl}>{k.label}</span>
          </div>
        ))}
      </div>

      {/* Filtre */}
      <div style={S.filterRow}>
        <input style={S.search} placeholder="Code ou désignation..."
          value={search} onChange={e => setSearch(e.target.value)} />
      </div>

      {/* Tableau */}
      <div style={S.tableBox}>
        <table style={S.table}>
          <thead>
            <tr style={S.thead}>
              {[
                { label: 'Code' },
                { label: 'Désignation' },
                { label: 'Catégorie' },
                { label: 'Unité' },
                { label: 'Stock présent', align: 'right' },
                { label: 'Sécurité',      align: 'right' },
                { label: 'Statut' },
              ].map(c => (
                <th key={c.label} style={{ ...S.th, textAlign: c.align || 'left' }}>{c.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} style={S.empty}>Chargement...</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={7} style={S.empty}>
                {products.length === 0
                  ? "Aucun mouvement de stock n'a encore été enregistré dans ce magasin."
                  : 'Aucun produit ne correspond à votre recherche.'}
              </td></tr>
            ) : filtered.map((p, i) => {
              const st = STATUS[p.stock_status] || STATUS.suffisant;
              return (
                <tr key={p.product_id} style={{ ...S.tr, background: i % 2 ? 'var(--bg-surface-sunken)' : '' }}>
                  <td style={S.td}><span style={S.code}>{p.code}</span></td>
                  <td style={S.td}><div style={S.desig}>{p.designation}</div></td>
                  <td style={S.td}>{p.category_name ? <span style={S.catTag}>{p.category_name}</span> : <span style={S.dash}>—</span>}</td>
                  <td style={S.td}>{p.unit}</td>
                  <td style={{ ...S.td, textAlign: 'right', fontWeight: '700', color: 'var(--text-primary)', fontFamily: 'monospace' }}>
                    {Number(p.stock_actuel).toLocaleString('fr-FR')}
                  </td>
                  <td style={{ ...S.td, textAlign: 'right', color: 'var(--text-faint)', fontFamily: 'monospace' }}>
                    {Number(p.stock_securite).toLocaleString('fr-FR')}
                  </td>
                  <td style={S.td}><Badge tone={st.tone}>{st.label}</Badge></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const S = {
  page:      { color: 'var(--text-secondary)' },
  header:    { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' },
  title:     { fontSize: '1.6rem', fontWeight: '700', color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.4px' },
  sub:       { fontSize: '0.8rem', color: 'var(--text-faint)', marginTop: '0.25rem' },
  kpiRow:    { display: 'flex', gap: '1px', marginBottom: '1.25rem', background: 'var(--border-subtle)', borderRadius: '8px', overflow: 'hidden' },
  kpi:       { flex: 1, padding: '0.875rem 1.25rem', background: 'var(--bg-surface)', display: 'flex', flexDirection: 'column', gap: '0.25rem' },
  kpiVal:    { fontSize: '1.6rem', fontWeight: '800', letterSpacing: '-1px', lineHeight: 1 },
  kpiLbl:    { fontSize: '0.65rem', fontWeight: '700', color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '0.5px' },
  filterRow: { display: 'flex', gap: '0.75rem', marginBottom: '1rem' },
  search:    { flex: 1, padding: '0.65rem 0.875rem', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '7px', fontSize: '0.875rem', color: 'var(--text-secondary)', outline: 'none' },
  tableBox:  { background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '10px', overflow: 'hidden' },
  table:     { width: '100%', borderCollapse: 'collapse' },
  thead:     { background: 'var(--bg-surface-alt)' },
  th:        { padding: '0.625rem 1rem', fontSize: '0.68rem', fontWeight: '700', color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '0.8px', textAlign: 'left' },
  tr:        {},
  td:        { padding: '0.75rem 1rem', fontSize: '0.83rem', color: 'var(--text-tertiary)', borderTop: '1px solid var(--border-faint)', verticalAlign: 'middle' },
  code:      { fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--accent-light)', background: 'var(--accent-bg)', padding: '0.15rem 0.5rem', borderRadius: '4px' },
  desig:     { fontWeight: '600', color: 'var(--text-secondary)' },
  catTag:    { background: 'var(--bg-surface-alt)', color: 'var(--text-faint)', padding: '0.15rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem' },
  dash:      { color: 'var(--border-subtle)' },
  empty:     { padding: '3rem', textAlign: 'center', color: 'var(--text-disabled)', fontSize: '0.875rem' },
};
