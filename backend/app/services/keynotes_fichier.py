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
# Pas de validation DMA à l'import — on accepte tous les formats Revit.
# La validation DMA s'applique uniquement à la création manuelle.


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

    Le fichier est écrit dans le dossier chemin_export
    du projet si défini, sinon dans CHEMIN_DOSSIER_KEYNOTES.

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
        # Le tri naturel garantit l'ordre : 1, 2, 10, 20
        # plutôt que 1, 10, 2, 20.
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

        # Étape 1.4 — Déterminer le dossier de destination
        # Priorité : chemin_export du projet → dossier par défaut
        projet = repo_projets.obtenir_projet_par_id(
            connexion, id_projet
        )
        chemin_export_projet = (
            projet.get("chemin_export") if projet else None
        )

        if chemin_export_projet and os.path.isdir(chemin_export_projet):
            # Utiliser le chemin d'export défini sur le projet
            dossier_destination = chemin_export_projet
        else:
            # Fallback sur le dossier par défaut du serveur
            dossier_destination = CHEMIN_DOSSIER_KEYNOTES
            if chemin_export_projet:
                logger.warning(
                    f"Chemin d'export '{chemin_export_projet}' "
                    "introuvable ou inaccessible — "
                    "utilisation du dossier par défaut."
                )

        # Étape 1.5 — Écrire le fichier .txt
        nom_fichier = _construire_nom_fichier(nom_projet)
        chemin_fichier = os.path.join(
            dossier_destination, nom_fichier
        )

        with open(
            chemin_fichier, "w",
            encoding=ENCODAGE_FICHIER_TXT
        ) as fichier:
            fichier.write("\n".join(lignes))

        logger.info(
            f"Fichier .txt exporté : {chemin_fichier}"
        )

        # Étape 1.6 — Mettre à jour txt_a_jour = True
        repo_projets.mettre_a_jour_txt_a_jour(
            connexion, id_projet, True
        )

        # Étape 1.7 — Enregistrer dans l'historique
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
        # Après import, il faut faire un export pour régénérer
        # le fichier .txt avec les nouvelles données.
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
    # On enregistre AVANT la suppression pour garder
    # une trace même si quelque chose échoue.
    repo_historique.inserer_historique(
        connexion,
        id_projet        = id_projet,
        table_cible      = "projet",
        action           = "import_remplacement",
        effectue_par_id  = effectue_par_id,
        effectue_par_role= effectue_par_role,
    )

    # Étape 3.2 — Supprimer toutes les catégories
    # ON DELETE CASCADE supprime automatiquement les notes
    # liées à chaque catégorie supprimée.
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
    Accepte tous les formats de numéros — pas de validation DMA à l'import.

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
    nb_notes      = 0

    for item in keynotes_parsed:
        numero_cat = item["numero_categorie"]
        desc_cat   = item["description_categorie"]

        # Mode fusion — vérifier si la catégorie existe déjà
        if ignorer_doublons:
            numero_disponible = (
                repo_categories
                .verifier_numero_categorie_unique(
                    connexion, id_projet, numero_cat
                )
            )
            if not numero_disponible:
                # Catégorie existante — récupérer son ID et traiter
                # quand même ses notes pour ajouter les nouvelles
                categorie_existante = (
                    repo_categories.obtenir_categorie_par_numero(
                        connexion, id_projet, numero_cat
                    )
                )
                if categorie_existante:
                    nb_notes += _inserer_notes(
                        connexion,
                        id_projet,
                        categorie_existante["id"],
                        numero_cat,
                        item["notes"],
                        effectue_par_id,
                        effectue_par_role,
                        action_note,
                        ignorer_doublons,
                    )
                continue

        # Créer la nouvelle catégorie
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
            nouvelle_valeur  = f"{numero_cat} — {desc_cat}",
        )

        # Insérer les notes de la nouvelle catégorie
        nb_notes += _inserer_notes(
            connexion,
            id_projet,
            categorie["id"],
            item["notes"],
            effectue_par_id,
            effectue_par_role,
            action_note,
            ignorer_doublons,
        )

    logger.info(
        f"Import : {nb_categories} catégories, "
        f"{nb_notes} notes insérées."
    )

    return {
        "categories_inserees": nb_categories,
        "notes_inserees"     : nb_notes,
    }


def _inserer_notes(
    connexion        : object,
    id_projet        : int,
    id_categorie     : int,
    notes            : list[dict],
    effectue_par_id  : int,
    effectue_par_role: str,
    action_note      : str,
    ignorer_doublons : bool,
) -> int:
    """
    Insère les notes d'une catégorie.
    Utilisée aussi bien pour les catégories nouvelles
    que pour les catégories existantes en mode fusion.

    Args:
        connexion        : Connexion PostgreSQL active
        id_projet        : ID du projet
        id_categorie     : ID de la catégorie parente
        notes            : Liste des notes à insérer
        effectue_par_id  : ID de l'auteur
        effectue_par_role: Rôle de l'auteur
        action_note      : Action à enregistrer dans l'historique
        ignorer_doublons : Si True, ignore les numéros existants

    Returns:
        Nombre de notes insérées
    """
    nb_notes = 0

    for note in notes:
        numero_note = note["numero"]
        desc_note   = note["description"]

        # Mode fusion — ignorer si le numéro existe déjà
        if ignorer_doublons:
            numero_disponible = (
                repo_notes.verifier_numero_note_unique(
                    connexion, id_projet, numero_note
                )
            )
            if not numero_disponible:
                continue

            # Ignorer aussi si la description existe déjà dans la catégorie
            # pour éviter les doublons de contenu
            description_disponible = (
                repo_notes.verifier_description_note_unique(
                    connexion, id_categorie, desc_note
                )
            )
            if not description_disponible:
                logger.info(
                    f"Import : note '{numero_note}' ignorée — "
                    "description déjà présente dans la catégorie."
                )
                continue

        # Insérer la note
        note_inseree = repo_notes.inserer_note(
            connexion,
            id_projet,
            id_categorie,
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
            nouvelle_valeur  = f"{numero_note} — {desc_note}",
        )

    return nb_notes


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
    # Chaque ligne a 3 colonnes séparées par tabulation :
    #   Col 1 : numéro (catégorie ou note)
    #   Col 2 : description
    #   Col 3 : numéro parent (vide = catégorie, sinon note)
    keynotes_par_categorie = {}
    ordre_categories = []

    # Dernière entrée traitée — pour fusionner les descriptions multi-lignes
    # Une continuation est une ligne dont la 1re colonne n'est pas un Key Value Revit
    derniere_entree: dict | None = None

    for numero_ligne, ligne in enumerate(lignes, 1):
        colonnes = ligne.split(SEPARATEUR_COLONNES_TXT)

        # Détecter si c'est une ligne de continuation :
        # — 1 seule colonne, OU
        # — première colonne non vide mais pas un numéro Revit valide
        premiere_colonne = colonnes[0].strip()
        est_continuation = (
            derniere_entree is not None
            and premiere_colonne
            and not re.match(r'^(D?A?)\d+$', premiere_colonne.upper())
        )

        if est_continuation:
            # Reconstituer le texte complet de la ligne (toutes colonnes)
            texte_continuation = ' '.join(c.strip() for c in colonnes if c.strip())
            if texte_continuation:
                obj   = derniere_entree["description_ref"]
                champ = derniere_entree["champ"]
                obj[champ] += " " + texte_continuation
            continue

        # Ligne malformée sans entrée précédente — ignorer
        if len(colonnes) < 2:
            logger.warning(
                f"Import : ligne {numero_ligne} ignorée — "
                "format invalide (attendu : numéro[TAB]description[TAB]parent)."
            )
            derniere_entree = None
            continue

        numero      = colonnes[0].strip()
        description = colonnes[1].strip() if len(colonnes) > 1 else ""
        parent      = colonnes[2].strip() if len(colonnes) > 2 else ""

        # Ignorer les lignes sans numéro
        if not numero:
            logger.warning(
                f"Import : ligne {numero_ligne} ignorée — numéro vide."
            )
            continue

        if parent == "":
            # 3e colonne vide → catégorie racine
            entree = {
                "numero_categorie"     : numero,
                "description_categorie": description,
                "notes"                : [],
            }
            keynotes_par_categorie[numero] = entree
            ordre_categories.append(numero)
            derniere_entree = {"description_ref": entree, "champ": "description_categorie"}
        else:
            # 3e colonne remplie → note appartenant à ce parent
            if parent not in keynotes_par_categorie:
                logger.warning(
                    f"Import : ligne {numero_ligne} — catégorie "
                    f"parent '{parent}' introuvable, note ignorée."
                )
                derniere_entree = None
                continue
            note = {
                "numero"     : numero,
                "description": description,
            }
            keynotes_par_categorie[parent]["notes"].append(note)
            derniere_entree = {"description_ref": note, "champ": "description"}

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
    # re.split sépare en alternant texte et chiffres.
    # Ex: "A-300" → ["A-", 300, ""]
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
    # Nom du fichier = nom du projet tel quel + .txt
    # Ex: projet "2026-016" → "2026-016.txt"
    # Garder le nom du projet tel quel — pas de transformation
    return f"{nom_projet.strip()}{EXTENSION_FICHIER_KEYNOTES}"
