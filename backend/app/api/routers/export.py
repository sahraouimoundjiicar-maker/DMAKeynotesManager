"""
api/routers/export.py
---------------------
Route d'export du fichier .txt Revit — /api/v1/projets/...

Routes définies :
    GET /api/v1/projets/{id}/exporter
        → Télécharger le fichier .txt Revit (utilisateur + super_admin)

Comportement :
    Le fichier .txt est généré en mémoire et retourné
    directement comme téléchargement dans le navigateur.
    Aucun fichier n'est écrit sur le serveur.

Importation dans main.py :
    from app.api.routers import export
    app.include_router(export.router, prefix=PREFIX_API)
"""

import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.api.dependencies import verifier_utilisateur
from app.config import (
    ENCODAGE_FICHIER_TXT,
    SEPARATEUR_COLONNES_TXT,
    EXTENSION_FICHIER_KEYNOTES,
)
from app.database.connection import creer_connexion
from app.logger import get_logger
from app.repositories import categories as repo_categories
from app.repositories import notes as repo_notes
from app.repositories import projets as repo_projets
from app.repositories import historique as repo_historique
from app.services import projets as service_projets


# Initialiser le logger pour ce module
logger = get_logger(__name__)

# Créer le routeur avec le préfixe /projets
router = APIRouter(prefix="/projets", tags=["Export"])


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — EXPORT FICHIER .TXT REVIT (TÉLÉCHARGEMENT)
# ─────────────────────────────────────────────────────────────

@router.get(
    "/{id_projet}/exporter",
    summary="Télécharger le fichier .txt Revit",
)
def exporter_fichier_txt(
    id_projet  : int,
    utilisateur: dict = Depends(verifier_utilisateur),
) -> Response:
    """
    Génère le fichier .txt keynotes au format standard Revit
    et le retourne comme téléchargement direct.

    Le fichier est généré en mémoire — rien n'est écrit
    sur le serveur. Le navigateur propose le téléchargement
    directement sur le poste de l'utilisateur.

    Format généré :
        numéro[TAB]description[TAB]parent
    Encodage : UTF-16 LE avec BOM (format natif Revit)
    Tri : numérique naturel (1, 2, 10 et non 1, 10, 2)
    """
    # Étape 1.1 — Récupérer les infos du projet
    try:
        projet = service_projets.afficher_projet(id_projet)
    except ValueError as erreur:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(erreur),
        )

    # Étape 1.2 — Générer le contenu du fichier en mémoire
    try:
        contenu_txt = _generer_contenu_txt(id_projet)
    except Exception as erreur:
        logger.error(
            f"Erreur génération .txt projet {id_projet} : "
            f"{erreur}"
        )
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail      = "Erreur lors de la génération du fichier .txt.",
        )

    # Étape 1.3 — Enregistrer l'export dans l'historique
    # et mettre à jour txt_a_jour = True
    role = utilisateur.get("role", "utilisateur")
    connexion = creer_connexion()
    try:
        repo_projets.mettre_a_jour_txt_a_jour(
            connexion, id_projet, True
        )
        repo_historique.inserer_historique(
            connexion,
            id_projet         = id_projet,
            table_cible       = "projet",
            action            = "export_txt",
            effectue_par_id   = utilisateur["id"],
            effectue_par_role = role,
            nouvelle_valeur   = _construire_nom_fichier(projet["nom"]),
        )
    except Exception as erreur:
        logger.warning(
            f"Historique export non enregistré : {erreur}"
        )
    finally:
        connexion.close()

    # Étape 1.4 — Encoder en UTF-16 LE avec BOM (format natif Revit)
    # Revit attend le format UTF-16 LE avec BOM — c'est le format
    # utilisé nativement dans les fichiers keynotes Revit.
    contenu_bytes = contenu_txt.encode("utf-16-le")
    bom = b'\xff\xfe'  # BOM UTF-16 LE
    contenu_final = bom + contenu_bytes

    # Étape 1.5 — Construire le nom du fichier de téléchargement
    nom_fichier = _construire_nom_fichier(projet["nom"])

    logger.info(
        f"Export .txt téléchargé : projet {id_projet} "
        f"par utilisateur {utilisateur['id']}"
    )

    # Étape 1.6 — Retourner le fichier comme téléchargement
    return Response(
        content     = contenu_final,
        media_type  = "text/plain; charset=utf-16",
        headers     = {
            "Content-Disposition": (
                f'attachment; filename="{nom_fichier}"'
            ),
        },
    )


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — FONCTIONS UTILITAIRES PRIVÉES
# ─────────────────────────────────────────────────────────────

def _generer_contenu_txt(id_projet: int) -> str:
    """
    Génère le contenu du fichier .txt keynotes en mémoire.
    Tri numérique naturel sur les numéros de catégories et notes.

    Args:
        id_projet: ID du projet

    Returns:
        Contenu du fichier .txt sous forme de chaîne
    """
    connexion = creer_connexion()

    try:
        # Étape 2.1 — Récupérer et trier les catégories
        categories = repo_categories.lister_categories_du_projet(
            connexion, id_projet
        )
        categories_triees = sorted(
            categories,
            key=lambda c: _cle_tri_naturel(c["numero"])
        )

        # Étape 2.2 — Construire les lignes du fichier
        lignes = []
        for categorie in categories_triees:

            # Ligne de catégorie (3e colonne vide = racine)
            ligne_categorie = SEPARATEUR_COLONNES_TXT.join([
                categorie["numero"],
                categorie["description"],
                "",
            ])
            lignes.append(ligne_categorie)

            # Récupérer et trier les notes de cette catégorie
            notes = repo_notes.lister_notes_de_categorie(
                connexion, categorie["id"]
            )
            notes_triees = sorted(
                notes,
                key=lambda n: _cle_tri_naturel(n["numero"])
            )

            for note in notes_triees:
                # Ligne de note (3e colonne = catégorie parente)
                ligne_note = SEPARATEUR_COLONNES_TXT.join([
                    note["numero"],
                    note["description"],
                    categorie["numero"],
                ])
                lignes.append(ligne_note)

        return "\n".join(lignes)

    finally:
        connexion.close()


def _cle_tri_naturel(valeur: str) -> list:
    """
    Génère une clé de tri naturel numérique.
    Permet de trier 1, 2, 10 au lieu de 1, 10, 2.

    Args:
        valeur: Chaîne à trier (ex: "D200", "100", "20")

    Returns:
        Liste utilisable comme clé de tri
    """
    parties = re.split(r"(\d+)", valeur.lower())
    return [
        int(partie) if partie.isdigit() else partie
        for partie in parties
    ]


def _construire_nom_fichier(nom_projet: str) -> str:
    """
    Construit le nom du fichier .txt à partir du nom du projet.

    Args:
        nom_projet: Nom du projet Revit

    Returns:
        Nom du fichier .txt (ex: keynotes_ecole_primaire.txt)
    """
    nom_nettoye = nom_projet.lower().strip()
    nom_nettoye = nom_nettoye.replace(" ", "_")
    nom_nettoye = "".join(
        c for c in nom_nettoye
        if c.isalnum() or c == "_"
    )
    return f"keynotes_{nom_nettoye}{EXTENSION_FICHIER_KEYNOTES}"
