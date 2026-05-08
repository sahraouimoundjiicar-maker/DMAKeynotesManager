"""
main.py
-------
Point d'entrée FastAPI — DMAKeynotesManager.

Rôle :
    - Initialiser l'application FastAPI
    - Configurer le middleware CORS
    - Inclure tous les routeurs avec le préfixe /api/v1
    - Initialiser la BD au démarrage
    - Vérifier la configuration au démarrage

Lancement :
    cd backend
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Documentation API interactive :
    http://localhost:8000/docs

Documentation API alternative :
    http://localhost:8000/redoc
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    NOM_APPLICATION,
    VERSION_APPLICATION,
    PREFIX_API,
    verifier_configuration,
)
from app.database.connection import initialiser_application
from app.logger import configurer_logging, get_logger

# Importer tous les routeurs
from app.api.routers import auth
from app.api.routers import utilisateurs
from app.api.routers import projets
from app.api.routers import acces
from app.api.routers import categories
from app.api.routers import notes
from app.api.routers import historique
from app.api.routers import export


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — INITIALISATION DU LOGGING
# ─────────────────────────────────────────────────────────────

# Étape 1.1 — Configurer le logging avant tout le reste
"""
Le logging doit être configuré en premier pour capturer
tous les messages dès le démarrage de l'application.
"""
configurer_logging()
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — CRÉATION DE L'APPLICATION FASTAPI
# ─────────────────────────────────────────────────────────────

# Étape 2.1 — Créer l'instance FastAPI
"""
La documentation Swagger est automatiquement générée
et accessible à /docs. Elle liste toutes les routes
avec leurs paramètres et modèles de réponse.
"""
app = FastAPI(
    title       = NOM_APPLICATION,
    version     = VERSION_APPLICATION,
    description = (
        "API de gestion des keynotes Revit — "
        "DMAKeynotesManager. "
        "Gérez vos projets, catégories et notes "
        "keynotes Revit en équipe."
    ),
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — CONFIGURATION CORS
# ─────────────────────────────────────────────────────────────

# Étape 3.1 — Configurer le middleware CORS
"""
CORS (Cross-Origin Resource Sharing) permet au frontend
d'accéder à l'API depuis un domaine différent.
allow_origins = ["*"] autorise tout le réseau local
ce qui est adapté pour une application interne.
En production, remplacer par l'URL exacte du frontend.
"""
app.add_middleware(
    CORSMiddleware,
    allow_origins     = [
        "https://dmakm.onrender.com",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — ÉVÉNEMENTS DE DÉMARRAGE
# ─────────────────────────────────────────────────────────────

@app.on_event("startup")
def au_demarrage() -> None:
    """
    Exécutée automatiquement au démarrage de l'application.
    Initialise la BD et vérifie la configuration.
    """
    # Étape 4.1 — Vérifier les dossiers nécessaires
    logger.info(
        f"Démarrage de {NOM_APPLICATION} v{VERSION_APPLICATION}"
    )
    verifier_configuration()

    # Étape 4.2 — Initialiser la BD et les tables
    """
    Crée la BD DMAKeynotesManager et toutes les tables
    si elles n'existent pas encore.
    Sans effet si la BD existe déjà.
    """
    initialiser_application()

    logger.info(
        f"{NOM_APPLICATION} prêt sur {PREFIX_API}"
    )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 5 — INCLUSION DES ROUTEURS
# ─────────────────────────────────────────────────────────────

# Étape 5.1 — Inclure tous les routeurs avec le préfixe API
"""
Chaque routeur gère un domaine métier distinct.
Le PREFIX_API (/api/v1) est ajouté devant toutes les routes.
Ex: auth.router avec prefix="/auth" → /api/v1/auth/login
"""
app.include_router(auth.router,         prefix=PREFIX_API)
app.include_router(utilisateurs.router, prefix=PREFIX_API)
app.include_router(projets.router,      prefix=PREFIX_API)
app.include_router(acces.router,        prefix=PREFIX_API)
app.include_router(categories.router,   prefix=PREFIX_API)
app.include_router(notes.router,        prefix=PREFIX_API)
app.include_router(historique.router,   prefix=PREFIX_API)
app.include_router(export.router,       prefix=PREFIX_API)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 6 — ROUTE DE SANTÉ
# ─────────────────────────────────────────────────────────────

@app.get("/", tags=["Santé"], summary="Vérifier l'état de l'API")
def healthcheck() -> dict:
    """
    Vérifie que l'API est en ligne et retourne les infos
    de base de l'application.
    Utilisée pour tester la connectivité au serveur.
    """
    # Étape 6.1 — Retourner les infos de l'application
    return {
        "application": NOM_APPLICATION,
        "version"    : VERSION_APPLICATION,
        "statut"     : "en ligne",
        "api"        : PREFIX_API,
        "docs"       : "/docs",
    }