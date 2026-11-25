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

Ces vérifications sont aussi exécutées automatiquement par GitHub Actions à chaque push et PR sur master.

## Exemples d'appels

Calcul d'un prix walk-in :
```bash
curl -X POST http://localhost:8000/quote \
     -H "Content-Type: application/json" \
     -d '{"zone":"standard","mode":"walk_in","duration_min":75}'
```

Modification d'un tarif (admin) :
```bash
curl -X PATCH http://localhost:8000/rates/standard/walk_in \
     -H "Content-Type: application/json" \
     -H "X-Admin-Token: change-me-in-production" \
     -d '{"hourly_rate_eur":"3.50"}'
```

Historique d'un devis :
```bash
curl http://localhost:8000/quotes/{quote_id}
```

## Sécurité

| Couche | Mesure |
|---|---|
| Authentification | Écritures admin protégées par header `X-Admin-Token` (env var), comparaison en temps constant (`hmac.compare_digest`) |
| Rate limiting | 10 requêtes/min par IP sur les endpoints admin (anti brute-force) |
| Headers HTTP | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy` |
| Validation | Entrées validées par Pydantic, anti-injection SQL par SQLAlchemy |
| CORS | Restreint au domaine GitHub Pages (configurable via env var) |
| Secrets | Token admin en variable d'environnement, jamais dans le code |

Lectures publiques (grille, gratuité, historique) — utile pour un panneau d'affichage ou un site web du parking.

## Logs

Une ligne par événement sur stdout, au format `clé=valeur` (lisible dans les logs Render et facile à filtrer). Niveau réglable via la variable d'environnement `LOG_LEVEL` (défaut `INFO`).

| Logger | Événement | Niveau | Contenu |
|---|---|---|---|
| `pricing` | `startup` / `shutdown` | INFO | version, environnement |
| `pricing.http` | `http_request` | INFO (2xx/3xx), WARNING (4xx), ERROR (5xx) | méthode, route, statut, durée en ms |
| `pricing.business` | `quote_computed` | INFO | quote_id, version de grille, zone, mode, durée, montant |
| `pricing.business` | `grid_published` | INFO | type de changement, nouvelle et ancienne version, valeur modifiée |
| `pricing.errors` | `domain_error` | WARNING | code d'erreur métier, route |
| `pricing.errors` | `unexpected_error` | ERROR | stack trace complète (le client reçoit seulement un message générique) |
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
4. Le token admin est généré automatiquement (visible dans les env vars du dashboard Render).

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
