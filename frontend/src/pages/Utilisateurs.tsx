// src/pages/Utilisateurs.tsx
//
// Composant de gestion des utilisateurs.
// Architecture : état géré exclusivement par useState → React re-rend le JSX automatiquement.
// Aucune manipulation directe du DOM (pas de innerHTML, pas de ref sur les inputs).

import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Header       from '../components/Header';
import { utilisateursService, projetsService, accesService } from '../api/api';

// ============================================================
// SECTION 1 — TYPES
// ============================================================

interface Utilisateur {
  id: number;
  nom: string;
  prenom: string;
  email: string;
  role: string;
  statut: string;
  date_creation: string; // Format ISO depuis l'API, ex: "2026-03-28T00:00:00"
  // Note : les projets accessibles ne sont PAS dans UtilisateurReponseModele (GET /utilisateurs).
  // Ils sont dans UtilisateurDetailModele (GET /utilisateurs/{id}).
  // La gestion des accès projets se fait depuis la page Projets.tsx.
}

// Les trois modes possibles pour le formulaire du haut
type ModeFormulaire = 'creation' | 'lecture' | 'edition';

// Structure de l'état du formulaire (champs contrôlés par React)
interface EtatFormulaire {
  nom: string;
  prenom: string;
  email: string;
  role: string;
  statut: string;
}

const ETAT_FORMULAIRE_VIDE: EtatFormulaire = {
  nom: '',
  prenom: '',
  email: '',
  role: '',
  statut: '',
};

// Interface pour les projets chargés depuis l'API
interface ProjetAcces {
  id  : number;
  nom : string;
}

// Ordre de tri pour les rôles et statuts dans le tableau
const ORDRE_ROLE: Record<string, number> = { super_admin: 1, utilisateur: 2 };
const ORDRE_STATUT: Record<string, number> = { en_attente: 1, approuve: 2, refuse: 3 };

// ============================================================
// SECTION 2 — FONCTIONS UTILITAIRES PURES (hors composant)
// Ces fonctions n'ont pas besoin de l'état React — elles restent stables.
// ============================================================

// Normalise une chaîne pour la recherche : minuscules + suppression des accents
function normaliserChaine(texte: string): string {
  return texte
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[œ]/g, 'oe')
    .replace(/[æ]/g, 'ae');
}

// Valide le format d'une adresse email
function validerEmail(email: string): boolean {
  const regexEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return regexEmail.test(email);
}

// Trie les utilisateurs : par rôle, puis par statut, puis par nom alphabétique
function trierUtilisateurs(utilisateurs: Utilisateur[]): Utilisateur[] {
  return [...utilisateurs].sort((a, b) => {
    const comparaisonRole = (ORDRE_ROLE[a.role] ?? 99) - (ORDRE_ROLE[b.role] ?? 99);
    if (comparaisonRole !== 0) return comparaisonRole;

    const comparaisonStatut = (ORDRE_STATUT[a.statut] ?? 99) - (ORDRE_STATUT[b.statut] ?? 99);
    if (comparaisonStatut !== 0) return comparaisonStatut;

    return a.nom.localeCompare(b.nom);
  });
}

// Formate une date ISO en format lisible fr-FR (ex: "28/03/2026")
function formaterDate(dateIso: string): string {
  try {
    return new Date(dateIso).toLocaleDateString('fr-FR');
  } catch {
    return dateIso; // Retourne la chaîne brute si le format est invalide
  }
}

// ============================================================
// SECTION 3 — SOUS-COMPOSANT : Notification
// Affichée en overlay fixe en haut à droite, disparaît après 3 secondes.
// ============================================================

interface PropsNotification {
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  onClose: () => void;
}

const Notification: React.FC<PropsNotification> = ({ message, type, onClose }) => {
  // Fermeture automatique après 3 secondes
  useEffect(() => {
    const minuterie = setTimeout(onClose, 3000);
    return () => clearTimeout(minuterie); // Nettoyage si le composant est démonté avant
  }, [onClose]);

  return (
    <div className={`notification ${type}`}>
      {message}
    </div>
  );
};

// ============================================================
// SECTION 4 — SOUS-COMPOSANT : Champ de recherche avec suggestions
// Réutilisé pour : filtre projet, recherche utilisateur, recherche projet.
// ============================================================

interface PropsChampsRecherche<T> {
  id: string;
  placeholder: string;
  valeur: string;
  suggestions: T[];
  renduSuggestion: (element: T) => React.ReactNode;
  cléSuggestion: (element: T) => string;
  onChangement: (valeur: string) => void;
  onSelectionSuggestion: (element: T) => void;
  onEffacer: () => void;
  disabled?: boolean;
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
  disabled = false,
}: PropsChampsRecherche<T>) {
  const [suggestionVisible, setSuggestionVisible] = useState(false);

  // Ferme les suggestions quand on clique ailleurs sur la page
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

  function gererChangementInput(evenement: React.ChangeEvent<HTMLInputElement>) {
    const nouvelleValeur = evenement.target.value;
    onChangement(nouvelleValeur);
    setSuggestionVisible(nouvelleValeur.trim().length >= 2 && suggestions.length > 0);
  }

  // Affiche les suggestions dès que la liste change et que le champ a du contenu
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
          onChange={gererChangementInput}
          disabled={disabled}
          autoComplete="off"
        />
        {valeur.trim().length > 0 && (
          <button
            className="clear-search visible"
            onClick={onEffacer}
            disabled={disabled}
            type="button"
          >
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
                // onMouseDown au lieu de onClick pour éviter que onBlur ferme avant
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

const Utilisateurs: React.FC = () => {
  const navigate = useNavigate();

  // --- États principaux ---
  const [utilisateurs, setUtilisateurs]     = useState<Utilisateur[]>([]);
  const [tousLesProjets, setTousLesProjets] = useState<ProjetAcces[]>([]);
  const [isLoading, setIsLoading]           = useState(true);

  // --- État du formulaire (champs contrôlés) ---
  const [formulaire, setFormulaire]                         = useState<EtatFormulaire>(ETAT_FORMULAIRE_VIDE);
  const [modeFormulaire, setModeFormulaire]                 = useState<ModeFormulaire>('creation');
  const [utilisateurSelectionne, setUtilisateurSelectionne] = useState<Utilisateur | null>(null);

  // Projets de l'utilisateur — chargés depuis l'API à la sélection
  // Chaque projet a un ID pour appeler accesService.attribuer/retirer
  const [projetsEnEdition, setProjetsEnEdition] = useState<ProjetAcces[]>([]);
  const [projetEnAttente, setProjetEnAttente]   = useState<ProjetAcces | null>(null);

  // --- États des champs de recherche ---
  const [rechercheUtilisateur, setRechercheUtilisateur] = useState('');
  const [rechercheProjet, setRechercheProjet]           = useState('');

  // --- État des notifications ---
  const [notification, setNotification] = useState<{
    message: string;
    type: 'success' | 'error' | 'warning' | 'info';
    cle: number; // Clé unique pour forcer le re-montage du composant à chaque notification
  } | null>(null);

  // ============================================================
  // SECTION 6 — DONNÉES DÉRIVÉES (calculées depuis l'état, sans setState)
  // ============================================================

  // Suggestions pour la recherche d'utilisateur
  const suggestionsUtilisateur: Utilisateur[] =
    rechercheUtilisateur.trim().length >= 2
      ? utilisateurs
          .filter(
            (u) =>
              normaliserChaine(u.nom).includes(normaliserChaine(rechercheUtilisateur)) ||
              normaliserChaine(u.prenom).includes(normaliserChaine(rechercheUtilisateur)) ||
              normaliserChaine(u.email).includes(normaliserChaine(rechercheUtilisateur))
          )
          .slice(0, 10)
      : [];

  // Suggestions pour la recherche de projet à ajouter
  // Exclut les projets déjà attribués à l'utilisateur
  const suggestionsProjet: ProjetAcces[] =
    rechercheProjet.trim().length >= 2
      ? tousLesProjets
          .filter(
            (p) =>
              !projetsEnEdition.some((pe) => pe.id === p.id) &&
              normaliserChaine(p.nom).includes(normaliserChaine(rechercheProjet))
          )
          .slice(0, 10)
      : [];

  // Tous les utilisateurs triés pour le tableau
  const utilisateursAffiches: Utilisateur[] = trierUtilisateurs(utilisateurs);

  // Détermine si les champs du formulaire sont modifiables
  // En mode création, les champs restent visibles mais vides et non éditables
  // (la création se fait via la page d'inscription)
  const formulaireEstModifiable = modeFormulaire === 'edition';

  // Détermine si le bouton "Enregistrer" est actif — uniquement en mode édition
  const enregistrerEstActif = modeFormulaire === 'edition';

  // Détermine si le bouton "Modifier" est actif
  const modifierEstActif = modeFormulaire === 'lecture';

  // Détermine si le bouton "Supprimer" est actif
  const supprimerEstActif = modeFormulaire === 'lecture';

  // Détermine si le bouton "Annuler" est actif — uniquement en mode édition
  const annulerEstActif = modeFormulaire === 'edition';

  // Détermine si la zone "Rechercher projet + Donner accès" est active — uniquement en édition
  const ajoutProjetEstActif = modeFormulaire === 'edition';

  // ============================================================
  // SECTION 7 — FONCTIONS D'AFFICHAGE DES NOTIFICATIONS
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

  const chargerUtilisateurs = useCallback(async (): Promise<Utilisateur[]> => {
    try {
      const reponse = await utilisateursService.getAll();
      const listeUtilisateurs: Utilisateur[] = reponse.data;
      setUtilisateurs(listeUtilisateurs);
      return listeUtilisateurs;
    } catch (erreur) {
      console.error('Erreur chargement utilisateurs:', erreur);
      afficherNotification('Erreur lors du chargement des utilisateurs', 'error');
      return [];
    }
  }, []);

  // Charge tous les projets disponibles depuis l'API
  const chargerProjets = useCallback(async () => {
    try {
      const reponse = await projetsService.getAll();
      const listeProjets: ProjetAcces[] = reponse.data.map((p: any) => ({
        id : p.id,
        nom: p.nom,
      }));
      setTousLesProjets(listeProjets);
    } catch (erreur) {
      console.error('Erreur chargement projets:', erreur);
      afficherNotification('Erreur lors du chargement des projets', 'error');
    }
  }, []);

  // Charge les projets d'un utilisateur spécifique via GET /utilisateurs/{id}
  const chargerProjetsUtilisateur = useCallback(async (
    idUtilisateur: number
  ): Promise<ProjetAcces[]> => {
    try {
      const reponse = await utilisateursService.getById(idUtilisateur);
      const detail  = reponse.data;
      // UtilisateurDetailModele retourne projets_accessibles avec id_projet et nom_projet
      const projets: ProjetAcces[] = (detail.projets_accessibles ?? []).map(
        (p: any) => ({
          id : p.id_projet,
          nom: p.nom_projet,
        })
      );
      return projets;
    } catch (erreur) {
      console.error('Erreur chargement projets utilisateur:', erreur);
      return [];
    }
  }, []);

  // ============================================================
  // SECTION 9 — INITIALISATION AU MONTAGE DU COMPOSANT
  // ============================================================

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/connexion');
      return;
    }

    async function initialiser() {
      setIsLoading(true);
      // Charger utilisateurs et projets en parallèle
      await Promise.all([chargerUtilisateurs(), chargerProjets()]);
      setIsLoading(false);
    }

    initialiser();
  }, [navigate, chargerUtilisateurs, chargerProjets]);

  // ============================================================
  // SECTION 10 — GESTION DES MODES DU FORMULAIRE
  // ============================================================

  // Passe en mode création : formulaire vide, tous les champs actifs
  function activerModeCreation() {
    setModeFormulaire('creation');
    setUtilisateurSelectionne(null);
    setFormulaire(ETAT_FORMULAIRE_VIDE);
    setProjetsEnEdition([]);
    setRechercheUtilisateur('');
    setRechercheProjet('');
    setProjetEnAttente(null);
  }

  // Passe en mode lecture : formulaire rempli, tous les champs désactivés
  async function activerModeLecture(utilisateur: Utilisateur) {
    setModeFormulaire('lecture');
    setUtilisateurSelectionne(utilisateur);
    setFormulaire({
      nom   : utilisateur.nom,
      prenom: utilisateur.prenom,
      email : utilisateur.email,
      role  : utilisateur.role,
      statut: utilisateur.statut,
    });
    setRechercheProjet('');
    setProjetEnAttente(null);
    // Charger les projets actuels de l'utilisateur depuis l'API
    const projets = await chargerProjetsUtilisateur(utilisateur.id);
    setProjetsEnEdition(projets);
  }

  // Passe en mode édition : formulaire pré-rempli, champs actifs
  function activerModeEdition() {
    if (!utilisateurSelectionne) return;
    setModeFormulaire('edition');
    // Les projets sont déjà chargés dans activerModeLecture
    // Pas besoin de les recharger ici
  }

  // ============================================================
  // SECTION 11 — SÉLECTION D'UN UTILISATEUR (depuis tableau ou suggestions)
  // ============================================================

  async function selectionnerUtilisateur(utilisateurId: number) {
    const utilisateurTrouve = utilisateurs.find((u) => u.id === utilisateurId);
    if (!utilisateurTrouve) return;

    await activerModeLecture(utilisateurTrouve);
    setRechercheUtilisateur(
      `${utilisateurTrouve.prenom} ${utilisateurTrouve.nom} — ${utilisateurTrouve.email}`
    );
    afficherNotification(
      `Utilisateur "${utilisateurTrouve.prenom} ${utilisateurTrouve.nom}" sélectionné`,
      'info'
    );
  }

  // ============================================================
  // SECTION 12 — ACTIONS SUR LES PROJETS
  // ============================================================

  // Ajoute le projet en attente à la liste en cours d'édition
  function ajouterProjet() {
    if (!projetEnAttente) {
      afficherNotification('Veuillez sélectionner un projet', 'warning');
      return;
    }
    if (projetsEnEdition.some((p) => p.id === projetEnAttente.id)) {
      afficherNotification(
        `Le projet "${projetEnAttente.nom}" est déjà dans la liste`,
        'warning'
      );
      return;
    }
    setProjetsEnEdition([...projetsEnEdition, projetEnAttente]);
    afficherNotification(`Projet "${projetEnAttente.nom}" ajouté`, 'success');
    setRechercheProjet('');
    setProjetEnAttente(null);
  }

  // Retire un projet de la liste en cours d'édition
  function retirerProjet(idProjet: number, nomProjet: string) {
    setProjetsEnEdition(projetsEnEdition.filter((p) => p.id !== idProjet));
    afficherNotification(`Projet "${nomProjet}" retiré`, 'warning');
  }

  // ============================================================
  // SECTION 13 — ENREGISTREMENT (modification uniquement)
  // La création d'utilisateur se fait via la page d'inscription.
  // ============================================================

  async function enregistrer() {
    // enregistrer() n'est actif qu'en mode édition
    if (modeFormulaire !== 'edition' || !utilisateurSelectionne) return;

    // --- Validation des champs obligatoires ---
    if (!formulaire.nom || !formulaire.prenom || !formulaire.email) {
      afficherNotification('Veuillez remplir tous les champs obligatoires', 'error');
      return;
    }
    if (!validerEmail(formulaire.email)) {
      afficherNotification('Email invalide. Format attendu : nom@domaine.com', 'error');
      return;
    }

    // Vérifie que le nouvel email n'appartient pas à un autre utilisateur
    const emailPrisParAutre = utilisateurs.some(
      (u) => u.id !== utilisateurSelectionne.id && u.email === formulaire.email
    );
    if (emailPrisParAutre) {
      afficherNotification('Cet email est déjà utilisé', 'error');
      return;
    }

    try {
      // Étape 1 — Mettre à jour les infos de l'utilisateur
      await utilisateursService.update(utilisateurSelectionne.id, {
        nouveau_nom   : formulaire.nom,
        nouveau_prenom: formulaire.prenom,
        nouveau_email : formulaire.email,
      });

      // Étape 2 — Synchroniser les accès projets
      // Comparer les projets actuels en BD avec ceux en édition
      const projetsActuels = await chargerProjetsUtilisateur(utilisateurSelectionne.id);
      const idsActuels = new Set(projetsActuels.map((p) => p.id));
      const idsVoulus  = new Set(projetsEnEdition.map((p) => p.id));

      // Retirer les projets supprimés
      for (const idProjet of idsActuels) {
        if (!idsVoulus.has(idProjet)) {
          try {
            await accesService.retirer(idProjet, utilisateurSelectionne.id);
          } catch (e) {
            console.warn(`Impossible de retirer l'accès au projet ${idProjet}`, e);
          }
        }
      }

      // Ajouter les nouveaux projets
      for (const projet of projetsEnEdition) {
        if (!idsActuels.has(projet.id)) {
          try {
            await accesService.attribuer(projet.id, {
              id_utilisateur: utilisateurSelectionne.id,
            });
          } catch (e) {
            console.warn(`Impossible d'attribuer l'accès au projet ${projet.id}`, e);
          }
        }
      }

      afficherNotification(
        `Utilisateur "${formulaire.prenom} ${formulaire.nom}" modifié avec succès`,
        'success'
      );

      const listeMAJ = await chargerUtilisateurs();
      const utilisateurMAJ = listeMAJ.find((u) => u.id === utilisateurSelectionne.id);
      if (utilisateurMAJ) await activerModeLecture(utilisateurMAJ);

    } catch (erreur) {
      console.error('Erreur modification utilisateur:', erreur);
      afficherNotification("Erreur lors de la modification de l'utilisateur", 'error');
    }
  }

  // ============================================================
  // SECTION 14 — ANNULATION
  // ============================================================

  function annuler() {
    if (modeFormulaire === 'edition' && utilisateurSelectionne) {
      // Retour en lecture : restaure les données originales de l'utilisateur sélectionné
      activerModeLecture(utilisateurSelectionne);
      afficherNotification('Modifications annulées', 'warning');
    }
  }

  // ============================================================
  // SECTION 15 — SUPPRESSION
  // ============================================================

  async function supprimerUtilisateur() {
    if (!utilisateurSelectionne) {
      afficherNotification("Veuillez d'abord sélectionner un utilisateur", 'warning');
      return;
    }

    const confirmation = window.confirm(
      `Êtes-vous sûr de vouloir supprimer l'utilisateur "${utilisateurSelectionne.prenom} ${utilisateurSelectionne.nom}" ?`
    );
    if (!confirmation) return;

    const prenomSauvegarde = utilisateurSelectionne.prenom;
    const nomSauvegarde = utilisateurSelectionne.nom;

    try {
      await utilisateursService.delete(utilisateurSelectionne.id);
      await chargerUtilisateurs();
      activerModeCreation();
      afficherNotification(
        `Utilisateur "${prenomSauvegarde} ${nomSauvegarde}" supprimé avec succès`,
        'success'
      );
    } catch (erreur) {
      console.error('Erreur suppression utilisateur:', erreur);
      afficherNotification("Erreur lors de la suppression de l'utilisateur", 'error');
    }
  }

  // ============================================================
  // SECTION 16 — APPROBATION / REFUS RAPIDE (depuis le tableau)
  // ============================================================

  async function approuverUtilisateur(utilisateurId: number) {
    const utilisateurCible = utilisateurs.find((u) => u.id === utilisateurId);
    try {
      await utilisateursService.approuver(utilisateurId);
      await chargerUtilisateurs();
      afficherNotification(
        `Utilisateur "${utilisateurCible?.prenom} ${utilisateurCible?.nom}" approuvé`,
        'success'
      );
    } catch (erreur) {
      console.error('Erreur approbation:', erreur);
      afficherNotification("Erreur lors de l'approbation", 'error');
    }
  }

  async function refuserUtilisateur(utilisateurId: number) {
    const utilisateurCible = utilisateurs.find((u) => u.id === utilisateurId);
    try {
      await utilisateursService.refuser(utilisateurId);
      await chargerUtilisateurs();
      afficherNotification(
        `Utilisateur "${utilisateurCible?.prenom} ${utilisateurCible?.nom}" refusé`,
        'warning'
      );
    } catch (erreur) {
      console.error('Erreur refus:', erreur);
      afficherNotification('Erreur lors du refus', 'error');
    }
  }

  // ============================================================
  // SECTION 17 — RENDU DU STATUT DANS LE TABLEAU
  // ============================================================

  function renduCelluleStatut(utilisateur: Utilisateur): React.ReactNode {
    if (utilisateur.statut === 'en_attente') {
      return (
        <div className="status-cell">
          <button
            className="quick-approve"
            title="Approuver"
            onClick={(e) => {
              e.stopPropagation(); // Empêche la sélection de la ligne
              approuverUtilisateur(utilisateur.id);
            }}
          >
            ✓
          </button>
          <span className="badge badge-pending">en attente</span>
          <button
            className="quick-reject"
            title="Refuser"
            onClick={(e) => {
              e.stopPropagation();
              refuserUtilisateur(utilisateur.id);
            }}
          >
            ✗
          </button>
        </div>
      );
    }
    if (utilisateur.statut === 'approuve') {
      return <span className="badge badge-active">approuvé</span>;
    }
    if (utilisateur.statut === 'refuse') {
      return <span className="badge badge-refuse">refusé</span>;
    }
    return <span className="badge badge-pending">{utilisateur.statut}</span>;
  }

  // ============================================================
  // SECTION 18 — RENDU DE LA LISTE DES PROJETS (formulaire)
  // ============================================================

  function renduListeProjets(): React.ReactNode {
    if (projetsEnEdition.length === 0) {
      return <div className="italic-text">Aucun projet</div>;
    }

    return (
      <ul className="projets-list">
        {projetsEnEdition.map((projet) => (
          <li key={projet.id}>
            <span>• {projet.nom}</span>
            {/* Bouton retirer visible seulement en mode édition */}
            {ajoutProjetEstActif && (
              <button
                className="remove-projet"
                type="button"
                onClick={() => retirerProjet(projet.id, projet.nom)}
              >
                ✖
              </button>
            )}
          </li>
        ))}
      </ul>
    );
  }

  // ============================================================
  // SECTION 19 — RENDU CONDITIONNEL : CHARGEMENT
  // ============================================================

  if (isLoading) {
    return <div className="container">Chargement...</div>;
  }

  // ============================================================
  // SECTION 20 — RENDU PRINCIPAL (JSX)
  // ============================================================

  return (
    <>
      {/* Notification flottante — re-montée à chaque nouvelle notification grâce à la clé */}
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
        {/* SECTION FORMULAIRE — Grille 5x3                    */}
        {/* -------------------------------------------------- */}
        <div className="section">
          <Header titre="Utilisateurs" />
          <div className="grid-5x3">

            {/* CELLULE 1 — Nom */}
            <div className="cell">
              <label className="cell-title" htmlFor="champ-nom">
                Nom <span className="required-star">*</span>
              </label>
              <input
                type="text"
                id="champ-nom"
                className="form-input"
                placeholder="Nom"
                value={formulaire.nom}
                readOnly={!formulaireEstModifiable}
                onChange={(e) => setFormulaire({ ...formulaire, nom: e.target.value })}
              />
            </div>

            {/* CELLULE 2 — Prénom */}
            <div className="cell">
              <label className="cell-title" htmlFor="champ-prenom">
                Prénom <span className="required-star">*</span>
              </label>
              <input
                type="text"
                id="champ-prenom"
                className="form-input"
                placeholder="Prénom"
                value={formulaire.prenom}
                readOnly={!formulaireEstModifiable}
                onChange={(e) => setFormulaire({ ...formulaire, prenom: e.target.value })}
              />
            </div>

            {/* CELLULE 3 — Email */}
            <div className="cell">
              <label className="cell-title" htmlFor="champ-email">
                Email <span className="required-star">*</span>
              </label>
              <input
                type="email"
                id="champ-email"
                className="form-input"
                placeholder="email@exemple.com"
                value={formulaire.email}
                readOnly={!formulaireEstModifiable}
                onChange={(e) => setFormulaire({ ...formulaire, email: e.target.value })}
              />
            </div>

            {/* CELLULE 4 — Rôle */}
            {/* Le rôle est en lecture seule :
                - La table "utilisateurs" a une contrainte CHECK (role = 'utilisateur')
                - Le super_admin est dans une table séparée "super_admin"
                - PUT /utilisateurs/{id} (ModifierUtilisateurModele) n'expose pas de champ "role"
                Le rôle affiché ici provient de GET /utilisateurs et est informatif uniquement. */}
            <div className="cell">
              <label className="cell-title" htmlFor="champ-role">
                Rôle
              </label>
              <input
                type="text"
                id="champ-role"
                className="form-input"
                value={
                  formulaire.role === 'super_admin'
                    ? 'Super Admin'
                    : formulaire.role === 'utilisateur'
                    ? 'Utilisateur'
                    : formulaire.role || '—'
                }
                readOnly
              />
            </div>

            {/* CELLULE 5 — Statut */}
            <div className="cell">
              <label className="cell-title" htmlFor="champ-statut">
                Statut <span className="required-star">*</span>
              </label>
              <select
                id="champ-statut"
                className="form-select"
                value={formulaire.statut}
                disabled={!formulaireEstModifiable}
                onChange={(e) => setFormulaire({ ...formulaire, statut: e.target.value })}
              >
                <option value="" disabled>-- Sélectionner un statut --</option>
                <option value="en_attente">En attente</option>
                <option value="approuve">Approuvé</option>
                <option value="refuse">Refusé</option>
              </select>
            </div>

            {/* LIGNE 2 — Col 1 : Chercher utilisateur */}
            <div className="cell">
              <label className="cell-title">Chercher utilisateur</label>
              <ChampRecherche<Utilisateur>
                id="recherche-utilisateur"
                placeholder="Nom, prénom ou email..."
                valeur={rechercheUtilisateur}
                suggestions={suggestionsUtilisateur}
                cléSuggestion={(u) => String(u.id)}
                renduSuggestion={(u) => (
                  <>
                    <strong>{u.prenom} {u.nom}</strong> — {u.email}
                  </>
                )}
                onChangement={(valeur) => setRechercheUtilisateur(valeur)}
                onSelectionSuggestion={(u) => selectionnerUtilisateur(u.id)}
                onEffacer={() => {
                  setRechercheUtilisateur('');
                  activerModeCreation();
                  afficherNotification('Recherche effacée', 'info');
                }}
              />
            </div>

            {/* LIGNE 2 — Col 2 : Projets attribués */}
            <div className="cell">
              <label className="cell-title">Projets attribués</label>
              {renduListeProjets()}
            </div>

            {/* LIGNE 2 — Col 3 : Attribuer un projet */}
            <div className="cell">
              <label className="cell-title">Attribuer un projet</label>
              <ChampRecherche<ProjetAcces>
                id="recherche-projet"
                placeholder="Chercher un projet..."
                valeur={rechercheProjet}
                suggestions={suggestionsProjet}
                cléSuggestion={(p) => String(p.id)}
                renduSuggestion={(p) => <strong>{p.nom}</strong>}
                onChangement={(valeur) => {
                  setRechercheProjet(valeur);
                  if (projetEnAttente && valeur !== projetEnAttente.nom) {
                    setProjetEnAttente(null);
                  }
                }}
                onSelectionSuggestion={(p) => {
                  setRechercheProjet(p.nom);
                  setProjetEnAttente(p);
                }}
                onEffacer={() => {
                  setRechercheProjet('');
                  setProjetEnAttente(null);
                }}
                disabled={!ajoutProjetEstActif}
              />
              <button
                className="add-button"
                type="button"
                disabled={!ajoutProjetEstActif}
                onClick={ajouterProjet}
              >
                + Donner accès
              </button>
            </div>

            {/* LIGNE 2 — Col 4+5 : Boutons d'action */}
            <div className="cell cell-span-2">
              <div className="button-group">
                <button
                  className="action-button"
                  type="button"
                  disabled={!modifierEstActif}
                  onClick={activerModeEdition}
                >
                  Modifier
                </button>
                <button
                  className="action-button"
                  type="button"
                  disabled={!enregistrerEstActif}
                  onClick={enregistrer}
                >
                  Enregistrer
                </button>
                <button
                  className="cancel-button"
                  type="button"
                  disabled={!annulerEstActif}
                  onClick={annuler}
                >
                  Annuler
                </button>
                <button
                  className="delete-button"
                  type="button"
                  disabled={!supprimerEstActif}
                  onClick={supprimerUtilisateur}
                >
                  Supprimer
                </button>
              </div>
            </div>
        </div>

        {/* -------------------------------------------------- */}
        {/* SECTION TABLEAU — Liste des utilisateurs           */}
        {/* -------------------------------------------------- */}
        <div className="section">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Nom</th>
                <th>Prénom</th>
                <th>Email</th>
                <th>Rôle</th>
                <th>Statut</th>
                <th>Date d'inscription</th>
              </tr>
            </thead>
            <tbody>
              {utilisateursAffiches.map((utilisateur) => (
                <tr
                  key={utilisateur.id}
                  style={{ cursor: 'pointer' }}
                  onClick={() => selectionnerUtilisateur(utilisateur.id)}
                >
                  <td>{utilisateur.id}</td>
                  <td>{utilisateur.nom}</td>
                  <td>{utilisateur.prenom}</td>
                  <td>{utilisateur.email}</td>
                  <td>
                    <span
                      className={`badge ${
                        utilisateur.role === 'super_admin' ? 'badge-admin' : 'badge-user'
                      }`}
                    >
                      {utilisateur.role === 'super_admin' ? 'super_admin' : 'utilisateur'}
                    </span>
                  </td>
                  <td>{renduCelluleStatut(utilisateur)}</td>
                  <td>{formaterDate(utilisateur.date_creation)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
};

export default Utilisateurs;
