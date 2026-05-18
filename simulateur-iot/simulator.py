#!/usr/bin/env python3
"""
Simulateur de capteurs IoT — Version intelligente
Comportements réalistes : cycles jour/nuit, corrélation machine,
pannes simulées, recharge batterie, scénarios d'incidents.
"""

import paho.mqtt.client as mqtt
import json
import time
import random
import math
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

running = True

def signal_handler(sig, frame):
    global running
    logger.info("Arrêt du simulateur...")
    running = False

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


# ── Profils de zones ──────────────────────────────────────────────────────
# Chaque zone a un comportement différent

ZONE_PROFILES = {
    "usine_nord": {
        "description": "Production lourde — machines industrielles",
        "temp_base": 55, "temp_amplitude": 15,
        "pression_base": 7.0, "pression_bruit": 0.5,
        "vibration_base": 2.5, "vibration_bruit": 0.8,
        "machine_cycle": True,   # Température et vibration corrélées
    },
    "usine_sud": {
        "description": "Production légère — assemblage",
        "temp_base": 35, "temp_amplitude": 8,
        "pression_base": 4.0, "pression_bruit": 0.3,
        "vibration_base": 1.0, "vibration_bruit": 0.4,
        "machine_cycle": True,
    },
    "entrepot_A": {
        "description": "Stockage climatisé — température stable",
        "temp_base": 20, "temp_amplitude": 3,
        "pression_base": 1.0, "pression_bruit": 0.1,
        "vibration_base": 0.2, "vibration_bruit": 0.1,
        "machine_cycle": False,
    },
    "entrepot_B": {
        "description": "Stockage froid — chambre froide",
        "temp_base": 5, "temp_amplitude": 2,
        "pression_base": 1.0, "pression_bruit": 0.1,
        "vibration_base": 0.3, "vibration_bruit": 0.1,
        "machine_cycle": False,
    },
    "site_exterieur": {
        "description": "Extérieur — capteurs météo",
        "temp_base": 22, "temp_amplitude": 12,
        "pression_base": 1.013, "pression_bruit": 0.05,
        "vibration_base": 0.5, "vibration_bruit": 0.3,
        "machine_cycle": False,
    },
}


# ── Génération des capteurs ───────────────────────────────────────────────

TYPES_CAPTEURS = ["temperature", "pression", "vibration", "batterie"]

def generer_capteurs(n):
    """Crée n capteurs avec des profils de zone réalistes."""
    zones = list(ZONE_PROFILES.keys())
    capteurs = []
    for i in range(1, n + 1):
        type_capteur = TYPES_CAPTEURS[(i - 1) % len(TYPES_CAPTEURS)]
        zone = zones[(i - 1) // 4 % len(zones)]  # 4 capteurs par zone
        capteurs.append({
            "id": f"capteur_{i:03d}",
            "location": zone,
            "type": type_capteur,
            "batterie": random.uniform(60, 100),
            "last_value": None,        # Pour lisser les variations
            "en_panne": False,          # Simulation de panne
            "panne_countdown": 0,       # Cycles restants avant reprise
            "charge_en_cours": False,   # Batterie en recharge
        })
    return capteurs


def get_heure_simulee():
    """Retourne une heure simulée (0-24) pour les cycles jour/nuit.
    Compresse 24h sur 20 minutes pour voir les variations rapidement."""
    return (time.time() % 1200) / 1200 * 24


def generer_valeur(capteur, heure):
    """Génère une valeur réaliste basée sur la zone, l'heure et l'historique."""
    zone = ZONE_PROFILES[capteur["location"]]
    t = capteur["type"]

    # ── Simulation de panne (2% de chance par cycle) ──
    if not capteur["en_panne"] and random.random() < 0.002:
        capteur["en_panne"] = True
        capteur["panne_countdown"] = random.randint(6, 18)  # 1-3 min de panne
        logger.warning(f"⚡ PANNE simulée : {capteur['id']} ({t} @ {capteur['location']})")
        return None  # Pas de données = capteur silencieux

    if capteur["en_panne"]:
        capteur["panne_countdown"] -= 1
        if capteur["panne_countdown"] <= 0:
            capteur["en_panne"] = False
            logger.info(f"✅ REPRISE : {capteur['id']} est de retour en ligne")
        return None  # Toujours en panne

    # ── Cycle jour/nuit (sinusoïdal) ──
    cycle_jour = math.sin((heure - 6) / 24 * 2 * math.pi)  # Max à 12h, min à 0h

    # ── Cycle machine (on/off selon l'heure) ──
    machine_active = 6 <= heure <= 22 if zone["machine_cycle"] else True

    if t == "temperature":
        base = zone["temp_base"]
        amplitude = zone["temp_amplitude"]
        # Température suit le cycle jour/nuit
        valeur = base + amplitude * cycle_jour * 0.5
        # Si machine active, la température monte
        if zone["machine_cycle"] and machine_active:
            valeur += amplitude * 0.4
        # Bruit réaliste (petites variations)
        valeur += random.gauss(0, 1.5)
        # 3% de chance de surchauffe (incident)
        if random.random() < 0.03 and machine_active:
            valeur = random.uniform(78, 95)
            logger.warning(f"🔥 SURCHAUFFE : {capteur['id']} → {valeur:.1f}°C")
        # Lisser avec la valeur précédente
        if capteur["last_value"] is not None:
            valeur = capteur["last_value"] * 0.7 + valeur * 0.3
        capteur["last_value"] = valeur
        return round(max(-10, min(100, valeur)), 2)

    elif t == "pression":
        base = zone["pression_base"]
        bruit = zone["pression_bruit"]
        valeur = base + random.gauss(0, bruit)
        # Pression augmente légèrement quand machines actives
        if zone["machine_cycle"] and machine_active:
            valeur += 1.5
        if capteur["last_value"] is not None:
            valeur = capteur["last_value"] * 0.8 + valeur * 0.2
        capteur["last_value"] = valeur
        return round(max(0.5, valeur), 2)

    elif t == "vibration":
        base = zone["vibration_base"]
        bruit = zone["vibration_bruit"]
        if zone["machine_cycle"] and machine_active:
            valeur = base + abs(random.gauss(0, bruit))
            # 2% de vibration anormale
            if random.random() < 0.02:
                valeur = random.uniform(4.5, 7.0)
                logger.warning(f"⚠️ VIBRATION anormale : {capteur['id']} → {valeur:.2f} mm/s")
        else:
            valeur = 0.1 + abs(random.gauss(0, 0.1))
        if capteur["last_value"] is not None:
            valeur = capteur["last_value"] * 0.6 + valeur * 0.4
        capteur["last_value"] = valeur
        return round(max(0.0, valeur), 3)

    elif t == "batterie":
        # Décharge lente
        drain = random.uniform(0.05, 0.2)
        capteur["batterie"] -= drain

        # Recharge automatique quand batterie < 10%
        if capteur["batterie"] < 10 and not capteur["charge_en_cours"]:
            capteur["charge_en_cours"] = True
            logger.info(f"🔋 RECHARGE démarrée : {capteur['id']} ({capteur['batterie']:.1f}%)")

        if capteur["charge_en_cours"]:
            capteur["batterie"] += random.uniform(1.0, 3.0)
            if capteur["batterie"] >= 95:
                capteur["charge_en_cours"] = False
                logger.info(f"🔋 RECHARGE terminée : {capteur['id']} (100%)")
                capteur["batterie"] = 100

        capteur["batterie"] = max(0, min(100, capteur["batterie"]))
        return round(capteur["batterie"], 1)

    return 0.0


def get_unite(type_capteur):
    return {"temperature": "°C", "pression": "bar",
            "vibration": "mm/s", "batterie": "%"}.get(type_capteur, "")


# ── Boucle principale ────────────────────────────────────────────────────

def main():
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

    capteurs = generer_capteurs(NB_CAPTEURS)
    logger.info(f"{'='*60}")
    logger.info(f"  {len(capteurs)} capteurs simulés — Mode intelligent")
    logger.info(f"{'='*60}")
    for zone, profil in ZONE_PROFILES.items():
        nb = sum(1 for c in capteurs if c["location"] == zone)
        logger.info(f"  📍 {zone} ({nb} capteurs) — {profil['description']}")
    logger.info(f"{'='*60}")

    compteur = 0
    publiees = 0
    pannes = 0

    while running:
        heure = get_heure_simulee()
        cycle_publiees = 0

        for capteur in capteurs:
            valeur = generer_valeur(capteur, heure)

            if valeur is None:
                pannes += 1
                continue  # Capteur en panne → pas de publication

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
            cycle_publiees += 1

        publiees += cycle_publiees
        compteur += 1

        if compteur % 6 == 0:
            en_panne = sum(1 for c in capteurs if c["en_panne"])
            en_charge = sum(1 for c in capteurs if c["charge_en_cours"])
            logger.info(
                f"Cycle #{compteur} | Heure simulée: {heure:.1f}h | "
                f"Publiées: {cycle_publiees}/{NB_CAPTEURS} | "
                f"En panne: {en_panne} | En recharge: {en_charge}"
            )

        time.sleep(INTERVALLE)

    client.loop_stop()
    client.disconnect()
    logger.info(f"Arrêté. Total: {publiees} mesures publiées, {pannes} pannes simulées.")


if __name__ == "__main__":
    main()
