"""
repositories/historique.py
--------------------------
Requêtes SQL — Historique.

Rôle :
    Effectuer toutes les opérations SQL sur la table :
        - historique

    Pas de logique métier ici — uniquement du SQL.
    La logique métier est dans services/notes.py,
    services/categories.py et services/keynotes_fichier.py.

Importation :
    from app.repositories.historique import (
        inserer_historique,
        lister_historique_projet,
        lister_historique_utilisateur,
    )
"""

import psycopg2
from app.logger import get_logger


# Initialiser le logger pour ce module
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — REQUÊTES DE LECTURE
# ─────────────────────────────────────────────────────────────

def compter_historique_projet(
    connexion : psycopg2.extensions.connection,
    id_projet : int,
) -> int:
    """
    Compte le nombre total d'entrées dans l'historique
    d'un projet. Utilisé pour calculer le nombre de pages.

    Args:
        connexion: Connexion PostgreSQL active
        id_projet: ID du projet

    Returns:
        Nombre total d'entrées dans l'historique
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.1 — Compter toutes les entrées
        curseur.execute("""
            SELECT COUNT(*)
            FROM historique
            WHERE id_projet = %s;
        """, (id_projet,))

        return curseur.fetchone()[0]

    except Exception as erreur:
        logger.error(
            f"Erreur comptage historique : {erreur}"
        )
        raise
    finally:
        curseur.close()


def compter_historique_utilisateur(
    connexion     : psycopg2.extensions.connection,
    id_projet     : int,
    id_utilisateur: int,
) -> int:
    """
    Compte le nombre d'entrées dans l'historique
    pour un utilisateur spécifique dans un projet.

    Args:
        connexion     : Connexion PostgreSQL active
        id_projet     : ID du projet
        id_utilisateur: ID de l'utilisateur

    Returns:
        Nombre d'entrées de l'utilisateur
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.2 — Compter les entrées de l'utilisateur
        curseur.execute("""
            SELECT COUNT(*)
            FROM historique
            WHERE id_projet = %s
            AND effectue_par_id = %s;
        """, (id_projet, id_utilisateur))

        return curseur.fetchone()[0]

    except Exception as erreur:
        logger.error(
            f"Erreur comptage historique "
            f"utilisateur : {erreur}"
        )
        raise
    finally:
        curseur.close()


def lister_historique_projet(
    connexion : psycopg2.extensions.connection,
    id_projet : int,
    limite    : int,
    offset    : int,
) -> list[dict]:
    """
    Récupère l'historique complet d'un projet paginé.
    Accessible au super_admin uniquement.
    Trié par date décroissante (plus récent en premier).

    Args:
        connexion: Connexion PostgreSQL active
        id_projet: ID du projet
        limite   : Nombre d'entrées par page
        offset   : Nombre d'entrées à sauter

    Returns:
        Liste paginée des entrées d'historique
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.3 — Récupérer l'historique paginé
        """
        LIMIT et OFFSET permettent la pagination.
        offset = (page - 1) * limite
        calculé dans le service avant d'appeler ce repo.
        """
        curseur.execute("""
            SELECT
                id,
                id_projet,
                table_cible,
                id_cible,
                action,
                ancienne_valeur,
                nouvelle_valeur,
                effectue_par_id,
                effectue_par_role,
                date_action
            FROM historique
            WHERE id_projet = %s
            ORDER BY date_action DESC
            LIMIT %s OFFSET %s;
        """, (id_projet, limite, offset))

        return [
            {
                "id"               : ligne[0],
                "id_projet"        : ligne[1],
                "table_cible"      : ligne[2],
                "id_cible"         : ligne[3],
                "action"           : ligne[4],
                "ancienne_valeur"  : ligne[5],
                "nouvelle_valeur"  : ligne[6],
                "effectue_par_id"  : ligne[7],
                "effectue_par_role": ligne[8],
                "date_action"      : ligne[9],
            }
            for ligne in curseur.fetchall()
        ]

    except Exception as erreur:
        logger.error(
            f"Erreur listage historique projet : {erreur}"
        )
        raise
    finally:
        curseur.close()


def lister_historique_utilisateur(
    connexion     : psycopg2.extensions.connection,
    id_projet     : int,
    id_utilisateur: int,
    limite        : int,
    offset        : int,
) -> list[dict]:
    """
    Récupère uniquement les actions d'un utilisateur
    dans l'historique d'un projet (paginé).
    Accessible aux utilisateurs pour leurs propres actions.

    Args:
        connexion     : Connexion PostgreSQL active
        id_projet     : ID du projet
        id_utilisateur: ID de l'utilisateur
        limite        : Nombre d'entrées par page
        offset        : Nombre d'entrées à sauter

    Returns:
        Liste paginée des actions de l'utilisateur
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.4 — Filtrer par utilisateur et paginer
        curseur.execute("""
            SELECT
                id,
                id_projet,
                table_cible,
                id_cible,
                action,
                ancienne_valeur,
                nouvelle_valeur,
                effectue_par_id,
                effectue_par_role,
                date_action
            FROM historique
            WHERE id_projet = %s
            AND effectue_par_id = %s
            ORDER BY date_action DESC
            LIMIT %s OFFSET %s;
        """, (id_projet, id_utilisateur, limite, offset))

        return [
            {
                "id"               : ligne[0],
                "id_projet"        : ligne[1],
                "table_cible"      : ligne[2],
                "id_cible"         : ligne[3],
                "action"           : ligne[4],
                "ancienne_valeur"  : ligne[5],
                "nouvelle_valeur"  : ligne[6],
                "effectue_par_id"  : ligne[7],
                "effectue_par_role": ligne[8],
                "date_action"      : ligne[9],
            }
            for ligne in curseur.fetchall()
        ]

    except Exception as erreur:
        logger.error(
            f"Erreur listage historique "
            f"utilisateur : {erreur}"
        )
        raise
    finally:
        curseur.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — REQUÊTES D'ÉCRITURE
# ─────────────────────────────────────────────────────────────

def inserer_historique(
    connexion        : psycopg2.extensions.connection,
    id_projet        : int,
    table_cible      : str,
    action           : str,
    effectue_par_id  : int,
    effectue_par_role: str,
    id_cible         : int | None = None,
    ancienne_valeur  : str | None = None,
    nouvelle_valeur  : str | None = None,
) -> dict:
    """
    Insère une nouvelle entrée dans l'historique.
    Appelée après chaque action sur les keynotes.

    Args:
        connexion        : Connexion PostgreSQL active
        id_projet        : ID du projet
        table_cible      : 'categories', 'notes' ou 'projet'
        action           : Type d'action effectuée
        effectue_par_id  : ID de l'auteur de l'action
        effectue_par_role: 'super_admin' ou 'utilisateur'
        id_cible         : ID de l'élément modifié
        ancienne_valeur  : Valeur avant modification
        nouvelle_valeur  : Valeur après modification

    Returns:
        Dictionnaire avec les infos de l'entrée créée
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.1 — Insérer l'entrée d'historique
        curseur.execute("""
            INSERT INTO historique (
                id_projet,
                table_cible,
                id_cible,
                action,
                ancienne_valeur,
                nouvelle_valeur,
                effectue_par_id,
                effectue_par_role
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING
                id,
                id_projet,
                table_cible,
                id_cible,
                action,
                ancienne_valeur,
                nouvelle_valeur,
                effectue_par_id,
                effectue_par_role,
                date_action;
        """, (
            id_projet,
            table_cible,
            id_cible,
            action,
            ancienne_valeur,
            nouvelle_valeur,
            effectue_par_id,
            effectue_par_role,
        ))

        ligne = curseur.fetchone()
        connexion.commit()

        logger.info(
            f"Historique : {action} sur "
            f"{table_cible} par {effectue_par_id}"
        )

        return {
            "id"               : ligne[0],
            "id_projet"        : ligne[1],
            "table_cible"      : ligne[2],
            "id_cible"         : ligne[3],
            "action"           : ligne[4],
            "ancienne_valeur"  : ligne[5],
            "nouvelle_valeur"  : ligne[6],
            "effectue_par_id"  : ligne[7],
            "effectue_par_role": ligne[8],
            "date_action"      : ligne[9],
        }

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur insertion historique : {erreur}"
        )
        raise
    finally:
        curseur.close()