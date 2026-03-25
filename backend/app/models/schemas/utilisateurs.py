"""
models/schemas/utilisateurs.py
------------------------------
Modèles Pydantic — Utilisateurs.

Rôle :
    Définir et valider les données entrantes et sortantes
    pour toutes les opérations sur les utilisateurs.

Schemas définis :
    - ModifierUtilisateurModele   modifier un collaborateur
    - UtilisateurReponseModele    réponse simple
    - UtilisateurDetailModele     réponse avec projets

Importation :
    from app.models.schemas.utilisateurs import (
        ModifierUtilisateurModele,
        UtilisateurReponseModele,
        UtilisateurDetailModele,
    )
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from app.config import MOT_DE_PASSE_MIN_LONGUEUR, NOM_MIN_LONGUEUR


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — SCHEMA DE MODIFICATION
# ─────────────────────────────────────────────────────────────

class ModifierUtilisateurModele(BaseModel):
    """
    Données pour modifier un collaborateur existant.
    Route : PUT /api/v1/utilisateurs/{id}

    Tous les champs sont optionnels — seuls les champs
    fournis seront mis à jour.
    """

    # Étape 1.1 — Champs optionnels de modification
    nouveau_nom    : Optional[str]      = None
    nouveau_prenom : Optional[str]      = None
    nouveau_email  : Optional[EmailStr] = None
    nouveau_mdp    : Optional[str]      = None

    # Étape 1.2 — Validation du nouveau nom
    @field_validator("nouveau_nom")
    @classmethod
    def valider_nouveau_nom(
        cls, valeur: Optional[str]
    ) -> Optional[str]:
        """
        Nettoie et valide le nouveau nom si fourni.
        Retourne None si le champ n'est pas fourni.
        """
        if valeur is None:
            return None
        valeur_nettoyee = valeur.strip()
        if len(valeur_nettoyee) < NOM_MIN_LONGUEUR:
            raise ValueError(
                f"Le nom doit contenir au moins "
                f"{NOM_MIN_LONGUEUR} caractères."
            )
        return valeur_nettoyee

    # Étape 1.3 — Validation du nouveau prénom
    @field_validator("nouveau_prenom")
    @classmethod
    def valider_nouveau_prenom(
        cls, valeur: Optional[str]
    ) -> Optional[str]:
        """
        Nettoie et valide le nouveau prénom si fourni.
        Retourne None si le champ n'est pas fourni.
        """
        if valeur is None:
            return None
        valeur_nettoyee = valeur.strip()
        if len(valeur_nettoyee) < NOM_MIN_LONGUEUR:
            raise ValueError(
                f"Le prénom doit contenir au moins "
                f"{NOM_MIN_LONGUEUR} caractères."
            )
        return valeur_nettoyee

    # Étape 1.4 — Validation du nouveau mot de passe
    @field_validator("nouveau_mdp")
    @classmethod
    def valider_nouveau_mdp(
        cls, valeur: Optional[str]
    ) -> Optional[str]:
        """
        Vérifie la longueur minimale du nouveau mot
        de passe si fourni.
        """
        if valeur is None:
            return None
        if len(valeur) < MOT_DE_PASSE_MIN_LONGUEUR:
            raise ValueError(
                f"Le mot de passe doit contenir au moins "
                f"{MOT_DE_PASSE_MIN_LONGUEUR} caractères."
            )
        return valeur


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — SCHEMAS DE RÉPONSE SIMPLE
# ─────────────────────────────────────────────────────────────

class UtilisateurReponseModele(BaseModel):
    """
    Réponse simple avec les infos de base d'un utilisateur.
    Utilisée pour la liste des collaborateurs et les
    opérations CRUD simples.
    Les mots de passe ne sont jamais inclus dans les réponses.
    """

    # Étape 2.1 — Champs de réponse simple
    id            : int
    nom           : str
    prenom        : str
    email         : str
    role          : str
    statut        : str
    date_creation : datetime

    class Config:
        """Permet la conversion depuis les objets PostgreSQL."""
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — SCHEMA DE RÉPONSE DÉTAILLÉE
# ─────────────────────────────────────────────────────────────

class ProjetAccessibleModele(BaseModel):
    """
    Informations d'un projet accessible par un utilisateur.
    Utilisé dans UtilisateurDetailModele.
    """

    # Étape 3.1 — Champs du projet accessible
    id_projet    : int
    nom_projet   : str
    date_attribution : datetime


class UtilisateurDetailModele(BaseModel):
    """
    Réponse détaillée avec les infos complètes d'un
    utilisateur incluant la liste de ses projets.
    Route : GET /api/v1/utilisateurs/{id}
    """

    # Étape 3.2 — Champs de réponse détaillée
    id                  : int
    nom                 : str
    prenom              : str
    email               : str
    role                : str
    statut              : str
    date_creation       : datetime
    projets_accessibles : list[ProjetAccessibleModele] = []

    class Config:
        """Permet la conversion depuis les objets PostgreSQL."""
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — SCHEMA DE RÉPONSE MESSAGE
# ─────────────────────────────────────────────────────────────

class MessageReponseModele(BaseModel):
    """
    Réponse générique pour les opérations sans retour
    de données (suppression, approbation, refus...).
    """

    # Étape 4.1 — Champ message
    message : str