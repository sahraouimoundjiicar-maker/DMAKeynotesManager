"""
repositories/notes.py
---------------------
Requêtes SQL — Notes (keynotes).

Rôle :
    Effectuer toutes les opérations SQL sur la table :
        - notes

    Pas de logique métier ici — uniquement du SQL.
    La logique métier est dans services/notes.py.

Importation :
    from app.repositories.notes import (
        inserer_note,
        obtenir_note_par_id,
        lister_notes_de_categorie,
        rechercher_notes,
    )
"""

import psycopg2
from app.logger import get_logger


# Initialiser le logger pour ce module
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — REQUÊTES DE LECTURE
# ─────────────────────────────────────────────────────────────

def obtenir_note_par_id(
    connexion: psycopg2.extensions.connection,
    id_note  : int,
) -> dict | None:
    """
    Récupère une note par son ID.

    Args:
        connexion: Connexion PostgreSQL active
        id_note  : ID de la note

    Returns:
        Dictionnaire avec les infos ou None si absente
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.1 — Rechercher la note par ID
        curseur.execute("""
            SELECT
                id,
                id_projet,
                id_categorie,
                numero,
                description,
                cree_par,
                modifie_par_id,
                date_modification,
                date_creation,
                version
            FROM notes
            WHERE id = %s;
        """, (id_note,))

        ligne = curseur.fetchone()
        if not ligne:
            return None

        return {
            "id"               : ligne[0],
            "id_projet"        : ligne[1],
            "id_categorie"     : ligne[2],
            "numero"           : ligne[3],
            "description"      : ligne[4],
            "cree_par"         : ligne[5],
            "modifie_par_id"   : ligne[6],
            "date_modification": ligne[7],
            "date_creation"    : ligne[8],
            "version"          : ligne[9],
        }

    except Exception as erreur:
        logger.error(
            f"Erreur obtenir note par ID : {erreur}"
        )
        raise
    finally:
        curseur.close()


def verifier_numero_note_unique(
    connexion : psycopg2.extensions.connection,
    id_projet : int,
    numero    : str,
    exclure_id: int | None = None,
) -> bool:
    """
    Vérifie si un numéro est unique dans un projet.
    Vérifie dans notes ET dans categories car les numéros
    doivent être distincts partout dans le projet.

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
        # Étape 1.2 — Vérifier l'unicité dans notes
        """
        On exclut l'ID courant lors d'une modification
        pour éviter le conflit avec soi-même.
        """
        if exclure_id:
            curseur.execute("""
                SELECT 1 FROM notes
                WHERE id_projet = %s
                AND numero = %s
                AND id != %s;
            """, (id_projet, numero, exclure_id))
        else:
            curseur.execute("""
                SELECT 1 FROM notes
                WHERE id_projet = %s
                AND numero = %s;
            """, (id_projet, numero))

        if curseur.fetchone():
            return False

        # Étape 1.3 — Vérifier l'unicité dans categories
        """
        Les numéros de notes et de catégories doivent
        être distincts dans tout le projet.
        """
        curseur.execute("""
            SELECT 1 FROM categories
            WHERE id_projet = %s
            AND numero = %s;
        """, (id_projet, numero))

        return curseur.fetchone() is None

    except Exception as erreur:
        logger.error(
            f"Erreur vérification numéro note : {erreur}"
        )
        raise
    finally:
        curseur.close()


def lister_notes_de_categorie(
    connexion   : psycopg2.extensions.connection,
    id_categorie: int,
) -> list[dict]:
    """
    Récupère toutes les notes d'une catégorie.
    Triées par numéro avec tri naturel numérique.

    Args:
        connexion   : Connexion PostgreSQL active
        id_categorie: ID de la catégorie

    Returns:
        Liste des notes de la catégorie
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.4 — Récupérer les notes d'une catégorie
        """
        Le tri par numero utilise la fonction
        string_to_array et regexp_split_to_array pour
        un tri naturel numérique (1, 2, 10 et non 1, 10, 2).
        """
        curseur.execute("""
            SELECT
                id,
                id_projet,
                id_categorie,
                numero,
                description,
                cree_par,
                modifie_par_id,
                date_modification,
                date_creation,
                version
            FROM notes
            WHERE id_categorie = %s
            ORDER BY numero;
        """, (id_categorie,))

        return [
            {
                "id"               : ligne[0],
                "id_projet"        : ligne[1],
                "id_categorie"     : ligne[2],
                "numero"           : ligne[3],
                "description"      : ligne[4],
                "cree_par"         : ligne[5],
                "modifie_par_id"   : ligne[6],
                "date_modification": ligne[7],
                "date_creation"    : ligne[8],
                "version"          : ligne[9],
            }
            for ligne in curseur.fetchall()
        ]

    except Exception as erreur:
        logger.error(
            f"Erreur listage notes catégorie : {erreur}"
        )
        raise
    finally:
        curseur.close()


def lister_keynotes_du_projet(
    connexion : psycopg2.extensions.connection,
    id_projet : int,
    id_categorie: int | None = None,
) -> list[dict]:
    """
    Récupère toutes les notes d'un projet avec les
    informations de leurs catégories.
    Filtre optionnel par catégorie.

    Args:
        connexion   : Connexion PostgreSQL active
        id_projet   : ID du projet
        id_categorie: Filtre optionnel par catégorie

    Returns:
        Liste des notes avec infos catégorie
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.5 — Récupérer notes + catégories
        """
        JOIN avec categories pour afficher les infos
        de la catégorie parente de chaque note.
        Filtre optionnel par id_categorie.
        """
        if id_categorie:
            curseur.execute("""
                SELECT
                    n.id,
                    n.numero,
                    n.description,
                    n.modifie_par_id,
                    n.date_modification,
                    n.version,
                    c.id         AS categorie_id,
                    c.numero     AS categorie_numero,
                    c.description AS categorie_description
                FROM notes n
                JOIN categories c
                    ON c.id = n.id_categorie
                WHERE n.id_projet = %s
                AND n.id_categorie = %s
                ORDER BY c.numero, n.numero;
            """, (id_projet, id_categorie))
        else:
            curseur.execute("""
                SELECT
                    n.id,
                    n.numero,
                    n.description,
                    n.modifie_par_id,
                    n.date_modification,
                    n.version,
                    c.id         AS categorie_id,
                    c.numero     AS categorie_numero,
                    c.description AS categorie_description
                FROM notes n
                JOIN categories c
                    ON c.id = n.id_categorie
                WHERE n.id_projet = %s
                ORDER BY c.numero, n.numero;
            """, (id_projet,))

        return [
            {
                "id"                    : ligne[0],
                "numero"                : ligne[1],
                "description"           : ligne[2],
                "modifie_par_id"        : ligne[3],
                "date_modification"     : ligne[4],
                "version"               : ligne[5],
                "categorie_id"          : ligne[6],
                "categorie_numero"      : ligne[7],
                "categorie_description" : ligne[8],
            }
            for ligne in curseur.fetchall()
        ]

    except Exception as erreur:
        logger.error(
            f"Erreur listage keynotes projet : {erreur}"
        )
        raise
    finally:
        curseur.close()


def rechercher_notes(
    connexion   : psycopg2.extensions.connection,
    id_projet   : int,
    terme       : str,
    id_categorie: int | None = None,
) -> list[dict]:
    """
    Recherche des notes par numéro ou description.
    Insensible à la casse et aux accents via ILIKE.

    Args:
        connexion   : Connexion PostgreSQL active
        id_projet   : ID du projet
        terme       : Terme de recherche
        id_categorie: Filtre optionnel par catégorie

    Returns:
        Liste des notes correspondant à la recherche
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.6 — Recherche ILIKE insensible à la casse
        """
        ILIKE est l'équivalent PostgreSQL de LIKE mais
        insensible à la casse. Il supporte aussi les
        caractères accentués français.
        Le % encadre le terme pour chercher partout
        dans le texte (contient).
        """
        terme_recherche = f"%{terme}%"

        if id_categorie:
            curseur.execute("""
                SELECT
                    n.id,
                    n.numero,
                    n.description,
                    n.modifie_par_id,
                    n.date_modification,
                    n.version,
                    c.id          AS categorie_id,
                    c.numero      AS categorie_numero,
                    c.description AS categorie_description
                FROM notes n
                JOIN categories c
                    ON c.id = n.id_categorie
                WHERE n.id_projet = %s
                AND n.id_categorie = %s
                AND (
                    n.numero      ILIKE %s
                    OR n.description ILIKE %s
                )
                ORDER BY c.numero, n.numero;
            """, (
                id_projet,
                id_categorie,
                terme_recherche,
                terme_recherche,
            ))
        else:
            curseur.execute("""
                SELECT
                    n.id,
                    n.numero,
                    n.description,
                    n.modifie_par_id,
                    n.date_modification,
                    n.version,
                    c.id          AS categorie_id,
                    c.numero      AS categorie_numero,
                    c.description AS categorie_description
                FROM notes n
                JOIN categories c
                    ON c.id = n.id_categorie
                WHERE n.id_projet = %s
                AND (
                    n.numero      ILIKE %s
                    OR n.description ILIKE %s
                )
                ORDER BY c.numero, n.numero;
            """, (
                id_projet,
                terme_recherche,
                terme_recherche,
            ))

        return [
            {
                "id"                   : ligne[0],
                "numero"               : ligne[1],
                "description"          : ligne[2],
                "modifie_par_id"       : ligne[3],
                "date_modification"    : ligne[4],
                "version"              : ligne[5],
                "categorie_id"         : ligne[6],
                "categorie_numero"     : ligne[7],
                "categorie_description": ligne[8],
            }
            for ligne in curseur.fetchall()
        ]

    except Exception as erreur:
        logger.error(
            f"Erreur recherche notes : {erreur}"
        )
        raise
    finally:
        curseur.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — REQUÊTES D'ÉCRITURE
# ─────────────────────────────────────────────────────────────

def inserer_note(
    connexion   : psycopg2.extensions.connection,
    id_projet   : int,
    id_categorie: int,
    numero      : str,
    description : str,
    id_createur : int,
) -> dict:
    """
    Insère une nouvelle note dans la BD.

    Args:
        connexion   : Connexion PostgreSQL active
        id_projet   : ID du projet
        id_categorie: ID de la catégorie parente
        numero      : Numéro unique de la note
        description : Description de la note
        id_createur : ID de l'utilisateur créateur

    Returns:
        Dictionnaire avec les infos de la note créée
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.1 — Insérer la note
        curseur.execute("""
            INSERT INTO notes (
                id_projet,
                id_categorie,
                numero,
                description,
                cree_par,
                modifie_par_id
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING
                id,
                id_projet,
                id_categorie,
                numero,
                description,
                cree_par,
                modifie_par_id,
                date_modification,
                date_creation,
                version;
        """, (
            id_projet,
            id_categorie,
            numero,
            description,
            id_createur,
            id_createur,
        ))

        ligne = curseur.fetchone()
        connexion.commit()

        logger.info(
            f"Note créée : '{numero}' "
            f"dans catégorie {id_categorie}"
        )

        return {
            "id"               : ligne[0],
            "id_projet"        : ligne[1],
            "id_categorie"     : ligne[2],
            "numero"           : ligne[3],
            "description"      : ligne[4],
            "cree_par"         : ligne[5],
            "modifie_par_id"   : ligne[6],
            "date_modification": ligne[7],
            "date_creation"    : ligne[8],
            "version"          : ligne[9],
        }

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur insertion note : {erreur}"
        )
        raise
    finally:
        curseur.close()


def mettre_a_jour_note(
    connexion       : psycopg2.extensions.connection,
    id_note         : int,
    version_actuelle: int,
    id_modificateur : int,
    nouveau_numero  : str | None = None,
    nouvelle_desc   : str | None = None,
) -> dict:
    """
    Met à jour une note avec verrouillage optimiste.
    Si la version en BD diffère de version_actuelle,
    un conflit est détecté et une erreur est levée.

    Args:
        connexion       : Connexion PostgreSQL active
        id_note         : ID de la note
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
        curseur.execute("""
            SELECT version FROM notes WHERE id = %s;
        """, (id_note,))

        ligne = curseur.fetchone()
        if not ligne:
            raise ValueError(
                f"Note {id_note} introuvable."
            )

        if ligne[0] != version_actuelle:
            raise ValueError(
                "Conflit détecté : cette note a été "
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

        valeurs.append(id_note)
        curseur.execute(f"""
            UPDATE notes
            SET {', '.join(parties_set)}
            WHERE id = %s
            RETURNING
                id, id_projet, id_categorie,
                numero, description, cree_par,
                modifie_par_id, date_modification,
                date_creation, version;
        """, valeurs)

        ligne = curseur.fetchone()
        connexion.commit()

        logger.info(f"Note {id_note} mise à jour.")

        return {
            "id"               : ligne[0],
            "id_projet"        : ligne[1],
            "id_categorie"     : ligne[2],
            "numero"           : ligne[3],
            "description"      : ligne[4],
            "cree_par"         : ligne[5],
            "modifie_par_id"   : ligne[6],
            "date_modification": ligne[7],
            "date_creation"    : ligne[8],
            "version"          : ligne[9],
        }

    except ValueError:
        connexion.rollback()
        raise
    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur mise à jour note : {erreur}"
        )
        raise
    finally:
        curseur.close()


def supprimer_note(
    connexion: psycopg2.extensions.connection,
    id_note  : int,
) -> bool:
    """
    Supprime une note de la BD.

    Args:
        connexion: Connexion PostgreSQL active
        id_note  : ID de la note à supprimer

    Returns:
        True si la suppression a réussi
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.5 — Supprimer la note
        curseur.execute("""
            DELETE FROM notes WHERE id = %s;
        """, (id_note,))

        connexion.commit()
        logger.info(f"Note {id_note} supprimée.")
        return True

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur suppression note : {erreur}"
        )
        raise
    finally:
        curseur.close()