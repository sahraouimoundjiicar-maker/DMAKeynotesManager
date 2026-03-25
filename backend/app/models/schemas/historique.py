"""
models/schemas/historique.py
----------------------------
Modèles Pydantic — Historique et Pagination.

Rôle :
    Définir et valider les données sortantes pour
    l'historique des actions et la pagination.

Schemas définis :
    - HistoriqueReponseModele   une entrée d'historique
    - HistoriquePagineModele    liste paginée d'historique

Actions possibles :
    - creation
    - modification
    - suppression
    - export_txt
    - import_remplacement
    - import_fusion_categorie
    - import_fusion_note

Importation :
    from app.models.schemas.historique import (
        HistoriqueReponseModele,
        HistoriquePagineModele,
    )
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — SCHEMA D'UNE ENTRÉE D'HISTORIQUE
# ─────────────────────────────────────────────────────────────

class HistoriqueReponseModele(BaseModel):
    """
    Réponse représentant une entrée dans l'historique.

    effectue_par_role permet de distinguer visuellement
    les actions du super_admin de celles des éditeurs
    dans l'interface frontend.

    ancienne_valeur et nouvelle_valeur sont optionnels
    car certaines actions (export_txt) n'ont pas de valeurs
    avant/après.
    """

    # Étape 1.1 — Champs d'une entrée historique
    id                : int
    id_projet         : int
    table_cible       : str
    id_cible          : Optional[int] = None
    action            : str
    ancienne_valeur   : Optional[str] = None
    nouvelle_valeur   : Optional[str] = None
    effectue_par_id   : int
    effectue_par_role : str
    date_action       : datetime

    class Config:
        """Permet la conversion depuis les objets PostgreSQL."""
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — SCHEMA DE PAGINATION
# ─────────────────────────────────────────────────────────────

class HistoriquePagineModele(BaseModel):
    """
    Réponse paginée de l'historique d'un projet.
    Route : GET /api/v1/projets/{id}/historique
            ?page=1&limite=50

    Utilisée pour éviter de retourner des milliers
    d'entrées d'un coup — l'historique grandit vite.

    Exemple de réponse :
        {
            "total"       : 245,
            "page"        : 1,
            "limite"      : 50,
            "total_pages" : 5,
            "donnees"     : [...]
        }
    """

    # Étape 2.1 — Champs de pagination
    """
    total       : nombre total d'entrées dans l'historique
    page        : numéro de la page courante (commence à 1)
    limite      : nombre d'entrées par page
    total_pages : nombre total de pages calculé côté service
    donnees     : liste des entrées de la page courante
    """
    total       : int
    page        : int
    limite      : int
    total_pages : int
    donnees     : list[HistoriqueReponseModele]


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — SCHEMA DES PARAMÈTRES DE PAGINATION
# ─────────────────────────────────────────────────────────────

class ParametresPaginationModele(BaseModel):
    """
    Paramètres de pagination reçus en query string.
    Utilisés dans le routeur historique pour valider
    les paramètres avant de les passer au service.

    Valeurs par défaut :
        page   = 1  (première page)
        limite = 50 (50 entrées par page)
    """

    # Étape 3.1 — Paramètres avec valeurs par défaut
    page   : int = 1
    limite : int = 50

    # Étape 3.2 — Validation de la page
    @classmethod
    def valider_page(cls, valeur: int) -> int:
        """
        La page doit être supérieure ou égale à 1.
        Une page 0 ou négative n'a pas de sens.
        """
        if valeur < 1:
            raise ValueError(
                "Le numéro de page doit être "
                "supérieur ou égal à 1."
            )
        return valeur

    # Étape 3.3 — Validation de la limite
    @classmethod
    def valider_limite(cls, valeur: int) -> int:
        """
        La limite doit être entre 1 et 100.
        Une limite trop grande pourrait surcharger le serveur.
        """
        if valeur < 1:
            raise ValueError(
                "La limite doit être supérieure "
                "ou égale à 1."
            )
        if valeur > 100:
            raise ValueError(
                "La limite ne peut pas dépasser 100 "
                "entrées par page."
            )
        return valeur