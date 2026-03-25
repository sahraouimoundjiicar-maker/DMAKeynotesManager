"""
api/routers/utilisateurs.py
---------------------------
Routes de gestion des utilisateurs — /api/v1/utilisateurs/...

Routes définies :
    GET    /api/v1/utilisateurs
        → Lister tous les collaborateurs (super_admin)

    GET    /api/v1/utilisateurs/demandes
        → Demandes d'inscription en attente (super_admin)

    GET    /api/v1/utilisateurs/demandes-reinitialisation
        → Demandes de reset mdp en attente (super_admin)

    GET    /api/v1/utilisateurs/{id}
        → Détails d'un collaborateur + ses projets

    PUT    /api/v1/utilisateurs/{id}
        → Modifier un collaborateur (super_admin)

    DELETE /api/v1/utilisateurs/{id}
        → Supprimer un collaborateur (super_admin)

    PUT    /api/v1/utilisateurs/{id}/approuver
        → Approuver une inscription (super_admin)

    PUT    /api/v1/utilisateurs/{id}/refuser
        → Refuser une inscription (super_admin)

    PUT    /api/v1/utilisateurs/{id}/approuver-reinitialisation
        → Approuver un reset mdp (super_admin)

    PUT    /api/v1/utilisateurs/{id}/refuser-reinitialisation
        → Refuser un reset mdp (super_admin)

Importation dans main.py :
    from app.api.routers import utilisateurs
    app.include_router(
        utilisateurs.router, prefix=PREFIX_API
    )
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import verifier_super_admin
from app.logger import get_logger
from app.models.schemas.utilisateurs import (
    MessageReponseModele,
    ModifierUtilisateurModele,
    UtilisateurDetailModele,
    UtilisateurReponseModele,
)
from app.services import utilisateurs as service_utilisateurs


# Initialiser le logger pour ce module
logger = get_logger(__name__)

# Créer le routeur avec le préfixe /utilisateurs
router = APIRouter(
    prefix="/utilisateurs",
    tags=["Utilisateurs"],
)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — LISTAGE ET AFFICHAGE
# ─────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[UtilisateurReponseModele],
    summary="Lister tous les collaborateurs",
)
def lister_utilisateurs(
    admin: dict = Depends(verifier_super_admin),
) -> list:
    """
    Retourne la liste de tous les collaborateurs.
    Les mots de passe ne sont jamais inclus.
    Réservé au super_admin.
    """
    # Étape 1.1 — Récupérer tous les utilisateurs
    return service_utilisateurs.lister_utilisateurs()


@router.get(
    "/demandes",
    response_model=list[UtilisateurReponseModele],
    summary="Demandes d'inscription en attente",
)
def lister_demandes_en_attente(
    admin: dict = Depends(verifier_super_admin),
) -> list:
    """
    Retourne les collaborateurs en attente d'approbation.
    Utilisée par le super_admin pour gérer les inscriptions.
    """
    # Étape 1.2 — Récupérer les demandes en attente
    return service_utilisateurs.lister_demandes_en_attente()


@router.get(
    "/demandes-reinitialisation",
    response_model=list[dict],
    summary="Demandes de réinitialisation en attente",
)
def lister_demandes_reinitialisation(
    admin: dict = Depends(verifier_super_admin),
) -> list:
    """
    Retourne les demandes de réinitialisation de mot de
    passe en attente d'approbation.
    """
    # Étape 1.3 — Récupérer les demandes de reset mdp
    return (
        service_utilisateurs
        .lister_demandes_reinitialisation()
    )


@router.get(
    "/{id_utilisateur}",
    response_model=UtilisateurDetailModele,
    summary="Détails d'un collaborateur",
)
def afficher_utilisateur(
    id_utilisateur: int,
    admin         : dict = Depends(verifier_super_admin),
) -> dict:
    """
    Retourne les détails complets d'un collaborateur
    incluant la liste de tous ses projets accessibles.
    """
    # Étape 1.4 — Récupérer les détails du collaborateur
    try:
        return service_utilisateurs.afficher_utilisateur(
            id_utilisateur
        )
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(erreur),
        )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — MODIFICATION ET SUPPRESSION
# ─────────────────────────────────────────────────────────────

@router.put(
    "/{id_utilisateur}",
    response_model=UtilisateurReponseModele,
    summary="Modifier un collaborateur",
)
def modifier_utilisateur(
    id_utilisateur: int,
    donnees       : ModifierUtilisateurModele,
    admin         : dict = Depends(verifier_super_admin),
) -> dict:
    """
    Modifie les champs fournis d'un collaborateur.
    Seuls les champs non nuls sont mis à jour.
    """
    # Étape 2.1 — Modifier le collaborateur
    try:
        return service_utilisateurs.modifier_utilisateur(
            id_utilisateur = id_utilisateur,
            nouveau_nom    = donnees.nouveau_nom,
            nouveau_prenom = donnees.nouveau_prenom,
            nouveau_email  = donnees.nouveau_email,
            nouveau_mdp    = donnees.nouveau_mdp,
        )
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail      = str(erreur),
        )


@router.delete(
    "/{id_utilisateur}",
    response_model=MessageReponseModele,
    summary="Supprimer un collaborateur",
)
def supprimer_utilisateur(
    id_utilisateur: int,
    admin         : dict = Depends(verifier_super_admin),
) -> dict:
    """
    Supprime un collaborateur de la BD.
    Les keynotes créés par cet utilisateur sont conservés.
    """
    # Étape 2.2 — Supprimer le collaborateur
    try:
        service_utilisateurs.supprimer_utilisateur(
            id_utilisateur
        )
        return {
            "message": (
                f"Collaborateur {id_utilisateur} "
                "supprimé avec succès."
            )
        }
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(erreur),
        )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — APPROBATION ET REFUS DES INSCRIPTIONS
# ─────────────────────────────────────────────────────────────

@router.put(
    "/{id_utilisateur}/approuver",
    response_model=UtilisateurReponseModele,
    summary="Approuver une inscription",
)
def approuver_utilisateur(
    id_utilisateur: int,
    admin         : dict = Depends(verifier_super_admin),
) -> dict:
    """
    Approuve l'inscription d'un collaborateur.
    Le collaborateur peut ensuite se connecter.
    """
    # Étape 3.1 — Approuver le compte
    try:
        return service_utilisateurs.approuver_utilisateur(
            id_utilisateur
        )
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = str(erreur),
        )


@router.put(
    "/{id_utilisateur}/refuser",
    response_model=MessageReponseModele,
    summary="Refuser une inscription",
)
def refuser_utilisateur(
    id_utilisateur: int,
    admin         : dict = Depends(verifier_super_admin),
) -> dict:
    """
    Refuse et supprime le compte d'un collaborateur.
    Action irréversible.
    """
    # Étape 3.2 — Refuser et supprimer le compte
    try:
        service_utilisateurs.refuser_utilisateur(
            id_utilisateur
        )
        return {
            "message": (
                f"Inscription de l'utilisateur "
                f"{id_utilisateur} refusée et supprimée."
            )
        }
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(erreur),
        )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — APPROBATION ET REFUS DES REINITIALISATIONS
# ─────────────────────────────────────────────────────────────

@router.put(
    "/{id_utilisateur}/approuver-reinitialisation",
    response_model=MessageReponseModele,
    summary="Approuver une réinitialisation de mot de passe",
)
def approuver_reinitialisation(
    id_utilisateur: int,
    admin         : dict = Depends(verifier_super_admin),
) -> dict:
    """
    Approuve la demande de réinitialisation et applique
    le nouveau mot de passe à l'utilisateur.
    """
    # Étape 4.1 — Approuver la réinitialisation
    try:
        service_utilisateurs.approuver_reinitialisation(
            id_utilisateur
        )
        return {
            "message": (
                "Mot de passe réinitialisé avec succès."
            )
        }
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = str(erreur),
        )


@router.put(
    "/{id_utilisateur}/refuser-reinitialisation",
    response_model=MessageReponseModele,
    summary="Refuser une réinitialisation de mot de passe",
)
def refuser_reinitialisation(
    id_utilisateur: int,
    admin         : dict = Depends(verifier_super_admin),
) -> dict:
    """
    Refuse et supprime la demande de réinitialisation.
    Le mot de passe actuel reste inchangé.
    """
    # Étape 4.2 — Refuser la réinitialisation
    try:
        service_utilisateurs.refuser_reinitialisation(
            id_utilisateur
        )
        return {
            "message": (
                "Demande de réinitialisation refusée."
            )
        }
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(erreur),
        )