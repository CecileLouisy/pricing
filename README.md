# Pricing — Parking Management

Micro-service de tarification pour le projet fil rouge de gestion de parking.

Répond à la question : *combien coûte le stationnement d'un véhicule dans une zone donnée pour une durée donnée ?*

Chaque calcul est relié à une version précise de la grille tarifaire (traçabilité garantie même après modification des tarifs).

## Architecture

Architecture hexagonale allégée, trois couches concentriques :

```
adapters/  (api HTTP, db SQLAlchemy)
    ↓
application/  (use cases + ports)
    ↓
domain/  (règles pures, zéro dépendance framework)
```

Le domaine ne dépend de rien. Les adapters implémentent les ports définis dans `application/ports.py`. Cela permet de tester la logique métier sans DB ni HTTP, et de remplacer SQLite par Postgres ou FastAPI par un CLI sans toucher au cœur.

## Stack

- Python 3.11
- FastAPI (HTTP + OpenAPI auto)
- SQLAlchemy 2.0 (ORM)
- PostgreSQL hébergé sur [Neon](https://neon.com) en production (driver psycopg 3), SQLite en développement local et pour les tests
- Pydantic v2 (validation)
- prometheus-client (métriques `/metrics`)
- pytest + httpx (tests)
- ruff (linter + formatter)
- pip-audit (audit de sécurité des dépendances)
- radon (complexité cyclomatique)

## Démarrage local

```bash
# 1. Créer et activer un venv
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows PowerShell

# 2. Installer les dépendances
pip install -e ".[dev]"

# 3. Copier la config
cp .env.example .env

# 4. Lancer le serveur
uvicorn app.main:app --reload
```

Le service écoute sur http://localhost:8000.

- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc
- **OpenAPI JSON** : http://localhost:8000/openapi.json
- **Health** : http://localhost:8000/health
- **Racine** : http://localhost:8000/ (nom du service, version, liens vers `/docs` et `/health`)

Au premier démarrage, la base est créée et pré-remplie avec une grille tarifaire initiale (5 zones × 2 modes + gratuité de 60 min).

## Tests & Qualité

```bash
pytest                            # tests unitaires + intégration
ruff check app/ tests/            # linter (analyse statique)
ruff format --check app/ tests/   # vérification du formatage
pip-audit --skip-editable         # audit de sécurité des dépendances
radon cc app/ -a -nc              # complexité cyclomatique (fail si > C)
```

Ces vérifications sont aussi exécutées automatiquement par GitHub Actions à chaque push et PR sur master, ainsi qu'un job « Build & smoke test » : il installe le service avec la même commande que Render, le démarre et vérifie que `/health`, `/` (avec la bonne version) et `/metrics` répondent.

## Exemples d'appels

Simulation publique d'un prix (rien n'est enregistré) :
```bash
curl -X POST http://localhost:8000/simulate      -H "Content-Type: application/json"      -d '{"zone":"standard","mode":"walk_in","duration_min":75}'
```

Devis d'un service appelant (Booking ou Access, avec sa clé API) :
```bash
curl -X POST http://localhost:8000/quote      -H "Content-Type: application/json"      -H "X-API-Key: <clé du service>"      -H "X-Correlation-ID: booking-42"      -d '{"zone":"standard","mode":"walk_in","duration_min":75}'
```

Relecture d'un devis (clé API ou jeton admin) :
```bash
curl http://localhost:8000/quotes/{quote_id} -H "X-API-Key: <clé du service>"
```

Modification d'un tarif (admin) :
```bash
curl -X PATCH http://localhost:8000/rates/standard/walk_in      -H "Content-Type: application/json"      -H "X-Admin-Token: <jeton admin>"      -d '{"hourly_rate_eur":"3.50"}'
```

## Sécurité

### Qui peut appeler quoi

| Endpoints | Accès | Pourquoi |
|---|---|---|
| `/`, `/health`, `/metrics` | Public | Supervision : Render, Prometheus. Aucune donnée personnelle ni secret |
| `GET /rates`, `/rates/{zone}`, `/grids`, `/grids/current`, `/grids/{id}`, `GET /settings/free-period` | Public | Affichage des tarifs (front, panneau du parking) |
| `POST /simulate` | Public, limité à 30 requêtes/min par IP | Simulateur du front : même calcul qu'un devis, **rien n'est enregistré** |
| `POST /quote` | **Clé API** (`X-API-Key`) de Booking ou d'Access | Un devis est une donnée métier enregistrée : seuls les services appelants en créent |
| `GET /quotes/{id}` | **Clé API** ou **jeton admin** (`X-Admin-Token`) | Relecture par le service appelant ou par la console admin |
| `PATCH /rates/...`, `POST /rates`, `PATCH /settings/free-period` | **Jeton admin**, limité à 10 requêtes/min par IP | Modification des tarifs |

**Une clé par service** (`BOOKING_API_KEY`, `ACCESS_API_KEY`) : les logs (`caller=booking`) et la métrique `pricing_api_calls_total{caller}` indiquent qui appelle, et une clé compromise peut être changée sans toucher à l'autre service. Les clés sont générées par Render et transmises à chaque équipe par un canal privé ; elles ne sont jamais dans le code ni dans git.

Un appel refusé renvoie `401 {"detail": {"code": "UNAUTHORIZED", "message": "Missing or invalid X-API-Key"}}` et écrit `event=api_auth_failed reason=missing_key|invalid_key` dans les logs, sans jamais la clé reçue.

### Mesures

| Couche | Mesure |
|---|---|
| Authentification | Clé API par service appelant, jeton admin pour l'administration, comparaison en temps constant (`hmac.compare_digest`, sur des octets : un en-tête non ASCII est refusé proprement) |
| Secrets au démarrage | En production (`ENV=production`), le service **refuse de démarrer** si `ADMIN_TOKEN`, `BOOKING_API_KEY` ou `ACCESS_API_KEY` est absent, laissé à sa valeur par défaut ou fait moins de 16 caractères (log `event=startup_refused`, avec les noms des variables seulement) |
| Rate limiting | 10 requêtes/min par IP sur l'administration, 30 sur la simulation publique |
| Validation | Entrées validées par Pydantic puis par le domaine, anti-injection SQL par SQLAlchemy |
| Erreurs | Format fixe `{code, message}` ; erreur inattendue : 500 générique, détails uniquement dans les logs |
| Headers HTTP | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy` |
| CORS | Restreint au domaine GitHub Pages (configurable via env var) |
| Secrets | Variables d'environnement uniquement, jamais dans le code ni dans les logs |

## Logs

Une ligne par événement sur stdout, au format `clé=valeur` (lisible dans les logs Render et facile à filtrer). Niveau réglable via la variable d'environnement `LOG_LEVEL` (défaut `INFO`).

| Logger | Événement | Niveau | Contenu |
|---|---|---|---|
| `pricing` | `startup` / `shutdown` | INFO | version, environnement |
| `pricing.http` | `http_request` | INFO (2xx/3xx), WARNING (4xx), ERROR (5xx) | méthode, route, statut, durée en ms, service appelant (`caller`) |
| `pricing.business` | `quote_computed` | INFO | quote_id, version de grille, zone, mode, durée, montant |
| `pricing.business` | `grid_published` | INFO | type de changement, nouvelle et ancienne version, valeur modifiée |
| `pricing.errors` | `domain_error` | WARNING | code d'erreur métier, route |
| `pricing.errors` | `unexpected_error` | ERROR | stack trace complète (le client reçoit seulement un message générique) |
| `pricing.business` | `price_simulated` | INFO | version de grille, zone, mode, durée, montant (simulation non enregistrée) |
| `pricing.security` | `api_auth_failed` | WARNING | raison (`missing_key` / `invalid_key`), route — **la clé n'est jamais loggée** |
| `pricing` | `startup_refused` | CRITICAL | noms des secrets manquants ou trop faibles en production |
| `pricing.security` | `admin_auth_failed` | WARNING | raison (`missing_token` / `invalid_token`), route — **le jeton n'est jamais loggé** |
| `pricing.http` | `invalid_correlation_id` | WARNING | longueur de la valeur reçue (la valeur elle-même n'est pas loggée) |
| `pricing.db` | `schema_upgraded` | INFO | table et colonne ajoutées au démarrage |

Exemple :

```
2026-11-25 14:21:37,902 level=INFO logger=pricing.business correlation_id=booking-42 event=quote_computed quote_id=01a212de-... grid_version=1 zone=handicapped mode=walk_in duration_min=120 amount_eur=1.50
2026-11-25 14:21:37,904 level=INFO logger=pricing.http correlation_id=booking-42 event=http_request method=POST path=/quote status=201 duration_ms=11.6
```

### Correlation ID

Chaque ligne de log porte un `correlation_id`, qui permet de suivre une même opération à travers plusieurs services (Booking ou Access → Pricing).

- Pricing **reprend** l'en-tête `X-Correlation-ID` envoyé par l'appelant (Booking, Access). Le nom de l'en-tête n'est pas sensible à la casse.
- S'il est absent (front, Swagger, curl), Pricing en **génère** un (UUID).
- S'il est invalide (vide, plus de 128 caractères, ou caractères autres que lettres, chiffres, `-` et `_`), il est remplacé par un UUID généré et un warning `invalid_correlation_id` est loggé. La requête n'est pas rejetée.
- L'identifiant est **renvoyé** dans l'en-tête `X-Correlation-ID` de la réponse, y compris en cas d'erreur, et exposé par CORS pour que le front puisse le lire.
- Il est **enregistré avec le devis** (`correlation_id` dans la réponse de `POST /quote` et de `GET /quotes/{id}`). Les devis antérieurs ont `null`.
- Hors requête (démarrage, arrêt), il vaut `-`.
- Pricing n'appelle aucun autre service : il n'a rien à propager plus loin.

C'est un identifiant technique opaque : il ne doit contenir aucune donnée personnelle (plaque, e-mail…).

```bash
curl -i -X POST https://pricing-9khk.onrender.com/quote \
     -H "Content-Type: application/json" \
     -H "X-Correlation-ID: booking-42" \
     -d '{"zone":"standard","mode":"walk_in","duration_min":75}'
```

## Métriques (`/metrics`)

`GET /metrics` expose les métriques au format texte Prometheus (bibliothèque officielle `prometheus-client`).

| Métrique | Type | Labels | Signification |
|---|---|---|---|
| `pricing_http_requests_total` | counter | `method`, `route`, `status` | Requêtes HTTP traitées. Les erreurs se lisent avec `status` (4xx, 5xx) |
| `pricing_http_request_duration_seconds` | histogram | `method`, `route` | Durée des requêtes |
| `pricing_build_info` | info | `version` | Version déployée |
| `pricing_quotes_computed_total` | counter | `zone`, `mode` | Devis calculés |
| `pricing_quote_amount_eur` | histogram | `mode` | Montants des devis calculés |
| `pricing_domain_errors_total` | counter | `code` | Requêtes refusées par une règle métier (`ZONE_NOT_FOUND`, `INVALID_DURATION`…) |
| `pricing_grid_publications_total` | counter | `change` | Nouvelles versions de grille, par type de changement |
| `pricing_active_grid_version` | gauge | — | Version de la grille en vigueur |
| `pricing_admin_auth_failures_total` | counter | `reason` | Appels admin refusés |
| `pricing_simulations_total` | counter | `zone`, `mode` | Simulations publiques (non enregistrées) |
| `pricing_api_calls_total` | counter | `caller` | Appels authentifiés par clé API, par service (booking, access) |
| `pricing_api_auth_failures_total` | counter | `reason` | Appels refusés faute de clé API valide |

S'y ajoutent les métriques du processus fournies par la bibliothèque (`process_*`, `python_*` : mémoire, CPU, GC).

Choix de conception :
- le label `route` contient le **modèle de route** (`/quotes/{quote_id}`), jamais le chemin brut ; une URL inconnue est comptée sous `unmatched`. Sinon, chaque identifiant de devis ou chaque URL testée par un scanner créerait une nouvelle série ;
- les valeurs sont **en mémoire** et repartent de zéro au redémarrage, ce que Prometheus gère nativement pour les compteurs ;
- `/metrics` **n'interroge pas la base** : un scraping toutes les 15 s n'empêche donc pas Neon de se mettre en veille ;
- les appels à `/metrics` sont loggés en DEBUG, pour ne pas noyer les logs d'une ligne toutes les 15 s ;
- `/metrics` est public, comme `/health` : il ne contient aucune donnée personnelle ni aucun secret.

Un Prometheus et un Grafana locaux, avec un tableau de bord prêt à l'emploi, sont fournis dans [`monitoring/`](monitoring/README.md) (`docker compose up -d`, puis http://localhost:3000).

Exemples de requêtes PromQL :

```promql
# Devis calculés par minute, par zone
sum by (zone) (rate(pricing_quotes_computed_total[5m])) * 60

# Taux de réponses en erreur serveur
sum(rate(pricing_http_requests_total{status=~"5.."}[5m])) / sum(rate(pricing_http_requests_total[5m]))

# Durée de réponse au 95e percentile de POST /quote
histogram_quantile(0.95, sum by (le) (rate(pricing_http_request_duration_seconds_bucket{route="/quote"}[5m])))
```

## Base de données (Neon)

Le disque d'un service Render gratuit est éphémère : une base SQLite y serait remise à zéro à chaque redémarrage. En production, les données sont donc stockées dans une base **PostgreSQL hébergée sur Neon**, ce qui conserve grilles et devis entre les déploiements.

1. Créer un projet sur [neon.com](https://neon.com), de préférence dans la même région que le service Render.
2. Copier la chaîne de connexion (*Connect* → connexion directe, sans `-pooler`), de la forme `postgresql://user:password@ep-xxx.<region>.aws.neon.tech/neondb?sslmode=require`.
3. La coller dans la variable d'environnement `DATABASE_URL` du service Render.

Le préfixe `postgresql://` est converti automatiquement vers le driver psycopg 3 (`app/config.py`). Au premier démarrage, les tables sont créées et la grille initiale est insérée ; les démarrages suivants réutilisent les données existantes.

`create_all` ne modifie jamais une table existante. Les colonnes ajoutées après le premier déploiement (aujourd'hui `quote.correlation_id`) sont listées dans `_ADDED_COLUMNS` (`app/adapters/db/engine.py`) et ajoutées automatiquement au démarrage si elles manquent (`ALTER TABLE ... ADD COLUMN`). Pour des évolutions de schéma plus importantes, un outil de migration comme Alembic serait préférable.

## Déploiement Render

Le fichier `render.yaml` déclare le service. Sur Render :
1. Nouveau *Web Service* → connecter le repo GitHub → détection auto de `render.yaml`.
2. Renseigner `DATABASE_URL` (chaîne de connexion Neon, voir ci-dessus).
3. Deploy.
4. `ADMIN_TOKEN`, `BOOKING_API_KEY` et `ACCESS_API_KEY` sont générés automatiquement (visibles dans les env vars du dashboard Render). Sur un service existant, les ajouter à la main (bouton *Generate*) **avant** de déployer une version qui les exige : sinon le service refuse de démarrer et Render garde la version précédente en ligne.

Ensuite, chaque merge sur `master` est déployé automatiquement (Auto-Deploy « On Commit », qui nécessite l'application GitHub Render installée sur le compte avec accès au dépôt).

### Procédure de livraison

1. Travailler sur une branche, ouvrir une PR vers `master`.
2. La CI doit passer : lint, format, tests, audit des dépendances, complexité, build & smoke test. `master` est protégée : impossible de merger sinon.
3. Merger la PR : Render redéploie automatiquement.
4. Vérifier le déploiement : `GET /` affiche la version et le commit déployés (les 7 premiers caractères du SHA, fournis par Render dans `RENDER_GIT_COMMIT`), qui doivent correspondre au dernier commit de `master`.

### Publier une version

1. Sur une branche, augmenter la version dans `app/__init__.py` (seul endroit où elle est définie) et compléter `CHANGELOG.md` ; merger.
2. Tagger le commit mergé sur `master` et pousser le tag :
   ```bash
   git checkout master && git pull
   git tag v2.0.0
   git push origin v2.0.0
   ```
3. Le workflow `release.yml` vérifie que le tag correspond à la version du code, puis publie la release GitHub avec les notes générées depuis les PR.

La version et le commit en production se lisent sur `GET /`, dans la métrique `pricing_build_info` et dans le log `event=startup`.

## Périmètre

Voir la spec complète dans le Google Doc partagé avec le groupe.

Résumé :
- Grille tarifaire versionnée, chaque devis référence sa grille.
- 5 zones alignées sur les catégories du service Parking (`standard`, `handicapped`, `electric`, `xl`, `two_wheels`) × 2 modes (`reserved`, `walk_in`).
- Codes de zone insensibles à la casse : `HANDICAPPED` (format Parking) et `handicapped` sont équivalents.
- Si Parking renomme une catégorie, ajouter `"ancien": "nouveau"` dans `ZONE_RENAMES` (`app/domain/value_objects.py`) : au démarrage suivant, une nouvelle version de grille est publiée avec le nouveau code, les grilles et devis passés gardent l'ancien.
- Walk-in facturé au quart d'heure entamé, gratuité initiale de 60 min.
- Réservation facturée à l'heure pleine, pas de gratuité.
- Durée max 7 jours.
- Devise unique : EUR.
