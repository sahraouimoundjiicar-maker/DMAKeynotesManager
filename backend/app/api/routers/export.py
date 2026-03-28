"""
api/routers/export.py
---------------------
Route d'export du fichier .txt Revit — /api/v1/projets/...

Routes définies :
    GET /api/v1/projets/{id}/exporter
        → Exporter le fichier .txt Revit (utilisateur + super_admin)

Importation dans main.py :
    from app.api.routers import export
    app.include_router(export.router, prefix=PREFIX_API)
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import verifier_utilisateur
from app.logger import get_logger
from app.services import projets as service_projets
from app.services import keynotes_fichier as service_fichier


# Initialiser le logger pour ce module
logger = get_logger(__name__)

# Créer le routeur avec le préfixe /projets
router = APIRouter(prefix="/projets", tags=["Export"])


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — EXPORT FICHIER .TXT REVIT
# ─────────────────────────────────────────────────────────────

@router.get(
    "/{id_projet}/exporter",
    response_model=dict,
    summary="Exporter le fichier .txt Revit",
)
def exporter_fichier_txt(
    id_projet  : int,
    utilisateur: dict = Depends(verifier_utilisateur),
) -> dict:
    """
    Génère le fichier .txt keynotes au format standard Revit
    et le sauvegarde dans shared/keynotes/.

    Le fichier peut ensuite être rechargé directement
    depuis Revit via le gestionnaire de keynotes.

    Comportement :
        - Tri numérique naturel (1, 2, 10 et non 1, 10, 2)
        - Encodage UTF-8 (accents supportés)
        - Format : numéro[TAB]description[TAB]parent
        - txt_a_jour = True après l'export

    Accessible à tous les utilisateurs ayant accès
    au projet et au super_admin.
    """
    # Étape 1.1 — Récupérer les infos du projet
    """
    On récupère le nom du projet pour construire
    le nom du fichier .txt à générer.
    """
    try:
        projet = service_projets.afficher_projet(id_projet)
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(erreur),
        )

    # Étape 1.2 — Déterminer le rôle pour l'historique
    role = utilisateur.get("role", "utilisateur")

    # Étape 1.3 — Générer et sauvegarder le fichier .txt
    try:
        chemin_fichier = service_fichier.exporter_fichier_txt(
            id_projet         = id_projet,
            nom_projet        = projet["nom"],
            effectue_par_id   = utilisateur["id"],
            effectue_par_role = role,
        )

        logger.info(
            f"Export .txt réussi : projet {id_projet} "
            f"par utilisateur {utilisateur['id']}"
        )

        return {
            "message"       : (
                "Fichier .txt exporté avec succès. "
                "Vous pouvez maintenant le recharger "
                "dans Revit."
            ),
            "chemin_fichier": chemin_fichier,
            "nom_projet"    : projet["nom"],
        }

    except Exception as erreur:
        logger.error(
            f"Erreur export .txt projet {id_projet} : "
            f"{erreur}"
        )
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail      = (
                "Erreur lors de la génération du fichier "
                ".txt. Vérifiez que le dossier shared/"
                "keynotes/ est accessible."
            ),
        )