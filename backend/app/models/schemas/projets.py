"""
models/schemas/projets.py
-------------------------
Modèles Pydantic — Projets.

Rôle :
    Définir et valider les données entrantes et sortantes
    pour toutes les opérations sur les projets Revit.

Schemas définis :
    - CreerProjetModele         créer un projet vide
    - ModifierProjetModele      renommer un projet
    - ImporterProjetModele      importer un fichier .txt
    - ProjetReponseModele       réponse simple
    - utilisateurProjetModele utilisateur dans un projet
    - ProjetDetailModele        réponse avec utilisateurs

Importation :
    from app.models.schemas.projets import (
        CreerProjetModele,
        ProjetDetailModele,
    )
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — SCHEMAS D'ENTRÉE
# ─────────────────────────────────────────────────────────────

class CreerProjetModele(BaseModel):
    """
    Données requises pour créer un nouveau projet vide.
    Route : POST /api/v1/projets
    Réservé au super_admin uniquement.
    """

    # Étape 1.1 — Nom du projet
    nom_projet : str

    # Étape 1.2 — Validation du nom du projet
    @field_validator("nom_projet")
    @classmethod
    def valider_nom_projet(cls, valeur: str) -> str:
        """
        Nettoie et valide le nom du projet.
        Le nom ne peut pas être vide ou contenir
        uniquement des espaces.
        """
        valeur_nettoyee = valeur.strip()
        if not valeur_nettoyee:
            raise ValueError(
                "Le nom du projet ne peut pas être vide."
            )
        if len(valeur_nettoyee) < 3:
            raise ValueError(
                "Le nom du projet doit contenir "
                "au moins 3 caractères."
            )
        return valeur_nettoyee


class ModifierProjetModele(BaseModel):
    """
    Données requises pour renommer un projet.
    Route : PUT /api/v1/projets/{id}
    Réservé au super_admin uniquement.
    """

    # Étape 1.3 — Nouveau nom du projet
    nouveau_nom : str

    # Étape 1.4 — Validation du nouveau nom
    @field_validator("nouveau_nom")
    @classmethod
    def valider_nouveau_nom(cls, valeur: str) -> str:
        """
        Nettoie et valide le nouveau nom du projet.
        """
        valeur_nettoyee = valeur.strip()
        if not valeur_nettoyee:
            raise ValueError(
                "Le nouveau nom ne peut pas être vide."
            )
        if len(valeur_nettoyee) < 3:
            raise ValueError(
                "Le nom du projet doit contenir "
                "au moins 3 caractères."
            )
        return valeur_nettoyee


class ImporterProjetModele(BaseModel):
    """
    Données requises pour importer un fichier .txt
    dans un projet existant.
    Route : POST /api/v1/projets/{id}/importer
    Réservé au super_admin uniquement.

    mode :
        'remplacer' → supprime tout et importe le fichier
        'fusionner' → ajoute uniquement les nouveaux éléments
    """

    # Étape 1.5 — Champs d'import
    mode         : str
    contenu_txt  : str

    # Étape 1.6 — Validation du mode d'import
    @field_validator("mode")
    @classmethod
    def valider_mode(cls, valeur: str) -> str:
        """
        Vérifie que le mode est 'remplacer' ou 'fusionner'.
        Aucun autre mode n'est accepté.
        """
        modes_autorises = ["remplacer", "fusionner"]
        if valeur not in modes_autorises:
            raise ValueError(
                f"Mode invalide '{valeur}'. "
                f"Valeurs acceptées : "
                f"{', '.join(modes_autorises)}."
            )
        return valeur

    # Étape 1.7 — Validation du contenu du fichier
    @field_validator("contenu_txt")
    @classmethod
    def valider_contenu_txt(cls, valeur: str) -> str:
        """
        Vérifie que le contenu du fichier n'est pas vide.
        La validation complète du format est faite
        dans le service keynotes_fichier.
        """
        if not valeur.strip():
            raise ValueError(
                "Le contenu du fichier .txt est vide."
            )
        return valeur


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — SCHEMAS DE RÉPONSE
# ─────────────────────────────────────────────────────────────

class ProjetReponseModele(BaseModel):
    """
    Réponse simple avec les infos de base d'un projet.
    Utilisée pour la liste des projets.
    """

    # Étape 2.1 — Champs de réponse simple
    id                  : int
    nom                 : str
    txt_a_jour          : bool
    date_dernier_export : Optional[datetime] = None
    date_creation       : datetime

    class Config:
        """Permet la conversion depuis les objets PostgreSQL."""
        from_attributes = True


class utilisateurProjetModele(BaseModel):
    """
    Informations d'un utilisateur ayant accès au projet.
    Utilisé dans ProjetDetailModele.
    """

    # Étape 2.2 — Champs du utilisateur
    id_utilisateur   : int
    nom              : str
    prenom           : str
    email            : str
    date_attribution : datetime


class ProjetDetailModele(BaseModel):
    """
    Réponse détaillée avec les infos complètes d'un projet
    incluant la liste des utilisateurs ayant accès.
    Route : GET /api/v1/projets/{id}
    """

    # Étape 2.3 — Champs de réponse détaillée
    id                  : int
    nom                 : str
    txt_a_jour          : bool
    date_dernier_export : Optional[datetime] = None
    date_creation       : datetime
    utilisateurs      : list[utilisateurProjetModele] = []

    class Config:
        """Permet la conversion depuis les objets PostgreSQL."""
        from_attributes = True