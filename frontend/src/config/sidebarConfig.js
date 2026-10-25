// ─────────────────────────────────────────────────────────────────────────────
// Configuration centralisée de la navigation par rôle.
// Chaque menu est une liste de sections { section, items[] } — les icônes
// (clé `icon`) sont résolues via le dictionnaire ICONS de Layout.jsx.
//
// Seules les routes réellement existantes (voir App.js) sont référencées :
// aucune page n'est inventée pour coller à une catégorie.
// ─────────────────────────────────────────────────────────────────────────────

// ── DG (Directeur Général) — vision complète de l'entreprise ───────────────
export const ADMIN_MENU = [
  {
    section: 'Tableau de bord',
    items: [
      { path: '/dashboard', icon: 'dashboard', label: "Vue d'ensemble" },
    ],
  },
  {
    section: 'Opérations',
    items: [
      { path: '/operations-dashboard', icon: 'ops_dashboard', label: 'Suivi Projets' },
      { path: '/operations',           icon: 'operations',    label: 'Projets'       },
    ],
  },
  {
    section: 'Stocks',
    items: [
      { path: '/products',   icon: 'products',   label: 'Produits' },
      { path: '/warehouses', icon: 'warehouses', label: 'Magasins' },
    ],
  },
  {
    section: 'Achats & Demandes',
    items: [
      { path: '/requests',  icon: 'requests',  label: 'Demandes'     },
      { path: '/suppliers', icon: 'suppliers', label: 'Fournisseurs' },
    ],
  },
  {
    section: 'Budget',
    items: [
      { path: '/ral-budget', icon: 'budget', label: 'Budget RAL' },
    ],
  },
  {
    section: 'Équipe',
    items: [
      { path: '/project-managers', icon: 'chefsprojet', label: 'Chefs de Projet' },
    ],
  },
  {
    section: 'Administration',
    items: [
      { path: '/administration', icon: 'administration', label: 'Comptes'         },
      { path: '/audit',          icon: 'audit',          label: "Centre d'audit" },
    ],
  },
];

// ── Responsable Achat et Logistique (RAL) ───────────────────────────────────
export const RAL_MENU = [
  {
    section: 'Tableau de bord',
    items: [
      { path: '/dashboard', icon: 'dashboard', label: 'Tableau de bord' },
    ],
  },
  {
    section: 'Stocks',
    items: [
      { path: '/products',   icon: 'products',   label: 'Produits' },
      { path: '/warehouses', icon: 'warehouses', label: 'Magasins' },
    ],
  },
  {
    section: 'Achats & Demandes',
    items: [
      { path: '/validations', icon: 'validation', label: 'Demandes à valider' },
      { path: '/requests',    icon: 'requests',    label: 'Mes Demandes'      },
      { path: '/suppliers',   icon: 'suppliers',   label: 'Fournisseurs'      },
    ],
  },
  {
    section: 'Budget',
    items: [
      { path: '/ral-budget', icon: 'budget', label: 'Mon Budget Annuel' },
    ],
  },
  {
    section: 'Logistique',
    items: [
      { path: '/logistics-circuit', icon: 'circuit', label: 'Circuit Logistique' },
    ],
  },
  {
    section: 'Traçabilité',
    items: [
      { path: '/audit', icon: 'audit', label: "Centre d'audit" },
    ],
  },
];

// ── DOP — Directrice des Opérations (anciennement "Chef des Opérations") ──
export const DOP_MENU = [
  {
    section: 'Tableau de bord',
    items: [
      { path: '/dashboard',            icon: 'dashboard',     label: 'Tableau de bord' },
      { path: '/operations-dashboard', icon: 'ops_dashboard', label: 'Suivi Projets'   },
    ],
  },
  {
    section: 'Projets',
    items: [
      { path: '/operations', icon: 'operations', label: 'Tous les projets' },
    ],
  },
  {
    section: 'Équipe',
    items: [
      { path: '/project-managers', icon: 'chefsprojet', label: 'Chefs de Projet' },
    ],
  },
  {
    section: 'Demandes',
    items: [
      { path: '/requests', icon: 'requests', label: 'Demandes' },
    ],
  },
  {
    section: 'Traçabilité',
    items: [
      { path: '/audit', icon: 'audit', label: "Centre d'audit" },
    ],
  },
];

// ── Chef de Projet ───────────────────────────────────────────────────────────
export const PROJECT_MANAGER_MENU = [
  {
    section: 'Tableau de bord',
    items: [
      { path: '/dashboard', icon: 'dashboard', label: 'Tableau de bord' },
    ],
  },
  {
    section: 'Mon Projet',
    items: [
      { path: '/operations', icon: 'operations', label: 'Mes Projets' },
    ],
  },
  {
    section: 'Stock & Achats',
    items: [
      { path: '/requests', icon: 'requests', label: 'Mes Demandes' },
    ],
  },
  {
    section: 'Traçabilité',
    items: [
      { path: '/audit', icon: 'audit', label: "Centre d'audit" },
    ],
  },
];

// ── Responsable Financier (Évolution 7) — interface volontairement minimale :
// exécute exclusivement les demandes d'achat validées, ne voit jamais le
// circuit logistique, les commandes reçues/en retard, ni les autres types
// de demandes (voir UnifiedRequestViewSet.get_queryset).
export const FINANCIAL_MENU = [
  {
    section: 'Tableau de bord',
    items: [
      { path: '/dashboard', icon: 'dashboard', label: 'Tableau de bord' },
    ],
  },
  {
    section: 'Exécution',
    items: [
      { path: '/financial-execution', icon: 'validation', label: 'Demandes à exécuter'    },
      { path: '/financial-history',   icon: 'audit',       label: 'Historique des exécutions' },
    ],
  },
  {
    section: 'Traçabilité',
    items: [
      { path: '/audit', icon: 'audit', label: "Centre d'audit" },
    ],
  },
];

// ── Compte Magasin (magasinier) ─────────────────────────────────────────────
export const STORE_MENU = [
  {
    section: 'Tableau de bord',
    items: [
      { path: '/dashboard', icon: 'dashboard', label: 'Tableau de bord' },
    ],
  },
  {
    section: 'Stock',
    items: [
      { path: '/my-stock', icon: 'stock', label: 'Mon Stock' },
    ],
  },
  {
    section: 'Demandes',
    items: [
      { path: '/requests', icon: 'requests', label: 'Mes Demandes' },
    ],
  },
  {
    section: 'Traçabilité',
    items: [
      { path: '/audit', icon: 'audit', label: "Centre d'audit" },
    ],
  },
];

// ── Sélecteur de menu par rôle ───────────────────────────────────────────────
export function sidebarConfigByRole(user) {
  if (!user) return RAL_MENU;
  if (user.is_dg)              return ADMIN_MENU;
  if (user.is_ops_chief)       return DOP_MENU;
  if (user.is_project_manager) return PROJECT_MANAGER_MENU;
  if (user.role === 'magasinier') return STORE_MENU;
  if (user.role === 'financier')  return FINANCIAL_MENU;
  return RAL_MENU;
}

// ── Chemins accessibles par rôle ─────────────────────────────────────────────
// Dérivés du menu affiché : une page absente du menu d'un rôle n'est pas non
// plus accessible par URL directe (voir App.js, MenuRoute).
export function getAllowedPaths(user) {
  return sidebarConfigByRole(user).flatMap(section => section.items.map(item => item.path));
}
