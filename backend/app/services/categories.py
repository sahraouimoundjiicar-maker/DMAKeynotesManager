"""
services/categories.py
----------------------
Logique métier — Catégories.

Rôle :
    - Créer, modifier, supprimer et lister les catégories
    - Valider l'unicité des numéros (catégories + notes)
    - Gérer le verrouillage optimiste
    - Bloquer la suppression si la catégorie contient des notes
    - Enregistrer les actions dans l'historique

Importation :
    from app.services.categories import (
        creer_categorie,
        modifier_categorie,
        supprimer_categorie,
        lister_categories,
    )
"""

from app.database.connection import creer_connexion
from app.logger import get_logger
from app.repositories import categories as repo_categories
from app.repositories import projets as repo_projets
from app.repositories import historique as repo_historique


# Initialiser le logger pour ce module
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — CRÉATION D'UNE CATÉGORIE
# ─────────────────────────────────────────────────────────────

def creer_categorie(
    id_projet   : int,
    numero      : str,
    description : str,
    id_createur : int,
    role_createur: str,
) -> dict:
    """
    Crée une nouvelle catégorie dans un projet.
    Vérifie l'unicité du numéro dans tout le projet
    (catégories ET notes).

    Args:
        id_projet    : ID du projet
        numero       : Numéro unique de la catégorie
        description  : Description de la catégorie
        id_createur  : ID de l'utilisateur créateur
        role_createur: Rôle de l'utilisateur créateur

    Returns:
        Dictionnaire avec les infos de la catégorie créée

    Raises:
        ValueError: Si le numéro existe déjà dans le projet
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

        # Étape 1.2 — Vérifier l'unicité du numéro
        """
        Le numéro doit être unique dans tout le projet :
        pas de doublon ni avec les catégories ni avec
        les notes existantes.
        """
        numero_disponible = (
            repo_categories.verifier_numero_categorie_unique(
                connexion, id_projet, numero
            )
        )
        if not numero_disponible:
            raise ValueError(
                f"Le numéro '{numero}' est déjà utilisé "
                "dans ce projet."
            )

        # Étape 1.4 — Créer la catégorie
        categorie = repo_categories.inserer_categorie(
            connexion,
            id_projet,
            numero,
            description,
            id_createur,
        )

        # Étape 1.5 — Enregistrer dans l'historique
        repo_historique.inserer_historique(
            connexion,
            id_projet        = id_projet,
            table_cible      = "categories",
            action           = "creation",
            effectue_par_id  = id_createur,
            effectue_par_role= role_createur,
            id_cible         = categorie["id"],
            nouvelle_valeur  = (
                f"{numero} — {description}"
            ),
        )

        # Étape 1.6 — Marquer le fichier .txt comme périmé
        repo_projets.mettre_a_jour_txt_a_jour(
            connexion, id_projet, False
        )

        return categorie

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur créer catégorie : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — MODIFICATION D'UNE CATÉGORIE
# ─────────────────────────────────────────────────────────────

def modifier_categorie(
    id_projet       : int,
    id_categorie    : int,
    version_actuelle: int,
    id_modificateur : int,
    role_modificateur: str,
    nouveau_numero  : str | None = None,
    nouvelle_desc   : str | None = None,
) -> dict:
    """
    Modifie une catégorie avec verrouillage optimiste.
    Détecte les modifications simultanées entre
    utilisateurs et retourne une erreur claire.

    Args:
        id_projet        : ID du projet
        id_categorie     : ID de la catégorie
        version_actuelle : Version au moment de l'ouverture
        id_modificateur  : ID de l'utilisateur modificateur
        role_modificateur: Rôle de l'utilisateur modificateur
        nouveau_numero   : Nouveau numéro (optionnel)
        nouvelle_desc    : Nouvelle description (optionnel)

    Returns:
        Dictionnaire avec les infos mises à jour

    Raises:
        ValueError: Si conflit de version détecté
                    ou numéro déjà utilisé
    """
    connexion = creer_connexion()

    try:
        # Étape 2.1 — Vérifier l'unicité du nouveau numéro
        if nouveau_numero:
            numero_disponible = (
                repo_categories
                .verifier_numero_categorie_unique(
                    connexion,
                    id_projet,
                    nouveau_numero,
                    exclure_id=id_categorie,
                )
            )
            if not numero_disponible:
                raise ValueError(
                    f"Le numéro '{nouveau_numero}' est "
                    "déjà utilisé dans ce projet."
                )

        # Étape 2.2 — Récupérer l'ancienne valeur
        """
        On sauvegarde l'ancienne valeur pour l'historique
        avant d'effectuer la modification.
        """
        ancienne_categorie = (
            repo_categories.obtenir_categorie_par_id(
                connexion, id_categorie
            )
        )

        # Étape 2.3 — Mettre à jour la catégorie
        categorie_modifiee = (
            repo_categories.mettre_a_jour_categorie(
                connexion,
                id_categorie,
                version_actuelle,
                id_modificateur,
                nouveau_numero,
                nouvelle_desc,
            )
        )

        # Étape 2.4 — Enregistrer dans l'historique
        ancienne_valeur = (
            f"{ancienne_categorie['numero']} — "
            f"{ancienne_categorie['description']}"
        )
        nouvelle_valeur = (
            f"{categorie_modifiee['numero']} — "
            f"{categorie_modifiee['description']}"
        )
        repo_historique.inserer_historique(
            connexion,
            id_projet        = id_projet,
            table_cible      = "categories",
            action           = "modification",
            effectue_par_id  = id_modificateur,
            effectue_par_role= role_modificateur,
            id_cible         = id_categorie,
            ancienne_valeur  = ancienne_valeur,
            nouvelle_valeur  = nouvelle_valeur,
        )

        # Étape 2.5 — Marquer le fichier .txt comme périmé
        repo_projets.mettre_a_jour_txt_a_jour(
            connexion, id_projet, False
        )

        return categorie_modifiee

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur modifier catégorie : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — SUPPRESSION D'UNE CATÉGORIE
# ─────────────────────────────────────────────────────────────

def supprimer_categorie(
    id_projet       : int,
    id_categorie    : int,
    id_modificateur : int,
    role_modificateur: str,
) -> bool:
    """
    Supprime une catégorie uniquement si elle est vide.
    Retourne une erreur claire si elle contient des notes.

    Args:
        id_projet        : ID du projet
        id_categorie     : ID de la catégorie
        id_modificateur  : ID de l'utilisateur qui supprime
        role_modificateur: Rôle de l'utilisateur

    Returns:
        True si la suppression a réussi

    Raises:
        ValueError: Si la catégorie contient des notes
    """
    connexion = creer_connexion()

    try:
        # Étape 3.1 — Récupérer les infos de la catégorie
        categorie = repo_categories.obtenir_categorie_par_id(
            connexion, id_categorie
        )
        if not categorie:
            raise ValueError(
                f"Catégorie {id_categorie} introuvable."
            )

        # Étape 3.2 — Vérifier que la catégorie est vide
        """
        On compte les notes avant de supprimer.
        Si la catégorie n'est pas vide, on retourne un
        message clair pour guider l'utilisateur.
        """
        nombre_notes = (
            repo_categories.compter_notes_de_categorie(
                connexion, id_categorie
            )
        )
        if nombre_notes > 0:
            raise ValueError(
                f"Impossible de supprimer la catégorie "
                f"'{categorie['numero']}' : elle contient "
                f"{nombre_notes} note(s). Veuillez d'abord "
                "supprimer toutes les notes."
            )

        # Étape 3.3 — Enregistrer dans l'historique
        repo_historique.inserer_historique(
            connexion,
            id_projet        = id_projet,
            table_cible      = "categories",
            action           = "suppression",
            effectue_par_id  = id_modificateur,
            effectue_par_role= role_modificateur,
            id_cible         = id_categorie,
            ancienne_valeur  = (
                f"{categorie['numero']} — "
                f"{categorie['description']}"
            ),
        )

        # Étape 3.4 — Supprimer la catégorie
        resultat = repo_categories.supprimer_categorie(
            connexion, id_categorie
        )

        # Étape 3.5 — Marquer le fichier .txt comme périmé
        repo_projets.mettre_a_jour_txt_a_jour(
            connexion, id_projet, False
        )

        return resultat

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur supprimer catégorie : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — LISTAGE DES CATÉGORIES
# ─────────────────────────────────────────────────────────────

def lister_categories(id_projet: int) -> list[dict]:
    """
    Retourne toutes les catégories d'un projet avec
    le nombre de notes associées à chacune.

    Args:
        id_projet: ID du projet

    Returns:
        Liste des catégories avec nombre_notes
    """
    connexion = creer_connexion()

    try:
        # Étape 4.1 — Récupérer les catégories du projet
        return repo_categories.lister_categories_du_projet(
            connexion, id_projet
        )

    except Exception as erreur:
        logger.error(
            f"Erreur lister catégories : {erreur}"
        )
        raise
    finally:
        connexion.close()