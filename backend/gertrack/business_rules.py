# ─────────────────────────────────────────────────────────────────────────────
# Règles métier introduites dans cette nouvelle version de GerTrack
# (renommage RAL, circuit logistique configurable, budget annuel RAL...).
#
# Centralisées ici pour que les évolutions suivantes (Responsable Financier,
# budget obligatoire, demandes urgentes, blocage budget projet...) les
# réutilisent sans les redéfinir dans plusieurs fichiers.
#
# Ce module ne doit JAMAIS importer de modèle Django : il est volontairement
# indépendant de toute app pour rester importable de partout sans risque
# d'import circulaire (apps.accounts, apps.requests et apps.notifications y
# font tous référence). Les `choices` Django (listes de tuples affichées
# dans l'admin/les formulaires) restent définies sur leurs modèles respectifs
# — convention déjà suivie par tout le reste du projet — mais leurs VALEURS
# réutilisées dans la logique métier (vues, propriétés de modèles, tests)
# doivent venir d'ici plutôt que d'être ré-écrites en dur à chaque usage.
# ─────────────────────────────────────────────────────────────────────────────

# ── Rôles impliqués dans les nouvelles règles métier ────────────────────────
# Doivent rester synchronisés avec apps.accounts.models.User.ROLE_STOCK /
# ROLE_DG / ROLE_PM / ROLE_MAGASINIER / ROLE_OPS_CHIEF — dupliqués ici en
# simples constantes de valeur (pas des `choices`) car business_rules.py ne
# peut pas importer le modèle User sans provoquer un import circulaire
# (apps.accounts.models importe ce module pour AUDIT_ACTION_DENIED).
ROLE_RAL        = 'stock'
ROLE_DG         = 'dg'
ROLE_PM         = 'chef_projet'
ROLE_MAGASINIER = 'magasinier'
ROLE_DOP        = 'chef_ops'
ROLE_FINANCIAL  = 'financier'

# ── Budget annuel du RAL (Évolution 3) ───────────────────────────────────────
# À partir de ce seuil, toute nouvelle demande d'achat du RAL est bloquée
# (voir apps.requests.models.RALBudget.is_threshold_reached) tant que le DG
# n'augmente pas le budget ou ne débloque pas le compte manuellement.
RAL_BUDGET_BLOCK_THRESHOLD_PERCENT = 85

# Seul ce type de demande est concerné par le budget annuel du RAL.
RAL_BUDGET_REQUEST_TYPE = 'achat'

# ── Statuts particuliers d'une UnifiedRequest ───────────────────────────────
# Une demande dans l'un de ces statuts a déjà été définitivement traitée
# (validée, refusée ou exécutée) — retenter une action d'exécution dessus
# (validate_dg) est une double exécution à rejeter, pas un état normal.
REQUEST_FINAL_STATUSES = ('validee', 'refusee', 'executee')

# Statuts à partir desquels le circuit logistique peut démarrer (Évolution 7) :
# uniquement 'executee' désormais — une demande d'achat validée mais pas
# encore exécutée par le Responsable Financier ne doit jamais pouvoir entrer
# dans le circuit logistique. Sans impact pour entrée/sortie/ajustement :
# elles atteignent déjà 'executee' immédiatement à la validation (voir
# UnifiedRequest._act_on_urgent/validate_dg), donc jamais observables à
# 'validee' au moment où ce contrôle s'applique.
REQUEST_STATUSES_ELIGIBLE_FOR_LOGISTICS = ('executee',)

# Statut marquant une demande comme réellement EXÉCUTÉE. C'est uniquement à
# partir de ce statut que le budget (RAL ou projet) est consommé — jamais à
# la simple validation (voir RALBudget.montant_consomme,
# Project.budget_consomme). Pour un achat (Évolution 7), ce statut est posé
# par le Responsable Financier (UnifiedRequest.execute_financial) — AVANT le
# circuit logistique, jamais à la réception magasin (qui reste un événement
# séparé, indépendant, déclenchant uniquement les mouvements de stock).
REQUEST_STATUS_EXECUTED = 'executee'

# ── Demandes d'achat urgentes (Évolution 5) ─────────────────────────────────
# Circuit de course DOP/DG : le premier des deux qui agit (valide OU refuse)
# décide seul du sort de la demande — l'action de l'autre devient caduque
# (voir UnifiedRequest._act_on_urgent). Une seule validation suffit donc,
# contrairement au circuit séquentiel 'dop_then_dg'.
VALIDATION_TYPE_URGENT = 'urgent_dop_ou_dg'

# Statut d'attente conjointe DOP/DG propre à ce circuit — distinct de
# 'en_attente_dop'/'en_attente_dg' (circuits où un seul rôle précis est
# attendu à la fois) pour ne jamais les confondre dans les filtres/tableaux
# de bord existants.
REQUEST_STATUS_AWAITING_DOP_OR_DG = 'en_attente_dop_dg'

# Seuls ces rôles peuvent créer une demande d'achat urgente — elle doit
# obligatoirement être liée à un projet (voir UnifiedRequestViewSet.
# _enforce_role_constraints). Le budget annuel RAL (Évolution 4) ne
# s'applique qu'aux demandes du RAL lui-même : une urgente d'un Chef de
# Projet/Magasinier est financée par le budget du PROJET, jamais par le
# budget annuel RAL (RALBudget.montant_consomme ne compte de toute façon que
# les demandes dont l'auteur a le rôle RAL).
URGENT_ACHAT_ALLOWED_ROLES = (ROLE_PM, ROLE_MAGASINIER, ROLE_RAL)

# ── Blocage automatique du budget projet (Évolution 6) ──────────────────────
# Distinct de RAL_BUDGET_BLOCK_THRESHOLD_PERCENT : concept différent (budget
# d'un projet, pas budget annuel RAL) — valeur par défaut identique mais
# réglable indépendamment.
PROJECT_BUDGET_BLOCK_THRESHOLD_PERCENT = 85

# ── Responsable Financier (Évolution 7) ─────────────────────────────────────
# Ce rôle exécute exclusivement les demandes d'achat validées, en attente
# d'exécution financière — jamais le suivi logistique, les commandes en
# retard/reçues, ni les entrées/sorties/ajustements (voir
# UnifiedRequestViewSet.get_queryset).
NOTIF_TYPE_A_EXECUTER_FINANCIER   = 'a_executer_financier'
NOTIF_TYPE_EXECUTEE_FINANCIEREMENT = 'demande_executee_financiere'

# ── Notifications introduites dans cette version ────────────────────────────
NOTIF_TYPE_BUDGET_RAL_SEUIL = 'budget_ral_seuil'
NOTIF_TYPE_PROJECT_BUDGET_BLOQUE = 'project_budget_bloque'

# ── Audit : action distincte pour les tentatives bloquées par une garde
# technique (double exécution, étape déjà atteinte) — à ne jamais confondre
# avec un refus métier (décision humaine, voir AuditLog.ACTION_REFUSE).
AUDIT_ACTION_DENIED = 'DENIED'

# ── Traçabilité avant/après (Évolution 8) ───────────────────────────────────
# Liste FERMÉE et volontairement courte des champs métier sensibles suivis
# avec old_value/new_value structurés (voir AuditLog.field_name/old_value/
# new_value) — PAS un mécanisme générique "tout changement de tout champ".
# Source unique : toute vue qui enrichit un AuditLog avec field_name doit
# utiliser une des clés ci-dessous plutôt que d'inventer sa propre chaîne.
#
# ('Warehouse', 'manager') / ('Warehouse', 'manager_username') : le flux
# prévu (WarehouseViewSet.perform_create) crée toujours un magasin avec son
# propre compte gérant dédié et ne prévoit pas de réaffectation ultérieure —
# mais WarehouseSerializer expose `manager` en champ écrivable standard (pas
# encore marqué read_only), donc une réaffectation reste possible via l'API
# générique (PATCH direct). Les deux transitions sont donc suivies : le
# changement d'identifiant de connexion du même gérant (cas prévu), et une
# éventuelle réaffectation du FK lui-même (cas possible mais non prévu par
# l'UI — revoir cette permission est hors périmètre de l'Évolution 8, qui se
# limite à observer/tracer, pas à revalider les permissions existantes).
AUDIT_TRACKED_FIELDS = {
    ('Project', 'budget'):             'Budget',
    ('Project', 'project_manager'):    'Chef de projet',
    ('Warehouse', 'manager'):          'Gérant du magasin',
    ('Warehouse', 'manager_username'): 'Identifiant du gérant',
    ('UnifiedRequest', 'is_urgent'):   'Priorité (urgent)',
    ('RALBudget', 'montant_annuel'):   'Budget annuel RAL',
}
