"""
api/routers/acces.py
--------------------
Routes de gestion des accès projets — /api/v1/projets/...

Routes définies :
    POST   /api/v1/projets/{id}/acces
        → Attribuer l'accès à un collaborateur (super_admin)

    DELETE /api/v1/projets/{id}/acces/{id_utilisateur}
        → Retirer l'accès d'un collaborateur (super_admin)

Importation dans main.py :
    from app.api.routers import acces
    app.include_router(acces.router, prefix=PREFIX_API)
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import verifier_super_admin
from app.logger import get_logger
from app.models.schemas.acces import (
    AttribuerAccesModele,
    AccesReponseModele,
)
from app.models.schemas.utilisateurs import (
    MessageReponseModele,
)
from app.services import acces as service_acces


# Initialiser le logger pour ce module
logger = get_logger(__name__)

# Créer le routeur avec le préfixe /projets
# (même préfixe que projets.py pour les routes imbriquées)
router = APIRouter(prefix="/projets", tags=["Accès"])


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — ATTRIBUTION D'ACCÈS
# ─────────────────────────────────────────────────────────────

@router.post(
    "/{id_projet}/acces",
    response_model=AccesReponseModele,
    status_code=status.HTTP_201_CREATED,
    summary="Attribuer l'accès à un collaborateur",
)
def attribuer_acces(
    id_projet: int,
    donnees  : AttribuerAccesModele,
    admin    : dict = Depends(verifier_super_admin),
) -> dict:
    """
    Donne l'accès à un collaborateur approuvé pour
    un projet spécifique.
    Le collaborateur doit avoir le statut 'approuve'
    pour recevoir un accès.
    Réservé au super_admin uniquement.
    """
    # Étape 1.1 — Attribuer l'accès au collaborateur
    try:
        return service_acces.attribuer_acces(
            id_projet      = id_projet,
            id_utilisateur = donnees.id_utilisateur,
            id_super_admin = admin["id"],
        )
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail      = str(erreur),
        )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — RETRAIT D'ACCÈS
# ─────────────────────────────────────────────────────────────

@router.delete(
    "/{id_projet}/acces/{id_utilisateur}",
    response_model=MessageReponseModele,
    summary="Retirer l'accès d'un collaborateur",
)
def retirer_acces(
    id_projet     : int,
    id_utilisateur: int,
    admin         : dict = Depends(verifier_super_admin),
) -> dict:
    """
    Retire l'accès d'un collaborateur à un projet.
    Le collaborateur ne pourra plus accéder aux keynotes
    de ce projet après cette opération.
    Réservé au super_admin uniquement.
    """
    # Étape 2.1 — Retirer l'accès du collaborateur
    try:
        service_acces.retirer_acces(
            id_projet      = id_projet,
            id_utilisateur = id_utilisateur,
        )
        return {
            "message": (
                f"Accès de l'utilisateur "
                f"{id_utilisateur} retiré du projet "
                f"{id_projet}."
            )
        }
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(erreur),
        )