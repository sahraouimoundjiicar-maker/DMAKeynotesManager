"""
api/routers/auth.py
-------------------
Routes d'authentification — /api/v1/auth/...

Routes définies :
    POST /api/v1/auth/register
        → Inscription publique d'un collaborateur

    POST /api/v1/auth/login
        → Connexion unifiée (super_admin et collaborateurs)

    PUT  /api/v1/auth/reinitialiser-mot-de-passe
        → Demande de réinitialisation de mot de passe

Importation dans main.py :
    from app.api.routers import auth
    app.include_router(auth.router, prefix=PREFIX_API)
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from app.logger import get_logger
from app.models.schemas.auth import (
    LoginAdminModele,
    LoginCollaborateurModele,
    RegisterModele,
    ReinitialisationMdpModele,
    TokenModele,
)
from app.models.schemas.utilisateurs import (
    MessageReponseModele,
    UtilisateurReponseModele,
)
from app.services import auth as service_auth

# Initialiser le logger pour ce module
logger = get_logger(__name__)

# Créer le routeur avec le préfixe /auth
router = APIRouter(prefix="/auth", tags=["Authentification"])


# ─────────────────────────────────────────────────────────────
# ÉTAPE 0 — MODÈLE UNIFIÉ POUR LA CONNEXION
# ─────────────────────────────────────────────────────────────

class LoginUnifieModele(BaseModel):
    """
    Modèle unifié pour la connexion.
    Utilisé par le nouvel endpoint /login unique.
    """
    email: EmailStr
    mot_de_passe: str


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — INSCRIPTION
# ─────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UtilisateurReponseModele,
    status_code=status.HTTP_201_CREATED,
    summary="Inscription d'un collaborateur",
)
def inscrire_collaborateur(
        donnees: RegisterModele,
) -> dict:
    """
    Inscrit un nouveau collaborateur avec le statut
    'en_attente'. Le super_admin doit approuver le compte
    avant que le collaborateur puisse se connecter.

    Le compte ne peut pas se connecter tant qu'il
    n'est pas approuvé par le BIM Manager.
    """
    # Étape 1.1 — Appeler le service d'inscription
    try:
        return service_auth.inscrire_collaborateur(
            nom=donnees.nom,
            prenom=donnees.prenom,
            email=donnees.email,
            mot_de_passe=donnees.mot_de_passe,
        )
    except ValueError as erreur:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(erreur),
        )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — CONNEXION UNIFIÉE
# ─────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenModele,
    summary="Connexion unifiée (super_admin et collaborateurs)"
)
def connecter(
        donnees: LoginUnifieModele,
) -> dict:
    """
    Endpoint unique de connexion.
    Détecte automatiquement si c'est un super_admin
    ou un collaborateur et utilise le service approprié.
    """
    # Étape 2.1 — Normaliser l'email
    email_normalise = donnees.email.lower().strip()

    # Étape 2.2 — Essayer d'abord en tant que super_admin
    try:
        return service_auth.connecter_admin(
            email=email_normalise,
            mot_de_passe=donnees.mot_de_passe
        )
    except ValueError:
        # Étape 2.3 — Si ce n'est pas admin, essayer collaborateur
        try:
            return service_auth.connecter_collaborateur(
                email=email_normalise,
                mot_de_passe=donnees.mot_de_passe
            )
        except ValueError as erreur:
            # Étape 2.4 — Si les deux échouent, erreur générique
            logger.warning(
                f"Échec connexion pour {email_normalise}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — ENDPOINT COMPATIBLE SWAGGER UI
# ─────────────────────────────────────────────────────────────

@router.post(
    "/login/swagger",
    include_in_schema=False
)
def connecter_swagger(
        form_data: OAuth2PasswordRequestForm = Depends()
) -> dict:
    """
    Endpoint compatible Swagger UI.
    Convertit le format username/password vers email/mot_de_passe.
    """
    # Étape 3.1 — Créer les données au format attendu
    donnees = LoginUnifieModele(
        email=form_data.username,
        mot_de_passe=form_data.password
    )
    # Étape 3.2 — Appeler le nouvel endpoint unifié
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
    Le super_admin doit approuver la demande avant que
    le nouveau mot de passe soit appliqué.
    Une nouvelle demande remplace l'ancienne si elle existe.
    """
    # Étape 4.1 — Soumettre la demande de réinitialisation
    try:
        service_auth.demander_reinitialisation_mdp(
            email=donnees.email,
            nouveau_mdp=donnees.nouveau_mot_de_passe,
            confirmer_mdp=donnees.confirmer_mot_de_passe,
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erreur),
        )