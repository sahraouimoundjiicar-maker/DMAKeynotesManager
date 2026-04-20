"""
utils/revit_numerotation.py
---------------------------
Logique de validation et génération des numéros Revit keynotes.

Règles de numérotation :
    Catégories :
        - Multiples de 10  (000-090) : 000, 010, 020... 090
        - Multiples de 100 (≥100)   : 100, 200, 300...
        - Avec préfixe D            : D000, D020, D100, D200...

    Notes :
        - Catégorie multiple de 10  → range +1 à +9  (ex: 020 → 021-029)
        - Catégorie multiple de 100 → range +1 à +99 (ex: 200 → 201-299)
        - Même logique avec préfixe D

Importation :
    from app.utils.revit_numerotation import (
        valider_numero_categorie,
        valider_numero_note,
        calculer_range_note,
        normaliser_numero_import,
    )
"""

import re
from typing import Optional


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — NORMALISATION À L'IMPORT
# ─────────────────────────────────────────────────────────────

def normaliser_numero_import(numero: str) -> str:
    """
    Normalise un numéro provenant d'un fichier .txt importé.
    Supprime le préfixe 'A' non standard pour obtenir
    le format Revit conforme.

    Règles :
        A200  → 200   (supprime A)
        A020  → 020   (supprime A)
        DA200 → D200  (supprime le A après D)
        DA020 → D020  (supprime le A après D)
        D200  → D200  (inchangé)
        200   → 200   (inchangé)

    Args:
        numero: Numéro brut du fichier importé

    Returns:
        Numéro normalisé au format Revit
    """
    # Étape 1.1 — Normaliser en majuscules
    numero_maj = numero.strip().upper()

    # Étape 1.2 — Cas DA... → D... (ex: DA200 → D200)
    if numero_maj.startswith('DA'):
        return 'D' + numero_maj[2:]

    # Étape 1.3 — Cas A... → ... (ex: A200 → 200)
    if numero_maj.startswith('A'):
        # Vérifier que c'est bien un préfixe A suivi de chiffres
        reste = numero_maj[1:]
        if reste and reste[0].isdigit():
            return reste

    return numero_maj


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — VALIDATION DU NUMÉRO DE CATÉGORIE
# ─────────────────────────────────────────────────────────────

def valider_numero_categorie(numero: str) -> bool:
    """
    Vérifie que le numéro respecte le format Revit
    pour une catégorie.

    Format accepté :
        - Multiples de 10  (000-090) : 000, 010, 020... 090
        - Multiples de 100 (≥100)   : 100, 200, 300...
        - Avec préfixe D            : D000, D020, D100, D200...

    Args:
        numero: Numéro de la catégorie à valider

    Returns:
        True si le format est valide, False sinon
    """
    # Étape 2.1 — Normaliser
    numero_normalise = numero.strip().upper()

    # Étape 2.2 — Extraire préfixe et partie numérique
    # Accepte préfixe "" ou "D" uniquement
    match = re.match(r'^(D?)(\d+)$', numero_normalise)
    if not match:
        return False

    partie_numerique = int(match.group(2))

    # Étape 2.3 — Vérifier les règles numériques
    # Multiples de 10 entre 0 et 90 inclus
    if 0 <= partie_numerique <= 90:
        return partie_numerique % 10 == 0

    # Multiples de 100 à partir de 100
    if partie_numerique >= 100:
        return partie_numerique % 100 == 0

    return False


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 — CALCUL DU RANGE VALIDE POUR UNE CATÉGORIE
# ─────────────────────────────────────────────────────────────

def calculer_range_note(
    numero_categorie: str,
) -> Optional[dict]:
    """
    Calcule le range valide des numéros de notes
    pour une catégorie donnée.

    Args:
        numero_categorie: Numéro de la catégorie parente

    Returns:
        Dictionnaire avec prefixe, base, min, max
        ou None si le format est invalide

    Exemples :
        "020"  → {"prefixe": "",  "base": 20,  "min": 21,  "max": 29 }
        "100"  → {"prefixe": "",  "base": 100, "min": 101, "max": 199}
        "D020" → {"prefixe": "D", "base": 20,  "min": 21,  "max": 29 }
        "D200" → {"prefixe": "D", "base": 200, "min": 201, "max": 299}
    """
    # Étape 3.1 — Normaliser
    numero_normalise = numero_categorie.strip().upper()

    # Étape 3.2 — Extraire préfixe et partie numérique
    match = re.match(r'^(D?)(\d+)$', numero_normalise)
    if not match:
        return None

    prefixe          = match.group(1)  # "D" ou ""
    partie_numerique = int(match.group(2))

    # Étape 3.3 — Calculer min/max selon la règle
    if 0 <= partie_numerique <= 90 and partie_numerique % 10 == 0:
        # Catégorie multiple de 10 → range +1 à +9
        return {
            "prefixe": prefixe,
            "base"   : partie_numerique,
            "min"    : partie_numerique + 1,
            "max"    : partie_numerique + 9,
        }

    if partie_numerique >= 100 and partie_numerique % 100 == 0:
        # Catégorie multiple de 100 → range +1 à +99
        return {
            "prefixe": prefixe,
            "base"   : partie_numerique,
            "min"    : partie_numerique + 1,
            "max"    : partie_numerique + 99,
        }

    return None


# ─────────────────────────────────────────────────────────────
# ÉTAPE 4 — VALIDATION DU NUMÉRO DE NOTE
# ─────────────────────────────────────────────────────────────

def valider_numero_note(
    numero_note     : str,
    numero_categorie: str,
) -> bool:
    """
    Vérifie que le numéro de note respecte le range
    de sa catégorie parente.

    Args:
        numero_note     : Numéro de la note à valider
        numero_categorie: Numéro de la catégorie parente

    Returns:
        True si le numéro est dans le range, False sinon

    Exemples :
        valider_numero_note("021", "020") → True
        valider_numero_note("030", "020") → False (hors range 021-029)
        valider_numero_note("101", "100") → True
        valider_numero_note("D201", "D200") → True
    """
    # Étape 4.1 — Calculer le range de la catégorie
    range_valide = calculer_range_note(numero_categorie)
    if not range_valide:
        return False

    # Étape 4.2 — Normaliser le numéro de note
    numero_normalise = numero_note.strip().upper()

    # Étape 4.3 — Vérifier que le préfixe correspond
    prefixe = range_valide["prefixe"]
    if not numero_normalise.startswith(prefixe):
        return False

    # Étape 4.4 — Extraire et valider la partie numérique
    partie_numerique = numero_normalise[len(prefixe):]
    try:
        valeur = int(partie_numerique)
    except ValueError:
        return False

    return range_valide["min"] <= valeur <= range_valide["max"]


# ─────────────────────────────────────────────────────────────
# ÉTAPE 5 — MESSAGE D'ERREUR FORMATÉ
# ─────────────────────────────────────────────────────────────

def message_range_invalide(numero_categorie: str) -> str:
    """
    Retourne un message d'erreur clair indiquant
    le range valide pour une catégorie.

    Args:
        numero_categorie: Numéro de la catégorie

    Returns:
        Message d'erreur formaté
    """
    # Étape 5.1 — Calculer le range
    range_valide = calculer_range_note(numero_categorie)
    if not range_valide:
        return (
            f"Le numéro de catégorie '{numero_categorie}' "
            "n'est pas dans un format Revit valide."
        )

    # Étape 5.2 — Formater le range avec padding
    prefixe  = range_valide["prefixe"]
    min_val  = range_valide["min"]
    max_val  = range_valide["max"]
    longueur = len(str(range_valide["base"] + range_valide["max"] - range_valide["base"]))

    min_formate = f"{prefixe}{str(min_val).zfill(longueur)}"
    max_formate = f"{prefixe}{str(max_val).zfill(longueur)}"

    return (
        f"Le numéro de note doit être compris entre "
        f"'{min_formate}' et '{max_formate}' "
        f"pour la catégorie '{numero_categorie}'."
    )
