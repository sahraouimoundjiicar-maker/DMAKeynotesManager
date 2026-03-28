"""
api/routers/historique.py
-------------------------
Routes de l'historique — /api/v1/projets/...

Routes définies :
    GET /api/v1/projets/{id}/historique
        → Super admin : tout l'historique du projet
        → utilisateur : uniquement ses propres actions
        Pagination via ?page=1&limite=50

Importation dans main.py :
    from app.api.routers import historique
    app.include_router(
        historique.router, prefix=PREFIX_API
    )
"""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import verifier_utilisateur
from app.database.connection import creer_connexion
from app.logger import get_logger
from app.models.schemas.historique import (
    HistoriquePagineModele,
    HistoriqueReponseModele,
)
from app.repositories import historique as repo_historique


# Initialiser le logger pour ce module
logger = get_logger(__name__)

# Créer le routeur avec le préfixe /projets
router = APIRouter(prefix="/projets", tags=["Historique"])


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — LISTAGE PAGINÉ DE L'HISTORIQUE
# ─────────────────────────────────────────────────────────────

@router.get(
    "/{id_projet}/historique",
    response_model=HistoriquePagineModele,
    summary="Historique d'un projet (paginé)",
)
def lister_historique(
    id_projet  : int,
    page       : int = Query(
        default     = 1,
        ge          = 1,
        description = "Numéro de page (commence à 1)",
    ),
    limite     : int = Query(
        default     = 50,
        ge          = 1,
        le          = 100,
        description = "Nombre d'entrées par page (max 100)",
    ),
    utilisateur: dict = Depends(verifier_utilisateur),
) -> dict:
    """
    Retourne l'historique paginé d'un projet.

    Comportement selon le rôle :
        - super_admin : tout l'historique du projet
        - utilisateur     : uniquement ses propres actions

    Paramètres de pagination :
        - page  : numéro de page (défaut : 1)
        - limite: entrées par page (défaut : 50, max : 100)
    """
    connexion = creer_connexion()

    try:
        # Étape 1.1 — Calculer l'offset de pagination
        """
        L'offset indique combien d'entrées sauter.
        Ex: page=2, limite=50 → offset=50 (sauter les 50 1ères)
        """
        offset = (page - 1) * limite

        # Étape 1.2 — Récupérer selon le rôle
        """
        Le super_admin voit tout l'historique du projet.
        Un utilisateur ne voit que ses propres actions.
        """
        role = utilisateur.get("role")
        id_utilisateur = utilisateur.get("id")

        if role == "super_admin":
            # Étape 1.3 — Historique complet (super_admin)
            total = repo_historique.compter_historique_projet(
                connexion, id_projet
            )
            donnees = repo_historique.lister_historique_projet(
                connexion, id_projet, limite, offset
            )
        else:
            # Étape 1.4 — Historique filtré (utilisateur)
            total = (
                repo_historique
                .compter_historique_utilisateur(
                    connexion, id_projet, id_utilisateur
                )
            )
            donnees = (
                repo_historique
                .lister_historique_utilisateur(
                    connexion,
                    id_projet,
                    id_utilisateur,
                    limite,
                    offset,
                )
            )

        # Étape 1.5 — Calculer le nombre total de pages
        """
        math.ceil arrondit au supérieur pour s'assurer
        que la dernière page partielle est bien comptée.
        Ex: 105 entrées / 50 par page = 3 pages (et non 2).
        """
        total_pages = math.ceil(total / limite) if total > 0 else 1

        return {
            "total"      : total,
            "page"       : page,
            "limite"     : limite,
            "total_pages": total_pages,
            "donnees"    : donnees,
        }

    except Exception as erreur:
        logger.error(
            f"Erreur listage historique : {erreur}"
        )
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail      = "Erreur lors de la récupération "
                          "de l'historique.",
        )
    finally:
        connexion.close()