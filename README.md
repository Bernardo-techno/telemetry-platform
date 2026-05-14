# Plateforme de Supervision de Télémétrie

> **Référence** : PRJ-TEL-2026-001  
> **Version** : 1.0  
> **Master 1** — Informatique / Systèmes embarqués

## Présentation

Plateforme de supervision multi-domaines couvrant :
- **Infrastructure IT** : métriques hôtes Linux et conteneurs Docker
- **IoT industriel** : capteurs simulés communiquant en MQTT
- **Microservices applicatifs** : instrumentation méthode RED (Rate, Errors, Duration)

Stack : Prometheus · Alertmanager · Grafana · Telegraf · Mosquitto · Docker Compose

---

## Prérequis

- Ubuntu Server 20.04+ (ou toute distribution Linux)
- Docker Engine 24+
- Docker Compose v2
- 4 cœurs CPU, 8 Go RAM minimum
- 20 Go d'espace disque libre

## Installation rapide

### 1. Installer Docker (si pas déjà fait)

```bash
# Mise à jour du système
sudo apt update && sudo apt upgrade -y

# Installation de Docker
curl -fsSL https://get.docker.com | sudo sh

# Ajouter votre utilisateur au groupe docker
sudo usermod -aG docker $USER

# Se reconnecter pour appliquer
exit
# Reconnexion SSH

# Vérifier l'installation
docker --version
docker compose version
```

### 2. Cloner et lancer le projet

```bash
# Cloner le dépôt
git clone <url-du-depot> telemetry-platform
cd telemetry-platform

# Copier le fichier d'environnement
cp .env.example .env
# (Optionnel) Modifier le mot de passe Grafana dans .env

# Lancer toute la plateforme
docker compose up -d

# Vérifier que tous les services tournent
docker compose ps
```

### 3. Accéder aux interfaces

| Service | URL | Identifiants |
|---|---|---|
| **Grafana** | http://<IP_VM>:3000 | admin / SuperSecret2026! |
| **Prometheus** | http://<IP_VM>:9090 | — |
| **Alertmanager** | http://<IP_VM>:9093 | — |
| **Pushgateway** | http://<IP_VM>:9091 | — |
| **Microservice** | http://<IP_VM>:8000/docs | — |

### 4. Vérifications post-déploiement

```bash
# Vérifier les logs de chaque service
docker compose logs prometheus --tail=20
docker compose logs telegraf --tail=20
docker compose logs simulateur-iot --tail=20
docker compose logs microservice-demo --tail=20

# Vérifier que Prometheus scrappe bien toutes les cibles
# → Ouvrir http://<IP_VM>:9090/targets
# → Toutes les cibles doivent être en état "UP"

# Vérifier les messages MQTT du simulateur
docker compose exec mosquitto mosquitto_sub -t "sensors/#" -C 5
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        COUCHE RESTITUTION                           │
│                    Grafana (dashboards + alertes)                    │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ PromQL
┌───────────────────────────────▼──────────────────────────────────────┐
│                    COUCHE COLLECTE & STOCKAGE                        │
│              Prometheus (TSDB + rules) ← Alertmanager                │
│                         ↑ scrape                                     │
├──────────────┬──────────────────┬───────────────────┬────────────────┤
│ Node Exporter│    cAdvisor      │    Telegraf        │  Microservice  │
│ (hôte Linux) │ (conteneurs)     │ (bridge MQTT)      │  (FastAPI)     │
├──────────────┴──────────────────┴───────┬───────────┴────────────────┤
│                                         │                            │
│           INFRASTRUCTURE                │ Mosquitto (broker MQTT)    │
│                                         │       ↑ publish            │
│                                         │  Simulateur IoT            │
└─────────────────────────────────────────┴────────────────────────────┘
```

---

## Commandes utiles

```bash
# Démarrer tout
docker compose up -d

# Arrêter tout
docker compose down

# Reconstruire après modification du code
docker compose up -d --build

# Voir les logs en temps réel
docker compose logs -f

# Redémarrer un seul service
docker compose restart prometheus

# Supprimer tout (y compris les volumes de données)
docker compose down -v
```

---

## Dashboards Grafana

4 dashboards provisionnés automatiquement :

1. **Synthèse — Vue Multi-Domaines** : indicateurs clés des 3 domaines
2. **Infrastructure — Hôtes & Conteneurs** : CPU, RAM, disque, réseau, Docker
3. **IoT — Capteurs Industriels** : températures, pressions, vibrations, batteries
4. **Applicatif — Métriques RED** : requêtes/s, taux d'erreur, latence p50/p95/p99

## Règles d'alerting

10 règles actives couvrant les 3 domaines (voir `prometheus/alert_rules.yml`).

---

## Structure du projet

```
telemetry-platform/
├── docker-compose.yml              # Orchestration de tous les services
├── .env.example                    # Variables d'environnement (template)
├── prometheus/
│   ├── prometheus.yml              # Configuration des cibles de scraping
│   └── alert_rules.yml             # 10 règles d'alerting
├── alertmanager/
│   └── alertmanager.yml            # Routage des alertes par domaine
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/            # Connexion auto Prometheus
│   │   └── dashboards/             # Chargement auto des dashboards
│   └── dashboards/
│       ├── synthese.json           # Dashboard de synthèse
│       ├── infra.json              # Dashboard infrastructure
│       ├── iot.json                # Dashboard IoT
│       └── app.json                # Dashboard applicatif
├── telegraf/
│   └── telegraf.conf               # Bridge MQTT → Prometheus
├── mosquitto/
│   └── mosquitto.conf              # Broker MQTT
├── simulateur-iot/
│   ├── Dockerfile
│   └── simulator.py                # Simulation de 20 capteurs
├── microservice-demo/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py                      # API FastAPI avec métriques RED
├── load-generator/
│   ├── Dockerfile
│   └── load_generator.py           # Génération de trafic réaliste
└── docs/
    └── ...                         # Documentation complémentaire
```
