"""
api/routers/projets.py
----------------------
Routes de gestion des projets — /api/v1/projets/...

Routes définies :
    POST   /api/v1/projets
        → Créer un projet vide (super_admin)

    POST   /api/v1/projets/{id}/importer
        → Importer un fichier .txt (super_admin)

    GET    /api/v1/projets
        → Lister tous les projets (tous)

    GET    /api/v1/projets/{id}
        → Détails d'un projet + utilisateurs (tous)

    GET    /api/v1/projets/{id}/keynotes
        → Toutes les notes avec catégories (utilisateur)

    GET    /api/v1/projets/{id}/keynotes/recherche
        → Rechercher des keynotes (utilisateur)

    PUT    /api/v1/projets/{id}
        → Renommer un projet (super_admin)

    DELETE /api/v1/projets/{id}
        → Supprimer un projet (super_admin)

Note :
    La route d'export est dans routers/export.py
    GET /api/v1/projets/{id}/exporter

Importation dans main.py :
    from app.api.routers import projets
    app.include_router(projets.router, prefix=PREFIX_API)
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from app.api.dependencies import (
    obtenir_utilisateur_actuel,
    obtenir_verificateur_acces,
    verifier_super_admin,
    verifier_utilisateur,
)
from app.logger import get_logger
from app.models.schemas.notes import NoteAvecCategorieModele
from app.models.schemas.projets import (
    CreerProjetModele,
    ImporterProjetModele,
    ModifierProjetModele,
    ProjetDetailModele,
    ProjetReponseModele,
)
from app.models.schemas.utilisateurs import (
    MessageReponseModele,
)
from app.services import projets as service_projets
from app.services import notes as service_notes
from app.services import keynotes_fichier as service_fichier


# Initialiser le logger pour ce module
logger = get_logger(__name__)

# Créer le routeur avec le préfixe /projets
router = APIRouter(prefix="/projets", tags=["Projets"])


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — CRÉATION ET IMPORT
# ─────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ProjetReponseModele,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un projet vide",
)
def creer_projet(
    donnees: CreerProjetModele,
    admin  : dict = Depends(verifier_super_admin),
) -> dict:
    """
    Crée un nouveau projet Revit vide.
    Réservé au super_admin uniquement.
    """
    # Étape 1.1 — Créer le projet
    try:
        return service_projets.creer_projet(
            nom_projet     = donnees.nom_projet,
            id_super_admin = admin["id"],
            chemin_export  = donnees.chemin_export,
        )
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail      = str(erreur),
        )


@router.post(
    "/{id_projet}/importer",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Importer un fichier .txt Revit",
)
def importer_fichier_txt(
    id_projet: int,
    donnees  : ImporterProjetModele,
    admin    : dict = Depends(verifier_super_admin),
) -> dict:
    """
    Importe un fichier .txt keynotes Revit dans un projet.
    Modes : 'remplacer' (tout effacer) ou 'fusionner'
    (ajouter uniquement les nouveaux éléments).
    Réservé au super_admin uniquement.
    """
    # Étape 1.2 — Importer le fichier .txt
    try:
        stats = service_fichier.importer_fichier_txt(
            id_projet         = id_projet,
            contenu_txt       = donnees.contenu_txt,
            mode              = donnees.mode,
            effectue_par_id   = admin["id"],
            effectue_par_role = "super_admin",
        )
        return {
            "message"            : (
                f"Import '{donnees.mode}' réussi."
            ),
            "categories_inserees": stats[
                "categories_inserees"
            ],
            "notes_inserees"     : stats["notes_inserees"],
        }
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = str(erreur),
        )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — LISTAGE ET AFFICHAGE
# ─────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[ProjetReponseModele],
    summary="Lister tous les projets",
)
def lister_projets(
    utilisateur: dict = Depends(obtenir_utilisateur_actuel),
) -> list:
    """
    Retourne la liste de tous les projets existants.
    Accessible à tous les utilisateurs connectés.
    """
    # Étape 2.1 — Lister tous les projets
    return service_projets.lister_projets()


@router.get(
    "/{id_projet}",
    response_model=ProjetDetailModele,
    summary="Détails d'un projet",
)
def afficher_projet(
    id_projet  : int,
    utilisateur: dict = Depends(obtenir_utilisateur_actuel),
) -> dict:
    """
    Retourne les détails d'un projet avec la liste
    complète des utilisateurs ayant accès.
    """
    # Étape 2.2 — Afficher les détails du projet
    try:
        return service_projets.afficher_projet(id_projet)
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(erreur),
        )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — KEYNOTES DU PROJET
# ─────────────────────────────────────────────────────────────

@router.get(
    "/{id_projet}/keynotes",
    response_model=list[NoteAvecCategorieModele],
    summary="Toutes les notes avec leurs catégories",
)
def lister_keynotes(
    id_projet   : int,
    id_categorie: int | None = Query(
        default     = None,
        description = "Filtrer par catégorie (optionnel)",
    ),
    utilisateur : dict = Depends(verifier_utilisateur),
) -> list:
    """
    Retourne toutes les notes d'un projet avec les
    informations de leurs catégories.
    Filtre optionnel par catégorie via menu déroulant.
    """
    # Étape 3.1 — Lister les keynotes du projet
    return service_notes.lister_keynotes_projet(
        id_projet, id_categorie
    )


@router.get(
    "/{id_projet}/keynotes/recherche",
    response_model=list[NoteAvecCategorieModele],
    summary="Rechercher des keynotes",
)
def rechercher_keynotes(
    id_projet   : int,
    q           : str = Query(
        description = "Terme de recherche"
    ),
    id_categorie: int | None = Query(
        default     = None,
        description = "Filtrer par catégorie (optionnel)",
    ),
    utilisateur : dict = Depends(verifier_utilisateur),
) -> list:
    """
    Recherche des keynotes par numéro ou description.
    Insensible à la casse et aux accents.
    Filtre optionnel par catégorie.
    """
    # Étape 3.2 — Valider et rechercher
    if not q.strip():
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = (
                "Le terme de recherche ne peut "
                "pas être vide."
            ),
        )
    return service_notes.rechercher_keynotes(
        id_projet, q, id_categorie
    )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — MODIFICATION ET SUPPRESSION
# ─────────────────────────────────────────────────────────────

@router.put(
    "/{id_projet}",
    response_model=ProjetReponseModele,
    summary="Modifier un projet",
)
def modifier_projet(
    id_projet: int,
    donnees  : ModifierProjetModele,
    admin    : dict = Depends(verifier_super_admin),
) -> dict:
    """
    Modifie un projet existant — nom et/ou chemin d'export.
    Le fichier .txt associé est renommé si le nom change.
    Réservé au super_admin uniquement.
    """
    # Étape 4.1 — Modifier le projet
    try:
        return service_projets.modifier_projet(
            id_projet     = id_projet,
            nouveau_nom   = donnees.nouveau_nom,
            chemin_export = donnees.chemin_export,
        )
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail      = str(erreur),
        )


@router.delete(
    "/{id_projet}",
    response_model=MessageReponseModele,
    summary="Supprimer un projet",
)
def supprimer_projet(
    id_projet: int,
    admin    : dict = Depends(verifier_super_admin),
) -> dict:
    """
    Supprime un projet et toutes ses données.
    Supprime aussi le fichier .txt associé si présent.
    Action irréversible — réservée au super_admin.
    """
    # Étape 4.2 — Supprimer le projet
    try:
        service_projets.supprimer_projet(id_projet)
        return {
            "message": (
                f"Projet {id_projet} "
                "supprimé avec succès."
            )
        }
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(erreur),
        )