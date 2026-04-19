"""
services/auth.py
----------------
Logique métier — Authentification.

Rôle :
    - Hacher et vérifier les mots de passe (bcrypt)
    - Générer et décoder les tokens JWT
    - Gérer l'inscription des collaborateurs
    - Gérer la connexion admin et collaborateur
    - Gérer les demandes de réinitialisation mdp

Importation :
    from app.services.auth import (
        hacher_mot_de_passe,
        verifier_mot_de_passe,
        generer_token_jwt,
        inscrire_collaborateur,
        connecter_admin,
        connecter_collaborateur,
    )
"""

from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import (
    SECRET_KEY,
    ALGORITHME_JWT,
    DUREE_TOKEN_MINUTES,
)
from app.database.connection import creer_connexion
from app.logger import get_logger
from app.repositories import utilisateurs as repo_utilisateurs


# Initialiser le logger pour ce module
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — HACHAGE DES MOTS DE PASSE
# ─────────────────────────────────────────────────────────────

def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """
    Hache un mot de passe avec bcrypt.
    bcrypt est intentionnellement lent pour résister
    aux attaques par force brute.

    Args:
        mot_de_passe: Mot de passe en clair

    Returns:
        Mot de passe haché sous forme de chaîne
    """
    # Étape 1.1 — Hacher avec bcrypt et sel aléatoire
    """
    gensalt() génère un sel aléatoire à chaque appel.
    Le même mot de passe donnera un hash différent
    à chaque fois — impossible à pré-calculer.
    """
    mot_de_passe_bytes = mot_de_passe.encode("utf-8")
    sel = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(mot_de_passe_bytes, sel)
    return hash_bytes.decode("utf-8")


def verifier_mot_de_passe(
    mot_de_passe      : str,
    mot_de_passe_hash : str,
) -> bool:
    """
    Vérifie qu'un mot de passe correspond à son hash.

    Args:
        mot_de_passe     : Mot de passe en clair à vérifier
        mot_de_passe_hash: Hash stocké en BD

    Returns:
        True si le mot de passe est correct, False sinon
    """
    # Étape 1.2 — Comparer avec bcrypt
    """
    bcrypt.checkpw gère la comparaison de façon sécurisée
    en évitant les attaques par timing (timing attacks).
    """
    mot_de_passe_bytes = mot_de_passe.encode("utf-8")
    hash_bytes = mot_de_passe_hash.encode("utf-8")
    return bcrypt.checkpw(mot_de_passe_bytes, hash_bytes)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — GESTION DES TOKENS JWT
# ─────────────────────────────────────────────────────────────

def generer_token_jwt(donnees: dict) -> str:
    """
    Génère un token JWT signé avec une expiration.

    Args:
        donnees: Dictionnaire avec les infos à encoder
                 (id, email, role)

    Returns:
        Token JWT signé sous forme de chaîne
    """
    # Étape 2.1 — Ajouter la date d'expiration
    """
    exp est un champ standard JWT qui indique quand
    le token expire. Après cette date, le token
    sera rejeté automatiquement lors du décodage.
    """
    donnees_a_encoder = donnees.copy()
    expiration = datetime.utcnow() + timedelta(
        minutes=DUREE_TOKEN_MINUTES
    )
    donnees_a_encoder.update({"exp": expiration})

    # Étape 2.2 — Signer et encoder le token
    return jwt.encode(
        donnees_a_encoder,
        SECRET_KEY,
        algorithm=ALGORITHME_JWT
    )


def decoder_token_jwt(token: str) -> dict:
    """
    Décode et valide un token JWT.

    Args:
        token: Token JWT à décoder

    Returns:
        Dictionnaire avec les infos décodées

    Raises:
        JWTError: Si le token est invalide ou expiré
    """
    # Étape 2.3 — Décoder et valider le token
    """
    jwt.decode vérifie automatiquement :
        - La signature (token non falsifié)
        - La date d'expiration (token non expiré)
    """
    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHME_JWT]
    )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — INSCRIPTION
# ─────────────────────────────────────────────────────────────

def inscrire_collaborateur(
    nom          : str,
    prenom       : str,
    email        : str,
    mot_de_passe : str,
) -> dict:
    """
    Inscrit un nouveau collaborateur avec statut
    'en_attente'. Le super_admin doit approuver
    le compte avant que le collaborateur puisse
    se connecter.

    Args:
        nom         : Nom du collaborateur
        prenom      : Prénom du collaborateur
        email       : Email unique en minuscules
        mot_de_passe: Mot de passe en clair

    Returns:
        Dictionnaire avec les infos du compte créé

    Raises:
        ValueError: Si l'email est déjà utilisé
    """
    connexion = creer_connexion()

    try:
        # Étape 3.1 — Normaliser l'email en minuscules
        """
        On stocke toujours l'email en minuscules pour
        éviter les doublons dus à la casse différente.
        Ex: Jean@exemple.com et jean@exemple.com
        seraient deux comptes différents sans cette règle.
        """
        email_normalise = email.lower().strip()

        # Étape 3.2 — Vérifier l'unicité de l'email
        utilisateur_existant = (
            repo_utilisateurs.obtenir_utilisateur_par_email(
                connexion, email_normalise
            )
        )
        if utilisateur_existant:
            raise ValueError(
                f"L'email '{email_normalise}' "
                "est déjà utilisé."
            )

        # Étape 3.3 — Hacher le mot de passe
        mot_de_passe_hash = hacher_mot_de_passe(
            mot_de_passe
        )

        # Étape 3.4 — Insérer le collaborateur
        return repo_utilisateurs.inserer_utilisateur(
            connexion,
            nom.strip(),
            prenom.strip(),
            email_normalise,
            mot_de_passe_hash,
        )

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur inscription collaborateur : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — CONNEXION
# ─────────────────────────────────────────────────────────────

def connecter_admin(
    email        : str,
    mot_de_passe : str,
) -> dict:
    """
    Authentifie le super_admin et génère un token JWT.

    Args:
        email       : Email du super_admin
        mot_de_passe: Mot de passe en clair

    Returns:
        Dictionnaire avec token JWT et infos de session

    Raises:
        ValueError: Si les identifiants sont incorrects
    """
    connexion = creer_connexion()

    try:
        # Étape 4.1 — Récupérer le super_admin
        admin = (
            repo_utilisateurs
            .obtenir_super_admin_par_email(
                connexion, email.lower().strip()
            )
        )

        # Étape 4.2 — Vérifier les identifiants
        """
        On vérifie d'abord l'existence du compte,
        puis le mot de passe pour éviter de révéler
        si l'email existe ou non.
        """
        if not admin or not verifier_mot_de_passe(
            mot_de_passe, admin["mot_de_passe_hash"]
        ):
            raise ValueError(
                "Email ou mot de passe incorrect."
            )

        # Étape 4.3 — Générer le token JWT
        token = generer_token_jwt({
            "id"   : admin["id"],
            "email": admin["email"],
            "role" : "super_admin",
        })

        logger.info(
            f"Connexion admin : {admin['email']}"
        )

        return {
            "access_token": token,
            "token_type"  : "bearer",
            "role"        : "super_admin",
        }

    except ValueError:
        logger.warning(
            f"Tentative de connexion admin échouée : "
            f"{email}"
        )
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur connexion admin : {erreur}"
        )
        raise
    finally:
        connexion.close()


def connecter_collaborateur(
    email        : str,
    mot_de_passe : str,
) -> dict:
    """
    Authentifie un collaborateur et génère un token JWT.
    Le collaborateur doit avoir le statut 'approuve'.

    Args:
        email       : Email du collaborateur
        mot_de_passe: Mot de passe en clair

    Returns:
        Dictionnaire avec token JWT et infos de session

    Raises:
        ValueError: Si les identifiants sont incorrects
                    ou le compte n'est pas approuvé
    """
    connexion = creer_connexion()

    try:
        # Étape 4.4 — Récupérer le collaborateur
        utilisateur = (
            repo_utilisateurs.obtenir_utilisateur_par_email(
                connexion, email.lower().strip()
            )
        )

        # Étape 4.5 — Vérifier les identifiants
        if not utilisateur or not verifier_mot_de_passe(
            mot_de_passe,
            utilisateur["mot_de_passe_hash"]
        ):
            raise ValueError(
                "Email ou mot de passe incorrect."
            )

        # Étape 4.6 — Vérifier le statut du compte
        """
        Un compte 'en_attente' ou 'refuse' ne peut
        pas se connecter. Seul un compte 'approuve'
        par le super_admin a accès à l'application.
        """
        if utilisateur["statut"] != "approuve":
            raise ValueError(
                "Votre compte est en attente "
                "d'approbation par le BIM Manager."
            )

        # Étape 4.7 — Générer le token JWT
        token = generer_token_jwt({
            "id"   : utilisateur["id"],
            "email": utilisateur["email"],
            "role" : utilisateur["role"],
        })

        logger.info(
            f"Connexion collaborateur : "
            f"{utilisateur['email']}"
        )

        return {
            "access_token": token,
            "token_type"  : "bearer",
            "role"        : utilisateur["role"],
        }

    except ValueError:
        logger.warning(
            f"Tentative de connexion échouée : {email}"
        )
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur connexion collaborateur : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 5 — RÉINITIALISATION MOT DE PASSE
# ─────────────────────────────────────────────────────────────

def demander_reinitialisation_mdp(
    email            : str,
    nouveau_mdp      : str,
    confirmer_mdp    : str,
) -> dict:
    """
    Soumet une demande de réinitialisation de mot de passe.
    La nouvelle demande remplace l'ancienne si elle existe.
    Le super_admin doit approuver avant application.

    Args:
        email        : Email du collaborateur
        nouveau_mdp  : Nouveau mot de passe en clair
        confirmer_mdp: Confirmation du nouveau mot de passe

    Returns:
        Dictionnaire confirmant la demande soumise

    Raises:
        ValueError: Si l'email est inconnu ou les mdp
                    ne correspondent pas
    """
    connexion = creer_connexion()

    try:
        # Étape 5.1 — Vérifier la confirmation
        if nouveau_mdp != confirmer_mdp:
            raise ValueError(
                "Les mots de passe ne correspondent pas."
            )

        # Étape 5.2 — Vérifier que l'utilisateur existe
        utilisateur = (
            repo_utilisateurs.obtenir_utilisateur_par_email(
                connexion, email.lower().strip()
            )
        )
        if not utilisateur:
            raise ValueError(
                "Aucun compte associé à cet email."
            )

        # Étape 5.3 — Hacher le nouveau mot de passe
        nouveau_mdp_hash = hacher_mot_de_passe(nouveau_mdp)

        # Étape 5.4 — Insérer ou remplacer la demande
        return (
            repo_utilisateurs
            .inserer_demande_reinitialisation(
                connexion,
                utilisateur["id"],
                nouveau_mdp_hash,
            )
        )

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur demande reset mdp : {erreur}"
        )
        raise
    finally:
        connexion.close()