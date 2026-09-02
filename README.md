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
- SQLite (persistance)
- Pydantic v2 (validation)
- pytest + httpx (tests)

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

Au premier démarrage, la base est créée et pré-remplie avec une grille tarifaire initiale (5 zones × 2 modes + gratuité de 15 min).

## Tests

```bash
pytest
```

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

- Écritures protégées par header `X-Admin-Token` (env var).
- Lectures publiques (grille, gratuité, historique) — utile pour un panneau d'affichage ou un site web du parking.
- Validation stricte des entrées (Pydantic).
- Anti-injection SQL garantie par SQLAlchemy.
- CORS configurable via env var.

## Déploiement Render

Le fichier `render.yaml` déclare le service. Sur Render :
1. Nouveau *Web Service* → connecter le repo GitHub → détection auto de `render.yaml`.
2. Deploy.
3. Le token admin est généré automatiquement (visible dans les env vars du dashboard Render).

## Périmètre

Voir la spec complète dans le Google Doc partagé avec le groupe.

Résumé :
- Grille tarifaire versionnée, chaque devis référence sa grille.
- 5 zones (`standard`, `xl`, `disabled`, `electric`, `two_wheels`) × 2 modes (`reserved`, `walk_in`).
- Walk-in facturé au quart d'heure entamé, gratuité initiale de 15 min.
- Réservation facturée à l'heure pleine, pas de gratuité.
- Durée max 7 jours.
- Devise unique : EUR.
