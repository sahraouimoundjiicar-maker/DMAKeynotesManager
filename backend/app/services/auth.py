"""
api/routers/auth.py
-------------------
Routes d'authentification — /api/v1/auth/...
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from app.logger import get_logger
from app.models.schemas.auth import (
    LoginAdminModele,
    LoginutilisateurModele,
    RegisterModele,
    ReinitialisationMdpModele,
    TokenModele,
)
from app.models.schemas.utilisateurs import (
    MessageReponseModele,
    UtilisateurReponseModele,
)
from app.services import auth as service_auth

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentification"])


# ─────────────────────────────────────────────────────────────
# ÉTAPE 0 — MODÈLE UNIFIÉ POUR LA CONNEXION
# ─────────────────────────────────────────────────────────────

class LoginUnifieModele(BaseModel):
    """Modèle unifié pour la connexion (admin + utilisateur)."""
    email        : EmailStr
    mot_de_passe : str


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — INSCRIPTION
# ─────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UtilisateurReponseModele,
    status_code=status.HTTP_201_CREATED,
    summary="Inscription d'un utilisateur",
)
def inscrire_utilisateur(donnees: RegisterModele) -> dict:
    """
    Inscrit un nouveau utilisateur avec le statut 'en_attente'.
    Le super_admin doit approuver le compte avant connexion.
    """
    try:
        return service_auth.inscrire_collaborateur(
            nom          = donnees.nom,
            prenom       = donnees.prenom,
            email        = donnees.email,
            mot_de_passe = donnees.mot_de_passe,
        )
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail      = str(erreur),
        )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — CONNEXION UNIFIÉE
# ─────────────────────────────────────────────────────────────

# Messages du backend qui indiquent un compte en attente.
# Utilisés pour retourner un code HTTP distinct (403)
# afin que le frontend puisse afficher le bon message.
MESSAGES_COMPTE_EN_ATTENTE = [
    "en attente",
    "approbation",
    "bim manager",
]

@router.post(
    "/login",
    response_model=TokenModele,
    summary="Connexion unifiée (super_admin et utilisateurs)",
)
def connecter(donnees: LoginUnifieModele) -> dict:
    """
    Endpoint unique de connexion.

    Détecte automatiquement si c'est un super_admin ou
    un utilisateur et utilise le service approprié.

    Codes HTTP retournés :
        200 → Connexion réussie
        401 → Email ou mot de passe incorrect
        403 → Compte en attente d'approbation ou refusé
    """
    # Étape 2.1 — Normaliser l'email
    email_normalise = donnees.email.lower().strip()

    # Étape 2.2 — Essayer d'abord en tant que super_admin
    try:
        return service_auth.connecter_admin(
            email        = email_normalise,
            mot_de_passe = donnees.mot_de_passe,
        )
    except ValueError:
        pass  # Pas un super_admin — on tente en utilisateur

    # Étape 2.3 — Essayer en tant qu'utilisateur
    try:
        return service_auth.connecter_collaborateur(
            email        = email_normalise,
            mot_de_passe = donnees.mot_de_passe,
        )

    except ValueError as erreur:
        message_erreur = str(erreur).lower()

        # Étape 2.4 — Distinguer "compte en attente" des autres erreurs
        # On retourne 403 pour les comptes en attente/refusés
        # afin que le frontend puisse afficher un message distinct
        # sans avoir à analyser le texte du message d'erreur.
        est_compte_en_attente = any(
            mot in message_erreur
            for mot in MESSAGES_COMPTE_EN_ATTENTE
        )

        if est_compte_en_attente:
            raise HTTPException(
                status_code = status.HTTP_403_FORBIDDEN,
                detail      = str(erreur),
            )

        # Étape 2.5 — Identifiants incorrects → 401
        logger.warning(
            f"Échec connexion pour {email_normalise}"
        )
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Email ou mot de passe incorrect",
            headers     = {"WWW-Authenticate": "Bearer"},
        )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — ENDPOINT COMPATIBLE SWAGGER UI
# ─────────────────────────────────────────────────────────────

@router.post(
    "/login/swagger",
    include_in_schema=False,
)
def connecter_swagger(
    form_data: OAuth2PasswordRequestForm = Depends()
) -> dict:
    """
    Endpoint compatible Swagger UI.
    Convertit le format username/password vers email/mot_de_passe.
    """
    donnees = LoginUnifieModele(
        email        = form_data.username,
        mot_de_passe = form_data.password,
    )
    return connecter(donnees)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — RÉINITIALISATION MOT DE PASSE
# ─────────────────────────────────────────────────────────────

@router.put(
    "/reinitialiser-mot-de-passe",
    response_model=MessageReponseModele,
    summary="Demande de réinitialisation de mot de passe",
)
def demander_reinitialisation(
    donnees: ReinitialisationMdpModele,
) -> dict:
    """
    Soumet une demande de réinitialisation de mot de passe.
    Le super_admin doit approuver avant application.
    """
    try:
        service_auth.demander_reinitialisation_mdp(
            email         = donnees.email,
            nouveau_mdp   = donnees.nouveau_mot_de_passe,
            confirmer_mdp = donnees.confirmer_mot_de_passe,
        )
        return {
            "message": (
                "Demande de réinitialisation soumise. "
                "Le BIM Manager doit l'approuver avant "
                "que votre mot de passe soit modifié."
            )
        }
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = str(erreur),
        )
