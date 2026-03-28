"""
models/schemas/acces.py
-----------------------
Modèles Pydantic — Accès projets.

Rôle :
    Définir et valider les données entrantes et sortantes
    pour la gestion des accès des utilisateurs aux projets.

Schemas définis :
    - AttribuerAccesModele   attribuer l'accès à un projet
    - AccesReponseModele     réponse après attribution

Importation :
    from app.models.schemas.acces import (
        AttribuerAccesModele,
        AccesReponseModele,
    )
"""

from datetime import datetime
from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — SCHEMA D'ENTRÉE
# ─────────────────────────────────────────────────────────────

class AttribuerAccesModele(BaseModel):
    """
    Données requises pour attribuer l'accès à un projet.
    Route : POST /api/v1/projets/{id}/acces

    Réservé au super_admin uniquement.
    id_utilisateur référence un utilisateur approuvé
    dans la table utilisateurs.
    """

    # Étape 1.1 — Champ d'attribution
    id_utilisateur : int


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — SCHEMA DE RÉPONSE
# ─────────────────────────────────────────────────────────────

class AccesReponseModele(BaseModel):
    """
    Réponse après attribution ou suppression d'un accès.
    Confirme les détails de l'opération effectuée.
    """

    # Étape 2.1 — Champs de réponse
    """
    id_projet et id_utilisateur permettent au frontend
    de mettre à jour l'interface sans recharger
    toute la liste des accès.
    """
    id               : int
    id_projet        : int
    id_utilisateur   : int
    date_attribution : datetime
    attribue_par     : int

    class Config:
        """Permet la conversion depuis les objets PostgreSQL."""
        from_attributes = True