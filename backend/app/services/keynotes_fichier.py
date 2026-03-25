"""
services/keynotes_fichier.py
----------------------------
Logique métier — Export et Import fichier .txt Revit.

Rôle :
    - Exporter les keynotes au format standard Revit (.txt)
    - Importer un fichier .txt existant dans un projet
    - Valider le format et l'encodage du fichier importé
    - Gérer les modes d'import (remplacer ou fusionner)
    - Enregistrer les actions dans l'historique

Format du fichier .txt Revit (3 colonnes, tabulation) :
    300     Architecture
    A-300   Béton armé coulé en place   300
    B-300   Béton préfabriqué           300
    100     Structure
    A-100   Acier structurel            100

Importation :
    from app.services.keynotes_fichier import (
        exporter_fichier_txt,
        importer_fichier_txt,
    )
"""

import os
import re

from app.config import (
    CHEMIN_DOSSIER_KEYNOTES,
    ENCODAGE_FICHIER_TXT,
    SEPARATEUR_COLONNES_TXT,
    EXTENSION_FICHIER_KEYNOTES,
    TAILLE_MAX_FICHIER_IMPORT,
)
from app.database.connection import creer_connexion
from app.logger import get_logger
from app.repositories import categories as repo_categories
from app.repositories import notes as repo_notes
from app.repositories import projets as repo_projets
from app.repositories import historique as repo_historique


# Initialiser le logger pour ce module
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — EXPORT DU FICHIER .TXT REVIT
# ─────────────────────────────────────────────────────────────

def exporter_fichier_txt(
    id_projet        : int,
    nom_projet       : str,
    effectue_par_id  : int,
    effectue_par_role: str,
) -> str:
    """
    Génère le fichier .txt keynotes au format Revit.
    Tri numérique naturel (1, 2, 10 et non 1, 10, 2).
    Met à jour txt_a_jour = True après l'export.

    Format généré :
        numero_cat  description_cat  (vide)
        numero_note description_note numero_cat_parent

    Args:
        id_projet        : ID du projet
        nom_projet       : Nom du projet (pour le fichier)
        effectue_par_id  : ID de l'auteur de l'export
        effectue_par_role: Rôle de l'auteur

    Returns:
        Chemin complet du fichier .txt généré
    """
    connexion = creer_connexion()

    try:
        # Étape 1.1 — Récupérer toutes les catégories
        categories = repo_categories.lister_categories_du_projet(
            connexion, id_projet
        )

        # Étape 1.2 — Trier les catégories numériquement
        """
        Le tri naturel garantit l'ordre :
        1, 2, 10, 20 plutôt que 1, 10, 2, 20.
        """
        categories_triees = sorted(
            categories,
            key=lambda c: _cle_tri_naturel(c["numero"])
        )

        # Étape 1.3 — Construire le contenu du fichier
        lignes = []
        for categorie in categories_triees:

            # Ligne de catégorie (3e colonne vide = racine)
            ligne_categorie = SEPARATEUR_COLONNES_TXT.join([
                categorie["numero"],
                categorie["description"],
                "",
            ])
            lignes.append(ligne_categorie)

            # Récupérer les notes de cette catégorie
            notes = repo_notes.lister_notes_de_categorie(
                connexion, categorie["id"]
            )

            # Trier les notes numériquement
            notes_triees = sorted(
                notes,
                key=lambda n: _cle_tri_naturel(n["numero"])
            )

            for note in notes_triees:
                # Ligne de note (3e colonne = catégorie parent)
                ligne_note = SEPARATEUR_COLONNES_TXT.join([
                    note["numero"],
                    note["description"],
                    categorie["numero"],
                ])
                lignes.append(ligne_note)

        # Étape 1.4 — Écrire le fichier .txt
        nom_fichier = _construire_nom_fichier(nom_projet)
        chemin_fichier = os.path.join(
            CHEMIN_DOSSIER_KEYNOTES, nom_fichier
        )

        with open(
            chemin_fichier, "w",
            encoding=ENCODAGE_FICHIER_TXT
        ) as fichier:
            fichier.write("\n".join(lignes))

        logger.info(
            f"Fichier .txt exporté : {nom_fichier}"
        )

        # Étape 1.5 — Mettre à jour txt_a_jour = True
        repo_projets.mettre_a_jour_txt_a_jour(
            connexion, id_projet, True
        )

        # Étape 1.6 — Enregistrer dans l'historique
        repo_historique.inserer_historique(
            connexion,
            id_projet        = id_projet,
            table_cible      = "projet",
            action           = "export_txt",
            effectue_par_id  = effectue_par_id,
            effectue_par_role= effectue_par_role,
            nouvelle_valeur  = chemin_fichier,
        )

        return chemin_fichier

    except Exception as erreur:
        logger.error(
            f"Erreur export fichier .txt : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — IMPORT DU FICHIER .TXT REVIT
# ─────────────────────────────────────────────────────────────

def importer_fichier_txt(
    id_projet        : int,
    contenu_txt      : str,
    mode             : str,
    effectue_par_id  : int,
    effectue_par_role: str,
) -> dict:
    """
    Importe un fichier .txt keynotes Revit dans un projet.

    Modes disponibles :
        'remplacer' → supprime tout et importe le fichier
        'fusionner' → ajoute uniquement les nouveaux éléments

    Args:
        id_projet        : ID du projet
        contenu_txt      : Contenu du fichier .txt en UTF-8
        mode             : 'remplacer' ou 'fusionner'
        effectue_par_id  : ID de l'auteur de l'import
        effectue_par_role: Rôle de l'auteur

    Returns:
        Dictionnaire avec les statistiques d'import

    Raises:
        ValueError: Si le format ou l'encodage est invalide
    """
    connexion = creer_connexion()

    try:
        # Étape 2.1 — Valider la taille du fichier
        taille_bytes = len(contenu_txt.encode("utf-8"))
        if taille_bytes > TAILLE_MAX_FICHIER_IMPORT:
            taille_mb = TAILLE_MAX_FICHIER_IMPORT // (
                1024 * 1024
            )
            raise ValueError(
                f"Le fichier dépasse la taille maximale "
                f"autorisée de {taille_mb} MB."
            )

        # Étape 2.2 — Parser le contenu du fichier
        keynotes_parsed = _parser_fichier_txt(contenu_txt)

        # Étape 2.3 — Appliquer le mode d'import
        if mode == "remplacer":
            stats = _importer_mode_remplacer(
                connexion,
                id_projet,
                keynotes_parsed,
                effectue_par_id,
                effectue_par_role,
            )
        else:
            stats = _importer_mode_fusionner(
                connexion,
                id_projet,
                keynotes_parsed,
                effectue_par_id,
                effectue_par_role,
            )

        # Étape 2.4 — Marquer le fichier .txt comme périmé
        """
        Après import, le fichier .txt sur le serveur ne
        reflète pas encore les données importées.
        Il faut faire un export pour le régénérer.
        """
        repo_projets.mettre_a_jour_txt_a_jour(
            connexion, id_projet, False
        )

        return stats

    except ValueError:
        raise
    except Exception as erreur:
        logger.error(
            f"Erreur import fichier .txt : {erreur}"
        )
        raise
    finally:
        connexion.close()


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — FONCTIONS PRIVÉES D'IMPORT
# ─────────────────────────────────────────────────────────────

def _importer_mode_remplacer(
    connexion        : object,
    id_projet        : int,
    keynotes_parsed  : list[dict],
    effectue_par_id  : int,
    effectue_par_role: str,
) -> dict:
    """
    Supprime toutes les données du projet et importe
    le contenu du fichier .txt.

    Args:
        connexion        : Connexion PostgreSQL active
        id_projet        : ID du projet
        keynotes_parsed  : Keynotes parsés du fichier
        effectue_par_id  : ID de l'auteur
        effectue_par_role: Rôle de l'auteur

    Returns:
        Statistiques d'import
    """
    # Étape 3.1 — Enregistrer l'import dans l'historique
    """
    On enregistre AVANT la suppression pour garder
    une trace de l'opération même si quelque chose échoue.
    """
    repo_historique.inserer_historique(
        connexion,
        id_projet        = id_projet,
        table_cible      = "projet",
        action           = "import_remplacement",
        effectue_par_id  = effectue_par_id,
        effectue_par_role= effectue_par_role,
    )

    # Étape 3.2 — Supprimer toutes les catégories
    """
    ON DELETE CASCADE supprime automatiquement les notes
    liées à chaque catégorie supprimée.
    """
    categories_existantes = (
        repo_categories.lister_categories_du_projet(
            connexion, id_projet
        )
    )
    for categorie in categories_existantes:
        repo_categories.supprimer_categorie(
            connexion, categorie["id"]
        )

    # Étape 3.3 — Importer les nouvelles données
    return _inserer_keynotes(
        connexion,
        id_projet,
        keynotes_parsed,
        effectue_par_id,
        effectue_par_role,
        action_categorie="creation",
        action_note="creation",
    )


def _importer_mode_fusionner(
    connexion        : object,
    id_projet        : int,
    keynotes_parsed  : list[dict],
    effectue_par_id  : int,
    effectue_par_role: str,
) -> dict:
    """
    Ajoute uniquement les catégories et notes nouvelles.
    Ignore les éléments dont le numéro existe déjà.

    Args:
        connexion        : Connexion PostgreSQL active
        id_projet        : ID du projet
        keynotes_parsed  : Keynotes parsés du fichier
        effectue_par_id  : ID de l'auteur
        effectue_par_role: Rôle de l'auteur

    Returns:
        Statistiques d'import
    """
    # Étape 3.4 — Insérer uniquement les nouveaux éléments
    return _inserer_keynotes(
        connexion,
        id_projet,
        keynotes_parsed,
        effectue_par_id,
        effectue_par_role,
        action_categorie="import_fusion_categorie",
        action_note="import_fusion_note",
        ignorer_doublons=True,
    )


def _inserer_keynotes(
    connexion        : object,
    id_projet        : int,
    keynotes_parsed  : list[dict],
    effectue_par_id  : int,
    effectue_par_role: str,
    action_categorie : str,
    action_note      : str,
    ignorer_doublons : bool = False,
) -> dict:
    """
    Insère les catégories et notes parsées dans la BD.
    Gère les doublons selon le paramètre ignorer_doublons.

    Args:
        connexion        : Connexion PostgreSQL active
        id_projet        : ID du projet
        keynotes_parsed  : Liste de dicts avec catégories/notes
        effectue_par_id  : ID de l'auteur
        effectue_par_role: Rôle de l'auteur
        action_categorie : Action à enregistrer (historique)
        action_note      : Action à enregistrer (historique)
        ignorer_doublons : Si True, ignore les numéros existants

    Returns:
        Statistiques : nb categories et notes insérées
    """
    # Étape 3.5 — Insérer catégories et notes
    nb_categories = 0
    nb_notes = 0

    for item in keynotes_parsed:
        # Insérer la catégorie
        numero_cat = item["numero_categorie"]
        desc_cat = item["description_categorie"]

        # Vérifier si la catégorie existe déjà
        if ignorer_doublons:
            numero_disponible = (
                repo_categories
                .verifier_numero_categorie_unique(
                    connexion, id_projet, numero_cat
                )
            )
            if not numero_disponible:
                continue

        categorie = repo_categories.inserer_categorie(
            connexion,
            id_projet,
            numero_cat,
            desc_cat,
            effectue_par_id,
        )
        nb_categories += 1

        # Enregistrer dans l'historique
        repo_historique.inserer_historique(
            connexion,
            id_projet        = id_projet,
            table_cible      = "categories",
            action           = action_categorie,
            effectue_par_id  = effectue_par_id,
            effectue_par_role= effectue_par_role,
            id_cible         = categorie["id"],
            nouvelle_valeur  = (
                f"{numero_cat} — {desc_cat}"
            ),
        )

        # Insérer les notes de cette catégorie
        for note in item["notes"]:
            numero_note = note["numero"]
            desc_note = note["description"]

            # Vérifier si la note existe déjà
            if ignorer_doublons:
                numero_disponible = (
                    repo_notes.verifier_numero_note_unique(
                        connexion, id_projet, numero_note
                    )
                )
                if not numero_disponible:
                    continue

            note_inseree = repo_notes.inserer_note(
                connexion,
                id_projet,
                categorie["id"],
                numero_note,
                desc_note,
                effectue_par_id,
            )
            nb_notes += 1

            # Enregistrer dans l'historique
            repo_historique.inserer_historique(
                connexion,
                id_projet        = id_projet,
                table_cible      = "notes",
                action           = action_note,
                effectue_par_id  = effectue_par_id,
                effectue_par_role= effectue_par_role,
                id_cible         = note_inseree["id"],
                nouvelle_valeur  = (
                    f"{numero_note} — {desc_note}"
                ),
            )

    logger.info(
        f"Import : {nb_categories} catégories, "
        f"{nb_notes} notes insérées."
    )

    return {
        "categories_inserees": nb_categories,
        "notes_inserees"     : nb_notes,
    }


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — FONCTIONS UTILITAIRES PRIVÉES
# ─────────────────────────────────────────────────────────────

def _parser_fichier_txt(contenu_txt: str) -> list[dict]:
    """
    Parse le contenu d'un fichier .txt keynotes Revit.
    Identifie les catégories et leurs notes associées.

    Format attendu (3 colonnes séparées par tabulation) :
        300     Architecture            (vide = catégorie)
        A-300   Béton armé coulé        300  (note)

    Args:
        contenu_txt: Contenu du fichier .txt en UTF-8

    Returns:
        Liste de dicts avec catégories et leurs notes

    Raises:
        ValueError: Si le format est invalide
    """
    # Étape 4.1 — Diviser en lignes et nettoyer
    lignes = [
        ligne.strip()
        for ligne in contenu_txt.splitlines()
        if ligne.strip()
    ]

    if not lignes:
        raise ValueError(
            "Le fichier .txt est vide ou ne contient "
            "pas de données valides."
        )

    # Étape 4.2 — Parser chaque ligne
    """
    Chaque ligne a 3 colonnes séparées par tabulation :
        Col 1 : numéro (catégorie ou note)
        Col 2 : description
        Col 3 : numéro parent (vide = catégorie, sinon note)
    """
    keynotes_par_categorie = {}
    ordre_categories = []

    for numero_ligne, ligne in enumerate(lignes, 1):
        colonnes = ligne.split(SEPARATEUR_COLONNES_TXT)

        # Vérifier qu'il y a au moins 2 colonnes
        if len(colonnes) < 2:
            raise ValueError(
                f"Format invalide à la ligne {numero_ligne}."
                " Format attendu : numéro[TAB]description"
                "[TAB]parent."
            )

        numero = colonnes[0].strip()
        description = colonnes[1].strip()
        parent = colonnes[2].strip() if (
            len(colonnes) > 2
        ) else ""

        # Valider que le numéro n'est pas vide
        if not numero or not description:
            raise ValueError(
                f"Ligne {numero_ligne} : le numéro et "
                "la description sont obligatoires."
            )

        if parent == "":
            # Ligne sans parent = catégorie
            keynotes_par_categorie[numero] = {
                "numero_categorie"    : numero,
                "description_categorie": description,
                "notes"               : [],
            }
            ordre_categories.append(numero)
        else:
            # Ligne avec parent = note
            if parent not in keynotes_par_categorie:
                raise ValueError(
                    f"Ligne {numero_ligne} : la catégorie "
                    f"parent '{parent}' n'a pas été "
                    "définie avant cette note."
                )
            keynotes_par_categorie[parent]["notes"].append({
                "numero"     : numero,
                "description": description,
            })

    # Étape 4.3 — Retourner dans l'ordre de lecture
    return [
        keynotes_par_categorie[num]
        for num in ordre_categories
    ]


def _cle_tri_naturel(valeur: str) -> list:
    """
    Génère une clé de tri naturel numérique.
    Permet de trier 1, 2, 10 au lieu de 1, 10, 2.

    Args:
        valeur: Chaîne à trier (ex: "A-300", "10", "2")

    Returns:
        Liste utilisable comme clé de tri
    """
    # Étape 4.4 — Séparer les parties numériques et texte
    """
    re.split sépare la chaîne en alternant texte et chiffres.
    Ex: "A-300" → ["A-", 300, ""]
    Les parties numériques sont converties en int pour
    un tri numérique correct.
    """
    parties = re.split(r"(\d+)", valeur.lower())
    return [
        int(partie) if partie.isdigit() else partie
        for partie in parties
    ]


def _construire_nom_fichier(nom_projet: str) -> str:
    """
    Construit le nom du fichier .txt à partir du nom
    du projet.

    Args:
        nom_projet: Nom du projet Revit

    Returns:
        Nom du fichier .txt
    """
    # Étape 4.5 — Normaliser le nom pour le fichier
    nom_nettoye = nom_projet.lower().strip()
    nom_nettoye = nom_nettoye.replace(" ", "_")
    nom_nettoye = "".join(
        c for c in nom_nettoye
        if c.isalnum() or c == "_"
    )
    return f"keynotes_{nom_nettoye}{EXTENSION_FICHIER_KEYNOTES}"