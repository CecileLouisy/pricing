# Changelog

Versions suivent le [versionnage sémantique](https://semver.org/lang/fr/) : `MAJEUR.MINEUR.CORRECTIF`. La version est définie à un seul endroit, `app/__init__.py`.

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
