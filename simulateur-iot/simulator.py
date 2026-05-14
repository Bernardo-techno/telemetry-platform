#!/usr/bin/env python3
"""
Simulateur de capteurs IoT
Publie des mesures MQTT réalistes sur le broker Mosquitto.
Types de capteurs : température, pression, vibration, batterie.
"""

import paho.mqtt.client as mqtt
import json
import time
import random
import os
import logging
import signal
import sys

# ── Configuration ──────────────────────────────────────────────────────────

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
NB_CAPTEURS = int(os.getenv("NB_CAPTEURS", 20))
INTERVALLE = int(os.getenv("INTERVALLE_SECONDES", 10))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("simulateur-iot")

# ── Gestion de l'arrêt propre ─────────────────────────────────────────────

running = True

def signal_handler(sig, frame):
    global running
    logger.info("Arrêt du simulateur...")
    running = False

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# ── Génération des capteurs ───────────────────────────────────────────────

TYPES_CAPTEURS = ["temperature", "pression", "vibration", "batterie"]
LOCATIONS = ["usine_nord", "usine_sud", "entrepot_A", "entrepot_B", "site_exterieur"]

def generer_capteurs(n):
    """Crée une liste de n capteurs avec des propriétés aléatoires."""
    capteurs = []
    for i in range(1, n + 1):
        type_capteur = TYPES_CAPTEURS[(i - 1) % len(TYPES_CAPTEURS)]
        capteurs.append({
            "id": f"capteur_{i:03d}",
            "location": random.choice(LOCATIONS),
            "type": type_capteur,
            "batterie": random.uniform(50, 100),  # État initial de la batterie
        })
    return capteurs


def generer_valeur(capteur):
    """Génère une valeur réaliste selon le type de capteur."""
    t = capteur["type"]

    if t == "temperature":
        # Température entre 15°C et 90°C avec pics occasionnels
        base = random.gauss(45, 15)
        # 5% de chance d'un pic de chaleur (pour déclencher des alertes)
        if random.random() < 0.05:
            base = random.uniform(76, 95)
        return round(max(10, min(100, base)), 2)

    elif t == "pression":
        # Pression entre 1 et 10 bar
        return round(random.gauss(5.5, 1.5), 2)

    elif t == "vibration":
        # Vibration entre 0.0 et 5.0 mm/s
        base = random.gauss(1.5, 0.8)
        # Pic occasionnel
        if random.random() < 0.03:
            base = random.uniform(4.0, 6.0)
        return round(max(0.0, base), 3)

    elif t == "batterie":
        # La batterie diminue lentement
        capteur["batterie"] = max(5, capteur["batterie"] - random.uniform(0, 0.3))
        return round(capteur["batterie"], 1)

    return 0.0


def get_unite(type_capteur):
    """Retourne l'unité de mesure pour chaque type."""
    unites = {
        "temperature": "°C",
        "pression": "bar",
        "vibration": "mm/s",
        "batterie": "%"
    }
    return unites.get(type_capteur, "")


# ── Boucle principale ────────────────────────────────────────────────────

def main():
    # Connexion MQTT avec retry
    client = mqtt.Client(client_id="simulateur-iot", protocol=mqtt.MQTTv311)

    logger.info(f"Connexion au broker MQTT {MQTT_HOST}:{MQTT_PORT}...")
    connected = False
    for attempt in range(30):
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            client.loop_start()
            connected = True
            logger.info("Connecté au broker MQTT.")
            break
        except Exception as e:
            logger.warning(f"Tentative {attempt+1}/30 échouée : {e}")
            time.sleep(2)

    if not connected:
        logger.error("Impossible de se connecter au broker MQTT. Abandon.")
        sys.exit(1)

    # Créer les capteurs
    capteurs = generer_capteurs(NB_CAPTEURS)
    logger.info(f"{len(capteurs)} capteurs simulés créés.")
    for c in capteurs:
        logger.info(f"  → {c['id']} | type={c['type']} | location={c['location']}")

    # Boucle d'envoi
    compteur = 0
    while running:
        for capteur in capteurs:
            valeur = generer_valeur(capteur)

            message = {
                "device_id": capteur["id"],
                "location": capteur["location"],
                "type": capteur["type"],
                "value": valeur,
                "unit": get_unite(capteur["type"]),
                "timestamp": time.time()
            }

            topic = f"sensors/{capteur['id']}/telemetry"
            client.publish(topic, json.dumps(message), qos=0)

        compteur += 1
        if compteur % 6 == 0:  # Log toutes les minutes environ
            logger.info(f"Cycle #{compteur} — {NB_CAPTEURS} mesures publiées.")

        time.sleep(INTERVALLE)

    # Nettoyage
    client.loop_stop()
    client.disconnect()
    logger.info("Simulateur arrêté proprement.")


if __name__ == "__main__":
    main()
