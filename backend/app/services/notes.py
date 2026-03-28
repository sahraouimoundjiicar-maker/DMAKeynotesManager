"""
services/notes.py
-----------------
Logique métier — Notes (keynotes).

Rôle :
    - Créer, modifier, supprimer et lister les notes
    - Valider l'unicité des numéros (notes + catégories)
    - Gérer le verrouillage optimiste
    - Rechercher les notes par numéro ou description
    - Filtrer les notes par catégorie
    - Enregistrer les actions dans l'historique

Importation :
    from app.services.notes import (
        creer_note,
        modifier_note,
        supprimer_note,
        lister_notes_categorie,
        lister_keynotes_projet,
        rechercher_keynotes,
    )
"""

from app.database.connection import creer_connexion
from app.logger import get_logger
from app.repositories import notes as repo_notes
from app.repositories import categories as repo_categories
from app.repositories import projets as repo_projets
from app.repositories import historique as repo_historique


# Initialiser le logger pour ce module
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — CRÉATION D'UNE NOTE
# ─────────────────────────────────────────────────────────────

def creer_note(
    id_projet    : int,
    id_categorie : int,
    numero       : str,
    description  : str,
    id_createur  : int,
    role_createur: str,
) -> dict:
    """
    Crée une nouvelle note obligatoirement liée à une
    catégorie existante. Vérifie l'unicité du numéro
    dans tout le projet (notes ET catégories).

    Args:
        id_projet    : ID du projet
        id_categorie : ID de la catégorie parente
        numero       : Numéro unique de la note
        description  : Description de la note
        id_createur  : ID de l'utilisateur créateur
        role_createur: Rôle de l'utilisateur créateur

    Returns:
        Dictionnaire avec les infos de la note créée

    Raises:
        ValueError: Si la catégorie n'existe pas ou si le
                    numéro est déjà utilisé dans le projet
    """
    connexion = creer_connexion()

    try:
        # Étape 1.1 — Vérifier que la catégorie existe
        """
        Une note ne peut pas exister sans catégorie.
        On vérifie que la catégorie appartient bien
        au projet pour éviter les injections croisées.
        """
        categorie = repo_categories.obtenir_categorie_par_id(
            connexion, id_categorie
        )
        if not categorie:
            raise ValueError(
                f"Catégorie {id_categorie} introuvable."
            )
        if categorie["id_projet"] != id_projet:
            raise ValueError(
                "La catégorie n'appartient pas "
                "à ce projet."
            )

        # Étape 1.2 — Vérifier l'unicité du numéro
        """
        Le numéro doit être unique dans tout le projet :
        pas de doublon ni avec les notes ni avec
        les catégories existantes.
        """
        numero_disponible = (
            repo_notes.verifier_numero_note_unique(
                connexion, id_projet, numero
            )
        )
        if not numero_disponible:
            raise ValueError(
                f"Le numéro '{numero}' est déjà utilisé "
                "dans ce projet."
            )

        # Étape 1.3 — Créer la note
        note = repo_notes.inserer_note(
            connexion,
            id_projet,
            id_categorie,
            numero,
            description,
            id_createur,
        )

        # Étape 1.4 — Enregistrer dans l'historique
        repo_historique.inserer_historique(
            connexion,
            id_projet        = id_projet,
            table_cible      = "notes",
            action           = "creation",
            effectue_par_id  = id_createur,
            effectue_par_role= role_createur,
            id_cible         = note["id"],
            nouvelle_valeur  = (
                f"{numero} — {description}"
            ),
        )

        # Étape 1.5 — Marquer le fichier .txt comme périmé
        repo_projets.mettre_a_jour_txt_a_jour(
            connexion, id_projet, False
        )

        return note

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur créer note : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — MODIFICATION D'UNE NOTE
# ─────────────────────────────────────────────────────────────

def modifier_note(
    id_projet        : int,
    id_note          : int,
    version_actuelle : int,
    id_modificateur  : int,
    role_modificateur: str,
    nouveau_numero   : str | None = None,
    nouvelle_desc    : str | None = None,
) -> dict:
    """
    Modifie une note avec verrouillage optimiste.
    Si deux utilisateurs modifient la même note
    simultanément, le second reçoit un message d'erreur
    clair lui demandant de recharger.

    Args:
        id_projet        : ID du projet
        id_note          : ID de la note
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
                repo_notes.verifier_numero_note_unique(
                    connexion,
                    id_projet,
                    nouveau_numero,
                    exclure_id=id_note,
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
        ancienne_note = repo_notes.obtenir_note_par_id(
            connexion, id_note
        )

        # Étape 2.3 — Mettre à jour la note
        note_modifiee = repo_notes.mettre_a_jour_note(
            connexion,
            id_note,
            version_actuelle,
            id_modificateur,
            nouveau_numero,
            nouvelle_desc,
        )

        # Étape 2.4 — Enregistrer dans l'historique
        ancienne_valeur = (
            f"{ancienne_note['numero']} — "
            f"{ancienne_note['description']}"
        )
        nouvelle_valeur = (
            f"{note_modifiee['numero']} — "
            f"{note_modifiee['description']}"
        )
        repo_historique.inserer_historique(
            connexion,
            id_projet        = id_projet,
            table_cible      = "notes",
            action           = "modification",
            effectue_par_id  = id_modificateur,
            effectue_par_role= role_modificateur,
            id_cible         = id_note,
            ancienne_valeur  = ancienne_valeur,
            nouvelle_valeur  = nouvelle_valeur,
        )

        # Étape 2.5 — Marquer le fichier .txt comme périmé
        repo_projets.mettre_a_jour_txt_a_jour(
            connexion, id_projet, False
        )

        return note_modifiee

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur modifier note : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — SUPPRESSION D'UNE NOTE
# ─────────────────────────────────────────────────────────────

def supprimer_note(
    id_projet        : int,
    id_note          : int,
    id_modificateur  : int,
    role_modificateur: str,
) -> bool:
    """
    Supprime une note spécifique sans affecter les
    autres notes de la catégorie.

    Args:
        id_projet        : ID du projet
        id_note          : ID de la note à supprimer
        id_modificateur  : ID de l'utilisateur qui supprime
        role_modificateur: Rôle de l'utilisateur

    Returns:
        True si la suppression a réussi

    Raises:
        ValueError: Si la note n'existe pas
    """
    connexion = creer_connexion()

    try:
        # Étape 3.1 — Récupérer les infos de la note
        note = repo_notes.obtenir_note_par_id(
            connexion, id_note
        )
        if not note:
            raise ValueError(
                f"Note {id_note} introuvable."
            )

        # Étape 3.2 — Enregistrer dans l'historique
        repo_historique.inserer_historique(
            connexion,
            id_projet        = id_projet,
            table_cible      = "notes",
            action           = "suppression",
            effectue_par_id  = id_modificateur,
            effectue_par_role= role_modificateur,
            id_cible         = id_note,
            ancienne_valeur  = (
                f"{note['numero']} — "
                f"{note['description']}"
            ),
        )

        # Étape 3.3 — Supprimer la note
        resultat = repo_notes.supprimer_note(
            connexion, id_note
        )

        # Étape 3.4 — Marquer le fichier .txt comme périmé
        repo_projets.mettre_a_jour_txt_a_jour(
            connexion, id_projet, False
        )

        return resultat

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur supprimer note : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — LISTAGE ET RECHERCHE
# ─────────────────────────────────────────────────────────────

def lister_notes_categorie(
    id_categorie: int,
) -> list[dict]:
    """
    Retourne toutes les notes d'une catégorie.

    Args:
        id_categorie: ID de la catégorie

    Returns:
        Liste des notes de la catégorie
    """
    connexion = creer_connexion()

    try:
        # Étape 4.1 — Récupérer les notes d'une catégorie
        return repo_notes.lister_notes_de_categorie(
            connexion, id_categorie
        )

    except Exception as erreur:
        logger.error(
            f"Erreur lister notes catégorie : {erreur}"
        )
        raise
    finally:
        connexion.close()


def lister_keynotes_projet(
    id_projet    : int,
    id_categorie : int | None = None,
) -> list[dict]:
    """
    Retourne toutes les notes d'un projet avec les
    informations de leurs catégories.
    Filtre optionnel par catégorie via menu déroulant.

    Args:
        id_projet   : ID du projet
        id_categorie: Filtre optionnel par catégorie

    Returns:
        Liste des notes avec infos catégorie
    """
    connexion = creer_connexion()

    try:
        # Étape 4.2 — Récupérer les keynotes du projet
        return repo_notes.lister_keynotes_du_projet(
            connexion, id_projet, id_categorie
        )

    except Exception as erreur:
        logger.error(
            f"Erreur lister keynotes projet : {erreur}"
        )
        raise
    finally:
        connexion.close()


def rechercher_keynotes(
    id_projet    : int,
    terme        : str,
    id_categorie : int | None = None,
) -> list[dict]:
    """
    Recherche des notes par numéro ou description.
    Insensible à la casse et aux accents (ILIKE).

    Args:
        id_projet   : ID du projet
        terme       : Terme de recherche
        id_categorie: Filtre optionnel par catégorie

    Returns:
        Liste des notes correspondant à la recherche
    """
    connexion = creer_connexion()

    try:
        # Étape 4.3 — Rechercher les notes
        return repo_notes.rechercher_notes(
            connexion, id_projet, terme, id_categorie
        )

    except Exception as erreur:
        logger.error(
            f"Erreur rechercher keynotes : {erreur}"
        )
        raise
    finally:
        connexion.close()