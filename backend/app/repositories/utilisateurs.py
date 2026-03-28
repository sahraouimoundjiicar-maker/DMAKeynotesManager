"""
repositories/utilisateurs.py
----------------------------
Requêtes SQL — Utilisateurs.

Rôle :
    Effectuer toutes les opérations SQL sur les tables :
        - super_admin
        - utilisateurs
        - reinitialisation_mdp

    Pas de logique métier ici — uniquement du SQL.
    La logique métier est dans services/utilisateurs.py.

Importation :
    from app.repositories.utilisateurs import (
        inserer_utilisateur,
        obtenir_utilisateur_par_email,
        obtenir_utilisateur_par_id,
    )
"""

import psycopg2
from app.logger import get_logger


# Initialiser le logger pour ce module
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — REQUÊTES SUPER ADMIN
# ─────────────────────────────────────────────────────────────

def obtenir_super_admin_par_email(
    connexion: psycopg2.extensions.connection,
    email    : str,
) -> dict | None:
    """
    Récupère le super_admin par son email.
    Utilisée lors du login admin.

    Args:
        connexion : Connexion PostgreSQL active
        email     : Email du super_admin

    Returns:
        Dictionnaire avec les infos ou None si absent
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.1 — Rechercher le super_admin par email
        curseur.execute("""
            SELECT
                id,
                nom,
                prenom,
                email,
                mot_de_passe_hash
            FROM super_admin
            WHERE email = %s;
        """, (email,))

        ligne = curseur.fetchone()
        if not ligne:
            return None

        return {
            "id"               : ligne[0],
            "nom"              : ligne[1],
            "prenom"           : ligne[2],
            "email"            : ligne[3],
            "mot_de_passe_hash": ligne[4],
        }

    except Exception as erreur:
        logger.error(
            f"Erreur obtenir super_admin "
            f"par email : {erreur}"
        )
        raise
    finally:
        curseur.close()


def super_admin_existe(
    connexion: psycopg2.extensions.connection,
) -> bool:
    """
    Vérifie si un super_admin existe déjà dans la BD.
    Garantit qu'il n'y a qu'un seul super_admin.

    Args:
        connexion: Connexion PostgreSQL active

    Returns:
        True si un super_admin existe, False sinon
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.2 — Compter les super_admins existants
        curseur.execute(
            "SELECT COUNT(*) FROM super_admin;"
        )
        compte = curseur.fetchone()[0]
        return compte > 0

    except Exception as erreur:
        logger.error(
            f"Erreur vérification super_admin : {erreur}"
        )
        raise
    finally:
        curseur.close()


def inserer_super_admin(
    connexion        : psycopg2.extensions.connection,
    nom              : str,
    prenom           : str,
    email            : str,
    mot_de_passe_hash: str,
) -> dict:
    """
    Insère le super_admin dans la BD.
    Appelée une seule fois au premier démarrage.

    Args:
        connexion        : Connexion PostgreSQL active
        nom              : Nom du BIM Manager
        prenom           : Prénom du BIM Manager
        email            : Email unique
        mot_de_passe_hash: Mot de passe haché avec bcrypt

    Returns:
        Dictionnaire avec les infos du super_admin créé
    """
    curseur = connexion.cursor()

    try:
        # Étape 1.3 — Insérer le super_admin
        curseur.execute("""
            INSERT INTO super_admin (
                nom,
                prenom,
                email,
                mot_de_passe_hash
            )
            VALUES (%s, %s, %s, %s)
            RETURNING
                id,
                nom,
                prenom,
                email,
                date_creation;
        """, (nom, prenom, email, mot_de_passe_hash))

        ligne = curseur.fetchone()
        connexion.commit()

        logger.info(
            f"Super admin créé : {email}"
        )

        return {
            "id"           : ligne[0],
            "nom"          : ligne[1],
            "prenom"       : ligne[2],
            "email"        : ligne[3],
            "date_creation": ligne[4],
        }

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur insertion super_admin : {erreur}"
        )
        raise
    finally:
        curseur.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — REQUÊTES UTILISATEURS
# ─────────────────────────────────────────────────────────────

def inserer_utilisateur(
    connexion        : psycopg2.extensions.connection,
    nom              : str,
    prenom           : str,
    email            : str,
    mot_de_passe_hash: str,
) -> dict:
    """
    Insère un nouveau utilisateur dans la BD.
    Le statut est 'en_attente' par défaut.

    Args:
        connexion        : Connexion PostgreSQL active
        nom              : Nom du utilisateur
        prenom           : Prénom du utilisateur
        email            : Email unique en minuscules
        mot_de_passe_hash: Mot de passe haché avec bcrypt

    Returns:
        Dictionnaire avec les infos du utilisateur créé
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.1 — Insérer le utilisateur
        curseur.execute("""
            INSERT INTO utilisateurs (
                nom,
                prenom,
                email,
                mot_de_passe_hash
            )
            VALUES (%s, %s, %s, %s)
            RETURNING
                id,
                nom,
                prenom,
                email,
                role,
                statut,
                date_creation;
        """, (nom, prenom, email, mot_de_passe_hash))

        ligne = curseur.fetchone()
        connexion.commit()

        logger.info(
            f"Utilisateur créé : {email}"
        )

        return {
            "id"           : ligne[0],
            "nom"          : ligne[1],
            "prenom"       : ligne[2],
            "email"        : ligne[3],
            "role"         : ligne[4],
            "statut"       : ligne[5],
            "date_creation": ligne[6],
        }

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur insertion utilisateur : {erreur}"
        )
        raise
    finally:
        curseur.close()


def obtenir_utilisateur_par_email(
    connexion: psycopg2.extensions.connection,
    email    : str,
) -> dict | None:
    """
    Récupère un utilisateur par son email.
    Utilisée lors du login et pour vérifier l'unicité.

    Args:
        connexion: Connexion PostgreSQL active
        email    : Email du utilisateur

    Returns:
        Dictionnaire avec les infos ou None si absent
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.2 — Rechercher l'utilisateur par email
        curseur.execute("""
            SELECT
                id,
                nom,
                prenom,
                email,
                mot_de_passe_hash,
                role,
                statut,
                date_creation
            FROM utilisateurs
            WHERE email = %s;
        """, (email,))

        ligne = curseur.fetchone()
        if not ligne:
            return None

        return {
            "id"               : ligne[0],
            "nom"              : ligne[1],
            "prenom"           : ligne[2],
            "email"            : ligne[3],
            "mot_de_passe_hash": ligne[4],
            "role"             : ligne[5],
            "statut"           : ligne[6],
            "date_creation"    : ligne[7],
        }

    except Exception as erreur:
        logger.error(
            f"Erreur obtenir utilisateur "
            f"par email : {erreur}"
        )
        raise
    finally:
        curseur.close()


def obtenir_utilisateur_par_id(
    connexion     : psycopg2.extensions.connection,
    id_utilisateur: int,
) -> dict | None:
    """
    Récupère un utilisateur par son ID.
    Utilisée pour afficher les détails d'un utilisateur.

    Args:
        connexion     : Connexion PostgreSQL active
        id_utilisateur: ID du utilisateur

    Returns:
        Dictionnaire avec les infos ou None si absent
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.3 — Rechercher l'utilisateur par ID
        curseur.execute("""
            SELECT
                id,
                nom,
                prenom,
                email,
                role,
                statut,
                date_creation
            FROM utilisateurs
            WHERE id = %s;
        """, (id_utilisateur,))

        ligne = curseur.fetchone()
        if not ligne:
            return None

        return {
            "id"           : ligne[0],
            "nom"          : ligne[1],
            "prenom"       : ligne[2],
            "email"        : ligne[3],
            "role"         : ligne[4],
            "statut"       : ligne[5],
            "date_creation": ligne[6],
        }

    except Exception as erreur:
        logger.error(
            f"Erreur obtenir utilisateur "
            f"par ID : {erreur}"
        )
        raise
    finally:
        curseur.close()


def lister_utilisateurs(
    connexion: psycopg2.extensions.connection,
) -> list[dict]:
    """
    Récupère la liste de tous les utilisateurs.
    Les mots de passe ne sont jamais inclus.

    Args:
        connexion: Connexion PostgreSQL active

    Returns:
        Liste de dictionnaires avec les infos de base
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.4 — Récupérer tous les utilisateurs
        curseur.execute("""
            SELECT
                id,
                nom,
                prenom,
                email,
                role,
                statut,
                date_creation
            FROM utilisateurs
            ORDER BY nom, prenom;
        """)

        return [
            {
                "id"           : ligne[0],
                "nom"          : ligne[1],
                "prenom"       : ligne[2],
                "email"        : ligne[3],
                "role"         : ligne[4],
                "statut"       : ligne[5],
                "date_creation": ligne[6],
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


def lister_utilisateurs_en_attente(
    connexion: psycopg2.extensions.connection,
) -> list[dict]:
    """
    Récupère les utilisateurs en attente d'approbation.
    Utilisée par le super_admin pour gérer les demandes.

    Args:
        connexion: Connexion PostgreSQL active

    Returns:
        Liste des utilisateurs avec statut 'en_attente'
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.5 — Filtrer par statut en_attente
        curseur.execute("""
            SELECT
                id,
                nom,
                prenom,
                email,
                role,
                statut,
                date_creation
            FROM utilisateurs
            WHERE statut = 'en_attente'
            ORDER BY date_creation;
        """)

        return [
            {
                "id"           : ligne[0],
                "nom"          : ligne[1],
                "prenom"       : ligne[2],
                "email"        : ligne[3],
                "role"         : ligne[4],
                "statut"       : ligne[5],
                "date_creation": ligne[6],
            }
            for ligne in curseur.fetchall()
        ]

    except Exception as erreur:
        logger.error(
            f"Erreur listage en attente : {erreur}"
        )
        raise
    finally:
        curseur.close()


def mettre_a_jour_statut_utilisateur(
    connexion     : psycopg2.extensions.connection,
    id_utilisateur: int,
    nouveau_statut: str,
) -> bool:
    """
    Met à jour le statut d'un utilisateur.
    Utilisée pour approuver ou refuser un compte.

    Args:
        connexion     : Connexion PostgreSQL active
        id_utilisateur: ID du utilisateur
        nouveau_statut: 'approuve' ou 'refuse'

    Returns:
        True si la mise à jour a réussi
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.6 — Mettre à jour le statut
        curseur.execute("""
            UPDATE utilisateurs
            SET statut = %s
            WHERE id = %s;
        """, (nouveau_statut, id_utilisateur))

        connexion.commit()
        logger.info(
            f"Statut utilisateur {id_utilisateur} "
            f"→ {nouveau_statut}"
        )
        return True

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur mise à jour statut : {erreur}"
        )
        raise
    finally:
        curseur.close()


def mettre_a_jour_utilisateur(
    connexion     : psycopg2.extensions.connection,
    id_utilisateur: int,
    champs        : dict,
) -> dict | None:
    """
    Met à jour les champs fournis d'un utilisateur.
    Seuls les champs présents dans le dict sont modifiés.

    Args:
        connexion     : Connexion PostgreSQL active
        id_utilisateur: ID du utilisateur
        champs        : Dict avec les champs à modifier

    Returns:
        Dictionnaire avec les infos mises à jour
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.7 — Construire la requête dynamiquement
        """
        On construit la clause SET dynamiquement pour
        ne modifier que les champs fournis.
        """
        parties_set = [
            f"{cle} = %s" for cle in champs.keys()
        ]
        valeurs = list(champs.values())
        valeurs.append(id_utilisateur)

        curseur.execute(f"""
            UPDATE utilisateurs
            SET {', '.join(parties_set)}
            WHERE id = %s
            RETURNING
                id, nom, prenom, email,
                role, statut, date_creation;
        """, valeurs)

        ligne = curseur.fetchone()
        connexion.commit()

        logger.info(
            f"Utilisateur {id_utilisateur} mis à jour."
        )

        return {
            "id"           : ligne[0],
            "nom"          : ligne[1],
            "prenom"       : ligne[2],
            "email"        : ligne[3],
            "role"         : ligne[4],
            "statut"       : ligne[5],
            "date_creation": ligne[6],
        }

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur mise à jour utilisateur : {erreur}"
        )
        raise
    finally:
        curseur.close()


def supprimer_utilisateur(
    connexion     : psycopg2.extensions.connection,
    id_utilisateur: int,
) -> bool:
    """
    Supprime un utilisateur de la BD.
    Les keynotes créés par cet utilisateur sont conservés
    grâce au ON DELETE SET NULL sur cree_par et
    modifie_par_id dans les tables categories et notes.

    Args:
        connexion     : Connexion PostgreSQL active
        id_utilisateur: ID du utilisateur à supprimer

    Returns:
        True si la suppression a réussi
    """
    curseur = connexion.cursor()

    try:
        # Étape 2.8 — Supprimer l'utilisateur
        curseur.execute("""
            DELETE FROM utilisateurs
            WHERE id = %s;
        """, (id_utilisateur,))

        connexion.commit()
        logger.info(
            f"Utilisateur {id_utilisateur} supprimé."
        )
        return True

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur suppression utilisateur : {erreur}"
        )
        raise
    finally:
        curseur.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — REQUÊTES RÉINITIALISATION MOT DE PASSE
# ─────────────────────────────────────────────────────────────

def inserer_demande_reinitialisation(
    connexion        : psycopg2.extensions.connection,
    id_utilisateur   : int,
    nouveau_mdp_hash : str,
) -> dict:
    """
    Insère ou remplace la demande de réinitialisation
    de mot de passe d'un utilisateur.
    ON CONFLICT remplace l'ancienne demande par la nouvelle.

    Args:
        connexion       : Connexion PostgreSQL active
        id_utilisateur  : ID du utilisateur
        nouveau_mdp_hash: Nouveau mot de passe haché

    Returns:
        Dictionnaire avec les infos de la demande
    """
    curseur = connexion.cursor()

    try:
        # Étape 3.1 — Insérer ou remplacer la demande
        """
        ON CONFLICT (id_utilisateur) DO UPDATE remplace
        l'ancienne demande — on garde toujours la dernière.
        """
        curseur.execute("""
            INSERT INTO reinitialisation_mdp (
                id_utilisateur,
                nouveau_mdp_hash,
                statut
            )
            VALUES (%s, %s, 'en_attente')
            ON CONFLICT (id_utilisateur)
            DO UPDATE SET
                nouveau_mdp_hash = EXCLUDED.nouveau_mdp_hash,
                statut           = 'en_attente',
                date_demande     = CURRENT_TIMESTAMP
            RETURNING id, id_utilisateur, statut, date_demande;
        """, (id_utilisateur, nouveau_mdp_hash))

        ligne = curseur.fetchone()
        connexion.commit()

        logger.info(
            f"Demande reset mdp pour "
            f"utilisateur {id_utilisateur}."
        )

        return {
            "id"            : ligne[0],
            "id_utilisateur": ligne[1],
            "statut"        : ligne[2],
            "date_demande"  : ligne[3],
        }

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur demande reset mdp : {erreur}"
        )
        raise
    finally:
        curseur.close()


def lister_demandes_reinitialisation(
    connexion: psycopg2.extensions.connection,
) -> list[dict]:
    """
    Récupère toutes les demandes de réinitialisation
    en attente d'approbation par le super_admin.

    Args:
        connexion: Connexion PostgreSQL active

    Returns:
        Liste des demandes en attente avec infos utilisateur
    """
    curseur = connexion.cursor()

    try:
        # Étape 3.2 — Récupérer les demandes en attente
        """
        On joint avec utilisateurs pour afficher le nom
        et l'email du demandeur dans l'interface admin.
        """
        curseur.execute("""
            SELECT
                r.id,
                r.id_utilisateur,
                u.nom,
                u.prenom,
                u.email,
                r.statut,
                r.date_demande
            FROM reinitialisation_mdp r
            JOIN utilisateurs u
                ON u.id = r.id_utilisateur
            WHERE r.statut = 'en_attente'
            ORDER BY r.date_demande;
        """)

        return [
            {
                "id"            : ligne[0],
                "id_utilisateur": ligne[1],
                "nom"           : ligne[2],
                "prenom"        : ligne[3],
                "email"         : ligne[4],
                "statut"        : ligne[5],
                "date_demande"  : ligne[6],
            }
            for ligne in curseur.fetchall()
        ]

    except Exception as erreur:
        logger.error(
            f"Erreur listage demandes reset : {erreur}"
        )
        raise
    finally:
        curseur.close()


def approuver_reinitialisation(
    connexion     : psycopg2.extensions.connection,
    id_utilisateur: int,
) -> bool:
    """
    Approuve la demande de réinitialisation et applique
    le nouveau mot de passe haché à l'utilisateur.
    Supprime la demande après application.

    Args:
        connexion     : Connexion PostgreSQL active
        id_utilisateur: ID du utilisateur

    Returns:
        True si l'approbation a réussi
    """
    curseur = connexion.cursor()

    try:
        # Étape 3.3 — Récupérer le nouveau mot de passe
        curseur.execute("""
            SELECT nouveau_mdp_hash
            FROM reinitialisation_mdp
            WHERE id_utilisateur = %s
            AND statut = 'en_attente';
        """, (id_utilisateur,))

        ligne = curseur.fetchone()
        if not ligne:
            raise ValueError(
                "Aucune demande en attente pour "
                "cet utilisateur."
            )

        nouveau_mdp_hash = ligne[0]

        # Étape 3.4 — Appliquer le nouveau mot de passe
        curseur.execute("""
            UPDATE utilisateurs
            SET mot_de_passe_hash = %s
            WHERE id = %s;
        """, (nouveau_mdp_hash, id_utilisateur))

        # Étape 3.5 — Supprimer la demande traitée
        curseur.execute("""
            DELETE FROM reinitialisation_mdp
            WHERE id_utilisateur = %s;
        """, (id_utilisateur,))

        connexion.commit()
        logger.info(
            f"Reset mdp approuvé pour "
            f"utilisateur {id_utilisateur}."
        )
        return True

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur approbation reset mdp : {erreur}"
        )
        raise
    finally:
        curseur.close()


def refuser_reinitialisation(
    connexion     : psycopg2.extensions.connection,
    id_utilisateur: int,
) -> bool:
    """
    Refuse et supprime la demande de réinitialisation.

    Args:
        connexion     : Connexion PostgreSQL active
        id_utilisateur: ID du utilisateur

    Returns:
        True si le refus a réussi
    """
    curseur = connexion.cursor()

    try:
        # Étape 3.6 — Supprimer la demande refusée
        curseur.execute("""
            DELETE FROM reinitialisation_mdp
            WHERE id_utilisateur = %s;
        """, (id_utilisateur,))

        connexion.commit()
        logger.info(
            f"Reset mdp refusé pour "
            f"utilisateur {id_utilisateur}."
        )
        return True

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur refus reset mdp : {erreur}"
        )
        raise
    finally:
        curseur.close()