"""
services/projets.py
-------------------
Logique métier — Projets.

Rôle :
    - Créer, afficher, modifier et supprimer les projets
    - Gérer le fichier .txt associé à chaque projet
    - Lister les projets et leurs utilisateurs

Importation :
    from app.services.projets import (
        creer_projet,
        afficher_projet,
        modifier_projet,
        supprimer_projet,
        lister_projets,
    )
"""

import os

from app.config import CHEMIN_DOSSIER_KEYNOTES
from app.database.connection import creer_connexion
from app.logger import get_logger
from app.repositories import projets as repo_projets
from app.repositories import acces as repo_acces


# Initialiser le logger pour ce module
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — CRÉATION D'UN PROJET
# ─────────────────────────────────────────────────────────────

def creer_projet(
    nom_projet    : str,
    id_super_admin: int,
) -> dict:
    """
    Crée un nouveau projet Revit vide.
    Réservé au super_admin uniquement.

    Args:
        nom_projet    : Nom du projet Revit
        id_super_admin: ID du super_admin créateur

    Returns:
        Dictionnaire avec les infos du projet créé

    Raises:
        ValueError: Si un projet avec ce nom existe déjà
    """
    connexion = creer_connexion()

    try:
        # Étape 1.1 — Vérifier l'unicité du nom
        projet_existant = repo_projets.obtenir_projet_par_nom(
            connexion, nom_projet.strip()
        )
        if projet_existant:
            raise ValueError(
                f"Un projet nommé '{nom_projet}' "
                "existe déjà."
            )

        # Étape 1.2 — Créer le projet en BD
        return repo_projets.inserer_projet(
            connexion,
            nom_projet.strip(),
            id_super_admin,
        )

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur créer projet : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — AFFICHAGE ET LISTAGE
# ─────────────────────────────────────────────────────────────

def afficher_projet(id_projet: int) -> dict:
    """
    Retourne les détails d'un projet avec la liste
    complète des utilisateurs ayant accès.

    Args:
        id_projet: ID du projet

    Returns:
        Dictionnaire avec infos projet + utilisateurs

    Raises:
        ValueError: Si le projet n'existe pas
    """
    connexion = creer_connexion()

    try:
        # Étape 2.1 — Récupérer les infos du projet
        projet = repo_projets.obtenir_projet_par_id(
            connexion, id_projet
        )
        if not projet:
            raise ValueError(
                f"Projet {id_projet} introuvable."
            )

        # Étape 2.2 — Récupérer les utilisateurs
        utilisateurs = (
            repo_acces.lister_utilisateurs_du_projet(
                connexion, id_projet
            )
        )

        projet["utilisateurs"] = utilisateurs
        return projet

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur afficher projet : {erreur}"
        )
        raise
    finally:
        connexion.close()


def lister_projets() -> list[dict]:
    """
    Retourne la liste de tous les projets existants.
    Triés par date de création décroissante.

    Returns:
        Liste des projets avec leurs infos de base
    """
    connexion = creer_connexion()

    try:
        # Étape 2.3 — Récupérer tous les projets
        return repo_projets.lister_projets(connexion)

    except Exception as erreur:
        logger.error(
            f"Erreur lister projets : {erreur}"
        )
        raise
    finally:
        connexion.close()


def lister_projets_utilisateur(
    id_utilisateur: int,
) -> list[dict]:
    """
    Retourne les projets accessibles par un utilisateur.

    Args:
        id_utilisateur: ID du utilisateur

    Returns:
        Liste des projets accessibles par l'utilisateur
    """
    connexion = creer_connexion()

    try:
        # Étape 2.4 — Récupérer les projets du utilisateur
        return repo_projets.lister_projets_par_utilisateur(
            connexion, id_utilisateur
        )

    except Exception as erreur:
        logger.error(
            f"Erreur lister projets utilisateur : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — MODIFICATION D'UN PROJET
# ─────────────────────────────────────────────────────────────

def modifier_projet(
    id_projet  : int,
    nouveau_nom: str,
) -> dict:
    """
    Renomme un projet existant.
    Renomme aussi le fichier .txt associé si il existe.

    Args:
        id_projet  : ID du projet à renommer
        nouveau_nom: Nouveau nom du projet

    Returns:
        Dictionnaire avec les infos mises à jour

    Raises:
        ValueError: Si le projet n'existe pas ou si le
                    nouveau nom est déjà utilisé
    """
    connexion = creer_connexion()

    try:
        # Étape 3.1 — Vérifier que le projet existe
        projet = repo_projets.obtenir_projet_par_id(
            connexion, id_projet
        )
        if not projet:
            raise ValueError(
                f"Projet {id_projet} introuvable."
            )

        # Étape 3.2 — Vérifier l'unicité du nouveau nom
        nouveau_nom_nettoye = nouveau_nom.strip()
        projet_existant = repo_projets.obtenir_projet_par_nom(
            connexion, nouveau_nom_nettoye
        )
        if projet_existant and (
            projet_existant["id"] != id_projet
        ):
            raise ValueError(
                f"Un projet nommé '{nouveau_nom_nettoye}' "
                "existe déjà."
            )

        # Étape 3.3 — Renommer le fichier .txt si présent
        """
        Si un fichier .txt existe pour ce projet,
        on le renomme pour rester cohérent avec le
        nouveau nom du projet.
        """
        ancien_nom_fichier = _construire_nom_fichier(
            projet["nom"]
        )
        nouveau_nom_fichier = _construire_nom_fichier(
            nouveau_nom_nettoye
        )

        ancien_chemin = os.path.join(
            CHEMIN_DOSSIER_KEYNOTES, ancien_nom_fichier
        )
        nouveau_chemin = os.path.join(
            CHEMIN_DOSSIER_KEYNOTES, nouveau_nom_fichier
        )

        if os.path.exists(ancien_chemin):
            os.rename(ancien_chemin, nouveau_chemin)
            logger.info(
                f"Fichier .txt renommé : "
                f"{ancien_nom_fichier} → "
                f"{nouveau_nom_fichier}"
            )

        # Étape 3.4 — Renommer le projet en BD
        return repo_projets.mettre_a_jour_nom_projet(
            connexion, id_projet, nouveau_nom_nettoye
        )

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur modifier projet : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — SUPPRESSION D'UN PROJET
# ─────────────────────────────────────────────────────────────

def supprimer_projet(id_projet: int) -> bool:
    """
    Supprime un projet et toutes ses données.
    Supprime aussi le fichier .txt associé si présent.
    Action irréversible — réservée au super_admin.

    Args:
        id_projet: ID du projet à supprimer

    Returns:
        True si la suppression a réussi

    Raises:
        ValueError: Si le projet n'existe pas
    """
    connexion = creer_connexion()

    try:
        # Étape 4.1 — Vérifier que le projet existe
        projet = repo_projets.obtenir_projet_par_id(
            connexion, id_projet
        )
        if not projet:
            raise ValueError(
                f"Projet {id_projet} introuvable."
            )

        # Étape 4.2 — Supprimer le fichier .txt si présent
        """
        On supprime le fichier avant la BD pour éviter
        d'avoir un fichier orphelin si la suppression BD
        échoue.
        """
        nom_fichier = _construire_nom_fichier(projet["nom"])
        chemin_fichier = os.path.join(
            CHEMIN_DOSSIER_KEYNOTES, nom_fichier
        )
        if os.path.exists(chemin_fichier):
            os.remove(chemin_fichier)
            logger.info(
                f"Fichier .txt supprimé : {nom_fichier}"
            )

        # Étape 4.3 — Supprimer le projet en BD
        """
        ON DELETE CASCADE supprime automatiquement :
        acces_projet, categories, notes, historique.
        """
        return repo_projets.supprimer_projet(
            connexion, id_projet
        )

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur supprimer projet : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 5 — FONCTIONS UTILITAIRES PRIVÉES
# ─────────────────────────────────────────────────────────────

def _construire_nom_fichier(nom_projet: str) -> str:
    """
    Construit le nom du fichier .txt à partir du nom
    du projet.

    Args:
        nom_projet: Nom du projet Revit

    Returns:
        Nom du fichier .txt (ex: keynotes_tour_montreal.txt)
    """
    # Étape 5.1 — Normaliser le nom pour le fichier
    """
    On remplace les espaces par des underscores et on
    supprime les caractères non autorisés dans un
    nom de fichier Windows.
    """
    nom_nettoye = nom_projet.lower().strip()
    nom_nettoye = nom_nettoye.replace(" ", "_")
    nom_nettoye = "".join(
        c for c in nom_nettoye
        if c.isalnum() or c == "_"
    )
    return f"keynotes_{nom_nettoye}.txt"