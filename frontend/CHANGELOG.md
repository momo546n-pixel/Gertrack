# CHANGELOG — GerTrack

## Version figée après Évolution 7 (2026-07-21)

Cette version couvre les 7 premières évolutions du projet (backend Django REST
+ frontend React). 236/236 tests backend passent ; base de code auditée
(imports/code morts, notifications orphelines, constantes dupliquées,
commentaires obsolètes, permissions redondantes) avant ce gel.

### Évolution 1 — Renommage du rôle RAL
Le rôle "Chef de Stock" devient "Responsable Achat et Logistique" (RAL),
partout dans le backend, le frontend et les libellés utilisateur.

### Évolution 2 — Circuit logistique
Ajout d'un circuit logistique configurable par le RAL (`LogisticsStage`) :
étapes personnalisables par type de demande, avec marquage de l'étape de
réception et de l'étape de clôture, suivi des retards de livraison.

### Évolution 3 — Budget annuel du RAL
`RALBudget` : budget annuel consommé par les achats du RAL réellement
exécutés, avec seuil de blocage automatique et notification du DG.

### Évolution 4 — Budget projet obligatoire
Tout projet doit désormais avoir un budget alloué, immuable après création
(sauf ajustement explicite par le DG).

### Évolution 5 — Demandes d'achat urgentes
Une demande d'achat peut être marquée urgente : notifie simultanément le
DOP et le DG, le premier des deux à statuer décide seul (course DOP/DG).

### Évolution 6 — Blocage automatique du budget projet
Un projet est automatiquement bloqué (plus aucune nouvelle demande) quand
son budget dépasse le seuil ET que l'avancement est en retard sur le
dernier rapport hebdomadaire. Déblocage manuel réservé au DG.

### Évolution 7 — Rôle Responsable Financier
Nouveau rôle dédié à l'exécution financière des achats validés :
- Exécution (`execute_financial`) découplée de la réception magasin —
  deux axes indépendants (`status` vs `logistics_status`).
- Interface minimaliste : dashboard dédié, liste "Demandes à exécuter"
  (tri urgentes-d'abord, badge fort), historique des exécutions.
- Permissions étanches : aucun accès au stock, aux produits, aux magasins,
  aux projets, aux budgets ni aux validations DOP/DG — vérifié côté
  backend (querysets scopés) et frontend (sidebar + garde de route).
- Notifications dédiées, traçabilité (AuditLog) et protection contre la
  double exécution (verrouillage transactionnel).

### Audit final (avant gel)
Vérification transversale des 7 évolutions : suppression de code mort
confirmé (propriété inutilisée, constante dupliquée, endpoint API inutilisé,
types de notification jamais émis), correction de docstrings devenues
fausses après l'Évolution 7, correction d'un risque de régression latent
(codes d'étape logistique figés en dur dans les statistiques fournisseur),
harmonisation UX des badges "Urgent" entre les pages du Responsable
Financier.
