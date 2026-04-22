// src/pages/Keynotes.tsx
//
// Composant de gestion des keynotes Revit.
// Architecture : état géré exclusivement par useState → React re-rend le JSX automatiquement.
// Aucune manipulation directe du DOM (pas de innerHTML, pas de ref sur les inputs,
// pas de window.* global, pas de addEventListener manuel).
//
// Structure des données :
//   Projet (sélectionné dans le select)
//     └─ Catégorie (collapsible dans le tableau)
//          └─ Note (collapsible dans le tableau)

import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Header       from '../components/Header';
import { projetsService, categoriesService, notesService } from '../api/api';

// ============================================================
// SECTION 1 — TYPES
// ============================================================

// Projet tel que retourné par GET /projets
interface Projet {
  id: number;
  nom: string;
  chemin_export: string | null;
  date_creation: string;
}

// Catégorie telle que retournée par GET /projets/{id}/categories
interface Categorie {
  id: number;
  id_projet: number;
  numero: string;
  description: string; // L'API appelle ce champ "description" (pas "titre")
  version: number;
  nombre_notes: number; // Retourné par lister_categories_du_projet (COUNT des notes)
}

// Note telle que retournée par GET /projets/{id}/categories/{id}/notes
interface Note {
  id: number;
  id_projet: number;
  id_categorie: number;
  numero: string;
  description: string;
  version: number;
}

// État de collapse pour le tableau arborescent — stocké séparément des données API
interface EtatCollapse {
  projetsCollapsed: Record<number, boolean>;   // true = fermé, false = ouvert
  categoriesCollapsed: Record<number, boolean>;
}

// Type de l'élément actuellement sélectionné dans le formulaire
type TypeSelection = 'aucun' | 'categorie' | 'note';

// Mode du formulaire pour la catégorie et la note
type ModeFormulaire = 'creation' | 'lecture' | 'edition';

// Formulaire catégorie (champs contrôlés)
interface EtatFormCategorie {
  numero: string;
  description: string;
}

// Formulaire note (champs contrôlés)
interface EtatFormNote {
  idCategorie: number | null;
  numero: string;
  description: string;
}

const FORM_CATEGORIE_VIDE: EtatFormCategorie = { numero: '', description: '' };
const FORM_NOTE_VIDE: EtatFormNote = { idCategorie: null, numero: '', description: '' };

// Type de recherche dans le champ recherche
type TypeRecherche = 'note' | 'categorie';

// ============================================================
// SECTION 2 — FONCTIONS UTILITAIRES PURES (hors composant)
// ============================================================

function normaliserChaine(texte: string): string {
  return texte
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[œ]/g, 'oe')
    .replace(/[æ]/g, 'ae');
}

// Trie numériquement (1, 2, 10 au lieu de 1, 10, 2)
function trierParNumero<T extends { numero: string }>(liste: T[]): T[] {
  return [...liste].sort((a, b) => {
    const numA = parseFloat(a.numero) || 0;
    const numB = parseFloat(b.numero) || 0;
    return numA !== numB ? numA - numB : a.numero.localeCompare(b.numero);
  });
}

// ============================================================
// SECTION 2B — LOGIQUE NUMÉROTATION REVIT
//
// Catégories valides :
//   Multiples de 10  (000-090) : 000, 010, 020... 090
//   Multiples de 100 (≥100)   : 100, 200, 300...
//   Avec préfixe D             : D000, D020, D100, D200...
//
// Notes — range selon la catégorie parente :
//   Catégorie multiple de 10  → +1 à +9  (ex: 020 → 021-029)
//   Catégorie multiple de 100 → +1 à +99 (ex: 200 → 201-299)
//   Même logique avec préfixe D
// ============================================================

/**
 * Calcule le range valide pour les notes d'une catégorie.
 * Retourne { prefixe, base, min, max } ou null si invalide.
 *
 * Ex: "020"  → { prefixe: "",  base: 20,  min: 21,  max: 29  }
 * Ex: "100"  → { prefixe: "",  base: 100, min: 101, max: 199 }
 * Ex: "D020" → { prefixe: "D", base: 20,  min: 21,  max: 29  }
 * Ex: "D200" → { prefixe: "D", base: 200, min: 201, max: 299 }
 */
function calculerRangeNote(numeroCategorie: string): {
  prefixe : string;
  base    : number;
  min     : number;
  max     : number;
} | null {
  const numeroBrut = numeroCategorie.trim().toUpperCase();

  // Extraire préfixe "D" ou "" et partie numérique
  const match = numeroBrut.match(/^(D?)(\d+)$/);
  if (!match) return null;

  const prefixe = match[1];
  const base    = parseInt(match[2], 10);

  // Catégorie multiple de 10 entre 0 et 90 → range +1 à +9
  if (base >= 0 && base <= 90 && base % 10 === 0) {
    return { prefixe, base, min: base + 1, max: base + 9 };
  }

  // Catégorie multiple de 100 à partir de 100 → range +1 à +99
  if (base >= 100 && base % 100 === 0) {
    return { prefixe, base, min: base + 1, max: base + 99 };
  }

  return null;
}

/**
 * Vérifie si un numéro de note respecte le range de sa catégorie.
 */
function validerNumeroNote(
  numeroNote      : string,
  numeroCategorie : string
): boolean {
  const range = calculerRangeNote(numeroCategorie);
  if (!range) return false;

  const numeroBrut = numeroNote.trim().toUpperCase();

  // Vérifier que le préfixe correspond
  if (!numeroBrut.startsWith(range.prefixe)) return false;

  // Extraire et valider la partie numérique
  const partieNumerique = numeroBrut.slice(range.prefixe.length);
  const valeur = parseInt(partieNumerique, 10);
  if (isNaN(valeur)) return false;

  return valeur >= range.min && valeur <= range.max;
}

/**
 * Génère le prochain numéro disponible pour une catégorie.
 * Retourne null si tous les numéros du range sont pris.
 *
 * Ex: catégorie "020", notes ["021","022"] → "023"
 * Ex: catégorie "100", notes ["101","102"] → "103"
 * Ex: catégorie "D200", notes ["D201"]     → "D202"
 */
function genererProchainNumeroNote(
  numeroCategorie  : string,
  numerosExistants : string[]
): string | null {
  const range = calculerRangeNote(numeroCategorie);
  if (!range) return null;

  // Ensemble des numéros déjà pris (en majuscules)
  const numerosExistantsMaj = new Set(
    numerosExistants.map((n) => n.trim().toUpperCase())
  );

  // Longueur du padding basée sur le max du range
  const longueurPadding = String(range.max).length;

  // Trouver le premier numéro disponible dans le range
  for (let valeur = range.min; valeur <= range.max; valeur++) {
    const nombreFormate  = String(valeur).padStart(longueurPadding, '0');
    const numeroCandidat = `${range.prefixe}${nombreFormate}`;
    if (!numerosExistantsMaj.has(numeroCandidat)) {
      return numeroCandidat;
    }
  }

  return null;
}

// ============================================================
// SECTION 3 — SOUS-COMPOSANT : Notification
// ============================================================

interface PropsNotification {
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  onClose: () => void;
}

const Notification: React.FC<PropsNotification> = ({ message, type, onClose }) => {
  useEffect(() => {
    const minuterie = setTimeout(onClose, 3000);
    return () => clearTimeout(minuterie);
  }, [onClose]);

  return <div className={`notification ${type}`}>{message}</div>;
};

// ============================================================
// SECTION 4 — SOUS-COMPOSANT : Champ de recherche avec suggestions
// ============================================================

interface PropsChampRecherche<T> {
  id: string;
  placeholder: string;
  valeur: string;
  suggestions: T[];
  renduSuggestion: (element: T) => React.ReactNode;
  cléSuggestion: (element: T) => string;
  onChangement: (valeur: string) => void;
  onSelectionSuggestion: (element: T) => void;
  onEffacer: () => void;
}

function ChampRecherche<T>({
  id,
  placeholder,
  valeur,
  suggestions,
  renduSuggestion,
  cléSuggestion,
  onChangement,
  onSelectionSuggestion,
  onEffacer,
}: PropsChampRecherche<T>) {
  const [suggestionVisible, setSuggestionVisible] = useState(false);

  useEffect(() => {
    function gererClicExterieur(evenement: MouseEvent) {
      const conteneur = document.getElementById(`conteneur-recherche-${id}`);
      if (conteneur && !conteneur.contains(evenement.target as Node)) {
        setSuggestionVisible(false);
      }
    }
    document.addEventListener('mousedown', gererClicExterieur);
    return () => document.removeEventListener('mousedown', gererClicExterieur);
  }, [id]);

  function gererChangement(e: React.ChangeEvent<HTMLInputElement>) {
    const nouvelleValeur = e.target.value;
    onChangement(nouvelleValeur);
    setSuggestionVisible(nouvelleValeur.trim().length >= 2 && suggestions.length > 0);
  }

  useEffect(() => {
    setSuggestionVisible(valeur.trim().length >= 2 && suggestions.length > 0);
  }, [suggestions, valeur]);

  return (
    <div id={`conteneur-recherche-${id}`} className="suggestions-container">
      <div className="search-wrapper">
        <input
          type="text"
          id={id}
          className="search-input"
          placeholder={placeholder}
          value={valeur}
          onChange={gererChangement}
          autoComplete="off"
        />
        {valeur.trim().length > 0 && (
          <button className="clear-search visible" type="button" onClick={onEffacer}>
            ✖
          </button>
        )}
      </div>

      {suggestionVisible && suggestions.length > 0 && (
        <div className="suggestions" style={{ display: 'block' }}>
          {suggestions.map((element) => (
            <div
              key={cléSuggestion(element)}
              className="suggestion-item"
              onMouseDown={(e) => {
                e.preventDefault();
                onSelectionSuggestion(element);
                setSuggestionVisible(false);
              }}
            >
              {renduSuggestion(element)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================
// SECTION 5 — COMPOSANT PRINCIPAL
// ============================================================

const Keynotes: React.FC = () => {
  const navigate = useNavigate();

  // --- Données chargées depuis l'API ---
  const [projets, setProjets] = useState<Projet[]>([]);
  const [categories, setCategories] = useState<Categorie[]>([]);
  // Notes indexées par id_categorie pour un accès rapide
  const [notesParCategorie, setNotesParCategorie] = useState<Record<number, Note[]>>({});

  const [isLoading, setIsLoading] = useState(true);
  const [isChargementCategories, setIsChargementCategories] = useState(false);

  // --- Projet sélectionné dans le select ---
  const [idProjetSelectionne, setIdProjetSelectionne] = useState<number | null>(null);

  // --- État de collapse du tableau arborescent ---
  const [etatCollapse, setEtatCollapse] = useState<EtatCollapse>({
    projetsCollapsed: {},
    categoriesCollapsed: {},
  });

  // --- Sélection courante (catégorie OU note, jamais les deux) ---
  const [typeSelection, setTypeSelection] = useState<TypeSelection>('aucun');
  const [categorieSelectionnee, setCategorieSelectionnee] = useState<Categorie | null>(null);
  const [noteSelectionnee, setNoteSelectionnee] = useState<Note | null>(null);

  // --- Formulaires ---
  const [modeCategorie, setModeCategorie] = useState<ModeFormulaire>('creation');
  const [modeNote, setModeNote] = useState<ModeFormulaire>('creation');
  const [formCategorie, setFormCategorie] = useState<EtatFormCategorie>(FORM_CATEGORIE_VIDE);
  const [formNote, setFormNote] = useState<EtatFormNote>(FORM_NOTE_VIDE);

  // --- Recherche ---
  const [typeRecherche, setTypeRecherche] = useState<TypeRecherche>('note');
  const [texteRecherche, setTexteRecherche] = useState('');

  // --- Notifications ---
  // --- État de la modale d'import ---
  const [modeImportEnCours, setModeImportEnCours] = useState<{
    nomFichier: string;
    resolve   : (mode: 'remplacer' | 'fusionner' | null) => void;
  } | null>(null);

  const [notification, setNotification] = useState<{
    message: string;
    type: 'success' | 'error' | 'warning' | 'info';
    cle: number;
  } | null>(null);

  // ============================================================
  // SECTION 6 — DONNÉES DÉRIVÉES
  // ============================================================

  // Projets filtrés pour le tableau — si un projet est sélectionné, on n'affiche que lui
  // Tous les projets sont toujours affichés dans le tableau
  // La sélection dans le formulaire n'affecte pas la visibilité
  const projetsPourTableau = projets;

  // Suggestions de recherche — catégories ou notes selon le type sélectionné
  const suggestionsCategorieRecherche: Categorie[] =
    typeRecherche === 'categorie' && texteRecherche.trim().length >= 2
      ? categories
          .filter(
            (c) =>
              (!idProjetSelectionne || c.id_projet === idProjetSelectionne) &&
              (normaliserChaine(c.numero).includes(normaliserChaine(texteRecherche)) ||
                normaliserChaine(c.description).includes(normaliserChaine(texteRecherche)))
          )
          .slice(0, 10)
      : [];

  const suggestionsNoteRecherche: Note[] =
    typeRecherche === 'note' && texteRecherche.trim().length >= 2
      ? Object.values(notesParCategorie)
          .flat()
          .filter(
            (n) =>
              (!idProjetSelectionne || n.id_projet === idProjetSelectionne) &&
              (normaliserChaine(n.numero).includes(normaliserChaine(texteRecherche)) ||
                normaliserChaine(n.description).includes(normaliserChaine(texteRecherche)))
          )
          .slice(0, 10)
      : [];

  // Détermine si les champs catégorie sont modifiables
  const categorieEstModifiable = modeCategorie === 'creation' || modeCategorie === 'edition';

  // Détermine si les champs note sont modifiables
  const noteEstModifiable = modeNote === 'creation' || modeNote === 'edition';

  // Détermine si le bouton "Annuler" est actif
  // Actif dès qu'un projet, une catégorie ou une note est sélectionné
  const annulerEstActif = idProjetSelectionne !== null || typeSelection !== 'aucun';

  // ============================================================
  // SECTION 7 — NOTIFICATIONS
  // ============================================================

  function afficherNotification(
    message: string,
    type: 'success' | 'error' | 'warning' | 'info' = 'success'
  ) {
    setNotification({ message, type, cle: Date.now() });
  }

  // ============================================================
  // SECTION 8 — CHARGEMENT DES DONNÉES DEPUIS L'API
  // ============================================================

  const chargerProjets = useCallback(async () => {
    try {
      const reponse = await projetsService.getAll();
      setProjets(reponse.data);
      // Initialise l'état collapse : tous les projets fermés
      const collapsed: Record<number, boolean> = {};
      reponse.data.forEach((p: Projet) => { collapsed[p.id] = true; });
      setEtatCollapse((prev) => ({ ...prev, projetsCollapsed: collapsed }));
    } catch (erreur) {
      console.error('Erreur chargement projets:', erreur);
      afficherNotification('Erreur lors du chargement des projets', 'error');
    }
  }, []);

  // Charge les catégories d'un projet et toutes leurs notes
  const chargerCategoriesEtNotes = useCallback(async (idProjet: number) => {
    setIsChargementCategories(true);
    try {
      // Étape 1 — Charge les catégories du projet
      const reponseCat = await categoriesService.getAll(idProjet);
      const nouvellesCategories: Categorie[] = reponseCat.data;

      // Met à jour les catégories en remplaçant celles du projet sélectionné
      setCategories((prev) => {
        const autresProjets = prev.filter((c) => c.id_projet !== idProjet);
        return [...autresProjets, ...nouvellesCategories];
      });

      // Initialise l'état collapse pour les nouvelles catégories
      setEtatCollapse((prev) => {
        const newCatCollapsed = { ...prev.categoriesCollapsed };
        nouvellesCategories.forEach((c) => { newCatCollapsed[c.id] = true; });
        return { ...prev, categoriesCollapsed: newCatCollapsed };
      });

      // Étape 2 — Charge les notes pour chaque catégorie
      const notesChargees: Record<number, Note[]> = {};
      await Promise.all(
        nouvellesCategories.map(async (categorie) => {
          try {
            const reponseNotes = await notesService.getAll(idProjet, categorie.id);
            notesChargees[categorie.id] = reponseNotes.data;
          } catch {
            notesChargees[categorie.id] = [];
          }
        })
      );

      setNotesParCategorie((prev) => {
        // Supprime les notes des catégories de l'ancien projet
        const notesAutresProjets: Record<number, Note[]> = {};
        Object.entries(prev).forEach(([idCat, notes]) => {
          if (!nouvellesCategories.some((c) => c.id === Number(idCat))) {
            notesAutresProjets[Number(idCat)] = notes;
          }
        });
        return { ...notesAutresProjets, ...notesChargees };
      });

    } catch (erreur) {
      console.error('Erreur chargement catégories/notes:', erreur);
      afficherNotification('Erreur lors du chargement des catégories', 'error');
    } finally {
      setIsChargementCategories(false);
    }
  }, []);

  // ============================================================
  // SECTION 9 — INITIALISATION AU MONTAGE
  // ============================================================

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/connexion');
      return;
    }
    async function initialiser() {
      setIsLoading(true);
      await chargerProjets();
      setIsLoading(false);
    }
    initialiser();
  }, [navigate, chargerProjets]);

  // ============================================================
  // SECTION 10 — CHANGEMENT DE PROJET SÉLECTIONNÉ
  // ============================================================

  async function changerProjet(idProjet: number | null) {
    setIdProjetSelectionne(idProjet);
    reinitialiserFormulaires();

    if (idProjet === null) return;

    // Charge les catégories et notes du projet sélectionné
    await chargerCategoriesEtNotes(idProjet);
  }

  // ============================================================
  // SECTION 11 — TOGGLE COLLAPSE TABLEAU
  // ============================================================

  async function toggleProjet(idProjet: number) {
    const estDejaSelectionne = idProjetSelectionne === idProjet;

    // Ouvrir/fermer le projet dans le tableau
    setEtatCollapse((prev) => ({
      ...prev,
      projetsCollapsed: {
        ...prev.projetsCollapsed,
        [idProjet]: !prev.projetsCollapsed[idProjet],
      },
    }));

    // Sélectionner le projet dans le formulaire si pas déjà sélectionné
    if (!estDejaSelectionne) {
      await changerProjet(idProjet);
    }
  }

  function toggleCategorie(idCategorie: number) {
    setEtatCollapse((prev) => {
      // Fermer toutes les catégories, puis ouvrir/fermer celle cliquée
      const nouvellesCategoriesCollapsed = { ...prev.categoriesCollapsed };
      Object.keys(nouvellesCategoriesCollapsed).forEach((k) => {
        nouvellesCategoriesCollapsed[Number(k)] = true;
      });
      nouvellesCategoriesCollapsed[idCategorie] = !prev.categoriesCollapsed[idCategorie];
      return { ...prev, categoriesCollapsed: nouvellesCategoriesCollapsed };
    });
  }

  // ============================================================
  // SECTION 12 — RÉINITIALISATION DES FORMULAIRES
  // ============================================================

  function reinitialiserFormulaires() {
    setTypeSelection('aucun');
    setCategorieSelectionnee(null);
    setNoteSelectionnee(null);
    setModeCategorie('creation');
    setModeNote('creation');
    setFormCategorie(FORM_CATEGORIE_VIDE);
    setFormNote(FORM_NOTE_VIDE);
    setTexteRecherche('');
  }

  // ============================================================
  // SECTION 13 — SÉLECTION CATÉGORIE (depuis suggestion ou tableau)
  // ============================================================

  function selectionnerCategorie(categorie: Categorie) {
    // Toujours mettre à jour le projet sélectionné
    setIdProjetSelectionne(categorie.id_projet);
    const categoriesDejaChargees = categories.some(
      (c) => c.id_projet === categorie.id_projet
    );
    if (!categoriesDejaChargees) {
      chargerCategoriesEtNotes(categorie.id_projet);
    }

    setTypeSelection('categorie');
    setCategorieSelectionnee(categorie);
    setNoteSelectionnee(null);
    setModeCategorie('lecture');
    setModeNote('creation');
    setFormCategorie({ numero: categorie.numero, description: categorie.description });

    // Générer automatiquement le prochain numéro de note disponible
    // pour cette catégorie selon le format Revit
    const notesCategorie = notesParCategorie[categorie.id] ?? [];
    const numerosExistants = notesCategorie.map((n) => n.numero);
    const prochainNumero = genererProchainNumeroNote(
      categorie.numero,
      numerosExistants
    );
    setFormNote({
      ...FORM_NOTE_VIDE,
      idCategorie: categorie.id,
      numero: prochainNumero ?? '',
    });

    setTexteRecherche(`${categorie.numero} — ${categorie.description}`);
    setTypeRecherche('categorie');

    // Ouvre la catégorie dans le tableau
    setEtatCollapse((prev) => ({
      ...prev,
      projetsCollapsed: { ...prev.projetsCollapsed, [categorie.id_projet]: false },
      categoriesCollapsed: { ...prev.categoriesCollapsed, [categorie.id]: false },
    }));

    afficherNotification(
      `Catégorie "${categorie.numero} — ${categorie.description}" sélectionnée`,
      'info'
    );
  }

  // ============================================================
  // SECTION 14 — SÉLECTION NOTE (depuis suggestion ou tableau)
  // ============================================================

  function selectionnerNote(note: Note) {
    // Toujours mettre à jour le projet sélectionné
    setIdProjetSelectionne(note.id_projet);
    const categoriesDejaChargees = categories.some(
      (c) => c.id_projet === note.id_projet
    );
    if (!categoriesDejaChargees) {
      chargerCategoriesEtNotes(note.id_projet);
    }

    // Charger la catégorie parente de la note dans le formulaire Catégorie
    const categorieParente = categories.find((c) => c.id === note.id_categorie) ?? null;

    setTypeSelection('note');
    setNoteSelectionnee(note);
    setCategorieSelectionnee(categorieParente);
    setModeNote('lecture');
    setModeCategorie('lecture');
    setFormNote({
      idCategorie: note.id_categorie,
      numero: note.numero,
      description: note.description,
    });
    setFormCategorie(
      categorieParente
        ? { numero: categorieParente.numero, description: categorieParente.description }
        : FORM_CATEGORIE_VIDE
    );
    setTexteRecherche(
      `${note.numero} — ${note.description.substring(0, 50)}${note.description.length > 50 ? '...' : ''}`
    );
    setTypeRecherche('note');

    // Ouvre le projet et la catégorie de la note dans le tableau
    setEtatCollapse((prev) => ({
      ...prev,
      projetsCollapsed: { ...prev.projetsCollapsed, [note.id_projet]: false },
      categoriesCollapsed: { ...prev.categoriesCollapsed, [note.id_categorie]: false },
    }));

    afficherNotification(`Note "${note.numero}" sélectionnée`, 'info');
  }

  // ============================================================
  // SECTION 15 — ACTIONS MODIFIER / ANNULER
  // ============================================================

  function activerEditionCategorie() {
    if (typeSelection !== 'categorie' || !categorieSelectionnee) {
      afficherNotification('Veuillez d\'abord sélectionner une catégorie', 'warning');
      return;
    }
    setModeCategorie('edition');
    afficherNotification('Mode édition catégorie activé', 'warning');
  }

  function activerEditionNote() {
    if (typeSelection !== 'note' || !noteSelectionnee) {
      afficherNotification('Veuillez d\'abord sélectionner une note', 'warning');
      return;
    }
    setModeNote('edition');
    afficherNotification('Mode édition note activé', 'warning');
  }

  function handleModifier() {
    if (typeSelection === 'categorie') activerEditionCategorie();
    else if (typeSelection === 'note') activerEditionNote();
    else afficherNotification('Veuillez d\'abord sélectionner une catégorie ou une note', 'warning');
  }

  function annuler() {
    if (modeCategorie === 'edition' && categorieSelectionnee) {
      // Restaure les valeurs originales de la catégorie
      setFormCategorie({ numero: categorieSelectionnee.numero, description: categorieSelectionnee.description });
      setModeCategorie('lecture');
      afficherNotification('Modifications annulées', 'warning');
    } else if (modeNote === 'edition' && noteSelectionnee) {
      // Restaure les valeurs originales de la note
      setFormNote({
        idCategorie: noteSelectionnee.id_categorie,
        numero: noteSelectionnee.numero,
        description: noteSelectionnee.description,
      });
      setModeNote('lecture');
      afficherNotification('Modifications annulées', 'warning');
    } else {
      // Réinitialiser tout — vider toutes les cellules et fermer dans le tableau
      const idProjet    = idProjetSelectionne;
      const idCategorie = categorieSelectionnee?.id ?? noteSelectionnee?.id_categorie;

      setIdProjetSelectionne(null);
      reinitialiserFormulaires();

      setEtatCollapse((prev) => {
        const newCollapse = { ...prev };

        if (typeSelection === 'aucun' && idProjet) {
          // Seulement un projet sélectionné → fermer le projet
          newCollapse.projetsCollapsed = {
            ...prev.projetsCollapsed,
            [idProjet]: true,
          };
        } else if (idCategorie) {
          // Catégorie ou note sélectionnée → fermer uniquement la catégorie
          newCollapse.categoriesCollapsed = {
            ...prev.categoriesCollapsed,
            [idCategorie]: true,
          };
        }

        return newCollapse;
      });

      afficherNotification('Sélection annulée', 'info');
    }
  }

  // ============================================================
  // SECTION 16 — ENREGISTREMENT (catégorie ou note selon le contexte)
  // ============================================================

  async function handleEnregistrer() {
    // Priorité 1 — mode édition catégorie
    if (modeCategorie === 'edition') {
      await enregistrerCategorie();
      return;
    }
    // Priorité 2 — mode édition note
    if (modeNote === 'edition') {
      await enregistrerNote();
      return;
    }
    // Priorité 3 — création note si une catégorie est sélectionnée
    if (typeSelection === 'categorie' && categorieSelectionnee) {
      await enregistrerNote();
      return;
    }
    // Priorité 4 — création catégorie si le formulaire catégorie est rempli
    if (formCategorie.numero.trim() !== '' || formCategorie.description.trim() !== '') {
      await enregistrerCategorie();
      return;
    }
    afficherNotification(
      'Veuillez sélectionner une catégorie ou remplir le formulaire',
      'warning'
    );
  }

  // --- Catégorie ---
  async function enregistrerCategorie() {
    if (!idProjetSelectionne) {
      afficherNotification('Veuillez d\'abord sélectionner un projet', 'warning');
      return;
    }
    if (!formCategorie.numero.trim()) {
      afficherNotification('Le numéro de la catégorie est obligatoire', 'error');
      return;
    }
    if (!formCategorie.description.trim()) {
      afficherNotification('La description de la catégorie est obligatoire', 'error');
      return;
    }

    // --- CAS 1 : MODIFICATION ---
    if (modeCategorie === 'edition' && categorieSelectionnee) {
      try {
        await categoriesService.update(idProjetSelectionne, categorieSelectionnee.id, {
          version_actuelle: categorieSelectionnee.version,
          nouveau_numero: formCategorie.numero.trim(),
          nouvelle_desc: formCategorie.description.trim(),
        });
        afficherNotification(
          `Catégorie "${formCategorie.numero} — ${formCategorie.description}" mise à jour`,
          'success'
        );
        await chargerCategoriesEtNotes(idProjetSelectionne);
        reinitialiserFormulaires();
      } catch (erreur: any) {
        console.error('Erreur modification catégorie:', erreur);
        const messageApi = erreur?.response?.data?.detail || 'Erreur lors de la modification';
        afficherNotification(messageApi, 'error');
      }
      return;
    }

    // --- CAS 2 : CRÉATION ---
    // Vérifier les doublons en mémoire avant d'envoyer au backend
    const numeroNorm      = normaliserChaine(formCategorie.numero.trim());
    const descriptionNorm = normaliserChaine(formCategorie.description.trim());
    const doublon = categories
      .filter((c) => c.id_projet === idProjetSelectionne)
      .find(
        (c) =>
          normaliserChaine(c.numero)      === numeroNorm ||
          normaliserChaine(c.description) === descriptionNorm
      );
    if (doublon) {
      afficherNotification(
        `Doublon détecté — le numéro ou le titre existe déjà : "${doublon.numero} — ${doublon.description}"`,
        'error'
      );
      return;
    }
    try {
      await categoriesService.create(idProjetSelectionne, {
        numero: formCategorie.numero.trim(),
        description: formCategorie.description.trim(),
      });
      afficherNotification(
        `Catégorie "${formCategorie.numero} — ${formCategorie.description}" créée`,
        'success'
      );
      await chargerCategoriesEtNotes(idProjetSelectionne);
      setFormCategorie(FORM_CATEGORIE_VIDE);
    } catch (erreur: any) {
      console.error('Erreur création catégorie:', erreur);
      const messageApi = erreur?.response?.data?.detail || 'Erreur lors de la création';
      afficherNotification(messageApi, 'error');
    }
  }

  // --- Note ---
  async function enregistrerNote() {
    if (!idProjetSelectionne) {
      afficherNotification('Veuillez d\'abord sélectionner un projet', 'warning');
      return;
    }
    if (!formNote.idCategorie) {
      afficherNotification('Veuillez sélectionner une catégorie pour la note', 'error');
      return;
    }
    if (!formNote.numero.trim()) {
      afficherNotification('Le numéro de la note est obligatoire', 'error');
      return;
    }

    // Valider que le numéro respecte le format Revit de la catégorie
    const categorieNote = categories.find((c) => c.id === formNote.idCategorie);
    if (categorieNote) {
      const numeroValide = validerNumeroNote(
        formNote.numero.trim(),
        categorieNote.numero
      );
      if (!numeroValide) {
        const range = calculerRangeNote(categorieNote.numero);
        const rangeTexte = range
          ? `${range.prefixe}${String(range.min).padStart(String(range.base + 99).length, '0')} à ${range.prefixe}${String(range.max).padStart(String(range.base + 99).length, '0')}`
          : 'invalide';
        afficherNotification(
          `Numéro invalide. Pour la catégorie "${categorieNote.numero}", le range valide est : ${rangeTexte}`,
          'error'
        );
        return;
      }
    }

    if (!formNote.description.trim()) {
      afficherNotification('La description de la note est obligatoire', 'error');
      return;
    }

    // --- CAS 1 : MODIFICATION ---
    if (modeNote === 'edition' && noteSelectionnee) {
      try {
        await notesService.update(idProjetSelectionne, noteSelectionnee.id, {
          version_actuelle: noteSelectionnee.version,
          nouveau_numero: formNote.numero.trim(),
          nouvelle_desc: formNote.description.trim(),
        });
        afficherNotification(`Note "${formNote.numero}" mise à jour`, 'success');
        await chargerCategoriesEtNotes(idProjetSelectionne);
        reinitialiserFormulaires();
      } catch (erreur: any) {
        console.error('Erreur modification note:', erreur);
        const messageApi = erreur?.response?.data?.detail || 'Erreur lors de la modification';
        afficherNotification(messageApi, 'error');
      }
      return;
    }

    // --- CAS 2 : CRÉATION ---
    // Vérifier les doublons en mémoire avant d'envoyer au backend
    const noteNumeroNorm = normaliserChaine(formNote.numero.trim());
    const noteDescNorm   = normaliserChaine(formNote.description.trim());
    const toutesLesNotes = Object.values(notesParCategorie).flat();
    const doublonNote = toutesLesNotes
      .filter((n) => n.id_projet === idProjetSelectionne)
      .find(
        (n) =>
          normaliserChaine(n.numero)      === noteNumeroNorm ||
          normaliserChaine(n.description) === noteDescNorm
      );
    if (doublonNote) {
      afficherNotification(
        `Doublon détecté — le numéro ou la description existe déjà : "${doublonNote.numero} — ${doublonNote.description.substring(0, 60)}..."`,
        'error'
      );
      return;
    }
    try {
      await notesService.create(idProjetSelectionne, formNote.idCategorie, {
        numero: formNote.numero.trim(),
        description: formNote.description.trim(),
      });
      afficherNotification(`Note "${formNote.numero}" créée`, 'success');
      await chargerCategoriesEtNotes(idProjetSelectionne);
      setFormNote(FORM_NOTE_VIDE);
    } catch (erreur: any) {
      console.error('Erreur création note:', erreur);
      const messageApi = erreur?.response?.data?.detail || 'Erreur lors de la création';
      afficherNotification(messageApi, 'error');
    }
  }

  // ============================================================
  // SECTION 17 — SUPPRESSION
  // ============================================================

  async function handleSupprimer() {
    if (typeSelection === 'categorie') await supprimerCategorie();
    else if (typeSelection === 'note') await supprimerNote();
    else afficherNotification('Veuillez d\'abord sélectionner une catégorie ou une note', 'warning');
  }

  async function supprimerCategorie() {
    if (!categorieSelectionnee || !idProjetSelectionne) return;

    // Vérifie qu'il n'y a plus de notes dans cette catégorie.
    // On utilise nombre_notes retourné directement par l'API (plus fiable que le count local).
    // Fallback sur le count local si nombre_notes n'est pas encore chargé.
    const nombreNotesApi = categorieSelectionnee.nombre_notes;
    const nombreNotesLocal = (notesParCategorie[categorieSelectionnee.id] ?? []).length;
    const nombreNotes = nombreNotesApi ?? nombreNotesLocal;

    if (nombreNotes > 0) {
      afficherNotification(
        `Impossible de supprimer "${categorieSelectionnee.numero} — ${categorieSelectionnee.description}" — supprimez d'abord ses ${nombreNotes} note(s).`,
        'error'
      );
      return;
    }

    const confirmation = window.confirm(
      `Êtes-vous sûr de vouloir supprimer la catégorie "${categorieSelectionnee.numero} — ${categorieSelectionnee.description}" ?\n\nCette action est irréversible.`
    );
    if (!confirmation) return;

    const labelSauvegarde = `${categorieSelectionnee.numero} — ${categorieSelectionnee.description}`;

    try {
      await categoriesService.delete(idProjetSelectionne, categorieSelectionnee.id);
      afficherNotification(`Catégorie "${labelSauvegarde}" supprimée`, 'success');
      await chargerCategoriesEtNotes(idProjetSelectionne);
      reinitialiserFormulaires();
    } catch (erreur: any) {
      console.error('Erreur suppression catégorie:', erreur);
      const messageApi = erreur?.response?.data?.detail || 'Erreur lors de la suppression';
      afficherNotification(messageApi, 'error');
    }
  }

  async function supprimerNote() {
    if (!noteSelectionnee || !idProjetSelectionne) return;

    const apercu =
      noteSelectionnee.description.length > 50
        ? noteSelectionnee.description.substring(0, 50) + '...'
        : noteSelectionnee.description;

    const confirmation = window.confirm(
      `Êtes-vous sûr de vouloir supprimer la note "${noteSelectionnee.numero} — ${apercu}" ?\n\nCette action est irréversible.`
    );
    if (!confirmation) return;

    const numeroSauvegarde = noteSelectionnee.numero;

    try {
      await notesService.delete(idProjetSelectionne, noteSelectionnee.id);
      afficherNotification(`Note "${numeroSauvegarde}" supprimée`, 'success');
      await chargerCategoriesEtNotes(idProjetSelectionne);
      reinitialiserFormulaires();
    } catch (erreur: any) {
      console.error('Erreur suppression note:', erreur);
      const messageApi = erreur?.response?.data?.detail || 'Erreur lors de la suppression';
      afficherNotification(messageApi, 'error');
    }
  }

  // ============================================================
  // SECTION 18 — EXPORT / IMPORT
  // ============================================================

  async function exporterProjet() {
    if (!idProjetSelectionne) {
      afficherNotification('Veuillez d\'abord sélectionner un projet', 'warning');
      return;
    }
    try {
      const projetActuel = projets.find((p) => p.id === idProjetSelectionne);
      const nomProjet    = projetActuel?.nom ?? 'projet';

      // Afficher le chemin cible si défini — aide l'utilisateur
      // à naviguer vers le bon dossier dans la fenêtre Windows
      if (projetActuel?.chemin_export) {
        afficherNotification(
          `Naviguez vers : ${projetActuel.chemin_export}`,
          'info'
        );
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }

      // Retourne false si l'utilisateur a annulé la fenêtre
      const succes = await projetsService.exporter(idProjetSelectionne, nomProjet);
      if (!succes) return; // Annulation — pas de notification
      afficherNotification('Exportation !', 'success');
    } catch (erreur) {
      console.error('Erreur export:', erreur);
      afficherNotification("Erreur lors de l'export", 'error');
    }
  }

  // Ouvre la fenêtre de sélection de fichier et lance l'import
  async function importerProjet() {
    if (!idProjetSelectionne) {
      afficherNotification("Veuillez d'abord sélectionner un projet", 'warning');
      return;
    }

    // Étape 1 — Ouvrir la fenêtre de sélection de fichier
    const input = document.createElement('input');
    input.type   = 'file';
    input.accept = '.txt';

    input.onchange = async (evenement) => {
      const fichier = (evenement.target as HTMLInputElement).files?.[0];
      if (!fichier) return;

      // Étape 2 — Valider le fichier
      if (!fichier.name.endsWith('.txt')) {
        afficherNotification('Le fichier doit être au format .txt', 'error');
        return;
      }
      if (fichier.size > 5 * 1024 * 1024) {
        afficherNotification('Le fichier dépasse la taille maximale (5 MB)', 'error');
        return;
      }

      // Étape 3 — Choisir le mode d'import
      const modeChoisi = await choisirModeImport(fichier.name);
      if (!modeChoisi) return; // Annulation

      // Étape 4 — Lire et envoyer le fichier
      try {
        const contenuTxt = await lireFichierTexte(fichier);
        await projetsService.importer(idProjetSelectionne, {
          mode        : modeChoisi,
          contenu_txt : contenuTxt,
        });
        afficherNotification(
          `Import (${modeChoisi}) réussi`,
          'success'
        );
        // Recharger les catégories et notes
        await chargerCategoriesEtNotes(idProjetSelectionne);
        // Ouvrir le projet dans le tableau pour afficher les données
        setEtatCollapse((prev) => ({
          ...prev,
          projetsCollapsed: {
            ...prev.projetsCollapsed,
            [idProjetSelectionne]: false,
          },
        }));
      } catch (erreur: any) {
        console.error('Erreur import:', erreur);
        const messageApi = erreur?.response?.data?.detail || "Erreur lors de l'import";
        afficherNotification(messageApi, 'error');
      }
    };

    input.click();
  }

  // Affiche la modale de choix du mode d'import
  function choisirModeImport(nomFichier: string): Promise<'remplacer' | 'fusionner' | null> {
    return new Promise((resolve) => {
      setModeImportEnCours({ nomFichier, resolve });
    });
  }

  // Lit un fichier .txt en détectant l'encodage UTF-16 ou UTF-8
  function lireFichierTexte(fichier: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const buffer = e.target?.result as ArrayBuffer;
        const bytes  = new Uint8Array(buffer);
        if (
          (bytes[0] === 0xFF && bytes[1] === 0xFE) ||
          (bytes[0] === 0xFE && bytes[1] === 0xFF)
        ) {
          resolve(new TextDecoder('utf-16').decode(buffer));
        } else {
          try {
            const texte16 = new TextDecoder('utf-16le').decode(buffer);
            resolve(texte16.includes('	') ? texte16 : new TextDecoder('utf-8').decode(buffer));
          } catch {
            resolve(new TextDecoder('utf-8').decode(buffer));
          }
        }
      };
      reader.onerror = () => reject(new Error('Erreur de lecture'));
      reader.readAsArrayBuffer(fichier);
    });
  }

  // ============================================================
  // SECTION 19 — RENDU CONDITIONNEL : CHARGEMENT
  // ============================================================

  if (isLoading) {
    return <div className="container">Chargement...</div>;
  }

  // ============================================================
  // SECTION 20 — RENDU DU TABLEAU ARBORESCENT
  // Le tableau est rendu entièrement en JSX avec .map() imbriqués.
  // Les lignes projet, catégorie et note ont chacune leur style distinct.
  // ============================================================

  function renduTableau(): React.ReactNode {
    return projetsPourTableau.map((projet) => {
      const estProjetOuvert = !etatCollapse.projetsCollapsed[projet.id];
      const categoriesDuProjet = trierParNumero(
        categories.filter((c) => c.id_projet === projet.id)
      );

      return (
        <React.Fragment key={projet.id}>
          {/* LIGNE PROJET */}
          <tr
            className="project-row"
            style={{ cursor: 'pointer' }}
            onClick={() => toggleProjet(projet.id)}
          >
            <td colSpan={2}>
              <span className="project-icon">{estProjetOuvert ? '▼' : '▶'}</span>{' '}
              {projet.nom}
            </td>
          </tr>

          {/* LIGNES CATÉGORIES ET NOTES (si le projet est ouvert) */}
          {estProjetOuvert &&
            categoriesDuProjet.map((categorie) => {
              const estCategorieOuverte = !etatCollapse.categoriesCollapsed[categorie.id];
              const notesDeLaCategorie = trierParNumero(notesParCategorie[categorie.id] ?? []);

              return (
                <React.Fragment key={categorie.id}>
                  {/* LIGNE CATÉGORIE */}
                  <tr
                    className={`category-row ${categorieSelectionnee?.id === categorie.id ? 'row-selected' : ''}`}
                    style={{ cursor: 'pointer' }}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleCategorie(categorie.id);
                      // Si la catégorie est déjà sélectionnée → vider le formulaire
                      // Sinon → la sélectionner et charger ses données
                      if (categorieSelectionnee?.id === categorie.id) {
                        reinitialiserFormulaires();
                      } else {
                        selectionnerCategorie(categorie);
                      }
                    }}
                  >
                    <td colSpan={2}>
                      <span className="category-icon">{estCategorieOuverte ? '▼' : '▶'}</span>{' '}
                      <strong>{categorie.numero}</strong> — {categorie.description}
                      {/* Compteur de notes — affiché entre parenthèses à droite de la description */}
                      <span style={{ marginLeft: '8px', fontSize: '12px', color: '#888', fontWeight: 'normal' }}>
                        ({categorie.nombre_notes ?? notesDeLaCategorie.length} note{(categorie.nombre_notes ?? notesDeLaCategorie.length) !== 1 ? 's' : ''})
                      </span>
                    </td>
                  </tr>

                  {/* LIGNES NOTES (si la catégorie est ouverte) */}
                  {estCategorieOuverte &&
                    notesDeLaCategorie.map((note) => (
                      <tr
                        key={note.id}
                        className={noteSelectionnee?.id === note.id ? 'row-selected' : ''}
                        style={{ cursor: 'pointer' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          // Sélectionne automatiquement le projet si pas encore sélectionné
                          if (idProjetSelectionne !== note.id_projet) {
                            setIdProjetSelectionne(note.id_projet);
                          }
                          selectionnerNote(note);
                        }}
                      >
                        <td>{note.numero}</td>
                        <td className="description-cell">{note.description}</td>
                      </tr>
                    ))}
                </React.Fragment>
              );
            })}
        </React.Fragment>
      );
    });
  }

  // ============================================================
  // SECTION 21 — RENDU PRINCIPAL (JSX)
  // ============================================================

  return (
    <>
      {notification && (
        <Notification
          key={notification.cle}
          message={notification.message}
          type={notification.type}
          onClose={() => setNotification(null)}
        />
      )}

      <div className="container">

        {/* -------------------------------------------------- */}
        {/* SECTION FORMULAIRE                                  */}
        {/* -------------------------------------------------- */}
        <div className="section">
          <Header titre="Keynotes" />
          <div className="grid-5x2">

            {/* CELLULE 1 — Sélecteur de projet */}
            <div className="cell">
              <div className="cell-title">Projet</div>
              <select
                id="projectSelect"
                className="project-select"
                value={idProjetSelectionne ?? ''}
                disabled={typeSelection !== 'aucun'}
                onChange={(e) => {
                  const valeur = e.target.value;
                  changerProjet(valeur === '' ? null : parseInt(valeur));
                }}
              >
                <option value="">— Sélectionner un projet —</option>
                {projets.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nom}
                  </option>
                ))}
              </select>
              {isChargementCategories && (
                <small style={{ color: '#888', marginTop: '4px', display: 'block' }}>
                  Chargement...
                </small>
              )}
            </div>

            {/* CELLULE 2 — Formulaire catégorie */}
            <div className="cell">
              <div className="cell-title">Catégorie</div>
              <div className="input-group">
                <input
                  type="text"
                  id="categorieNumero"
                  className="categorie-numero"
                  placeholder="xxxx"
                  value={formCategorie.numero}
                  readOnly={!categorieEstModifiable}
                  onChange={(e) =>
                    setFormCategorie({ ...formCategorie, numero: e.target.value })
                  }
                />
                <input
                  type="text"
                  id="categorieTitre"
                  className="categorie-titre"
                  placeholder="Saisir votre nouvelle catégorie"
                  value={formCategorie.description}
                  readOnly={!categorieEstModifiable}
                  maxLength={500}
                  onChange={(e) =>
                    setFormCategorie({ ...formCategorie, description: e.target.value })
                  }
                />
              </div>
            </div>

            {/* CELLULE 3+4+5 — Formulaire note */}
            <div className="cell-span-3">
              <div className="cell-title">Note</div>
              <div className="input-group-note">
                <input
                  type="text"
                  id="noteNumero"
                  className="input-number"
                  placeholder="xxx"
                  value={formNote.numero}
                  readOnly={!noteEstModifiable}
                  onChange={(e) => setFormNote({ ...formNote, numero: e.target.value })}
                />

                <textarea
                  id="noteDescription"
                  className="textarea-description"
                  placeholder="Saisir votre nouvelle description"
                  value={formNote.description}
                  readOnly={!noteEstModifiable}
                  maxLength={500}
                  onChange={(e) => setFormNote({ ...formNote, description: e.target.value })}
                />
              </div>
            </div>

            {/* CELLULE 6+7 — Recherche */}
            <div className="cell-span-2">
              <div className="search-row">
                <span className="search-label">Rechercher par :</span>
                <select
                  id="searchTypeSelect"
                  className="search-type-select"
                  value={typeRecherche}
                  onChange={(e) => {
                    setTypeRecherche(e.target.value as TypeRecherche);
                    setTexteRecherche('');
                  }}
                >
                  <option value="note">Note</option>
                  <option value="categorie">Catégorie</option>
                </select>

                <ChampRecherche<Categorie | Note>
                  id="searchInput"
                  placeholder={
                    typeRecherche === 'categorie'
                      ? 'Rechercher une catégorie par numéro ou description...'
                      : 'Rechercher une note par numéro ou description...'
                  }
                  valeur={texteRecherche}
                  suggestions={
                    typeRecherche === 'categorie'
                      ? suggestionsCategorieRecherche
                      : suggestionsNoteRecherche
                  }
                  cléSuggestion={(element) => String(element.id)}
                  renduSuggestion={(element) => {
                    if (typeRecherche === 'categorie') {
                      const cat = element as Categorie;
                      const nomProjet = projets.find((p) => p.id === cat.id_projet)?.nom ?? '';
                      return (
                        <>
                          <strong>{cat.numero}</strong> — {cat.description}
                          <br />
                          <small>📁 {nomProjet}</small>
                        </>
                      );
                    } else {
                      const note = element as Note;
                      const cat = categories.find((c) => c.id === note.id_categorie);
                      const nomProjet = projets.find((p) => p.id === note.id_projet)?.nom ?? '';
                      return (
                        <>
                          <strong>{note.numero}</strong> —{' '}
                          {note.description.substring(0, 80)}
                          {note.description.length > 80 ? '...' : ''}
                          <br />
                          <small>
                            📁 {nomProjet} | 📋 {cat?.numero} — {cat?.description}
                          </small>
                        </>
                      );
                    }
                  }}
                  onChangement={(valeur) => {
                    setTexteRecherche(valeur);
                    if (!idProjetSelectionne && valeur.trim().length >= 2) {
                      afficherNotification(
                        'Veuillez d\'abord sélectionner un projet',
                        'warning'
                      );
                    }
                  }}
                  onSelectionSuggestion={(element) => {
                    if (typeRecherche === 'categorie') {
                      selectionnerCategorie(element as Categorie);
                    } else {
                      selectionnerNote(element as Note);
                    }
                  }}
                  onEffacer={() => {
                    reinitialiserFormulaires();
                    afficherNotification('Recherche effacée', 'info');
                  }}
                />
              </div>
            </div>

            {/* CELLULE 8+9+10 — Boutons d'action */}
            <div className="cell-span-3">
              <div className="button-group">
                <button
                  type="button"
                  className="btn"
                  onClick={importerProjet}
                >
                  Importer
                </button>
                <button
                  type="button"
                  className="btn"
                  disabled={!idProjetSelectionne}
                  onClick={exporterProjet}
                >
                  Exporter
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={handleEnregistrer}
                >
                  Enregistrer
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={handleModifier}
                >
                  Modifier
                </button>
                <button
                  type="button"
                  className="btn-cancel"
                  disabled={!annulerEstActif}
                  onClick={annuler}
                >
                  Annuler
                </button>
                <button
                  type="button"
                  className="btn-delete"
                  onClick={handleSupprimer}
                >
                  Supprimer
                </button>
              </div>
            </div>

          </div>
        </div>

        {/* -------------------------------------------------- */}
        {/* SECTION TABLEAU ARBORESCENT                         */}
        {/* Clic simple → collapse/expand                       */}
        {/* Double-clic sur catégorie/note → sélectionne        */}
        {/* -------------------------------------------------- */}
        <div className="section">
          <table className="data-table" id="dataTable">
            {/* Largeur fixe pour la colonne N° — évite que les numéros longs
                élargissent la colonne et décalent tout le tableau */}
            <colgroup>
              <col style={{ width: '120px', minWidth: '120px' }} />
              <col />
            </colgroup>
            <thead>
              <tr>
                <th style={{ width: '120px' }}>N°</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {renduTableau()}
            </tbody>
          </table>
        </div>

        {/* ─── MODALE CHOIX MODE IMPORT ─── */}
        {modeImportEnCours && (
          <div style={{
            position       : 'fixed',
            top            : 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display        : 'flex',
            alignItems     : 'center',
            justifyContent : 'center',
            zIndex         : 1000,
          }}>
            <div style={{
              backgroundColor: '#fff',
              borderRadius   : '12px',
              padding        : '32px',
              maxWidth       : '480px',
              width          : '90%',
              boxShadow      : '0 8px 32px rgba(0,0,0,0.2)',
            }}>
              <h3 style={{ margin: '0 0 8px', fontSize: '18px', color: '#333' }}>
                Mode d'import
              </h3>
              <p style={{ margin: '0 0 8px', fontSize: '14px', color: '#666' }}>
                Fichier : <strong>{modeImportEnCours.nomFichier}</strong>
              </p>
              <p style={{ margin: '0 0 24px', fontSize: '14px', color: '#666' }}>
                Choisissez comment importer les données dans ce projet :
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
                <div style={{ padding: '16px', border: '1px solid #e0e0e0', borderRadius: '8px' }}>
                  <strong style={{ fontSize: '14px' }}>Remplacer</strong>
                  <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#666' }}>
                    Supprime toutes les catégories et notes existantes, puis importe le fichier.
                  </p>
                </div>
                <div style={{ padding: '16px', border: '1px solid #e0e0e0', borderRadius: '8px' }}>
                  <strong style={{ fontSize: '14px' }}>Fusionner</strong>
                  <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#666' }}>
                    Ajoute uniquement les catégories et notes absentes.
                  </p>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className="cancel-button"
                  onClick={() => {
                    modeImportEnCours.resolve(null);
                    setModeImportEnCours(null);
                  }}
                >
                  Annuler
                </button>
                <button
                  type="button"
                  className="action-button"
                  onClick={() => {
                    modeImportEnCours.resolve('fusionner');
                    setModeImportEnCours(null);
                  }}
                >
                  Fusionner
                </button>
                <button
                  type="button"
                  className="delete-button"
                  onClick={() => {
                    modeImportEnCours.resolve('remplacer');
                    setModeImportEnCours(null);
                  }}
                >
                  Remplacer
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </>
  );
};

export default Keynotes;
