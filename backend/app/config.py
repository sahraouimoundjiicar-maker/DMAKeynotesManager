"""
config.py
---------
Configuration centrale de l'application DMAKeynotesManager.

Rôle :
    Fournir toutes les constantes et paramètres de
    configuration à l'ensemble des modules.
    Lit les variables sensibles depuis le fichier .env.
    Compatible avec Render (DATABASE_URL) et développement local.

Importation dans les autres modules :
    from app.config import POSTGRES_CONFIG, NOM_BD, DATABASE_URL
    from app.config import CHEMIN_DOSSIER_KEYNOTES
    from app.config import PREFIX_API, SECRET_KEY
"""

import os
from dotenv import load_dotenv
from urllib.parse import urlparse


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — CHARGEMENT DES VARIABLES D'ENVIRONNEMENT
# ─────────────────────────────────────────────────────────────

# Étape 1.1 — Charger le fichier .env au démarrage
"""
Le fichier .env contient les variables sensibles.
Il ne doit jamais être commité sur Git.
Copier .env.example en .env et remplir les valeurs.
"""
load_dotenv(encoding="utf-8")


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — CONFIGURATION POSTGRESQL (COMPATIBLE RENDER)
# ─────────────────────────────────────────────────────────────

# Étape 2.1 — Gestion de DATABASE_URL (format Render)
"""
Render fournit une variable DATABASE_URL au format :
postgresql://user:password@host:port/database

Cette fonction parse cette URL et retourne un dictionnaire
de configuration compatible avec psycopg2.
"""
def _parse_database_url(url: str) -> dict:
    """Parse une URL de base de données PostgreSQL."""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": parsed.username,
        "password": parsed.password,
        "database": parsed.path.lstrip('/')
    }


# Étape 2.2 — Récupération de la configuration PostgreSQL
"""
Priorité :
1. DATABASE_URL (utilisé par Render et Neon)
2. Variables individuelles POSTGRES_* (développement local)
"""
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Mode Render / Cloud : utilisation de DATABASE_URL
    db_config = _parse_database_url(DATABASE_URL)
    POSTGRES_CONFIG = {
        "host": db_config["host"],
        "port": db_config["port"],
        "user": db_config["user"],
        "password": db_config["password"],
    }
    # Le nom de la base peut venir soit de l'URL, soit de NOM_BD
    _nom_bd_from_url = db_config["database"]
else:
    # Mode développement local : variables individuelles
    POSTGRES_CONFIG = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "user": os.getenv("POSTGRES_USER", "admin"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
    }
    _nom_bd_from_url = None

# Étape 2.3 — Nom de la base de données
"""
Priorité :
1. NOM_BD (si défini explicitement)
2. Database extraite de DATABASE_URL
3. Valeur par défaut
"""
NOM_BD = os.getenv("NOM_BD") or _nom_bd_from_url or "DMAKeynotesDB"


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — CONFIGURATION DES CHEMINS
# ─────────────────────────────────────────────────────────────

# Étape 3.1 — Dossier racine du projet
"""
Remonte 3 niveaux depuis backend/app/config.py
pour atteindre DMAKeynotesManager/.
"""
DOSSIER_RACINE = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

# Étape 3.2 — Dossier des fichiers .txt keynotes
"""
Les fichiers .txt générés sont stockés ici et accessibles
sur le réseau partagé pour être rechargés dans Revit.
Un fichier .txt par projet : keynotes_[nom_projet].txt
"""
CHEMIN_DOSSIER_KEYNOTES = os.path.join(
    DOSSIER_RACINE, "shared", "keynotes"
)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — CONFIGURATION DE L'APPLICATION
# ─────────────────────────────────────────────────────────────

# Étape 4.1 — Informations générales
NOM_APPLICATION     = "DMAKeynotesManager"
VERSION_APPLICATION = "1.0.0"

# Étape 4.2 — Configuration du serveur FastAPI
"""
0.0.0.0 permet l'accès depuis tout le réseau local.
Changer à 127.0.0.1 pour limiter à localhost uniquement.
"""
FASTAPI_HOST = os.getenv("FASTAPI_HOST", "0.0.0.0")
FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", 8000))

# Étape 4.3 — Préfixe de versionnement de l'API
"""
Centraliser le préfixe ici permet de passer à /api/v2
en modifiant uniquement le fichier .env,
sans toucher aux routeurs.
"""
PREFIX_API = os.getenv("PREFIX_API", "/api/v1")


# ─────────────────────────────────────────────────────────────
# ÉTAPE 5 — CONFIGURATION DE LA SÉCURITÉ JWT
# ─────────────────────────────────────────────────────────────

# Étape 5.1 — Clé secrète pour signer les tokens JWT
"""
Générer une clé sécurisée avec :
python -c "import secrets; print(secrets.token_hex(32))"
Ne jamais utiliser la valeur par défaut en production.
Sur Render, on peut générer une clé automatiquement.
"""
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "changez_cette_cle_en_production"
)

# Étape 5.2 — Algorithme de signature JWT
"""
HS256 est l'algorithme standard recommandé pour les JWT.
"""
ALGORITHME_JWT = "HS256"

# Étape 5.3 — Durée de validité d'un token JWT
"""
480 minutes = 8 heures de session.
Après expiration, l'utilisateur doit se reconnecter.
"""
DUREE_TOKEN_MINUTES = int(
    os.getenv("DUREE_TOKEN_MINUTES", 480)
)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 6 — CONFIGURATION DU FICHIER .TXT REVIT
# ─────────────────────────────────────────────────────────────

# Étape 6.1 — Encodage des fichiers .txt
"""
UTF-8 supporte tous les caractères français avec accents
(é, è, ê, à, ù, ç...) et est compatible avec Revit.
"""
ENCODAGE_FICHIER_TXT = "utf-8"

# Étape 6.2 — Séparateur de colonnes (format Revit)
"""
Le format standard Revit utilise la tabulation comme
séparateur entre les colonnes du fichier keynotes.
"""
SEPARATEUR_COLONNES_TXT = "\t"

# Étape 6.3 — Extension des fichiers keynotes
EXTENSION_FICHIER_KEYNOTES = ".txt"

# Étape 6.4 — Taille maximale d'un fichier importé
"""
Limite à 5 MB pour éviter les imports trop volumineux
qui ralentiraient le serveur.
"""
TAILLE_MAX_FICHIER_IMPORT = 5 * 1024 * 1024  # 5 MB


# ─────────────────────────────────────────────────────────────
# ÉTAPE 7 — RÈGLES DE VALIDATION
# ─────────────────────────────────────────────────────────────

# Étape 7.1 — Longueur minimale du mot de passe
"""
3 caractères minimum.
"""
MOT_DE_PASSE_MIN_LONGUEUR = 3

# Étape 7.2 — Longueur minimale du nom et prénom
"""
2 caractères minimum pour éviter les valeurs
vides ou trop courtes.
"""
NOM_MIN_LONGUEUR = 2

# Étape 7.3 — Longueur maximale des descriptions
"""
2000 caractères maximum pour supporter les descriptions
multi-lignes importées depuis les fichiers .txt Revit.
"""
DESCRIPTION_MAX_LONGUEUR = 2000


# ─────────────────────────────────────────────────────────────
# ÉTAPE 8 — VÉRIFICATION AU DÉMARRAGE
# ─────────────────────────────────────────────────────────────

def verifier_configuration() -> None:
    """
    Vérifie que les dossiers nécessaires existent.
    Crée le dossier keynotes s'il n'existe pas.
    Appelée depuis main.py au démarrage de l'application.
    """
    # Étape 8.1 — Créer le dossier keynotes si absent
    if not os.path.exists(CHEMIN_DOSSIER_KEYNOTES):
        os.makedirs(CHEMIN_DOSSIER_KEYNOTES)
        print(
            "✅ Dossier keynotes créé : "
            f"{CHEMIN_DOSSIER_KEYNOTES}"
        )
    else:
        print(
            "ℹ️  Dossier keynotes : "
            f"{CHEMIN_DOSSIER_KEYNOTES}"
        )


# ─────────────────────────────────────────────────────────────
# POINT D'ENTRÉE — VÉRIFICATION RAPIDE
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print(
        f"Application  : "
        f"{NOM_APPLICATION} v{VERSION_APPLICATION}"
    )
    print("-" * 50)
    print(f"Serveur BD   : {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}")
    print(f"Utilisateur  : {POSTGRES_CONFIG['user']}")
    print(f"Base données : {NOM_BD}")
    print(f"Dossier .txt : {CHEMIN_DOSSIER_KEYNOTES}")
    print(f"API          : {PREFIX_API}")
    print(f"Mode         : {'DATABASE_URL' if DATABASE_URL else 'variables individuelles'}")
    print("=" * 50)
    verifier_configuration()