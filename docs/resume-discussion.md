# Résumé de la discussion — Projet Télémétrie PRJ-TEL-2026-001

> Ce fichier permet de reprendre la discussion dans une nouvelle conversation sans perdre le contexte.

---

## 1. Le projet

**Cahier des charges** : Implémenter une plateforme de supervision de télémétrie couvrant 3 domaines (Infrastructure IT, IoT industriel, Microservices applicatifs) dans le cadre d'un Master 1. Le projet est réalisé en binôme (Bernard + Samira).

**Repo GitHub** : https://github.com/Bernardo-techno/telemetry-platform (privé)

**Stack** : Prometheus, Alertmanager, Grafana, Telegraf, Mosquitto, Docker Compose, Python/FastAPI.

**12 besoins fonctionnels (BF-01 à BF-12)** — tous validés.

---

## 2. Architecture — 11 conteneurs

| Service | Port | Rôle |
|---|---|---|
| node-exporter | 9100 | Métriques OS |
| cadvisor | 8080 | Métriques conteneurs Docker |
| mosquitto | 1883 | Broker MQTT |
| telegraf | 9273 | Bridge MQTT → Prometheus |
| simulateur-iot | — | 20 capteurs simulés (mode intelligent) |
| microservice-demo | 8000 | API FastAPI + métriques RED |
| load-generator | — | Trafic simulé |
| prometheus | 9090 | Collecte pull + TSDB + règles |
| alertmanager | 9093 | Routage alertes par domaine |
| pushgateway | 9091 | Jobs batch |
| grafana | 3000 | 4 dashboards provisionnés |

---

## 3. Environnements

**VM locale (en cours d'utilisation)** : IP 100.108.147.110, user bernard

**VM Azure (prête mais pas encore utilisée)** : IP 4.178.155.91, user bernardo, clé SSH ubuntu-serv_key.pem, Ubuntu 24.04, Standard_B2s_v2, France Central, Azure for Students. Compte amie : ndamsamira (mot de passe, PasswordAuthentication activé). Ports NSG ouverts : 22, 3000, 8000, 9090, 9091, 9093.

---

## 4. Problèmes résolus

**cAdvisor cgroup v2** : volumes corrigés → `/var/run:/var/run:ro`, `/:/rootfs:ro`, `/etc/machine-id:/etc/machine-id:ro`. Fonctionne maintenant.

**Simulateur IoT** : v3 avec cycles jour/nuit, profils par zone, surchauffes persistantes 2-5 min, recharge batterie à 3%, pannes 1-3 min. Dernière erreur : requirements.txt manquant → créé avec paho-mqtt==2.1.0.

---

## 5. CI/CD

Fichier `.github/workflows/deploy.yml`. Secrets : VM_HOST, VM_USER, VM_SSH_KEY ou VM_PASSWORD. Pas encore fonctionnel (VM locale inaccessible depuis GitHub, VM Azure pas encore testée).

---

## 6. Livrables

| Code | État |
|---|---|
| L1 Code source | ✅ |
| L2 Doc architecture | ✅ (architecture.md) |
| L3 Procédure déploiement | ✅ (README.md) |
| L4 Dashboards Grafana | ✅ (4 JSON) |
| L5 Catalogue alertes | ❌ À faire |
| L6 Rapport de tests | ❌ À faire |
| L7 Slides soutenance | ❌ À faire |

---

## 7. Alertes testées

- IoTBatteryLow ✅ Firing
- IoTTemperatureHigh ✅ Firing
- AppHighErrorRate ✅ Firing
- AppServiceDown ✅ Firing (docker compose stop microservice-demo)
- HostHighCpuUsage ⚠️ À retester pendant que stress tourne
- IoTSensorSilent ⚠️ À vérifier

---

## 8. Prochaines étapes

1. Push requirements.txt + redéployer simulateur
2. Tester CI/CD sur VM Azure
3. Rédiger L5, L6, L7
4. Valider alertes restantes