import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { getAllowedPaths } from './config/sidebarConfig';
import Layout       from './components/Layout';
import Login        from './pages/Login';
import Dashboard    from './pages/Dashboard';
import Products     from './pages/Products';
import Suppliers    from './pages/Suppliers';
import Audit        from './pages/Audit';
import Projects      from './pages/operations/Projects';
import ProjectDetail from './pages/operations/ProjectDetail';
import WeeklyReport  from './pages/operations/WeeklyReport';
import OpsDashboard  from './pages/operations/OpsDashboard';
import Warehouses from './pages/Warehouses';
import Requests from './pages/Requests';
import MyWarehouseStock from './pages/MyWarehouseStock';
import LogisticsCircuit from './pages/LogisticsCircuit';
import RALBudget from './pages/RALBudget';
import FinancialExecution from './pages/FinancialExecution';
import FinancialHistory from './pages/FinancialHistory';
import ProjectManagers from './pages/ProjectManagers';
import Administration from './pages/Administration';
// Une page absente du menu latéral d'un rôle (voir sidebarConfig.js) ne doit
// pas non plus être accessible en tapant directement son URL — sinon retirer
// un lien du menu ne fait que le cacher, pas le protéger.
function isPathAllowed(pathname, user) {
  if (pathname === '/dashboard') return true;
  return getAllowedPaths(user).some(p => pathname === p || pathname.startsWith(p + '/'));
}

function PrivateRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return (
    <div style={{
      display:'flex', alignItems:'center', justifyContent:'center',
      height:'100vh', background:'var(--bg-page)',
      fontFamily:'var(--font-sans)', color:'var(--text-faint)', fontSize:'0.9rem',
    }}>
      Chargement...
    </div>
  );
  if (!user) return <Navigate to="/login" />;
  if (!isPathAllowed(location.pathname, user)) return <Navigate to="/dashboard" />;
  return <Layout>{children}</Layout>;
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? <Navigate to="/dashboard" /> : children;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />

      {/* Commun */}
      <Route path="/dashboard"   element={<PrivateRoute><Dashboard /></PrivateRoute>} />
      <Route path="/products"    element={<PrivateRoute><Products /></PrivateRoute>} />
      <Route path="/suppliers"   element={<PrivateRoute><Suppliers /></PrivateRoute>} />
      <Route path="/warehouses"  element={<PrivateRoute><Warehouses /></PrivateRoute>} />
      <Route path="/requests" element={<PrivateRoute><Requests /></PrivateRoute>} />
      <Route path="/validations" element={<PrivateRoute><Requests validationMode /></PrivateRoute>} />
      <Route path="/my-stock" element={<PrivateRoute><MyWarehouseStock /></PrivateRoute>} />
      <Route path="/logistics-circuit" element={<PrivateRoute><LogisticsCircuit /></PrivateRoute>} />
      <Route path="/ral-budget" element={<PrivateRoute><RALBudget /></PrivateRoute>} />
      <Route path="/financial-execution" element={<PrivateRoute><FinancialExecution /></PrivateRoute>} />
      <Route path="/financial-history" element={<PrivateRoute><FinancialHistory /></PrivateRoute>} />
      <Route path="/project-managers" element={<PrivateRoute><ProjectManagers /></PrivateRoute>} />

      {/* Centre d'audit (Évolution 8) — accessible à tous les rôles listés
          dans leur propre menu ; le périmètre affiché (tout pour le DG,
          uniquement son propre scope pour les autres) est décidé côté
          backend (voir apps.accounts.views._audit_center_queryset), pas ici. */}
      <Route path="/audit" element={<PrivateRoute><Audit /></PrivateRoute>} />

      {/* DG uniquement — restriction assurée par ADMIN_MENU (voir isPathAllowed) */}
      <Route path="/administration" element={<PrivateRoute><Administration /></PrivateRoute>} />

      {/* Module Opérations */}
      <Route path="/operations"            element={<PrivateRoute><Projects /></PrivateRoute>} />
      <Route path="/operations/:id"        element={<PrivateRoute><ProjectDetail /></PrivateRoute>} />
      <Route path="/operations/:id/report" element={<PrivateRoute><WeeklyReport /></PrivateRoute>} />
      <Route path="/operations-dashboard"  element={<PrivateRoute><OpsDashboard /></PrivateRoute>} />

      {/* Redirections — toujours EN DERNIER */}
      <Route path="/" element={<Navigate to="/dashboard" />} />
      <Route path="*" element={<Navigate to="/dashboard" />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 3500,
              style: {
                fontFamily: 'var(--font-sans)',
                fontSize: '0.875rem',
                background: 'var(--bg-surface)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                boxShadow: 'var(--shadow-lg)',
              },
            }}
          />
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}