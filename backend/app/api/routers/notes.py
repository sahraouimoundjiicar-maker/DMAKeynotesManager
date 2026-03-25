"""
api/routers/notes.py
--------------------
Routes de gestion des notes — /api/v1/projets/...

Routes définies :
    POST   /api/v1/projets/{id}/categories/{id_cat}/notes
        → Créer une note (éditeur + super_admin)

    GET    /api/v1/projets/{id}/categories/{id_cat}/notes
        → Lister les notes d'une catégorie (éditeur)

    PUT    /api/v1/projets/{id}/notes/{id_note}
        → Modifier une note (éditeur + super_admin)

    DELETE /api/v1/projets/{id}/notes/{id_note}
        → Supprimer une note (éditeur + super_admin)

Importation dans main.py :
    from app.api.routers import notes
    app.include_router(notes.router, prefix=PREFIX_API)
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import verifier_editeur
from app.logger import get_logger
from app.models.schemas.notes import (
    CreerNoteModele,
    ModifierNoteModele,
    NoteReponseModele,
)
from app.models.schemas.utilisateurs import (
    MessageReponseModele,
)
from app.services import notes as service_notes


# Initialiser le logger pour ce module
logger = get_logger(__name__)

# Créer le routeur avec le préfixe /projets
router = APIRouter(prefix="/projets", tags=["Notes"])


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — CRÉATION D'UNE NOTE
# ─────────────────────────────────────────────────────────────

@router.post(
    "/{id_projet}/categories/{id_categorie}/notes",
    response_model=NoteReponseModele,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une note dans une catégorie",
)
def creer_note(
    id_projet   : int,
    id_categorie: int,
    donnees     : CreerNoteModele,
    utilisateur : dict = Depends(verifier_editeur),
) -> dict:
    """
    Crée une nouvelle note obligatoirement liée à une
    catégorie existante. Le numéro doit être unique dans
    tout le projet (notes ET catégories).
    Accessible aux éditeurs et au super_admin.
    """
    # Étape 1.1 — Créer la note dans la catégorie
    try:
        return service_notes.creer_note(
            id_projet    = id_projet,
            id_categorie = id_categorie,
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
# ÉTAPE 2 — LISTAGE DES NOTES
# ─────────────────────────────────────────────────────────────

@router.get(
    "/{id_projet}/categories/{id_categorie}/notes",
    response_model=list[NoteReponseModele],
    summary="Lister les notes d'une catégorie",
)
def lister_notes(
    id_projet   : int,
    id_categorie: int,
    utilisateur : dict = Depends(verifier_editeur),
) -> list:
    """
    Retourne toutes les notes d'une catégorie spécifique.
    Triées par numéro en ordre numérique naturel.
    Accessible aux éditeurs et au super_admin.
    """
    # Étape 2.1 — Lister les notes de la catégorie
    return service_notes.lister_notes_categorie(
        id_categorie
    )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — MODIFICATION D'UNE NOTE
# ─────────────────────────────────────────────────────────────

@router.put(
    "/{id_projet}/notes/{id_note}",
    response_model=NoteReponseModele,
    summary="Modifier une note",
)
def modifier_note(
    id_projet  : int,
    id_note    : int,
    donnees    : ModifierNoteModele,
    utilisateur: dict = Depends(verifier_editeur),
) -> dict:
    """
    Modifie une note avec verrouillage optimiste.
    Si un autre utilisateur a modifié la note depuis
    l'ouverture, une erreur 409 est retournée avec
    un message demandant de recharger et réessayer.
    Accessible aux éditeurs et au super_admin.
    """
    # Étape 3.1 — Modifier la note
    try:
        return service_notes.modifier_note(
            id_projet        = id_projet,
            id_note          = id_note,
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
# ÉTAPE 4 — SUPPRESSION D'UNE NOTE
# ─────────────────────────────────────────────────────────────

@router.delete(
    "/{id_projet}/notes/{id_note}",
    response_model=MessageReponseModele,
    summary="Supprimer une note",
)
def supprimer_note(
    id_projet  : int,
    id_note    : int,
    utilisateur: dict = Depends(verifier_editeur),
) -> dict:
    """
    Supprime une note spécifique sans affecter les
    autres notes de la catégorie.
    Accessible aux éditeurs et au super_admin.
    """
    # Étape 4.1 — Supprimer la note
    try:
        service_notes.supprimer_note(
            id_projet        = id_projet,
            id_note          = id_note,
            id_modificateur  = utilisateur["id"],
            role_modificateur= utilisateur["role"],
        )
        return {
            "message": f"Note {id_note} supprimée."
        }
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(erreur),
        )