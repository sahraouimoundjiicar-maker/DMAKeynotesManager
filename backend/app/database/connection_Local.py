"""
database/connection.py
----------------------
Connexions PostgreSQL et création des tables.

Rôle :
    - Créer et retourner les connexions à la BD unique
    - Créer la BD DMAKeynotesManager et toutes ses tables
    - Créer les index sur les colonnes importantes
    - Initialiser l'application au premier démarrage

Architecture :
    Une seule BD PostgreSQL : DMAKeynotesManager
    Tables :
        - super_admin
        - utilisateurs
        - reinitialisation_mdp
        - projets
        - acces_projet
        - categories
        - notes
        - historique

Importation :
    from app.database.connection import (
        creer_connexion,
        initialiser_application,
    )
"""

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from app.config import POSTGRES_CONFIG, NOM_BD
from app.logger import get_logger


# Initialiser le logger pour ce module
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — FONCTIONS DE CONNEXION
# ─────────────────────────────────────────────────────────────

def creer_connexion_admin() -> psycopg2.extensions.connection:
    """
    Crée une connexion à la BD 'postgres' (admin).
    Utilisée uniquement pour créer la BD principale.
    AUTOCOMMIT est requis pour CREATE DATABASE.

    Returns:
        Connexion PostgreSQL admin avec AUTOCOMMIT

    Raises:
        psycopg2.Error: Si la connexion échoue
    """
    # Étape 1.1 — Connexion admin avec AUTOCOMMIT
    """
    AUTOCOMMIT est nécessaire pour CREATE DATABASE.
    Cette connexion ne sert qu'à créer la BD principale
    et n'est utilisée qu'une seule fois au démarrage.
    """
    connexion = psycopg2.connect(
        **POSTGRES_CONFIG,
        dbname          = "postgres",
        client_encoding = "utf-8",
    )
    connexion.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return connexion


def creer_connexion() -> psycopg2.extensions.connection:
    """
    Crée et retourne une connexion à la BD principale.
    C'est la seule fonction de connexion utilisée par
    tous les repositories de l'application.

    Returns:
        Connexion PostgreSQL à DMAKeynotesManager

    Raises:
        psycopg2.Error: Si la connexion échoue
    """
    # Étape 1.2 — Connexion à la BD principale
    return psycopg2.connect(
        **POSTGRES_CONFIG,
        dbname=NOM_BD
    )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — CRÉATION DE LA BASE DE DONNÉES
# ─────────────────────────────────────────────────────────────

def creer_base_de_donnees() -> None:
    """
    Crée la BD DMAKeynotesManager si elle n'existe pas.
    Encodage UTF-8 pour supporter les caractères français.
    """
    connexion_admin = creer_connexion_admin()
    curseur = connexion_admin.cursor()

    try:
        # Étape 2.1 — Vérifier si la BD existe déjà
        curseur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s;",
            (NOM_BD,)
        )
        bd_existe = curseur.fetchone()

        # Étape 2.2 — Créer la BD si absente
        """
        UTF-8 est obligatoire pour supporter les accents
        dans les descriptions de keynotes (é, è, ê, à...).
        """
        if not bd_existe:
            curseur.execute(
                sql.SQL(
                    "CREATE DATABASE {} ENCODING 'UTF8';"
                ).format(sql.Identifier(NOM_BD))
            )
            logger.info(f"BD '{NOM_BD}' créée avec succès.")
        else:
            logger.info(f"BD '{NOM_BD}' existe déjà.")

    except Exception as erreur:
        logger.error(f"Erreur création BD : {erreur}")
        raise
    finally:
        curseur.close()
        connexion_admin.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — CRÉATION DES TABLES UTILISATEURS
# ─────────────────────────────────────────────────────────────

def creer_tables_utilisateurs(
    curseur: psycopg2.extensions.cursor
) -> None:
    """
    Crée les tables liées à la gestion des utilisateurs.

    Tables créées :
        - super_admin         (compte unique du BIM Manager)
        - utilisateurs        (collaborateurs)
        - reinitialisation_mdp (demandes de reset mdp)

    Args:
        curseur: Curseur PostgreSQL actif
    """
    # Étape 3.1 — Table super_admin
    """
    Contient un seul enregistrement : le BIM Manager.
    C'est lui qui gère les projets et les utilisateurs.
    """
    curseur.execute("""
        CREATE TABLE IF NOT EXISTS super_admin (
            id                SERIAL       PRIMARY KEY,
            nom               VARCHAR(100) NOT NULL,
            prenom            VARCHAR(100) NOT NULL,
            email             VARCHAR(150) NOT NULL UNIQUE,
            mot_de_passe_hash TEXT         NOT NULL,
            date_creation     TIMESTAMP
                              DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Étape 3.2 — Table utilisateurs
    """
    Contient tous les collaborateurs de l'application.
    statut gère le flux d'approbation :
        'en_attente' → nouveau compte en attente
        'approuve'   → accès autorisé
        'refuse'     → compte refusé et supprimé
    """
    curseur.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id                SERIAL       PRIMARY KEY,
            nom               VARCHAR(100) NOT NULL,
            prenom            VARCHAR(100) NOT NULL,
            email             VARCHAR(150) NOT NULL UNIQUE,
            mot_de_passe_hash TEXT         NOT NULL,
            role              VARCHAR(20)  NOT NULL
                              DEFAULT 'editeur'
                              CHECK (role = 'editeur'),
            statut            VARCHAR(20)  NOT NULL
                              DEFAULT 'en_attente'
                              CHECK (statut IN (
                                  'en_attente',
                                  'approuve',
                                  'refuse'
                              )),
            date_creation     TIMESTAMP
                              DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Étape 3.3 — Table reinitialisation_mdp
    """
    Stocke les demandes de réinitialisation de mot de passe.
    UNIQUE sur id_utilisateur : une seule demande active
    par utilisateur — la nouvelle remplace l'ancienne.
    """
    curseur.execute("""
        CREATE TABLE IF NOT EXISTS reinitialisation_mdp (
            id               SERIAL      PRIMARY KEY,
            id_utilisateur   INT         NOT NULL UNIQUE
                             REFERENCES utilisateurs(id)
                             ON DELETE CASCADE,
            nouveau_mdp_hash TEXT        NOT NULL,
            statut           VARCHAR(20) NOT NULL
                             DEFAULT 'en_attente'
                             CHECK (statut IN (
                                 'en_attente',
                                 'approuve',
                                 'refuse'
                             )),
            date_demande     TIMESTAMP
                             DEFAULT CURRENT_TIMESTAMP
        );
    """)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — CRÉATION DES TABLES PROJETS
# ─────────────────────────────────────────────────────────────

def creer_tables_projets(
    curseur: psycopg2.extensions.cursor
) -> None:
    """
    Crée les tables liées à la gestion des projets.

    Tables créées :
        - projets       (projets Revit)
        - acces_projet  (accès des collaborateurs)

    Args:
        curseur: Curseur PostgreSQL actif
    """
    # Étape 4.1 — Table projets
    """
    Contient tous les projets Revit de l'application.
    txt_a_jour indique si le fichier .txt est synchronisé
    avec les données de la BD :
        False → des modifications ont été faites
        True  → le fichier .txt est à jour après export
    """
    curseur.execute("""
        CREATE TABLE IF NOT EXISTS projets (
            id                  SERIAL       PRIMARY KEY,
            nom                 VARCHAR(200) NOT NULL UNIQUE,
            txt_a_jour          BOOLEAN      NOT NULL
                                DEFAULT FALSE,
            date_dernier_export TIMESTAMP,
            cree_par            INT          NOT NULL
                                REFERENCES super_admin(id),
            date_creation       TIMESTAMP
                                DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Étape 4.2 — Table acces_projet
    """
    Gère les accès des collaborateurs aux projets.
    Un collaborateur peut avoir accès à plusieurs projets.
    UNIQUE(id_projet, id_utilisateur) évite les doublons.
    """
    curseur.execute("""
        CREATE TABLE IF NOT EXISTS acces_projet (
            id               SERIAL    PRIMARY KEY,
            id_projet        INT       NOT NULL
                             REFERENCES projets(id)
                             ON DELETE CASCADE,
            id_utilisateur   INT       NOT NULL
                             REFERENCES utilisateurs(id)
                             ON DELETE CASCADE,
            date_attribution TIMESTAMP
                             DEFAULT CURRENT_TIMESTAMP,
            attribue_par     INT       NOT NULL
                             REFERENCES super_admin(id),
            UNIQUE (id_projet, id_utilisateur)
        );
    """)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 5 — CRÉATION DES TABLES KEYNOTES
# ─────────────────────────────────────────────────────────────

def creer_tables_keynotes(
    curseur: psycopg2.extensions.cursor
) -> None:
    """
    Crée les tables liées à la gestion des keynotes.

    Tables créées :
        - categories  (catégories de keynotes)
        - notes       (keynotes)

    Args:
        curseur: Curseur PostgreSQL actif
    """
    # Étape 5.1 — Table categories
    """
    Contient les catégories de keynotes par projet.
    UNIQUE(id_projet, numero) : le numéro est unique
    par projet mais peut se répéter dans d'autres projets.
    version : champ pour le verrouillage optimiste —
    incrémenté à chaque modification pour détecter
    les conflits entre collaborateurs.
    """
    curseur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id                SERIAL       PRIMARY KEY,
            id_projet         INT          NOT NULL
                              REFERENCES projets(id)
                              ON DELETE CASCADE,
            numero            VARCHAR(50)  NOT NULL,
            description       VARCHAR(500) NOT NULL,
            cree_par          INT
                              REFERENCES utilisateurs(id)
                              ON DELETE SET NULL,
            modifie_par_id    INT
                              REFERENCES utilisateurs(id)
                              ON DELETE SET NULL,
            date_modification TIMESTAMP
                              DEFAULT CURRENT_TIMESTAMP,
            version           INT NOT NULL DEFAULT 1,
            UNIQUE (id_projet, numero)
        );
    """)

    # Étape 5.2 — Table notes
    """
    Contient les keynotes par projet.
    id_categorie est OBLIGATOIRE — une note sans catégorie
    n'est pas autorisée dans notre application.
    ON DELETE RESTRICT sur id_categorie empêche la
    suppression d'une catégorie qui contient des notes.
    UNIQUE(id_projet, numero) : même logique que categories.
    """
    curseur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id                SERIAL       PRIMARY KEY,
            id_projet         INT          NOT NULL
                              REFERENCES projets(id)
                              ON DELETE CASCADE,
            id_categorie      INT          NOT NULL
                              REFERENCES categories(id)
                              ON DELETE RESTRICT,
            numero            VARCHAR(50)  NOT NULL,
            description       VARCHAR(500) NOT NULL,
            cree_par          INT
                              REFERENCES utilisateurs(id)
                              ON DELETE SET NULL,
            modifie_par_id    INT
                              REFERENCES utilisateurs(id)
                              ON DELETE SET NULL,
            date_modification TIMESTAMP
                              DEFAULT CURRENT_TIMESTAMP,
            date_creation     TIMESTAMP
                              DEFAULT CURRENT_TIMESTAMP,
            version           INT NOT NULL DEFAULT 1,
            UNIQUE (id_projet, numero)
        );
    """)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 6 — CRÉATION DE LA TABLE HISTORIQUE
# ─────────────────────────────────────────────────────────────

def creer_table_historique(
    curseur: psycopg2.extensions.cursor
) -> None:
    """
    Crée la table historique pour la traçabilité complète
    de toutes les actions effectuées sur les projets.

    Args:
        curseur: Curseur PostgreSQL actif
    """
    # Étape 6.1 — Table historique
    """
    Enregistre toutes les actions sur les keynotes.
    Super admin voit tout l'historique du projet.
    Collaborateur voit uniquement ses propres actions.
    effectue_par_role permet de distinguer super_admin
    des éditeurs sans FK inter-tables complexe.
    """
    curseur.execute("""
        CREATE TABLE IF NOT EXISTS historique (
            id                SERIAL      PRIMARY KEY,
            id_projet         INT         NOT NULL
                              REFERENCES projets(id)
                              ON DELETE CASCADE,
            table_cible       VARCHAR(20) NOT NULL
                              CHECK (table_cible IN (
                                  'categories',
                                  'notes',
                                  'projet'
                              )),
            id_cible          INT,
            action            VARCHAR(50) NOT NULL
                              CHECK (action IN (
                                  'creation',
                                  'modification',
                                  'suppression',
                                  'export_txt',
                                  'import_remplacement',
                                  'import_fusion_categorie',
                                  'import_fusion_note'
                              )),
            ancienne_valeur   TEXT,
            nouvelle_valeur   TEXT,
            effectue_par_id   INT         NOT NULL,
            effectue_par_role VARCHAR(20) NOT NULL
                              CHECK (effectue_par_role IN (
                                  'super_admin',
                                  'editeur'
                              )),
            date_action       TIMESTAMP
                              DEFAULT CURRENT_TIMESTAMP
        );
    """)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 7 — CRÉATION DES INDEX
# ─────────────────────────────────────────────────────────────

def creer_index(
    curseur: psycopg2.extensions.cursor
) -> None:
    """
    Crée les index sur les colonnes les plus utilisées
    dans les requêtes SQL pour améliorer les performances.

    Args:
        curseur: Curseur PostgreSQL actif
    """
    # Étape 7.1 — Index sur la table utilisateurs
    """
    email est utilisé à chaque login et vérification
    d'unicité → index essentiel.
    statut est utilisé pour filtrer les demandes
    en attente d'approbation.
    """
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS idx_utilisateurs_email
        ON utilisateurs(email);
    """)
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS idx_utilisateurs_statut
        ON utilisateurs(statut);
    """)

    # Étape 7.2 — Index sur la table acces_projet
    """
    Utilisé pour vérifier rapidement si un collaborateur
    a accès à un projet donné.
    """
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS idx_acces_projet_projet
        ON acces_projet(id_projet);
    """)
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_acces_projet_utilisateur
        ON acces_projet(id_utilisateur);
    """)

    # Étape 7.3 — Index sur la table categories
    """
    id_projet est utilisé pour récupérer toutes les
    catégories d'un projet — requête très fréquente.
    """
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS idx_categories_projet
        ON categories(id_projet);
    """)
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS idx_categories_numero
        ON categories(numero);
    """)

    # Étape 7.4 — Index sur la table notes
    """
    id_categorie est utilisé pour récupérer toutes les
    notes d'une catégorie — requête très fréquente.
    id_projet est utilisé pour la recherche globale
    dans un projet.
    """
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS idx_notes_categorie
        ON notes(id_categorie);
    """)
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS idx_notes_projet
        ON notes(id_projet);
    """)
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS idx_notes_numero
        ON notes(numero);
    """)

    # Étape 7.5 — Index sur la table historique
    """
    date_action est utilisé pour le tri et la pagination.
    effectue_par_id est utilisé pour filtrer les actions
    d'un collaborateur spécifique.
    """
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS idx_historique_projet
        ON historique(id_projet);
    """)
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS idx_historique_date
        ON historique(date_action);
    """)
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_historique_effectue_par
        ON historique(effectue_par_id);
    """)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 8 — CRÉATION DE TOUTES LES TABLES
# ─────────────────────────────────────────────────────────────

def creer_toutes_les_tables() -> None:
    """
    Crée toutes les tables et index de la BD principale.
    Appelle les fonctions de création dans l'ordre logique
    en respectant les dépendances entre tables (FK).
    """
    connexion = creer_connexion()
    curseur = connexion.cursor()

    try:
        # Étape 8.1 — Créer les tables dans l'ordre des FK
        """
        L'ordre est important pour respecter les FK :
        1. super_admin et utilisateurs (pas de dépendances)
        2. reinitialisation_mdp (dépend de utilisateurs)
        3. projets (dépend de super_admin)
        4. acces_projet (dépend de projets et utilisateurs)
        5. categories (dépend de projets)
        6. notes (dépend de categories)
        7. historique (dépend de projets)
        8. index (après toutes les tables)
        """
        creer_tables_utilisateurs(curseur)
        creer_tables_projets(curseur)
        creer_tables_keynotes(curseur)
        creer_table_historique(curseur)
        creer_index(curseur)

        connexion.commit()
        logger.info("Toutes les tables créées avec succès.")

    except Exception as erreur:
        connexion.rollback()
        logger.error(
            f"Erreur création tables : {erreur}"
        )
        raise
    finally:
        curseur.close()
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 9 — INITIALISATION DE L'APPLICATION
# ─────────────────────────────────────────────────────────────

def initialiser_application() -> None:
    """
    Initialise l'application au premier démarrage.
    Crée la BD et toutes les tables si elles n'existent pas.
    Appelée automatiquement depuis main.py au démarrage.
    """
    # Étape 9.1 — Créer la BD principale
    logger.info("Initialisation de DMAKeynotesManager...")
    creer_base_de_donnees()

    # Étape 9.2 — Créer toutes les tables
    creer_toutes_les_tables()

    logger.info("Application initialisée avec succès.")