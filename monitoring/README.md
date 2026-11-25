# Monitoring local de Pricing (Prometheus + Grafana)

Prometheus collecte toutes les 15 s les métriques du service déployé (`https://pricing-9khk.onrender.com/metrics`). Grafana les affiche dans un tableau de bord « Pricing ».

## Lancer / arrêter

Docker Desktop doit être démarré. Les commandes se lancent depuis ce dossier (`monitoring/`).

```powershell
docker compose up -d      # démarrer
docker compose stop       # arrêter (les données sont gardées)
docker compose start      # relancer
docker compose down       # supprimer les conteneurs (les données restent dans les volumes)
docker compose down -v    # tout supprimer, y compris l'historique collecté
```

## Accès

| Outil | URL | Usage |
|---|---|---|
| Grafana | http://localhost:3000 | Tableau de bord « Pricing ». Lecture sans connexion ; `admin` / `admin` pour modifier (mot de passe à changer à la première connexion) |
| Prometheus | http://localhost:9090 | Requêtes PromQL (onglet *Query*), état de la collecte (*Status → Target health*) |

Les ports sont liés à `127.0.0.1` : accessibles uniquement depuis cet ordinateur.

## Fichiers

| Fichier | Rôle |
|---|---|
| `docker-compose.yml` | Les deux conteneurs et leurs volumes |
| `prometheus/prometheus.yml` | Cible collectée (Render, en HTTPS) et intervalle |
| `grafana/provisioning/datasources/prometheus.yml` | Branche Grafana sur Prometheus automatiquement |
| `grafana/provisioning/dashboards/pricing.yml` | Charge les tableaux de bord du dossier `grafana/dashboards` |
| `grafana/dashboards/pricing.json` | Le tableau de bord « Pricing » |

## Tableau de bord

- **En haut** : service UP/DOWN, version, grille en vigueur, devis calculés sur la période, taux d'erreur serveur, mémoire.
- **Métier** : devis par zone et par mode, montant moyen d'un devis.
- **Technique** : requêtes par seconde et par route, requêtes par statut, temps de réponse au 95e percentile, refus métier par code, échecs d'authentification admin et publications de grille.

Les appels de Prometheus à `/metrics` sont exclus des graphiques de requêtes.

Les métriques de Pricing sont en mémoire : elles repartent de zéro quand Render redémarre le service. Les fonctions `rate()` et `increase()` utilisées dans les graphiques tiennent compte de ces remises à zéro.
