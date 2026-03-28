"""
services/utilisateurs.py
------------------------
Logique métier — Utilisateurs.

Rôle :
    - Gérer le CRUD des utilisateurs
    - Approuver ou refuser les inscriptions
    - Approuver ou refuser les reinitialisations mdp
    - Afficher les détails d'un utilisateur avec ses projets

Importation :
    from app.services.utilisateurs import (
        afficher_utilisateur,
        modifier_utilisateur,
        supprimer_utilisateur,
        lister_utilisateurs,
        approuver_utilisateur,
        refuser_utilisateur,
    )
"""

from app.database.connection import creer_connexion
from app.logger import get_logger
from app.repositories import utilisateurs as repo_utilisateurs
from app.repositories import projets as repo_projets
from app.services.auth import hacher_mot_de_passe


# Initialiser le logger pour ce module
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — AFFICHAGE ET LISTAGE
# ─────────────────────────────────────────────────────────────

def afficher_utilisateur(id_utilisateur: int) -> dict:
    """
    Retourne les détails d'un utilisateur avec
    la liste de tous les projets auxquels il a accès.

    Args:
        id_utilisateur: ID du utilisateur

    Returns:
        Dictionnaire avec infos + projets accessibles

    Raises:
        ValueError: Si l'utilisateur n'existe pas
    """
    connexion = creer_connexion()

    try:
        # Étape 1.1 — Récupérer les infos du utilisateur
        utilisateur = (
            repo_utilisateurs.obtenir_utilisateur_par_id(
                connexion, id_utilisateur
            )
        )
        if not utilisateur:
            raise ValueError(
                f"Utilisateur {id_utilisateur} introuvable."
            )

        # Étape 1.2 — Récupérer ses projets accessibles
        projets_accessibles = (
            repo_projets.lister_projets_par_utilisateur(
                connexion, id_utilisateur
            )
        )

        utilisateur["projets_accessibles"] = (
            projets_accessibles
        )
        return utilisateur

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur afficher utilisateur : {erreur}"
        )
        raise
    finally:
        connexion.close()


def lister_utilisateurs() -> list[dict]:
    """
    Retourne la liste de tous les utilisateurs.
    Les mots de passe ne sont jamais inclus.

    Returns:
        Liste des utilisateurs avec leurs infos de base
    """
    connexion = creer_connexion()

    try:
        # Étape 1.3 — Récupérer tous les utilisateurs
        return repo_utilisateurs.lister_utilisateurs(
            connexion
        )

    except Exception as erreur:
        logger.error(
            f"Erreur lister utilisateurs : {erreur}"
        )
        raise
    finally:
        connexion.close()


def lister_demandes_en_attente() -> list[dict]:
    """
    Retourne les utilisateurs en attente d'approbation.
    Utilisée par le super_admin pour gérer les inscriptions.

    Returns:
        Liste des utilisateurs avec statut 'en_attente'
    """
    connexion = creer_connexion()

    try:
        # Étape 1.4 — Récupérer les demandes en attente
        return (
            repo_utilisateurs
            .lister_utilisateurs_en_attente(connexion)
        )

    except Exception as erreur:
        logger.error(
            f"Erreur lister demandes : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — MODIFICATION
# ─────────────────────────────────────────────────────────────

def modifier_utilisateur(
    id_utilisateur : int,
    nouveau_nom    : str | None = None,
    nouveau_prenom : str | None = None,
    nouveau_email  : str | None = None,
    nouveau_mdp    : str | None = None,
) -> dict:
    """
    Modifie les champs fournis d'un utilisateur.
    Seuls les champs non nuls sont mis à jour.

    Args:
        id_utilisateur: ID du utilisateur
        nouveau_nom   : Nouveau nom (optionnel)
        nouveau_prenom: Nouveau prénom (optionnel)
        nouveau_email : Nouvel email (optionnel)
        nouveau_mdp   : Nouveau mot de passe (optionnel)

    Returns:
        Dictionnaire avec les infos mises à jour

    Raises:
        ValueError: Si l'utilisateur n'existe pas
                    ou l'email est déjà utilisé
    """
    connexion = creer_connexion()

    try:
        # Étape 2.1 — Vérifier que l'utilisateur existe
        utilisateur = (
            repo_utilisateurs.obtenir_utilisateur_par_id(
                connexion, id_utilisateur
            )
        )
        if not utilisateur:
            raise ValueError(
                f"Utilisateur {id_utilisateur} introuvable."
            )

        # Étape 2.2 — Vérifier l'unicité du nouvel email
        if nouveau_email:
            email_normalise = nouveau_email.lower().strip()
            existant = (
                repo_utilisateurs
                .obtenir_utilisateur_par_email(
                    connexion, email_normalise
                )
            )
            if existant and existant["id"] != id_utilisateur:
                raise ValueError(
                    f"L'email '{email_normalise}' "
                    "est déjà utilisé."
                )

        # Étape 2.3 — Construire les champs à modifier
        """
        On ne met à jour que les champs fournis.
        Le strip() garantit la propreté des données.
        """
        champs = {}
        if nouveau_nom:
            champs["nom"] = nouveau_nom.strip()
        if nouveau_prenom:
            champs["prenom"] = nouveau_prenom.strip()
        if nouveau_email:
            champs["email"] = nouveau_email.lower().strip()
        if nouveau_mdp:
            champs["mot_de_passe_hash"] = (
                hacher_mot_de_passe(nouveau_mdp)
            )

        if not champs:
            raise ValueError(
                "Aucun champ à modifier n'a été fourni."
            )

        # Étape 2.4 — Mettre à jour l'utilisateur
        return repo_utilisateurs.mettre_a_jour_utilisateur(
            connexion, id_utilisateur, champs
        )

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur modifier utilisateur : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — SUPPRESSION
# ─────────────────────────────────────────────────────────────

def supprimer_utilisateur(id_utilisateur: int) -> bool:
    """
    Supprime un utilisateur de la BD.
    Les keynotes créés par cet utilisateur sont conservés
    grâce au ON DELETE SET NULL sur cree_par et
    modifie_par_id dans les tables categories et notes.

    Args:
        id_utilisateur: ID du utilisateur à supprimer

    Returns:
        True si la suppression a réussi

    Raises:
        ValueError: Si l'utilisateur n'existe pas
    """
    connexion = creer_connexion()

    try:
        # Étape 3.1 — Vérifier que l'utilisateur existe
        utilisateur = (
            repo_utilisateurs.obtenir_utilisateur_par_id(
                connexion, id_utilisateur
            )
        )
        if not utilisateur:
            raise ValueError(
                f"Utilisateur {id_utilisateur} introuvable."
            )

        # Étape 3.2 — Supprimer l'utilisateur
        """
        ON DELETE CASCADE sur reinitialisation_mdp et
        acces_projet supprime automatiquement les
        enregistrements liés.
        ON DELETE SET NULL sur categories.cree_par et
        notes.cree_par conserve les keynotes.
        """
        return repo_utilisateurs.supprimer_utilisateur(
            connexion, id_utilisateur
        )

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur supprimer utilisateur : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — APPROBATION ET REFUS
# ─────────────────────────────────────────────────────────────

def approuver_utilisateur(id_utilisateur: int) -> dict:
    """
    Approuve l'inscription d'un utilisateur.
    Change le statut de 'en_attente' à 'approuve'.
    Le utilisateur peut ensuite se connecter.

    Args:
        id_utilisateur: ID du utilisateur à approuver

    Returns:
        Dictionnaire avec les infos mises à jour

    Raises:
        ValueError: Si l'utilisateur n'existe pas
                    ou n'est pas en attente
    """
    connexion = creer_connexion()

    try:
        # Étape 4.1 — Vérifier que l'utilisateur existe
        utilisateur = (
            repo_utilisateurs.obtenir_utilisateur_par_id(
                connexion, id_utilisateur
            )
        )
        if not utilisateur:
            raise ValueError(
                f"Utilisateur {id_utilisateur} introuvable."
            )

        # Étape 4.2 — Vérifier le statut
        if utilisateur["statut"] != "en_attente":
            raise ValueError(
                "Cet utilisateur n'est pas en attente "
                "d'approbation."
            )

        # Étape 4.3 — Approuver le compte
        repo_utilisateurs.mettre_a_jour_statut_utilisateur(
            connexion, id_utilisateur, "approuve"
        )

        logger.info(
            f"Utilisateur {id_utilisateur} approuvé."
        )

        return repo_utilisateurs.obtenir_utilisateur_par_id(
            connexion, id_utilisateur
        )

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur approuver utilisateur : {erreur}"
        )
        raise
    finally:
        connexion.close()


def refuser_utilisateur(id_utilisateur: int) -> bool:
    """
    Refuse et supprime le compte d'un utilisateur.
    Le compte est définitivement supprimé de la BD.

    Args:
        id_utilisateur: ID du utilisateur à refuser

    Returns:
        True si le refus et la suppression ont réussi

    Raises:
        ValueError: Si l'utilisateur n'existe pas
    """
    connexion = creer_connexion()

    try:
        # Étape 4.4 — Vérifier que l'utilisateur existe
        utilisateur = (
            repo_utilisateurs.obtenir_utilisateur_par_id(
                connexion, id_utilisateur
            )
        )
        if not utilisateur:
            raise ValueError(
                f"Utilisateur {id_utilisateur} introuvable."
            )

        # Étape 4.5 — Supprimer le compte refusé
        """
        On supprime directement le compte plutôt que
        de le passer à 'refuse' — un compte refusé
        n'a pas de raison d'être conservé.
        """
        repo_utilisateurs.supprimer_utilisateur(
            connexion, id_utilisateur
        )

        logger.info(
            f"Utilisateur {id_utilisateur} refusé "
            f"et supprimé."
        )
        return True

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur refuser utilisateur : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 5 — RÉINITIALISATION MOT DE PASSE
# ─────────────────────────────────────────────────────────────

def lister_demandes_reinitialisation() -> list[dict]:
    """
    Retourne les demandes de réinitialisation en attente.
    Utilisée par le super_admin pour les approuver ou refuser.

    Returns:
        Liste des demandes en attente avec infos utilisateur
    """
    connexion = creer_connexion()

    try:
        # Étape 5.1 — Récupérer les demandes en attente
        return (
            repo_utilisateurs
            .lister_demandes_reinitialisation(connexion)
        )

    except Exception as erreur:
        logger.error(
            f"Erreur lister demandes reset : {erreur}"
        )
        raise
    finally:
        connexion.close()


def approuver_reinitialisation(
    id_utilisateur: int
) -> bool:
    """
    Approuve la demande de réinitialisation et applique
    le nouveau mot de passe haché à l'utilisateur.

    Args:
        id_utilisateur: ID du utilisateur

    Returns:
        True si l'approbation a réussi

    Raises:
        ValueError: Si aucune demande n'est en attente
    """
    connexion = creer_connexion()

    try:
        # Étape 5.2 — Approuver et appliquer le nouveau mdp
        return repo_utilisateurs.approuver_reinitialisation(
            connexion, id_utilisateur
        )

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur approuver reset mdp : {erreur}"
        )
        raise
    finally:
        connexion.close()


def refuser_reinitialisation(id_utilisateur: int) -> bool:
    """
    Refuse et supprime la demande de réinitialisation.

    Args:
        id_utilisateur: ID du utilisateur

    Returns:
        True si le refus a réussi
    """
    connexion = creer_connexion()

    try:
        # Étape 5.3 — Supprimer la demande refusée
        return repo_utilisateurs.refuser_reinitialisation(
            connexion, id_utilisateur
        )

    except Exception as erreur:
        logger.error(
            f"Erreur refuser reset mdp : {erreur}"
        )
        raise
    finally:
        connexion.close()