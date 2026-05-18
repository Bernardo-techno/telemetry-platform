# Procédure d'ajout d'une nouvelle source de métriques

> **Besoin BF-12** : Permettre l'ajout d'une nouvelle source sans modifier l'architecture.

Cette procédure montre comment ajouter un nouvel exporter à la plateforme en 3 étapes, sans toucher aux composants existants (Prometheus, Grafana, Alertmanager restent inchangés).

---

## Exemple : Ajouter un exporter Redis

### Étape 1 — Ajouter le service dans `docker-compose.yml`

Ajouter ce bloc dans la section `services` :

```yaml
  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: redis-exporter
    restart: unless-stopped
    ports:
      - "9121:9121"
    environment:
      - REDIS_ADDR=redis://redis:6379
    networks:
      - telemetry-net
```

### Étape 2 — Déclarer la cible dans `prometheus/prometheus.yml`

Ajouter un nouveau job dans `scrape_configs` :

```yaml
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']
        labels:
          domaine: 'infrastructure'
          role: 'cache-redis'
```

### Étape 3 — Recharger Prometheus et vérifier

```bash
# Relancer les services modifiés
docker compose up -d

# Vérifier que Prometheus scrappe la nouvelle cible
curl -s http://localhost:9090/api/v1/targets | grep redis
```

La nouvelle cible apparaît dans Prometheus > Status > Targets avec le statut "UP".

---

## Optionnel : Ajouter un dashboard Grafana

Créer un fichier `grafana/dashboards/redis.json` avec les panels souhaités. Grâce au provisioning automatique, le dashboard sera chargé au prochain redémarrage de Grafana.

---

## Validation du cas test

| Étape | Résultat attendu | Validé |
|-------|------------------|--------|
| Service ajouté dans docker-compose.yml | Le conteneur démarre sans erreur | ☐ |
| Job ajouté dans prometheus.yml | La cible apparaît dans Prometheus /targets en "UP" | ☐ |
| Aucun autre fichier modifié | Alertmanager, Grafana, Telegraf inchangés | ☐ |
| Métriques disponibles | Requête PromQL `redis_up` retourne 1 | ☐ |

Cette procédure prouve que l'architecture est extensible : ajouter une source = 2 fichiers modifiés, 0 composant impacté.
