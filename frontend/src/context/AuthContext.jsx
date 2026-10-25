import { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/axios';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('user');
    if (stored) {
      try {
        const userData = JSON.parse(stored);
        // ── Flags de rôle ──────────────────────────────────────────────
        userData.is_dg              = userData.role === 'dg';
        userData.is_ops_chief       = userData.role === 'chef_ops';
        userData.is_project_manager = userData.role === 'chef_projet';
        userData.is_stock_manager   = userData.role === 'stock';
        userData.is_magasinier      = userData.role === 'magasinier';
        userData.is_financial_officer = userData.role === 'financier';
        setUser(userData);
      } catch { localStorage.clear(); }
    }
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    const res = await api.post('/auth/login/', { username, password });
    const { access, refresh, user: userData } = res.data;

    // ── Flags de rôle ────────────────────────────────────────────────
    userData.is_dg              = userData.role === 'dg';
    userData.is_ops_chief       = userData.role === 'chef_ops';
    userData.is_project_manager = userData.role === 'chef_projet';
    userData.is_stock_manager   = userData.role === 'stock';
    userData.is_magasinier      = userData.role === 'magasinier';
    userData.is_financial_officer = userData.role === 'financier';

    localStorage.setItem('access_token',  access);
    localStorage.setItem('refresh_token', refresh);
    localStorage.setItem('user',          JSON.stringify(userData));

    setUser(userData);
    return userData;
  };

  const logout = async () => {
    // Trace la déconnexion dans le journal d'activité — best-effort : le
    // client se déconnecte localement même si l'appel échoue (token déjà
    // expiré, réseau indisponible, etc.).
    try {
      await api.post('/auth/logout/');
    } catch { /* non bloquant */ }
    localStorage.clear();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);