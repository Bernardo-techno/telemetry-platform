#!/usr/bin/env python3
"""
Générateur de charge — simule du trafic utilisateur sur le microservice.
Envoie un mélange de requêtes GET et POST pour produire des métriques RED réalistes.
"""

import requests
import time
import random
import os
import logging
import signal
import sys

TARGET_HOST = os.getenv("TARGET_HOST", "microservice-demo")
TARGET_PORT = os.getenv("TARGET_PORT", "8000")
RPS = float(os.getenv("REQUESTS_PER_SECOND", "2"))
BASE_URL = f"http://{TARGET_HOST}:{TARGET_PORT}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("load-generator")

running = True

def signal_handler(sig, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def main():
    # Attendre que le service soit prêt
    logger.info(f"Attente du service {BASE_URL}...")
    for attempt in range(60):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=3)
            if r.status_code == 200:
                logger.info("Service prêt. Début de la génération de charge.")
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        logger.error("Service non disponible après 120s. Abandon.")
        sys.exit(1)

    intervalle = 1.0 / RPS
    compteur = 0
    erreurs = 0

    while running:
        try:
            # Mélange réaliste de requêtes
            choix = random.random()

            if choix < 0.50:
                # 50% : lister les commandes
                r = requests.get(f"{BASE_URL}/api/commandes", timeout=5)
            elif choix < 0.85:
                # 35% : détail d'une commande (parfois ID invalide)
                cid = random.choice([1, 2, 3, 4, 5, 6, 7, 8, 50, 99])
                r = requests.get(f"{BASE_URL}/api/commandes/{cid}", timeout=5)
            else:
                # 15% : créer une commande
                r = requests.post(f"{BASE_URL}/api/commandes", timeout=5)

            compteur += 1
            if r.status_code >= 500:
                erreurs += 1

        except requests.exceptions.RequestException as e:
            erreurs += 1
            compteur += 1

        # Log toutes les 100 requêtes
        if compteur % 100 == 0:
            taux_erreur = (erreurs / compteur * 100) if compteur > 0 else 0
            logger.info(f"Requêtes: {compteur} | Erreurs: {erreurs} ({taux_erreur:.1f}%)")

        # Attente avec un peu de jitter
        time.sleep(intervalle * random.uniform(0.5, 1.5))

    logger.info(f"Arrêt. Total: {compteur} requêtes, {erreurs} erreurs.")


if __name__ == "__main__":
    main()
