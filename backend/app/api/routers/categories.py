"""
api/routers/categories.py
-------------------------
Routes de gestion des catégories — /api/v1/projets/...

Routes définies :
    POST   /api/v1/projets/{id}/categories
        → Créer une catégorie (éditeur + super_admin)

    GET    /api/v1/projets/{id}/categories
        → Lister les catégories (éditeur + super_admin)

    PUT    /api/v1/projets/{id}/categories/{id_cat}
        → Modifier une catégorie (éditeur + super_admin)

    DELETE /api/v1/projets/{id}/categories/{id_cat}
        → Supprimer une catégorie vide (éditeur + super_admin)

Importation dans main.py :
    from app.api.routers import categories
    app.include_router(
        categories.router, prefix=PREFIX_API
    )
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    obtenir_verificateur_acces,
    verifier_editeur,
)
from app.logger import get_logger
from app.models.schemas.categories import (
    CategorieReponseModele,
    CreerCategorieModele,
    ModifierCategorieModele,
)
from app.models.schemas.utilisateurs import (
    MessageReponseModele,
)
from app.services import categories as service_categories


# Initialiser le logger pour ce module
logger = get_logger(__name__)

# Créer le routeur avec le préfixe /projets
router = APIRouter(prefix="/projets", tags=["Catégories"])


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — CRÉATION D'UNE CATÉGORIE
# ─────────────────────────────────────────────────────────────

@router.post(
    "/{id_projet}/categories",
    response_model=CategorieReponseModele,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une catégorie",
)
def creer_categorie(
    id_projet  : int,
    donnees    : CreerCategorieModele,
    utilisateur: dict = Depends(verifier_editeur),
) -> dict:
    """
    Crée une nouvelle catégorie dans un projet.
    Le numéro doit être unique dans tout le projet
    (catégories ET notes).
    Accessible aux éditeurs et au super_admin.
    """
    # Étape 1.1 — Créer la catégorie
    try:
        return service_categories.creer_categorie(
            id_projet    = id_projet,
            numero       = donnees.numero,
            description  = donnees.description,
            id_createur  = utilisateur["id"],
            role_createur= utilisateur["role"],
        )
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail      = str(erreur),
        )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — LISTAGE DES CATÉGORIES
# ─────────────────────────────────────────────────────────────

@router.get(
    "/{id_projet}/categories",
    response_model=list[CategorieReponseModele],
    summary="Lister les catégories d'un projet",
)
def lister_categories(
    id_projet  : int,
    utilisateur: dict = Depends(verifier_editeur),
) -> list:
    """
    Retourne toutes les catégories d'un projet avec
    le nombre de notes associées à chacune.
    Le nombre de notes est utile pour informer l'utilisateur
    avant une tentative de suppression.
    """
    # Étape 2.1 — Lister les catégories du projet
    return service_categories.lister_categories(id_projet)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — MODIFICATION D'UNE CATÉGORIE
# ─────────────────────────────────────────────────────────────

@router.put(
    "/{id_projet}/categories/{id_categorie}",
    response_model=CategorieReponseModele,
    summary="Modifier une catégorie",
)
def modifier_categorie(
    id_projet   : int,
    id_categorie: int,
    donnees     : ModifierCategorieModele,
    utilisateur : dict = Depends(verifier_editeur),
) -> dict:
    """
    Modifie une catégorie avec verrouillage optimiste.
    Si un autre utilisateur a modifié la catégorie
    depuis l'ouverture, une erreur 409 est retournée
    avec un message demandant de recharger.
    """
    # Étape 3.1 — Modifier la catégorie
    try:
        return service_categories.modifier_categorie(
            id_projet        = id_projet,
            id_categorie     = id_categorie,
            version_actuelle = donnees.version_actuelle,
            id_modificateur  = utilisateur["id"],
            role_modificateur= utilisateur["role"],
            nouveau_numero   = donnees.nouveau_numero,
            nouvelle_desc    = donnees.nouvelle_desc,
        )
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail      = str(erreur),
        )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — SUPPRESSION D'UNE CATÉGORIE
# ─────────────────────────────────────────────────────────────

@router.delete(
    "/{id_projet}/categories/{id_categorie}",
    response_model=MessageReponseModele,
    summary="Supprimer une catégorie vide",
)
def supprimer_categorie(
    id_projet   : int,
    id_categorie: int,
    utilisateur : dict = Depends(verifier_editeur),
) -> dict:
    """
    Supprime une catégorie uniquement si elle est vide.
    Si la catégorie contient des notes, une erreur 409
    est retournée avec un message explicatif demandant
    de supprimer d'abord toutes les notes.
    """
    # Étape 4.1 — Supprimer la catégorie si vide
    try:
        service_categories.supprimer_categorie(
            id_projet        = id_projet,
            id_categorie     = id_categorie,
            id_modificateur  = utilisateur["id"],
            role_modificateur= utilisateur["role"],
        )
        return {
            "message": (
                f"Catégorie {id_categorie} supprimée."
            )
        }
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail      = str(erreur),
        )