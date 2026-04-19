"""
utils/revit_numerotation.py
---------------------------
Logique de validation et génération des numéros Revit keynotes.

Rôle :
    Valider et générer les numéros de catégories et notes
    selon le format standard Revit keynotes.

Format Revit :
    Catégories : x00 ou Dx00 (ex: 100, 200, D200, D500)
    Notes      : préfixe + numéro entre base+1 et base+99
                 avec padding (ex: 101, 102... D201, D202...)

Cas fixes :
    - Catégorie "000" → notes "001" à "019"
    - Catégorie "020" → notes "021" à "099"

Importation :
    from app.utils.revit_numerotation import (
        valider_numero_categorie,
        valider_numero_note,
        calculer_range_note,
    )
"""

import re
from typing import Optional


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 — RANGES FIXES POUR LES CATÉGORIES SPÉCIALES
# ─────────────────────────────────────────────────────────────

# Catégories "000" et "020" ont des ranges fixes
# qui ne suivent pas la règle générale x00 → x01 à x99
RANGES_FIXES: dict[str, dict] = {
    "000": {"min": 1,  "max": 19},   # notes 001 à 019
    "020": {"min": 21, "max": 99},   # notes 021 à 099
}


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 — VALIDATION DU NUMÉRO DE CATÉGORIE
# ─────────────────────────────────────────────────────────────

def valider_numero_categorie(numero: str) -> bool:
    """
    Vérifie que le numéro respecte le format Revit
    pour une catégorie.

    Format accepté :
        - x00  : numérique multiple de 100 (100, 200, 300...)
        - Dx00 : préfixe D + multiple de 100 (D100, D200...)
        - 000  : cas spécial accepté
        - 020  : cas spécial accepté

    Args:
        numero: Numéro de la catégorie à valider

    Returns:
        True si le format est valide, False sinon
    """
    # Étape 2.1 — Normaliser en majuscules et strip
    numero_normalise = numero.strip().upper()

    # Étape 2.2 — Cas fixes toujours valides
    if numero_normalise in RANGES_FIXES:
        return True

    # Étape 2.3 — Format général : préfixe optionnel + multiple de 100
    # Ex: "100", "200", "D100", "D200", "D500"
    match = re.match(r'^([A-Z]*)(\d+)$', numero_normalise)
    if not match:
        return False

    partie_numerique = int(match.group(2))

    # Le numéro doit être un multiple de 100 (100, 200, 300...)
    return partie_numerique > 0 and partie_numerique % 100 == 0


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
        "100"  → {"prefixe": "",  "base": 100, "min": 101, "max": 199}
        "D200" → {"prefixe": "D", "base": 200, "min": 201, "max": 299}
        "000"  → {"prefixe": "",  "base": 0,   "min": 1,   "max": 19 }
        "020"  → {"prefixe": "",  "base": 20,  "min": 21,  "max": 99 }
    """
    # Étape 3.1 — Normaliser
    numero_normalise = numero_categorie.strip().upper()

    # Étape 3.2 — Cas fixes
    if numero_normalise in RANGES_FIXES:
        base = int(numero_normalise)
        return {
            "prefixe": "",
            "base"   : base,
            "min"    : RANGES_FIXES[numero_normalise]["min"],
            "max"    : RANGES_FIXES[numero_normalise]["max"],
        }

    # Étape 3.3 — Cas général
    match = re.match(r'^([A-Z]*)(\d+)$', numero_normalise)
    if not match:
        return None

    prefixe = match.group(1)   # "D" ou ""
    base    = int(match.group(2))  # 100, 200, etc.

    if base <= 0 or base % 100 != 0:
        return None

    return {
        "prefixe": prefixe,
        "base"   : base,
        "min"    : base + 1,    # 101, 201, etc.
        "max"    : base + 99,   # 199, 299, etc.
    }


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
        valider_numero_note("101", "100") → True
        valider_numero_note("201", "100") → False
        valider_numero_note("D201", "D200") → True
        valider_numero_note("001", "000") → True
        valider_numero_note("020", "000") → False (hors range 001-019)
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
    prefixe   = range_valide["prefixe"]
    min_val   = range_valide["min"]
    max_val   = range_valide["max"]
    longueur  = len(str(range_valide["base"] + 99))

    min_formate = f"{prefixe}{str(min_val).zfill(longueur)}"
    max_formate = f"{prefixe}{str(max_val).zfill(longueur)}"

    return (
        f"Le numéro de note doit être compris entre "
        f"'{min_formate}' et '{max_formate}' "
        f"pour la catégorie '{numero_categorie}'."
    )
