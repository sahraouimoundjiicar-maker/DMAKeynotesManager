"""
models/schemas/auth.py
----------------------
Modèles Pydantic — Authentification.

Rôle :
    Définir et valider les données entrantes et sortantes
    pour toutes les opérations d'authentification.

Schemas définis :
    - LoginAdminModele          connexion super_admin
    - LoginCollaborateurModele  connexion collaborateur
    - RegisterModele            inscription publique
    - TokenModele               réponse JWT
    - ReinitialisationMdpModele demande de reset mdp

Importation :
    from app.models.schemas.auth import (
        RegisterModele,
        TokenModele,
    )
"""

from pydantic import BaseModel, EmailStr, field_validator
from app.config import (
    MOT_DE_PASSE_MIN_LONGUEUR,
    NOM_MIN_LONGUEUR,
)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — SCHEMAS DE CONNEXION
# ─────────────────────────────────────────────────────────────

class LoginAdminModele(BaseModel):
    """
    Données requises pour la connexion du super_admin.
    Route : POST /api/v1/auth/login/admin
    """

    # Étape 1.1 — Champs de connexion admin
    email        : EmailStr
    mot_de_passe : str


class LoginCollaborateurModele(BaseModel):
    """
    Données requises pour la connexion d'un collaborateur.
    Route : POST /api/v1/auth/login
    """

    # Étape 1.2 — Champs de connexion collaborateur
    email        : EmailStr
    mot_de_passe : str


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — SCHEMA D'INSCRIPTION
# ─────────────────────────────────────────────────────────────

class RegisterModele(BaseModel):
    """
    Données requises pour l'inscription d'un collaborateur.
    Route : POST /api/v1/auth/register

    Validations appliquées :
        - nom et prenom           : min 2 caractères, strip()
        - email                   : format valide
        - mot_de_passe            : min 8 caractères
        - confirmer_mot_de_passe  : doit être identique au mdp
    """

    # Étape 2.1 — Champs d'inscription
    """
    confirmer_mot_de_passe est obligatoire pour éviter
    les fautes de frappe lors de l'inscription.
    La vérification se fait côté Pydantic avant même
    d'appeler le service ou la BD.
    """
    nom                   : str
    prenom                : str
    email                 : EmailStr
    mot_de_passe          : str
    confirmer_mot_de_passe: str

    # Étape 2.2 — Validation du nom
    @field_validator("nom")
    @classmethod
    def valider_nom(cls, valeur: str) -> str:
        """
        Nettoie et valide le nom.
        Strip les espaces et vérifie la longueur minimale.
        """
        valeur_nettoyee = valeur.strip()
        if len(valeur_nettoyee) < NOM_MIN_LONGUEUR:
            raise ValueError(
                f"Le nom doit contenir au moins "
                f"{NOM_MIN_LONGUEUR} caractères."
            )
        return valeur_nettoyee

    # Étape 2.3 — Validation du prénom
    @field_validator("prenom")
    @classmethod
    def valider_prenom(cls, valeur: str) -> str:
        """
        Nettoie et valide le prénom.
        Strip les espaces et vérifie la longueur minimale.
        """
        valeur_nettoyee = valeur.strip()
        if len(valeur_nettoyee) < NOM_MIN_LONGUEUR:
            raise ValueError(
                f"Le prénom doit contenir au moins "
                f"{NOM_MIN_LONGUEUR} caractères."
            )
        return valeur_nettoyee

    # Étape 2.4 — Validation du mot de passe
    @field_validator("mot_de_passe")
    @classmethod
    def valider_mot_de_passe(cls, valeur: str) -> str:
        """
        Vérifie que le mot de passe respecte la longueur
        minimale de sécurité.
        """
        if len(valeur) < MOT_DE_PASSE_MIN_LONGUEUR:
            raise ValueError(
                f"Le mot de passe doit contenir au moins "
                f"{MOT_DE_PASSE_MIN_LONGUEUR} caractères."
            )
        return valeur

    # Étape 2.5 — Validation de la confirmation
    @field_validator("confirmer_mot_de_passe")
    @classmethod
    def valider_confirmation_mot_de_passe(
        cls, valeur: str, values: dict
    ) -> str:
        """
        Vérifie que la confirmation correspond au
        mot de passe saisi.
        Retourne une erreur claire si les deux champs
        ne correspondent pas.
        """
        mdp = values.data.get("mot_de_passe")
        if mdp and valeur != mdp:
            raise ValueError(
                "Les mots de passe ne correspondent pas."
            )
        return valeur


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — SCHEMA DE RÉPONSE TOKEN
# ─────────────────────────────────────────────────────────────

class TokenModele(BaseModel):
    """
    Réponse retournée après une connexion réussie.
    Contient le token JWT et les infos de session.
    """

    # Étape 3.1 — Champs du token JWT
    """
    access_token : token JWT signé à inclure dans
                   le header Authorization: Bearer <token>
    token_type   : toujours 'bearer' pour JWT
    role         : 'super_admin' ou 'editeur'
    """
    access_token : str
    token_type   : str = "bearer"
    role         : str


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — SCHEMA DE RÉINITIALISATION MOT DE PASSE
# ─────────────────────────────────────────────────────────────

class ReinitialisationMdpModele(BaseModel):
    """
    Données requises pour une demande de réinitialisation
    de mot de passe.
    Route : PUT /api/v1/auth/reinitialiser-mot-de-passe

    Le collaborateur soumet son email et son nouveau
    mot de passe. Le super_admin doit ensuite approuver
    la demande avant qu'elle soit appliquée.
    """

    # Étape 4.1 — Champs de réinitialisation
    email            : EmailStr
    nouveau_mot_de_passe     : str
    confirmer_mot_de_passe   : str

    # Étape 4.2 — Validation du nouveau mot de passe
    @field_validator("nouveau_mot_de_passe")
    @classmethod
    def valider_nouveau_mot_de_passe(
        cls, valeur: str
    ) -> str:
        """
        Vérifie que le nouveau mot de passe respecte
        la longueur minimale de sécurité.
        """
        if len(valeur) < MOT_DE_PASSE_MIN_LONGUEUR:
            raise ValueError(
                f"Le mot de passe doit contenir au moins "
                f"{MOT_DE_PASSE_MIN_LONGUEUR} caractères."
            )
        return valeur

    # Étape 4.3 — Validation de la confirmation
    @field_validator("confirmer_mot_de_passe")
    @classmethod
    def valider_confirmation(
        cls, valeur: str, values: dict
    ) -> str:
        """
        Vérifie que la confirmation correspond au
        nouveau mot de passe saisi.
        """
        nouveau = values.data.get("nouveau_mot_de_passe")
        if nouveau and valeur != nouveau:
            raise ValueError(
                "Les mots de passe ne correspondent pas."
            )
        return valeur