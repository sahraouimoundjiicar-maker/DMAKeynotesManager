"""
models/schemas/notes.py
-----------------------
Modèles Pydantic — Notes (keynotes).

Rôle :
    Définir et valider les données entrantes et sortantes
    pour toutes les opérations sur les notes (keynotes).

Schemas définis :
    - CreerNoteModele       créer une note
    - ModifierNoteModele    modifier une note
    - NoteReponseModele     réponse simple
    - NoteAvecCategorieModele  réponse avec catégorie

Importation :
    from app.models.schemas.notes import (
        CreerNoteModele,
        NoteReponseModele,
    )
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator
from app.config import DESCRIPTION_MAX_LONGUEUR


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — SCHEMAS D'ENTRÉE
# ─────────────────────────────────────────────────────────────

class CreerNoteModele(BaseModel):
    """
    Données requises pour créer une nouvelle note.
    Route : POST /api/v1/projets/{id}/categories/{id}/notes

    id_categorie est obligatoire — une note sans catégorie
    n'est pas autorisée dans l'application.

    Validations appliquées :
        - numero      : strip(), pas de tabulation
        - description : strip(), max 500 caractères,
                        pas de tabulation
    """

    # Étape 1.1 — Champs de création
    """
    id_categorie est envoyé dans l'URL mais aussi dans
    le body pour une validation explicite côté Pydantic.
    """
    numero      : str
    description : str

    # Étape 1.2 — Validation du numéro
    @field_validator("numero")
    @classmethod
    def valider_numero(cls, valeur: str) -> str:
        """
        Nettoie et valide le numéro de la note.
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
        Nettoie et valide la description de la note.
        Interdit la tabulation pour ne pas corrompre
        le fichier .txt Revit lors de l'export.
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


class ModifierNoteModele(BaseModel):
    """
    Données pour modifier une note existante.
    Route : PUT /api/v1/projets/{id}/notes/{id}

    version_actuelle est obligatoire pour le verrouillage
    optimiste — détecte les modifications simultanées
    entre collaborateurs.
    Les autres champs sont optionnels.
    """

    # Étape 1.4 — Champs de modification
    """
    version_actuelle : version de la note au moment de
    l'ouverture par l'utilisateur. Si la version en BD
    diffère, un conflit est détecté et la modification
    est rejetée avec un message explicite.
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

class NoteReponseModele(BaseModel):
    """
    Réponse avec les infos complètes d'une note.
    Inclut modifie_par_id pour afficher qui a modifié
    la note en dernier dans le frontend.
    """

    # Étape 2.1 — Champs de réponse
    id                : int
    id_projet         : int
    id_categorie      : int
    numero            : str
    description       : str
    cree_par          : Optional[int] = None
    modifie_par_id    : Optional[int] = None
    date_modification : datetime
    date_creation     : datetime
    version           : int

    class Config:
        """Permet la conversion depuis les objets PostgreSQL."""
        from_attributes = True


class NoteAvecCategorieModele(BaseModel):
    """
    Réponse d'une note avec les infos de sa catégorie.
    Utilisée pour la vue complète des keynotes d'un projet
    (toutes les notes avec leurs catégories).
    Route : GET /api/v1/projets/{id}/keynotes
    """

    # Étape 2.2 — Champs note + catégorie
    id                   : int
    numero               : str
    description          : str
    modifie_par_id       : Optional[int] = None
    date_modification    : datetime
    version              : int
    categorie_id         : int
    categorie_numero     : str
    categorie_description: str

    class Config:
        """Permet la conversion depuis les objets PostgreSQL."""
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — SCHEMA DE RECHERCHE
# ─────────────────────────────────────────────────────────────

class RechercheNoteModele(BaseModel):
    """
    Paramètres de recherche pour les keynotes.
    Route : GET /api/v1/projets/{id}/keynotes/recherche

    q            : terme de recherche (numéro ou description)
    id_categorie : filtre optionnel par catégorie
    """

    # Étape 3.1 — Paramètres de recherche
    q            : str
    id_categorie : Optional[int] = None

    # Étape 3.2 — Validation du terme de recherche
    @field_validator("q")
    @classmethod
    def valider_terme_recherche(cls, valeur: str) -> str:
        """
        Nettoie le terme de recherche.
        Un terme vide retournerait tous les résultats
        ce qui n'est pas le comportement souhaité.
        """
        valeur_nettoyee = valeur.strip()
        if not valeur_nettoyee:
            raise ValueError(
                "Le terme de recherche ne peut "
                "pas être vide."
            )
        return valeur_nettoyee