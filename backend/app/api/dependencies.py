"""
api/dependencies.py
-------------------
Dépendances FastAPI — JWT et protection des routes.

Rôle :
    Fournir les dépendances réutilisables pour protéger
    les routes de l'API selon le rôle de l'utilisateur.

Dépendances disponibles :
    - obtenir_utilisateur_actuel()  tout utilisateur connecté
    - verifier_super_admin()        super_admin uniquement
    - verifier_utilisateur()            utilisateur ou super_admin
    - verifier_acces_projet()       accès au projet requis

Utilisation dans les routeurs :
    from app.api.dependencies import verifier_super_admin

    @router.post("/projets")
    def creer_projet(
        admin: dict = Depends(verifier_super_admin)
    ):
        ...
"""

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.logger import get_logger
from app.services.auth import decoder_token_jwt
from app.services.acces import verifier_acces_projet


# Initialiser le logger pour ce module
logger = get_logger(__name__)

# Schéma OAuth2 — indique où récupérer le token JWT
# Le token est envoyé dans le header : Authorization: Bearer <token>
# Modification: tokenUrl pointe vers l'endpoint compatible Swagger
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login/swagger",
    scheme_name="DMA Authentication",
    description="Entrez votre email et mot de passe"
)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — OBTENIR L'UTILISATEUR CONNECTÉ
# ─────────────────────────────────────────────────────────────

def obtenir_utilisateur_actuel(
    token: str = Depends(oauth2_scheme),
) -> dict:
    """
    Dépendance FastAPI — décode le token JWT et retourne
    les infos de l'utilisateur connecté.
    Utilisée sur toutes les routes protégées.

    Args:
        token: Token JWT extrait du header Authorization

    Returns:
        Dictionnaire avec id, email et role de l'utilisateur

    Raises:
        HTTPException 401: Si le token est invalide ou expiré
    """
    # Étape 1.1 — Décoder et valider le token JWT
    """
    Si le token est invalide, expiré ou falsifié,
    une erreur 401 est retournée automatiquement.
    """
    try:
        payload = decoder_token_jwt(token)
        return payload

    except JWTError:
        logger.warning("Token JWT invalide ou expiré.")
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = (
                "Session expirée ou token invalide. "
                "Veuillez vous reconnecter."
            ),
            headers     = {"WWW-Authenticate": "Bearer"},
        )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — PROTECTION PAR RÔLE
# ─────────────────────────────────────────────────────────────

def verifier_super_admin(
    utilisateur_actuel: dict = Depends(
        obtenir_utilisateur_actuel
    ),
) -> dict:
    """
    Dépendance FastAPI — vérifie que l'utilisateur connecté
    est le super_admin. Sinon retourne une erreur 403.

    À utiliser sur les routes réservées au BIM Manager :
        - Créer/supprimer des projets
        - Gérer les utilisateurs
        - Attribuer les accès

    Args:
        utilisateur_actuel: Infos de l'utilisateur connecté

    Returns:
        Dictionnaire avec les infos du super_admin

    Raises:
        HTTPException 403: Si l'utilisateur n'est pas admin
    """
    # Étape 2.1 — Vérifier le rôle super_admin
    if utilisateur_actuel.get("role") != "super_admin":
        logger.warning(
            f"Accès refusé (super_admin requis) : "
            f"{utilisateur_actuel.get('email')}"
        )
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = (
                "Accès refusé. "
                "Cette action est réservée au BIM Manager."
            ),
        )
    return utilisateur_actuel


def verifier_utilisateur(
    utilisateur_actuel: dict = Depends(
        obtenir_utilisateur_actuel
    ),
) -> dict:
    """
    Dépendance FastAPI — vérifie que l'utilisateur connecté
    est un utilisateur ou le super_admin.
    Sinon retourne une erreur 403.

    À utiliser sur les routes de gestion des keynotes :
        - Créer/modifier/supprimer des catégories et notes
        - Exporter le fichier .txt

    Args:
        utilisateur_actuel: Infos de l'utilisateur connecté

    Returns:
        Dictionnaire avec les infos de l'utilisateur

    Raises:
        HTTPException 403: Si le rôle est invalide
    """
    # Étape 2.2 — Vérifier le rôle utilisateur ou super_admin
    roles_autorises = ["utilisateur", "super_admin"]
    if utilisateur_actuel.get("role") not in roles_autorises:
        logger.warning(
            f"Accès refusé (utilisateur requis) : "
            f"{utilisateur_actuel.get('email')}"
        )
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Accès refusé.",
        )
    return utilisateur_actuel


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — PROTECTION PAR ACCÈS AU PROJET
# ─────────────────────────────────────────────────────────────

def obtenir_verificateur_acces(id_projet: int):
    """
    Fabrique de dépendance — retourne une dépendance
    qui vérifie l'accès d'un utilisateur à un projet.

    Le super_admin a toujours accès à tous les projets.
    Un utilisateur doit avoir un accès explicite.

    Args:
        id_projet: ID du projet à vérifier

    Returns:
        Fonction de dépendance FastAPI

    Exemple d'utilisation dans un routeur :
        @router.get("/{id_projet}/categories")
        def lister_categories(
            id_projet: int,
            utilisateur = Depends(
                obtenir_verificateur_acces(id_projet)
            )
        ):
    """
    # Étape 3.1 — Créer la dépendance de vérification
    def _verifier_acces(
        utilisateur_actuel: dict = Depends(verifier_utilisateur),
    ) -> dict:
        """
        Vérifie que l'utilisateur a accès au projet.
        Le super_admin est exempt de cette vérification.
        """
        # Étape 3.2 — Super admin a toujours accès
        if utilisateur_actuel.get("role") == "super_admin":
            return utilisateur_actuel

        # Étape 3.3 — Vérifier l'accès du utilisateur
        id_utilisateur = utilisateur_actuel.get("id")
        a_acces = verifier_acces_projet(
            id_projet, id_utilisateur
        )

        if not a_acces:
            logger.warning(
                f"Accès projet refusé : "
                f"utilisateur {id_utilisateur} "
                f"→ projet {id_projet}"
            )
            raise HTTPException(
                status_code = status.HTTP_403_FORBIDDEN,
                detail      = (
                    "Vous n'avez pas accès à ce projet."
                ),
            )

        return utilisateur_actuel

    return _verifier_acces