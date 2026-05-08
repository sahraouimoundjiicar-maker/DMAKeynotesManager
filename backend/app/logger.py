"""
logger.py
---------
Configuration centrale du logging — DMAKeynotesManager.

Rôle :
    Fournir un logger configuré et réutilisable
    à tous les modules de l'application.
    Écrit les logs dans la console ET dans un fichier.

Utilisation dans les autres modules :
    from app.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Utilisateur créé : john@exemple.com")
    logger.warning("Login échoué : john@exemple.com")
    logger.error("Erreur BD : connexion refusée")

Niveaux de log utilisés :
    INFO    → actions normales (création, connexion, export)
    WARNING → situations anormales non critiques
    ERROR   → erreurs critiques nécessitant une attention
"""

import logging


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — CONSTANTES DE CONFIGURATION...
# ─────────────────────────────────────────────────────────────

# Étape 1.1 — Format des messages de log
"""
Format choisi pour faciliter la lecture et le débogage.

Exemple de sortie :
2026-03-14 10:30:00 | INFO     | app.services.auth | Connecté
2026-03-14 10:31:00 | WARNING  | app.services.auth | Échec
2026-03-14 10:32:00 | ERROR    | app.database      | Erreur BD
"""
FORMAT_LOG = (
    "%(asctime)s | %(levelname)-8s | "
    "%(name)s | %(message)s"
)

# Étape 1.2 — Format de la date dans les logs
FORMAT_DATE = "%Y-%m-%d %H:%M:%S"

# Étape 1.3 — Nom du fichier de log
"""
Le fichier est créé à la racine du projet.
Il est ignoré par Git grâce au .gitignore.
Le mode 'a' (append) conserve les logs existants
entre les redémarrages de l'application.
"""
NOM_FICHIER_LOG = "dma_keynotes.log"


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — CRÉATION DES HANDLERS
# ─────────────────────────────────────────────────────────────

def creer_formateur() -> logging.Formatter:
    """
    Crée et retourne le formateur de logs.
    Partagé entre tous les handlers pour uniformité.

    Returns:
        Formateur configuré avec le format et la date
    """
    return logging.Formatter(
        FORMAT_LOG,
        datefmt=FORMAT_DATE
    )


def creer_handler_console() -> logging.StreamHandler:
    """
    Crée un handler pour afficher les logs en console.
    Utile pendant le développement pour voir les logs
    directement dans le terminal.

    Returns:
        Handler configuré pour la console
    """
    # Étape 2.1 — Créer et configurer le handler console
    handler_console = logging.StreamHandler()
    handler_console.setLevel(logging.INFO)
    handler_console.setFormatter(creer_formateur())
    return handler_console


def creer_handler_fichier() -> logging.FileHandler:
    """
    Crée un handler pour écrire les logs dans un fichier.
    Le fichier est créé automatiquement s'il n'existe pas.

    Returns:
        Handler configuré pour le fichier de log
    """
    # Étape 2.2 — Créer et configurer le handler fichier
    """
    encoding='utf-8' pour supporter les caractères
    français dans les messages de log.
    """
    handler_fichier = logging.FileHandler(
        NOM_FICHIER_LOG,
        mode     = "a",
        encoding = "utf-8",
    )
    handler_fichier.setLevel(logging.INFO)
    handler_fichier.setFormatter(creer_formateur())
    return handler_fichier


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — CONFIGURATION GLOBALE
# ─────────────────────────────────────────────────────────────

def configurer_logging() -> None:
    """
    Configure le système de logging global.
    Appelée une seule fois au démarrage via main.py.

    Ajoute les handlers console et fichier au logger
    racine dont tous les modules héritent automatiquement.
    """
    # Étape 3.1 — Récupérer le logger racine
    logger_racine = logging.getLogger()
    logger_racine.setLevel(logging.INFO)

    # Étape 3.2 — Éviter les handlers dupliqués
    """
    En mode --reload de uvicorn, configurer_logging()
    peut être appelée plusieurs fois.
    On vérifie que les handlers ne sont pas déjà ajoutés.
    """
    if logger_racine.handlers:
        return

    # Étape 3.3 — Ajouter les deux handlers
    logger_racine.addHandler(creer_handler_console())
    logger_racine.addHandler(creer_handler_fichier())


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — FONCTION PUBLIQUE D'ACCÈS AU LOGGER
# ─────────────────────────────────────────────────────────────

def get_logger(nom_module: str) -> logging.Logger:
    """
    Retourne un logger configuré pour le module appelant.
    Doit être appelé en haut de chaque module.

    Args:
        nom_module: Nom du module — toujours passer __name__

    Returns:
        Logger prêt à l'emploi

    Exemple :
        from app.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Projet créé avec succès")
    """
    # Étape 4.1 — S'assurer que le logging est configuré
    configurer_logging()

    # Étape 4.2 — Retourner le logger du module
    return logging.getLogger(nom_module)


# ─────────────────────────────────────────────────────────────
# POINT D'ENTRÉE — TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger = get_logger(__name__)
    logger.info("✅ Niveau INFO fonctionne")
    logger.warning("⚠️  Niveau WARNING fonctionne")
    logger.error("❌ Niveau ERROR fonctionne")
    print(f"\n📄 Logs écrits dans : {NOM_FICHIER_LOG}")