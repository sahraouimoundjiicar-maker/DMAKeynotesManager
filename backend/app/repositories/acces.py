"""
repositories/acces.py
---------------------
Requêtes SQL — Accès projets.

Rôle :
    Effectuer toutes les opérations SQL sur la table :
        - acces_projet

    Pas de logique métier ici — uniquement du SQL.
    La logique métier est dans services/acces.py.

Importation :
    from app.repositories.acces import (
        inserer_acces,
        supprimer_acces,
        verifier_acces_existant,
    )
"""

import psycopg2
from app.logger import get_logger


# Initialiser le logger pour ce module
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — REQUÊTES DE LECTURE
# ─────────────────────────────────────────────────────────────

def verifier_acces_existant(
    connexion     : psycopg2.extensions.connection,
    id_projet     : int,
    id_utilisateur: int,
) -> bool:
    """
    Vérifie si un utilisateur a déjà accès à un projet.
    Utilisée avant d'attribuer un accès pour éviter
    les doublons.

    Args:
        connexion     : Connexion PostgreSQL active
        id_projet     : ID du projet
        id_utilisateur: ID du utilisateur

    Returns:
        True si l'accès existe déjà, False sinon
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.1 — Vérifier l'existence de l'accès
        curseur.execute("""
            SELECT 1
            FROM acces_projet
            WHERE id_projet = %s
            AND id_utilisateur = %s;
        """, (id_projet, id_utilisateur))

        return curseur.fetchone() is not None

    except Exception as erreur:
        logger.error(
            f"Erreur vérification accès : {erreur}"
        )
        raise
    finally:
        curseur.close()


def lister_utilisateurs_du_projet(
    connexion: psycopg2.extensions.connection,
    id_projet: int,
) -> list[dict]:
    """
    Récupère la liste des utilisateurs ayant accès
    à un projet avec leurs informations.

    Args:
        connexion: Connexion PostgreSQL active
        id_projet: ID du projet

    Returns:
        Liste des utilisateurs avec date d'attribution
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.2 — Joindre acces_projet et utilisateurs
        """
        On joint avec utilisateurs pour récupérer
        le nom et l'email de chaque utilisateur.
        """
        curseur.execute("""
            SELECT
                a.id,
                a.id_utilisateur,
                u.nom,
                u.prenom,
                u.email,
                a.date_attribution,
                a.attribue_par
            FROM acces_projet a
            JOIN utilisateurs u
                ON u.id = a.id_utilisateur
            WHERE a.id_projet = %s
            ORDER BY u.nom, u.prenom;
        """, (id_projet,))

        return [
            {
                "id"             : ligne[0],
                "id_utilisateur" : ligne[1],
                "nom"            : ligne[2],
                "prenom"         : ligne[3],
                "email"          : ligne[4],
                "date_attribution": ligne[5],
                "attribue_par"   : ligne[6],
            }
            for ligne in curseur.fetchall()
        ]

    except Exception as erreur:
        logger.error(
            f"Erreur listage utilisateurs : {erreur}"
        )
        raise
    finally:
        curseur.close()


def verifier_acces_utilisateur(
    connexion     : psycopg2.extensions.connection,
    id_projet     : int,
    id_utilisateur: int,
) -> bool:
    """
    Vérifie si un utilisateur a accès à un projet.
    Utilisée par la dépendance verifier_acces_projet()
    pour protéger les routes keynotes.

    Args:
        connexion     : Connexion PostgreSQL active
        id_projet     : ID du projet
        id_utilisateur: ID du utilisateur

    Returns:
        True si l'utilisateur a accès, False sinon
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.3 — Vérifier l'accès de l'utilisateur
        curseur.execute("""
            SELECT 1
            FROM acces_projet
            WHERE id_projet = %s
            AND id_utilisateur = %s;
        """, (id_projet, id_utilisateur))

        return curseur.fetchone() is not None

    except Exception as erreur:
        logger.error(
            f"Erreur vérification accès utilisateur : "
            f"{erreur}"
        )
        raise
    finally:
        curseur.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — REQUÊTES D'ÉCRITURE
# ─────────────────────────────────────────────────────────────

def inserer_acces(
    connexion     : psycopg2.extensions.connection,
    id_projet     : int,
    id_utilisateur: int,
    id_super_admin: int,
) -> dict:
    """
    Attribue l'accès d'un utilisateur à un projet.

    Args:
        connexion     : Connexion PostgreSQL active
        id_projet     : ID du projet
        id_utilisateur: ID du utilisateur
        id_super_admin: ID du super_admin qui attribue

    Returns:
        Dictionnaire avec les infos de l'accès créé
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.1 — Insérer l'accès
        curseur.execute("""
            INSERT INTO acces_projet (
                id_projet,
                id_utilisateur,
                attribue_par
            )
            VALUES (%s, %s, %s)
            RETURNING
                id,
                id_projet,
                id_utilisateur,
                date_attribution,
                attribue_par;
        """, (id_projet, id_utilisateur, id_super_admin))

        ligne = curseur.fetchone()
        connexion.commit()

        logger.info(
            f"Accès attribué : utilisateur "
            f"{id_utilisateur} → projet {id_projet}"
        )

        return {
            "id"             : ligne[0],
            "id_projet"      : ligne[1],
            "id_utilisateur" : ligne[2],
            "date_attribution": ligne[3],
            "attribue_par"   : ligne[4],
        }

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur insertion accès : {erreur}"
        )
        raise
    finally:
        curseur.close()


def supprimer_acces(
    connexion     : psycopg2.extensions.connection,
    id_projet     : int,
    id_utilisateur: int,
) -> bool:
    """
    Retire l'accès d'un utilisateur à un projet.

    Args:
        connexion     : Connexion PostgreSQL active
        id_projet     : ID du projet
        id_utilisateur: ID du utilisateur

    Returns:
        True si la suppression a réussi
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.2 — Supprimer l'accès
        curseur.execute("""
            DELETE FROM acces_projet
            WHERE id_projet = %s
            AND id_utilisateur = %s;
        """, (id_projet, id_utilisateur))

        connexion.commit()

        logger.info(
            f"Accès retiré : utilisateur "
            f"{id_utilisateur} ← projet {id_projet}"
        )
        return True

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur suppression accès : {erreur}"
        )
        raise
    finally:
        curseur.close()