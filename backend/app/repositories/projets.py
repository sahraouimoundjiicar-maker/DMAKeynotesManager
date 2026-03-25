"""
repositories/projets.py
-----------------------
Requêtes SQL — Projets.

Rôle :
    Effectuer toutes les opérations SQL sur la table :
        - projets

    Pas de logique métier ici — uniquement du SQL.
    La logique métier est dans services/projets.py.

Importation :
    from app.repositories.projets import (
        inserer_projet,
        obtenir_projet_par_id,
        lister_projets,
    )
"""

import psycopg2
from app.logger import get_logger


# Initialiser le logger pour ce module
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — REQUÊTES DE LECTURE
# ─────────────────────────────────────────────────────────────

def obtenir_projet_par_id(
    connexion : psycopg2.extensions.connection,
    id_projet : int,
) -> dict | None:
    """
    Récupère un projet par son ID.

    Args:
        connexion: Connexion PostgreSQL active
        id_projet: ID du projet

    Returns:
        Dictionnaire avec les infos ou None si absent
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.1 — Rechercher le projet par ID
        curseur.execute("""
            SELECT
                id,
                nom,
                txt_a_jour,
                date_dernier_export,
                cree_par,
                date_creation
            FROM projets
            WHERE id = %s;
        """, (id_projet,))

        ligne = curseur.fetchone()
        if not ligne:
            return None

        return {
            "id"                 : ligne[0],
            "nom"                : ligne[1],
            "txt_a_jour"         : ligne[2],
            "date_dernier_export": ligne[3],
            "cree_par"           : ligne[4],
            "date_creation"      : ligne[5],
        }

    except Exception as erreur:
        logger.error(
            f"Erreur obtenir projet par ID : {erreur}"
        )
        raise
    finally:
        curseur.close()


def obtenir_projet_par_nom(
    connexion  : psycopg2.extensions.connection,
    nom_projet : str,
) -> dict | None:
    """
    Récupère un projet par son nom.
    Utilisée pour vérifier l'unicité du nom.

    Args:
        connexion : Connexion PostgreSQL active
        nom_projet: Nom du projet

    Returns:
        Dictionnaire avec les infos ou None si absent
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.2 — Rechercher le projet par nom
        curseur.execute("""
            SELECT
                id,
                nom,
                txt_a_jour,
                date_dernier_export,
                cree_par,
                date_creation
            FROM projets
            WHERE nom = %s;
        """, (nom_projet,))

        ligne = curseur.fetchone()
        if not ligne:
            return None

        return {
            "id"                 : ligne[0],
            "nom"                : ligne[1],
            "txt_a_jour"         : ligne[2],
            "date_dernier_export": ligne[3],
            "cree_par"           : ligne[4],
            "date_creation"      : ligne[5],
        }

    except Exception as erreur:
        logger.error(
            f"Erreur obtenir projet par nom : {erreur}"
        )
        raise
    finally:
        curseur.close()


def lister_projets(
    connexion: psycopg2.extensions.connection,
) -> list[dict]:
    """
    Récupère la liste de tous les projets.
    Triés par date de création (plus récent en premier).

    Args:
        connexion: Connexion PostgreSQL active

    Returns:
        Liste de dictionnaires avec les infos des projets
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.3 — Récupérer tous les projets
        curseur.execute("""
            SELECT
                id,
                nom,
                txt_a_jour,
                date_dernier_export,
                cree_par,
                date_creation
            FROM projets
            ORDER BY date_creation DESC;
        """)

        return [
            {
                "id"                 : ligne[0],
                "nom"                : ligne[1],
                "txt_a_jour"         : ligne[2],
                "date_dernier_export": ligne[3],
                "cree_par"           : ligne[4],
                "date_creation"      : ligne[5],
            }
            for ligne in curseur.fetchall()
        ]

    except Exception as erreur:
        logger.error(
            f"Erreur listage projets : {erreur}"
        )
        raise
    finally:
        curseur.close()


def lister_projets_par_utilisateur(
    connexion     : psycopg2.extensions.connection,
    id_utilisateur: int,
) -> list[dict]:
    """
    Récupère les projets accessibles par un utilisateur.
    Utilisée pour afficher les projets d'un collaborateur.

    Args:
        connexion     : Connexion PostgreSQL active
        id_utilisateur: ID du collaborateur

    Returns:
        Liste des projets accessibles par l'utilisateur
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.4 — Joindre projets et acces_projet
        """
        On joint les tables pour récupérer uniquement
        les projets auxquels l'utilisateur a accès.
        """
        curseur.execute("""
            SELECT
                p.id,
                p.nom,
                p.txt_a_jour,
                p.date_dernier_export,
                p.date_creation,
                a.date_attribution
            FROM projets p
            JOIN acces_projet a
                ON a.id_projet = p.id
            WHERE a.id_utilisateur = %s
            ORDER BY p.nom;
        """, (id_utilisateur,))

        return [
            {
                "id_projet"       : ligne[0],
                "nom_projet"      : ligne[1],
                "txt_a_jour"      : ligne[2],
                "date_dernier_export": ligne[3],
                "date_creation"   : ligne[4],
                "date_attribution": ligne[5],
            }
            for ligne in curseur.fetchall()
        ]

    except Exception as erreur:
        logger.error(
            f"Erreur listage projets utilisateur : {erreur}"
        )
        raise
    finally:
        curseur.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — REQUÊTES D'ÉCRITURE
# ─────────────────────────────────────────────────────────────

def inserer_projet(
    connexion     : psycopg2.extensions.connection,
    nom_projet    : str,
    id_super_admin: int,
) -> dict:
    """
    Insère un nouveau projet dans la BD.

    Args:
        connexion     : Connexion PostgreSQL active
        nom_projet    : Nom du projet Revit
        id_super_admin: ID du super_admin créateur

    Returns:
        Dictionnaire avec les infos du projet créé
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.1 — Insérer le projet
        curseur.execute("""
            INSERT INTO projets (nom, cree_par)
            VALUES (%s, %s)
            RETURNING
                id,
                nom,
                txt_a_jour,
                date_dernier_export,
                cree_par,
                date_creation;
        """, (nom_projet, id_super_admin))

        ligne = curseur.fetchone()
        connexion.commit()

        logger.info(f"Projet créé : '{nom_projet}'")

        return {
            "id"                 : ligne[0],
            "nom"                : ligne[1],
            "txt_a_jour"         : ligne[2],
            "date_dernier_export": ligne[3],
            "cree_par"           : ligne[4],
            "date_creation"      : ligne[5],
        }

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur insertion projet : {erreur}"
        )
        raise
    finally:
        curseur.close()


def mettre_a_jour_nom_projet(
    connexion  : psycopg2.extensions.connection,
    id_projet  : int,
    nouveau_nom: str,
) -> dict | None:
    """
    Met à jour le nom d'un projet existant.

    Args:
        connexion  : Connexion PostgreSQL active
        id_projet  : ID du projet à renommer
        nouveau_nom: Nouveau nom du projet

    Returns:
        Dictionnaire avec les infos mises à jour
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.2 — Mettre à jour le nom du projet
        curseur.execute("""
            UPDATE projets
            SET nom = %s
            WHERE id = %s
            RETURNING
                id,
                nom,
                txt_a_jour,
                date_dernier_export,
                date_creation;
        """, (nouveau_nom, id_projet))

        ligne = curseur.fetchone()
        connexion.commit()

        logger.info(
            f"Projet {id_projet} renommé : '{nouveau_nom}'"
        )

        return {
            "id"                 : ligne[0],
            "nom"                : ligne[1],
            "txt_a_jour"         : ligne[2],
            "date_dernier_export": ligne[3],
            "date_creation"      : ligne[4],
        }

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur renommage projet : {erreur}"
        )
        raise
    finally:
        curseur.close()


def mettre_a_jour_txt_a_jour(
    connexion  : psycopg2.extensions.connection,
    id_projet  : int,
    txt_a_jour : bool,
) -> bool:
    """
    Met à jour le statut txt_a_jour d'un projet.
    Appelée après chaque export ou modification de keynote.

    Args:
        connexion : Connexion PostgreSQL active
        id_projet : ID du projet
        txt_a_jour: True après export, False après modif

    Returns:
        True si la mise à jour a réussi
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.3 — Mettre à jour txt_a_jour
        """
        Si txt_a_jour = True (après export), on enregistre
        aussi la date du dernier export.
        """
        if txt_a_jour:
            curseur.execute("""
                UPDATE projets
                SET
                    txt_a_jour          = TRUE,
                    date_dernier_export = CURRENT_TIMESTAMP
                WHERE id = %s;
            """, (id_projet,))
        else:
            curseur.execute("""
                UPDATE projets
                SET txt_a_jour = FALSE
                WHERE id = %s;
            """, (id_projet,))

        connexion.commit()
        return True

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur mise à jour txt_a_jour : {erreur}"
        )
        raise
    finally:
        curseur.close()


def supprimer_projet(
    connexion: psycopg2.extensions.connection,
    id_projet: int,
) -> bool:
    """
    Supprime un projet et toutes ses données associées.
    Le CASCADE sur les FK supprime automatiquement :
    acces_projet, categories, notes, historique.

    Args:
        connexion: Connexion PostgreSQL active
        id_projet: ID du projet à supprimer

    Returns:
        True si la suppression a réussi
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.4 — Supprimer le projet
        """
        ON DELETE CASCADE sur toutes les tables liées
        garantit la suppression complète de toutes
        les données du projet en une seule requête.
        """
        curseur.execute("""
            DELETE FROM projets
            WHERE id = %s;
        """, (id_projet,))

        connexion.commit()
        logger.info(f"Projet {id_projet} supprimé.")
        return True

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur suppression projet : {erreur}"
        )
        raise
    finally:
        curseur.close()