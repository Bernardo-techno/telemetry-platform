#!/usr/bin/env python3
"""
Microservice de démonstration — Service Commandes
Instrumenté avec la méthode RED (Rate, Errors, Duration).
Expose un endpoint /metrics pour Prometheus.
"""

from fastapi import FastAPI, HTTPException
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
)
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import random
import asyncio
import time
import os

# ── Configuration ──────────────────────────────────────────────────────────

APP_NAME = os.getenv("APP_NAME", "service-commandes")

app = FastAPI(title="Service Commandes — Démo Télémétrie")

# ── Métriques Prometheus (RED) ─────────────────────────────────────────────

# R = Rate : nombre total de requêtes
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Nombre total de requêtes HTTP',
    ['method', 'endpoint', 'status']
)

# E = Errors : compté dans REQUEST_COUNT avec status=5xx

# D = Duration : histogramme des durées
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'Durée des requêtes HTTP en secondes',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Métriques supplémentaires
REQUESTS_IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'Nombre de requêtes en cours de traitement',
    ['method', 'endpoint']
)

APP_INFO = Gauge(
    'app_info',
    'Informations sur le service',
    ['app_name', 'version']
)
APP_INFO.labels(app_name=APP_NAME, version="1.0.0").set(1)

# ── Données simulées ──────────────────────────────────────────────────────

COMMANDES_DB = [
    {"id": 1, "produit": "Capteur Température Pro", "prix": 89.99, "statut": "livrée"},
    {"id": 2, "produit": "Sonde Pression Industrielle", "prix": 249.00, "statut": "en cours"},
    {"id": 3, "produit": "Accéléromètre 3 axes", "prix": 129.50, "statut": "livrée"},
    {"id": 4, "produit": "Module Gateway LoRa", "prix": 199.00, "statut": "préparation"},
    {"id": 5, "produit": "Batterie Li-Ion 3.7V", "prix": 34.99, "statut": "livrée"},
    {"id": 6, "produit": "Boîtier IP67 extérieur", "prix": 45.00, "statut": "en cours"},
    {"id": 7, "produit": "Carte SIM M2M", "prix": 9.99, "statut": "livrée"},
    {"id": 8, "produit": "Antenne 868MHz", "prix": 19.50, "statut": "préparation"},
]

# ── Endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/commandes")
async def liste_commandes():
    """Liste toutes les commandes."""
    endpoint = "/api/commandes"
    REQUESTS_IN_PROGRESS.labels("GET", endpoint).inc()

    try:
        with REQUEST_DURATION.labels("GET", endpoint).time():
            # Simuler un temps de traitement variable
            await asyncio.sleep(random.uniform(0.01, 0.2))

            # Simuler des erreurs (environ 8% du temps)
            if random.random() < 0.08:
                REQUEST_COUNT.labels("GET", endpoint, "500").inc()
                raise HTTPException(status_code=500, detail="Erreur base de données simulée")

            # Simuler des ralentissements occasionnels (3%)
            if random.random() < 0.03:
                await asyncio.sleep(random.uniform(0.5, 2.0))

            REQUEST_COUNT.labels("GET", endpoint, "200").inc()
            return {"total": len(COMMANDES_DB), "commandes": COMMANDES_DB}
    finally:
        REQUESTS_IN_PROGRESS.labels("GET", endpoint).dec()


@app.get("/api/commandes/{commande_id}")
async def detail_commande(commande_id: int):
    """Détail d'une commande par ID."""
    endpoint = "/api/commandes/{id}"
    REQUESTS_IN_PROGRESS.labels("GET", endpoint).inc()

    try:
        with REQUEST_DURATION.labels("GET", endpoint).time():
            await asyncio.sleep(random.uniform(0.005, 0.1))

            # Simuler erreur 404 pour IDs > 8
            if commande_id > len(COMMANDES_DB):
                REQUEST_COUNT.labels("GET", endpoint, "404").inc()
                raise HTTPException(status_code=404, detail="Commande non trouvée")

            # Simuler erreur 500 (5%)
            if random.random() < 0.05:
                REQUEST_COUNT.labels("GET", endpoint, "500").inc()
                raise HTTPException(status_code=500, detail="Erreur interne simulée")

            REQUEST_COUNT.labels("GET", endpoint, "200").inc()
            return COMMANDES_DB[commande_id - 1]
    finally:
        REQUESTS_IN_PROGRESS.labels("GET", endpoint).dec()


@app.post("/api/commandes")
async def creer_commande():
    """Créer une nouvelle commande."""
    endpoint = "/api/commandes"
    REQUESTS_IN_PROGRESS.labels("POST", endpoint).inc()

    try:
        with REQUEST_DURATION.labels("POST", endpoint).time():
            await asyncio.sleep(random.uniform(0.05, 0.4))

            if random.random() < 0.1:
                REQUEST_COUNT.labels("POST", endpoint, "500").inc()
                raise HTTPException(status_code=500, detail="Erreur création simulée")

            REQUEST_COUNT.labels("POST", endpoint, "201").inc()
            return {"id": random.randint(100, 999), "statut": "créée"}
    finally:
        REQUESTS_IN_PROGRESS.labels("POST", endpoint).dec()


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": APP_NAME}


@app.get("/metrics")
async def metrics():
    """Endpoint Prometheus — scrappé toutes les 15s."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
