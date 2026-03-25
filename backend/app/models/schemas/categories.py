"""
models/schemas/categories.py
----------------------------
Modèles Pydantic — Catégories.

Rôle :
    Définir et valider les données entrantes et sortantes
    pour toutes les opérations sur les catégories de keynotes.

Schemas définis :
    - CreerCategorieModele      créer une catégorie
    - ModifierCategorieModele   modifier une catégorie
    - CategorieReponseModele    réponse simple
    - CategorieDetailModele     réponse avec notes

Importation :
    from app.models.schemas.categories import (
        CreerCategorieModele,
        CategorieReponseModele,
    )
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator
from app.config import DESCRIPTION_MAX_LONGUEUR


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — SCHEMAS D'ENTRÉE
# ─────────────────────────────────────────────────────────────

class CreerCategorieModele(BaseModel):
    """
    Données requises pour créer une nouvelle catégorie.
    Route : POST /api/v1/projets/{id}/categories

    Validations appliquées :
        - numero      : strip(), pas de tabulation
        - description : strip(), max 500 caractères
    """

    # Étape 1.1 — Champs de création
    numero      : str
    description : str

    # Étape 1.2 — Validation du numéro
    @field_validator("numero")
    @classmethod
    def valider_numero(cls, valeur: str) -> str:
        """
        Nettoie et valide le numéro de catégorie.
        Interdit la tabulation car elle est utilisée
        comme séparateur dans le fichier .txt Revit.
        """
        valeur_nettoyee = valeur.strip()
        if not valeur_nettoyee:
            raise ValueError(
                "Le numéro ne peut pas être vide."
            )
        if "\t" in valeur_nettoyee:
            raise ValueError(
                "Le numéro ne peut pas contenir "
                "de tabulation."
            )
        return valeur_nettoyee

    # Étape 1.3 — Validation de la description
    @field_validator("description")
    @classmethod
    def valider_description(cls, valeur: str) -> str:
        """
        Nettoie et valide la description de la catégorie.
        Interdit la tabulation pour ne pas corrompre
        le fichier .txt Revit.
        """
        valeur_nettoyee = valeur.strip()
        if not valeur_nettoyee:
            raise ValueError(
                "La description ne peut pas être vide."
            )
        if "\t" in valeur_nettoyee:
            raise ValueError(
                "La description ne peut pas contenir "
                "de tabulation."
            )
        if len(valeur_nettoyee) > DESCRIPTION_MAX_LONGUEUR:
            raise ValueError(
                f"La description ne peut pas dépasser "
                f"{DESCRIPTION_MAX_LONGUEUR} caractères."
            )
        return valeur_nettoyee


class ModifierCategorieModele(BaseModel):
    """
    Données pour modifier une catégorie existante.
    Route : PUT /api/v1/projets/{id}/categories/{id}

    version_actuelle est obligatoire pour le verrouillage
    optimiste — détecte les modifications simultanées.
    Les autres champs sont optionnels.
    """

    # Étape 1.4 — Champs de modification
    """
    version_actuelle : version de la catégorie au moment
    de l'ouverture par l'utilisateur. Si la version en BD
    est différente, un conflit est détecté et la modification
    est rejetée avec un message d'erreur clair.
    """
    version_actuelle : int
    nouveau_numero   : Optional[str] = None
    nouvelle_desc    : Optional[str] = None

    # Étape 1.5 — Validation du nouveau numéro
    @field_validator("nouveau_numero")
    @classmethod
    def valider_nouveau_numero(
        cls, valeur: Optional[str]
    ) -> Optional[str]:
        """
        Nettoie et valide le nouveau numéro si fourni.
        """
        if valeur is None:
            return None
        valeur_nettoyee = valeur.strip()
        if not valeur_nettoyee:
            raise ValueError(
                "Le numéro ne peut pas être vide."
            )
        if "\t" in valeur_nettoyee:
            raise ValueError(
                "Le numéro ne peut pas contenir "
                "de tabulation."
            )
        return valeur_nettoyee

    # Étape 1.6 — Validation de la nouvelle description
    @field_validator("nouvelle_desc")
    @classmethod
    def valider_nouvelle_desc(
        cls, valeur: Optional[str]
    ) -> Optional[str]:
        """
        Nettoie et valide la nouvelle description si fournie.
        """
        if valeur is None:
            return None
        valeur_nettoyee = valeur.strip()
        if not valeur_nettoyee:
            raise ValueError(
                "La description ne peut pas être vide."
            )
        if "\t" in valeur_nettoyee:
            raise ValueError(
                "La description ne peut pas contenir "
                "de tabulation."
            )
        if len(valeur_nettoyee) > DESCRIPTION_MAX_LONGUEUR:
            raise ValueError(
                f"La description ne peut pas dépasser "
                f"{DESCRIPTION_MAX_LONGUEUR} caractères."
            )
        return valeur_nettoyee


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — SCHEMAS DE RÉPONSE
# ─────────────────────────────────────────────────────────────

class CategorieReponseModele(BaseModel):
    """
    Réponse avec les infos d'une catégorie.
    Inclut le nombre de notes pour informer l'utilisateur
    avant une tentative de suppression.
    """

    # Étape 2.1 — Champs de réponse
    id                : int
    id_projet         : int
    numero            : str
    description       : str
    cree_par          : Optional[int] = None
    modifie_par_id    : Optional[int] = None
    date_modification : datetime
    version           : int
    nombre_notes      : int = 0

    class Config:
        """Permet la conversion depuis les objets PostgreSQL."""
        from_attributes = True