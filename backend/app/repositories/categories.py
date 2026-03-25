"""
repositories/categories.py
--------------------------
Requêtes SQL — Catégories.

Rôle :
    Effectuer toutes les opérations SQL sur la table :
        - categories

    Pas de logique métier ici — uniquement du SQL.
    La logique métier est dans services/categories.py.

Importation :
    from app.repositories.categories import (
        inserer_categorie,
        obtenir_categorie_par_id,
        lister_categories_du_projet,
    )
"""

import psycopg2
from app.logger import get_logger


# Initialiser le logger pour ce module
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — REQUÊTES DE LECTURE
# ─────────────────────────────────────────────────────────────

def obtenir_categorie_par_id(
    connexion   : psycopg2.extensions.connection,
    id_categorie: int,
) -> dict | None:
    """
    Récupère une catégorie par son ID.

    Args:
        connexion   : Connexion PostgreSQL active
        id_categorie: ID de la catégorie

    Returns:
        Dictionnaire avec les infos ou None si absente
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.1 — Rechercher la catégorie par ID
        curseur.execute("""
            SELECT
                id,
                id_projet,
                numero,
                description,
                cree_par,
                modifie_par_id,
                date_modification,
                version
            FROM categories
            WHERE id = %s;
        """, (id_categorie,))

        ligne = curseur.fetchone()
        if not ligne:
            return None

        return {
            "id"               : ligne[0],
            "id_projet"        : ligne[1],
            "numero"           : ligne[2],
            "description"      : ligne[3],
            "cree_par"         : ligne[4],
            "modifie_par_id"   : ligne[5],
            "date_modification": ligne[6],
            "version"          : ligne[7],
        }

    except Exception as erreur:
        logger.error(
            f"Erreur obtenir catégorie par ID : {erreur}"
        )
        raise
    finally:
        curseur.close()


def verifier_numero_categorie_unique(
    connexion   : psycopg2.extensions.connection,
    id_projet   : int,
    numero      : str,
    exclure_id  : int | None = None,
) -> bool:
    """
    Vérifie si un numéro est unique dans un projet.
    Vérifie à la fois dans categories ET dans notes
    car les numéros doivent être distincts partout.

    Args:
        connexion : Connexion PostgreSQL active
        id_projet : ID du projet
        numero    : Numéro à vérifier
        exclure_id: ID à exclure (lors d'une modification)

    Returns:
        True si le numéro est disponible, False sinon
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.2 — Vérifier l'unicité dans categories
        """
        On exclut l'ID courant lors d'une modification
        pour éviter le conflit avec soi-même.
        """
        if exclure_id:
            curseur.execute("""
                SELECT 1 FROM categories
                WHERE id_projet = %s
                AND numero = %s
                AND id != %s;
            """, (id_projet, numero, exclure_id))
        else:
            curseur.execute("""
                SELECT 1 FROM categories
                WHERE id_projet = %s
                AND numero = %s;
            """, (id_projet, numero))

        if curseur.fetchone():
            return False

        # Étape 1.3 — Vérifier l'unicité dans notes
        """
        Les numéros de catégories et de notes doivent
        être distincts dans tout le projet pour éviter
        toute ambiguïté dans le fichier .txt Revit.
        """
        curseur.execute("""
            SELECT 1 FROM notes
            WHERE id_projet = %s
            AND numero = %s;
        """, (id_projet, numero))

        return curseur.fetchone() is None

    except Exception as erreur:
        logger.error(
            f"Erreur vérification numéro unique : {erreur}"
        )
        raise
    finally:
        curseur.close()


def lister_categories_du_projet(
    connexion: psycopg2.extensions.connection,
    id_projet: int,
) -> list[dict]:
    """
    Récupère toutes les catégories d'un projet avec
    le nombre de notes associées à chaque catégorie.

    Args:
        connexion: Connexion PostgreSQL active
        id_projet: ID du projet

    Returns:
        Liste des catégories avec nombre_notes
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.4 — Récupérer catégories + count notes
        """
        Le COUNT des notes est utile dans le frontend
        pour informer l'utilisateur avant une suppression
        (une catégorie non vide ne peut pas être supprimée).
        """
        curseur.execute("""
            SELECT
                c.id,
                c.id_projet,
                c.numero,
                c.description,
                c.cree_par,
                c.modifie_par_id,
                c.date_modification,
                c.version,
                COUNT(n.id) AS nombre_notes
            FROM categories c
            LEFT JOIN notes n
                ON n.id_categorie = c.id
            WHERE c.id_projet = %s
            GROUP BY c.id
            ORDER BY c.numero;
        """, (id_projet,))

        return [
            {
                "id"               : ligne[0],
                "id_projet"        : ligne[1],
                "numero"           : ligne[2],
                "description"      : ligne[3],
                "cree_par"         : ligne[4],
                "modifie_par_id"   : ligne[5],
                "date_modification": ligne[6],
                "version"          : ligne[7],
                "nombre_notes"     : ligne[8],
            }
            for ligne in curseur.fetchall()
        ]

    except Exception as erreur:
        logger.error(
            f"Erreur listage catégories : {erreur}"
        )
        raise
    finally:
        curseur.close()


def compter_notes_de_categorie(
    connexion   : psycopg2.extensions.connection,
    id_categorie: int,
) -> int:
    """
    Compte le nombre de notes dans une catégorie.
    Utilisée avant une suppression pour vérifier
    si la catégorie est vide.

    Args:
        connexion   : Connexion PostgreSQL active
        id_categorie: ID de la catégorie

    Returns:
        Nombre de notes dans la catégorie
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.5 — Compter les notes de la catégorie
        curseur.execute("""
            SELECT COUNT(*)
            FROM notes
            WHERE id_categorie = %s;
        """, (id_categorie,))

        return curseur.fetchone()[0]

    except Exception as erreur:
        logger.error(
            f"Erreur comptage notes : {erreur}"
        )
        raise
    finally:
        curseur.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — REQUÊTES D'ÉCRITURE
# ─────────────────────────────────────────────────────────────

def inserer_categorie(
    connexion   : psycopg2.extensions.connection,
    id_projet   : int,
    numero      : str,
    description : str,
    id_createur : int,
) -> dict:
    """
    Insère une nouvelle catégorie dans la BD.

    Args:
        connexion  : Connexion PostgreSQL active
        id_projet  : ID du projet
        numero     : Numéro unique de la catégorie
        description: Description de la catégorie
        id_createur: ID de l'utilisateur créateur

    Returns:
        Dictionnaire avec les infos de la catégorie créée
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.1 — Insérer la catégorie
        curseur.execute("""
            INSERT INTO categories (
                id_projet,
                numero,
                description,
                cree_par,
                modifie_par_id
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING
                id,
                id_projet,
                numero,
                description,
                cree_par,
                modifie_par_id,
                date_modification,
                version;
        """, (
            id_projet,
            numero,
            description,
            id_createur,
            id_createur,
        ))

        ligne = curseur.fetchone()
        connexion.commit()

        logger.info(
            f"Catégorie créée : '{numero}' "
            f"dans projet {id_projet}"
        )

        return {
            "id"               : ligne[0],
            "id_projet"        : ligne[1],
            "numero"           : ligne[2],
            "description"      : ligne[3],
            "cree_par"         : ligne[4],
            "modifie_par_id"   : ligne[5],
            "date_modification": ligne[6],
            "version"          : ligne[7],
        }

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur insertion catégorie : {erreur}"
        )
        raise
    finally:
        curseur.close()


def mettre_a_jour_categorie(
    connexion        : psycopg2.extensions.connection,
    id_categorie     : int,
    version_actuelle : int,
    id_modificateur  : int,
    nouveau_numero   : str | None = None,
    nouvelle_desc    : str | None = None,
) -> dict:
    """
    Met à jour une catégorie avec verrouillage optimiste.
    Si la version en BD diffère de version_actuelle,
    un conflit est détecté et une erreur est levée.

    Args:
        connexion       : Connexion PostgreSQL active
        id_categorie    : ID de la catégorie
        version_actuelle: Version au moment de l'ouverture
        id_modificateur : ID de l'utilisateur modificateur
        nouveau_numero  : Nouveau numéro (optionnel)
        nouvelle_desc   : Nouvelle description (optionnel)

    Returns:
        Dictionnaire avec les infos mises à jour

    Raises:
        ValueError: Si un conflit de version est détecté
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.2 — Vérifier la version (verrouillage)
        """
        Si la version en BD est différente de la version
        reçue, cela signifie qu'un autre utilisateur a
        modifié la catégorie entre-temps.
        """
        curseur.execute("""
            SELECT version FROM categories
            WHERE id = %s;
        """, (id_categorie,))

        ligne = curseur.fetchone()
        if not ligne:
            raise ValueError(
                f"Catégorie {id_categorie} introuvable."
            )

        if ligne[0] != version_actuelle:
            raise ValueError(
                "Conflit détecté : cette catégorie a été "
                "modifiée par un autre utilisateur. "
                "Veuillez recharger et réessayer."
            )

        # Étape 2.3 — Construire la mise à jour dynamique
        champs = {
            "modifie_par_id"   : id_modificateur,
            "date_modification": "CURRENT_TIMESTAMP",
            "version"          : version_actuelle + 1,
        }
        if nouveau_numero:
            champs["numero"] = nouveau_numero
        if nouvelle_desc:
            champs["description"] = nouvelle_desc

        # Étape 2.4 — Exécuter la mise à jour
        parties_set = []
        valeurs = []
        for cle, valeur in champs.items():
            if valeur == "CURRENT_TIMESTAMP":
                parties_set.append(
                    f"{cle} = CURRENT_TIMESTAMP"
                )
            else:
                parties_set.append(f"{cle} = %s")
                valeurs.append(valeur)

        valeurs.append(id_categorie)
        curseur.execute(f"""
            UPDATE categories
            SET {', '.join(parties_set)}
            WHERE id = %s
            RETURNING
                id, id_projet, numero, description,
                cree_par, modifie_par_id,
                date_modification, version;
        """, valeurs)

        ligne = curseur.fetchone()
        connexion.commit()

        logger.info(
            f"Catégorie {id_categorie} mise à jour."
        )

        return {
            "id"               : ligne[0],
            "id_projet"        : ligne[1],
            "numero"           : ligne[2],
            "description"      : ligne[3],
            "cree_par"         : ligne[4],
            "modifie_par_id"   : ligne[5],
            "date_modification": ligne[6],
            "version"          : ligne[7],
        }

    except ValueError:
        connexion.rollback()
        raise
    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur mise à jour catégorie : {erreur}"
        )
        raise
    finally:
        curseur.close()


def supprimer_categorie(
    connexion   : psycopg2.extensions.connection,
    id_categorie: int,
) -> bool:
    """
    Supprime une catégorie vide.
    ON DELETE RESTRICT empêche la suppression si des
    notes existent encore — PostgreSQL lèvera une erreur.

    Args:
        connexion   : Connexion PostgreSQL active
        id_categorie: ID de la catégorie à supprimer

    Returns:
        True si la suppression a réussi
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.5 — Supprimer la catégorie
        curseur.execute("""
            DELETE FROM categories
            WHERE id = %s;
        """, (id_categorie,))

        connexion.commit()
        logger.info(
            f"Catégorie {id_categorie} supprimée."
        )
        return True

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur suppression catégorie : {erreur}"
        )
        raise
    finally:
        curseur.close()