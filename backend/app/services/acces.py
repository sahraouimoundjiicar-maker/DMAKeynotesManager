"""
services/acces.py
-----------------
Logique métier — Accès projets.

Rôle :
    - Attribuer l'accès d'un utilisateur à un projet
    - Retirer l'accès d'un utilisateur à un projet
    - Vérifier si un utilisateur a accès à un projet

Importation :
    from app.services.acces import (
        attribuer_acces,
        retirer_acces,
        verifier_acces_projet,
    )
"""

from app.database.connection import creer_connexion
from app.logger import get_logger
from app.repositories import acces as repo_acces
from app.repositories import projets as repo_projets
from app.repositories import utilisateurs as repo_utilisateurs


# Initialiser le logger pour ce module
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — ATTRIBUTION D'ACCÈS
# ─────────────────────────────────────────────────────────────

def attribuer_acces(
    id_projet     : int,
    id_utilisateur: int,
    id_super_admin: int,
) -> dict:
    """
    Donne l'accès à un utilisateur pour un projet.
    Réservé au super_admin uniquement.

    Args:
        id_projet     : ID du projet
        id_utilisateur: ID du utilisateur
        id_super_admin: ID du super_admin qui attribue

    Returns:
        Dictionnaire avec les infos de l'accès créé

    Raises:
        ValueError: Si le projet ou l'utilisateur n'existe
                    pas, ou si l'accès existe déjà,
                    ou si l'utilisateur n'est pas approuvé
    """
    connexion = creer_connexion()

    try:
        # Étape 1.1 — Vérifier que le projet existe
        projet = repo_projets.obtenir_projet_par_id(
            connexion, id_projet
        )
        if not projet:
            raise ValueError(
                f"Projet {id_projet} introuvable."
            )

        # Étape 1.2 — Vérifier que l'utilisateur existe
        utilisateur = (
            repo_utilisateurs.obtenir_utilisateur_par_id(
                connexion, id_utilisateur
            )
        )
        if not utilisateur:
            raise ValueError(
                f"Utilisateur {id_utilisateur} introuvable."
            )

        # Étape 1.3 — Vérifier que le compte est approuvé
        """
        Un utilisateur non approuvé ne peut pas
        recevoir d'accès à un projet.
        """
        if utilisateur["statut"] != "approuve":
            raise ValueError(
                "Impossible d'attribuer un accès à un "
                "compte non approuvé."
            )

        # Étape 1.4 — Vérifier que l'accès n'existe pas
        acces_existant = repo_acces.verifier_acces_existant(
            connexion, id_projet, id_utilisateur
        )
        if acces_existant:
            raise ValueError(
                f"L'utilisateur {id_utilisateur} a déjà "
                f"accès au projet {id_projet}."
            )

        # Étape 1.5 — Attribuer l'accès
        return repo_acces.inserer_acces(
            connexion,
            id_projet,
            id_utilisateur,
            id_super_admin,
        )

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur attribuer accès : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — RETRAIT D'ACCÈS
# ─────────────────────────────────────────────────────────────

def retirer_acces(
    id_projet     : int,
    id_utilisateur: int,
) -> bool:
    """
    Retire l'accès d'un utilisateur à un projet.
    Réservé au super_admin uniquement.

    Args:
        id_projet     : ID du projet
        id_utilisateur: ID du utilisateur

    Returns:
        True si le retrait a réussi

    Raises:
        ValueError: Si l'accès n'existe pas
    """
    connexion = creer_connexion()

    try:
        # Étape 2.1 — Vérifier que l'accès existe
        acces_existant = repo_acces.verifier_acces_existant(
            connexion, id_projet, id_utilisateur
        )
        if not acces_existant:
            raise ValueError(
                f"L'utilisateur {id_utilisateur} n'a pas "
                f"accès au projet {id_projet}."
            )

        # Étape 2.2 — Retirer l'accès
        return repo_acces.supprimer_acces(
            connexion, id_projet, id_utilisateur
        )

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur retirer accès : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — VÉRIFICATION D'ACCÈS
# ─────────────────────────────────────────────────────────────

def verifier_acces_projet(
    id_projet     : int,
    id_utilisateur: int,
) -> bool:
    """
    Vérifie si un utilisateur a accès à un projet.
    Utilisée par la dépendance FastAPI verifier_acces_projet
    pour protéger les routes keynotes.

    Args:
        id_projet     : ID du projet
        id_utilisateur: ID du utilisateur

    Returns:
        True si l'utilisateur a accès, False sinon
    """
    connexion = creer_connexion()

    try:
        # Étape 3.1 — Vérifier l'accès en BD
        return repo_acces.verifier_acces_utilisateur(
            connexion, id_projet, id_utilisateur
        )

    except Exception as erreur:
        logger.error(
            f"Erreur vérifier accès projet : {erreur}"
        )
        raise
    finally:
        connexion.close()