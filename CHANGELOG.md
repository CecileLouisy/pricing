# Changelog

Versions suivent le [versionnage sémantique](https://semver.org/lang/fr/) : `MAJEUR.MINEUR.CORRECTIF`. La version est définie à un seul endroit, `app/__init__.py`.

## 2.0.0 — 27 novembre 2026

Version majeure : `POST /quote` et `GET /quotes/{id}` exigent désormais une authentification, ce qui casse les appelants qui ne l'envoient pas (#14).

### Changements incompatibles
- `POST /quote` exige la clé API du service appelant dans l'en-tête `X-API-Key` (une clé par service : `BOOKING_API_KEY`, `ACCESS_API_KEY`). Sans clé valide : `401 UNAUTHORIZED`.
- `GET /quotes/{id}` exige la clé API d'un service appelant ou le jeton admin (`X-Admin-Token`).
- En production, le service refuse de démarrer si `ADMIN_TOKEN`, `BOOKING_API_KEY` ou `ACCESS_API_KEY` est absent, garde sa valeur par défaut ou fait moins de 16 caractères.

### Ajouté
- `POST /simulate`, public et limité à 30 requêtes/min par IP : même calcul qu'un devis, sans enregistrement. Le simulateur du front l'utilise.
- Service appelant (`caller=booking|access|admin`) dans le log de chaque requête authentifiée.
- Métriques `pricing_simulations_total`, `pricing_api_calls_total{caller}` et `pricing_api_auth_failures_total{reason}`, et deux panneaux dans le tableau de bord Grafana.

### Corrigé
- Un en-tête d'authentification contenant un caractère non ASCII provoquait une erreur 500 ; il est maintenant refusé en 401.

### Migration pour les services appelants
1. Récupérer sa clé auprès de l'équipe Pricing (transmise par un canal privé).
2. L'ajouter dans ses propres variables d'environnement, jamais dans le code.
3. L'envoyer dans l'en-tête `X-API-Key` de chaque appel à `POST /quote` et `GET /quotes/{id}`.

## 1.1.0 — 27 novembre 2026

### Ajouté
- Correlation ID : l'en-tête `X-Correlation-ID` envoyé par Booking ou Access est repris (ou généré s'il est absent), écrit sur chaque ligne de log, renvoyé dans la réponse et enregistré avec le devis (#10).
- Endpoint `GET /metrics` au format Prometheus : requêtes, durées, devis calculés, refus métier, publications de grille (#11).
- Monitoring local Prometheus + Grafana avec un tableau de bord « Pricing » (dossier `monitoring/`) (#12).
- Commit git déployé visible dans `GET /`, dans la métrique `pricing_build_info` et dans le log de démarrage.
- CI : job « Build & smoke test » qui installe et démarre le service comme Render, puis vérifie `/health`, `/` et `/metrics`.
- Publication automatique d'une release GitHub à chaque tag `v*`.

## 1.0.0 — 24 novembre 2026

Première version identifiée.

- Calcul des prix walk-in (quart d'heure entamé, période de gratuité) et réservation (heure pleine) à partir d'une grille tarifaire versionnée ; chaque devis est enregistré avec la grille utilisée.
- Administration des tarifs et de la période de gratuité, protégée par `X-Admin-Token` ; chaque modification publie une nouvelle version de grille.
- Sécurité : rate limiting sur l'administration, en-têtes de sécurité, comparaison du jeton en temps constant, CORS restreint (#1, #4).
- Logs structurés `clé=valeur` (#5).
- Données persistées dans PostgreSQL (Neon) (#6).
- Route `/` d'identification du service (#7).
- Codes de zone alignés sur les catégories du service Parking (#8).
- CI GitHub Actions : lint, tests, audit des dépendances, complexité (#3).
